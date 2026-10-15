"""Configuración de tiendas, rutas permitidas y equivalencia de búsquedas."""
import os
from pathlib import Path
import re
import unicodedata
from urllib.parse import parse_qs, quote, quote_plus, unquote, urljoin, urlparse

ROOT = Path(__file__).resolve().parent.parent
# El guion bajo identifica filtros o paginación de MercadoLibre.
SEARCH_SLUG = r'[a-zA-Z0-9%.,\u00c0-\u024f-]+'


def allowed_hosts(provider):
    return provider.get('allowed_hosts', [urlparse(provider['base']).hostname])


def allowed_url(provider, url):
    try:
        parsed = urlparse(url)
        return (parsed.scheme == 'https' and not parsed.username and not parsed.password
                and parsed.port in (None, 443) and parsed.hostname in allowed_hosts(provider))
    except (TypeError, ValueError):
        return False


def ml_parameters(parsed):
    """MercadoLibre también lleva variantes en el fragmento; el seguimiento no cambia la página."""
    fields = parse_qs(parsed.query, keep_blank_values=True)
    if '=' in parsed.fragment:
        for key, values in parse_qs(parsed.fragment, keep_blank_values=True).items():
            fields.setdefault(key, []).extend(values)
    return {key: values for key, values in fields.items()
            if key not in ('tracking_id', 'position', 'search_layout', 'type', 'sid') and not key.startswith('utm_')}


def search_parameters(params):
    # «Todo MercadoLibre» no filtra la búsqueda. Otros valores sí se conservan.
    return {key: values for key, values in params.items()
            if not (key == 'sb' and values == ['all_mercadolibre'])}


def same_url(first, second, provider=None):
    """Acepta redirecciones de ML sólo para la misma búsqueda o publicación."""
    try:
        a, b = urlparse(first), urlparse(second)
        ports = a.port or 443, b.port or 443
    except (TypeError, ValueError):
        return False
    if provider and (not allowed_url(provider, first) or not allowed_url(provider, second)):
        return False
    if ((a.scheme, a.hostname, ports[0], a.path, parse_qs(a.query, keep_blank_values=True)) ==
            (b.scheme, b.hostname, ports[1], b.path, parse_qs(b.query, keep_blank_values=True)) and
            (not provider or provider.get('adapter') != 'mercadolibre' or a.fragment == b.fragment)):
        return True
    if not provider or provider.get('adapter') != 'mercadolibre':
        return False

    aq, bq = ml_parameters(a), ml_parameters(b)
    ap, bp = unquote(a.path).rstrip('/'), unquote(b.path).rstrip('/')
    if a.hostname == b.hostname and a.path == b.path and aq == bq:
        return True
    # Mantener wid y los parámetros de variante evita mezclar ofertas/vendedores.
    aid, bid = re.search(r'\bMLA-?(\d+)\b', ap, re.I), re.search(r'\bMLA-?(\d+)\b', bp, re.I)
    if aid or bid:
        return bool(aid and bid and aid[1] == bid[1] and aq == bq)

    def search_key(url, path, params):
        params = search_parameters(params)
        values = params.get('q', params.get('as_word'))
        if values and len(values) == 1 and len(params) == 1 and path in ('/jm/search', '/search'):
            return slugify(values[0])
        if (url.hostname == 'listado.mercadolibre.com.ar' and not params
                and re.fullmatch('/' + SEARCH_SLUG, path)):
            return slugify(path.lstrip('/')) or None
        return None

    ak, bk = search_key(a, ap, aq), search_key(b, bp, bq)
    return ak is not None and ak == bk


def slugify(text):
    clean = unicodedata.normalize('NFKD', str(text or '').lower())
    clean = ''.join(c for c in clean if not unicodedata.combining(c))
    return re.sub(r'[^a-z0-9]+', '-', clean).strip('-')


def without_price_order(url, provider):
    """Quita sólo el orden ascendente solicitado, nunca filtros de producto."""
    if not allowed_url(provider, url):
        return url
    parsed = urlparse(url)
    if (provider.get('adapter') != 'mercadolibre' or parsed.hostname != 'listado.mercadolibre.com.ar'
            or not re.fullmatch('/' + SEARCH_SLUG + r'(?:_Desde_[1-9]\d*)?_OrderId_PRICE(?:_Desde_[1-9]\d*)?(?:_NoIndex_True)?/?', parsed.path)):
        return url
    path = parsed.path.replace('_OrderId_PRICE', '').replace('_NoIndex_True', '')
    return parsed._replace(path=path).geturl()


