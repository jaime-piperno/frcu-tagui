"""Valida las capturas y recalcula la comparación desde las evidencias guardadas."""
import hashlib
import json
from pathlib import Path
import re

from matching import select, query, compact_query, brand_query, candidates_by_price, money, validate_offer
from capturas import METADATA_FIELDS, evidence_path, normalize_capture, validate_intervention
from proveedores import same_url, capture_matches


def _read_json(path):
    try:
        data = json.loads(path.read_text(encoding='utf-8-sig'))
    except (OSError, ValueError) as error:
        raise ValueError(f'No se puede leer el JSON {path.name}: {error}') from error
    if not isinstance(data, dict):
        raise ValueError(f'{path.name} debe contener un objeto JSON.')
    return data


def _index(items, label):
    if not isinstance(items, list) or not items:
        raise ValueError(f'La corrida requiere {label}.')
    result = {}
    for item in items:
        if not isinstance(item, dict) or not isinstance(item.get('id'), str) or not item['id']:
            raise ValueError(f'ID inválido en {label}.')
        if item['id'] in result:
            raise ValueError(f'ID duplicado en {label}: {item["id"]}')
        result[item['id']] = item
    return result


def _technical(status):
    return status.startswith('error') or status in ('bloqueado', 'busqueda_incompleta')


def _evidence(folder, record, provider, settings):
    references = record.get('evidence', [])
    if not isinstance(references, list) or any(not isinstance(ref, str) for ref in references):
        raise ValueError('evidence debe ser una lista de rutas.')
    if len({ref.replace('\\', '/') for ref in references}) != len(references):
        raise ValueError('Hay evidencias duplicadas en un registro.')
    hashes = record.get('evidence_sha256', {})
    if not isinstance(hashes, dict) or set(hashes) != set(references):
        raise ValueError('evidence_sha256 debe incluir exactamente las evidencias del registro.')
    artifacts = []
    for reference in references:
        path = evidence_path(folder, reference)
        expected = hashes[reference]
        if not isinstance(expected, str) or not re.fullmatch(r'[a-fA-F0-9]{64}', expected):
            raise ValueError('Hash de evidencia inválido: ' + reference)
        if hashlib.sha256(path.read_bytes()).hexdigest() != expected.lower():
            raise ValueError('Cambió el contenido de la evidencia: ' + reference)
        data = normalize_capture(_read_json(path))
        request = data.get('request')
        if request is None:
            raise ValueError('La captura requiere request: ' + reference)
        if request['provider'] != provider:
            raise ValueError('La evidencia pertenece a otro proveedor: ' + reference)
        if not capture_matches(data, request['expected_url'], settings, request.get('expected_page'), request.get('order_by')) and not _technical(data['status']):
            data['status'] = 'error_url'
        artifacts.append((reference, data))
    return artifacts


