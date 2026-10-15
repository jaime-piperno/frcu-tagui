// Confirmar la navegación después del clic.
js comparasuple_reached = false; comparasuple_navigation_retries = 0; comparasuple_navigation_last_click = Date.now();
for intento from 1 to 60
  js comparasuple_reached = comparasuple_url_matches('exact'); comparasuple_blocked = comparasuple_page_blocked();
  if comparasuple_reached || comparasuple_blocked
    break
  // Reintentar la ficha si el clic no navegó; nunca usar coordenadas antiguas.
  tagui comun/avisos.tag
  js comparasuple_navigation_retry = comparasuple_notices_closed || (comparasuple_click_kind === 'product' && Date.now() - comparasuple_navigation_last_click >= 3000);
  if comparasuple_navigation_retry && comparasuple_navigation_retries < 2
    js comparasuple_same_page = comparasuple_evaluate('location.href') === comparasuple_click_page;
    if comparasuple_same_page
      js comparasuple_locate(comparasuple_click_kind); comparasuple_navigation_retries++;
      if comparasuple_click_kind == 'product' && !comparasuple_target.visible
        js comparasuple_kind = 'product'; comparasuple_notches = 3; comparasuple_delta = 490;
        tagui comun/ubicar.tag
      js comparasuple_same_page = comparasuple_evaluate('location.href') === comparasuple_click_page;
      if comparasuple_target.visible && comparasuple_same_page
        tagui comun/clic.tag
      js comparasuple_navigation_last_click = Date.now();
  wait 0.25
js if (!comparasuple_reached && !comparasuple_blocked) throw new Error('No se llegó a la página solicitada: ' + comparasuple_current_url);
