// Revisar durante el scroll: algunos avisos aparecen con demora.
js comparasuple_notices_closed = false; comparasuple_blocked = comparasuple_blocked || comparasuple_page_blocked();
if comparasuple_job.human && !comparasuple_blocked
  if comparasuple_force_notices
    py print(dismiss_browser_notices(force=True))
  else
    py print(dismiss_browser_notices())
  js comparasuple_check_python(py_result); comparasuple_notices_closed = String(py_result).trim() === 'True';
js comparasuple_force_notices = false;
for aviso from 1 to 3
  js comparasuple_blocked = comparasuple_blocked || comparasuple_page_blocked();
  if comparasuple_blocked
    break
  js begin
  try {
    comparasuple_locate('popup'); comparasuple_notice_label = 'close_popup';
    if (!comparasuple_target.visible) {comparasuple_locate('consent'); comparasuple_notice_label = 'accept_notice';}
    comparasuple_context_retries = 0;
  } catch (error) {
    // La navegación puede reemplazar el DOM entre dos consultas a Chrome.
    if (!error.transient_context || ++comparasuple_context_retries > 3) throw error;
    comparasuple_target = {visible: false};
  }
  js finish
  if !comparasuple_target.visible
    break
  // No usar clic.tag aquí: produciría una llamada circular.
  js comparasuple_notice_clicked = false;
  if comparasuple_job.human
    py move_target()
    js comparasuple_check_python(py_result);
    js comparasuple_blocked = comparasuple_page_blocked(); comparasuple_notice_clicked = !comparasuple_blocked && comparasuple_hit_test();
    if comparasuple_notice_clicked
      py click_target()
      js comparasuple_check_python(py_result);
  else
    js comparasuple_notice_clicked = comparasuple_click(comparasuple_notice_label);
  js comparasuple_notices_closed = comparasuple_notices_closed || comparasuple_notice_clicked;
  wait 0.3
