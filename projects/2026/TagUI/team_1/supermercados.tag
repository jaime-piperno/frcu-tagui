// ==============================================================================
// UTN FRCU - Tecnologías para la Automatización (Año 2026)
// Trabajo Práctico Integrador - Etapa 1: RPA
//
// Script: supermercados.tag
// Descripción: Motor de Búsqueda Rápida Individual ejecutado exclusivamente con TagUI:
//              tagui supermercados.tag <archivo_de_entrada>
//              (La Compra del Mes / Canasta se ejecuta exclusivamente con Puppeteer vía rpa_runner.js)
//
// Ejecución: tagui supermercados.tag temp_input.csv
// ==============================================================================

// En la primera iteración creamos el encabezado si el archivo aún no existe
if iteration equals to 1
    js var fs = require('fs'); if (!fs.exists('resultados.csv')) { fs.write('resultados.csv', 'modo,producto_solicitado,nombre_encontrado,precio,supermercado,url,fecha,stock_status,cantidad,unidad\n', 'w'); }

echo ----------------------------------------------------------------------------
echo [INFO] Procesando producto: `producto` (Fila `iteration`)
echo ----------------------------------------------------------------------------

// Obtenemos la fecha actual en formato YYYY-MM-DD
js var hoy = new Date(); var m = (hoy.getMonth() + 1).toString(); var d = hoy.getDate().toString(); if (m.length < 2) m = '0' + m; if (d.length < 2) d = '0' + d; fechaHoy = hoy.getFullYear() + '-' + m + '-' + d;

// Detectar el modo de ejecución y cantidad solicitada (Búsqueda Individual exclusiva TagUI)
js modo_actual = 'individual'; try { if (typeof modo !== 'undefined' && modo && modo !== 'modo') { modo_actual = modo.trim(); } } catch(e) { modo_actual = 'individual'; }
js cant_actual = 1; try { if (typeof cantidad !== 'undefined' && cantidad && !isNaN(parseFloat(cantidad))) { cant_actual = parseFloat(cantidad); } } catch(e) { cant_actual = 1; }
js unid_actual = ''; try { if (typeof unidad !== 'undefined' && unidad) { unid_actual = unidad.trim(); } } catch(e) { unid_actual = ''; }
js unidades_compra = 1; try { if (typeof unidades !== 'undefined' && unidades && !isNaN(parseInt(unidades))) { unidades_compra = parseInt(unidades); } } catch(e) { unidades_compra = 1; }

