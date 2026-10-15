// Recorrido principal. Python entrega los datos de la consulta.
timeout 45
js begin
eval(require('fs').read('flujos/apoyo.js'));
comparasuple_read_job();
if (comparasuple_job.provider !== comparasuple_provider) throw new Error('Proveedor incorrecto para este flujo');
js finish

// Inspeccionar conserva el foco y los avisos: no ejecuta acciones.
if comparasuple_job.action != 'inspect'
  // Un bloqueo de la tienda anterior no impide abrir el siguiente proveedor.
  js begin
  comparasuple_same_store = comparasuple_dom(function (hosts) {
    return hosts.indexOf(location.host) >= 0;
  }, comparasuple_job.allowed_hosts);
  comparasuple_blocked = (!comparasuple_job.initial || comparasuple_same_store) && comparasuple_page_blocked();
  js finish
  if comparasuple_job.human && !comparasuple_blocked
    py exec(open('human_input.py', encoding='utf-8').read())
    js comparasuple_check_python(py_result);
    py focus()
    js comparasuple_check_python(py_result);

  // Reutilizar la página actual en las búsquedas de la misma tienda.
  if comparasuple_job.initial && !comparasuple_blocked
    js comparasuple_home = (comparasuple_job.home || ('https://' + comparasuple_job.host + '/')).replace(/^https:\/\//, '');
    https://`comparasuple_home`
    for carga_portada from 1 to 40
      js comparasuple_blocked = comparasuple_page_blocked();
      if comparasuple_blocked
        break
      js begin
      comparasuple_home_ready = comparasuple_dom(function(s) {
        if (document.readyState !== 'complete') return false;
        var inputs = document.querySelectorAll(s.input + (s.login_input ? ',' + s.login_input : ''));
        return Array.prototype.some.call(inputs, function(el) {
          var r = el.getBoundingClientRect(), style = getComputedStyle(el);
          return !el.disabled && !el.readOnly && r.width > 8 && r.height > 8 &&
            style.display !== 'none' && style.visibility !== 'hidden';
        });
      }, comparasuple_adapter.selectors);
      js finish
      if comparasuple_home_ready
        break
      wait 0.1

  js comparasuple_blocked = comparasuple_blocked || comparasuple_page_blocked();
  if !comparasuple_blocked
    tagui comun/acceso.tag

  // buscar.tag maneja sus propios avisos.
  js comparasuple_blocked = comparasuple_blocked || comparasuple_page_blocked();
  if !comparasuple_blocked && comparasuple_job.action != 'search'
    tagui comun/avisos.tag

  if !comparasuple_blocked
    if comparasuple_job.action == 'search'
      tagui comun/buscar.tag
    else if comparasuple_job.action == 'detail'
      tagui comun/ficha.tag
    else
      tagui comun/paginar.tag

  // Los bloqueos requieren intervención; no se resuelven automáticamente.
  if !comparasuple_blocked
    js comparasuple_content_ready = false;
    for carga_contenido from 1 to 40
      js comparasuple_blocked = comparasuple_page_blocked(); comparasuple_content_ready = comparasuple_url_matches('exact') && comparasuple_page_ready();
      if comparasuple_blocked || comparasuple_content_ready
        break
      wait 0.5
    js if (!comparasuple_blocked && !comparasuple_content_ready) throw new Error('La página solicitada no mostró su contenido.');

  if !comparasuple_blocked && comparasuple_job.action == 'search' && comparasuple_job.order_by == 'price_asc'
    tagui comun/ordenar.tag

js comparasuple_extract((comparasuple_job.action === 'inspect' ? comparasuple_job.inspect_action : comparasuple_job.action) === 'detail');
