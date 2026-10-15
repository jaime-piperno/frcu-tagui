"""Lee el catálogo, consulta las tiendas con TagUI y prepara la comparación."""
import argparse
from collections import Counter
from contextlib import contextmanager, ExitStack
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import sys
import uuid

from engine import BrowserDisconnected, ChromeSession, Engine, session_profile
from iniciar_sesion import ensure_session, session_state
from matching import money, norm
from capturas import now, save_provider
from proveedores import read_providers, provider_settings, read_credentials, provider_snapshot
from busqueda import Navigation, ProviderSuspended, check_brand, search_product

ROOT = Path(__file__).resolve().parents[1]


def read_catalog(path):
    """Una fila activa representa un producto con una presentación concreta."""
    import openpyxl
    book = openpyxl.load_workbook(path, read_only=True, data_only=True)
    sheet = book['Productos'] if 'Productos' in book.sheetnames else book.active
    rows = list(sheet.values)
    book.close()
    header = next((i for i, row in enumerate(rows) if any(norm(v) == 'producto' for v in row)), None)
    if header is None:
        raise ValueError('El Excel debe incluir la columna PRODUCTO.')
    names = [norm(value) for value in rows[header] if norm(value)]
    if len(names) != len(set(names)):
        raise ValueError('El Excel tiene encabezados repetidos.')
    columns = {norm(value): i for i, value in enumerate(rows[header]) if norm(value)}

    def value(row, *names):
        return next((row[columns[n]] for n in names if n in columns and columns[n] < len(row)), None)

    products = []
    for number, row in enumerate(rows[header + 1:], header + 2):
        name = str(value(row, 'producto') or '').strip()
        brand = str(value(row, 'marca') or '').strip()
        if not name or norm(value(row, 'activo')) in ('no', 'false', '0'):
            continue
        if not brand:
            raise ValueError(f'Fila {number}: MARCA es obligatoria para verificar cada tienda.')
        product = dict(id=str(value(row, 'id') or '').strip() or f'P{number:04d}', name=name,
                       brand=brand, category=str(value(row, 'categoria') or ''),
                       cost=money(value(row, 'costo')),
                       sale_price=money(value(row, 'precio de venta', 'precio de venta recomendado', 'precio')),
                       weight_g=money(value(row, 'peso g')), pack=money(value(row, 'unidades por pack')),
                       source_row=number)
        for field, column in [('sku', 'sku'), ('line', 'linea'), ('flavor', 'sabor'), ('presentation', 'presentacion')]:
            product[field] = str(value(row, column) or '').strip()
        products.append(product)
    if not products:
        raise ValueError('No hay productos activos en el Excel.')
    if len({p['id'] for p in products}) != len(products):
        raise ValueError('Hay IDs duplicados en el catálogo.')
    return products


def needs_capture(result):
    # Reanudar sólo lo pendiente, fallido o sin ficha confirmada.
    return result is None or result.get('needs_detail', False) or result['status'].startswith('error') or result['status'] in (
        'pendiente', 'bloqueado', 'busqueda_incompleta', 'omitido_sin_sesion')


@contextmanager
def run_lock(folder):
    """Evita escrituras simultáneas. Windows libera el bloqueo al salir del proceso."""
    import msvcrt
    with (folder / '.running.lock').open('a+b') as handle:
        handle.seek(0)
        try:
            msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
        except OSError as error:
            raise RuntimeError('Ya hay una ejecución activa en esta carpeta.') from error
        try:
            yield
        finally:
            handle.seek(0)
            msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)


def save_blocked(payload, folder, provider, product, data, path, request):
    """Guarda el trabajo pendiente antes de ceder el control al usuario."""
    result = dict(product_id=product['id'], provider=provider['id'], status='bloqueado',
                  price=None, reason=data.get('reason') or 'La tienda requiere intervención',
                  block_type=data.get('block_type', 'acceso_denegado'),
                  checked_at=now(), evidence=[path.relative_to(folder).as_posix()],
                  checkpoint=request)
    payload['results'] = [r for r in payload['results']
                          if (r['provider'], r['product_id']) != (provider['id'], product['id'])]
    payload['results'].append(result)
    save_provider(payload, folder, provider['id'])


