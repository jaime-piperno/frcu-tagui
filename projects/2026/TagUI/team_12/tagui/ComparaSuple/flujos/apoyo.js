// Acciones DOM y Chrome compartidas por los flujos .tag.
// Funciones globales: cada bloque js de TagUI tiene su propio ámbito.

comparasuple_read_job = function () {
  comparasuple_job = JSON.parse(require('fs').read('trabajo.json').replace(/^\uFEFF/, ''));
  if (!comparasuple_job || typeof comparasuple_job.url !== 'string' ||
      typeof comparasuple_job.destination !== 'string') {
    throw new Error('Faltan la URL o el destino en trabajo.json');
  }
  comparasuple_job.query = comparasuple_job.query || '';
  if (!/^[a-z0-9_-]+$/.test(comparasuple_job.adapter || '')) throw new Error('Falta el adaptador de la tienda');
  comparasuple_adapter = eval(require('fs').read('parsers/' + comparasuple_job.adapter + '.js'));
  if (!comparasuple_adapter || !comparasuple_adapter.selectors || typeof comparasuple_adapter.extract !== 'function') {
    throw new Error('El adaptador debe definir selectors y extract(detail)');
  }
  comparasuple_pointer = {x: 40, y: 70};
  comparasuple_current_url = '';
  comparasuple_retry_search = false;
  comparasuple_search_attempts = 0;
  comparasuple_search_retries = [];
  comparasuple_force_notices = false;
  comparasuple_optional_click = false;
  comparasuple_blocked = false;
  comparasuple_last_character = 0;
  comparasuple_context_retries = 0;
  comparasuple_last_notice = '';
};

comparasuple_evaluate = function (expression) {
  var response = JSON.parse(chrome_step('Runtime.evaluate', {
    expression: expression, returnByValue: true, timeout: 5000
  }));
  var result = response.result;
  if (response.error || !result || result.exceptionDetails || !result.result ||
      result.result.subtype === 'error') {
    var error = new Error('Chrome no pudo evaluar la página');
    error.transient_context = !!response.error && /cannot find (?:execution )?context|execution context was destroyed/i.test(response.error.message || '');
    throw error;
  }
  return result.result.value;
};

comparasuple_dom = function (fn, data) {
  return comparasuple_evaluate('(' + fn.toString() + ')(' + JSON.stringify(data || {}) + ')');
};

