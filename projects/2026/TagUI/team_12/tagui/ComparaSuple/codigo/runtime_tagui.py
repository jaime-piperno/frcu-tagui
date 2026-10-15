"""Prepara una copia privada de TagUI para cada ejecución."""
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
FLOWS = ROOT.parent / 'flujos'
# ComparaSuple junto a la carpeta src de TagUI, como en C:\tagui.
BESIDE_PROJECT = ROOT.parent.parent / 'src'
DLL_NOT_FOUND = 0xC0000135
TROUBLESHOOTING = 'https://tagui.readthedocs.io/en/latest/setup_troubleshooting.html'


def windows_desktop():
    """El Escritorio puede estar redirigido a OneDrive o tener un nombre traducido."""
    if os.name != 'nt':
        return None
    import ctypes
    buffer = ctypes.create_unicode_buffer(260)
    if ctypes.windll.shell32.SHGetFolderPathW(None, 0x0010, None, 0, buffer) != 0:
        return None
    return Path(buffer.value)


def tagui_locations():
    """Carpetas donde se busca TagUI, en orden de prioridad."""
    configured = os.environ.get('COMPARASUPLE_TAGUI', '').strip().strip('"')
    if configured:
        # Una ruta explícita nunca se reemplaza por otra instalación.
        return [Path(configured).expanduser().absolute()]
    places = [BESIDE_PROJECT]
    command = shutil.which('tagui')
    if command:
        places.append(Path(command).parent)
    places.append(Path(os.environ.get('SystemDrive', 'C:') + os.sep) / 'tagui')
    # La guía oficial de TagUI propone el Escritorio si no se puede usar C:\.
    desktop = windows_desktop()
    if desktop:
        places.append(desktop / 'tagui')
    places += [Path.home() / 'Desktop' / 'tagui', Path.home() / 'tagui']
    if os.environ.get('APPDATA'):
        places.append(Path(os.environ['APPDATA']) / 'tagui')  # Ubicación de TagUI for Python.
    return list(dict.fromkeys(places))


def tagui_source(place):
    """Acepta la carpeta de TagUI o directamente su carpeta src."""
    for folder in (place, place / 'src'):
        if (folder / 'tagui_parse.php').is_file():
            return folder
    return None


TAGUI = next((found for found in map(tagui_source, tagui_locations()) if found), BESIDE_PROJECT)


