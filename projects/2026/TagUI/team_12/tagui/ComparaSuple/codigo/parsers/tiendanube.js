// Adaptador compartido por las tiendas Tiendanube.
(function () {
  return {
    selectors: {
      input: 'form.js-search-form input[name=q]',
      submit: 'form.js-search-form button[type=submit],form.js-search-form button.js-search-input-submit',
      loadmore: '.js-load-more'
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
      function add(prices, value, method) {
        var amount = money(value);
        if (amount !== null) prices.push({amount: amount, method: method, currency: 'ARS'});
        return amount !== null;
      }
      function field(prices, variant, names, method) {
        for (var i = 0; i < names.length; i++) if (add(prices, variant[names[i]], method)) break;
      }
      function normalize(raw, title) {
        var result = [];
        for (var i = 0; i < raw.length; i++) {
          var v = raw[i];
          if (!v || typeof v !== 'object' || v.is_visible === false || v.is_visible === 'false') continue;
          var available = v.contact ? null : v.available;
          if (typeof available === 'string') available = available.toLowerCase() === 'true' ? true :
            available.toLowerCase() === 'false' ? false : null;
          if (available !== true && available !== false) available = null;
          if (v.stock !== null && v.stock !== undefined && String(v.stock).trim() !== '' &&
              isFinite(Number(v.stock)) && Number(v.stock) <= 0) available = false;
          var methods = [], gateways = v.popup_discount_visibility || {};
          Object.keys(gateways).forEach(function (key) {
            var options = gateways[key] && gateways[key].methods || {};
            Object.keys(options).forEach(function (method) {
              var label = {cash: 'Efectivo', wire_transfer: 'Transferencia'}[method];
              if (label && options[method] && options[method].show_discount && methods.indexOf(label) < 0) methods.push(label);
            });
          });
          var prices = [];
          field(prices, v, ['price_number', 'price_short'], 'Precio publicado');
          field(prices, v, ['price_with_payment_discount_short', 'price_with_payment_discount_number'],
            methods.sort().join(' / ') || 'Descuento de pago publicado');
          if (v.has_promotional_price) field(prices, v,
            ['promotional_price_number', 'promotional_price_short'], 'Promoción vigente');
          var options = [v.option0, v.option1, v.option2].filter(function (value) {
            return value !== null && value !== undefined && String(value).trim() !== '';
          }).join(' ');
          result.push({variant_id: String(v.id || ''), title: (title + ' ' + options).trim(),
            sku: String(v.sku || '').trim(), available: available, prices: prices});
        }
        return result;
      }
      function rawVariants(el) {
        try {
          var data = JSON.parse(el ? el.getAttribute('data-variants') || '[]' : '[]');
          return Array.isArray(data) ? data : [];
        } catch (e) { return []; }
      }
      function visiblePrices(el) {
        var prices = [];
        [['.js-price-display,.item-price', 'Precio publicado'],
          ['.js-payment-discount-price-product,.js-payment-discount-price', 'Descuento de pago']].forEach(function (item) {
          var node = el.querySelector(item[0]);
          if (visible(node) && !node.closest('del,s,.price-compare,.js-compare-price-display')) add(prices, text(node), item[1]);
        });
        return prices;
      }
      var body = text(document.body), cards = [], hidden = 0;
      var blocked = /access denied|verify you are human|verifica que eres humano|just a moment|captcha|too many requests/i.test(document.title + ' ' + body.slice(0, 1200));
      if (detail) {
        var name = document.querySelector('h1.js-product-name,.js-product-name,h1');
        var title = text(name), container = document.querySelector('#product_form[data-variants],.js-product-container[data-variants]');
        var normalized = normalize(rawVariants(container), title);
        if (title) cards.push({title: title, url: location.href,
          product_id: container ? container.getAttribute('data-product-id') || '' : '',
          variants: normalized, prices: [], available: null});
      } else {
        var nodes = document.querySelectorAll('.js-item-product');
        for (var i = 0; i < nodes.length; i++) {
          var el = nodes[i], label = text(el.querySelector('.js-item-name,.item-name'));
          if (!label) continue;
          if (!visible(el)) { hidden++; continue; }
          var link = el.querySelector('a[href*="/productos/"],a.item-link');
          var variantsNode = el.hasAttribute('data-variants') ? el : el.querySelector('[data-variants]');
          var stock = el.querySelector('.js-stock-label');
          cards.push({title: label, url: link ? link.href : '', product_id: el.getAttribute('data-product-id') || '',
            variants: normalize(rawVariants(variantsNode), label), prices: visiblePrices(el),
            available: visible(stock) && /sin stock|agotado/i.test(text(stock)) ? false : null, html: el.outerHTML});
        }
      }
      var next = detail ? null : document.querySelector('a[rel="next"],a.js-pagination-next,.pagination-next a');
      var more = detail ? null : document.querySelector('.js-load-more'), pagination = [];
      if (!detail) Array.prototype.forEach.call(document.querySelectorAll('[class*="pagination"],[class*="load-more"]'), function (el) {
        if (visible(el)) pagination.push(el.outerHTML.slice(0, 2500));
      });
      var empty = /no encontramos|no se encontraron|sin resultados|no hay productos|no hay resultados/i.test(body);
      if (!cards.length && hidden > 0 && /resultados de b[uú]squeda/i.test(body)) empty = true;
      var valid = cards.length && (!detail || cards[0].variants.length);
      var result = {capture_version: 1, url: location.href, title: document.title,
        status: blocked ? 'bloqueado' : valid ? 'ok' : !detail && empty ? 'no_encontrado' : 'error_extraccion',
        cards: cards, next: enabled(next) ? next.href : null, load_more: enabled(more), pagination: pagination,
        hidden_products: hidden, diagnostic: valid ? '' : body.slice(0, 5000), captured_at: new Date().toISOString()};
      if (detail) result.description = text(document.querySelector('[data-store^="product-description"] .user-content,[data-store^="product-description"]')).slice(0, 3000);
      return result;
    }
  };
})()