comparasuple_locate = function (kind) {
  comparasuple_target = comparasuple_dom(function (data) {
    // Evitar los elementos que abren submenús al pasar el mouse.
    var navigation = [], navSelector = data.selectors.navigation ||
      'header a,header button,nav a,nav button,[role="navigation"] a,[role="navigation"] button,.nav-item-desktop > a,.js-nav-desktop a';
    var controls = document.querySelectorAll(navSelector);
    for (var n = 0; n < controls.length; n++) {
      var control = controls[n], owner = control.closest('li,.nav-item-desktop,.nav-item,.dropdown') || control.parentElement;
      var panel = owner && owner.querySelector('ul,[role="menu"],.js-desktop-dropdown,.desktop-dropdown,.dropdown-menu,.nav-list-subitems');
      var controlled = control.getAttribute('aria-controls');
      if (!panel && controlled) panel = document.getElementById(controlled);
      if (!panel || control.contains(panel)) continue;
      var bounds = control.getBoundingClientRect(), navHit = document.elementFromPoint(bounds.left + bounds.width / 2, bounds.top + bounds.height / 2);
      if (bounds.width > 4 && bounds.height > 4 && bounds.bottom > 0 && bounds.top < innerHeight &&
          bounds.right > 0 && bounds.left < innerWidth && navHit && (control === navHit || control.contains(navHit))) {
        navigation.push({owner: owner, panel: panel, bounds: bounds});
      }
    }
    function target(x, y, extra) {
      extra = extra || {};
      extra.visible = true;
      extra.clientX = x;
      extra.clientY = y;
      extra.x = x;
      extra.y = y;
      extra.metrics = {width: innerWidth, height: innerHeight, scale: devicePixelRatio};
      extra.viewport = {left: 4, top: 4, right: innerWidth - 4, bottom: innerHeight - 4};
      extra.navigation = navigation.map(function (item) {
        return {left: item.bounds.left, top: item.bounds.top,
          right: item.bounds.right, bottom: item.bounds.bottom};
      });
      return extra;
    }
    function hoverPanel(x, y) {
      var node = document.elementFromPoint(x, y);
      for (var h = 0; node && h < navigation.length; h++) {
        var item = navigation[h];
        // Confirmar que el menú realmente cubra el contenido.
        if (item.panel.contains(node)) return item;
      }
      return null;
    }
    function uncovered(x, y) {
      var item = hoverPanel(x, y);
      if (!item) return null;
      var r = item.panel.getBoundingClientRect();
      var options = [[x, r.bottom + 16], [x, r.top - 16], [r.left - 16, y], [r.right + 16, y],
        [innerWidth / 2, innerHeight - 20], [20, innerHeight - 20], [innerWidth - 20, innerHeight - 20]];
      for (var o = 0; o < options.length; o++) {
        var px = options[o][0], py = options[o][1];
        if (px < 8 || px > innerWidth - 8 || py < 8 || py > innerHeight - 8) continue;
        var node = document.elementFromPoint(px, py);
        if (node && !item.owner.contains(node) && !hoverPanel(px, py)) return target(px, py, {hover_exit: true});
      }
      return null;
    }
    function hit(el, x, y) {
      var found = document.elementFromPoint(x, y);
      return found && (found === el || el.contains(found));
    }
    function dismissOverlay() {
      // Un aviso desconocido que tapa el centro de la página sólo se cierra o se rechaza; nunca se acepta.
      var closeLabel = /^(?:cerrar|close|[×✕✖x])(?: (?:el |la )?(?:modal|aviso|di[aá]logo|dialog|ventana|banner|popup|anuncio))?$/i;
      var declineLabel = /^(?:no,? gracias|no en este momento|ahora no|m[aá]s tarde|quiz[aá]s? m[aá]s tarde|omitir|saltar|no me interesa)$/i;
      var probes = [[innerWidth / 2, innerHeight / 2], [innerWidth / 2, innerHeight * .35], [innerWidth / 2, innerHeight * .65]];
      var unknown = null;
      function describe(root) {
        var labels = [], buttons = root.querySelectorAll('button,[role="button"],a');
        for (var d = 0; d < buttons.length && labels.length < 8; d++) {
          var label = (buttons[d].getAttribute('aria-label') || buttons[d].innerText || '').replace(/\s+/g, ' ').trim();
          if (label) labels.push(label.slice(0, 40));
        }
        return {etiqueta: root.tagName.toLowerCase(), clase: String(root.getAttribute('class') || '').slice(0, 80),
          rol: root.getAttribute('role') || '', botones: labels};
      }
      for (var p = 0; p < probes.length; p++) {
        var node = document.elementFromPoint(probes[p][0], probes[p][1]), frame = null, root = null;
        if (node && node.tagName === 'IFRAME') {
          try {
            frame = node;
            var box = frame.getBoundingClientRect();
            node = frame.contentDocument.elementFromPoint(probes[p][0] - box.left, probes[p][1] - box.top);
          } catch (error) { // Un iframe de otro dominio no se puede revisar.
            try { unknown = unknown || {iframe: new URL(frame.src, location.href).host}; } catch (ignored) {}
            continue;
          }
        }
        for (var up = node; up && up.nodeType === 1 && up !== up.ownerDocument.body &&
            up !== up.ownerDocument.documentElement; up = up.parentElement) {
          var size = up.getBoundingClientRect();
          if ((up.ownerDocument.defaultView.getComputedStyle(up).position === 'fixed' || up.tagName === 'DIALOG' ||
              /^(?:dialog|alertdialog)$/.test(up.getAttribute('role') || '') || up.getAttribute('aria-modal') === 'true') &&
              size.width >= 200 && size.height >= 150) root = up; // Se conserva el contenedor más externo.
        }
        if (!root && frame && node) {
          // El iframe completo es el aviso cuando él mismo cubre la página.
          var area = frame.getBoundingClientRect();
          if (getComputedStyle(frame).position === 'fixed' || area.width * area.height >= innerWidth * innerHeight / 2) {
            root = node.ownerDocument.body;
          }
        }
        if (!root) continue;
        var controls = root.querySelectorAll('button,[role="button"],a'), choice = null;
        for (var b = 0; b < controls.length; b++) {
          var control = controls[b], rect = control.getBoundingClientRect();
          var text = (control.innerText || control.textContent || '').replace(/\s+/g, ' ').trim();
          var name = (control.getAttribute('aria-label') || control.getAttribute('title') || text).replace(/\s+/g, ' ').trim();
          var closes = closeLabel.test(name) || closeLabel.test(text) ||
            (!name && /(?:^|[-_\s])(?:close|cerrar)(?:$|[-_\s])/i.test(control.getAttribute('class') || ''));
          if (!(closes || declineLabel.test(name) || declineLabel.test(text)) || rect.width <= 8 || rect.height <= 8) continue;
          var cx = rect.left + rect.width / 2, cy = rect.top + rect.height / 2;
          var found = control.ownerDocument.elementFromPoint(cx, cy);
          if (!found || !(found === control || control.contains(found))) continue;
          if (!choice || closes) choice = {control: control, x: cx, y: cy};
          if (closes) break;
        }
        if (!choice) {
          unknown = unknown || describe(root);
          continue;
        }
        var shift = frame ? frame.getBoundingClientRect() : {left: 0, top: 0};
        // La marca permite confirmar, después de mover el mouse, que sigue debajo el mismo control.
        choice.control.setAttribute('data-comparasuple-cerrar', '');
        if (frame) frame.setAttribute('data-comparasuple-cerrar', '');
        return target(choice.x + shift.left, choice.y + shift.top, {selector: '[data-comparasuple-cerrar]', overlay: true});
      }
      return unknown && {visible: false, aviso: unknown};
    }
    var i, el, r, x, y, es, style, selector, escape = null;
    if (data.kind === 'top') return {visible: window.pageYOffset <= 0};
    if (data.kind === 'center') return uncovered(innerWidth * .65, innerHeight * .6) || target(innerWidth * .65, innerHeight * .6);
    if (data.kind === 'product' || data.kind === 'link') {
      es = document.querySelectorAll('a[href]');
      for (i = 0; i < es.length; i++) {
        if (es[i].href !== data.url) continue;
        el = data.kind === 'product' ? (es[i].querySelector('img') || es[i]) : es[i];
        r = el.getBoundingClientRect();
        // Exigir que la foto esté visible antes de pulsarla.
        var left = Math.max(0, r.left), top = Math.max(0, r.top);
        var width = Math.min(innerWidth, r.right) - left;
        var height = Math.min(innerHeight, r.bottom) - top;
        x = left + width / 2;
        y = top + height / 2;
        style = getComputedStyle(el);
        if (width >= Math.min(r.width, 80) && height >= Math.min(r.height, 120) &&
            width > 8 && height > 8 && r.top + r.height / 2 >= 0 &&
            r.top + r.height / 2 < innerHeight && style.visibility !== 'hidden' &&
            style.display !== 'none' && style.opacity !== '0') {
          if (hit(es[i], x, y)) return target(x, y, {href: es[i].href});
          escape = escape || uncovered(x, y);
        }
      }
      return {visible: false, escape: escape};
    }
    if (data.kind === 'consent') {
      es = document.querySelectorAll('a,button');
      for (i = 0; i < es.length; i++) {
        el = es[i];
        if (!/^(entendido|aceptar(?: cookies)?)$/i.test((el.innerText || '').trim())) continue;
        r = el.getBoundingClientRect();
        x = r.left + r.width / 2;
        y = r.top + r.height / 2;
        if (r.width > 8 && r.height > 8 && x >= 0 && x < innerWidth &&
            y >= 0 && y < innerHeight && hit(el, x, y)) {
          return target(x, y, {consent: true});
        }
      }
      return {visible: false};
    }
    // Cierres reconocibles dentro de avisos, sin tocar botones de compra o envío.
    var popup = ['.p-layer .p-close'];
    if (data.selectors.popup) popup.push(data.selectors.popup);
    var dialogs = ['dialog[open]', '[role="dialog"]', '[aria-modal="true"]', '.js-modal', '.modal', '.popup'];
    var closes = ['.modal-close', '.js-modal-close', '.close', '.btn-close',
      '[aria-label^="Cerrar" i]', '[aria-label^="Close" i]',
      '[title="Cerrar" i]', '[title="Close" i]', '[data-dismiss="modal"]', '[data-bs-dismiss="modal"]'];
    for (i = 0; i < dialogs.length; i++) {
      for (var c = 0; c < closes.length; c++) popup.push(dialogs[i] + ' ' + closes[c]);
    }
    selector = data.kind === 'popup' ? popup.join(',') : data.selectors[data.kind];
    if (!selector && /^(login_input|login_submit|loadmore)$/.test(data.kind)) return {visible: false};
    if (!selector) throw new Error('Localizador desconocido: ' + data.kind);
    es = document.querySelectorAll(selector);
    for (i = 0; i < es.length; i++) {
      el = es[i];
      if (data.kind === 'price_asc' && !/^Menor precio$/i.test((el.innerText || el.textContent || '').replace(/\s+/g, ' ').trim())) continue;
      if (data.kind === 'next' && (el.hasAttribute('disabled') || el.getAttribute('aria-disabled') === 'true' ||
          el.closest('[aria-disabled="true"], [data-andes-state="disabled"], .andes-pagination__button--disabled'))) continue;
      r = el.getBoundingClientRect();
      style = getComputedStyle(el);
      x = r.left + r.width / 2;
      y = r.top + r.height / 2;
      if (r.width > 8 && r.height > 8 && r.top >= 0 && r.bottom <= innerHeight &&
          r.left >= 0 && r.right <= innerWidth && style.display !== 'none' &&
          style.visibility !== 'hidden') {
        if (hit(el, x, y)) return target(x, y, {selector: selector});
        escape = escape || uncovered(x, y);
      }
    }
    if (data.kind === 'popup') {
      var overlay = dismissOverlay();
      if (overlay && overlay.visible) return overlay;
      if (overlay) return {visible: false, escape: escape, aviso: overlay.aviso};
    }
    return {visible: false, escape: escape};
  }, {kind: kind, url: comparasuple_job.url, human: !!comparasuple_job.human, selectors: comparasuple_adapter.selectors});
  if (!comparasuple_target) throw new Error('No se pudo medir el elemento en Chrome');
  if (comparasuple_target.aviso && JSON.stringify(comparasuple_target.aviso) !== comparasuple_last_notice) {
    // Un aviso que no se puede cerrar con seguridad queda descrito en error.log.
    comparasuple_last_notice = JSON.stringify(comparasuple_target.aviso);
    comparasuple_record('aviso_sin_cierre', {aviso: comparasuple_target.aviso});
  }
  comparasuple_target.kind = kind;
  require('fs').write('human_target.json', JSON.stringify(comparasuple_target), 'w');
};

