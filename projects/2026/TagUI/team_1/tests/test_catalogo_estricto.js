/**
 * tests/test_catalogo_estricto.js
 * 
 * Banco de pruebas automatizado para validar el cumplimiento riguroso del
 * catálogo cerrado, las equivalencias dimensionales exactas, las reglas de
 * descarte semántico y la regla de los 3 supermercados.
 */

const assert = require('assert');
const path = require('path');
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
console.log('  🧪 SUITE DE PRUEBAS: CATÁLOGO CERRADO Y REGLAS ESTRICTAS RPA');
console.log('======================================================================\n');

// ----------------------------------------------------------------------
// 1. CARGA Y ESTRUCTURA DEL CATÁLOGO
// ----------------------------------------------------------------------
console.log('📦 1. Verificación de Carga e Integridad del Catálogo...');

runTest('El catálogo contiene las categorías principales requeridas', () => {
    const { catalogo: cat, items } = catalogo.cargarCatalogo();
    assert.ok(cat.gaseosas && cat.gaseosas.length >= 3, 'Deben existir gaseosas');
    assert.ok(cat.arroz && cat.arroz.length >= 2, 'Debe existir arroz');
    assert.ok(cat.fideos && cat.fideos.length >= 2, 'Deben existir fideos');
    assert.ok(cat.leche && cat.leche.length >= 2, 'Debe existir leche');
    assert.ok(items.length >= 15, 'El catálogo debe contener al menos 15 productos representativos');
});

runTest('Cada producto del catálogo contiene todos los campos obligatorios', () => {
    const { items } = catalogo.cargarCatalogo();
    for (const item of items) {
        assert.ok(item.id, `ID faltante en item: ${JSON.stringify(item)}`);
        assert.ok(item.categoria, `Categoría faltante en: ${item.id}`);
        assert.ok(item.marca, `Marca faltante en: ${item.id}`);
        assert.ok(item.producto, `Producto faltante en: ${item.id}`);
        assert.ok(item.cantidad > 0, `Cantidad inválida en: ${item.id}`);
        assert.ok(['L', 'ml', 'kg', 'g', 'un'].includes(item.unidad), `Unidad inválida en: ${item.id}`);
        assert.ok(item.nombre_completo, `Nombre completo faltante en: ${item.id}`);
    }
});

// ----------------------------------------------------------------------
// 2. EQUIVALENCIA PRESENTACIONES (TOLERANCIA CERO)
// ----------------------------------------------------------------------
console.log('\n⚖️ 2. Pruebas de Equivalencia Dimensional Exacta...');

runTest('Equivalencia de volumen: 2.25 L == 2250 ml', () => {
    assert.strictEqual(catalogo.esPresentacionEquivalente(2.25, 'L', 2250, 'ml'), true);
    assert.strictEqual(catalogo.esPresentacionEquivalente(2250, 'ml', 2.25, 'L'), true);
});

runTest('Equivalencia de volumen: 1 L == 1000 ml', () => {
    assert.strictEqual(catalogo.esPresentacionEquivalente(1, 'L', 1000, 'ml'), true);
});

runTest('Equivalencia de masa: 1 kg == 1000 g', () => {
    assert.strictEqual(catalogo.esPresentacionEquivalente(1, 'kg', 1000, 'g'), true);
    assert.strictEqual(catalogo.esPresentacionEquivalente(500, 'g', 0.5, 'kg'), true);
});

runTest('Rechazo estricto: 2.25 L NO es equivalente a 1.5 L (Diferencia de tamaño)', () => {
    assert.strictEqual(catalogo.esPresentacionEquivalente(2.25, 'L', 1.5, 'L'), false);
});

runTest('Rechazo estricto: 1 kg NO es equivalente a 500 g (Diferencia de tamaño)', () => {
    assert.strictEqual(catalogo.esPresentacionEquivalente(1, 'kg', 500, 'g'), false);
});

runTest('Rechazo por incompatibilidad de magnitud (L vs kg)', () => {
    assert.strictEqual(catalogo.esPresentacionEquivalente(1, 'L', 1, 'kg'), false);
});

// ----------------------------------------------------------------------
// 3. VALIDACIÓN DE ENTRADAS ANTES DE LA BÚSQUEDA (GATEKEEPER)
// ----------------------------------------------------------------------
console.log('\n🚪 3. Validación de Entrada Previa (Gatekeeper del Catálogo)...');

