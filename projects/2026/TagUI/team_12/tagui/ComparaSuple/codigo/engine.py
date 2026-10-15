"""Ejecuta TagUI y administra la conexión con Chrome."""
from contextlib import contextmanager
import json
import os
import platform
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
import uuid
from urllib.parse import urlparse

from capturas import atomic_json, normalize_capture, now
from proveedores import allowed_hosts, allowed_url, read_providers, capture_matches
from runtime_tagui import ROOT, TAGUI, prepare_runtime, check_installation

HIDDEN = getattr(subprocess, 'CREATE_NO_WINDOW', 0)


class BrowserDisconnected(RuntimeError):
    """La conexión terminó; la corrida debe conservar lo pendiente sin insistir."""


def session_profile():
    """Guarda la sesión fuera del proyecto."""
    base = Path(os.environ.get('LOCALAPPDATA') or Path.home() / '.local/share')
    return base / 'ComparaSuple/perfiles/mercadolibre'


@contextmanager
def profile_lock(profile):
    """Evita que dos robots compartan el mismo perfil."""
    profile = Path(profile)
    profile.mkdir(parents=True, exist_ok=True)
    with (profile / '.comparasuple.lock').open('a+b') as handle:
        handle.seek(0, 2)
        if handle.tell() == 0:
            handle.write(b'0')
            handle.flush()
        handle.seek(0)
        if os.name == 'nt':
            import msvcrt
            lock, unlock = lambda: msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1), lambda: msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl
            lock, unlock = lambda: fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB), lambda: fcntl.flock(handle, fcntl.LOCK_UN)
        try:
            lock()
        except OSError as error:
            raise RuntimeError('El perfil está en uso. Cerrá la otra ejecución o la ventana de preparar sesión.') from error
        try:
            yield
        finally:
            handle.seek(0)
            unlock()


def browser_path(chrome_only=False):
    candidates = [os.environ.get('COMPARASUPLE_BROWSER', '')]
    for env in ('PROGRAMW6432', 'PROGRAMFILES', 'PROGRAMFILES(X86)', 'LOCALAPPDATA'):
        base = Path(os.environ.get(env, 'C:/'))
        candidates.extend([
            base / 'Google/Chrome/Application/chrome.exe',
            base / 'Microsoft/Edge/Application/msedge.exe',
        ])
    return next((Path(p) for p in candidates if p and Path(p).is_file()
                 and (not chrome_only or Path(p).name.lower() == 'chrome.exe')), None)


def current_chrome_endpoint():
    """El archivo puede sobrevivir a Chrome: comprobar también el puerto local."""
    port_file = Path(os.environ.get('LOCALAPPDATA', '')) / 'Google/Chrome/User Data/DevToolsActivePort'
    try:
        parts = port_file.read_text(encoding='utf-8').splitlines()
    except (FileNotFoundError, UnicodeError):
        return None
    except OSError as error:
        raise RuntimeError('No se pudo leer la conexión local de Chrome. Ejecutá ComparaSuple con tu usuario habitual.') from error
    if (len(parts) < 2 or not parts[0].isdigit() or not 0 < int(parts[0]) < 65536 or
            not parts[1].startswith('/devtools/browser/') or any(c.isspace() for c in parts[1])):
        return None
    try:
        # Solo TCP: no solicita permiso ni crea otra sesión de depuración.
        with socket.create_connection(('127.0.0.1', int(parts[0])), timeout=.3):
            pass
    except OSError:
        return None
    return 'ws://127.0.0.1:' + parts[0] + parts[1]


def browser_version(browser):
    """Lee la versión instalada sin abrir otra instancia del navegador."""
    if os.name != 'nt':
        return None
    import ctypes
    from ctypes import wintypes
    version = ctypes.WinDLL('version', use_last_error=True)
    version.GetFileVersionInfoSizeW.argtypes = [wintypes.LPCWSTR, ctypes.POINTER(wintypes.DWORD)]
    version.GetFileVersionInfoSizeW.restype = wintypes.DWORD
    version.GetFileVersionInfoW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, ctypes.c_void_p]
    version.VerQueryValueW.argtypes = [ctypes.c_void_p, wintypes.LPCWSTR, ctypes.POINTER(ctypes.c_void_p), ctypes.POINTER(wintypes.UINT)]
    size = version.GetFileVersionInfoSizeW(str(browser), None)
    if not size:
        return None
    data = ctypes.create_string_buffer(size)
    pointer, length = ctypes.c_void_p(), wintypes.UINT()
    if (not version.GetFileVersionInfoW(str(browser), 0, size, data) or
            not version.VerQueryValueW(data, '\\', ctypes.byref(pointer), ctypes.byref(length)) or length.value < 24):
        return None
    values = ctypes.cast(pointer, ctypes.POINTER(wintypes.DWORD))
    if values[0] != 0xFEEF04BD:
        return None
    return '.'.join(str(value) for value in (values[4] >> 16, values[4] & 65535, values[5] >> 16, values[5] & 65535))