comparasuple_escape_hover = function () {
  if (!comparasuple_target.escape || comparasuple_page_blocked()) return false;
  comparasuple_target = comparasuple_target.escape;
  require('fs').write('human_target.json', JSON.stringify(comparasuple_target), 'w');
  if (comparasuple_job.human) comparasuple_python('move_target()');
  else comparasuple_move('leave_menu');
  return true;
};

comparasuple_record = function (action, data) {
  data = data || {};
  data.action = action;
  data.time = Date.now();
  require('fs').write('background_actions.jsonl', JSON.stringify(data) + '\n', 'a');
};

comparasuple_pointer_route = function (start, target, navigation, viewport) {
  function crosses(a, b, r) {
    if (a.x >= r.left && a.x <= r.right && a.y >= r.top && a.y <= r.bottom) return false;
    var lower = 0, upper = 1, axes = [['x', 'left', 'right'], ['y', 'top', 'bottom']];
    for (var i = 0; i < axes.length; i++) {
      var axis = axes[i], delta = b[axis[0]] - a[axis[0]];
      if (!delta) {if (a[axis[0]] < r[axis[1]] || a[axis[0]] > r[axis[2]]) return false; continue;}
      var first = (r[axis[1]] - a[axis[0]]) / delta, last = (r[axis[2]] - a[axis[0]]) / delta;
      lower = Math.max(lower, Math.min(first, last)); upper = Math.min(upper, Math.max(first, last));
      if (lower > upper) return false;
    }
    return true;
  }
  function clear(points) {
    var previous = start;
    for (var p = 0; p < points.length; p++) {
      for (var n = 0; n < navigation.length; n++) if (crosses(previous, points[p], navigation[n])) return false;
      previous = points[p];
    }
    return true;
  }
  if (!navigation.length || clear([target])) return [target];
  var xs = [start.x, target.x], best = [target], distance = Infinity;
  navigation.forEach(function (r) {xs.push(r.left - 14, r.right + 14);});
  xs.forEach(function (x) {
    var points = [{x: x, y: start.y}, {x: x, y: target.y}, target];
    if (viewport && points.some(function (p) {return p.x < viewport.left || p.x > viewport.right || p.y < viewport.top || p.y > viewport.bottom;})) return;
    if (!clear(points)) return;
    var length = 0, previous = start;
    points.forEach(function (p) {length += Math.sqrt(Math.pow(p.x - previous.x, 2) + Math.pow(p.y - previous.y, 2)); previous = p;});
    if (length < distance) {best = points; distance = length;}
  });
  return best;
};

