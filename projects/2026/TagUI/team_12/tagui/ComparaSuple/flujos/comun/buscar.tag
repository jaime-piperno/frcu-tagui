// Reintentar en la misma página si un aviso interrumpe la búsqueda.
js comparasuple_retry_search = true; comparasuple_reached = false;
for busqueda from 1 to 3
  js begin
  if (comparasuple_search_attempts) {
    comparasuple_search_retries.push(comparasuple_search_retry_reason);
    casper.echo('AVISO: reintento de búsqueda (' + comparasuple_search_retry_reason + ').');
  }
  comparasuple_search_attempts++;
  comparasuple_search_retry_reason = 'buscador sin foco';
  js finish
  js comparasuple_blocked = comparasuple_blocked || comparasuple_page_blocked();
  if comparasuple_blocked
    break
  tagui comun/avisos.tag
  js comparasuple_kind = 'input'; comparasuple_notches = -3; comparasuple_delta = -490;
  tagui comun/ubicar.tag
  js comparasuple_label = 'search_input';
  tagui comun/clic.tag
  js comparasuple_ready = comparasuple_clicked && comparasuple_search_ready(false);
  if !comparasuple_ready
    js comparasuple_force_notices = true;
    continue

  if comparasuple_job.human
    py select_query()
    js comparasuple_check_python(py_result);
  else
    js comparasuple_select_query();
  // Comprobar el foco entre letras; un solo bloque evita demoras de CasperJS.
  js begin
  comparasuple_letters = comparasuple_job.query.match(/[\uD800-\uDBFF][\uDC00-\uDFFF]|[\s\S]/g) || [];
  for (var letra = 0; letra < comparasuple_letters.length; letra++) {
    comparasuple_wait_character();
    comparasuple_ready = comparasuple_search_ready(false);
    if (!comparasuple_ready) break;
    if (comparasuple_job.human) {
      require('fs').write('human_character.json', JSON.stringify(comparasuple_letters[letra]), 'w');
      comparasuple_python("type_character(read_json('human_character.json'))");
    } else comparasuple_type_character(comparasuple_letters[letra]);
  }
  js finish
  js comparasuple_ready = comparasuple_search_ready(true);
  if !comparasuple_ready
    js comparasuple_force_notices = true; comparasuple_search_retry_reason = 'texto incompleto o foco interrumpido';
    tagui comun/avisos.tag
    continue

  js comparasuple_locate('submit'); comparasuple_label = 'search_submit';
  tagui comun/clic.tag
  if !comparasuple_clicked
    js comparasuple_search_retry_reason = 'botón de búsqueda cubierto';
    continue
  js comparasuple_search_retry_reason = 'URL de resultados no confirmada';
  for espera_busqueda from 1 to 60
    js comparasuple_reached = comparasuple_url_matches('search'); comparasuple_blocked = comparasuple_page_blocked();
    if comparasuple_reached || comparasuple_blocked
      break
    // La navegación puede destruir el DOM anterior mientras llega la respuesta.
    js try {comparasuple_locate('popup');} catch (error) {comparasuple_target = {visible:false};}
    if comparasuple_target.visible
      break
    wait 0.25
  if comparasuple_reached || comparasuple_blocked
    break
js comparasuple_retry_search = false;
js if (!comparasuple_reached && !comparasuple_blocked) throw new Error('No se pudo completar la búsqueda; comprobar avisos o foco del buscador. URL: ' + comparasuple_current_url);