def ensure_existing_chrome(timeout=300):
    """Guía la habilitación manual y espera sin comenzar consultas."""
    browser = browser_path(chrome_only=True)
    if not browser:
        raise RuntimeError('Este modo necesita Google Chrome estable instalado en Windows. No alcanza con tener Edge.')
    version = browser_version(browser)
    if version and int(version.split('.')[0]) < 144:
        raise RuntimeError('Chrome ' + version + ' no tiene el modo requerido. Actualizalo a Chrome 144 o posterior '
                           'desde chrome://settings/help, reinicialo y repetí la operación.')
    endpoint = current_chrome_endpoint()
    if endpoint:
        print('Paso 1/2: depuración remota disponible.', flush=True)
        return endpoint
    print('Paso 1/2: falta habilitar la depuración remota. Se abre la opción en tu Chrome habitual.\n'
          'En «Remote debugging / Depuración remota», activá «Allow remote debugging» '
          '(permitir depuración remota).\n'
          'Mantené Chrome abierto. El programa detectará el cambio automáticamente; no hace falta pulsar Enter.', flush=True)
    # Chrome personal nunca se incorpora a los procesos que termina el robot.
    subprocess.Popen([str(browser), '--start-maximized', '--new-window',
                      'chrome://inspect/#remote-debugging'], stdout=subprocess.DEVNULL,
                     stderr=subprocess.DEVNULL, creationflags=HIDDEN)
    print(f'Esperando la habilitación, hasta {timeout} segundos. Ctrl+C cancela sin iniciar búsquedas.', flush=True)
    deadline = time.monotonic() + timeout
    reminder = time.monotonic() + 30
    while time.monotonic() < deadline:
        endpoint = current_chrome_endpoint()
        if endpoint:
            print('Paso 1/2: depuración remota habilitada.', flush=True)
            return endpoint
        if time.monotonic() >= reminder:
            print('Sigo esperando que habilites la opción en chrome://inspect/#remote-debugging.', flush=True)
            reminder = time.monotonic() + 30
        time.sleep(.5)
    raise RuntimeError('Chrome no publicó un puerto de depuración activo. Revisá '
                       'chrome://inspect/#remote-debugging. Si la opción no aparece, actualizá Chrome; '
                       'si está deshabilitada por tu organización, consultá al administrador. '
                       'Usá Chrome estable con tu usuario habitual, sin un perfil de datos personalizado.')


def stop_process(process):
    if process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)


def guard_bridge(process):
    """Windows termina el puente si se cierra abruptamente la consola de Python."""
    import ctypes
    from ctypes import wintypes

    class Limits(ctypes.Structure):
        _fields_ = [('process_time', ctypes.c_longlong), ('job_time', ctypes.c_longlong),
                    ('flags', wintypes.DWORD), ('min_working', ctypes.c_size_t),
                    ('max_working', ctypes.c_size_t), ('active', wintypes.DWORD),
                    ('affinity', ctypes.c_size_t), ('priority', wintypes.DWORD),
                    ('scheduling', wintypes.DWORD)]

    class ExtendedLimits(ctypes.Structure):
        _fields_ = [('basic', Limits), ('io', ctypes.c_ulonglong * 6),
                    ('process_memory', ctypes.c_size_t), ('job_memory', ctypes.c_size_t),
                    ('peak_process_memory', ctypes.c_size_t), ('peak_job_memory', ctypes.c_size_t)]

    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.CreateJobObjectW.argtypes = [ctypes.c_void_p, wintypes.LPCWSTR]
    kernel.CreateJobObjectW.restype = wintypes.HANDLE
    kernel.SetInformationJobObject.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD]
    kernel.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    job = kernel.CreateJobObjectW(None, None)
    limits = ExtendedLimits()
    limits.basic.flags = 0x2000  # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE.
    try:
        if not job or not kernel.SetInformationJobObject(job, 9, ctypes.byref(limits), ctypes.sizeof(limits)):
            raise ctypes.WinError(ctypes.get_last_error())
        # Solo se incorpora nuestro PHP. Chrome personal nunca pertenece al job.
        if not kernel.AssignProcessToJobObject(job, int(process._handle)):
            raise ctypes.WinError(ctypes.get_last_error())
    except BaseException:
        stop_process(process)
        if job:
            kernel.CloseHandle(job)
        raise
    return lambda: kernel.CloseHandle(job)