comparasuple_move = function (label) {
  if (!comparasuple_target.visible) throw new Error('No se ve el elemento para ' + label);
  var points = comparasuple_pointer_route(comparasuple_pointer, {x: comparasuple_target.clientX, y: comparasuple_target.clientY},
    comparasuple_target.navigation || [], comparasuple_target.viewport);
  for (var p = 0; p < points.length; p++) {
    var startX = comparasuple_pointer.x, startY = comparasuple_pointer.y;
    if (startX === points[p].x && startY === points[p].y) continue;
    for (var i = 1; i <= 9; i++) {
      var progress = i / 9, smooth = progress * progress * (3 - 2 * progress);
      chrome_step('Input.dispatchMouseEvent', {
        type: 'mouseMoved', x: startX + (points[p].x - startX) * smooth,
        y: startY + (points[p].y - startY) * smooth
      });
      sleep(45);
    }
    comparasuple_pointer = points[p];
  }
  // Esperar la apertura de menús antes de comprobar el destino.
  sleep(450);
};

comparasuple_hit_test = function () {
  return comparasuple_dom(function (t) {
    var hit = document.elementFromPoint(t.clientX, t.clientY);
    if (!hit) return false;
    if (t.href) {
      var anchor = hit.closest('a[href]');
      return !!anchor && anchor.href === t.href;
    }
    if (t.consent) {
      var button = hit.closest('a,button');
      return !!button && /^(entendido|aceptar(?: cookies)?)$/i.test((button.innerText || '').trim());
    }
    return !!t.selector && !!hit.closest(t.selector);
  }, comparasuple_target) === true;
};

