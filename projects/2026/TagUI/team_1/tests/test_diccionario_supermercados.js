// ==============================================================================
// UTN FRCU - Tecnologías para la Automatización (Año 2026)
// test_diccionario_supermercados.js - Pruebas del Diccionario de Supermercados
// ==============================================================================

const assert = require('assert');
const catalogo = require('../catalogo.js');
const validador = require('../validador.js');

let totalTests = 0;
let passedTests = 0;

function test(description, fn) {
    totalTests++;
    try {
        fn();
        console.log(`  ✅ [PASS] ${description}`);
        passedTests++;
    } catch (e) {
        console.error(`  ❌ [FAIL] ${description}`);
        console.error(`     Detalle: ${e.message}`);
    }
}

console.log('======================================================================');
console.log('  🧪 SUITE DE PRUEBAS: DICCIONARIO DE NOMBRES DE SUPERMERCADOS');
console.log('======================================================================\n');

console.log('📖 1. Verificación de Nombres Solicitados por el Usuario en Leche La Serenísima...');

const NOMBRES_SOLICITADOS = [
    'Leche Larga Vida Clásica 3% La Serenisima 1 Lt.',
    'Leche Larga Vida Entera Ua Clasica 3% LA SERENISIMA 1l',
    'Leche La serenisima clásica 3% 1L'
];

test('Los 3 nombres requeridos están registrados en catalogo.json para Leche La Serenísima', () => {
    const { items } = catalogo.cargarCatalogo();
    const leche = items.find(it => it.id === 'leche_la_serenisima_entera_1l');
    assert(leche, 'Debe existir el producto leche_la_serenisima_entera_1l');
    assert(Array.isArray(leche.nombres_supermercados), 'Debe tener array nombres_supermercados');
    
    for (const nom of NOMBRES_SOLICITADOS) {
        const normEsperado = catalogo.normalizarTexto(nom);
        const existe = leche.nombres_supermercados.some(n => catalogo.normalizarTexto(n) === normEsperado);
        assert(existe, `El nombre "${nom}" debe estar en nombres_supermercados de Leche La Serenísima`);
    }
});

console.log('\n🔍 2. Búsqueda y Resolución Directa en el Diccionario...');

NOMBRES_SOLICITADOS.forEach((nom, idx) => {
    test(`Nombre ${idx + 1}: "${nom}" resuelve a leche_la_serenisima_entera_1l con score 100`, () => {
        const match = catalogo.buscarPorDiccionarioSupermercado(nom);
        assert(match, 'Debe retornar un objeto match');
        assert.strictEqual(match.match, true, 'Debe coincidir');
        assert.strictEqual(match.item.id, 'leche_la_serenisima_entera_1l');
        assert.strictEqual(match.score, 100, 'Debe tener score máximo de coincidencia exacta');
    });
});

test('Coincidencia parcial/contención con texto de góndola de e-commerce', () => {
    const textoGondola = 'Super Promo! Leche Larga Vida Clásica 3% La Serenisima 1 Lt. Tetra Brik';
    const match = catalogo.buscarPorDiccionarioSupermercado(textoGondola);
    assert(match, 'Debe resolver por contención');
    assert.strictEqual(match.item.id, 'leche_la_serenisima_entera_1l');
});

console.log('\n🛡️ 3. Validación Semántica en validador.js usando Diccionario...');

NOMBRES_SOLICITADOS.forEach((nom, idx) => {
    test(`Validación ${idx + 1}: Búsqueda "Leche La Serenisima Clasica 1L" valida "${nom}"`, () => {
        const resultadoScraper = {
            nombre: nom,
            precio: 1450,
            precioStr: '$1.450',
            stockRaw: 'disponible'
        };
        const val = validador.validarCoincidencia('Leche La Serenisima Clasica 1L', resultadoScraper);
        assert.strictEqual(val.estado, 'VALIDADA', `Debe validar ${nom}`);
        assert.strictEqual(val.valido, true);
        assert(val.motivo.includes('diccionario oficial de supermercados'), 'El motivo debe acreditar el diccionario');
        assert.strictEqual(val.itemCatalogo.id, 'leche_la_serenisima_entera_1l');
    });
});

test('Seguridad: Consulta de Coca Cola rechaza título de Leche La Serenísima', () => {
    const resultadoScraper = {
        nombre: 'Leche Larga Vida Clásica 3% La Serenisima 1 Lt.',
        precio: 1450,
        precioStr: '$1.450',
        stockRaw: 'disponible'
    };
    const val = validador.validarCoincidencia('Coca Cola 2.25L', resultadoScraper);
    assert.strictEqual(val.valido, false, 'No debe validar leche para consulta de coca cola');
    assert.strictEqual(val.estado, 'COINCIDENCIA NO VÁLIDA');
});

console.log('\n➕ 4. Gestión Dinámica del Diccionario (obtener y agregar)...');

test('obtenerDiccionarioSupermercados retorna todos los productos con sus aliases', () => {
    const dicc = catalogo.obtenerDiccionarioSupermercados();
    assert(typeof dicc === 'object');
    assert(Object.keys(dicc).length >= 17, 'Debe contener al menos 17 productos');
    assert(dicc['leche_la_serenisima_entera_1l'].nombres_supermercados.length >= 3);
});

test('agregarNombreSupermercado agrega alias dinámico y permite búsqueda inmediata', () => {
    const nuevoAlias = 'Leche Especial UHT La Serenisima Clasica 1000cm3';
    const agregado = catalogo.agregarNombreSupermercado('leche_la_serenisima_entera_1l', nuevoAlias, false);
    assert.strictEqual(agregado, true, 'Debe agregar nuevo alias');

    const matchNuevo = catalogo.buscarPorDiccionarioSupermercado(nuevoAlias);
    assert(matchNuevo, 'Debe encontrar el nuevo alias');
    assert.strictEqual(matchNuevo.item.id, 'leche_la_serenisima_entera_1l');
});

console.log('\n----------------------------------------------------------------------');
console.log(`  RESULTADO: ${passedTests} de ${totalTests} pruebas pasaron exitosamente.`);
if (passedTests === totalTests) {
    console.log('  🎉 TODAS LAS PRUEBAS DEL DICCIONARIO DE SUPERMERCADOS PASARON CON ÉXITO.\n');
    process.exit(0);
} else {
    console.error(`  ❌ FALLARON ${totalTests - passedTests} PRUEBAS.\n`);
    process.exit(1);
}