// Codificamos el término de búsqueda validado por el catálogo oficial
js prod_clean = producto.replace(/"/g, '').replace(/'/g, '').trim();
js query_term = prod_clean;
js try { if (typeof termino !== 'undefined' && termino && termino.trim() && termino !== 'termino') { query_term = termino.trim(); } } catch(e) {}

// Adaptaciones específicas para búsqueda individual con TagUI
js var pLow = prod_clean.toLowerCase();
js var qLow = query_term.toLowerCase();
js if (pLow.indexOf('coca cola') > -1 || pLow.indexOf('coca-cola') > -1 || qLow.indexOf('coca cola') > -1) { query_term = 'coca cola 2,25L'; }
js else if (pLow.indexOf('sprite') > -1 || qLow.indexOf('sprite') > -1) { query_term = 'sprite 2,25L'; }
js else if ((pLow.indexOf('manaos') > -1 && pLow.indexOf('naranja') > -1) || (qLow.indexOf('manaos') > -1 && qLow.indexOf('naranja') > -1)) { query_term = 'manaos naranja'; }
js else if ((pLow.indexOf('manaos') > -1 && (pLow.indexOf('lima') > -1 || pLow.indexOf('limon') > -1)) || (qLow.indexOf('manaos') > -1 && (qLow.indexOf('lima') > -1 || qLow.indexOf('limon') > -1))) { query_term = 'manaos lima limon'; }
js else if ((pLow.indexOf('manaos') > -1 && pLow.indexOf('cola') > -1) || (qLow.indexOf('manaos') > -1 && qLow.indexOf('cola') > -1)) { query_term = 'manaos cola'; }

js prod_url = encodeURIComponent(query_term.replace(/,/g, ' ').replace(/\s+/g, ' '));


// ==============================================================================
// 1. CONSULTA EN CARREFOUR ARGENTINA
// ==============================================================================
echo [SUPERMERCADO 1] Abriendo navegador...
https://www.carrefour.com.ar
wait 3

// Cierre de cookies si estuviera presente
if present('Aceptar todo')
    click Aceptar todo
    wait 1

echo [SUPERMERCADO 1] Localizando buscador y escribiendo producto: `query_term`...
if present('input.vtex-styleguide-9-x-input')
    type input.vtex-styleguide-9-x-input as [clear]`query_term`[enter]
else if present('input[placeholder*="buscando"]')
    type input[placeholder*="buscando"] as [clear]`query_term`[enter]
wait 2
if present('button[aria-label="Buscar Productos"]')
    click button[aria-label="Buscar Productos"]
else if present('button[class*="searchBarIcon--external-search"]')
    click button[class*="searchBarIcon--external-search"]
wait 5

echo [SUPERMERCADO 1] Extrayendo resultados...
carrefour_nom = "No encontrado"
carrefour_pre = "N/D"
carrefour_url = url()
carrefour_stock = "NO ENCONTRADO"

dom begin
function cleanText(s) {
    if (!s) return '';
    return s.toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '').replace(/[\.,;:!¡?¿\(\)\[\]"'\-_/]/g, ' ').replace(/\s+/g, ' ').trim();
}

var qStr = cleanText("`producto`");
var qWords = qStr.split(/\s+/).filter(function(w){ return w.length >= 2; });

// Seleccionar únicamente contenedores principales de tarjeta para evitar duplicados anidados
var cards = Array.from(document.querySelectorAll('[class*="galleryItem"]'));
if (cards.length === 0) cards = Array.from(document.querySelectorAll('article'));
if (cards.length === 0) cards = Array.from(document.querySelectorAll('section[class*="product-summary"]'));
if (cards.length === 0) return 'null';

var incompatibles = ['arrocera', 'olla', 'vaporera', 'electrodomestico', 'jabon', 'shampoo', 'perro', 'gato', 'juguete', 'vela', 'taza', 'vaso', 'termo', 'alimento para perro', 'alimento para gato'];

var candidates = [];
for (var i = 0; i < cards.length; i++) {
    var c = cards[i];
    var nEl = c.querySelector('[class*="productBrand"], [class*="product-summary-2-x-nameContainer"], [data-testid="product-summary-name"], [class*="productName"], h3, h2');
    var pEl = c.querySelector('[class*="sellingPrice"], [class*="currencyContainer"], [class*="price_sellingPrice"]');
    var lEl = c.querySelector('a[href*="/p"]') || c.querySelector('a');
    if (!nEl) continue;

    var nameVal = nEl.innerText.trim();
    if (!nameVal) continue;
    var priceVal = pEl ? pEl.innerText.replace(/\n/g, ' ').replace(/\s+/g, ' ').trim() : 'N/D';
    var urlVal = lEl ? lEl.href : window.location.href;

    var cardText = (c.innerText || '').toLowerCase();
    var unavail = (c.querySelector('[class*="unavailable"], [class*="outOfStock"]') !== null) || cardText.indexOf('agotado') > -1 || cardText.indexOf('sin stock') > -1;
    if (priceVal === 'N/D' || priceVal === '' || priceVal === '$ 0' || priceVal === '$ 0,00') unavail = true;

    var nClean = cleanText(nameVal);

    var tieneInc = false;
    for (var k = 0; k < incompatibles.length; k++) {
        if (nClean.indexOf(incompatibles[k]) > -1 && qStr.indexOf(incompatibles[k]) === -1) {
            tieneInc = true;
            break;
        }
    }
    if (tieneInc) continue;

    // Reglas estrictas de marca del catálogo
    if (qStr.indexOf('coca cola') > -1 && (nClean.indexOf('manaos') > -1 || nClean.indexOf('pepsi') > -1 || nClean.indexOf('secco') > -1)) continue;
    if (qStr.indexOf('manaos') > -1 && (nClean.indexOf('coca cola') > -1 || nClean.indexOf('pepsi') > -1 || nClean.indexOf('sprite') > -1 || nClean.indexOf('fanta') > -1)) continue;
    if (qStr.indexOf('sprite') > -1 && (nClean.indexOf('manaos') > -1 || nClean.indexOf('coca cola') > -1 || nClean.indexOf('7up') > -1)) continue;
    if (qStr.indexOf('gallo') > -1 && (nClean.indexOf('lucchetti') > -1 || nClean.indexOf('ala') > -1)) continue;
    if (qStr.indexOf('lucchetti') > -1 && (nClean.indexOf('gallo') > -1 || nClean.indexOf('ala') > -1 || nClean.indexOf('matarazzo') > -1)) continue;
    if (qStr.indexOf('matarazzo') > -1 && (nClean.indexOf('lucchetti') > -1 || nClean.indexOf('barilla') > -1 || nClean.indexOf('favorita') > -1)) continue;
    if (qStr.indexOf('serenisima') > -1 && (nClean.indexOf('tregar') > -1 || nClean.indexOf('ilolay') > -1)) continue;
    if (qStr.indexOf('tregar') > -1 && (nClean.indexOf('serenisima') > -1 || nClean.indexOf('ilolay') > -1)) continue;
    if (qStr.indexOf('cocinero') > -1 && (nClean.indexOf('natura') > -1 || nClean.indexOf('canuelas') > -1)) continue;
    if (qStr.indexOf('natura') > -1 && (nClean.indexOf('cocinero') > -1 || nClean.indexOf('canuelas') > -1)) continue;
    if (qStr.indexOf('playadito') > -1 && (nClean.indexOf('taragui') > -1 || nClean.indexOf('rosamonte') > -1)) continue;
    if (qStr.indexOf('taragui') > -1 && (nClean.indexOf('playadito') > -1 || nClean.indexOf('rosamonte') > -1)) continue;

    // Descartar Zero / Light si la consulta busca sabor regular / original
    if (qStr.indexOf('coca cola') > -1 && qStr.indexOf('zero') === -1 && qStr.indexOf('light') === -1 && qStr.indexOf('diet') === -1 && qStr.indexOf('sin azucar') === -1) {
        if (nClean.indexOf('zero') > -1 || nClean.indexOf('light') > -1 || nClean.indexOf('diet') > -1 || nClean.indexOf('sin azucar') > -1) continue;
    }
    if (qStr.indexOf('sprite') > -1 && qStr.indexOf('zero') === -1 && qStr.indexOf('sin azucar') === -1) {
        if (nClean.indexOf('zero') > -1 || nClean.indexOf('sin azucar') > -1) continue;
    }

    // Reglas estrictas de variantes y sabores (Manaos, etc.)
    if (qStr.indexOf('naranja') > -1) {
        if (nClean.indexOf('naranja') === -1) continue;
        if (nClean.indexOf('cola') > -1 || nClean.indexOf('pomelo') > -1 || nClean.indexOf('lima') > -1 || nClean.indexOf('limon') > -1 || nClean.indexOf('guarana') > -1 || nClean.indexOf('tonica') > -1) continue;
    }
    if (qStr.indexOf('cola') > -1 && qStr.indexOf('coca') === -1) {
        if (nClean.indexOf('cola') === -1) continue;
        if (nClean.indexOf('naranja') > -1 || nClean.indexOf('pomelo') > -1 || nClean.indexOf('lima') > -1 || nClean.indexOf('limon') > -1 || nClean.indexOf('guarana') > -1 || nClean.indexOf('tonica') > -1) continue;
    }
    if ((qStr.indexOf('lima') > -1 || qStr.indexOf('limon') > -1) && qStr.indexOf('sprite') === -1) {
        if (nClean.indexOf('lima') === -1 && nClean.indexOf('limon') === -1) continue;
        if (nClean.indexOf('cola') > -1 || nClean.indexOf('naranja') > -1 || nClean.indexOf('pomelo') > -1 || nClean.indexOf('guarana') > -1 || nClean.indexOf('tonica') > -1) continue;
    }

    var score = 0;
    if (nClean.indexOf('sabor original') > -1 || nClean.indexOf('original') > -1) score += 150;
    if (qStr.indexOf('naranja') > -1 && nClean.indexOf('naranja') > -1) score += 200;
    if (qStr.indexOf('cola') > -1 && nClean.indexOf('cola') > -1) score += 200;
    if ((qStr.indexOf('lima') > -1 || qStr.indexOf('limon') > -1) && (nClean.indexOf('lima') > -1 || nClean.indexOf('limon') > -1)) score += 200;
    if (nClean.indexOf(qStr) > -1) score += 100;
    for (var w = 0; w < qWords.length; w++) {
        if (nClean.indexOf(qWords[w]) > -1) score += 20;
    }
    if (score <= 0) continue;
    if ((qStr.indexOf('gaseosa') > -1 || qStr.indexOf('bebida') > -1) && (nClean.indexOf('shampoo') > -1 || nClean.indexOf('jabon') > -1 || nClean.indexOf('xkg') > -1)) {
        score -= 200;
    }
    if (unavail) score -= 10;

    candidates.push({
        name: nameVal,
        price: priceVal,
        url: urlVal,
        stock: unavail ? 'SIN STOCK' : 'DISPONIBLE',
        score: score
    });
}

if (candidates.length === 0) return 'null';
candidates.sort(function(a, b) { return b.score - a.score; });
return JSON.stringify(candidates[0]);
dom finish

js var cData = null; try { cData = JSON.parse(dom_result); } catch(e){}
js if (cData) { carrefour_nom = cData.name; carrefour_pre = cData.price; carrefour_url = cData.url; carrefour_stock = cData.stock; }
echo [SUPERMERCADO 1] Extraído: `carrefour_nom` | `carrefour_pre` | `carrefour_stock`
echo [SUPERMERCADO 1] Finalizado.
write `csv_row([modo_actual, producto, carrefour_nom, carrefour_pre, "Carrefour", carrefour_url, fechaHoy, carrefour_stock, cant_actual, unid_actual])` to resultados.csv


// ==============================================================================
// 2. CONSULTA EN COTO DIGITAL
// ==============================================================================
echo [SUPERMERCADO 2] Abriendo navegador...
echo [SUPERMERCADO 2] Navegando a https://www.coto.com.ar...
https://www.coto.com.ar
wait 3

if present('input#cio-autocomplete-0-input')
    type input#cio-autocomplete-0-input as [clear]`query_term`[enter]
else if present('input[placeholder*="busc"]')
    type input[placeholder*="busc"] as [clear]`query_term`[enter]
wait 4

echo [SUPERMERCADO 2] Extrayendo resultados...
coto_nom = "No encontrado"
coto_pre = "N/D"
coto_url = url()
coto_stock = "NO ENCONTRADO"

dom begin
function cleanText(s) {
    if (!s) return '';
    return s.toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '').replace(/[\.,;:!¡?¿\(\)\[\]"'\-_/]/g, ' ').replace(/\s+/g, ' ').trim();
}

var qStr = cleanText("`producto`");
var qWords = qStr.split(/\s+/).filter(function(w){ return w.length >= 2; });

var items = Array.from(document.querySelectorAll('constructor-result-item, .product-card, article')).slice(0, 15);
if (items.length === 0) return 'null';

var incompatibles = ['arrocera', 'olla', 'vaporera', 'electrodomestico', 'jabon', 'shampoo', 'perro', 'gato', 'juguete', 'vela', 'taza', 'vaso', 'termo', 'alimento para perro', 'alimento para gato'];

var candidates = [];
for (var i = 0; i < items.length; i++) {
    var it = items[i];
    var nEl = it.querySelector('.nombre-producto, h3, h2');
    var pEl = it.querySelector('.card-title, h4, [class*="price"]');
    var lEl = it.querySelector('a');
    if (!nEl) continue;

    var nameVal = nEl.innerText.trim();
    if (!nameVal) continue;
    var priceVal = pEl ? pEl.innerText.replace(/\n/g, ' ').replace(/\s+/g, ' ').trim() : 'N/D';
    var urlVal = lEl ? lEl.href : window.location.href;

    var itText = (it.innerText || '').toLowerCase();
    var unavail = itText.indexOf('sin stock') > -1 || itText.indexOf('agotado') > -1 || itText.indexOf('no disponible') > -1;
    if (priceVal === 'N/D' || priceVal === '' || priceVal === '$0' || priceVal === '$0,00') unavail = true;

    var nClean = cleanText(nameVal);

    var tieneInc = false;
    for (var k = 0; k < incompatibles.length; k++) {
        if (nClean.indexOf(incompatibles[k]) > -1 && qStr.indexOf(incompatibles[k]) === -1) {
            tieneInc = true;
            break;
        }
    }
    if (tieneInc) continue;

    // Reglas estrictas de marca del catálogo
    if (qStr.indexOf('coca cola') > -1 && (nClean.indexOf('manaos') > -1 || nClean.indexOf('pepsi') > -1 || nClean.indexOf('secco') > -1)) continue;
    if (qStr.indexOf('manaos') > -1 && (nClean.indexOf('coca cola') > -1 || nClean.indexOf('pepsi') > -1 || nClean.indexOf('sprite') > -1 || nClean.indexOf('fanta') > -1)) continue;
    if (qStr.indexOf('sprite') > -1 && (nClean.indexOf('manaos') > -1 || nClean.indexOf('coca cola') > -1 || nClean.indexOf('7up') > -1)) continue;
    if (qStr.indexOf('gallo') > -1 && (nClean.indexOf('lucchetti') > -1 || nClean.indexOf('ala') > -1)) continue;
    if (qStr.indexOf('lucchetti') > -1 && (nClean.indexOf('gallo') > -1 || nClean.indexOf('ala') > -1 || nClean.indexOf('matarazzo') > -1)) continue;
    if (qStr.indexOf('matarazzo') > -1 && (nClean.indexOf('lucchetti') > -1 || nClean.indexOf('barilla') > -1 || nClean.indexOf('favorita') > -1)) continue;
    if (qStr.indexOf('serenisima') > -1 && (nClean.indexOf('tregar') > -1 || nClean.indexOf('ilolay') > -1)) continue;
    if (qStr.indexOf('tregar') > -1 && (nClean.indexOf('serenisima') > -1 || nClean.indexOf('ilolay') > -1)) continue;
    if (qStr.indexOf('cocinero') > -1 && (nClean.indexOf('natura') > -1 || nClean.indexOf('canuelas') > -1)) continue;
    if (qStr.indexOf('natura') > -1 && (nClean.indexOf('cocinero') > -1 || nClean.indexOf('canuelas') > -1)) continue;
    if (qStr.indexOf('playadito') > -1 && (nClean.indexOf('taragui') > -1 || nClean.indexOf('rosamonte') > -1)) continue;
    if (qStr.indexOf('taragui') > -1 && (nClean.indexOf('playadito') > -1 || nClean.indexOf('rosamonte') > -1)) continue;

    // Descartar Zero / Light si la consulta busca sabor regular / original
    if (qStr.indexOf('coca cola') > -1 && qStr.indexOf('zero') === -1 && qStr.indexOf('light') === -1 && qStr.indexOf('diet') === -1 && qStr.indexOf('sin azucar') === -1) {
        if (nClean.indexOf('zero') > -1 || nClean.indexOf('light') > -1 || nClean.indexOf('diet') > -1 || nClean.indexOf('sin azucar') > -1) continue;
    }
    if (qStr.indexOf('sprite') > -1 && qStr.indexOf('zero') === -1 && qStr.indexOf('sin azucar') === -1) {
        if (nClean.indexOf('zero') > -1 || nClean.indexOf('sin azucar') > -1) continue;
    }

    // Reglas estrictas de variantes y sabores (Manaos, etc.)
    if (qStr.indexOf('naranja') > -1) {
        if (nClean.indexOf('naranja') === -1) continue;
        if (nClean.indexOf('cola') > -1 || nClean.indexOf('pomelo') > -1 || nClean.indexOf('lima') > -1 || nClean.indexOf('limon') > -1 || nClean.indexOf('guarana') > -1 || nClean.indexOf('tonica') > -1) continue;
    }
    if (qStr.indexOf('cola') > -1 && qStr.indexOf('coca') === -1) {
        if (nClean.indexOf('cola') === -1) continue;
        if (nClean.indexOf('naranja') > -1 || nClean.indexOf('pomelo') > -1 || nClean.indexOf('lima') > -1 || nClean.indexOf('limon') > -1 || nClean.indexOf('guarana') > -1 || nClean.indexOf('tonica') > -1) continue;
    }
    if ((qStr.indexOf('lima') > -1 || qStr.indexOf('limon') > -1) && qStr.indexOf('sprite') === -1) {
        if (nClean.indexOf('lima') === -1 && nClean.indexOf('limon') === -1) continue;
        if (nClean.indexOf('cola') > -1 || nClean.indexOf('naranja') > -1 || nClean.indexOf('pomelo') > -1 || nClean.indexOf('guarana') > -1 || nClean.indexOf('tonica') > -1) continue;
    }

    var score = 0;
    if (nClean.indexOf('sabor original') > -1 || nClean.indexOf('original') > -1) score += 150;
    if (qStr.indexOf('naranja') > -1 && nClean.indexOf('naranja') > -1) score += 200;
    if (qStr.indexOf('cola') > -1 && nClean.indexOf('cola') > -1) score += 200;
    if ((qStr.indexOf('lima') > -1 || qStr.indexOf('limon') > -1) && (nClean.indexOf('lima') > -1 || nClean.indexOf('limon') > -1)) score += 200;
    if (nClean.indexOf(qStr) > -1) score += 100;
    for (var w = 0; w < qWords.length; w++) {
        if (nClean.indexOf(qWords[w]) > -1) score += 20;
    }
    if (score <= 0) continue;
    if ((qStr.indexOf('gaseosa') > -1 || qStr.indexOf('bebida') > -1) && (nClean.indexOf('shampoo') > -1 || nClean.indexOf('xkg') > -1)) {
        score -= 200;
    }
    if (unavail) score -= 10;

    candidates.push({
        name: nameVal,
        price: priceVal,
        url: urlVal,
        stock: unavail ? 'SIN STOCK' : 'DISPONIBLE',
        score: score
    });
}

if (candidates.length === 0) return 'null';
candidates.sort(function(a, b) { return b.score - a.score; });
return JSON.stringify(candidates[0]);
dom finish

js var ctData = null; try { ctData = JSON.parse(dom_result); } catch(e){}
js if (ctData) { coto_nom = ctData.name; coto_pre = ctData.price; coto_url = ctData.url; coto_stock = ctData.stock; }
echo [SUPERMERCADO 2] Extraído: `coto_nom` | `coto_pre` | `coto_stock`
echo [SUPERMERCADO 2] Finalizado.
write `csv_row([modo_actual, producto, coto_nom, coto_pre, "COTO", coto_url, fechaHoy, coto_stock, cant_actual, unid_actual])` to resultados.csv


// ==============================================================================
// 3. CONSULTA EN DÍA %
// ==============================================================================
echo [SUPERMERCADO 3] Abriendo navegador...
echo [SUPERMERCADO 3] Navegando a https://diaonline.supermercadosdia.com.ar...
https://diaonline.supermercadosdia.com.ar
wait 3

// Cierre de modales/cookies si estuviera presente
if present('Aceptar todo')
    click Aceptar todo
    wait 1
if present('Aceptar')
    click Aceptar
    wait 1

echo [SUPERMERCADO 3] Localizando buscador y escribiendo producto: `query_term`...
if present('input#downshift-0-input')
    type input#downshift-0-input as [clear]`query_term`
else if present('input[placeholder*="busc"]')
    type input[placeholder*="busc"] as [clear]`query_term`
else if present('input.vtex-styleguide-9-x-input')
    type input.vtex-styleguide-9-x-input as [clear]`query_term`
wait 2

echo [SUPERMERCADO 3] Seleccionando 'Ver todos los productos' mediante TagUI...
if present('Ver todos los productos')
    click Ver todos los productos
else if present('//*[contains(text(), "Ver todos los productos")]')
    click //*[contains(text(), "Ver todos los productos")]
else if present('button[aria-label="Buscar Productos"]')
    click button[aria-label="Buscar Productos"]
wait 2

// Carga directa del catálogo de resultados de Día % según query_term
js chrome_step('Page.navigate', {url: 'https://diaonline.supermercadosdia.com.ar/' + encodeURIComponent(query_term) + '?map=ft&_q=' + encodeURIComponent(query_term)});
wait 4

echo [SUPERMERCADO 3] Extrayendo resultados...
dia_nom = "No encontrado"
dia_pre = "N/D"
dia_url = url()
dia_stock = "NO ENCONTRADO"

dom begin
function cleanText(s) {
    if (!s) return '';
    return s.toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '').replace(/[\.,;:!¡?¿\(\)\[\]"'\-_/]/g, ' ').replace(/\s+/g, ' ').trim();
}

var qStr = cleanText("`producto`");
var qWords = qStr.split(/\s+/).filter(function(w){ return w.length >= 2; });

var dCards = Array.from(document.querySelectorAll('[class*="galleryItem"]'));
if (dCards.length === 0) dCards = Array.from(document.querySelectorAll('article'));
if (dCards.length === 0) dCards = Array.from(document.querySelectorAll('section[class*="product-summary"]'));
if (dCards.length === 0) return 'null';

var incompatibles = ['arrocera', 'olla', 'vaporera', 'electrodomestico', 'jabon', 'shampoo', 'perro', 'gato', 'juguete', 'vela', 'taza', 'vaso', 'termo', 'alimento para perro', 'alimento para gato'];

var candidates = [];
for (var i = 0; i < dCards.length; i++) {
    var c = dCards[i];
    var nEl = c.querySelector('h3, [class*="productBrand"]');
    var pEl = c.querySelector('[class*="sellingPriceValue"], [class*="sellingPrice"], [class*="price_sellingPrice"], [class*="currencyContainer"]');
    var lEl = c.querySelector('a[href*="/p"]') || c.querySelector('a');
    if (!nEl) continue;

    var nameVal = nEl.innerText.trim();
    if (!nameVal) continue;
    var priceVal = 'N/D';
    if (pEl) {
        priceVal = pEl.innerText.replace(/\n/g, ' ').replace(/\s+/g, ' ').trim();
    } else {
        var lines = c.innerText.split('\n').filter(function(s){ return s.trim().length > 0; });
        for (var l = 0; l < lines.length; l++) {
            if (lines[l].indexOf('$') > -1) { priceVal = lines[l].trim(); break; }
        }
    }
    var urlVal = lEl ? lEl.href : window.location.href;

    var cardText = (c.innerText || '').toLowerCase();
    var unavail = cardText.indexOf('agotado') > -1 || cardText.indexOf('sin stock') > -1 || cardText.indexOf('no disponible') > -1;
    if (priceVal === 'N/D' || priceVal === '' || priceVal === '$ 0' || priceVal === '$ 0,00') unavail = true;

    var nClean = cleanText(nameVal);

    var tieneInc = false;
    for (var k = 0; k < incompatibles.length; k++) {
        if (nClean.indexOf(incompatibles[k]) > -1 && qStr.indexOf(incompatibles[k]) === -1) {
            tieneInc = true;
            break;
        }
    }
    if (tieneInc) continue;

    // Reglas estrictas de marca del catálogo
    if (qStr.indexOf('coca cola') > -1 && (nClean.indexOf('manaos') > -1 || nClean.indexOf('pepsi') > -1 || nClean.indexOf('secco') > -1)) continue;
    if (qStr.indexOf('manaos') > -1 && (nClean.indexOf('coca cola') > -1 || nClean.indexOf('pepsi') > -1 || nClean.indexOf('sprite') > -1 || nClean.indexOf('fanta') > -1)) continue;
    if (qStr.indexOf('sprite') > -1 && (nClean.indexOf('manaos') > -1 || nClean.indexOf('coca cola') > -1 || nClean.indexOf('7up') > -1)) continue;
    if (qStr.indexOf('gallo') > -1 && (nClean.indexOf('lucchetti') > -1 || nClean.indexOf('ala') > -1)) continue;
    if (qStr.indexOf('lucchetti') > -1 && (nClean.indexOf('gallo') > -1 || nClean.indexOf('ala') > -1 || nClean.indexOf('matarazzo') > -1)) continue;
    if (qStr.indexOf('matarazzo') > -1 && (nClean.indexOf('lucchetti') > -1 || nClean.indexOf('barilla') > -1 || nClean.indexOf('favorita') > -1)) continue;
    if (qStr.indexOf('serenisima') > -1 && (nClean.indexOf('tregar') > -1 || nClean.indexOf('ilolay') > -1)) continue;
    if (qStr.indexOf('tregar') > -1 && (nClean.indexOf('serenisima') > -1 || nClean.indexOf('ilolay') > -1)) continue;
    if (qStr.indexOf('cocinero') > -1 && (nClean.indexOf('natura') > -1 || nClean.indexOf('canuelas') > -1)) continue;
    if (qStr.indexOf('natura') > -1 && (nClean.indexOf('cocinero') > -1 || nClean.indexOf('canuelas') > -1)) continue;
    if (qStr.indexOf('playadito') > -1 && (nClean.indexOf('taragui') > -1 || nClean.indexOf('rosamonte') > -1)) continue;
    if (qStr.indexOf('taragui') > -1 && (nClean.indexOf('playadito') > -1 || nClean.indexOf('rosamonte') > -1)) continue;

    // Descartar Zero / Light si la consulta busca sabor regular / original
    if (qStr.indexOf('coca cola') > -1 && qStr.indexOf('zero') === -1 && qStr.indexOf('light') === -1 && qStr.indexOf('diet') === -1 && qStr.indexOf('sin azucar') === -1) {
        if (nClean.indexOf('zero') > -1 || nClean.indexOf('light') > -1 || nClean.indexOf('diet') > -1 || nClean.indexOf('sin azucar') > -1) continue;
    }
    if (qStr.indexOf('sprite') > -1 && qStr.indexOf('zero') === -1 && qStr.indexOf('sin azucar') === -1) {
        if (nClean.indexOf('zero') > -1 || nClean.indexOf('sin azucar') > -1) continue;
    }

    // Reglas estrictas de variantes y sabores (Manaos, etc.)
    if (qStr.indexOf('naranja') > -1) {
        if (nClean.indexOf('naranja') === -1) continue;
        if (nClean.indexOf('cola') > -1 || nClean.indexOf('pomelo') > -1 || nClean.indexOf('lima') > -1 || nClean.indexOf('limon') > -1 || nClean.indexOf('guarana') > -1 || nClean.indexOf('tonica') > -1) continue;
    }
    if (qStr.indexOf('cola') > -1 && qStr.indexOf('coca') === -1) {
        if (nClean.indexOf('cola') === -1) continue;
        if (nClean.indexOf('naranja') > -1 || nClean.indexOf('pomelo') > -1 || nClean.indexOf('lima') > -1 || nClean.indexOf('limon') > -1 || nClean.indexOf('guarana') > -1 || nClean.indexOf('tonica') > -1) continue;
    }
    if ((qStr.indexOf('lima') > -1 || qStr.indexOf('limon') > -1) && qStr.indexOf('sprite') === -1) {
        if (nClean.indexOf('lima') === -1 && nClean.indexOf('limon') === -1) continue;
        if (nClean.indexOf('cola') > -1 || nClean.indexOf('naranja') > -1 || nClean.indexOf('pomelo') > -1 || nClean.indexOf('guarana') > -1 || nClean.indexOf('tonica') > -1) continue;
    }

    var score = 0;
    if (nClean.indexOf('sabor original') > -1 || nClean.indexOf('original') > -1) score += 150;
    if (qStr.indexOf('naranja') > -1 && nClean.indexOf('naranja') > -1) score += 200;
    if (qStr.indexOf('cola') > -1 && nClean.indexOf('cola') > -1) score += 200;
    if ((qStr.indexOf('lima') > -1 || qStr.indexOf('limon') > -1) && (nClean.indexOf('lima') > -1 || nClean.indexOf('limon') > -1)) score += 200;
    if (nClean.indexOf(qStr) > -1) score += 100;
    for (var w = 0; w < qWords.length; w++) {
        if (nClean.indexOf(qWords[w]) > -1) score += 20;
    }
    if (score <= 0) continue;
    if ((qStr.indexOf('gaseosa') > -1 || qStr.indexOf('bebida') > -1) && (nClean.indexOf('shampoo') > -1 || nClean.indexOf('xkg') > -1)) {
        score -= 200;
    }
    if (unavail) score -= 10;

    candidates.push({
        name: nameVal,
        price: priceVal,
        url: urlVal,
        stock: unavail ? 'SIN STOCK' : 'DISPONIBLE',
        score: score
    });
}

if (candidates.length === 0) return 'null';
candidates.sort(function(a, b) { return b.score - a.score; });
return JSON.stringify(candidates[0]);
dom finish

js var dData = null; try { dData = JSON.parse(dom_result); } catch(e){}
js if (dData) { dia_nom = dData.name; dia_pre = dData.price; dia_url = dData.url; dia_stock = dData.stock; }
echo [SUPERMERCADO 3] Extraído: `dia_nom` | `dia_pre` | `dia_stock`
echo [SUPERMERCADO 3] Finalizado.
write `csv_row([modo_actual, producto, dia_nom, dia_pre, "Día %", dia_url, fechaHoy, dia_stock, cant_actual, unid_actual])` to resultados.csv

echo ----------------------------------------------------------------------------
echo [ RPA FINALIZADO ]
echo 3 supermercados procesados.
echo Resultados guardados en resultados.csv.
echo ----------------------------------------------------------------------------
