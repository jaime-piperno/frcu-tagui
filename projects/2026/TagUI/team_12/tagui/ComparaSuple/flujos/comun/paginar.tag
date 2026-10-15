// Si Siguiente no tiene URL, comprobar la página activa antes de pulsar.
js if (comparasuple_job.expected_page && !comparasuple_url_matches('previous')) throw new Error('La página activa no es la anterior al avance solicitado.');
js comparasuple_kind = comparasuple_job.action === 'next' ? (comparasuple_job.expected_page ? 'next' : 'link') : 'loadmore';
js comparasuple_notches = 3; comparasuple_delta = 490;
tagui comun/ubicar.tag
js comparasuple_label = comparasuple_job.action;
tagui comun/clic.tag
if comparasuple_job.action == 'next'
  tagui comun/esperar.tag
// Cargar más conserva la URL; esperar a que aparezcan las tarjetas.
if comparasuple_job.action == 'load_more'
  wait 3
