"""Mouse y teclado reales, con control de ventana, foco y cancelación."""
import ctypes
from ctypes import wintypes
import json
import math
import os
import random
import subprocess
import time

CANCEL_FILE = 'human_cancelled.txt'


def cancel(reason):
    """La señal en disco detiene también al orquestador."""
    with open(CANCEL_FILE, 'w', encoding='utf-8') as handle:
        handle.write(reason)
    record('cancelled', reason=reason)
    raise RuntimeError('COMPARASUPLE_CANCELLED: ' + reason)


def check_cancelled():
    if os.path.exists(CANCEL_FILE):
        with open(CANCEL_FILE, encoding='utf-8') as handle:
            raise RuntimeError('COMPARASUPLE_CANCELLED: ' + handle.read())
    if user32.GetAsyncKeyState(0x1B) & 0x8000:
        cancel('Modo humano detenido con Escape')


def record(action, **data):
    with open('human_actions.jsonl', 'a', encoding='utf-8') as handle:
        handle.write(json.dumps(dict(time=time.time(), action=action, **data)) + '\n')


def read_json(path):
    with open(path, encoding='utf-8') as handle:
        return json.load(handle)


# Las firmas HWND evitan truncar identificadores de ventana en Windows de 64 bits.
user32 = ctypes.WinDLL('user32', use_last_error=True)
user32.GetForegroundWindow.restype = wintypes.HWND
user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
user32.GetWindowThreadProcessId.restype = wintypes.DWORD
user32.SetForegroundWindow.argtypes = [wintypes.HWND]
user32.BringWindowToTop.argtypes = [wintypes.HWND]
user32.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
user32.IsWindowVisible.argtypes = [wintypes.HWND]
user32.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
user32.IsZoomed.argtypes = [wintypes.HWND]
user32.SetWindowPos.argtypes = [
    wintypes.HWND, wintypes.HWND, ctypes.c_int, ctypes.c_int,
    ctypes.c_int, ctypes.c_int, wintypes.UINT,
]
user32.WindowFromPoint.argtypes = [wintypes.POINT]
user32.WindowFromPoint.restype = wintypes.HWND
user32.GetAncestor.argtypes = [wintypes.HWND, wintypes.UINT]
user32.GetAncestor.restype = wintypes.HWND
user32.GetWindow.argtypes = [wintypes.HWND, wintypes.UINT]
user32.GetWindow.restype = wintypes.HWND
user32.GetClassNameW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
user32.IsWindowEnabled.argtypes = [wintypes.HWND]
user32.EnumChildWindows.argtypes = [wintypes.HWND, ctypes.c_void_p, wintypes.LPARAM]
try:
    user32.SetThreadDpiAwarenessContext.argtypes = [ctypes.c_void_p]
    user32.SetThreadDpiAwarenessContext.restype = ctypes.c_void_p
    if not user32.SetThreadDpiAwarenessContext(ctypes.c_void_p(-4)):
        raise RuntimeError('Windows no permitió usar coordenadas físicas para el mouse')
except AttributeError:
    raise RuntimeError('El modo visible requiere una versión actual de Windows 10 u 11')


def window_pid(hwnd):
    pid = wintypes.DWORD()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    return pid.value


def browser_window():
    wanted = int(os.environ['COMPARASUPLE_BROWSER_PID'])
    selected = os.environ.get('COMPARASUPLE_BROWSER_HWND')
    # El motor entrega el HWND exacto; nunca elegir otra ventana del mismo Chrome.
    if not selected:
        cancel('Falta identificar la ventana propia del comparador')
    hwnd = int(selected)
    if window_pid(hwnd) != wanted or not user32.IsWindowVisible(hwnd):
        cancel('La ventana propia del comparador ya no está disponible')
    return hwnd


def owned_popup(hwnd, owner):
    """Otra ventana del mismo proceso no necesariamente pertenece al comparador."""
    visited = set()
    for _ in range(16):
        hwnd = int(user32.GetWindow(hwnd, 4) or 0)  # GW_OWNER.
        if not hwnd or hwnd in visited:
            return False
        if hwnd == owner:
            return True
        visited.add(hwnd)
    return False


def window_diagnostic(hwnd):
    name = ctypes.create_unicode_buffer(128)
    if hwnd:
        user32.GetClassNameW(hwnd, name, len(name))
    return dict(class_name=name.value, owner=int(user32.GetWindow(hwnd, 4) or 0),
                root_owner=int(user32.GetAncestor(hwnd, 3) or 0),
                visible=bool(user32.IsWindowVisible(hwnd)), enabled=bool(user32.IsWindowEnabled(hwnd)))


