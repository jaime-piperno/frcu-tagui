// La búsqueda o paginación puede dejarnos debajo de la tarjeta elegida.
js comparasuple_kind = 'top'; comparasuple_notches = -8; comparasuple_delta = -900;
tagui comun/ubicar.tag
js comparasuple_kind = 'product'; comparasuple_notches = 3; comparasuple_delta = 490;
tagui comun/ubicar.tag

js comparasuple_label = 'product_image';
tagui comun/clic.tag
tagui comun/esperar.tag
for carga_ficha from 1 to 40
  js comparasuple_blocked = comparasuple_page_blocked(); comparasuple_detail_ready = !comparasuple_blocked && comparasuple_page_ready();
  if comparasuple_blocked || comparasuple_detail_ready
    break
  wait 0.1
tagui comun/avisos.tag

js comparasuple_blocked = comparasuple_blocked || comparasuple_page_blocked();
if !comparasuple_blocked
  if comparasuple_job.human
    js comparasuple_locate('center');
    py scroll_center()
    js comparasuple_check_python(py_result);
    wait 0.15
    tagui comun/avisos.tag
    if !comparasuple_blocked
      js comparasuple_locate('center');
      py move_target()
      js comparasuple_check_python(py_result);
      py scroll(3)
      js comparasuple_check_python(py_result);
  else
    js comparasuple_wheel(500, 'scroll_detail');
    wait 0.15
    tagui comun/avisos.tag
    if !comparasuple_blocked
      js comparasuple_wheel(500, 'scroll_detail');
tagui comun/avisos.tag
