/**
 * tests/test_busqueda_subcadenas.js
 * 
 * Banco de pruebas automatizado para validar la búsqueda por subcadenas
 * dentro de las validaciones del sistema (catalogo.js y validador.js),
 * asegurando la obtención de la mayor cantidad de coincidencias posibles.
 */

const assert = require('assert');
const catalogo = require('../catalogo.js');
const validador = require('../validador.js');

let totalTests = 0;
let passedTests = 0;

function runTest(nombre, fn) {
    totalTests++;
    try {
        fn();
        console.log(`  ✅ [PASS] ${nombre}`);
        passedTests++;
    } catch (err) {
        console.error(`  ❌ [FAIL] ${nombre}: ${err.message}`);
    }
}

console.log('======================================================================');
console.log('  🧪 SUITE DE PRUEBAS: BÚSQUEDA POR SUBCADENAS EN VALIDACIONES');
console.log('======================================================================\n');

// ----------------------------------------------------------------------
// 1. EXTRACCIÓN DE SUBCADENAS (catalogo.js y validador.js)
// ----------------------------------------------------------------------
console.log('🔍 1. Pruebas de Descomposición en Subcadenas...');

runTest('extraerSubcadenas descompone tokens, n-gramas y raíces', () => {
    const subs = catalogo.extraerSubcadenas('Arroz Gallo Largo Fino');
    assert.ok(subs.includes('arroz'), 'Debe incluir token individual arroz');
    assert.ok(subs.includes('gallo'), 'Debe incluir token individual gallo');
    assert.ok(subs.includes('arroz gallo'), 'Debe incluir bigrama arroz gallo');
    assert.ok(subs.includes('gallo largo fino'), 'Debe incluir trigrama gallo largo fino');
    assert.ok(subs.includes('arroz gallo largo fino'), 'Debe incluir frase completa');
    assert.ok(subs.includes('arro'), 'Debe incluir subcadena/raíz de palabra larga');
});

runTest('extraerSubcadenas maneja textos vacíos o nulos limpiamente', () => {
    assert.deepStrictEqual(catalogo.extraerSubcadenas(null), []);
    assert.deepStrictEqual(catalogo.extraerSubcadenas(''), []);
    assert.deepStrictEqual(catalogo.extraerSubcadenas('   '), []);
});

// ----------------------------------------------------------------------
// 2. MÁXIMA CANTIDAD DE COINCIDENCIAS (buscarPorSubcadenas en catalogo.js)
// ----------------------------------------------------------------------
console.log('\n📦 2. Pruebas de Máxima Cantidad de Coincidencias en Catálogo...');

runTest('Búsqueda por subcadena "arroz" obtiene todos los arroces del catálogo (2/2)', () => {
    const res = catalogo.buscarPorSubcadenas('arroz');
    assert.strictEqual(res.length, 2, 'Deben encontrarse los 2 productos de arroz');
    assert.ok(res.every(r => r.cantidadCoincidencias > 0), 'Todos deben tener coincidencias > 0');
    assert.ok(res.every(r => r.subcadenasCoincidentes.includes('arroz')), 'Todos deben coincidir en "arroz"');
});

runTest('Búsqueda por subcadena "gaseosa" obtiene todas las gaseosas del catálogo (5/5)', () => {
    const res = catalogo.buscarPorSubcadenas('gaseosa');
    assert.strictEqual(res.length, 5, 'Deben encontrarse las 5 gaseosas del catálogo');
    const marcas = res.map(r => r.item.marca);
    assert.ok(marcas.includes('Coca Cola'), 'Debe incluir Coca Cola');
    assert.ok(marcas.includes('Sprite'), 'Debe incluir Sprite');
    assert.ok(marcas.includes('Manaos'), 'Debe incluir Manaos');
});

runTest('Búsqueda por subcadena "fideos" obtiene todos los fideos del catálogo (2/2)', () => {
    const res = catalogo.buscarPorSubcadenas('fideos');
    assert.strictEqual(res.length, 2, 'Deben encontrarse los 2 fideos del catálogo');
});

runTest('Búsqueda por subcadena "leche" obtiene todas las leches del catálogo (2/2)', () => {
    const res = catalogo.buscarPorSubcadenas('leche');
    assert.strictEqual(res.length, 2, 'Deben encontrarse las 2 leches del catálogo');
});

// ----------------------------------------------------------------------
// 3. RELEVANCIA Y ORDENAMIENTO POR AFINIDAD (Score y Coincidencias)
// ----------------------------------------------------------------------
console.log('\n🎯 3. Pruebas de Priorización y Ranking por Score...');

runTest('"arroz gallo" prioriza Arroz Gallo en primer lugar frente a Lucchetti', () => {
    const res = catalogo.buscarPorSubcadenas('arroz gallo');
    assert.ok(res.length >= 2, 'Debe obtener múltiples coincidencias');
    assert.strictEqual(res[0].item.marca, 'Gallo', 'El primer lugar debe ser Gallo');
    assert.ok(res[0].score > res[1].score, 'Gallo debe tener mayor score que Lucchetti');
    assert.strictEqual(res[1].item.marca, 'Lucchetti', 'El segundo lugar debe ser Lucchetti (coincide en arroz)');
});

runTest('"gaseosa de cola" obtiene Manaos Cola y Coca Cola con máxima coincidencia', () => {
    const res = catalogo.buscarPorSubcadenas('gaseosa de cola');
    assert.ok(res.length >= 2, 'Debe obtener al menos 2 coincidencias de gaseosas cola');
    const primeros2 = res.slice(0, 2).map(r => r.item.nombre_completo);
    assert.ok(primeros2.some(n => n.includes('Coca Cola')), 'Debe incluir Coca Cola en top');
    assert.ok(primeros2.some(n => n.includes('Manaos')), 'Debe incluir Manaos en top');
});

