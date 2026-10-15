"""Compara presentación, sabor y stock antes de elegir un precio total."""
import re
import unicodedata
from decimal import Decimal

FLAVORS = {
    'vainilla': ('vainilla', 'vainlla', 'vanilla'),
    'chocolate': ('chocolate', 'choco', 'cacao'),
    'frutilla': ('frutilla', 'fresa', 'strawberry'),
    'neutro': ('neutro', 'sin sabor', 'unflavored'),
    'frutos rojos': ('frutos rojos', 'berry'),
    'yogurt': ('yogurt', 'yogur'),
    'lemonade': ('lemonade', 'limonada'),
    'lemon punch': ('lemon punch',),
    'fruit punch': ('fruit punch',),
}
# Las líneas específicas van antes que las generales: Collagen Whey no es Whey.
LINES = [
    ('soy', r'soy'), ('xt gold', r'xt\s*gold'),
    ('collagen whey', r'(?:collagen|colageno)\s+whey|whey\s+(?:collagen|colageno)'),
    ('whey', r'whey'), ('barra', r'bar\b|barra'),
    ('creatina', r'creatina|creatine'), ('xplode', r'xplode'),
    ('nitric', r'nitro|nitric'), ('pump', r'pump'), ('explosive', r'explosive'),
    ('bcaa', r'bcaa'), ('citrato', r'citrato|citrate'),
    ('vitamin pro', r'vitamin pro'), ('vitamina c', r'vitamina\s*c\b|vitamin\s*c\b'),
    ('k2', r'k2'), ('omega', r'omega'), ('antioxidante', r'antioxid'),
    ('colageno', r'colageno|collagen'), ('alfajor', r'alfajor'),
]


def norm(s):
    """Unifica mayúsculas, acentos y separadores para comparar nombres."""
    s = unicodedata.normalize('NFKD', str(s or '').lower())
    s = ''.join(c for c in s if not unicodedata.combining(c))
    return re.sub(r'[^a-z0-9]+', ' ', s).strip()


def brand_matches(brand, title):
    """Acepta OneFit/One Fit con palabras completas; no confunde OneFitness."""
    wanted, words = norm(brand).split(), norm(title).split()
    if not wanted:
        return False
    # Gold también puede ser una línea de otra marca (Nitro Tech Whey Gold es de MuscleTech).
    if ''.join(wanted) in ('gold', 'goldnutrition') and re.search(
            r'\b(?:optimum|gold\s*standard|body\s*advance|htn|hard\s*core|muscletech|nitro\s*tech)\b', ' '.join(words)):
        return False
    if wanted == ['gold'] and 'goldnutrition' in words:
        return True
    if all(word in words for word in wanted):
        return True
    compact = ''.join(wanted)
    if len(compact) < 5:
        return False
    for start in range(len(words)):
        joined = ''
        for word in words[start:]:
            joined += word
            if joined == compact:
                return True
            if not compact.startswith(joined):
                break
    return False


def money(value):
    """Acepta importes positivos, tanto 12.345,67 como 12345.67."""
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float, Decimal)):
        number = float(value)
        return number if 0 < number < float('inf') else None
    s = str(value).replace('$', '').replace(' ', '').replace('\xa0', '')
    if ',' in s:
        s = s.replace('.', '').replace(',', '.')
    elif re.fullmatch(r'\d{1,3}(\.\d{3})+', s):
        s = s.replace('.', '')
    try:
        number = float(s)
        return number if 0 < number < float('inf') else None
    except ValueError:
        return None


