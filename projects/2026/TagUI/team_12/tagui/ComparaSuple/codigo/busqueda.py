"""Busca marcas y productos con TagUI y conserva la evidencia de cada consulta."""
import hashlib
import time
import uuid

from capturas import atomic_json, now
from engine import BrowserDisconnected
from iniciar_sesion import wait_for_user
from matching import brand_matches, brand_query, candidates_by_price, compact_query, money, norm, query, select, validate_offer
from proveedores import allowed_url, capture_matches, same_url, search_url


def brand_present(data, brand):
    return any(brand_matches(brand, card.get('title', '')) for card in data.get('cards', []))


def collect_with_retries(engine, url, destination, attempts=2, **options):
    """Un fallo transitorio se reintenta; nunca significa falta de stock."""
    for attempt in range(1, attempts + 1):
        path = destination if attempt == 1 else destination.with_name(f'{destination.stem}-reintento-{attempt}.json')
        try:
            data = engine.collect(url, path, **options)
            if data.get('status') not in ('error_extraccion', 'error_url') or attempt == attempts:
                return data, path
        except BrowserDisconnected:
            raise
        except Exception:
            if attempt == attempts:
                raise
        time.sleep(1)


class ProviderSuspended(Exception):
    """La tienda necesita intervención; las demás pueden seguir trabajando."""


def log_progress(navigation, message):
    prefix = getattr(navigation, 'progress_prefix', '')
    if prefix:
        print(f"{prefix} {message}", flush=True)
    else:
        print(message, flush=True)