def check_focus():
    check_cancelled()
    hwnd = browser_window()
    foreground = user32.GetForegroundWindow()
    foreground_pid = window_pid(foreground)
    if foreground != hwnd and foreground_pid == int(os.environ['COMPARASUPLE_BROWSER_PID']) and owned_popup(foreground, hwnd):
        # Sólo cerrar un aviso reconocido que pertenece a esta ventana.
        popup = foreground
        closed = _scan_browser_notices(hwnd, popup)
        check_cancelled()
        foreground = user32.GetForegroundWindow()
        foreground_pid = window_pid(foreground)
        deadline = time.monotonic() + .4
        while (closed and foreground == popup and foreground_pid == int(os.environ['COMPARASUPLE_BROWSER_PID'])
               and owned_popup(foreground, hwnd) and time.monotonic() < deadline):
            time.sleep(.05)
            check_cancelled()
            foreground = user32.GetForegroundWindow()
            foreground_pid = window_pid(foreground)
    if foreground_pid != int(os.environ['COMPARASUPLE_BROWSER_PID']) or foreground != hwnd:
        record('focus_lost', expected=int(hwnd), foreground=int(foreground or 0),
               foreground_pid=foreground_pid, browser_pid=int(os.environ['COMPARASUPLE_BROWSER_PID']),
               expected_window=window_diagnostic(hwnd), foreground_window=window_diagnostic(foreground))
        cancel('Modo humano detenido: el navegador perdió el foco')
    if not user32.IsZoomed(hwnd):
        cancel('Modo humano detenido: el navegador no está maximizado')
    return hwnd


def click():
    user32.mouse_event(0x0002, 0, 0, 0, 0)
    try:
        time.sleep(.07)
    finally:
        user32.mouse_event(0x0004, 0, 0, 0, 0)


def focus_window():
    check_cancelled()
    # No recuperar el foco a costa de otra aplicación elegida por el usuario.
    if os.environ.get('COMPARASUPLE_ACTIVATE_BROWSER') != '1':
        check_focus()
        return
    hwnd = browser_window()
    user32.ShowWindow(hwnd, 3)
    time.sleep(.35)
    if user32.GetForegroundWindow() == hwnd:
        check_focus()
        return

    current = ctypes.windll.kernel32.GetCurrentThreadId()
    foreground_thread = user32.GetWindowThreadProcessId(user32.GetForegroundWindow(), None)
    attached = False
    try:
        if foreground_thread and foreground_thread != current:
            attached = bool(user32.AttachThreadInput(current, foreground_thread, True))
        user32.ShowWindow(hwnd, 3)
        user32.SetForegroundWindow(hwnd)
    finally:
        if attached:
            user32.AttachThreadInput(current, foreground_thread, False)
    time.sleep(.3)

    if user32.GetForegroundWindow() != hwnd:
        # Si Windows rechaza la activación, usar sólo la barra de título propia.
        try:
            if not user32.SetWindowPos(hwnd, wintypes.HWND(-1), 0, 0, 0, 0, 0x0001 | 0x0002 | 0x0040):
                raise RuntimeError('Windows no permitió poner Chrome delante')
            user32.BringWindowToTop(hwnd)
            user32.SetForegroundWindow(hwnd)
            time.sleep(.2)
            rect = wintypes.RECT()
            user32.GetWindowRect(hwnd, ctypes.byref(rect))
            x = round(rect.left + (rect.right - rect.left) * .7)
            y = rect.top + 18
            hit = user32.WindowFromPoint(wintypes.POINT(x, y))
            owner_pid = window_pid(hit)
            own_window = user32.GetAncestor(hit, 2) == hwnd
            if owner_pid != int(os.environ['COMPARASUPLE_BROWSER_PID']) or not own_window:
                record('activation_blocked', owner_pid=owner_pid,
                       browser_pid=int(os.environ['COMPARASUPLE_BROWSER_PID']), x=x, y=y,
                       rect=[rect.left, rect.top, rect.right, rect.bottom], topmost=True)
                raise RuntimeError('Otra ventana cubre la barra del navegador')
            user32.SetCursorPos(x, y)
            time.sleep(.1)
            click()
            record('activate_browser', x=x, y=y)
        finally:
            user32.SetWindowPos(hwnd, wintypes.HWND(-2), 0, 0, 0, 0, 0x0001 | 0x0002 | 0x0010)
    time.sleep(.3)
    check_focus()