comparasuple_click = function (label) {
  comparasuple_blocked = comparasuple_blocked || comparasuple_page_blocked();
  if (comparasuple_blocked) return false;
  if (!comparasuple_target.visible) return false;
  comparasuple_move(label);
  comparasuple_blocked = comparasuple_blocked || comparasuple_page_blocked();
  if (comparasuple_blocked) return false;
  if (!comparasuple_hit_test()) return false;
  chrome_step('Input.dispatchMouseEvent', {
    type: 'mousePressed', x: comparasuple_target.clientX, y: comparasuple_target.clientY,
    button: 'left', clickCount: 1
  });
  sleep(75);
  chrome_step('Input.dispatchMouseEvent', {
    type: 'mouseReleased', x: comparasuple_target.clientX, y: comparasuple_target.clientY,
    button: 'left', clickCount: 1
  });
  comparasuple_record(label, {x: comparasuple_target.clientX, y: comparasuple_target.clientY});
  return true;
};

comparasuple_field_ready = function (kind, expected, require_text) {
  // Tener Chrome activo no garantiza que el foco siga dentro del buscador.
  comparasuple_blocked = comparasuple_blocked || comparasuple_page_blocked();
  if (comparasuple_blocked) return false;
  return comparasuple_dom(function (data) {
    if (data.human && !document.hasFocus()) return false;
    var el = document.activeElement;
    if (!el || !data.selector || !el.matches(data.selector) ||
        el.disabled || el.readOnly) return false;
    var r = el.getBoundingClientRect();
    return r.width > 8 && r.height > 8 &&
      document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2) === el &&
      (!data.require_text || el.value === data.expected);
  }, {selector: comparasuple_adapter.selectors[kind], expected: expected,
      require_text: !!require_text, human: !!comparasuple_job.human}) === true;
};

comparasuple_search_ready = function (require_text) {
  return comparasuple_field_ready('input', comparasuple_job.query, require_text);
};

comparasuple_wheel = function (delta, label) {
  chrome_step('Input.dispatchMouseEvent', {
    type: 'mouseWheel', x: comparasuple_pointer.x, y: comparasuple_pointer.y, deltaX: 0, deltaY: delta
  });
  sleep(120);
  comparasuple_record(label || (delta < 0 ? 'scroll_up' : 'scroll_down'));
};

