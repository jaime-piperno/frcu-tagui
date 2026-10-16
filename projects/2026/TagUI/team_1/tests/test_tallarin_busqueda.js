// ==============================================================================
// UTN FRCU - Tecnologías para la Automatización (Año 2026)
// test_tallarin_busqueda.js - Test de Verificación de Búsqueda y Validación de Tallarines
// ==============================================================================

const assert = require('assert');
const catalogo = require('../catalogo.js');
const validador = require('../validador.js');

console.log('======================================================================');
console.log('  🧪 TEST: BÚSQUEDA Y VALIDACIÓN DE TALLARÍN EN 3 SUPERMERCADOS');
console.log('======================================================================\n');

// 1. Verificación en Catálogo Cerrado
console.log('📦 1. Verificación de catálogo para fideos_lucchetti_tallarines_500g...');
const { items } = catalogo.cargarCatalogo();
const itemLucchetti = items.find(it => it.id === 'fideos_lucchetti_tallarines_500g');
assert(itemLucchetti, 'Debe existir fideos_lucchetti_tallarines_500g en el catálogo');
assert.strictEqual(itemLucchetti.termino_busqueda, 'tallarin', 'El término de búsqueda debe ser "tallarin"');
assert.strictEqual(itemLucchetti.nombre_completo, 'Fideos Lucchetti Tallarín N5 500 g', 'El nombre completo debe ser "Fideos Lucchetti Tallarín N5 500 g"');
assert.strictEqual(itemLucchetti.variante, 'Tallarín N5', 'La variante debe ser "Tallarín N5"');
console.log('  ✅ [PASS] fideos_lucchetti_tallarines_500g configurado como "' + itemLucchetti.nombre_completo + '" (Variante: ' + itemLucchetti.variante + ') con término "tallarin"');

// 2. Validación de Entrada Gatekeeper
console.log('\n🚪 2. Validación de Entrada...');
const valTallarin = catalogo.validarEntrada('tallarin');
assert(valTallarin.valido, 'Búsqueda "tallarin" debe ser válida en el catálogo');
assert.strictEqual(valTallarin.item.id, 'fideos_lucchetti_tallarines_500g');
console.log('  ✅ [PASS] "tallarin" es aceptado como producto válido');

const valTallarinLucc = catalogo.validarEntrada('tallarin lucchetti');
assert(valTallarinLucc.valido, '"tallarin lucchetti" debe ser válido');
console.log('  ✅ [PASS] "tallarin lucchetti" es aceptado');

const valTallarinLuchetti = catalogo.validarEntrada('tallarin luchetti');
assert(valTallarinLuchetti.valido, '"tallarin luchetti" debe ser válido');
console.log('  ✅ [PASS] "tallarin luchetti" (con una c) es aceptado');

const valN5 = catalogo.validarEntrada('Fideos Lucchetti Tallarín N5 500 g');
assert(valN5.valido, '"Fideos Lucchetti Tallarín N5 500 g" debe ser válido');
console.log('  ✅ [PASS] Nombre completo con N5 es aceptado');

// 3. Diccionario Oficial con nombres reales de los 3 supermercados
console.log('\n📖 3. Verificación de nombres de supermercados según capturas de pantalla...');
const nombreDia = 'Fideos Tallarin N5 Luchetti 500 Gr.';
const nombreCoto = 'Fideos Tallarin N5 Lucchetti 500g';
const nombreCarrefour = 'Fideos tallarin N5 Lucchetti 500 g.';

const matchDia = catalogo.buscarPorDiccionarioSupermercado(nombreDia);
assert(matchDia && matchDia.item, 'Debe coincidir nombre de Día');
assert.strictEqual(matchDia.item.id, 'fideos_lucchetti_tallarines_500g');
console.log('  ✅ [PASS] Día %: "' + nombreDia + '" -> ' + matchDia.item.nombre_completo);

const matchCoto = catalogo.buscarPorDiccionarioSupermercado(nombreCoto);
assert(matchCoto && matchCoto.item, 'Debe coincidir nombre de COTO');
assert.strictEqual(matchCoto.item.id, 'fideos_lucchetti_tallarines_500g');
console.log('  ✅ [PASS] COTO: "' + nombreCoto + '" -> ' + matchCoto.item.nombre_completo);