NOTICE_SCRIPT = r"""
param([long]$BrowserHandle, [long]$NoticeHandle)
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName UIAutomationClient, UIAutomationTypes
$noticeLibrary = Join-Path (Get-Location) 'browser_notice_owners.dll'
if (-not (Test-Path -LiteralPath $noticeLibrary)) {
Add-Type -OutputAssembly $noticeLibrary -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
public static class ComparaSupleNoticeWindow {
    [DllImport("user32.dll")] public static extern IntPtr GetForegroundWindow();
    [DllImport("user32.dll")] public static extern bool IsZoomed(IntPtr hwnd);
    [DllImport("user32.dll")] public static extern uint GetDpiForWindow(IntPtr hwnd);
    [DllImport("user32.dll")] public static extern IntPtr GetWindow(IntPtr hwnd, uint command);
    [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr hwnd, out uint pid);
}
'@
}
Add-Type -Path $noticeLibrary
function OwnedNotice {
    if ($NoticeHandle -eq $BrowserHandle) { return $true }
    [uint32]$browserPid = 0
    [uint32]$noticePid = 0
    $null = [ComparaSupleNoticeWindow]::GetWindowThreadProcessId([IntPtr]$BrowserHandle, [ref]$browserPid)
    $null = [ComparaSupleNoticeWindow]::GetWindowThreadProcessId([IntPtr]$NoticeHandle, [ref]$noticePid)
    if (-not $browserPid -or $noticePid -ne $browserPid) { return $false }
    $owner = [IntPtr]$NoticeHandle
    for ($level = 0; $level -lt 16; $level++) {
        $owner = [ComparaSupleNoticeWindow]::GetWindow($owner, 4)
        if ($owner -eq [IntPtr]$BrowserHandle) { return $true }
        if ($owner -eq [IntPtr]::Zero) { break }
    }
    return $false
}
if (-not (OwnedNotice)) { 'unavailable'; exit }
$noticeScale = 1.0
try {
    $dpi = [ComparaSupleNoticeWindow]::GetDpiForWindow([IntPtr]$BrowserHandle)
    if ($dpi -ge 96 -and $dpi -le 384) { $noticeScale = $dpi / 96.0 }
} catch { }
$root = [System.Windows.Automation.AutomationElement]::FromHandle([IntPtr]$NoticeHandle)
$walker = [System.Windows.Automation.TreeWalker]::ControlViewWalker
function NativeControls($node, $depth = 0) {
    # No recorrer la página ni los campos donde Chrome muestra credenciales.
    if ($depth -gt 18 -or $node.Current.IsPassword -or $node.Current.ControlType -in @(
            [System.Windows.Automation.ControlType]::Document,
            [System.Windows.Automation.ControlType]::Edit,
            [System.Windows.Automation.ControlType]::ComboBox)) { return }
    $node
    $child = $walker.GetFirstChild($node)
    while ($child) {
        NativeControls $child ($depth + 1)
        $child = $walker.GetNextSibling($child)
    }
}
$patterns = @{
    automation = '^Chrome (is being controlled by automated test software|está siendo controlado por un software automatizado de pruebas)\.?$'
    default_browser = '^(Google )?Chrome (is not|isn.t) your default browser\.?$|^(Google )?Chrome no es (tu|el|su) navegador predeterminado\.?$'
    translation = '^(Google Translate|Traductor de Google|Translate this page\??|Traducir esta página\??|Translate|Traducir)$'
    password = '^(Save|Update|Remember) (this )?password( for [^?]+)?\??$|^¿?((Quieres|Deseas) )?(guardar|actualizar|recordar) (la |esta )?contraseña( (de|para) [^?]+)?\??$'
}
$closed = $false
for ($attempt = 0; $attempt -lt 3; $attempt++) {
    $dismissed = $false
    foreach ($label in @(NativeControls $root)) {
        if ($label.Current.IsOffscreen) { continue }
        $kind = @($patterns.Keys | Where-Object { $label.Current.Name -match $patterns[$_] })
        if ($kind.Count -ne 1) { continue }
        $parent = $label
        for ($level = 0; $level -lt 4 -and $parent -and
                (-not $parent.Equals($root) -or $NoticeHandle -ne $BrowserHandle); $level++) {
            $bounds = $parent.Current.BoundingRectangle
            $controls = @(NativeControls $parent)
            $buttons = @($controls | Where-Object { $_.Current.ControlType -eq [System.Windows.Automation.ControlType]::Button })
            $close = @($buttons | Where-Object { $_.Current.Name -in @('Close', 'Cerrar', 'Dismiss', 'Descartar') -and
                $_.Current.IsEnabled -and -not $_.Current.IsOffscreen })
            $permission = @($buttons | Where-Object { $_.Current.Name -match '^(Allow|Permitir|Connect|Conectar|Sign in|Iniciar sesión)$' })
            $support = switch ($kind[0]) {
                automation { @($buttons | Where-Object { $_.Current.Name -match '^(Turn off in settings|Desactivar en (la )?[Cc]onfiguración)$' }).Count -gt 0 }
                default_browser { @($buttons | Where-Object { $_.Current.Name -match '^(Set as default|Make default|Establecer como predeterminado|Establecer predeterminado|Definir como predeterminado)$' }).Count -gt 0 }
                translation { @($controls | Where-Object { $_.Current.Name -match '^(Options|More options|Opciones|Más opciones|Show original|Mostrar original|Choose [Ll]anguage [Tt]o [Tt]ranslate [Tt]o|Elegir idioma de traducción|Always translate .+|Traducir siempre .+)$' }).Count -gt 0 }
                password { @($buttons | Where-Object { $_.Current.Name -match '^(Save|Update|Save password|Update password|Guardar|Actualizar|Guardar contraseña|Actualizar contraseña)$' }).Count -gt 0 }
            }
            if ($bounds.Height -gt 0 -and $bounds.Height -le 420 * $noticeScale -and $close.Count -eq 1 -and
                    $permission.Count -eq 0 -and $support) {
                if ([ComparaSupleNoticeWindow]::GetForegroundWindow() -ne [IntPtr]$NoticeHandle -or
                        -not [ComparaSupleNoticeWindow]::IsZoomed([IntPtr]$BrowserHandle) -or -not (OwnedNotice)) {
                    'unavailable'
                    exit
                }
                $invoke = $close[0].GetCurrentPattern([System.Windows.Automation.InvokePattern]::Pattern)
                $invoke.Invoke()
                if ($NoticeHandle -ne $BrowserHandle) { 'closed'; exit }
                $dismissed = $true
                $closed = $true
                break
            }
            if ($parent.Equals($root)) { break }
            $parent = $walker.GetParent($parent)
        }
        if ($dismissed) { break }
    }
    if (-not $dismissed) { break }
}
if ($closed) { 'closed' } else { 'absent' }
"""

