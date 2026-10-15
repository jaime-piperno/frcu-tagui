// Si un aviso aparece al mover el mouse, cerrarlo y repetir el mismo clic.
js comparasuple_clicked = false; comparasuple_click_kind = comparasuple_target.kind; comparasuple_click_page = comparasuple_evaluate('location.href');
for intento_clic from 1 to 3
  tagui comun/avisos.tag
  if comparasuple_blocked
    break
  js comparasuple_locate(comparasuple_click_kind);
  js comparasuple_uncovered = comparasuple_escape_hover();
  if comparasuple_uncovered
    wait 0.35
    js comparasuple_locate(comparasuple_click_kind);
  if comparasuple_target.visible
    if comparasuple_job.human
      py move_target()
      js comparasuple_check_python(py_result);
      js comparasuple_blocked = comparasuple_page_blocked(); comparasuple_clicked = !comparasuple_blocked && comparasuple_hit_test();
      if comparasuple_clicked
        py click_target()
        js comparasuple_check_python(py_result);
    else
      js comparasuple_clicked = comparasuple_click(comparasuple_label);
  if comparasuple_clicked || comparasuple_blocked
    break
  wait 0.3
js if (!comparasuple_clicked && !comparasuple_retry_search && !comparasuple_optional_click && !comparasuple_blocked) throw new Error('El elemento está tapado antes del clic: ' + comparasuple_label);
