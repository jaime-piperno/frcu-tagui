// Adaptador de MercadoLibre Argentina. Los datos inciertos requieren revisión.
(function () {
  return {
    selectors: {
      input: 'input[name="as_word"], input.nav-search-input',
      submit: 'button.nav-search-btn, button[type="submit"].nav-search-btn',
      sort: '.ui-search-sort-filter__dropdown button[role="combobox"], .ui-search-sort-filter button, .ui-search-sort-filter [role="combobox"]',
      price_asc: '[role="listbox"] [role="option"][data-key="price_asc"], .andes-list__item, .ui-search-sort-filter a[href]',
      next: 'a.andes-pagination__link[data-andes-pagination-control="next"], a.andes-pagination__link[title="Siguiente"], a[rel="next"]'
    },

    // Estas funciones se ejecutan aisladas en Chrome mediante toString().
    sort_order: function () {
      if (location.hostname !== 'listado.mercadolibre.com.ar' ||
          !/_OrderId_PRICE(?:_Desde_[1-9]\d*)?(?:_NoIndex_True)?\/?$/.test(location.pathname)) return null;
      var controls = document.querySelectorAll('.ui-search-sort-filter__dropdown button[role="combobox"], .ui-search-sort-filter button, .ui-search-sort-filter [role="combobox"]');
      for (var i = 0; i < controls.length; i++) {
        var el = controls[i], label = (el.getAttribute('aria-label') || el.innerText || el.textContent || '').replace(/\s+/g, ' ').trim();
        if (el.getClientRects().length && getComputedStyle(el).visibility !== 'hidden' &&
            /^(?:Ordenar por\s*)?Menor precio$/i.test(label)) return 'price_asc';
      }
      return null;
    },

    blocked: function () {
      // No basta encontrar "recaptcha" en un script: debe existir un desafío.
      function visible(el) {
        return !!el && el.getClientRects().length > 0 && getComputedStyle(el).visibility !== 'hidden';
      }
      var body = document.body ? (document.body.innerText || '') : '';
      var path = location.pathname || '';
      if (/\/(?:captcha|account-verification|gz|login|registration)(?:\/|$)/i.test(path) ||
          visible(document.querySelector('form[action*="/login"] input[type="password"]')) ||
          /\b(?:re)?captcha\b|verific[aá] que no (?:eres|sos) un robot|por seguridad, complet[aá] este paso|ingres[aá] el c[oó]digo|acceso denegado|hubo un error accediendo|access denied|\b403 forbidden\b/i.test(document.title + ' ' + body.slice(0, 1500))) return true;
      var challenges = document.querySelectorAll('iframe[src*="recaptcha"][src*="/anchor"], iframe[src*="recaptcha"][src*="/bframe"], iframe[src*="hcaptcha"], .g-recaptcha, .h-captcha');
      for (var i = 0; i < challenges.length; i++) {
        var bounds = challenges[i].getBoundingClientRect();
        if (visible(challenges[i]) && bounds.width > 1 && bounds.height > 1 &&
            !challenges[i].closest('.grecaptcha-badge, [data-size="invisible"]')) return true;
      }
      return false;
    },

    ready: function (detail) {
      function visible(el) {
        return !!el && el.getClientRects().length > 0 && getComputedStyle(el).visibility !== 'hidden';
      }
      if (document.readyState === 'loading') return false;
      if (detail) {
        var title = document.querySelector('h1.ui-pdp-title, h1');
        var nodes = document.querySelectorAll('.ui-pdp-price, .ui-pdp-stock-information, .ui-pdp-buybox__quantity__available');
        if (!visible(title)) return false;
        for (var i = 0; i < nodes.length; i++) if (visible(nodes[i])) return true;
        return false;
      }
      var cards = document.querySelectorAll('li.ui-search-layout__item, .poly-card, .ui-search-result');
      for (var j = 0; j < cards.length; j++) {
        if (visible(cards[j]) && cards[j].querySelector('a.poly-component__title, h2 a.ui-search-link, a.ui-search-item__group__element')) return true;
      }
      var body = document.body ? (document.body.innerText || document.body.textContent || '') : '';
      return /no encontramos publicaciones|no hay publicaciones|ning[uú]n resultado|0 resultados/i.test(body);
    },

    extract: function (detail) {
      function text(el) {
        return el ? (el.innerText || el.textContent || '').replace(/\s+/g, ' ').trim() : '';
      }
      function visible(el) {
        return !!el && el.getClientRects().length > 0 && getComputedStyle(el).visibility !== 'hidden';
      }
      function norm(value) {
        return String(value || '').toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '').replace(/[^a-z0-9]+/g, ' ').trim();
      }
      function positive(value) {
        if (typeof value !== 'number' || !isFinite(value) || value <= 0) return null;
        return value;
      }
      function structuredNumber(value) {
        // JSON-LD usa punto decimal, nunca separador argentino de miles.
        if (typeof value === 'number') return positive(value);
        if (typeof value !== 'string' || !/^\d+(?:\.\d+)?$/.test(value.trim())) return null;
        return positive(Number(value));
      }
      function stock(value) {
        if (/\/(?:InStock|LimitedAvailability)\/?$/.test(String(value || ''))) return true;
        if (/\/(?:OutOfStock|SoldOut|Discontinued)\/?$/.test(String(value || ''))) return false;
        return null;
      }
      function combine(first, second) {
        if (first === null) return second;
        if (second === null) return first;
        return first === second ? first : null;
      }
      function visibleStock(root, isDetail) {
        var selectors = isDetail ?
          '.ui-pdp-stock-information, .ui-pdp-buybox__quantity__available, .ui-pdp-buybox' :
          '.poly-component__stock, .ui-search-item__stock, .ui-search-item__group__element--stock';
        var nodes = root.querySelectorAll(selectors), positiveStock = false, negativeStock = false;
        for (var i = 0; i < nodes.length; i++) {
          if (!visible(nodes[i])) continue;
          var label = text(nodes[i]);
          if (/sin stock|agotado|publicaci[oó]n pausada|no disponible|\b0\s+(?:unidades?\s+)?disponibles?\b/i.test(label)) negativeStock = true;
          if (/stock disponible|[uú]ltima disponible|\b[1-9]\d*\s+(?:unidades?\s+)?disponibles?\b/i.test(label)) positiveStock = true;
        }
        // El rótulo de agotado puede estar fuera del bloque habitual de stock.
        if (!isDetail && /sin stock|agotado|publicaci[oó]n pausada|no disponible/i.test(text(root))) negativeStock = true;
        return positiveStock && negativeStock ? 'conflict' : negativeStock ? false : positiveStock ? true : null;
      }
      function add(prices, amount, method) {
        if (amount === null) return;
        for (var i = 0; i < prices.length; i++) if (prices[i].amount === amount) return;
        prices.push({amount: amount, method: method || 'Precio publicado', currency: 'ARS'});
      }
      function currency(node) {
        var explicit = node.getAttribute('data-currency-id') || node.getAttribute('data-currency');
        var meta = node.querySelector('[itemprop="priceCurrency"]');
        if (meta) explicit = meta.getAttribute('content') || text(meta);
        var symbol = text(node.querySelector('.andes-money-amount__currency-symbol'));
        if (/^(?:U\$S|US\$|USD)$/i.test(symbol)) return 'USD';
        // priceCurrency también puede ser un span con "$", no un código ISO.
        if (explicit && !/^(?:\$|AR\$)$/.test(String(explicit).trim())) return String(explicit).toUpperCase().trim();
        // En el sitio argentino el símbolo local de estas tarjetas es el peso.
        if ((symbol === '$' || symbol === 'AR$' || symbol === 'ARS' || explicit === '$' || explicit === 'AR$') &&
            /(?:^|\.)mercadolibre\.com\.ar$/i.test(location.hostname)) return 'ARS';
        return '';
      }
      function visiblePrices(root) {
        var prices = [], nodes = root.querySelectorAll('.andes-money-amount');
        // "compact" es solo estilo: también se usa en el precio principal.
        var excluded = 's, del, .andes-money-amount--previous, .ui-pdp-price__original-value, .poly-installments, [class*="installment"], [class*="cuota"], .ui-pdp-price__subtitles, [id$="price_subtitle"]';
        for (var i = 0; i < nodes.length; i++) {
          var node = nodes[i];
          if (!visible(node) || node.closest(excluded) || currency(node) !== 'ARS') continue;
          var fraction = node.querySelector('.andes-money-amount__fraction');
          var cents = node.querySelector('.andes-money-amount__cents');
          if (!visible(fraction) || fraction.closest(excluded)) continue;
          var whole = text(fraction), decimal = visible(cents) ? text(cents) : '';
          if (!/^(?:\d+|\d{1,3}(?:\.\d{3})+)$/.test(whole) || (decimal && !/^\d{1,2}$/.test(decimal))) continue;
          add(prices, positive(Number(whole.replace(/\./g, '')) + (decimal ? Number(decimal) / 100 : 0)));
        }
        return prices;
      }
      function cardPrices(root) {
        var scope = root.querySelector('.poly-price__current') || root.querySelector('.poly-component__price') || root;
        return visiblePrices(scope);
      }
      function productsLD() {
        var products = [];
        function visit(value) {
          if (Array.isArray(value)) { value.forEach(visit); return; }
          if (!value || typeof value !== 'object') return;
          if (value['@type'] === 'Product' || Array.isArray(value['@type']) && value['@type'].indexOf('Product') >= 0) products.push(value);
          if (value['@graph']) visit(value['@graph']);
        }
        var scripts = document.querySelectorAll('script[type="application/ld+json"]');
        for (var i = 0; i < scripts.length; i++) {
          try { visit(JSON.parse(scripts[i].textContent)); } catch (e) { /* Un JSON inválido no confirma una oferta. */ }
        }
        return products;
      }
      function idFromUrl(url) {
        var match = String(url).match(/MLA-?(\d+)/i);
        return match ? 'MLA' + match[1] : '';
      }
      function oneCard(title, url, id, sku, available, prices, variantUnconfirmed) {
        if (available !== true && available !== false) available = null;
        return {
          title: title, url: url, product_id: String(id || ''),
          variants: [{variant_id: '', title: title, sku: String(sku || ''),
            available: available, prices: prices}],
          available: available, prices: prices, variant_unconfirmed: !!variantUnconfirmed
        };
      }
      var body = document.body ? (document.body.innerText || '') : '', cards = [], hidden = 0;
      var path = location.pathname || '', blockType = '';
      var message = document.title + ' ' + body.slice(0, 1500);
      var challenges = document.querySelectorAll('iframe[src*="recaptcha"][src*="/anchor"], iframe[src*="recaptcha"][src*="/bframe"], iframe[src*="hcaptcha"], .g-recaptcha, .h-captcha');
      for (var b = 0; b < challenges.length; b++) {
        var bounds = challenges[b].getBoundingClientRect();
        if (visible(challenges[b]) && bounds.width > 1 && bounds.height > 1 &&
            !challenges[b].closest('.grecaptcha-badge, [data-size="invisible"]')) blockType = 'captcha';
      }
      if (/\/captcha(?:\/|$)/i.test(path) || /\b(?:re)?captcha\b|verific[aá] que no (?:eres|sos) un robot|por seguridad, complet[aá] este paso/i.test(message)) blockType = 'captcha';
      if (!blockType && (/\/(?:account-verification|login|registration)(?:\/|$)/i.test(path) ||
          visible(document.querySelector('form[action*="/login"] input[type="password"]')) ||
          /ingres[aá] el c[oó]digo/i.test(message))) blockType = 'login_requerido';
      if (!blockType && (/\/gz(?:\/|$)/i.test(path) ||
          /acceso denegado|hubo un error accediendo|access denied|\b403 forbidden\b/i.test(message))) blockType = 'acceso_denegado';
      // Nunca conserva contenido de una verificación, que puede contener datos personales.
      if (blockType) {
        var reasons = {captcha: 'El sitio solicita completar un CAPTCHA manualmente.',
          login_requerido: 'El sitio solicita iniciar sesión o verificar la cuenta.',
          acceso_denegado: 'El sitio denegó el acceso; no se confirmó un CAPTCHA resoluble.'};
        return {capture_version: 1, url: location.href, title: document.title, status: 'bloqueado',
          block_type: blockType, reason: reasons[blockType],
          cards: [], next: null, load_more: false, pagination: [], hidden_products: 0,
          diagnostic: reasons[blockType],
          captured_at: new Date().toISOString()};
      }
      if (detail) {
        var heading = document.querySelector('h1.ui-pdp-title, h1'), title = text(heading);
        if (title && visible(heading)) {
          // El stock debe corresponder a la oferta principal, no a otros vendedores.
          var prices = [], mainPriceRoots = document.querySelectorAll('.ui-pdp-price--size-large');
          var priceRoots = Array.prototype.filter.call(mainPriceRoots.length ? mainPriceRoots : document.querySelectorAll('.ui-pdp-price'), visible);
          if (priceRoots.length !== 1) priceRoots = [];
          for (var p = 0; p < priceRoots.length; p++) {
            if (!visible(priceRoots[p])) continue;
            var found = visiblePrices(priceRoots[p]);
            var method = /con\s+cup[oó]n/i.test(text(priceRoots[p])) ? 'Precio publicado con cupón' : 'Precio publicado';
            for (var n = 0; n < found.length; n++) add(prices, found[n].amount, method);
          }
          var available = visibleStock(document, true), sku = '', id = idFromUrl(location.href);
          var metaCurrency = document.querySelector('meta[itemprop="priceCurrency"], meta[property="product:price:currency"]');
          if (metaCurrency && String(metaCurrency.getAttribute('content') || '').toUpperCase() !== 'ARS') prices = [];
          var products = productsLD();
          for (var j = 0; j < products.length; j++) {
            var product = products[j];
            // Una recomendación puede tener su propio Product: debe coincidir con el h1.
            if (norm(product.name) !== norm(title)) continue;
            sku = String(product.sku || '').trim();
            id = String(product.productID || id || sku);
            var offers = Array.isArray(product.offers) ? product.offers : [product.offers];
            var matchedStock = null, foundOffer = false, stockConflict = false, unsupportedCurrency = false;
            for (var o = 0; o < offers.length; o++) {
              var offer = offers[o];
              if (!offer) continue;
              if (String(offer.priceCurrency || '').toUpperCase() !== 'ARS') { unsupportedCurrency = true; continue; }
              var amount = structuredNumber(offer.price), matches = false;
              for (var v = 0; v < prices.length; v++) if (amount !== null && Math.abs(prices[v].amount - amount) < .005) matches = true;
              if (!matches) continue;
              var offerStock = stock(offer.availability);
              if (foundOffer && matchedStock !== null && offerStock !== null && matchedStock !== offerStock) stockConflict = true;
              matchedStock = combine(matchedStock, offerStock);
              foundOffer = true;
            }
            if (unsupportedCurrency && !foundOffer) prices = [];
            if (foundOffer) available = stockConflict ? null : combine(available, matchedStock);
            break;
          }
          var variants = document.querySelectorAll('.ui-pdp-variations, .ui-pdp-variations__attribute'), variantUnconfirmed = false;
          for (var k = 0; k < variants.length; k++) if (visible(variants[k])) variantUnconfirmed = true;
          // Sin precio vinculado a cada opción, la variante requiere revisión.
          if (variantUnconfirmed) available = null;
          cards.push(oneCard(title, location.href, id, sku, available, prices, variantUnconfirmed));
        }
      } else {
        var nodes = document.querySelectorAll('li.ui-search-layout__item, .poly-card, .ui-search-result'), seen = {};
        for (var c = 0; c < nodes.length; c++) {
          var el = nodes[c];
          if (!visible(el)) { hidden++; continue; }
          var link = el.querySelector('a.poly-component__title, h2 a.ui-search-link, a.ui-search-item__group__element');
          var label = text(link);
          if (!link || !visible(link) || !label || !link.href || seen[link.href]) continue;
          // Excluir enlaces publicitarios que no llevan directamente a una ficha.
          var target;
          try { target = new URL(link.href); } catch (_) { continue; }
          if (target.protocol !== 'https:' || target.username || target.password ||
              (target.port && target.port !== '443') ||
              !/^(www|articulo)\.mercadolibre\.com\.ar$/.test(target.hostname)) continue;
          var condition = el.querySelector('.poly-component__condition, .ui-search-item__group__element--item-condition');
          if (visible(condition) && /\busado\b/i.test(text(condition))) continue;
          if (/^(vaso|shaker|remera|botella|pastillero|scoop)\b/i.test(label)) continue;
          var card = oneCard(label, link.href, idFromUrl(link.href), '', visibleStock(el, false), cardPrices(el), false);
          card.html = el.outerHTML.slice(0, 1500);
          cards.push(card);
          seen[link.href] = true;
        }
      }
      var empty = /no encontramos publicaciones|no hay publicaciones|ning[uú]n resultado|0 resultados/i.test(body);
      var next = detail ? null : document.querySelector('a.andes-pagination__link[data-andes-pagination-control="next"], a.andes-pagination__link[title="Siguiente"], a[rel="next"]');
      var selected = detail ? null : document.querySelector('.andes-pagination [aria-current="page"], .andes-pagination [data-andes-state="selected"], .andes-pagination__button--current');
      var pageNumber = visible(selected) && /^\d+$/.test(text(selected)) ? Number(text(selected)) : null;
      var nextUrl = null, nextPage = null, paginationProblem = false, pagination = [];
      if (visible(next)) {
        pagination.push((next.closest('li') || next).outerHTML.slice(0, 2000));
        var disabled = next.hasAttribute('disabled') || next.getAttribute('aria-disabled') === 'true' ||
          next.closest('[aria-disabled="true"], [data-andes-state="disabled"], .andes-pagination__button--disabled');
        if (!disabled) {
          var raw = (next.getAttribute('href') || '').trim();
          // Sin href, la página activa identifica el avance del botón JavaScript.
          if (!raw || raw.charAt(0) === '#' || next.href.split('#')[0] === location.href.split('#')[0]) {
            if (pageNumber > 0) nextPage = pageNumber + 1;
            else paginationProblem = true;
          } else if (/^https:\/\/listado\.mercadolibre\.com\.ar\//.test(next.href)) nextUrl = next.href;
          else paginationProblem = true;
        }
      }
      if (visible(selected)) pagination.push((selected.closest('li') || selected).outerHTML.slice(0, 1000));
      return {
        capture_version: 1, url: location.href, title: document.title,
        status: paginationProblem ? 'busqueda_incompleta' : cards.length ? 'ok' : !detail && empty ? 'no_encontrado' : 'error_extraccion',
        cards: cards, next: nextUrl, next_page: nextPage, page_number: pageNumber, load_more: false,
        pagination: pagination, hidden_products: hidden,
        diagnostic: paginationProblem ? 'El siguiente está habilitado, pero no se pudo verificar su destino o página activa.' : cards.length ? '' : 'No se pudo reconocer el contenido esperado.',
        captured_at: new Date().toISOString()
      };
    }
  };
})()