comparasuple_select_query = function () {
  chrome_step('Input.dispatchKeyEvent', {
    type: 'keyDown', key: 'Control', code: 'ControlLeft', windowsVirtualKeyCode: 17, modifiers: 2
  });
  chrome_step('Input.dispatchKeyEvent', {
    type: 'keyDown', key: 'a', code: 'KeyA', windowsVirtualKeyCode: 65, modifiers: 2
  });
  chrome_step('Input.dispatchKeyEvent', {
    type: 'keyUp', key: 'a', code: 'KeyA', windowsVirtualKeyCode: 65, modifiers: 2
  });
  chrome_step('Input.dispatchKeyEvent', {
    type: 'keyUp', key: 'Control', code: 'ControlLeft', windowsVirtualKeyCode: 17
  });
};

comparasuple_type_character = function (character) {
  chrome_step('Input.dispatchKeyEvent', {type: 'char', text: character});
  sleep(50);
};

comparasuple_wait_character = function () {
  if (!comparasuple_job.human) return;
  // 115 palabras/minuto; el intervalo incluye el tiempo de los puentes.
  var interval = 60000 / (115 * 5);
  if (comparasuple_last_character) sleep(Math.max(0, interval - (Date.now() - comparasuple_last_character)));
  comparasuple_last_character = Date.now();
};

comparasuple_python = function (command) {
  if (!py_step(command)) throw new Error('Falló el puente de teclado Python.');
  var result = fetch_py_text();
  clear_py_text();
  comparasuple_check_python(result);
};