class Engine:
    def __init__(self, run_dir, headless=False, human=False, profile_template=None, attach_existing=False):
        if human and headless:
            raise ValueError('El modo humano requiere navegador visible.')
        if attach_existing and (headless or profile_template is not None):
            raise ValueError('Chrome actual requiere modo visible y conserva su propio perfil.')
        self.run_dir = Path(run_dir).resolve()
        self.work = Path(tempfile.mkdtemp(prefix='comparasuple-'))
        self.processes = []
        self.handles = []
        self.headless = headless
        self.human = human
        self.human_started = False
        self.credentials = {}  # main.py las asigna después de crear la captura.
        self.profile_template = Path(profile_template).resolve() if profile_template is not None else None
        self.profile_guard = None
        self.chrome = None
        self.browser_ws = None
        self.attach_existing = attach_existing
        self.external_bridge = None
        self.release_bridge_guard = None
        self.attached_target = None
        self.control_sequence = 0
        self.browser_hwnd = None
        self.log_offsets = {}
        self.diagnostic = {}
        self.diagnostic_at = 0
        self.logged_error = None
        self.recovery_attempted = False
        self.preserve_window = False

    def start(self):
        self.save_diagnostic('abriendo_navegador')
        try:
            self._start()
        except BaseException as error:
            self.save_error_logs(error)
            try:
                self.close()
            except Exception:
                pass  # El fallo de cierre queda registrado sin ocultar el arranque.
            raise

    def _start(self):
        # Sólo una orden nueva puede borrar la señal de cancelación.
        if self.human:
            (self.work / 'human_cancelled.txt').unlink(missing_ok=True)
        self.diagnostic['environment'] = dict(python=sys.version.split()[0], executable=sys.executable,
                                              windows=platform.platform(), mode='visible' if self.human else 'segundo_plano')
        self.save_diagnostic('comprobando_instalacion')
        self.diagnostic['environment']['tagui'] = check_installation(human=self.human)
        browser = browser_path(chrome_only=self.attach_existing)
        if not browser:
            raise RuntimeError('No encuentro Google Chrome estable. Instalalo para usar este modo.' if self.attach_existing
                               else 'No encuentro Chrome o Edge. Instalá uno o configurá COMPARASUPLE_BROWSER.')
        self.diagnostic['environment'].update(browser=str(browser), browser_version=browser_version(browser))
        self.save_diagnostic('preparando_tagui')
        prepare_runtime(self.work, self.human)

        if self.attach_existing:
            self._attach_existing()
            return

        # Reutilizar el perfil conserva cookies y verificaciones manuales.
        self.profile = self.profile_template or self.work / 'browser-profile'
        guard = profile_lock(self.profile)
        guard.__enter__()
        self.profile_guard = guard
        # Un archivo de una ejecución anterior no identifica a nuestro Chrome.
        (self.profile / 'DevToolsActivePort').unlink(missing_ok=True)
        window = '--window-size=1920,1080' if self.headless else '--start-maximized'
        args = [
            str(browser), '--remote-debugging-port=0',
            '--remote-debugging-address=127.0.0.1',
            '--user-data-dir=' + str(self.profile), '--no-first-run',
            '--no-default-browser-check', '--disable-gpu',
            '--disable-software-rasterizer', window,
            '--lang=es-419,es', 'about:blank',
        ]
        if self.headless:
            args.append('--headless=new')
        chrome_log = open(self.work / 'chrome.log', 'ab')
        self.handles.append(chrome_log)
        chrome = subprocess.Popen(
            args, stdout=chrome_log, stderr=chrome_log, creationflags=HIDDEN
        )
        self.processes.append(chrome)
        self.chrome = chrome
        self.browser_pid = chrome.pid
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            if chrome.poll() is not None:
                raise BrowserDisconnected('Chrome se cerró al iniciar. Revisar error.log de la captura.')
            port_file = self.profile / 'DevToolsActivePort'
            if port_file.exists():
                try:
                    port, browser_path_ws = port_file.read_text().splitlines()[:2]
                    if not port.isdigit() or not 0 < int(port) < 65536 or not browser_path_ws.startswith('/devtools/browser/'):
                        raise ValueError('Conexión de Chrome inválida')
                    browser_ws = 'ws://127.0.0.1:' + port + browser_path_ws
                    with urllib.request.urlopen(
                        'http://127.0.0.1:' + port + '/json', timeout=2
                    ) as response:
                        tabs = json.load(response)
                    tab = next((t for t in tabs if t.get('type') == 'page'), None)
                    if tab:
                        info = self.browser_command('SystemInfo.getProcessInfo', websocket=browser_ws)
                        owned = any(p.get('type') == 'browser' and p.get('id') == chrome.pid
                                    for p in info.get('processInfo', []))
                        if not owned or chrome.poll() is not None:
                            raise RuntimeError('El puerto de depuración no pertenece al navegador de esta ejecución.')
                        self.browser_ws = browser_ws
                        self.ws = tab['webSocketDebuggerUrl']
                        if not self.headless:
                            self._prepare_window(tab['id'])
                        return
                except (OSError, ValueError, IndexError):
                    pass
            time.sleep(.2)
        raise RuntimeError('Chrome no publicó su conexión de depuración en 30 segundos.')

    def _attach_existing(self):
        self.save_diagnostic('esperando_depuracion')
        self.browser_ws = ensure_existing_chrome()
        self.ws = 'comparasuple:page'
        self.save_diagnostic('esperando_permiso')
        print('Paso 2/2: en Chrome, aceptá «Permitir / Allow» para conectar el programa.\n'
              'Habilitar la casilla y aceptar este aviso son dos pasos distintos. '
              'Las búsquedas esperan la autorización.', flush=True)
        self._open_external_bridge()
        try:
            info = self.browser_command('SystemInfo.getProcessInfo')
        except RuntimeError as error:
            raise RuntimeError('No se confirmó la autorización de Chrome. ' + str(error)) from error
        browsers = [p for p in info.get('processInfo', []) if p.get('type') == 'browser']
        if len(browsers) != 1 or not isinstance(browsers[0].get('id'), int):
            raise RuntimeError('No se pudo identificar el proceso del Chrome autorizado.')
        self.browser_pid = browsers[0]['id']
        self._open_run_window()
        self.save_diagnostic('navegador_listo')
        print('Chrome autorizado y ventana maximizada. Ya se puede iniciar la captura.', flush=True)

    def _open_run_window(self):
        self.attached_target = self.browser_command('Target.createTarget',
            {'url': 'about:blank', 'newWindow': True})['targetId']
        session = self.browser_command('Target.attachToTarget',
            {'targetId': self.attached_target, 'flatten': True})['sessionId']
        self.browser_command('ComparaSuple.setSession', {'sessionId': session})
        self._prepare_window(self.attached_target)

    def _open_external_bridge(self):
        """Abre el puente sin crear ventanas ni navegar."""
        shutil.copy2(ROOT / 'chrome_actual.php', self.work / 'chrome_actual.php')
        log = open(self.work / 'chrome-actual.log', 'ab')
        self.handles.append(log)
        self.external_bridge = subprocess.Popen(
            [str(TAGUI / 'php/php.exe'), '-q', 'chrome_actual.php', self.browser_ws],
            cwd=self.work, stdout=log, stderr=log, creationflags=HIDDEN)
        self.processes.append(self.external_bridge)
        self.release_bridge_guard = guard_bridge(self.external_bridge)

    def recover_connection(self):
        """Recupera la misma pestaña una vez por incidente, sin repetir clics."""
        self.preserve_window = True
        if not self.attach_existing or self.attached_target is None or self.recovery_attempted:
            raise BrowserDisconnected('No se pudo recuperar la conexión. El avance queda guardado para reanudar.')
        self.recovery_attempted = True
        old = self.external_bridge
        if old is not None and old.poll() is None and self.external_status().get('phase') != 'failed':
            raise BrowserDisconnected('El puente sigue activo; no se abrirá otra conexión simultánea.')
        print('Recuperando la conexión con la misma ventana. Si Chrome pide Permitir, aceptá para continuar.', flush=True)
        try:
            if old is not None:
                stop_process(old)
                if old in self.processes:
                    self.processes.remove(old)
            if self.release_bridge_guard is not None:
                self.release_bridge_guard()
                self.release_bridge_guard = None
            self.external_bridge = None
            # Un proceso nuevo nunca debe ejecutar solicitudes de la conexión anterior.
            for name in ('control.in', 'control.out', 'tagui_chrome.in', 'tagui_chrome.out'):
                (self.work / name).unlink(missing_ok=True)
            self.control_sequence = 0
            self._open_external_bridge()
            info = self.browser_command('SystemInfo.getProcessInfo')
            browsers = [p.get('id') for p in info.get('processInfo', []) if p.get('type') == 'browser']
            if browsers != [self.browser_pid]:
                raise BrowserDisconnected('Chrome cambió de proceso; no se retomará otra ventana.')
            target = self.browser_command('Target.getTargetInfo', {'targetId': self.attached_target}).get('targetInfo', {})
            if target.get('targetId') != self.attached_target or target.get('type') != 'page':
                raise BrowserDisconnected('La pestaña del comparador ya no está disponible.')
            session = self.browser_command('Target.attachToTarget',
                {'targetId': self.attached_target, 'flatten': True})['sessionId']
            self.browser_command('ComparaSuple.setSession', {'sessionId': session})
            return True
        except Exception as error:
            self.save_error_logs(error)
            if self.external_bridge is not None:
                stop_process(self.external_bridge)
            if isinstance(error, BrowserDisconnected):
                raise
            raise BrowserDisconnected('No se pudo restablecer el puente: ' + str(error)) from error

    def _prepare_window(self, target):
        """Identifica la ventana exacta del comparador y la maximiza."""
        window = self.browser_command('Browser.getWindowForTarget', {'targetId': target})
        self.browser_command('Browser.setWindowBounds', {'windowId': window['windowId'], 'bounds': {'windowState': 'maximized'}})
        if self.human:
            marker = 'ComparaSuple ' + uuid.uuid4().hex
            self.browser_command('Runtime.evaluate', {'expression': 'document.title = ' + json.dumps(marker)}, websocket=self.ws)
            self.browser_hwnd = self._window_handle(marker)

    def _window_handle(self, marker):
        """Relaciona la ventana CDP creada por el robot con su HWND de Windows."""
        import ctypes
        from ctypes import wintypes
        user32 = ctypes.WinDLL('user32', use_last_error=True)
        callback = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
        user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
        user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
        user32.IsWindowVisible.argtypes = [wintypes.HWND]
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            windows = []
            @callback
            def visit(hwnd, _):
                pid = wintypes.DWORD()
                user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
                title = ctypes.create_unicode_buffer(512)
                if pid.value == self.browser_pid and user32.IsWindowVisible(hwnd):
                    user32.GetWindowTextW(hwnd, title, len(title))
                    if marker in title.value:
                        windows.append(int(hwnd))
                return True
            user32.EnumWindows(visit, 0)
            if len(windows) == 1:
                return windows[0]
            time.sleep(.1)
        raise RuntimeError('No se pudo identificar exclusivamente la ventana del comparador.')

    def _external_command(self, method, params, page):
        """Publica cada comando una vez y espera su respuesta."""
        if self.external_bridge is None or self.external_bridge.poll() is not None:
            raise BrowserDisconnected(self.external_error())
        self.control_sequence += 1
        number = self.control_sequence
        request = dict(id=number, method=method, params=params or {}, scope='page' if page else 'browser')
        for attempt in range(20):
            try:
                atomic_json(self.work / 'control.in', request)
                break
            except PermissionError:
                # Se reintenta publicar el mismo ID, nunca ejecutar otra vez el comando.
                if attempt == 19:
                    raise
                time.sleep(.05)
        deadline = time.monotonic() + (135 if number == 1 else 45)
        while time.monotonic() < deadline:
            response_file = self.work / 'control.out'
            if response_file.is_file():
                try:
                    response = json.loads(response_file.read_text(encoding='utf-8'))
                except (OSError, ValueError):
                    response = {}
                if response.get('id') == number:
                    if 'error' in response:
                        if self.external_status().get('phase') == 'failed':
                            raise BrowserDisconnected(self.external_error())
                        if response['error'].get('code') == -32002:
                            raise RuntimeError(self.external_error('cdp_timeout'))
                        raise RuntimeError('Chrome rechazó el comando ' + method)
                    return response.get('result', {})
            if self.external_bridge.poll() is not None:
                raise BrowserDisconnected(self.external_error())
            time.sleep(.05)
        raise RuntimeError('Chrome no respondió: revisá el permiso de conexión en su ventana.')

    def external_status(self):
        try:
            status = json.loads((self.work / 'chrome-actual-status.json').read_text(encoding='utf-8'))
            return status if isinstance(status, dict) else {}
        except (OSError, ValueError):
            return {}

    def external_error(self, code=None):
        # Solo textos propios: nunca mostrar respuestas crudas de Chrome/cuenta.
        messages = {
            'connection_refused': 'El puerto de Chrome no acepta conexiones. Chrome puede haberse cerrado o desactivado la depuración.',
            'connect_timeout': 'Se agotó el tiempo para conectar con el puerto local de Chrome.',
            'handshake_timeout': 'Chrome no completó el permiso de conexión a tiempo. Revisá el aviso Permitir en su ventana.',
            'handshake_rejected': 'Chrome rechazó la conexión de depuración. Revisá el permiso en chrome://inspect/#remote-debugging.',
            'connection_lost': 'Se perdió la conexión de depuración con Chrome.',
            'cdp_timeout': 'Chrome no respondió al comando en el tiempo previsto. Revisá error.log.',
            'socket_timeout': 'Se agotó la espera de respuesta de la conexión con Chrome. Revisá error.log.',
            'frame_timeout': 'La respuesta de Chrome quedó incompleta; se detuvo el puente. Revisá error.log.',
            'session_mismatch': 'Chrome respondió desde otra sesión; se detuvo el puente. Revisá error.log.',
            'protocol_error': 'La conexión de depuración recibió una respuesta inválida. Revisá error.log.',
            'ipc_error': 'El puente no pudo intercambiar sus archivos de trabajo. Revisá error.log.',
            'config_error': 'El puente recibió una conexión local de Chrome inválida.',
        }
        return messages.get(code or self.external_status().get('code'),
                            'El puente de Chrome terminó antes de completar la conexión. Revisá error.log.')

    def browser_command(self, method, params=None, websocket=None, wait=True):
        """Envía el comando al Chrome seleccionado."""
        if self.attach_existing:
            if method == 'Browser.close':
                raise RuntimeError('El navegador personal no pertenece al robot y no se puede cerrar.')
            return self._external_command(method, params, websocket == self.ws)
        endpoint = websocket or self.browser_ws
        if not endpoint:
            raise RuntimeError('Chrome todavía no publicó su conexión propia.')
        php = (
            "require 'ws/Base.php'; require 'ws/Client.php'; require 'ws/Exception.php'; "
            "require 'ws/BadOpcodeException.php'; require 'ws/BadUriException.php'; "
            "require 'ws/ConnectionException.php'; "
            "$client = new WebSocket\\Client($argv[1], array('timeout'=>3)); "
            "$client->send($argv[2]); "
            "if ($argv[3] === '1') { do { $result = json_decode($client->receive(), true); } "
            "while (!isset($result['id']) || $result['id'] !== 1); echo json_encode($result); }"
        )
        result = subprocess.run([
            str(TAGUI / 'php/php.exe'), '-r', php, endpoint,
            json.dumps(dict(id=1, method=method, params=params or {})), '1' if wait else '0',
        ], cwd=TAGUI, capture_output=True, timeout=5, creationflags=HIDDEN)
        if result.returncode:
            raise RuntimeError('Chrome no respondió al comando ' + method)
        if not wait:
            return {}
        response = json.loads(result.stdout)
        if 'error' in response:
            raise RuntimeError('Chrome rechazó el comando ' + method)
        return response.get('result', {})

    def prepare_flow(self, url, destination, action, query, initial, provider, inspect_action='search', expected_page=None, order_by=None):
        """Selecciona un .tag permanente y entrega sus datos por JSON."""
        providers = read_providers(json.loads((ROOT.parent / 'config.json').read_text(encoding='utf-8')))
        shop = next((p for p in providers if p['id'] == provider), None)
        if not shop or not allowed_url(shop, url):
            raise ValueError('La consulta debe pertenecer al proveedor elegido.')
        if action not in ('search', 'detail', 'next', 'load_more', 'inspect'):
            raise ValueError('Acción TagUI desconocida.')
        if inspect_action not in ('search', 'detail', 'next', 'load_more'):
            raise ValueError('Tipo de inspección TagUI desconocido.')
        if order_by is not None and (order_by != 'price_asc' or shop['adapter'] != 'mercadolibre' or
                (inspect_action if action == 'inspect' else action) == 'detail'):
            raise ValueError('El orden por precio requiere un listado de MercadoLibre.')
        if expected_page is not None and (shop['adapter'] != 'mercadolibre' or
                (inspect_action if action == 'inspect' else action) != 'next' or
                type(expected_page) is not int or expected_page < 2):
            raise ValueError('La página dinámica requiere un avance de MercadoLibre.')
        flow = self.work / 'flujos' / (shop['id'] + '.tag')
        if not flow.is_file():
            raise FileNotFoundError('Falta el flujo fuente: ' + str(flow))
        job = dict(provider=shop['id'], host=urlparse(shop['base']).netloc,
                   allowed_hosts=allowed_hosts(shop), home=shop.get('home', shop['base'].rstrip('/') + '/'),
                   adapter=shop['adapter'], access_env=shop.get('access_env'),
                   url=url, query=query or '', action=action, inspect_action=inspect_action, initial=initial,
                   human=self.human, destination=destination.as_posix())
        if expected_page is not None:
            job['expected_page'] = expected_page
        if order_by is not None:
            job['order_by'] = order_by
        contents = json.dumps(job, ensure_ascii=False, indent=2)
        (self.work / 'trabajo.json').write_text(contents, encoding='utf-8')
        self.job = job
        self.provider = shop
        return flow

    def collect(self, url, destination, timeout=120, action='search', query='', initial=False, provider=None, inspect_action='search', expected_page=None, order_by=None):
        self.diagnostic = dict(provider=provider, action=action, query=self.redact(query or ''))
        self.logged_error = None
        self.save_diagnostic('preparando_consulta')
        try:
            result = self._collect(url, destination, timeout, action, query, initial, provider, inspect_action, expected_page, order_by)
            if result.get('status') in ('ok', 'no_encontrado') and capture_matches(result, url, self.provider, expected_page, order_by=order_by):
                self.recovery_attempted = False
            self.save_diagnostic('consulta_completada')
            return result
        except BaseException as error:
            self.save_error_logs(error)
            raise

    def _collect(self, url, destination, timeout, action, query, initial, provider, inspect_action, expected_page, order_by=None):
        inspecting = action == 'inspect'
        if not inspecting:
            self.check_cancelled()
        if self.chrome is not None and self.chrome.poll() is not None:
            raise BrowserDisconnected('El Chrome del comparador se cerró antes de la consulta. Revisá error.log.')
        if self.attach_existing and (self.external_bridge is None or self.external_bridge.poll() is not None):
            raise BrowserDisconnected(self.external_error())
        destination = Path(destination).resolve()
        # Una consulta fallida no puede reutilizar ni borrar la evidencia anterior.
        capture_file = self.work / 'captura.json'
        capture_file.unlink(missing_ok=True)
        flow = self.prepare_flow(url, capture_file, action, query, initial, provider, inspect_action, expected_page, order_by)
        env = dict(
            os.environ,
            tagui_web_browser='headless' if self.headless else 'chrome',
            tagui_data_set='1', tagui_turbo_mode='false', tagui_quiet_mode='true',
            PYTHONUTF8='1', COMPARASUPLE_BROWSER_PID=str(self.browser_pid),
            COMPARASUPLE_ACTIVATE_BROWSER='0' if inspecting or self.human_started else '1',
        )
        if self.browser_hwnd is not None:
            env['COMPARASUPLE_BROWSER_HWND'] = str(self.browser_hwnd)
        access_env = self.job.get('access_env')
        if access_env and access_env in self.credentials:
            env[access_env] = self.credentials[access_env]
        parsed = subprocess.run(
            [str(TAGUI / 'php/php.exe'), '-q', 'tagui_parse.php', str(flow)],
            cwd=self.work, env=env, capture_output=True, timeout=20, creationflags=HIDDEN,
        )
        if parsed.returncode or b'ERROR' in parsed.stdout:
            raise RuntimeError(
                'Error compilando flujo TagUI: ' + parsed.stdout.decode(errors='replace')[:500]
            )

        # Las consultas con clave no registran las teclas enviadas.
        bridge_log = open(os.devnull if access_env else self.work / 'bridge.log', 'ab')
        self.handles.append(bridge_log)
        local_processes = []
        try:
            if self.attach_existing:
                self.browser_command('ComparaSuple.startCapture')
            commands = [] if self.attach_existing else [[str(TAGUI / 'php/php.exe'), '-q', 'tagui_chrome.php', self.ws]]
            if self.human and not inspecting:
                commands.append([sys.executable, '-u', 'tagui_py/tagui_py.py'])
            for command in commands:
                process = subprocess.Popen(
                    command, cwd=self.work, env=env, stdout=bridge_log,
                    stderr=bridge_log, creationflags=HIDDEN,
                )
                local_processes.append(process)
                self.processes.append(process)
            bridge = self.external_bridge if self.attach_existing else local_processes[0]
            self.save_diagnostic('iniciando_puente')
            deadline = time.monotonic() + 5
            while time.monotonic() < deadline:
                self.check_connection(bridge, checking_cancel=not inspecting)
                out = self.work / 'tagui_chrome.out'
                if out.exists() and out.read_text().strip() == '[0] START':
                    break
                time.sleep(.1)
            else:
                raise RuntimeError('El puente TagUI no inició en 5 segundos.')

            cp = TAGUI / 'casperjs'
            args = [
                str(TAGUI / 'phantomjs/bin/phantomjs.exe'), str(cp / 'bin/bootstrap.js'),
                '--casper-path=' + str(cp), '--cli', str(flow) + '.js',
            ]
            with open(self.work / 'tagui.log', 'ab+') as log:
                start = log.tell()
                runner = subprocess.Popen(
                    args, cwd=self.work, env=env, stdout=log, stderr=log,
                    creationflags=HIDDEN,
                )
                try:
                    deadline = time.monotonic() + timeout
                    while runner.poll() is None:
                        self.save_diagnostic('ejecutando_flujo', periodic=True)
                        self.check_connection(bridge, checking_cancel=not inspecting)
                        if time.monotonic() > deadline:
                            raise RuntimeError('TagUI excedió el tiempo máximo de consulta.')
                        time.sleep(.25)
                finally:
                    stop_process(runner)
                if not inspecting:
                    self.check_cancelled()
                log.flush()
                log.seek(start)
                output = log.read()

            if runner.returncode or b'ERROR -' in output:
                raise RuntimeError('TagUI falló: ' + output.decode(errors='replace')[-600:])
            if not capture_file.is_file():
                raise RuntimeError('TagUI no produjo datos: ' + output.decode(errors='replace')[-600:])
            data = normalize_capture(json.loads(capture_file.read_text(encoding='utf-8')))
            data['request'] = dict(provider=provider, query=query or '', action=action, expected_url=url)
            if expected_page is not None:
                data['request']['expected_page'] = expected_page
            if order_by is not None:
                data['request']['order_by'] = order_by
            if not inspecting:
                self.human_started = True
            if not inspecting and not capture_matches(data, url, self.provider, expected_page, order_by=order_by) and data['status'] != 'bloqueado':
                data.update(status='error_url', cards=[], reason='La navegación no llegó a la URL solicitada')
            atomic_json(destination, data)
            return data
        finally:
            for process in reversed(local_processes):
                stop_process(process)
                self.processes.remove(process)
            bridge_log.close()
            self.handles.remove(bridge_log)
            self.trim_bridge_log()

    def resume_human(self):
        """La confirmación del usuario autoriza recuperar foco en la próxima acción."""
        self.human_started = False
        (self.work / 'human_cancelled.txt').unlink(missing_ok=True)

    def begin_run(self, run_dir):
        """Una orden nueva del menú reutiliza el permiso y delimita sus registros."""
        if not self.attach_existing:
            raise ValueError('Solo Chrome actual comparte conexión entre corridas.')
        self.run_dir = Path(run_dir).resolve()
        self.diagnostic = {}
        self.logged_error = None
        self.log_offsets = {name: (self.work / name).stat().st_size
                            for name in ('chrome.log', 'chrome-actual.log', 'tagui.log', 'human_actions.jsonl')
                            if (self.work / name).is_file()}
        self.recovery_attempted = False
        self.preserve_window = False
        if self.attached_target is None:
            self._open_run_window()
        else:
            self.browser_command('Target.getTargetInfo', {'targetId': self.attached_target})
        self.resume_human()

    def finish_run(self, completed):
        """Cierra la ventana propia al completar la captura y conserva el permiso."""
        self.preserve_window = not completed
        if not self.attach_existing or not completed:
            return
        try:
            self._close_run_window()
        except Exception as error:
            self.save_error_logs(error)
            print('La captura terminó, pero no se pudo cerrar su ventana. Revisá error.log.', flush=True)

    def _close_run_window(self):
        if self.attached_target is not None:
            result = self.browser_command('Target.closeTarget', {'targetId': self.attached_target})
            if result.get('success') is not True:
                raise RuntimeError('Chrome no confirmó el cierre de la ventana del comparador.')
            self.attached_target = None
            self.browser_hwnd = None

    def check_connection(self, bridge, checking_cancel=True):
        if checking_cancel:
            self.check_cancelled()
        if self.chrome is not None and self.chrome.poll() is not None:
            raise BrowserDisconnected('El Chrome del comparador se cerró. Revisá error.log.')
        if bridge is None or bridge.poll() is not None:
            if self.attach_existing:
                raise BrowserDisconnected(self.external_error())
            raise BrowserDisconnected('El puente TagUI terminó antes de completar la consulta. Revisá error.log.')

    def check_cancelled(self):
        signal = self.work / 'human_cancelled.txt'
        if self.human and signal.exists():
            reason = signal.read_text(encoding='utf-8').strip() or 'Modo humano detenido'
            # KeyboardInterrupt evita reintentos y conserva los bloques finally.
            raise KeyboardInterrupt(reason)

    def trim_bridge_log(self):
        # Conservar la cola limita el tamaño del registro de CDP.
        path = self.work / 'bridge.log'
        try:
            if path.exists() and path.stat().st_size > 8 * 1024 * 1024:
                with open(path, 'rb+') as log:
                    log.seek(-4 * 1024 * 1024, 2)
                    tail = log.read()
                    log.seek(0)
                    log.write(tail)
                    log.truncate()
        except OSError:
            pass

    def close(self):
        errors = []
        keep_chrome = (self.chrome is not None and self.chrome.poll() is None and
                       self.preserve_window and not self.headless)
        if self.attach_existing and self.external_bridge is not None and self.external_bridge.poll() is None:
            try:
                if not self.preserve_window:
                    self._close_run_window()
            except Exception as error:
                errors.append('Ventana propia: ' + type(error).__name__)
            try:
                self.browser_command('ComparaSuple.disconnect')
                self.external_bridge.wait(timeout=5)
            except Exception as error:
                errors.append('Desconexión: ' + type(error).__name__)
        for process in reversed(self.processes):
            if process is not self.chrome:
                try:
                    stop_process(process)
                except Exception as error:
                    errors.append('Puente: ' + type(error).__name__)
        # El cierre normal permite que Chrome guarde la sesión antes de liberar el perfil.
        if self.chrome is not None and self.chrome.poll() is None and not keep_chrome:
            if self.browser_ws:
                try:
                    self.browser_command('Browser.close', wait=False)
                    self.chrome.wait(timeout=10)
                except Exception as error:
                    errors.append('Browser.close: ' + type(error).__name__)
            if self.chrome.poll() is None and os.name == 'nt':
                # Se termina sólo el árbol del PID propio, nunca por nombre de programa.
                try:
                    subprocess.run(['taskkill', '/PID', str(self.chrome.pid), '/T', '/F'],
                                   capture_output=True, timeout=10, creationflags=HIDDEN)
                except Exception as error:
                    errors.append('Árbol Chrome: ' + type(error).__name__)
            try:
                stop_process(self.chrome)
            except Exception as error:
                errors.append('Proceso Chrome: ' + type(error).__name__)
        chrome_alive = self.chrome is not None and self.chrome.poll() is None
        if errors or (chrome_alive and not keep_chrome):
            try:
                with (self.run_dir / 'error.log').open('a', encoding='utf-8') as log:
                    log.write('\nCierre: ' + '; '.join(errors) + '\n')
            except OSError:
                pass
        if chrome_alive and not keep_chrome:
            # Conservar la exclusión y el directorio permite reintentar close().
            raise RuntimeError('No se pudo cerrar Chrome; su perfil continúa bloqueado por esta ejecución.')
        for handle in self.handles:
            try:
                handle.close()
            except OSError:
                pass
        self.handles.clear()
        if self.release_bridge_guard is not None:
            self.release_bridge_guard()
            self.release_bridge_guard = None
        self.processes = [process for process in self.processes if process.poll() is None]
        if self.profile_guard is not None and not keep_chrome:
            self.profile_guard.__exit__(None, None, None)
            self.profile_guard = None
        # Solo se elimina el directorio temporal creado por este motor.
        if (not keep_chrome and self.work.name.startswith('comparasuple-') and
                self.work.resolve().parent == Path(tempfile.gettempdir()).resolve()):
            shutil.rmtree(self.work, ignore_errors=True)
        if keep_chrome:
            print('Se conserva Chrome visible y su perfil para revisar el fallo. El avance está guardado.', flush=True)

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, *exc):
        if exc[0] is not None:
            self.save_error_logs(exc[1])
        try:
            self.close()
        except Exception:
            if exc[0] is None:
                raise

    def log_tail(self, name):
        path = self.work / name
        if not path.is_file():
            return ''
        with path.open('rb') as source:
            source.seek(max(self.log_offsets.get(name, 0), path.stat().st_size - 12000))
            text = source.read().decode('utf-8', errors='replace')
        return self.redact(text)

    def redact(self, text):
        for secret in self.credentials.values():
            if secret:
                text = text.replace(str(secret), '[clave omitida]')
        return text

    def save_diagnostic(self, phase, periodic=False):
        """Guarda el último paso aunque se cierre la consola."""
        if periodic and time.monotonic() - self.diagnostic_at < 1:
            return
        self.diagnostic_at = time.monotonic()
        self.diagnostic.update(phase=phase, updated_at=now())
        try:
            events = self.log_tail('human_actions.jsonl').splitlines()
            self.diagnostic.pop('last_human_action', None)
            if events:
                try:
                    event = json.loads(events[-1])
                    self.diagnostic['last_human_action'] = {key: event[key] for key in ('time', 'action') if key in event}
                except (ValueError, TypeError):
                    pass  # El puente puede estar terminando de escribir esta línea.
            atomic_json(self.run_dir / 'diagnostico.json', self.diagnostic)
        except (OSError, ValueError):
            pass  # El diagnóstico nunca reemplaza el resultado de la consulta.

    def save_error_logs(self, error=None):
        """Conserva el error y sus últimas acciones."""
        if error is not None and self.logged_error is error:
            return
        if error is not None:
            if self.attach_existing or not self.headless:
                self.preserve_window = True
            self.diagnostic['error'] = self.redact(f'{type(error).__name__}: {error}')
        self.save_diagnostic('detenido' if isinstance(error, KeyboardInterrupt) else 'error')
        try:
            with (self.run_dir / 'error.log').open('a', encoding='utf-8') as log:
                log.write('\n' + self.redact(json.dumps(self.diagnostic, ensure_ascii=False)) + '\n')
                for name in ('chrome.log', 'chrome-actual.log', 'chrome-actual-status.json', 'tagui.log',
                             'human_actions.jsonl', 'background_actions.jsonl', 'human_cancelled.txt'):
                    text = self.log_tail(name)
                    if text:
                        log.write('\n' + name + '\n' + text)
            self.logged_error = error
            if isinstance(error, KeyboardInterrupt):
                print('DIAGNÓSTICO: ' + str(self.run_dir / 'error.log'), flush=True)
        except OSError:
            pass  # Un fallo al guardar el registro no debe ocultar el error original.


class ChromeSession:
    """Conserva la conexión mientras el menú sigue abierto."""
    def __init__(self):
        self.engine = None

    def acquire(self, folder):
        try:
            # Una nueva orden permite reconectar; nunca se hace durante una consulta.
            if self.engine is not None and (self.engine.external_bridge is None or
                                           self.engine.external_bridge.poll() is not None):
                self.close()
            if self.engine is None:
                engine = Engine(folder, human=True, attach_existing=True)
                engine.start()
                self.engine = engine
            else:
                self.engine.begin_run(folder)
                print('Chrome actual: se reutiliza la conexión autorizada.', flush=True)
            return self.engine
        except BaseException as error:
            if self.engine is not None:
                self.engine.save_error_logs(error)
                self.close()
            raise

    def close(self):
        if self.engine is not None:
            engine, self.engine = self.engine, None
            engine.close()