_notice_checked_at = None
_notice_closed_count = 0


def _scan_browser_notices(hwnd, notice_hwnd=None):
    """UIA puede cerrar un aviso propio; nunca activa ventanas ni envía teclas."""
    global _notice_checked_at, _notice_closed_count
    notice_hwnd = notice_hwnd or hwnd
    shell = os.path.join(os.environ['SystemRoot'], 'System32', 'WindowsPowerShell', 'v1.0', 'powershell.exe')
    import base64
    command = NOTICE_SCRIPT.replace('param([long]$BrowserHandle, [long]$NoticeHandle)',
        '$BrowserHandle = ' + str(int(hwnd)) + '; $NoticeHandle = ' + str(int(notice_hwnd)))
    encoded = base64.b64encode(command.encode('utf-16-le')).decode('ascii')
    started = time.monotonic()
    category, returncode = None, None
    # La primera llamada compila la DLL auxiliar; en un equipo lento puede superar los 5 s habituales.
    timeout = 5 if os.path.exists('browser_notice_owners.dll') else 30
    try:
        result = subprocess.run([shell, '-NoProfile', '-NonInteractive', '-EncodedCommand', encoded],
                                capture_output=True, timeout=timeout, creationflags=subprocess.CREATE_NO_WINDOW)
        returncode = result.returncode
        state = result.stdout.decode(errors='replace').strip() if returncode == 0 else 'unavailable'
        if returncode:
            category = 'process_error'
        elif state not in ('closed', 'absent'):
            category = 'unavailable' if state == 'unavailable' else 'unexpected_output'
            state = 'unavailable'
    except subprocess.TimeoutExpired:
        state, category = 'unavailable', 'timeout'
    except OSError:
        state, category = 'unavailable', 'launch_error'
    _notice_checked_at = time.monotonic()
    if state == 'closed':
        _notice_closed_count += 1
    record('browser_notice', state=state, category=category, returncode=returncode,
           duration_ms=round((_notice_checked_at - started) * 1000),
           scope='browser' if notice_hwnd == hwnd else 'owned_popup')
    return state == 'closed'