comparasuple_url_matches = function (kind) {
  try {
    var result = comparasuple_dom(function (data) {
      function parameters(search, mercado, hash) {
        var source = search.replace(/^\?/, '');
        // Mercado Libre también transporta vendedores/variantes en el fragmento.
        if (mercado && hash.indexOf('=') >= 0) source += '&' + hash.replace(/^#/, '');
        var values = Object.create(null), fields = source.split('&');
        for (var i = 0; i < fields.length; i++) {
          if (!fields[i]) continue;
          var pair = fields[i].split('=');
          var key = decodeURIComponent(pair.shift().replace(/\+/g, ' '));
          var value = decodeURIComponent(pair.join('=').replace(/\+/g, ' '));
          if (mercado && (/^(tracking_id|position|search_layout|type|sid)$/.test(key) || /^utm_/.test(key))) continue;
          if (!Object.prototype.hasOwnProperty.call(values, key)) values[key] = [];
          values[key].push(value);
        }
        return Object.keys(values).sort().map(function (key) {
          return [key, values[key]];
        });
      }
      var actual = new URL(location.href), expected = new URL(data.url);
      var mercado = data.adapter === 'mercadolibre';
      function searchPath(url) {
        // Sólo el orden solicitado es equivalente; otros filtros siguen siendo distintos.
        if (data.order_by !== 'price_asc' || url.hostname !== 'listado.mercadolibre.com.ar' ||
            !/^\/[a-zA-Z0-9%.,\u00c0-\u024f\-]+(?:_Desde_[1-9]\d*)?_OrderId_PRICE(?:_Desde_[1-9]\d*)?(?:_NoIndex_True)?\/?$/.test(url.pathname)) return url.pathname;
        return url.pathname.replace('_OrderId_PRICE', '').replace('_NoIndex_True', '');
      }
      var allowed = data.hosts || [expected.host];
      var valid = actual.protocol === 'https:' && expected.protocol === 'https:' &&
        !actual.username && !actual.password && !expected.username && !expected.password &&
        allowed.indexOf(actual.host) >= 0 && allowed.indexOf(expected.host) >= 0;
      var actualParameters = parameters(actual.search, mercado, actual.hash);
      var expectedParameters = parameters(expected.search, mercado, expected.hash);
      var sameParameters = JSON.stringify(actualParameters) === JSON.stringify(expectedParameters);
      var reached = valid && actual.host === expected.host && actual.pathname === expected.pathname && sameParameters;
      function searchParameters(params) {
        // «Todo MercadoLibre» no filtra; conservar cualquier otro alcance.
        return params.filter(function (item) {
          return !(item[0] === 'sb' && item[1].length === 1 && item[1][0] === 'all_mercadolibre');
        });
      }
      if (data.expected_page) {
        function paginatedSearch(url, params) {
          params = searchParameters(params);
          if (url.hostname !== 'listado.mercadolibre.com.ar' || params.length) return null;
          var found = searchPath(url).match(/^\/([a-zA-Z0-9%.,\u00c0-\u024f\-]+)(?:_Desde_[1-9]\d*)?(?:_NoIndex_True)?\/?$/);
          if (!found) return null;
          var decoded = decodeURIComponent(found[1]);
          if (/[\/_]/.test(decoded)) return null;
          return decoded.normalize('NFKD').replace(/[\u0300-\u036f]/g, '').toLowerCase()
            .replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '');
        }
        var selected = document.querySelector('.andes-pagination [aria-current="page"], .andes-pagination [data-andes-state="selected"], .andes-pagination__button--current');
        var number = selected ? (selected.innerText || selected.textContent || '').trim() : '';
        var firstPageSearch = paginatedSearch(actual, actualParameters);
        var secondPageSearch = paginatedSearch(expected, expectedParameters);
        reached = valid && mercado && !!firstPageSearch && firstPageSearch === secondPageSearch &&
          !!selected && selected.getClientRects().length > 0 && getComputedStyle(selected).visibility !== 'hidden' &&
          /^\d+$/.test(number) && Number(number) === data.expected_page;
      } else if (valid && mercado && !reached) {
        // El slug puede cambiar; wid y variantes deben seguir coincidiendo.
        var firstId = decodeURIComponent(actual.pathname).match(/\bMLA-?(\d+)\b/i);
        var secondId = decodeURIComponent(expected.pathname).match(/\bMLA-?(\d+)\b/i);
        if (firstId || secondId) {
          reached = !!firstId && !!secondId && firstId[1] === secondId[1] && sameParameters;
        } else {
          function slug(value) {
            return String(value).normalize('NFKD').replace(/[\u0300-\u036f]/g, '')
              .toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '');
          }
          function searchIdentity(url, params) {
            params = searchParameters(params);
            var path = searchPath(url).replace(/\/+$/, '');
            if ((path === '/jm/search' || path === '/search') && params.length === 1 &&
                /^(q|as_word)$/.test(params[0][0]) && params[0][1].length === 1) {
              return slug(params[0][1][0]);
            }
            // Un filtro o una página posterior (_Desde_...) no equivale al inicio.
            if (url.hostname === 'listado.mercadolibre.com.ar' && params.length === 0 &&
                /^\/[a-z0-9%.,\u00c0-\u024f\-]+$/i.test(path)) {
              var decodedPath = decodeURIComponent(path.slice(1));
              if (!/[\/_]/.test(decodedPath)) return slug(decodedPath);
            }
            return null;
          }
          var firstSearch = searchIdentity(actual, actualParameters);
          var secondSearch = searchIdentity(expected, expectedParameters);
          reached = !!firstSearch && firstSearch === secondSearch;
        }
      }
      return {url: location.href, reached: reached};
    }, {url: comparasuple_job.url,
      adapter: comparasuple_job.adapter, hosts: comparasuple_job.allowed_hosts,
      order_by: comparasuple_job.order_by,
      expected_page: comparasuple_job.expected_page ? comparasuple_job.expected_page - (kind === 'previous' ? 1 : 0) : null});
    comparasuple_current_url = result.url;
    return result.reached;
  } catch (error) {
    // Durante la carga, Chrome puede destruir temporalmente el contexto anterior.
    return false;
  }
};

comparasuple_generic_block = function () {
  // Respaldo para tiendas sin detector propio. Los scripts de CAPTCHA ocultos no cuentan.
  var text = document.title + ' ' + (document.body ? document.body.innerText || '' : '').slice(0, 1200);
  if (/\b(?:re)?captcha\b|verify you are human|verific[aá] que (?:eres|sos) humano|por seguridad, complet[aá] este paso/i.test(text)) return 'captcha';
  var nodes = document.querySelectorAll('iframe[src*="recaptcha"][src*="/anchor"], iframe[src*="recaptcha"][src*="/bframe"], iframe[src*="hcaptcha"], .g-recaptcha, .h-captcha');
  for (var i = 0; i < nodes.length; i++) {
    var bounds = nodes[i].getBoundingClientRect();
    if (nodes[i].getClientRects().length && getComputedStyle(nodes[i]).visibility !== 'hidden' &&
        bounds.width > 1 && bounds.height > 1 && !nodes[i].closest('.grecaptcha-badge, [data-size="invisible"]')) return 'captcha';
  }
  return /access denied|acceso denegado|too many requests|just a moment|\b403 forbidden\b/i.test(text) ? 'acceso_denegado' : '';
};