def _source(folder, path, data, payload, products, providers):
    provider = data.get('provider')
    if type(data.get('schema_version')) is not int or data['schema_version'] != 3:
        raise ValueError('Sólo se admiten capturas con schema_version 3: ' + path.name)
    if not isinstance(provider, str) or provider not in providers or path.stem != provider:
        raise ValueError('Proveedor inválido en ' + path.name)
    if any(data.get(key) != payload[key] for key in METADATA_FIELDS):
        raise ValueError('Las tiendas tienen metadatos de corrida distintos: ' + path.name)
    if provider not in payload['selected_providers']:
        raise ValueError('Hay un archivo de una tienda no seleccionada: ' + path.name)
    if data.get('status') not in ('in_progress', 'complete') or not isinstance(data.get('records'), list):
        raise ValueError('Estado o registros inválidos en ' + path.name)
    if not isinstance(data.get('captured_at'), str) or not data['captured_at']:
        raise ValueError('La captura requiere captured_at: ' + path.name)
    records = {}
    for record in data['records']:
        if not isinstance(record, dict) or not isinstance(record.get('product_id'), str) or record['product_id'] not in products:
            raise ValueError('Producto desconocido en ' + path.name)
        product_id = record['product_id']
        if product_id in records:
            raise ValueError('Producto duplicado en ' + path.name + ': ' + product_id)
        if record.get('provider', provider) != provider:
            raise ValueError('El registro pertenece a otro proveedor: ' + path.name)
        status = record.get('status')
        if not isinstance(status, str) or not (status in ('captured', 'pendiente', 'marca_no_encontrada', 'omitido_sin_sesion') or _technical(status)):
            raise ValueError('Estado de captura inválido en ' + path.name)
        if 'query' in record and not isinstance(record['query'], str):
            raise ValueError('La consulta del producto debe ser texto.')
        if 'candidate_url' in record and not isinstance(record['candidate_url'], str):
            raise ValueError('La URL candidata debe ser texto.')
        validate_intervention(record)
        if 'search_limited' in record or 'pages_checked' in record:
            if (providers[provider].get('adapter') != 'mercadolibre' or record.get('search_limited') is not True or
                    type(record.get('pages_checked')) is not int or record['pages_checked'] < 1):
                raise ValueError('Alcance de búsqueda inválido en ' + path.name)
        artifacts = _evidence(folder, record, provider, providers[provider])
        if status == 'captured' and not artifacts:
            raise ValueError('Una captura terminada requiere evidencia: ' + product_id)
        records[product_id] = (record, artifacts)
    if data['status'] == 'complete' and set(records) != set(products):
        raise ValueError('La tienda está completa pero faltan productos: ' + path.name)
    if data['status'] == 'complete' and any(record['status'] == 'pendiente' for record, _ in records.values()):
        raise ValueError('La tienda está completa pero tiene productos pendientes: ' + path.name)
    # Una captura bloqueada debe quedar pendiente aunque figure como completa.
    complete = len(records) == len(products) and all(
        record['status'] in ('captured', 'marca_no_encontrada') and
        not any(_technical(artifact['status']) for _, artifact in artifacts)
        for record, artifacts in records.values())
    checks = data.get('brand_checks', {})
    if not isinstance(checks, dict):
        raise ValueError('brand_checks debe ser un objeto en ' + path.name)
    for key, check in checks.items():
        if not key.startswith(provider + '|') or not isinstance(check, dict) or not isinstance(check.get('status'), str):
            raise ValueError('Comprobación de marca inválida en ' + path.name)
        if check['status'] not in ('ok', 'marca_no_encontrada') and not _technical(check['status']):
            raise ValueError('Estado de marca inválido en ' + path.name)
        validate_intervention(check)
        artifacts = _evidence(folder, check, provider, providers[provider])
        technical = next((artifact for _, artifact in artifacts if _technical(artifact['status'])), None)
        if technical:
            checks[key] = dict(check, status=technical['status'], **{
                key: technical[key] for key in ('block_type', 'reason') if key in technical})
        if _technical(checks[key]['status']):
            complete = False
    return dict(status='complete' if complete and data['status'] == 'complete' else 'in_progress',
                records=records, brand_checks=checks)


def _result(product, provider, record, artifacts, settings):
    row = dict(product_id=product['id'], provider=provider, status=record['status'],
               price=None, method='', evidence=record.get('evidence', []),
               checked_at=record.get('checked_at'))
    for key in ('query', 'candidate_url', 'evidence_sha256', 'block_type', 'reason', 'checkpoint',
                'search_limited', 'pages_checked'):
        if key in record:
            row[key] = record[key]
    if record['status'] != 'captured':
        row.setdefault('reason', 'La marca no apareció en las búsquedas del sitio' if record['status'] == 'marca_no_encontrada'
                       else 'Captura pendiente' if record['status'] == 'pendiente'
                       else 'MercadoLibre omitido: no se confirmó una sesión iniciada.' if record['status'] == 'omitido_sin_sesion'
                       else 'Consulta incompleta; revisar evidencia')
        return row

    # Usar sólo la ficha evita mezclar precios de distintas presentaciones.
    details = [(ref, data) for ref, data in artifacts if data['request']['action'] == 'detail']
    if details and settings.get('adapter') == 'mercadolibre' and record.get('candidate_url'):
        # Las fichas descartadas se conservan para diagnóstico, no para calcular el precio elegido.
        details = [(ref, data) for ref, data in details
                   if same_url(data['request']['expected_url'], record['candidate_url'], settings)]
        if not details:
            return dict(row, status='error_url', reason='Falta la evidencia de la publicación elegida')
    selected = details or artifacts
    queries = {record.get('query')}
    equivalents = {query(product), compact_query(product), brand_query(product)}
    if record.get('query') in equivalents:
        queries.update(equivalents)  # Conserva los intentos equivalentes en cualquiera de los órdenes.
    cards, status = [], 'ok'
    for reference, data in selected:
        status = data['status']
        if _technical(status):
            break
        if status not in ('ok', 'no_encontrado'):
            raise ValueError('Estado de evidencia desconocido: ' + reference)
        if details and record.get('candidate_url') and not same_url(data['url'], record['candidate_url'], settings):
            status = 'error_url'
            break
        if not details and record.get('query'):
            if data['request']['query'] not in queries:
                status = 'error_url'
                break
        cards.extend(data['cards'])
        if data.get('captured_at'):
            row['checked_at'] = data['captured_at']
    if _technical(status):
        row.update(status=status, reason=data.get('reason') or row.get('reason') or
                   'Consulta incompleta; revisar evidencia')
        if data.get('block_type'):
            row['block_type'] = data['block_type']
        return row
    row.update(select(product, cards, status))
    if details and settings.get('adapter') == 'mercadolibre':
        listings = []
        for _, data in artifacts:
            if data['request']['action'] == 'detail':
                continue
            found = [card for card in data['cards']
                     if same_url(card['url'], record.get('candidate_url', ''), settings)]
            if found:
                listings = found  # Al volver del primer intento, el precio puede haber cambiado.
        candidates = candidates_by_price(product, listings)
        listed = min((money(p.get('amount')) for candidate in candidates for p in candidate['prices']
                      if p.get('currency') == 'ARS' and money(p.get('amount'))), default=None)
        row = validate_offer(product, row, listed)
    if record.get('search_limited'):
        if row['status'] == 'ok' and details:
            row['reason'] = ('Publicación verificada; búsqueda limitada a ' + str(record['pages_checked']) +
                             ' páginas. No garantiza el menor precio de todo MercadoLibre.')
        else:
            row.update(status='busqueda_incompleta', price=None, method='',
                       reason='Búsqueda limitada sin una ficha con precio y stock confirmados.')
    if row['status'] == 'ok' and not details:
        row.update(status='revisar', price=None, method='', needs_detail=True,
                   reason='Falta confirmar la ficha del producto')
    return row


