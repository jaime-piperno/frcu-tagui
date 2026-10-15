// Reintentar el acceso si un aviso interrumpe la contraseña.
js comparasuple_secret = ''; comparasuple_secret_letters = []; comparasuple_login = !!comparasuple_adapter.selectors.login_input;
if comparasuple_login
  js comparasuple_access_granted = false; comparasuple_retry_search = true;
  for acceso from 1 to 3
    tagui comun/avisos.tag
    if comparasuple_blocked
      break
    js comparasuple_locate('login_input');
    if !comparasuple_target.visible
      js begin
      comparasuple_access_granted = comparasuple_dom(function (data) {
        var fields = document.querySelectorAll(data.selector);
        for (var i = 0; i < fields.length; i++) {
          if (fields[i].getClientRects().length && getComputedStyle(fields[i]).visibility !== 'hidden') return false;
        }
        return true;
      }, {selector: comparasuple_adapter.selectors.login_input});
      js finish
      if comparasuple_access_granted
        break
      continue

    // La clave queda en memoria; no se escribe en los archivos de trabajo.
    js comparasuple_secret = require('system').env[comparasuple_job.access_env] || '';
    js if (!comparasuple_secret) throw new Error('Falta la variable de entorno para acceder a esta tienda.');
    js comparasuple_label = 'login_input';
    tagui comun/clic.tag
    js comparasuple_ready = comparasuple_clicked && comparasuple_field_ready('login_input', '', false);
    if !comparasuple_ready
      js comparasuple_secret = '';
      continue
    if comparasuple_job.human
      py select_query()
      js comparasuple_check_python(py_result);
    else
      js comparasuple_select_query();

    // Python recibe el índice, nunca el texto de la contraseña.
    js begin
    comparasuple_secret_letters = comparasuple_secret.match(/[\uD800-\uDBFF][\uDC00-\uDFFF]|[\s\S]/g) || [];
    for (var caracter_acceso = 0; caracter_acceso < comparasuple_secret_letters.length; caracter_acceso++) {
      comparasuple_wait_character();
      comparasuple_ready = comparasuple_field_ready('login_input', '', false);
      if (!comparasuple_ready) break;
      if (comparasuple_job.human) {
        require('fs').write('human_index.json', JSON.stringify(caracter_acceso), 'w');
        comparasuple_python("credential_character(read_json('human_index.json'))");
      } else comparasuple_type_character(comparasuple_secret_letters[caracter_acceso]);
    }
    js finish
    tagui comun/avisos.tag
    js comparasuple_ready = comparasuple_field_ready('login_input', comparasuple_secret, true); comparasuple_secret = ''; comparasuple_secret_letters = [];
    if !comparasuple_ready
      continue

    js comparasuple_locate('login_submit'); comparasuple_label = 'login_submit';
    tagui comun/clic.tag
    if !comparasuple_clicked
      continue
    for espera_acceso from 1 to 60
      tagui comun/avisos.tag
      if comparasuple_blocked
        break
      js begin
      try {
        comparasuple_locate('login_input');
        if (!comparasuple_target.visible) {
          comparasuple_locate('input');
          comparasuple_access_granted = comparasuple_target.visible;
        }
      } catch (error) {comparasuple_access_granted = false;}
      js finish
      if comparasuple_access_granted
        break
      wait 0.25
    if comparasuple_access_granted || comparasuple_blocked
      break
  js comparasuple_retry_search = false;
  js if (!comparasuple_blocked && !comparasuple_access_granted) throw new Error('La tienda no confirmó el acceso; revisar la clave o los avisos del sitio.');
js comparasuple_secret = ''; comparasuple_secret_letters = [];
