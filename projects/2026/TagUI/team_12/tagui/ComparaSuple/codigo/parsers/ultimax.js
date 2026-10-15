(function () {
  return {
    selectors: {
      input: '#searchbox',
      submit: 'form[action="/buscar"] button[type=submit]',
      login_input: 'form[action="/__acceso"] input[type=password][name=password]',
      login_submit: 'form[action="/__acceso"] button[type=submit]'
    },
    extract: function (detail) {
      function text(el) {
        return el ? (el.innerText || el.textContent || '').replace(/\s+/g, ' ').trim() : '';
      }
      function visible(el) {
        return !!el && el.getClientRects().length > 0 && getComputedStyle(el).visibility !== 'hidden';
      }
      function enabled(el) {
        return visible(el) && !el.hasAttribute('disabled') && el.getAttribute('aria-disabled') !== 'true' &&
          !el.closest('[aria-disabled="true"], .disabled');
      }
      function money(value) {
        if (typeof value === 'boolean' || value === null || value === undefined) return null;
        if (typeof value === 'number') return value > 0 && isFinite(value) ? value : null;
        var s = String(value).replace(/[$\s\u00a0]/g, '');
        if (s.indexOf(',') >= 0) s = s.replace(/\./g, '').replace(',', '.');
        else if (/^\d{1,3}(\.\d{3})+$/.test(s)) s = s.replace(/\./g, '');
        var amount = Number(s);
        return amount > 0 && isFinite(amount) ? amount : null;
      }
      function norm(s) {
        return String(s || '').toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '').replace(/[^a-z0-9]+/g, ' ').trim();
      }
      function price(el) {
        var node = el.querySelector('.pr'), note = el.querySelector('.pr-note');
        var label = visible(note) ? text(note) : '';
        if (!visible(node) || node.closest('del,s') || /cuotas?|mensual/i.test(label)) return [];
        var amount = money(text(node));
        if (amount === null) return [];
        return [{amount: amount, method: /efectivo/i.test(label) ? 'Efectivo' :
          /transferencia/i.test(label) ? 'Transferencia' : 'Precio publicado', currency: 'ARS'}];
      }
      function publishedStock(el, isDetail) {
        var status = el.querySelector(isDetail ? '.pdp-qty-stock' : '.badge.ya');
        var label = visible(status) ? text(status) : '';
        if (/sin stock|agotado|no disponible|^0\s+disponibles/i.test(label)) return false;
        if (isDetail) {
          var button = el.querySelector('#addbtn');
          // Un botón habilitado por sí solo no demuestra que haya unidades.
          if (/\b[1-9]\d*\s+disponibles\b/i.test(label) && visible(button) && !button.disabled &&
              button.getAttribute('aria-disabled') !== 'true') return true;
          var chip = el.querySelector('.chip');
          if (visible(chip) && /entrega inmediata|entrega ya/i.test(text(chip)) && enabled(button)) return true;
        } else if (/entrega ya|entrega inmediata/i.test(label)) return true;
        return null;
      }
      function jsonProducts() {
        var found = [];
        function visit(value) {
          if (Array.isArray(value)) { value.forEach(visit); return; }
          if (!value || typeof value !== 'object') return;
          var type = value['@type'];
          if (type === 'Product' || Array.isArray(type) && type.indexOf('Product') >= 0) found.push(value);
          if (value['@graph']) visit(value['@graph']);
        }
        Array.prototype.forEach.call(document.querySelectorAll('script[type="application/ld+json"]'), function (node) {
          try { visit(JSON.parse(node.textContent)); } catch (e) { /* JSON-LD roto no confirma la oferta. */ }
        });
        return found;
      }
      if (document.querySelector('form[action="/__acceso"] input[type=password]')) {
        return {capture_version: 1, url: location.href, title: document.title, status: 'error_auth',
          cards: [], next: null, load_more: false, pagination: [], captured_at: new Date().toISOString()};
      }
      var body = text(document.body), cards = [];
      var blocked = /access denied|verify you are human|verifica que eres humano|just a moment|captcha|too many requests/i.test(document.title + ' ' + body.slice(0, 1200));
      if (detail) {
        var name = document.querySelector('h1'), title = text(name), container = name && name.parentElement;
        if (title && visible(name) && container) {
          var prices = price(container), available = publishedStock(container, true), sku = '', productId = '';
          var products = jsonProducts();
          for (var i = 0; i < products.length; i++) {
            var product = products[i];
            if (norm(product.name) !== norm(title)) continue;
            sku = String(product.sku || '').trim();
            productId = String(product.productID || product.sku || '');
            var offers = Array.isArray(product.offers) ? product.offers : [product.offers];
            for (var j = 0; j < offers.length; j++) {
              var offer = offers[j];
              if (!offer) continue;
              if (String(offer.priceCurrency || '').toUpperCase() !== 'ARS') { prices = []; break; }
              // Conserva centavos del dato estructurado solo si coincide con lo visible.
              var amount = typeof offer.price === 'string' ? Number(offer.price) : offer.price;
              if (!prices.length || !(amount > 0 && isFinite(amount)) || Math.abs(amount - prices[0].amount) > .5) continue;
              prices[0].amount = amount;
              var stock = /\/(InStock|LimitedAvailability)$/.test(offer.availability || '') ? true :
                /\/(OutOfStock|SoldOut|Discontinued)$/.test(offer.availability || '') ? false : null;
              if (stock !== null) available = available === null || available === stock ? stock : null;
              break;
            }
            break;
          }
          cards.push({title: title, url: location.href, product_id: productId, available: available, prices: prices,
            variants: [{variant_id: sku, title: title, sku: sku, available: available, prices: prices}]});
        }
      } else {
        var nodes = document.querySelectorAll('.grid .card');
        for (var k = 0; k < nodes.length; k++) {
          var el = nodes[k], link = el.querySelector('a[href^="/p/"]'), label = text(el.querySelector('.nm'));
          if (!visible(el) || !link || !label) continue;
          var brand = text(el.querySelector('.br'));
          if (brand && norm(label).indexOf(norm(brand)) < 0) label = brand + ' ' + label;
          cards.push({title: label, url: link.href, product_id: '', variants: [],
            available: publishedStock(el, false), prices: price(el)});
        }
      }
      var next = detail ? null : document.querySelector('a[rel="next"]');
      if (!detail && !next) {
        // El enlace anterior también lleva offset: solo avanzar en la misma consulta.
        var current = new URL(location.href), offset = Number(current.searchParams.get('offset') || 0);
        var links = document.querySelectorAll('a[href*="offset="]'), smallest = Infinity;
        current.searchParams.delete('offset'); current.searchParams.sort();
        for (var p = 0; p < links.length; p++) {
          if (!enabled(links[p])) continue;
          var target = new URL(links[p].href), value = Number(target.searchParams.get('offset'));
          target.searchParams.delete('offset'); target.searchParams.sort();
          if (target.origin === current.origin && target.pathname === current.pathname &&
              target.search === current.search && value > offset && value < smallest) {
            next = links[p]; smallest = value;
          }
        }
      }
      var empty = /no encontramos|no se encontraron|sin resultados|no hay productos|no hay resultados|ning[uú]n producto/i.test(body);
      var result = {capture_version: 1, url: location.href, title: document.title,
        status: blocked ? 'bloqueado' : cards.length ? 'ok' : !detail && empty ? 'no_encontrado' : 'error_extraccion',
        cards: cards, next: enabled(next) ? next.href : null, load_more: false,
        pagination: visible(next) ? [next.outerHTML.slice(0, 2500)] : [],
        diagnostic: cards.length ? '' : body.slice(0, 5000), captured_at: new Date().toISOString()};
      if (detail) result.description = Array.prototype.map.call(document.querySelectorAll('.acc details p'), text).join(' ').slice(0, 3000);
      return result;
    }
  };
})()
