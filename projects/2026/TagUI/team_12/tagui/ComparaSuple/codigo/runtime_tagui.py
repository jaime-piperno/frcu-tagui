"""Prepara una copia privada de TagUI para cada ejecución."""
from pathlib import Path
import re
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
TAGUI = ROOT.parent.parent / 'src'
FLOWS = ROOT.parent / 'flujos'


def check_installation(human=False):
    """Comprueba TagUI antes de abrir Chrome o consultar una tienda."""
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
            'La instalacion de TagUI esta incompleta. Se espera su carpeta src en '
            + str(TAGUI) + '. Falta: ' + ', '.join(missing)
            + '. Copia Grupo12 y el archivo de inicio junto a la carpeta src de TagUI para Windows.')
    versions = {'python': sys.version.split()[0]}
    for tool, name in (('php', 'php/php.exe'), ('phantomjs', 'phantomjs/bin/phantomjs.exe')):
        executable = TAGUI / name
        try:
            result = subprocess.run([str(executable), '--version'], capture_output=True,
                                    timeout=10, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        except (OSError, subprocess.TimeoutExpired) as error:
            raise RuntimeError('No se pudo ejecutar ' + str(executable)
                               + '. Revisa la instalacion y los permisos del archivo: ' + str(error)) from error
        if result.returncode:
            raise RuntimeError('No se pudo ejecutar ' + str(executable)
                               + f' (codigo {result.returncode}). Revisa la instalacion de TagUI para Windows.')
        output = result.stdout.decode('utf-8', errors='replace').strip()
        if not output:
            raise RuntimeError('No se pudo comprobar la version de ' + str(executable) + '.')
        versions[tool] = output.splitlines()[0]
    return versions


def prepare_runtime(work, human):
    for name in ('tagui_parse.php', 'tagui_config.txt', 'tagui_header.js',
                 'tagui_footer.js', 'tagui_chrome.php'):
        shutil.copy2(TAGUI / name, work / name)
    # Los flujos usan las palabras de TagUI en inglés; no modificar la instalación.
    config = work / 'tagui_config.txt'
    declaration = r'''(?m)^([ \t]*)var[ \t]+tagui_language[ \t]*=[ \t]*(['"])[^'"\r\n]*\2[ \t]*;([ \t]*(?://[^\r\n]*)?)$'''
    settings, count = re.subn(declaration, r"\1var tagui_language = 'english';\3", config.read_text(encoding='utf-8'))
    if count != 1:
        raise RuntimeError('tagui_config.txt debe declarar una sola vez var tagui_language. Revisá la configuración de TagUI.')
    config.write_text(settings, encoding='utf-8')
    # TagUI ajusta este archivo al compilar, aunque el flujo no use Sikuli.
    (work / 'tagui.sikuli').mkdir(exist_ok=True)
    shutil.copy2(TAGUI / 'tagui.sikuli/tagui.py', work / 'tagui.sikuli/tagui.py')

    # Esperar una respuesta completa del mismo ID; reintentar sólo su lectura.
    header = work / 'tagui_header.js'
    source = header.read_text(encoding='utf-8')
    old = "while (chrome_result.indexOf('['+chrome_id.toString()+'] ') == -1);"
    new = ("while (chrome_result.indexOf('['+chrome_id.toString()+'] ') !== 0 || "
           "!grupo12_response_complete(chrome_result));")
    if source.count(old) != 1:
        raise RuntimeError('Cambió el protocolo del puente Chrome de TagUI.')
    helper = ("function grupo12_response_complete(message) {"
              "try {JSON.parse(message.substring(message.indexOf('] ')+2));return true;}"
              "catch(e) {return false;}}\n")
    helper += """function grupo12_read_bridge(path) {
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
    for path, count in (("'tagui_chrome.out'", 2),
                        ("'tagui_py'+ds+'tagui_py.out'", 2),
                        ("'tagui_py'+ds+'tagui_py.txt'", 1)):
        reading = 'fs.read(' + path + ').trim()'
        if source.count(reading) != count:
            raise RuntimeError('Cambió la lectura del puente TagUI: ' + path)
        source = source.replace(reading, 'grupo12_read_bridge(' + path + ')')
    python_wait = "while (py_step_result.indexOf('['+py_count.toString()+'] ') == -1);"
    if source.count(python_wait) != 1:
        raise RuntimeError('Cambió la respuesta del puente Python de TagUI.')
    source = source.replace(python_wait,
        "while (py_step_result !== '['+py_count.toString()+'] SUCCESS' && "
        "py_step_result !== '['+py_count.toString()+'] ERROR');")
    if human:
        # El sondeo rápido del puente mantiene fluida la escritura visible.
        for variable in ('py_step_result', 'chrome_result'):
            polling = "do {sleep(100); " + variable + " ="
            if source.count(polling) != 1:
                raise RuntimeError('Cambió el sondeo del puente TagUI: ' + variable)
            source = source.replace(polling, polling.replace('100', '10'))
        bridge = work / 'tagui_chrome.php'
        bridge_source = bridge.read_text(encoding='utf-8')
        if bridge_source.count('$scan_period = 100000;') != 1:
            raise RuntimeError('Cambió el sondeo del puente Chrome de TagUI.')
        # La expresión evita que el compilador lo restablezca a 100 ms.
        bridge.write_text(bridge_source.replace('$scan_period = 100000;',
                                                '$scan_period = 10 * 1000;'), encoding='utf-8')
    header.write_text(helper + source.replace(old, new), encoding='utf-8')
    shutil.copytree(TAGUI / 'ws', work / 'ws', dirs_exist_ok=True)
    shutil.copytree(FLOWS, work / 'flujos', dirs_exist_ok=True)
    (work / 'parsers').mkdir(exist_ok=True)
    for path in (ROOT / 'parsers').glob('*.js'):
        shutil.copy2(path, work / 'parsers' / path.name)
    # El parser encuentra pasos py aun cuando la rama visible no se ejecuta.
    (work / 'tagui_py').mkdir(exist_ok=True)
    if human:
        python_bridge = (TAGUI / 'tagui_py/tagui_py.py').read_text(encoding='utf-8')
        if python_bridge.count('scan_period = 0.1\n') != 1:
            raise RuntimeError('Cambió el sondeo del puente Python de TagUI.')
        (work / 'tagui_py/tagui_py.py').write_text(
            python_bridge.replace('scan_period = 0.1\n', 'scan_period = 0.01\n'), encoding='utf-8')
        shutil.copy2(ROOT / 'human_input.py', work / 'human_input.py')
