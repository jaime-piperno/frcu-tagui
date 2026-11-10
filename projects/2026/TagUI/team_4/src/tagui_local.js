function ruta_con_barras(ruta) {
  return require('fs').absolute(String(ruta).replace(/\\/g, '/')).replace(/\\/g, '/');
}

function carpeta_escritorio() {
  return ruta_con_barras(require('system').env.USERPROFILE + '/Desktop');
}

var ENCABEZADOS_PLANILLA = ['N°', 'Fecha y hora', 'Código de curso', 'Curso', 'Nombre y apellido', 'DNI', 'Email', 'Teléfono', 'ID de chat'];
var COLUMNA_NUMERO = 0, COLUMNA_CODIGO = 2, COLUMNA_DNI = 5;

function texto_para_excel(valor) {
  var texto = String(valor === undefined || valor === null ? '' : valor).replace(/["\r\n\t]/g, ' ');
  texto = texto.replace(/[^\x00-\x7F]/g, function (caracter) { return '" & ChrW(' + caracter.charCodeAt(0) + ') & "'; });
  return "'" + texto;
}

function encabezados_planilla() {
  var fila = [];
  for (var i = 0; i < ENCABEZADOS_PLANILLA.length; i++) fila.push(texto_para_excel(ENCABEZADOS_PLANILLA[i]));
  return [fila];
}

function filas_como_lista(filas) {
  if (!(filas instanceof Array)) return [];
  if (filas.length > 0 && !(filas[0] instanceof Array)) return [filas];
  return filas;
}

function inscriptos_desde_filas(filas) {
  filas = filas_como_lista(filas);
  var inscriptos = [];
  for (var i = 1; i < filas.length; i++) {
    var codigo = String(filas[i][COLUMNA_CODIGO] || '').replace(/^\s+|\s+$/g, '').toLowerCase();
    var dni = String(filas[i][COLUMNA_DNI] || '').replace(/\D/g, '');
    if (codigo === '' && dni === '') continue;
    inscriptos.push({codigo: codigo, dni: dni, numero: parseInt(filas[i][COLUMNA_NUMERO], 10) || 0});
  }
  return inscriptos;
}

function proxima_fila(filas) {
  return filas_como_lista(filas).length + 1;
}

function proximo_numero(filas) {
  filas = filas_como_lista(filas);
  var mayor = 0;
  for (var i = 1; i < filas.length; i++) mayor = Math.max(mayor, parseInt(filas[i][COLUMNA_NUMERO], 10) || 0);
  return mayor + 1;
}

function fecha_hora_actual() {
  var ahora = new Date();
  function dos(n) { return (n < 10 ? '0' : '') + n; }
  return dos(ahora.getDate()) + '/' + dos(ahora.getMonth() + 1) + '/' + ahora.getFullYear() + ' ' + dos(ahora.getHours()) + ':' + dos(ahora.getMinutes());
}

function fila_preinscripcion(numero, registro, chat_id) {
  return [[String(numero), texto_para_excel(fecha_hora_actual()), texto_para_excel(registro.codigo),
    texto_para_excel(registro.curso), texto_para_excel(registro.nombre), texto_para_excel(registro.dni),
    texto_para_excel(registro.email), texto_para_excel(registro.telefono), texto_para_excel(chat_id)]];
}

function fila_guardada(fila_releida, registro) {
  var fila = filas_como_lista(fila_releida)[0];
  if (!fila) return false;
  return String(fila[COLUMNA_DNI]).replace(/\D/g, '') === registro.dni &&
    String(fila[COLUMNA_CODIGO]).replace(/^\s+|\s+$/g, '').toLowerCase() === registro.codigo;
}

function minimizar_chrome() {
  try {
    var ventana = JSON.parse(chrome_step('Browser.getWindowForTarget', {})).result;
    chrome_step('Browser.setWindowBounds', {windowId: ventana.windowId, bounds: {windowState: 'minimized'}});
    return {windowId: ventana.windowId, estado: ventana.bounds.windowState};
  } catch (e) {
    return null;
  }
}

function restaurar_chrome(ventana) {
  if (!ventana) return;
  try {
    chrome_step('Browser.setWindowBounds', {windowId: ventana.windowId, bounds: {windowState: 'normal'}});
    if (ventana.estado === 'maximized' || ventana.estado === 'fullscreen')
      chrome_step('Browser.setWindowBounds', {windowId: ventana.windowId, bounds: {windowState: ventana.estado}});
  } catch (e) {}
}

function identificador_de_chat(hash, titulo) {
  var id = decodeURIComponent(String(hash || '')).replace(/^#/, '');
  if (id) return id;
  return titulo ? 'nombre:' + titulo : '';
}