def mark_pending(payload, folder, provider, products, status, reason, keep_blocked=False):
    """Registra por qué quedó pendiente cada producto, sin borrar capturas terminadas."""
    existing = {r['product_id']: r for r in payload['results'] if r['provider'] == provider['id']}
    for product in products:
        old = existing.get(product['id'])
        if not needs_capture(old) or (keep_blocked and old and old['status'] == 'bloqueado'):
            continue
        if old:
            payload['results'].remove(old)
        payload['results'].append(dict(product_id=product['id'], provider=provider['id'], status=status,
                                       price=None, evidence=[], checked_at=now(), reason=reason))
    save_provider(payload, folder, provider['id'])


def save_provider_error(payload, folder, provider, products, error):
    """Un fallo de una tienda no borra precios confirmados ni detiene las otras."""
    mark_pending(payload, folder, provider, products, 'error_consulta',
                 f'No se completó la tienda: {type(error).__name__}: {error}', keep_blocked=True)


@contextmanager
def current_chrome(folder, connection=None):
    """El menú conserva su permiso; una ejecución suelta cierra su conexión."""
    if connection is not None:
        browser = connection.acquire(folder)
        try:
            yield browser
        except BaseException as error:
            browser.save_error_logs(error)
            raise
    else:
        with Engine(folder, human=True, attach_existing=True) as browser:
            yield browser


def menu(connected=False):
    print('\nComparaSuple - Comparador de suplementos\n')
    if connected:
        print('Chrome habitual conectado. Se desconecta al salir.\n')
    print('1. Demo visible: un producto en las tiendas configuradas')
    print('2. Catálogo completo visible')
    print('3. Catálogo completo en segundo plano (MercadoLibre: perfil dedicado)')
    print('4. Generar Excel desde una captura guardada')
    print('5. Reanudar una captura interrumpida')
    print('0. Salir')
    choice = input('Opción: ').strip()
    if choice == '4':
        return ['--procesar', input('Carpeta de la captura: ').strip().strip('"')]
    if choice == '5':
        folder = input('Carpeta de la captura: ').strip().strip('"')
        mode = input('Modo: Enter anterior; V visible; S segundo plano: ').strip().lower()
        if mode not in ('', 'v', 's'):
            raise ValueError('Modo no válido.')
        return ['--reanudar', folder] + ({'v': ['--visible'], 's': ['--segundo-plano']}.get(mode, []))
    if choice not in ('0', '1', '2', '3'):
        raise ValueError('Opción no válida.')
    return {'0': None, '1': ['--demo'], '2': ['--visible'], '3': ['--segundo-plano']}[choice]