const matchCarrefour = catalogo.buscarPorDiccionarioSupermercado(nombreCarrefour);
assert(matchCarrefour && matchCarrefour.item, 'Debe coincidir nombre de Carrefour');
assert.strictEqual(matchCarrefour.item.id, 'fideos_lucchetti_tallarines_500g');
console.log('  ✅ [PASS] Carrefour: "' + nombreCarrefour + '" -> ' + matchCarrefour.item.nombre_completo);

// 4. Validación Semántica en validador.js con query oficial
console.log('\n⚖️ 4. Validación Semántica en validador.js con query oficial...');
const queryOficial = 'Fideos Lucchetti Tallarín N5 500 g';

const resDia = validador.validarCoincidencia(queryOficial, { nombre: nombreDia, precio: 1750 });
assert.strictEqual(resDia.estado, 'VALIDADA', 'Día debe ser VALIDADA');
console.log('  ✅ [PASS] Día: ' + resDia.estado + ' (' + resDia.motivo + ')');

const resCoto = validador.validarCoincidencia(queryOficial, { nombre: nombreCoto, precio: 1312.50 });
assert.strictEqual(resCoto.estado, 'VALIDADA', 'COTO debe ser VALIDADA');
console.log('  ✅ [PASS] COTO: ' + resCoto.estado + ' (' + resCoto.motivo + ')');

const resCarrefour = validador.validarCoincidencia(queryOficial, { nombre: nombreCarrefour, precio: 1749 });
assert.strictEqual(resCarrefour.estado, 'VALIDADA', 'Carrefour debe ser VALIDADA');
console.log('  ✅ [PASS] Carrefour: ' + resCarrefour.estado + ' (' + resCarrefour.motivo + ')');

// 5. Validación Semántica en validador.js con query "tallarin"
console.log('\n🔍 5. Validación Semántica con query "tallarin"...');
const resDiaTallarin = validador.validarCoincidencia('tallarin', { nombre: nombreDia, precio: 1750 });
assert.strictEqual(resDiaTallarin.estado, 'VALIDADA', 'Día con query "tallarin" debe ser VALIDADA');
console.log('  ✅ [PASS] Día con "tallarin": ' + resDiaTallarin.estado);

const resCotoTallarin = validador.validarCoincidencia('tallarin', { nombre: nombreCoto, precio: 1312.50 });
assert.strictEqual(resCotoTallarin.estado, 'VALIDADA', 'COTO con query "tallarin" debe ser VALIDADA');
console.log('  ✅ [PASS] COTO con "tallarin": ' + resCotoTallarin.estado);

const resCarrefourTallarin = validador.validarCoincidencia('tallarin', { nombre: nombreCarrefour, precio: 1749 });
assert.strictEqual(resCarrefourTallarin.estado, 'VALIDADA', 'Carrefour con query "tallarin" debe ser VALIDADA');
console.log('  ✅ [PASS] Carrefour con "tallarin": ' + resCarrefourTallarin.estado);

// 6. Verificación de regla de 3 supermercados
console.log('\n🛒 6. Comparación válida de los 3 supermercados...');
const comparacion = validador.validarComparacion3Supermercados([
    { supermercado: 'Carrefour', nombre: nombreCarrefour, precio: 1749, valido: true, stock_status: 'DISPONIBLE' },
    { supermercado: 'COTO', nombre: nombreCoto, precio: 1312.50, valido: true, stock_status: 'DISPONIBLE' },
    { supermercado: 'Día %', nombre: nombreDia, precio: 1750, valido: true, stock_status: 'DISPONIBLE' }
]);
assert(comparacion.comparable, 'La comparación debe ser válida entre los 3 supermercados');
assert.strictEqual(comparacion.supermercadoGanador, 'COTO', 'El ganador de precio debe ser COTO ($1.312,50)');
console.log('  ✅ [PASS] Canasta válida en los 3 supermercados! Ganador: ' + comparacion.supermercadoGanador + ' ($' + comparacion.precioMinimo + ')');

console.log('\n----------------------------------------------------------------------');
console.log('  🎉 TODAS LAS VERIFICACIONES DE TALLARÍN PASARON CON ÉXITO (100%)');
console.log('======================================================================\n');