class Navigation:
    """Entrega los datos al .tag de la tienda y conserva la página entre consultas."""
    def __init__(self, engine, on_blocked=None, intervention_timeout=300):
        self.engine = engine
        self.current_provider = None
        self.provider = None
        self.on_blocked = on_blocked
        self.intervention_timeout = intervention_timeout
        self.progress_prefix = getattr(engine, 'progress_prefix', '') if engine else ''

    def _capture(self, provider, url, destination, term, action, initial, retry=True, expected_page=None, order_by=None):
        options = dict(timeout=150, provider=provider['id'], query=term, action=action, initial=initial)
        page_options = {} if expected_page is None else dict(expected_page=expected_page)
        if order_by is not None:
            page_options['order_by'] = order_by
        options.update(page_options)
        # Repetir un clic de paginación tras un error podría saltar una página.
        retry = retry and expected_page is None
        try:
            data, used = collect_with_retries(self.engine, url, destination, attempts=2 if retry else 1, **options)
        except BrowserDisconnected:
            self.engine.recover_connection()
            # El clic pudo completarse antes del corte. Leer primero evita repetirlo.
            used = destination.with_name(destination.stem + '-recuperacion-' + uuid.uuid4().hex[:8] + '.json')
            for attempt in range(3):
                data = self.engine.collect(url, used, timeout=45, provider=provider['id'], query=term,
                                           action='inspect', inspect_action=action, **page_options)
                if data['status'] != 'error_extraccion':
                    break
                if attempt < 2:
                    time.sleep(1)
            if data['status'] != 'bloqueado' and not capture_matches(data, url, provider, expected_page, order_by):
                data.update(status='error_url', cards=[],
                            reason='Conexión recuperada; la página esperada no pudo confirmarse.')
            data['request'].update(action=action)
            atomic_json(used, data)
        deadline = time.monotonic() + self.intervention_timeout
        while data['status'] == 'bloqueado':
            request = dict(url=url, query=term, action=action, initial=initial)
            request.update(page_options)
            if self.on_blocked:
                self.on_blocked(data, used, request)
            reason = data.get('reason') or 'La tienda requiere intervención'
            log_progress(self, f"{provider['name']} | PAUSA: {reason}. Avance guardado.")
            if (self.engine.headless or data.get('block_type') not in ('captcha', 'login_requerido')
                    or not wait_for_user(max(0, deadline - time.monotonic()), on_skip=self.engine.resume_human)):
                raise ProviderSuspended(reason)

            # Leer la misma pestaña no envía una nueva búsqueda ni pulsa el desafío.
            resumed = destination.with_name(destination.stem + '-continuacion-' + uuid.uuid4().hex[:8] + '.json')
            try:
                data = self.engine.collect(url, resumed, timeout=45, provider=provider['id'], query=term,
                                           action='inspect', inspect_action=action, **page_options)
                used = resumed
                # Confirmar mientras carga requiere esperar, sin recargar ni hacer clic.
                for _ in range(3):
                    if data['status'] != 'error_extraccion' or not capture_matches(data, url, provider, expected_page, order_by):
                        break
                    time.sleep(1)
                    data = self.engine.collect(url, resumed, timeout=45, provider=provider['id'], query=term,
                                               action='inspect', inspect_action=action, **page_options)
                if data['status'] == 'bloqueado':
                    continue
                if not allowed_url(provider, data.get('url', '')):
                    raise ProviderSuspended('La verificación terminó fuera de la tienda; revisar el navegador.')
                if capture_matches(data, url, provider, expected_page, order_by) and data['status'] not in ('ok', 'no_encontrado'):
                    raise ProviderSuspended('La página todavía no está lista; se conserva el trabajo pendiente.')
                self.engine.resume_human()
                if not capture_matches(data, url, provider, expected_page, order_by):
                    # El desafío pudo aparecer en la portada, antes de buscar.
                    resumed = destination.with_name(destination.stem + '-retomar-' + uuid.uuid4().hex[:8] + '.json')
                    data, used = collect_with_retries(self.engine, url, resumed, attempts=1,
                                                     **dict(options, initial=False))
                else:
                    data['request'].update(action=action)
                    atomic_json(used, data)
            except (ProviderSuspended, BrowserDisconnected):
                raise
            except Exception as error:
                # Conserva la evidencia y su hash si Chrome se cierra durante la pausa.
                raise ProviderSuspended('No se pudo retomar la sesión: ' + str(error)) from error
        return data, used

    def collect(self, provider, url, destination, term, action='search', expected_page=None, order_by=None):
        initial = self.current_provider != provider['id']
        self.provider = provider
        result = self._capture(provider, url, destination, term, action, initial, expected_page=expected_page, order_by=order_by)
        self.current_provider = provider['id']
        return result

    def detail(self, url, path):
        return self._capture(self.provider, url, path, '', 'detail', False, retry=False)


def check_brand(product, provider, navigation, folder):
    """Antes de omitir una marca, prueba su nombre y una consulta de producto."""
    refs, status = [], 'marca_no_encontrada'
    incomplete = False
    key = provider['id'] + '|' + norm(product['brand'])
    stem = provider['id'] + '-marca-' + hashlib.sha256(key.encode()).hexdigest()[:12] + '-' + uuid.uuid4().hex[:8]
    log_progress(navigation, f"{provider['name']} | Comprobando marca {product['brand']}")
    terms = [product['brand'], brand_query(product)]
    if provider['adapter'] == 'mercadolibre':
        terms.reverse()  # La línea evita resultados de otros rubros con la misma palabra.
    for index, term in enumerate(dict.fromkeys(terms)):
        path = folder / 'evidencia' / (stem + ('-confirmacion' if index else '') + '.json')
        url = search_url(provider, term)
        try:
            data, used = navigation.collect(provider, url, path, term)
            refs.append(used.relative_to(folder).as_posix())
            if data['status'] not in ('ok', 'no_encontrado'):
                status = data['status']
                break
            if brand_present(data, product['brand']):
                status = 'ok'
                break
            incomplete = incomplete or bool(data.get('next') or data.get('next_page') or data.get('load_more'))
        except (ProviderSuspended, BrowserDisconnected):
            raise
        except Exception as error:
            atomic_json(path, dict(capture_version=1, status='error_consulta', url=url, error=str(error), cards=[],
                request=dict(provider=provider['id'], query=term, action='search', expected_url=url)))
            refs.append(path.relative_to(folder).as_posix())
            status = 'error_consulta'
            break
    if status == 'marca_no_encontrada' and incomplete:
        status = 'busqueda_incompleta'
    return dict(status=status, evidence=refs, checked_at=now())