def main():
    try:
        # Sólo comprueba la instalación: el Excel se genera al final y debe fallar antes de abrir Chrome.
        from openpyxl.workbook.properties import CalcProperties  # noqa: F401
    except ImportError as error:
        raise RuntimeError('Falta instalar o actualizar openpyxl en el Python que ejecuta el programa. Ejecutá:\n'
                           f'"{sys.executable}" -m pip install -r "{ROOT / "requirements.txt"}"') from error
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--menu', action='store_true', help='Abrir el menú')
    parser.add_argument('--demo', action='store_true', help='Producto N001 en las tiendas configuradas')
    parser.add_argument('--excel', type=Path, default=ROOT / 'entrada/Productos.xlsx')
    parser.add_argument('--producto', action='append', default=[], help='ID a consultar; se puede repetir')
    parser.add_argument('--proveedor', action='append', default=[], help='Tienda a consultar; se puede repetir')
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument('--visible', action='store_true', help='Una ventana maximizada con mouse real; MercadoLibre al final')
    modes.add_argument('--segundo-plano', action='store_true', help='Dejar libre el escritorio')
    parser.add_argument('--iniciar-sesion', action='store_true', help='Comprueba o inicia sesión en MercadoLibre con Chrome habitual')
    parser.add_argument('--chrome-actual', action='store_true',
                        help='Usar Chrome habitual; lo abre si hace falta (requiere habilitar y aprobar depuración)')
    parser.add_argument('--reanudar', type=Path, help='Carpeta de una captura interrumpida')
    parser.add_argument('--solo-capturar', action='store_true', help='Guardar JSON sin generar Excel')
    parser.add_argument('--espera-intervencion', type=int, default=300,
                        help='Segundos para resolver CAPTCHA/login visible; 0 guarda y omite la tienda')
    parser.add_argument('--procesar', type=Path, help='Generar Excel sin consultar las tiendas')
    args = parser.parse_args()

    if not args.menu:
        return run(args, parser)

    connection = ChromeSession()
    print('Las tiendas comparten una ventana; MercadoLibre se procesa al final.\n'
          'En modo visible con MercadoLibre se usa tu Chrome habitual. El permiso dura mientras este menú siga conectado.')
    try:
        while True:
            try:
                selection = menu(connected=connection.engine is not None)
                if selection is None:
                    return
                run(parser.parse_args(selection), parser, connection)
            except (ValueError, OSError, RuntimeError) as error:
                print('No se pudo completar la operación: ' + str(error), flush=True)
    finally:
        connection.close()


