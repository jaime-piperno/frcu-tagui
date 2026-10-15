// Buscar con scroll hasta encontrar el elemento o llegar al final.
js comparasuple_locate(comparasuple_kind); comparasuple_previous = -1; comparasuple_still = 0; comparasuple_scroll_reposition = true;
// El puente py no interpola estas variables: compartimos el número como JSON.
if comparasuple_job.human
  js require('fs').write('human_scroll.json', JSON.stringify(comparasuple_notches), 'w');
for paso from 1 to 60
  tagui comun/avisos.tag
  if comparasuple_blocked
    break
  js comparasuple_locate(comparasuple_kind);
  js comparasuple_uncovered = comparasuple_escape_hover();
  if comparasuple_uncovered
    wait 0.35
    js comparasuple_locate(comparasuple_kind);
  if comparasuple_target.visible
    break
  // Mover el cursor al área de scroll sólo cuando haga falta.
  if comparasuple_scroll_reposition || comparasuple_notices_closed
    js comparasuple_locate('center');
    if comparasuple_job.human
      py move_target()
      js comparasuple_check_python(py_result);
    else
      js comparasuple_move('scroll_area');
    js comparasuple_scroll_reposition = false;
  if comparasuple_job.human
    py scroll(read_json('human_scroll.json'))
    js comparasuple_check_python(py_result);
  else
    js comparasuple_wheel(comparasuple_delta);
  wait 0.3
  tagui comun/avisos.tag
  js comparasuple_scroll_reposition = comparasuple_notices_closed;
  js begin
  comparasuple_locate(comparasuple_kind);
  comparasuple_position = comparasuple_evaluate('window.pageYOffset');
  comparasuple_still = comparasuple_position === comparasuple_previous ? comparasuple_still + 1 : 0;
  comparasuple_previous = comparasuple_position;
  if (comparasuple_notices_closed) comparasuple_still = 0;
  js finish
  if comparasuple_still >= 2
    break