runTest('Acepta búsquedas que coinciden exactamente con productos del catálogo', () => {
    assert.strictEqual(catalogo.validarEntrada('Coca Cola 2.25L').valido, true);
    assert.strictEqual(catalogo.validarEntrada('Sprite 2.25L').valido, true);
    assert.strictEqual(catalogo.validarEntrada('Manaos Cola 2.25L').valido, true);
    assert.strictEqual(catalogo.validarEntrada('Manaos Naranja 2.25L').valido, true);
    assert.strictEqual(catalogo.validarEntrada('Manaos Lima Limon 2.25L').valido, true);
    assert.strictEqual(catalogo.validarEntrada('Arroz Gallo 1kg').valido, true);
    assert.strictEqual(catalogo.validarEntrada('Leche La Serenisima 1L').valido, true);
});

runTest('Acepta objeto con producto, cantidad y unidad existentes en catálogo', () => {
    const res = catalogo.validarEntrada({ producto: 'Arroz Gallo', cantidad: 1, unidad: 'kg' });
    assert.strictEqual(res.valido, true);
    assert.strictEqual(res.item.marca, 'Gallo');
});

runTest('Rechaza términos genéricos que NO pertenecen al catálogo cerrado', () => {
    assert.strictEqual(catalogo.validarEntrada('gaseosa de cola').valido, false);
    assert.strictEqual(catalogo.validarEntrada('arroz barato').valido, false);
    assert.strictEqual(catalogo.validarEntrada('vino tinto').valido, false);
});

runTest('Rechaza marcas fuera del catálogo', () => {
    assert.strictEqual(catalogo.validarEntrada('Gaseosa Cunnington Cola 2.25L').valido, false);
    assert.strictEqual(catalogo.validarEntrada('Arroz Tío Pelon 1kg').valido, false);
});

runTest('Rechaza presentaciones no catalogadas para un producto', () => {
    // Si Coca Cola solo está en 2.25L en el catálogo, 500ml debe ser rechazada
    assert.strictEqual(catalogo.validarEntrada('Coca Cola 500ml').valido, false);
});

// ----------------------------------------------------------------------
// 4. VALIDACIÓN SEMÁNTICA DE RESULTADOS (validador.js)
// ----------------------------------------------------------------------
console.log('\n🔎 4. Validación Semántica de Coincidencias en Supermercados...');

runTest('Coincidencia válida: Coca Cola 2.25 L', () => {
    const res = validador.validarCoincidencia('Coca Cola 2.25L', {
        nombre: 'Gaseosa Coca Cola Sabor Original 2.25 L',
        precio: 3800
    });
    assert.strictEqual(res.estado, 'VALIDADA');
    assert.strictEqual(res.valido, true);
});

runTest('Coincidencia válida: Sprite 2.25 L', () => {
    const res = validador.validarCoincidencia('Sprite 2.25L', {
        nombre: 'Gaseosa Sprite Lima Limon 2.25 L',
        precio: 3600
    });
    assert.strictEqual(res.estado, 'VALIDADA');
    assert.strictEqual(res.valido, true);
});

runTest('Coincidencia válida: Manaos Cola 2.25 L', () => {
    const res = validador.validarCoincidencia('Manaos Cola 2.25L', {
        nombre: 'Gaseosa cola Manaos 2,25 lts',
        precio: 1500
    });
    assert.strictEqual(res.estado, 'VALIDADA');
    assert.strictEqual(res.valido, true);
});

runTest('Rechazo por marca distinta: Manaos Cola 2.25L vs Pepsi Cola 2.25L', () => {
    const res = validador.validarCoincidencia('Manaos Cola 2.25L', {
        nombre: 'Gaseosa Pepsi Cola 2.25 L',
        precio: 1200
    });
    assert.strictEqual(res.estado, 'COINCIDENCIA NO VÁLIDA');
    assert.strictEqual(res.valido, false);
});

runTest('Rechazo por variante distinta: Manaos Cola 2.25L vs Manaos Naranja 2.25L', () => {
    const res = validador.validarCoincidencia('Manaos Cola 2.25L', {
        nombre: 'Gaseosa Naranja Manaos 2.25l',
        precio: 1500
    });
    assert.strictEqual(res.estado, 'COINCIDENCIA NO VÁLIDA');
    assert.strictEqual(res.valido, false);
});

runTest('Rechazo por presentación distinta: Manaos Cola 2.25L vs Manaos Cola 1.5L', () => {
    const res = validador.validarCoincidencia('Manaos Cola 2.25L', {
        nombre: 'Gaseosa Cola Manaos 1.5 L',
        precio: 1100
    });
    assert.strictEqual(res.estado, 'COINCIDENCIA NO VÁLIDA');
    assert.strictEqual(res.valido, false);
});

