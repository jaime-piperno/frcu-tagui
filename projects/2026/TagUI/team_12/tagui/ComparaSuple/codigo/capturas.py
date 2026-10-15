"""Contrato de salida de los robots: un JSON independiente por proveedor."""
import hashlib
import json
import math
from datetime import datetime, timezone
import os
from pathlib import Path, PurePosixPath, PureWindowsPath
import tempfile


METADATA_FIELDS = ('run_id', 'created_at', 'input_sha256', 'mode', 'products',
                   'providers', 'selected_providers')
CAPTURE_ACTIONS = ('search', 'next', 'load_more', 'detail', 'inspect')
BLOCK_TYPES = ('captcha', 'login_requerido', 'acceso_denegado')


def validate_intervention(data):
    """El punto de reanudación guarda sólo datos de navegación, nunca la sesión."""
    if 'block_type' in data and data['block_type'] not in BLOCK_TYPES:
        raise ValueError('Tipo de bloqueo desconocido.')
    if 'reason' in data and not isinstance(data['reason'], str):
        raise ValueError('El motivo de la captura debe ser texto.')
    if 'checkpoint' in data:
        checkpoint = data['checkpoint']
        if not isinstance(checkpoint, dict) or set(checkpoint) - {'expected_page', 'order_by'} != {'url', 'query', 'action', 'initial'}:
            raise ValueError('checkpoint requiere url, query, action e initial.')
        if any(not isinstance(checkpoint[key], str) for key in ('url', 'query', 'action')):
            raise ValueError('El punto de reanudación requiere texto de navegación.')
        if not checkpoint['url'] or checkpoint['action'] not in CAPTURE_ACTIONS or type(checkpoint['initial']) is not bool:
            raise ValueError('Punto de reanudación inválido.')
        if 'expected_page' in checkpoint and (checkpoint['action'] != 'next' or
                type(checkpoint['expected_page']) is not int or checkpoint['expected_page'] < 2):
            raise ValueError('Página de reanudación inválida.')
        if 'order_by' in checkpoint and checkpoint['order_by'] != 'price_asc':
            raise ValueError('Orden de reanudación inválido.')


def normalize_capture(data):
    """Valida stock y precios totales en ARS."""
    if not isinstance(data, dict) or not isinstance(data.get('status'), str):
        raise ValueError('La evidencia requiere un objeto con status.')
    status = data['status']
    if status not in ('ok', 'no_encontrado', 'bloqueado', 'busqueda_incompleta') and not status.startswith('error'):
        raise ValueError('Estado de evidencia desconocido: ' + status)
    validate_intervention(data)
    if not isinstance(data.get('url'), str) or not isinstance(data.get('cards'), list):
        raise ValueError('La evidencia requiere url y cards.')
    if any(not isinstance(card, dict) or not isinstance(card.get('title'), str) or
           not isinstance(card.get('url'), str) for card in data['cards']):
        raise ValueError('Tarjeta de producto inválida.')
    if type(data.get('capture_version')) is not int or data['capture_version'] != 1:
        raise ValueError('capture_version desconocida; el parser debe entregar el contrato común.')
    cards = []
    for card in data['cards']:
        if not card['title'].strip() or not card['url'].strip():
            raise ValueError('Cada producto requiere título y URL.')
        variants = card.get('variants', [])
        if not isinstance(variants, list):
            raise ValueError('variants debe ser una lista.')
        items = []
        for item in variants or [card]:
            if not isinstance(item, dict) or not isinstance(item.get('title'), str) or not item['title'].strip():
                raise ValueError('Cada variante requiere su título completo.')
            if 'available' not in item or (item['available'] is not None and type(item['available']) is not bool):
                raise ValueError('available debe ser true, false o null.')
            if not isinstance(item.get('prices'), list):
                raise ValueError('prices debe ser una lista de precios totales.')
            for key in ('variant_id', 'sku'):
                if key in item and not isinstance(item[key], str):
                    raise ValueError(key + ' debe ser texto.')
            prices = []
            for price in item['prices']:
                if not isinstance(price, dict):
                    raise ValueError('Precio inválido.')
                amount = price.get('amount')
                if type(amount) not in (int, float) or not math.isfinite(amount) or amount <= 0:
                    raise ValueError('El importe debe ser un número finito positivo.')
                if price.get('currency') != 'ARS':
                    raise ValueError('La comparación requiere precios totales en ARS.')
                if not isinstance(price.get('method'), str) or not price['method'].strip():
                    raise ValueError('El precio requiere una forma de pago.')
                prices.append(dict(price))
            items.append(dict(item, variant_id=item.get('variant_id', ''), sku=item.get('sku', ''), prices=prices))
        cards.append(dict(card, variants=items) if variants else dict(items[0], variants=[]))
    if data.get('next') is not None and not isinstance(data['next'], str):
        raise ValueError('next debe ser una URL o null.')
    if 'load_more' in data and type(data['load_more']) is not bool:
        raise ValueError('load_more debe ser booleano.')
    for key in ('page_number', 'next_page'):
        if data.get(key) is not None and (type(data[key]) is not int or data[key] < 1):
            raise ValueError(key + ' debe ser un entero positivo o null.')
    if data.get('next_page') is not None and (data.get('page_number') is None or
            data['next_page'] != data['page_number'] + 1 or data.get('next') is not None):
        raise ValueError('El siguiente dinámico requiere la página actual y un avance de uno.')
    if 'request' in data:
        request = data['request']
        if not isinstance(request, dict) or any(not isinstance(request.get(key), str) for key in
                                                ('query', 'action', 'expected_url', 'provider')):
            raise ValueError('request requiere query, action, expected_url y provider.')
        if request['action'] not in CAPTURE_ACTIONS or not request['provider'] or not request['expected_url']:
            raise ValueError('Solicitud de captura inválida.')
        if 'order_by' in request and (request['order_by'] != 'price_asc' or request['action'] == 'detail'):
            raise ValueError('Orden solicitado inválido.')
        if 'expected_page' in request and (request['action'] not in ('next', 'inspect') or
                type(request['expected_page']) is not int or request['expected_page'] < 2):
            raise ValueError('Página solicitada inválida.')
    if data.get('order_by') not in (None, 'price_asc'):
        raise ValueError('Orden de resultados inválido.')
    return dict(data, cards=cards)