runTest('Búsqueda por prefijo/raíz "sereni" encuentra Leche La Serenísima', () => {
    const res = catalogo.buscarPorSubcadenas('sereni');
    assert.ok(res.length >= 1, 'Debe encontrar al menos 1 coincidencia');
    assert.strictEqual(res[0].item.marca, 'La Serenísima');
});

runTest('Búsqueda por prefijo/raíz "mataraz" encuentra Fideos Matarazzo', () => {
    const res = catalogo.buscarPorSubcadenas('mataraz');
    assert.ok(res.length >= 1, 'Debe encontrar al menos 1 coincidencia');
    assert.strictEqual(res[0].item.marca, 'Matarazzo');
});

runTest('Búsqueda con presentación "2.25L" prioriza gaseosas de 2.25 L', () => {
    const res = catalogo.buscarPorSubcadenas('Coca Cola 2.25L');
    assert.ok(res.length >= 1);
    assert.strictEqual(res[0].item.id, 'gaseosa_coca_cola_225l');
    assert.strictEqual(res[0].coincidePresentacion, true);
});

// ----------------------------------------------------------------------
// 4. INTEGRACIÓN EN validarEntrada (catalogo.js)
// ----------------------------------------------------------------------
console.log('\n🚪 4. Pruebas de Subcadenas dentro de validarEntrada...');

runTest('validarEntrada incluye array de coincidencias completas al validar con éxito', () => {
    const val = catalogo.validarEntrada('Coca Cola 2.25L');
    assert.strictEqual(val.valido, true);
    assert.ok(Array.isArray(val.coincidencias), 'Debe incluir array de coincidencias');
    assert.ok(val.coincidencias.length >= 1, 'Debe contener al menos 1 coincidencia');
    assert.strictEqual(val.totalCoincidencias, val.coincidencias.length);
});

runTest('validarEntrada para término genérico incluye todas las sugerencias por subcadena', () => {
    const val = catalogo.validarEntrada('gaseosa de cola');
    assert.strictEqual(val.valido, false);
    assert.ok(Array.isArray(val.coincidencias));
    assert.ok(val.coincidencias.length >= 2, 'Debe incluir las alternativas de gaseosa cola');
    assert.ok(val.opciones.length >= 2, 'opciones debe poblarse con los nombres coincidentes');
    assert.ok(val.opciones.includes('Manaos Cola 2.25 L'));
    assert.ok(val.opciones.includes('Coca Cola Original 2.25 L'));
});

// ----------------------------------------------------------------------
// 5. MÓDULO validador.js: buscarPorSubcadenas y validarCoincidencia
// ----------------------------------------------------------------------
console.log('\n🔎 5. Pruebas de Subcadenas en validador.js...');

runTest('validador.calcularCoincidenciasSubcadenas mide similitud y porcentaje', () => {
    const match = validador.calcularCoincidenciasSubcadenas('Coca Cola 2.25L', 'Gaseosa Coca Cola Sabor Original 2.25 L');
    assert.ok(match.cantidad >= 4, 'Debe detectar múltiples subcadenas coincidentes');
    assert.ok(match.coincidentes.includes('coca'), 'Debe incluir coca');
    assert.ok(match.coincidentes.includes('cola'), 'Debe incluir cola');
    assert.ok(match.score > 50, 'Score debe ser alto');
    assert.ok(match.porcentaje >= 0.8, 'Porcentaje de tokens debe ser >= 80%');
});

runTest('validador.buscarPorSubcadenas en lista externa de candidatos extraídos', () => {
    const candidatos = [
        { nombre: 'Gaseosa Coca Cola Original 2.25 L', precio: 3800 },
        { nombre: 'Gaseosa Manaos Cola 2.25 L', precio: 1200 },
        { nombre: 'Fideos Lucchetti Tallarines 500 g', precio: 1100 }
    ];
    const res = validador.buscarPorSubcadenas('coca cola', candidatos);
    assert.strictEqual(res.length, 2, 'Deben coincidir las dos gaseosas cola');
    assert.strictEqual(res[0].candidato.nombre, 'Gaseosa Coca Cola Original 2.25 L', 'Coca Cola debe ser primera');
    assert.strictEqual(res[1].candidato.nombre, 'Gaseosa Manaos Cola 2.25 L', 'Manaos Cola debe ser segunda');
});

runTest('validarCoincidencia enriquece los resultados con subcadenas y cantidad', () => {
    const rVal = validador.validarCoincidencia('Coca Cola 2.25L', {
        nombre: 'Gaseosa Coca Cola Sabor Original 2.25 L',
        precio: 3800
    });
    assert.strictEqual(rVal.estado, 'VALIDADA');
    assert.ok(Array.isArray(rVal.subcadenasCoincidentes), 'Debe contener subcadenasCoincidentes');
    assert.ok(rVal.cantidadCoincidencias > 0, 'cantidadCoincidencias debe ser > 0');
    assert.ok(typeof rVal.porcentajeCoincidencia === 'number', 'porcentajeCoincidencia debe ser numérico');
});

console.log('\n----------------------------------------------------------------------');
console.log(`  RESULTADO: ${passedTests} de ${totalTests} pruebas pasaron exitosamente.`);
if (passedTests === totalTests) {
    console.log('  🎉 TODAS LAS PRUEBAS DE BÚSQUEDA POR SUBCADENAS PASARON CON ÉXITO.\n');
    process.exit(0);
} else {
    console.error('  ❌ ALGUNAS PRUEBAS FALLARON.\n');
    process.exit(1);
}