runTest('Rechazo por presentación distinta: Arroz Gallo 1kg vs Arroz Gallo 500g', () => {
    const res = validador.validarCoincidencia('Arroz Gallo 1kg', {
        nombre: 'Arroz Gallo 500 g',
        precio: 1200
    });
    assert.strictEqual(res.estado, 'COINCIDENCIA NO VÁLIDA');
    assert.strictEqual(res.valido, false);
});

// ----------------------------------------------------------------------
// 5. REGLA DE COMPARABILIDAD EN LOS 3 SUPERMERCADOS
// ----------------------------------------------------------------------
console.log('\n🛒 5. Regla Obligatoria de los 3 Supermercados...');

runTest('Rechaza comparación si falta un supermercado (Día % sin stock o no encontrado)', () => {
    const items = [
        { supermercado: 'Carrefour', valido: true, precio: 1500, stock_status: 'DISPONIBLE', nombre: 'Manaos Cola 2.25L' },
        { supermercado: 'COTO', valido: true, precio: 1550, stock_status: 'DISPONIBLE', nombre: 'Manaos Cola 2.25L' },
        { supermercado: 'Día %', valido: false, precio: null, stock_status: 'NO ENCONTRADO', nombre: 'No encontrado' }
    ];
    const comp = validador.validarComparacion3Supermercados(items);
    assert.strictEqual(comp.comparable, false);
    assert.strictEqual(comp.disponibles, 2);
    assert.strictEqual(comp.supermercadosFaltantes.includes('Día %'), true);
});

runTest('Rechaza comparación si un supermercado devolvió una presentación distinta', () => {
    const items = [
        { supermercado: 'Carrefour', valido: true, precio: 1500, stock_status: 'DISPONIBLE', nombre: 'Manaos Cola 2.25L' },
        { supermercado: 'COTO', valido: true, precio: 1550, stock_status: 'DISPONIBLE', nombre: 'Manaos Cola 2.25L' },
        { supermercado: 'Día %', valido: true, precio: 1100, stock_status: 'DISPONIBLE', nombre: 'Manaos Cola 1.5L' }
    ];
    const comp = validador.validarComparacion3Supermercados(items);
    assert.strictEqual(comp.comparable, false);
    assert.ok(comp.motivo.includes('Presentación discrepante'));
});

runTest('Acepta comparación si el producto es idéntico y disponible en los 3 supermercados', () => {
    const items = [
        { supermercado: 'Carrefour', valido: true, precio: 1500, stock_status: 'DISPONIBLE', nombre: 'Manaos Cola 2.25L' },
        { supermercado: 'COTO', valido: true, precio: 1550, stock_status: 'DISPONIBLE', nombre: 'Manaos Cola 2.25L' },
        { supermercado: 'Día %', valido: true, precio: 1480, stock_status: 'DISPONIBLE', nombre: 'Manaos Cola 2.25L' }
    ];
    const comp = validador.validarComparacion3Supermercados(items);
    assert.strictEqual(comp.comparable, true);
    assert.strictEqual(comp.disponibles, 3);
    assert.strictEqual(comp.precioMinimo, 1480);
    assert.strictEqual(comp.supermercadoGanador, 'Día %');
});

// ----------------------------------------------------------------------
// 6. VALIDACIÓN DEL ARCHIVO input.csv
// ----------------------------------------------------------------------
console.log('\n📄 6. Verificación del Archivo input.csv...');

runTest('El archivo input.csv actual cumple 100% con el catálogo cerrado', () => {
    const csvPath = path.join(__dirname, '..', 'input.csv');
    const res = catalogo.validarArchivoCSV(csvPath);
    assert.strictEqual(res.valido, true, `input.csv tiene filas inválidas: ${JSON.stringify(res.filasInvalidas)}`);
    assert.ok(res.totalFilas >= 1, 'input.csv debe contener al menos 1 producto de canasta');
});

// ----------------------------------------------------------------------
// RESUMEN
// ----------------------------------------------------------------------
console.log('\n----------------------------------------------------------------------');
console.log(`  RESULTADO: ${passedTests} de ${totalTests} pruebas pasaron exitosamente.`);
if (passedTests === totalTests) {
    console.log('  🎉 TODAS LAS PRUEBAS DEL CATÁLOGO Y VALIDACIONES PASARON CON ÉXITO.\n');
    process.exit(0);
} else {
    console.error(`  ❌ FALLARON ${totalTests - passedTests} PRUEBAS.\n`);
    process.exit(1);
}