def specs(name):
    """Extrae los datos que distinguen una presentación de otra."""
    s, raw = norm(name), str(name).lower()
    flavors = {key for key, aliases in FLAVORS.items()
               if any(re.search(r'\b' + re.escape(alias) + r'\b', s) for alias in aliases)}
    weights = []
    for match in re.finditer(r'(\d+(?:[.,]\d+)?)\s*(kg|kilos?|grs?|gramos?|g|lbs?|libras?)\b', raw):
        # La proteína por porción no es el peso del envase.
        if re.match(r'\s+de\s+prote', raw[match.end():]):
            continue
        number, unit = float(match[1].replace(',', '.')), match[2]
        factor = 1000 if unit.startswith('k') else 453.59237 if unit.startswith('l') else 1
        weights.append(round(number * factor, 1))
    count = re.search(r'(\d+)\s*(caps(?:ulas)?|days|dias|serv(?:ings)?)\b', s)
    unit = count[2] if count else ''
    count_unit = 'caps' if unit.startswith('cap') else 'days' if unit in ('days', 'dias') else 'serv' if unit else ''
    pack = re.search(r'\b(?:caja|pack)\s*(?:x\s*)?(\d+)\b|(?<![\w.,])(?:x\s*)?(\d+)\s*(?:unidad(?:es)?|un|uds?)\b', raw)
    pack_count = int(pack[1] or pack[2]) if pack else None
    if pack_count is None:
        pack = re.search(r'\bx\s*(\d+)\s*(?=$|[+,;]|\b(?:con|mas)\b)|\b(\d+)\s*x\s*\d+(?:[.,]\d+)?\s*(?:kg|g|grs?|gramos?|lbs?)\b', raw)
        pack_count = int(pack[1] or pack[2]) if pack else None
    # "2 Creatina 300g" es un pack; "2 lb" y "100% whey" no lo son.
    if pack_count is None:
        leading = re.match(r'\s*(\d+)\s+([a-z]+)\b', raw)
        if (leading and (1 < int(leading[1]) <= 24 or re.search(r'\bc\s*/\s*u\b', raw))
                and not re.fullmatch(r'kg|kilos?|grs?|gramos?|g|mg|ml|lbs?|libras?|caps(?:ulas)?|days|dias|serv(?:ings)?', leading[2])):
            pack_count = int(leading[1])
    return dict(
        line=next((key for key, pattern in LINES if re.search(pattern, s)), ''),
        flavors=flavors, weights=weights, count=int(count[1]) if count else None,
        count_unit=count_unit, pack=pack_count,
        sugarfree='sin azucar' in s, doypack=bool(re.search(r'doy\s*pack|doypack', s)),
    )


def requested_name(product):
    """Las columnas opcionales del Excel completan el nombre original."""
    extra = [product.get(key, '') for key in ('line', 'flavor', 'presentation')]
    if product.get('weight_g'):
        extra.append(str(product['weight_g']) + ' g')
    if product.get('pack'):
        extra.append('caja x ' + str(int(product['pack'])))
    return ' '.join([product['name']] + [str(value) for value in extra if value])


def brand_query(product):
    """Confirma la marca sin exigir una presentación o sabor particular."""
    spec = specs(requested_name(product))
    return (product['brand'] + ' ' + (spec['line'] or product['name'])).strip()


def query(product):
    parts = [' '.join(str(product['name']).split())]

    def contains(value):
        return ' ' + norm(value) + ' ' in ' ' + norm(' '.join(parts)) + ' '

    if not contains(product['brand']) and not brand_matches(product['brand'], parts[0]):
        parts.insert(0, product['brand'])
    for field in ('line', 'flavor', 'presentation', 'sku'):
        value = ' '.join(str(product.get(field) or '').split())
        if not value or contains(value):
            continue
        present, extra = specs(' '.join(parts)), specs(value)
        if field == 'flavor' and any(norm(value) in aliases and key in present['flavors']
                                     for key, aliases in FLAVORS.items()):
            continue
        if field == 'presentation' and norm(value) in ('doypack', 'doy pack') and present['doypack']:
            continue
        if field == 'presentation':
            if (re.fullmatch(r'(?:caja|pack)\s*(?:x\s*)?\d+|(?:x\s*)?\d+\s*(?:unidades?|un|uds?)', norm(value))
                    and extra['pack'] is not None and extra['pack'] == present['pack']):
                continue
            if (re.fullmatch(r'\d+(?:[.,]\d+)?\s*(?:kg|kilos?|grs?|gramos?|g|lbs?|libras?)\.?', value, re.I)
                    and any(abs(extra['weights'][0] - weight) <= .5 for weight in present['weights'])):
                continue
        parts.append(value)
    present = specs(' '.join(parts))
    weight = money(product.get('weight_g'))
    # Medio gramo admite el redondeo de libras a gramos, sin cambiar el envase.
    if weight and not any(abs(weight - current) <= .5 for current in present['weights']):
        parts.append(format(Decimal(str(weight)).normalize(), 'f') + ' g')
    pack = money(product.get('pack'))
    if pack and pack != present['pack']:
        parts.append('caja x ' + format(Decimal(str(pack)).normalize(), 'f'))
    return ' '.join(parts)