def dismiss_browser_notices(force=False):
    """Cierra avisos conocidos de Chrome; no cambia preferencias ni permisos."""
    if not os.environ.get('COMPARASUPLE_BROWSER_HWND'):
        return False
    before = _notice_closed_count
    hwnd = check_focus()
    if before != _notice_closed_count:
        return True
    if not force and _notice_checked_at is not None and time.monotonic() - _notice_checked_at < 4:
        return False
    closed = _scan_browser_notices(hwnd)
    check_focus()
    return closed or before != _notice_closed_count


def focus():
    focus_window()
    dismiss_browser_notices(force=True)


def move(x, y):
    hwnd = check_focus()
    rect = wintypes.RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(rect))
    if not (rect.left + 4 < x < rect.right - 4 and rect.top + 4 < y < rect.bottom - 4):
        raise RuntimeError('El elemento está fuera de la ventana')
    point = wintypes.POINT()
    user32.GetCursorPos(ctypes.byref(point))
    distance = math.hypot(x - point.x, y - point.y)
    if distance < 2:
        return
    duration = min(.45, max(.12, distance / 1700))
    steps = max(6, int(duration * 60))
    for i in range(1, steps + 1):
        check_focus()
        t = i / steps
        smooth = t * t * (3 - 2 * t)
        user32.SetCursorPos(
            round(point.x + (x - point.x) * smooth),
            round(point.y + (y - point.y) * smooth),
        )
        time.sleep(duration / steps)


def pointer_route(start, target, navigation, viewport):
    """Evita los menús del encabezado solo cuando cruzan el recorrido directo."""
    def crosses(a, b, rect):
        if rect['left'] <= a[0] <= rect['right'] and rect['top'] <= a[1] <= rect['bottom']:
            return False  # Salir del menú sobre el que ya está el puntero.
        lower, upper = 0, 1
        for index, low, high in ((0, rect['left'], rect['right']), (1, rect['top'], rect['bottom'])):
            delta = b[index] - a[index]
            if not delta:
                if a[index] < low or a[index] > high:
                    return False
                continue
            entry, leave = sorted(((low - a[index]) / delta, (high - a[index]) / delta))
            lower, upper = max(lower, entry), min(upper, leave)
            if lower > upper:
                return False
        return True

    def clear(points):
        return all(not crosses(a, b, rect) for a, b in zip([start] + points, points) for rect in navigation)

    if not navigation or clear([target]):
        return [target]
    candidates = []
    for x in [start[0], target[0]] + [edge for rect in navigation for edge in (rect['left'] - 14, rect['right'] + 14)]:
        points = [(x, start[1]), (x, target[1]), target]
        if viewport and not all(viewport['left'] <= p[0] <= viewport['right'] and
                                viewport['top'] <= p[1] <= viewport['bottom'] for p in points):
            continue
        if clear(points):
            candidates.append(points)
    if not candidates:
        return [target]  # El flujo comprueba de nuevo qué quedó bajo el puntero.
    return min(candidates, key=lambda points: sum(math.dist(a, b) for a, b in zip([start] + points, points)))


