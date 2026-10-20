const assert = require('assert');
const validador = require('../validador.js');
const catalogo = require('../catalogo.js');

console.log('======================================================================');
console.log('🧪 TEST: BÚSQUEDA DE COCA COLA EN CARREFOUR Y REUSO DE BÚSQUEDAS');
console.log('======================================================================\n');

// 1. Adaptación de término para Carrefour
console.log('🥤 1. Prueba de adaptación de término para Carrefour...');
const terminoCarrefour = validador.adaptarTerminoSupermercado('Coca Cola 2.25L', 'Carrefour');
assert.strictEqual(terminoCarrefour, 'Coca Cola 2,25 lts', 'Debe convertir 2.25L a 2,25 lts');

const terminoCarrefourConEspacio = validador.adaptarTerminoSupermercado('Coca Cola 2.25 L', 'Carrefour');
assert.strictEqual(terminoCarrefourConEspacio, 'Coca Cola 2,25 lts', 'Debe convertir 2.25 L a 2,25 lts');

const terminoCoto = validador.adaptarTerminoSupermercado('Coca Cola 2.25 L', 'COTO');
assert.strictEqual(terminoCoto, 'Coca Cola 2.25 L', 'COTO debe mantener formato con punto');

const terminoDia = validador.adaptarTerminoSupermercado('Coca Cola 2.25 L', 'Día %');
assert.strictEqual(terminoDia, 'Coca Cola 2.25 L', 'Día % debe mantener formato con punto');
console.log('  ✅ [PASS] Formato de término de búsqueda en Carrefour adaptado a coma y lts sin punto.');

// 2. Reconocimiento de nombre exacto de Carrefour
console.log('\n🏪 2. Prueba de validación de título exacto de Carrefour...');
const nombreCarrefour = 'Gaseosa cola Coca Cola sabor original 2,25 lts';
const valC = validador.validarCoincidencia('Coca Cola', {
    nombre: nombreCarrefour,
    precio: 4999,
    cantidad: 2.25,
    unidad: 'L'
});
assert.strictEqual(valC.estado, 'VALIDADA');
assert.strictEqual(valC.valido, true);
console.log('  ✅ [PASS] Título "Gaseosa cola Coca Cola sabor original 2,25 lts" validado como VALIDADA.');

// 3. Catálogo cerrado contiene el alias y término
console.log('\n📚 3. Verificación de catálogo para Coca Cola...');
const itemCoca = catalogo.buscarEnCatalogo({ producto: 'Coca Cola', cantidad: 2.25, unidad: 'L' });
assert.ok(itemCoca, 'Debe existir Coca Cola 2.25L en catálogo');
assert.ok(itemCoca.nombres_supermercados.includes(nombreCarrefour), 'Debe incluir nombre exacto de Carrefour');
console.log('  ✅ [PASS] Catálogo cerrado incluye el nombre exacto de Carrefour.');

// 4. Verificación de término de búsqueda de Manaos
console.log('\n🔄 4. Verificación de término de búsqueda idéntico para sabores de Manaos...');
const itemManaosCola = catalogo.buscarEnCatalogo({ producto: 'Manaos Cola', cantidad: 2.25, unidad: 'L' });
const itemManaosNaranja = catalogo.buscarEnCatalogo({ producto: 'Manaos Naranja', cantidad: 2.25, unidad: 'L' });
const itemManaosLima = catalogo.buscarEnCatalogo({ producto: 'Manaos Lima Limón', cantidad: 2.25, unidad: 'L' });

assert.strictEqual(itemManaosCola.termino_busqueda, 'manaos');
assert.strictEqual(itemManaosNaranja.termino_busqueda, 'manaos');
assert.strictEqual(itemManaosLima.termino_busqueda, 'manaos');
console.log('  ✅ [PASS] Los 3 sabores de Manaos comparten exactamente el término "manaos" en el catálogo.');

console.log('\n----------------------------------------------------------------------');
console.log('🎉 TODAS LAS PRUEBAS DE COCA COLA Y REUSO PASARON EXITOSAMENTE.');