def capture_matches(data, expected_url, provider, expected_page=None, order_by=None):
    """Una paginación JS debe probar la búsqueda y su página activa, por separado."""
    actual_url = data.get('url', '')
    if order_by == 'price_asc' and provider and provider.get('adapter') == 'mercadolibre':
        expected_url = without_price_order(expected_url, provider)
        actual_url = without_price_order(actual_url, provider)
    if expected_page is None:
        return same_url(expected_url, actual_url, provider)
    if (not provider or provider.get('adapter') != 'mercadolibre' or type(expected_page) is not int or
            expected_page < 2 or type(data.get('page_number')) is not int or data.get('page_number') != expected_page):
        return False

    def identity(url):
        if not allowed_url(provider, url):
            return None
        parsed = urlparse(url)
        if parsed.hostname != 'listado.mercadolibre.com.ar':
            return None
        if search_parameters(ml_parameters(parsed)):
            return None  # Un filtro distinto del inicio de la búsqueda no es la misma página.
        found = re.fullmatch('/(' + SEARCH_SLUG + r')(?:_Desde_([1-9]\d*))?(?:_NoIndex_True)?/?', parsed.path)
        if not found or re.search(r'[/_]', unquote(found[1])):
            return None
        return slugify(unquote(found[1]))

    first, second = identity(expected_url), identity(actual_url)
    return first is not None and first == second


def provider_settings(provider):
    settings = dict(provider)
    for key in ('id', 'adapter'):
        if not isinstance(settings.get(key), str) or not re.fullmatch(r'[a-z0-9_-]+', settings[key]):
            raise ValueError('Cada tienda requiere un ' + key + ' válido.')
    base = urlparse(settings.get('base', ''))
    if base.scheme != 'https' or not base.netloc or base.username or base.password:
        raise ValueError('Cada tienda requiere una URL HTTPS sin credenciales.')
    hosts = allowed_hosts(settings)
    if (not isinstance(hosts, list) or not hosts or
            any(not isinstance(host, str) or not re.fullmatch(r'[a-z0-9]+(?:[.-][a-z0-9]+)*', host) for host in hosts)
            or base.hostname not in hosts or len(set(hosts)) != len(hosts)):
        raise ValueError('allowed_hosts requiere los hosts exactos de la tienda, sin comodines.')
    if not allowed_url(settings, settings['base']):
        raise ValueError('URL base inválida para la tienda.')
    if 'home' in settings and not allowed_url(settings, settings['home']):
        raise ValueError('La portada debe pertenecer a un host permitido de la tienda.')
    pattern = settings.get('search')
    cleaned = pattern.replace('{query}', '').replace('{slug}', '') if isinstance(pattern, str) else ''
    if not isinstance(pattern, str) or not pattern or '{' in cleaned or '}' in cleaned:
        raise ValueError('La búsqueda requiere una ruta; {query} o {slug} representa la consulta.')
    secret = settings.get('access_env')
    if secret is not None and (not isinstance(secret, str) or not re.fullmatch(r'COMPARASUPLE_[A-Z0-9_]+', secret)):
        raise ValueError('access_env debe nombrar una variable COMPARASUPLE_ válida.')
    if 'access_password' in settings:
        password = settings['access_password']
        if not isinstance(password, str) or not password or '\x00' in password:
            raise ValueError('access_password debe ser un texto no vacío, sin caracteres nulos.')
        if not secret:
            raise ValueError('access_password requiere access_env para entregar la clave al flujo.')
    if not isinstance(settings.get('name'), str) or not settings['name'].strip():
        raise ValueError('La tienda requiere un nombre.')
    if settings.get('query_mode', 'full') not in ('full', 'compact'):
        raise ValueError('query_mode debe ser full o compact.')
    search_url(settings, 'prueba')
    return settings


def search_url(provider, term):
    slug = slugify(term)
    pattern = provider['search'].replace('{slug}', slug)
    template = urlparse(urljoin(provider['base'].rstrip('/') + '/', pattern))
    # El espacio se codifica distinto en la ruta (/buscar/texto) y en ?q=texto.
    url = template._replace(path=template.path.replace('{query}', quote(term, safe='')),
                            query=template.query.replace('{query}', quote_plus(term)),
                            fragment=template.fragment.replace('{query}', quote(term, safe=''))).geturl()
    if not allowed_url(provider, url):
        raise ValueError('La búsqueda debe permanecer en la tienda configurada.')
    return url


def read_providers(config):
    items = config.get('providers')
    if not isinstance(items, list) or not items:
        raise ValueError('Configurar al menos una tienda.')
    providers = [provider_settings(item) for item in items]
    if len({p['id'] for p in providers}) != len(providers):
        raise ValueError('Los IDs de las tiendas deben ser únicos.')
    for provider in providers:
        for path in (ROOT / 'flujos' / (provider['id'] + '.tag'),
                     ROOT / 'codigo/parsers' / (provider['adapter'] + '.js')):
            if not path.is_file():
                raise ValueError('Falta el archivo de la tienda: ' + str(path))
    return providers


def provider_snapshot(provider):
    """La clave y el orden de búsqueda no forman parte de la identidad guardada."""
    return {key: value for key, value in provider.items() if key not in ('access_password', 'query_mode')}


def read_credentials(providers):
    """Prioriza el entorno, luego la configuración y por último la entrada manual."""
    import getpass
    credentials = {}
    for provider in providers:
        name = provider.get('access_env')
        if name and name not in credentials:
            credentials[name] = (os.environ.get(name) or provider.get('access_password') or
                                 getpass.getpass('Clave de acceso a ' + provider['name'] + ': '))
            if not credentials[name]:
                raise ValueError('Falta la clave de acceso a ' + provider['name'])
    return credentials