def now():
    return datetime.now(timezone.utc).isoformat()


def atomic_json(path, data):
    """Publica el JSON completo; una interrupción conserva la versión anterior."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=path.parent,
                                         prefix=path.name + '.', suffix='.tmp', delete=False) as handle:
            temporary = Path(handle.name)
            json.dump(data, handle, ensure_ascii=False, indent=2, allow_nan=False)
            handle.flush()
            os.fsync(handle.fileno())
        temporary.replace(path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def evidence_path(folder, reference):
    """Acepta separadores de ambos sistemas, siempre dentro de la corrida."""
    if not isinstance(reference, str) or not reference or '\x00' in reference:
        raise ValueError('Referencia de evidencia inválida.')
    relative = PurePosixPath(reference.replace('\\', '/'))
    if relative.is_absolute() or PureWindowsPath(reference).drive or '..' in relative.parts:
        raise ValueError('La evidencia debe estar dentro de la corrida: ' + reference)
    folder = Path(folder).resolve()
    path = (folder / relative).resolve()
    if folder not in path.parents or path.suffix.lower() != '.json' or not path.is_file():
        raise ValueError('No existe una evidencia JSON válida dentro de la corrida: ' + reference)
    return path


def _hash_evidence(folder, observation):
    """Fija la evidencia al guardarla por primera vez y comprueba su integridad."""
    previous = {key.replace('\\', '/'): value for key, value in observation.get('evidence_sha256', {}).items()}
    hashes = {}
    for ref in observation.get('evidence', []):
        path = evidence_path(folder, ref)
        ref = ref.replace('\\', '/')
        if ref in hashes:
            raise ValueError('Hay evidencias duplicadas en un registro: ' + ref)
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if ref in previous and previous[ref] != digest:
            raise ValueError('Cambió el contenido de la evidencia: ' + ref)
        hashes[ref] = digest
    observation['evidence_sha256'] = hashes
    observation['evidence'] = list(hashes)
    return hashes


def save_provider(payload, folder, provider_id):
    folder = Path(folder)
    records = []
    for result in payload['results']:
        if result['provider'] != provider_id:
            continue
        validate_intervention(result)
        hashes = _hash_evidence(folder, result)
        # La captura aporta observaciones; el procesador decide el precio final.
        status = result['status']
        if status in ('ok', 'sin_stock', 'sin_precio', 'no_encontrado', 'revisar'):
            status = 'captured'
        record = {key: result[key] for key in
                  ('product_id', 'query', 'checked_at', 'evidence', 'reason', 'block_type', 'checkpoint',
                   'search_limited', 'pages_checked') if key in result}
        record['status'] = status
        if result.get('url'):
            record['candidate_url'] = result['url']
        elif result.get('candidate_url'):
            record['candidate_url'] = result['candidate_url']
        record['evidence_sha256'] = hashes
        records.append(record)
    complete = len(records) == len(payload['products']) and all(
        r['status'] in ('captured', 'marca_no_encontrada') for r in records)
    checks = {}
    for key, check in payload.get('brand_checks', {}).items():
        if key.startswith(provider_id + '|'):
            validate_intervention(check)
            _hash_evidence(folder, check)
            checks[key] = check
    complete = complete and all(check['status'] in ('ok', 'marca_no_encontrada') for check in checks.values())
    document = {key: payload[key] for key in METADATA_FIELDS}
    version = payload.get('schema_version', 3)
    if type(version) is not int or version != 3:
        raise ValueError('Sólo se admiten capturas con schema_version 3.')
    document.update(schema_version=version, provider=provider_id,
                    status='complete' if complete else 'in_progress',
                    captured_at=now(), records=records, brand_checks=checks)
    destination = folder / 'proveedores' / (provider_id + '.json')
    destination.parent.mkdir(exist_ok=True)
    atomic_json(destination, document)