def run_tool(executable):
    """Sin el aviso modal de Windows, una DLL faltante devuelve un código reconocible."""
    previous = None
    if os.name == 'nt':
        import ctypes
        kernel = ctypes.WinDLL('kernel32')
        # El proceso hijo hereda este modo: SEM_FAILCRITICALERRORS | SEM_NOGPFAULTERRORBOX | SEM_NOOPENFILEERRORBOX.
        previous = kernel.SetErrorMode(0x0001 | 0x0002 | 0x8000)
    try:
        return subprocess.run([str(executable), '--version'], capture_output=True,
                              timeout=10, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    finally:
        if previous is not None:
            kernel.SetErrorMode(previous)


def check_installation(human=False):
    """Comprueba TagUI antes de abrir Chrome o consultar una tienda."""
    if tagui_source(TAGUI) is None:
        raise RuntimeError(
            'No se encontró TagUI para Windows. Se buscó en: '
            + '; '.join(str(place) for place in tagui_locations())
            + '. Instalá TagUI en C:\\tagui o en el Escritorio, o indicá su carpeta en la variable COMPARASUPLE_TAGUI.')
    required = (
        'tagui_parse.php', 'tagui_config.txt', 'tagui_header.js', 'tagui_footer.js',
        'tagui_chrome.php', 'tagui.sikuli/tagui.py',
        'php/php.exe', 'phantomjs/bin/phantomjs.exe', 'casperjs/bin/bootstrap.js',
        'casperjs/modules/casper.js', 'ws/Base.php', 'ws/Client.php', 'ws/Exception.php',
        'ws/BadOpcodeException.php', 'ws/BadUriException.php', 'ws/ConnectionException.php',
    )
    if human:
        required += ('tagui_py/tagui_py.py',)
    missing = [name for name in required if not (TAGUI / name).is_file()]
    if missing:
        raise RuntimeError(
            'La instalación de TagUI en ' + str(TAGUI) + ' está incompleta. Falta: ' + ', '.join(missing)
            + '. Descargá el paquete TagUI_Windows.zip completo; el código fuente de GitHub no incluye PHP ni PhantomJS.')
    versions = {'python': sys.version.split()[0], 'tagui_path': str(TAGUI)}
    for tool, name in (('php', 'php/php.exe'), ('phantomjs', 'phantomjs/bin/phantomjs.exe')):
        executable = TAGUI / name
        try:
            result = run_tool(executable)
        except subprocess.TimeoutExpired as error:
            raise RuntimeError(str(executable) + ' no respondió en 10 segundos. Si Windows avisó que falta '
                               'MSVCR110.dll, instalá Visual C++ (vcredist_x86.exe) según ' + TROUBLESHOOTING) from error
        except OSError as error:
            raise RuntimeError('No se pudo ejecutar ' + str(executable)
                               + '. Revisá la instalación y los permisos del archivo: ' + str(error)) from error
        if result.returncode in (DLL_NOT_FOUND, DLL_NOT_FOUND - 2 ** 32):
            raise RuntimeError('Windows no encontró una DLL que necesita ' + str(executable)
                               + ' (normalmente MSVCR110.dll). Instalá Visual C++ (vcredist_x86.exe) según '
                               + TROUBLESHOOTING + ' y repetí la operación.')
        if result.returncode:
            raise RuntimeError('No se pudo ejecutar ' + str(executable)
                               + f' (código {result.returncode}). Revisá la instalación de TagUI para Windows.')
        output = result.stdout.decode('utf-8', errors='replace').strip()
        if not output:
            raise RuntimeError('No se pudo comprobar la versión de ' + str(executable) + '.')
        versions[tool] = output.splitlines()[0]
    return versions


def patch(source, old, new, skipped, label):
    """Aplica una mejora del puente; otra versión de TagUI sólo pierde esa mejora."""
    if old in source:
        return source.replace(old, new)
    if new not in source:
        skipped.append(label)
    return source


def prepare_runtime(work, human):
    for name in ('tagui_parse.php', 'tagui_config.txt', 'tagui_header.js',
                 'tagui_footer.js', 'tagui_chrome.php'):
        shutil.copy2(TAGUI / name, work / name)
    skipped = []

    # Los flujos usan las palabras de TagUI en inglés; no modificar la instalación.
    config = work / 'tagui_config.txt'
    declaration = r'''(?m)^([ \t]*)var[ \t]+tagui_language[ \t]*=[ \t]*(['"])[^'"\r\n]*\2[ \t]*;([ \t]*(?://[^\r\n]*)?)$'''
    settings = re.sub(declaration, r"\1var tagui_language = 'english';\3", config.read_text(encoding='utf-8'))
    if "var tagui_language = 'english';" not in settings:
        # Sin esta línea, TagUI intentaría traducir los flujos con archivos que no se copian.
        settings = settings.rstrip('\n') + "\nvar tagui_language = 'english';\n"
    config.write_text(settings, encoding='utf-8')

    # TagUI ajusta este archivo al compilar, aunque el flujo no use Sikuli.
    (work / 'tagui.sikuli').mkdir(exist_ok=True)
    shutil.copy2(TAGUI / 'tagui.sikuli/tagui.py', work / 'tagui.sikuli/tagui.py')

    # Esperar una respuesta completa del mismo ID; reintentar sólo su lectura.
    header = work / 'tagui_header.js'
    source = header.read_text(encoding='utf-8')
    helper = ("function comparasuple_response_complete(message) {"
              "try {JSON.parse(message.substring(message.indexOf('] ')+2));return true;}"
              "catch(e) {return false;}}\n")
    helper += """function comparasuple_read_bridge(path) {
    var deadline = Date.now() + 1000;
    while (true) {
        try { return require('fs').read(path).trim(); }
        catch (error) {
            if (Date.now() >= deadline)
                throw new Error('No se pudo leer la respuesta del puente durante 1 segundo: ' + path);
            sleep(10);
        }
    }
}
"""
    if 'function comparasuple_response_complete' not in source:
        source = helper + source
    source = patch(source, "while (chrome_result.indexOf('['+chrome_id.toString()+'] ') == -1);",
                   "while (chrome_result.indexOf('['+chrome_id.toString()+'] ') !== 0 || "
                   "!comparasuple_response_complete(chrome_result));", skipped, 'respuesta completa de Chrome')
    for path in ("'tagui_chrome.out'", "'tagui_py'+ds+'tagui_py.out'", "'tagui_py'+ds+'tagui_py.txt'"):
        source = patch(source, 'fs.read(' + path + ').trim()', 'comparasuple_read_bridge(' + path + ')',
                       skipped, 'lectura de ' + path.replace("'+ds+'", '/').strip("'"))
    source = patch(source, "while (py_step_result.indexOf('['+py_count.toString()+'] ') == -1);",
                   "while (py_step_result !== '['+py_count.toString()+'] SUCCESS' && "
                   "py_step_result !== '['+py_count.toString()+'] ERROR');", skipped, 'respuesta de Python')
    if human:
        # El sondeo rápido del puente mantiene fluida la escritura visible.
        for variable in ('py_step_result', 'chrome_result'):
            polling = 'do {sleep(100); ' + variable + ' ='
            source = patch(source, polling, polling.replace('100', '10'), skipped, 'sondeo de ' + variable)
        bridge = work / 'tagui_chrome.php'
        # La expresión evita que el compilador lo restablezca a 100 ms.
        bridge.write_text(patch(bridge.read_text(encoding='utf-8'), '$scan_period = 100000;',
                                '$scan_period = 10 * 1000;', skipped, 'sondeo de Chrome'), encoding='utf-8')
    header.write_text(source, encoding='utf-8')
    shutil.copytree(TAGUI / 'ws', work / 'ws', dirs_exist_ok=True)
    shutil.copytree(FLOWS, work / 'flujos', dirs_exist_ok=True)
    (work / 'parsers').mkdir(exist_ok=True)
    for path in (ROOT / 'parsers').glob('*.js'):
        shutil.copy2(path, work / 'parsers' / path.name)

    # El parser encuentra pasos py aun cuando la rama visible no se ejecuta.
    (work / 'tagui_py').mkdir(exist_ok=True)
    if human:
        # El puente siempre se copia: sin él, cada paso py esperaría hasta el tiempo máximo.
        python_bridge = (TAGUI / 'tagui_py/tagui_py.py').read_text(encoding='utf-8')
        (work / 'tagui_py/tagui_py.py').write_text(
            patch(python_bridge, 'scan_period = 0.1\n', 'scan_period = 0.01\n', skipped, 'sondeo de Python'),
            encoding='utf-8')
        shutil.copy2(ROOT / 'human_input.py', work / 'human_input.py')
    if skipped:
        print('Aviso: la versión de TagUI en ' + str(TAGUI) + ' difiere de la probada (v6.110). '
              'Se continúa sin estas mejoras del puente: ' + ', '.join(skipped) + '.', flush=True)