comparasuple_page_blocked = function () {
  try {
    var detect = typeof comparasuple_adapter.blocked === 'function' ? comparasuple_adapter.blocked : comparasuple_generic_block;
    return !!comparasuple_evaluate('(' + detect.toString() + ')()');
  } catch (error) { return false; }
};

comparasuple_page_ready = function () {
  // Las recomendaciones no demuestran que la ficha solicitada haya cargado.
  try {
    var detail = (comparasuple_job.action === 'inspect' ? comparasuple_job.inspect_action : comparasuple_job.action) === 'detail';
    if (typeof comparasuple_adapter.ready !== 'function') {
      return comparasuple_evaluate("document.readyState === 'complete' && /^(ok|no_encontrado)$/.test((" +
        comparasuple_adapter.extract.toString() + ')(' + JSON.stringify(detail) + ').status)') === true;
    }
    return comparasuple_evaluate('(' + comparasuple_adapter.ready.toString() + ')(' +
      JSON.stringify(detail) + ')') === true;
  } catch (error) { return false; }
};

comparasuple_sort_order = function () {
  if (typeof comparasuple_adapter.sort_order !== 'function') return null;
  try { return comparasuple_evaluate('(' + comparasuple_adapter.sort_order.toString() + ')()'); }
  catch (error) { return null; }
};

comparasuple_extract = function (detail) {
  var result;
  var genericBlock = typeof comparasuple_adapter.blocked !== 'function' ?
    comparasuple_evaluate('(' + comparasuple_generic_block.toString() + ')()') : '';
  if (genericBlock) {
    result = comparasuple_dom(function (data) {
      var reason = data.type === 'captcha' ? 'El sitio solicita completar una verificación manual.' : 'El sitio denegó el acceso.';
      return {capture_version: 1, url: location.href, title: 'Verificación del sitio', status: 'bloqueado',
        block_type: data.type, reason: reason, diagnostic: reason, cards: [], next: null, load_more: false,
        pagination: [], hidden_products: 0, captured_at: new Date().toISOString()};
    }, {type: genericBlock});
  } else if (comparasuple_job.action === 'inspect' && !comparasuple_page_blocked() && !comparasuple_page_ready()) {
    // Una página todavía cargando no prueba ausencia, stock ni precio.
    result = comparasuple_dom(function () {
      return {capture_version: 1, url: location.href, title: document.title,
        status: 'error_extraccion', cards: [], next: null, load_more: false,
        pagination: [], hidden_products: 0, captured_at: new Date().toISOString(),
        diagnostic: 'La página actual todavía no muestra el contenido esperado.'};
    });
  } else {
    result = comparasuple_evaluate('(' + comparasuple_adapter.extract.toString() + ')(' + JSON.stringify(!!detail) + ')');
  }
  if (!result || result.capture_version !== 1) throw new Error('La extracción no respeta el contrato común');
  if (!detail && comparasuple_job.order_by) {
    result.order_by = result.status === 'bloqueado' ? null : comparasuple_sort_order();
    if (!result.order_by && result.status !== 'bloqueado') {
      result.diagnostic = ((result.diagnostic || '') + ' No se confirmó el orden por menor precio; se conserva la búsqueda sin ordenar.').trim();
    }
  }
  if (comparasuple_search_retries.length) {
    result.diagnostic = ((result.diagnostic || '') + ' Búsqueda: ' + comparasuple_search_attempts +
      ' intentos. Reintentos: ' + comparasuple_search_retries.join('; ') + '.').trim();
  }
  result.request = {provider: comparasuple_job.provider, query: comparasuple_job.query,
    action: comparasuple_job.action, expected_url: comparasuple_job.url};
  if (comparasuple_job.order_by) result.request.order_by = comparasuple_job.order_by;
  require('fs').write(comparasuple_job.destination, JSON.stringify(result), 'w');
};

comparasuple_check_python = function (result) {
  if (/error\s*-/i.test(String(result))) throw new Error(String(result));
};