def process_run(folder, write_outputs=True):
    """Reconstruye la comparación desde las tiendas y valida antes de escribir."""
    folder = Path(folder).resolve()
    files = sorted((folder / 'proveedores').glob('*.json'))
    if not files:
        raise ValueError('No hay JSON de tiendas en ' + str(folder / 'proveedores'))
    documents = [(path, _read_json(path)) for path in files]
    payload = {key: documents[0][1].get(key) for key in METADATA_FIELDS}
    payload['schema_version'] = documents[0][1].get('schema_version')
    if not isinstance(payload['run_id'], str) or not payload['run_id']:
        raise ValueError('La captura requiere run_id.')
    if not isinstance(payload['created_at'], str) or not payload['created_at']:
        raise ValueError('La captura requiere created_at.')
    if not isinstance(payload.get('mode'), str) or not payload['mode']:
        raise ValueError('La corrida requiere su modo de captura.')
    if not isinstance(payload.get('input_sha256'), str) or not re.fullmatch(r'[a-fA-F0-9]{64}', payload['input_sha256']):
        raise ValueError('La corrida requiere el SHA256 del catálogo.')
    products = _index(payload.get('products'), 'productos')
    providers = _index(payload.get('providers'), 'proveedores')
    for product in products.values():
        if any(not isinstance(product.get(key), str) or not product[key].strip() for key in ('name', 'brand')):
            raise ValueError('Cada producto requiere nombre y marca.')
    if any(not re.fullmatch(r'[A-Za-z0-9_-]+', provider) for provider in providers):
        raise ValueError('ID de proveedor inválido para su archivo JSON.')
    selected = payload['selected_providers']
    if not isinstance(selected, list) or not selected or any(not isinstance(item, str) for item in selected) or len(set(selected)) != len(selected) or set(selected) - set(providers):
        raise ValueError('Selección de proveedores inválida.')
    sources = {path.stem: _source(folder, path, data, payload, products, providers)
               for path, data in documents}
    payload['results'], payload['brand_checks'], payload['source_status'] = [], {}, {}
    for provider in selected:
        source = sources.get(provider, dict(status='missing', records={}, brand_checks={}))
        payload['source_status'][provider] = source['status']
        payload['brand_checks'].update(source['brand_checks'])
        for product in products.values():
            record, artifacts = source['records'].get(product['id'], (
                dict(status='pendiente', evidence=[]), []))
            payload['results'].append(_result(product, provider, record, artifacts, providers[provider]))
    if write_outputs:
        from workbook_portable import export_workbook
        export_workbook(payload, folder / 'Comparación de precios.xlsx')
    return payload