def compact_query(product):
    """Quita ruido del buscador; conserva tamaño, sabor, envase y cantidad."""
    term = query(product)
    # Un SKU puede terminar en "300G"; nunca se modifica un identificador.
    if product.get('sku') or not specs(term)['weights']:
        return term
    # 300 g, 300 gr y 300 gramos se buscan como 300. La ficha valida la unidad.
    term = re.sub(r'(\d+(?:[.,]\d+)?)\s*(?:gramos?|grs?|g)\b', r'\1', term, flags=re.I)
    term = re.sub(r'\bmonohidrato\b', '', term, flags=re.I)
    return ' '.join(term.split())


def variants(card):
    return [dict(title=item['title'], url=card['url'], variant_id=item.get('variant_id', ''),
                 sku=item.get('sku', ''), available=item['available'], prices=item['prices'])
            for item in (card.get('variants') or [card])]


def identity(product, candidate):
    """Devuelve exacta, revisar o no; un dato faltante nunca confirma identidad."""
    wanted, actual = specs(requested_name(product)), specs(candidate['title'])
    name, hay = norm(requested_name(product)), norm(candidate['title'])
    if not brand_matches(product['brand'], candidate['title']):
        return 'no'
    if wanted['line'] and wanted['line'] != actual['line']:
        return 'no'
    sku, actual_sku = norm(product.get('sku', '')), norm(candidate.get('sku', ''))
    if sku and actual_sku and sku != actual_sku:
        return 'no'
    if wanted['line'] == 'whey' and bool(re.search(r'\b(?:collagen|colageno)\b', name)) != bool(re.search(r'\b(?:collagen|colageno)\b', hay)):
        return 'no'
    # Una línea nueva necesita el nombre completo o un SKU coincidente.
    variant_uncertain = (not wanted['line'] and not set(name.split()) <= set(hay.split())
                         and not (sku and sku == actual_sku))
    if wanted['line'] == 'whey':
        # Ripped y aislada/ISO son variantes diferentes de la whey común.
        variants = (r'\bripped\b', r'\b(?:isolate|isolated|aislad[ao]s?|iso(?:\s*100)?)\b')
        requested = {pattern for pattern in variants if re.search(pattern, name)}
        offered = {pattern for pattern in variants if re.search(pattern, hay)}
        if offered - requested:
            return 'no'
        variant_uncertain = bool(requested - offered)
    if 'combo' in hay:
        return 'no'
    extras = norm(candidate['title'].replace('+', ' mas '))
    for accessory in ('shaker', 'vaso', 'botella', 'scoop'):
        prefix = '' if accessory in ('shaker', 'vaso') else r'(?:mas|con|incluye|regalo)\s+(?:(?:un|una|\d+)\s+)?'
        if (re.search(r'\b' + prefix + accessory + r's?\b', extras)
                and not re.search(r'\b' + accessory + r's?\b', name)):
            return 'no'
    qualifiers = {
        'creatina': (r'colageno|collagen', r'magnesio|magnesium', r'creapure'),
        'citrato': (r'magnesio|magnesium', r'potasio|potassium', r'calcio|calcium'),
        'k2': (r'd3',),
    }
    for pattern in qualifiers.get(wanted['line'], ()):
        requested = bool(re.search(r'\b(?:' + pattern + r')\b', name))
        offered = bool(re.search(r'\b(?:' + pattern + r')\b', hay))
        if offered and not requested:
            return 'no'
        variant_uncertain = variant_uncertain or (requested and not offered)
    variant_uncertain = variant_uncertain or any(
        word in name and word not in hay for word in ('classic', 'sport', 'ripped'))
    if wanted['line'] == 'barra' and wanted['sugarfree'] != actual['sugarfree']:
        return 'no'
    uncertain = variant_uncertain or (wanted['doypack'] and not actual['doypack']) or (bool(sku) and not candidate.get('sku'))
    if wanted['count'] and actual['count'] and wanted['count_unit'] != actual['count_unit']:
        uncertain = True
    if wanted['flavors']:
        if actual['flavors'] and wanted['flavors'] != actual['flavors']:
            return 'no'
        if not actual['flavors']:
            uncertain = True
    for weight in wanted['weights']:
        if not actual['weights']:
            uncertain = True
        elif not any(abs(weight - value) <= max(2, weight * .005) for value in actual['weights']):
            return 'no'
    # 1 kg + 300 g es otro producto; 2 lb / 907 g expresan el mismo envase.
    sizes = wanted['weights'] + [weight * wanted['pack'] for weight in wanted['weights'] if wanted['pack']]
    if sizes and any(not any(abs(value - size) <= max(2, size * .005) for size in sizes)
                     for value in actual['weights']):
        return 'no'
    for key in ('count', 'pack'):
        if wanted[key] is not None:
            if actual[key] is None:
                uncertain = True
            elif wanted[key] != actual[key]:
                return 'no'
        elif key == 'pack' and actual[key] and actual[key] > 1:
            return 'no'
    return 'revisar' if uncertain else 'exacta'