def search_product(product, provider, navigation, folder, max_pages):
    full, compact = query(product), compact_query(product)
    term, alternative = (compact, full) if provider.get('query_mode') == 'compact' else (full, compact)
    result, detail_attempted = _search_query(product, provider, navigation, folder, max_pages, term)
    # La consulta más amplia puede agotar páginas; la completa aún puede encontrarlo.
    incomplete = result['status'] == 'busqueda_incompleta' and term == compact
    if (detail_attempted or norm(alternative) == norm(term) or
            result['status'] != 'no_encontrado' and not incomplete):
        return result
    log_progress(navigation, f"{provider['name']} | {product['id']} | Probar consulta equivalente: {alternative}")
    retried, _ = _search_query(product, provider, navigation, folder, max_pages, alternative)
    retried['evidence'] = result['evidence'] + retried['evidence']
    if incomplete and retried['status'] == 'no_encontrado':
        retried.update(status='busqueda_incompleta', reason='Consulta incompleta; revisar evidencia')
    return retried


def _search_query(product, provider, navigation, folder, max_pages, term):
    marketplace = provider['adapter'] == 'mercadolibre'
    log_progress(navigation, f"{provider['name']} | {product['id']} | Buscar: {term}")

    stem = f"{provider['id']}-{product['id']}-{uuid.uuid4().hex[:8]}"
    url = search_url(provider, term)

    cards, refs, seen = [], [], set()
    history, origins = [], {}
    action, status, expected_page = 'search', 'ok', None
    limited = False

    for page in range(max_pages):
        if (url, action, expected_page) in seen and action != 'load_more':
            status = 'busqueda_incompleta'
            break
        seen.add((url, action, expected_page))

        if not allowed_url(provider, url):
            status = 'error_url'
            break

        path = folder / 'evidencia' / f'{stem}-{page + 1}.json'
        try:
            options = {} if expected_page is None else dict(expected_page=expected_page)
            if marketplace:
                options['order_by'] = 'price_asc'
            data, used = navigation.collect(provider, url, path, term, action, **options)
            refs.append(used.relative_to(folder).as_posix())
        except (ProviderSuspended, BrowserDisconnected):
            raise
        except Exception as error:
            atomic_json(path, dict(capture_version=1, status='error_consulta', url=url, error=str(error), cards=[],
                request=dict(provider=provider['id'], query=term, action=action, expected_url=url)))
            refs.append(path.relative_to(folder).as_posix())
            status = 'error_consulta'
            break

        status = data['status']
        history.append((url, action, expected_page))
        previous = {card.get('url') for card in cards}
        added = [c for c in data.get('cards', []) if c.get('url') not in previous]
        cards.extend(added)

        for card in added:
            origins[card.get('url')] = len(history) - 1

        if status != 'ok':
            break

        if action == 'load_more' and not added:
            status = 'busqueda_incompleta'
            break

        # Verificar una ficha compatible antes de avanzar a la página siguiente.
        if marketplace and candidates_by_price(product, cards):
            if data.get('next') or data.get('next_page') or data.get('load_more'):
                limited = True
                status = 'busqueda_incompleta'
            break

        if data.get('next'):
            url, action, expected_page = data['next'], 'next', None
        elif data.get('next_page'):
            url, action, expected_page = data['url'], 'next', data['next_page']
        elif data.get('load_more'):
            expected_page = None
            action = 'load_more'
        else:
            break
    else:
        # Alcanzar el límite con páginas pendientes no demuestra ausencia.
        status = 'busqueda_incompleta'
        limited = marketplace

    result = select(product, cards, status)
    candidates = candidates_by_price(product, cards)[:3] if marketplace else [result]
    if marketplace and candidates:
        result = dict(result, url=candidates[0]['url'])
    detail_attempted = bool(result.get('url')) and (status == 'ok' or limited)
    # Una ficha verificada sirve para comparar, aunque no se recorra todo el sitio.
    for attempt, candidate in enumerate(candidates if detail_attempted else []):
        log_progress(navigation, f"{provider['name']} | {product['id']} | Verificando ficha: {candidate.get('title', '')}")
        path = folder / 'evidencia' / f'{stem}-ficha-{attempt + 1}.json'
        try:
            origin = origins[candidate['url']]
            if attempt or any(action == 'next' for _, action, _ in history[origin + 1:]):
                for index, (source_url, source_action, source_page) in enumerate(history[:origin + 1], 1):
                    back = folder / 'evidencia' / f'{stem}-regreso-{attempt}-{index}.json'
                    try:
                        options = {} if source_page is None else dict(expected_page=source_page)
                        if marketplace:
                            options['order_by'] = 'price_asc'
                        data, used = navigation.collect(provider, source_url, back, term, source_action, **options)
                    except (ProviderSuspended, BrowserDisconnected):
                        raise
                    except Exception as error:
                        atomic_json(back, dict(capture_version=1, status='error_consulta', url=source_url, error=str(error), cards=[],
                            request=dict(provider=provider['id'], query=term, action=source_action, expected_url=source_url)))
                        refs.append(back.relative_to(folder).as_posix())
                        raise
                    refs.append(used.relative_to(folder).as_posix())
                    if data['status'] != 'ok':
                        raise RuntimeError('No se pudo regresar a la página del producto elegido')
                if marketplace:
                    candidate = next((item for item in candidates_by_price(product, data['cards'])
                                      if same_url(item['url'], candidate['url'], provider)), candidate)

            detail, path = navigation.detail(candidate['url'], path)
            result = select(product, detail.get('cards', []), detail['status'])
            result['url'] = candidate['url']
            if detail['status'] != 'ok':
                result.update(status=detail['status'], price=None, reason='No se pudo confirmar la ficha')
            elif marketplace:
                listed = min((money(p.get('amount')) for p in candidate['prices']
                              if p.get('currency') == 'ARS' and money(p.get('amount'))), default=None)
                result = validate_offer(product, result, listed)
        except (ProviderSuspended, BrowserDisconnected):
            raise
        except Exception as error:
            atomic_json(path, dict(capture_version=1, status='error_consulta', url=candidate['url'], error=str(error), cards=[],
                request=dict(provider=provider['id'], query='', action='detail', expected_url=candidate['url'])))
            result.update(status='error_consulta', url=candidate['url'], price=None, reason='No se pudo confirmar la ficha')
        refs.append(path.relative_to(folder).as_posix())
        if result['status'] == 'ok' or not marketplace or result['status'].startswith('error'):
            break

    if marketplace and detail_attempted and result['status'] != 'ok' and status == 'ok':
        result.update(status='busqueda_incompleta', price=None,
                      reason='Las primeras publicaciones compatibles no pudieron confirmarse; revisar evidencia')

    if limited and result['status'] == 'ok':
        result.update(search_limited=True, pages_checked=len(history),
                      reason=f'Publicación verificada; búsqueda limitada a {len(history)} páginas. '
                             'No garantiza el menor precio de todo MercadoLibre.')
    elif status not in ('ok', 'no_encontrado'):
        result.update(status=status, price=None, reason='Consulta incompleta; revisar evidencia')

    result.update(product_id=product['id'], provider=provider['id'], query=term, evidence=refs, checked_at=now())
    return result, detail_attempted