def run(args, parser, connection=None):

    if args.espera_intervencion < 0:
        parser.error('--espera-intervencion no puede ser negativo.')
    if (args.chrome_actual or args.iniciar_sesion) and args.segundo_plano:
        parser.error('--chrome-actual y --iniciar-sesion requieren modo visible.')

    if args.iniciar_sesion:
        # Los registros de sesión quedan fuera del proyecto y del perfil personal.
        folder = session_profile().parent.parent / 'sesion'
        folder.mkdir(parents=True, exist_ok=True)
        with current_chrome(folder, connection) as browser:
            print('Sesión disponible.' if ensure_session(args.espera_intervencion, browser=browser)
                  else 'MercadoLibre omitido: sin sesión confirmada.')
        return

    from procesar import process_run
    if args.procesar:
        process_run(args.procesar)
        print('RESULTADO: ' + str(args.procesar.resolve() / 'Comparación de precios.xlsx'))
        return
    if os.name != 'nt':
        parser.error('La navegación de esta versión requiere Windows. --procesar sí funciona en Linux.')
    if args.reanudar and (args.demo or args.producto or args.proveedor):
        parser.error('Al reanudar se usan los productos y tiendas guardados.')
    config = json.loads((ROOT / 'config.json').read_text(encoding='utf-8'))
    providers = read_providers(config)
    ids = {p['id'] for p in providers}
    if set(args.proveedor) - ids:
        parser.error('Hay proveedores desconocidos.')
    if type(config.get('max_pages')) is not int or config['max_pages'] < 1:
        raise ValueError('max_pages debe ser un entero positivo.')
    products = read_catalog(args.excel)
    wanted = ['N001'] if args.demo else args.producto
    if set(wanted) - {p['id'] for p in products}:
        parser.error('Hay IDs de producto desconocidos.')
    if wanted:
        products = [p for p in products if p['id'] in wanted]
    human = args.chrome_actual or args.visible or (args.demo and not args.segundo_plano)
    run_id = datetime.now().strftime('%Y%m%d-%H%M%S') + '-' + uuid.uuid4().hex[:6]
    folder = args.reanudar.resolve() if args.reanudar else ROOT / 'salidas' / run_id
    if args.reanudar and not folder.is_dir():
        raise ValueError('La reanudación requiere la carpeta de la captura.')
    with ExitStack() as opened:
        if args.reanudar:
            opened.enter_context(run_lock(folder))
        payload = dict(run_id=run_id, created_at=now(),
            input_sha256=hashlib.sha256(args.excel.read_bytes()).hexdigest(),
            providers=[provider_snapshot(p) for p in providers],
            selected_providers=list(dict.fromkeys(args.proveedor)) or [p['id'] for p in providers],
            products=products, results=[], mode='humano' if human else 'segundo_plano')
        if args.reanudar:
            previous = process_run(folder, write_outputs=False)
            current = {p['id']: provider_snapshot(p) for p in providers}
            same_providers = all(
                provider_snapshot(provider_settings(p))
                == current.get(p['id']) for p in previous['providers'])
            if previous['input_sha256'] != payload['input_sha256'] or not same_providers:
                raise ValueError('La reanudación requiere el mismo catálogo y proveedores.')
            human = args.chrome_actual or args.visible or (previous['mode'] == 'humano' and not args.segundo_plano)
            # Los JSON conservan el modo original aunque se reanude en otro modo.
            payload, products = previous, previous['products']
        active_providers = [p for p in providers if p['id'] in payload['selected_providers']]
        brands = list(dict.fromkeys(norm(p['brand']) for p in products))
        ordered = sorted(products, key=lambda p: brands.index(norm(p['brand'])))
        checks = payload.setdefault('brand_checks', {})
        for key in list(checks):
            if checks[key]['status'] not in ('ok', 'marca_no_encontrada'):
                del checks[key]
        existing = {(r['provider'], r['product_id']): r for r in payload['results']}
        pending_providers = [p for p in active_providers if any(
            needs_capture(existing.get((p['id'], product['id']))) for product in ordered)]
        # Mantener el orden configurado, dejando MercadoLibre para el final.
        pending_providers.sort(key=lambda p: p['adapter'] == 'mercadolibre')
        mercado = [p for p in pending_providers if p['adapter'] == 'mercadolibre']
        secrets = read_credentials(pending_providers)
        engine = None
        # Los requisitos y permisos se resuelven antes de crear una captura.
        if pending_providers:
            startup = ROOT / 'salidas' / 'inicio'
            try:
                startup.mkdir(parents=True, exist_ok=True)
            except PermissionError as error:
                raise RuntimeError('No se puede escribir en ' + str(startup) +
                                   '. Extraé el proyecto en una carpeta donde tu usuario tenga permiso de escritura.') from error
            print('Comprobando requisitos y navegador. Las búsquedas todavía no comenzaron.', flush=True)
            try:
                if human and (mercado or args.chrome_actual):
                    engine = opened.enter_context(current_chrome(startup, connection))
                else:
                    profile = session_profile() if mercado and not human else None
                    engine = opened.enter_context(Engine(startup, not human, human=human, profile_template=profile))
            except Exception as error:
                raise RuntimeError('No se iniciaron las búsquedas. ' + str(error) +
                                   '\nDiagnóstico de inicio: ' + str(startup) +
                                   '\nCorregí el requisito indicado y elegí nuevamente la opción del menú.') from error
        if not args.reanudar:
            folder.mkdir(parents=True)
            opened.enter_context(run_lock(folder))
        print('CAPTURA: ' + str(folder), flush=True)
        (folder / 'evidencia').mkdir(exist_ok=True)
        for provider in active_providers:
            if not (folder / 'proveedores' / (provider['id'] + '.json')).exists():
                save_provider(payload, folder, provider['id'])
        if engine is not None:
            engine.run_dir = folder
            engine.credentials = dict(secrets)
        if human and pending_providers:
            print('Modo visible: dejar libres mouse y teclado. Escape o cambiar de ventana detiene el robot.', flush=True)
        for provider in pending_providers:
            active_product = None
            try:
                navigation = Navigation(engine, intervention_timeout=args.espera_intervencion)
                if provider['adapter'] == 'mercadolibre':
                    try:
                        session_ready = ensure_session(args.espera_intervencion, headless=not human, browser=engine)
                    except BrowserDisconnected as error:
                        engine.save_error_logs(error)
                        engine.recover_connection()
                        # Tras reconectar se lee la página actual sin volver a navegar.
                        session_ready = session_state(engine) == 'iniciada'
                        if not session_ready:
                            raise BrowserDisconnected('Se recuperó la conexión, pero falta confirmar la sesión en la página actual.')
                    if not session_ready:
                        # Sin sesión no se consultan productos ni se borran capturas terminadas.
                        mark_pending(payload, folder, provider, ordered, 'omitido_sin_sesion',
                                     'MercadoLibre omitido: no se confirmó una sesión iniciada.')
                        print('MercadoLibre omitido: sin sesión confirmada.', flush=True)
                        continue
                    navigation.current_provider = provider['id']  # La comprobación ya abrió la tienda.
                for product in ordered:
                    old = next((r for r in payload['results'] if (r['product_id'], r['provider']) == (product['id'], provider['id'])), None)
                    if not needs_capture(old):
                        continue
                    active_product = product
                    navigation.on_blocked = lambda data, path, request: save_blocked(
                        payload, folder, provider, product, data, path, request)
                    key = provider['id'] + '|' + norm(product['brand'])
                    try:
                        if key not in checks or checks[key]['status'] not in ('ok', 'marca_no_encontrada', 'busqueda_incompleta'):
                            checks[key] = check_brand(product, provider, navigation, folder)
                            save_provider(payload, folder, provider['id'])
                        check = checks[key]
                        if check['status'] in ('ok', 'busqueda_incompleta'):
                            result = search_product(product, provider, navigation, folder, config['max_pages'])
                        else:
                            result = dict(product_id=product['id'], provider=provider['id'], status=check['status'],
                                price=None, evidence=check['evidence'], checked_at=check['checked_at'])
                    except ProviderSuspended as error:
                        print(f"{provider['name']} suspendido: {error}. Reanudar con --reanudar y --visible.", flush=True)
                        break
                    # Reemplaza el checkpoint que pudo guardarse durante la pausa.
                    payload['results'] = [r for r in payload['results'] if
                        (r['product_id'], r['provider']) != (product['id'], provider['id'])]
                    payload['results'].append(result)
                    save_provider(payload, folder, provider['id'])
                    print(f"{provider['name']} | {product['name']} | {result['status']} | {result.get('price')}", flush=True)
                    active_product = None
            except BrowserDisconnected as error:
                engine.save_error_logs(error)
                if active_product is not None:
                    save_provider_error(payload, folder, provider, [active_product], error)
                print('Conexión no recuperada: ' + str(error) + ' Se conserva el trabajo pendiente para reanudar.', flush=True)
                break
            except Exception as error:
                print(f"{provider['name']} | Error: {error}. Se continúa con las demás tiendas.", flush=True)
                save_provider_error(payload, folder, provider, ordered, error)
        if not args.solo_capturar:
            payload = process_run(folder)
            print('RESULTADO: ' + str(folder / 'Comparación de precios.xlsx'))
        print('Estados: ' + str(dict(Counter(row['status'] for row in payload['results']))))
        if engine is not None:
            finished = {(r['provider'], r['product_id']): r for r in payload['results']}
            requested = [finished.get((p['id'], product['id'])) for p in active_providers for product in ordered]
            engine.finish_run(all(result is not None and
                                  (not needs_capture(result) or result['status'] == 'omitido_sin_sesion')
                                  for result in requested))


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt as error:
        print(f'\nEjecución detenida: {error or "cancelada por el usuario"}. Se conserva el avance.', flush=True)
        raise SystemExit(130)
    except (ValueError, OSError, RuntimeError, ImportError) as error:
        print('No se pudo completar la operación: ' + str(error), flush=True)
        raise SystemExit(1)