def selection(status, candidate, reason, price=None, method=''):
    return dict(status=status, price=price, method=method, reason=reason,
                title=candidate.get('title', ''), url=candidate.get('url', ''),
                variant_id=candidate.get('variant_id', ''))


def validate_offer(product, result, listed=None):
    """Una diferencia grande requiere revisión, no se toma como una oferta segura."""
    if result.get('status') != 'ok':
        return result
    price, cost = result['price'], money(product.get('cost'))
    reason = ''
    if cost and price < cost * .2:
        reason = 'Precio inferior al 20% del costo de referencia; revisar la publicación'
    elif listed and abs(price - listed) > max(1, listed * .01):
        reason = 'El precio de la ficha difiere del listado; revisar la oferta y sus condiciones'
    return dict(result, status='revisar', price=None, method='', reason=reason) if reason else result


def candidates_by_price(product, cards):
    """Ordena fichas para revisar; el stock desconocido se confirma al abrirlas."""
    ranked = []
    for card in cards:
        for candidate in variants(card):
            match = identity(product, candidate)
            if match == 'no':
                continue
            price = min((money(item.get('amount')) or float('inf') for item in candidate['prices']
                         if item.get('currency') == 'ARS'), default=float('inf'))
            ranked.append((candidate['available'] is False, match != 'exacta', price, candidate))
    return [item[3] for item in sorted(ranked, key=lambda item: item[:3])]


def select(product, cards, page_status='ok'):
    """Elige el menor precio de una coincidencia exacta con stock confirmado."""
    matches = {'exacta': [], 'revisar': []}
    for card in cards:
        for candidate in variants(card):
            match = identity(product, candidate)
            if match in matches:
                matches[match].append(candidate)
    exact, review = matches['exacta'], matches['revisar']
    wanted = specs(requested_name(product))
    # Aunque haya una sola oferta, no adivinamos un tamaño ausente en el Excel.
    for field in ('weights', 'count', 'pack'):
        if not wanted[field] and any(specs(candidate['title'])[field] for candidate in exact):
            return selection('revisar', exact[0], 'El catálogo no especifica cuál de las presentaciones encontradas se necesita')
    usable = []
    for candidate in exact:
        if candidate['available'] is True:
            for price in candidate['prices']:
                if price.get('currency') != 'ARS':
                    continue
                amount = money(price.get('amount'))
                if amount is not None:
                    usable.append((amount, price['method'], candidate))
    if usable:
        amount, method, candidate = min(usable, key=lambda item: item[0])
        return selection('ok', candidate, 'Misma variante y presentación', amount, method)
    if review or any(candidate['available'] is None for candidate in exact):
        status = 'revisar'
    elif exact and all(candidate['available'] is False for candidate in exact):
        status = 'sin_stock'
    elif exact:
        status = 'sin_precio'
    else:
        status = page_status if page_status != 'ok' else 'no_encontrado'
    reason = {'revisar': 'Falta confirmar presentación o disponibilidad',
              'no_encontrado': 'Ninguna publicación coincide con la presentación pedida',
              'sin_stock': 'La presentación pedida figura sin stock',
              'sin_precio': 'La presentación pedida no muestra un precio'}.get(status, status)
    if status == 'revisar' and (exact or review):
        # El precio publicado solo ordena qué ficha revisar; no confirma su precio final.
        def priority(candidate):
            listed = min((money(price.get('amount')) or float('inf')
                          for price in candidate.get('prices', []) if price.get('currency') == 'ARS'),
                         default=float('inf'))
            return candidate['available'] is False, candidate not in exact, listed
        return selection(status, min(exact + review, key=priority), reason)
    return selection(status, (exact or review or [{}])[0], reason)