def screen_target():
    """Convierte el DOM a píxeles reales, incluido el zoom y el escalado de Windows."""
    data = read_json('human_target.json')
    if not data or not data.get('visible'):
        raise RuntimeError('No se encontró un elemento visible para hacer clic')
    hwnd = check_focus()
    metrics = data['metrics']
    scale = float(metrics['scale'])
    width, height = float(metrics['width']) * scale, float(metrics['height']) * scale
    if not all(math.isfinite(value) and value > 0 for value in (scale, width, height)):
        raise RuntimeError('Chrome devolvió medidas de pantalla inválidas')
    matches = []
    callback = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

    @callback
    def visit(child, _):
        name = ctypes.create_unicode_buffer(128)
        user32.GetClassNameW(child, name, len(name))
        if name.value == 'Chrome_RenderWidgetHostHWND' and user32.IsWindowVisible(child):
            rect = wintypes.RECT()
            if user32.GetWindowRect(child, ctypes.byref(rect)) and (
                    abs(rect.right - rect.left - width) <= max(2, scale) and
                    abs(rect.bottom - rect.top - height) <= max(2, scale)):
                matches.append((rect.left, rect.top))
        return True

    # El área web nativa evita adivinar el alto de pestañas, avisos y barras.
    user32.EnumChildWindows(hwnd, visit, 0)
    if len(matches) != 1:
        raise RuntimeError('No se pudo medir de forma única el área web de Chrome. '
                           'Cerrá paneles adicionales del navegador y reintentá.')
    left, top = matches[0]

    def rectangle(rect):
        return {key: value * scale + (left if key in ('left', 'right') else top)
                for key, value in rect.items()}

    return dict(data, x=left + data['x'] * scale, y=top + data['y'] * scale,
                viewport=rectangle(data['viewport']),
                navigation=[rectangle(rect) for rect in data.get('navigation', [])])


def move_target():
    data = screen_target()
    point = wintypes.POINT()
    user32.GetCursorPos(ctypes.byref(point))
    for x, y in pointer_route((point.x, point.y), (float(data['x']), float(data['y'])),
                              data.get('navigation', []), data.get('viewport')):
        move(x, y)
    if data.get('hover_exit'):
        time.sleep(.35)


def click_target():
    # El .tag vuelve a comprobar el DOM después del movimiento del mouse.
    data = screen_target()
    check_focus()
    click()
    record('click', x=data['x'], y=data['y'], maximized=bool(user32.IsZoomed(browser_window())))
    time.sleep(random.uniform(.08, .14))


# SendInput exige la unión completa, incluida MOUSEINPUT, para calcular el tamaño.
ULONG_PTR = ctypes.c_size_t


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ('wVk', wintypes.WORD), ('wScan', wintypes.WORD), ('dwFlags', wintypes.DWORD),
        ('time', wintypes.DWORD), ('dwExtraInfo', ULONG_PTR),
    ]


class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ('dx', wintypes.LONG), ('dy', wintypes.LONG), ('mouseData', wintypes.DWORD),
        ('dwFlags', wintypes.DWORD), ('time', wintypes.DWORD), ('dwExtraInfo', ULONG_PTR),
    ]


class INPUTUNION(ctypes.Union):
    _fields_ = [('ki', KEYBDINPUT), ('mi', MOUSEINPUT)]


class INPUT(ctypes.Structure):
    _fields_ = [('type', wintypes.DWORD), ('u', INPUTUNION)]


def key(vk=0, scan=0, flags=0):
    # Soltar una tecla sigue siendo necesario aunque el usuario haya cambiado el foco.
    if not flags & 2:
        check_focus()
    event = INPUT(type=1, u=INPUTUNION(ki=KEYBDINPUT(vk, scan, flags, 0, 0)))
    if user32.SendInput(1, ctypes.byref(event), ctypes.sizeof(event)) != 1:
        raise RuntimeError('Windows no aceptó la entrada de teclado')


def select_query():
    key(0x11)
    try:
        key(0x41)
        key(0x41, flags=2)
    finally:
        # Soltamos Ctrl incluso si cambia el foco durante Ctrl+A.
        user32.keybd_event(0x11, 0, 2, 0)


def type_character(text):
    # El .tag controla foco y cadencia, incluida la demora de los puentes.
    encoded = text.encode('utf-16-le')
    for i in range(0, len(encoded), 2):
        scan = int.from_bytes(encoded[i:i + 2], 'little')
        key(scan=scan, flags=4)
        key(scan=scan, flags=6)


def credential_character(index):
    """Lee la clave del entorno; el puente recibe solamente un índice."""
    variable = read_json('trabajo.json').get('access_env')
    secret = os.environ.get(variable, '') if isinstance(variable, str) else ''
    if not secret or type(index) is not int or not 0 <= index < len(secret):
        raise RuntimeError('No se pudo leer el carácter de acceso')
    try:
        type_character(secret[index])
    finally:
        secret = ''


def scroll(notches=3):
    check_focus()
    for _ in range(abs(notches)):
        check_focus()
        delta = (-120 if notches > 0 else 120) & 0xffffffff
        user32.mouse_event(0x0800, 0, 0, delta, 0)
        time.sleep(.15)
    record('scroll', notches=notches)


def scroll_center():
    data = screen_target()
    move(data['x'], data['y'])
    scroll(3)
