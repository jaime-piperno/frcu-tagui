const assert = require('assert');
const catalogo = require('../catalogo.js');
const validador = require('../validador.js');

console.log('======================================================================');
console.log('  🧪 TEST ESPECÍFICO: AISLAMIENTO Y DIFERENCIACIÓN DE SABORES MANAOS');
console.log('======================================================================');

// 1. Verificación en Catálogo Cerrado
console.log('\n📦 1. Verificación en catálogo cerrado...');
const colaItem = catalogo.buscarEnCatalogo('Manaos Cola 2.25 L');
const naranjaItem = catalogo.buscarEnCatalogo('Manaos Naranja 2.25 L');
const limaItem = catalogo.buscarEnCatalogo('Manaos Lima Limón 2.25 L');

assert.strictEqual(colaItem.id, 'gaseosa_manaos_cola_225l', 'Cola debe tener id gaseosa_manaos_cola_225l');
assert.strictEqual(colaItem.producto, 'Manaos Cola', 'Cola debe tener producto "Manaos Cola"');
assert.strictEqual(colaItem.variante, 'Cola', 'Cola debe tener variante "Cola"');
assert.strictEqual(colaItem.termino_busqueda, 'manaos', 'Cola debe tener termino_busqueda "manaos"');
console.log('  ✅ [PASS] Manaos Cola verificado en catálogo');

assert.strictEqual(naranjaItem.id, 'gaseosa_manaos_naranja_225l', 'Naranja debe tener id gaseosa_manaos_naranja_225l');
assert.strictEqual(naranjaItem.producto, 'Manaos Naranja', 'Naranja debe tener producto "Manaos Naranja"');
assert.strictEqual(naranjaItem.variante, 'Naranja', 'Naranja debe tener variante "Naranja"');
assert.strictEqual(naranjaItem.termino_busqueda, 'manaos', 'Naranja debe tener termino_busqueda "manaos"');
console.log('  ✅ [PASS] Manaos Naranja verificado en catálogo');

assert.strictEqual(limaItem.id, 'gaseosa_manaos_lima_limon_225l', 'Lima Limón debe tener id gaseosa_manaos_lima_limon_225l');
assert.strictEqual(limaItem.producto, 'Manaos Lima Limón', 'Lima Limón debe tener producto "Manaos Lima Limón"');
assert.strictEqual(limaItem.variante, 'Lima Limón', 'Lima Limón debe tener variante "Lima Limón"');
assert.strictEqual(limaItem.termino_busqueda, 'manaos', 'Lima Limón debe tener termino_busqueda "manaos"');
console.log('  ✅ [PASS] Manaos Lima Limón verificado en catálogo');

// 2. Validación de Entrada (validarEntrada)
console.log('\n🚪 2. Verificación de validarEntrada...');
const vCola = catalogo.validarEntrada({ producto: 'Manaos Cola', cantidad: 2.25, unidad: 'L' });
assert.strictEqual(vCola.valido, true);
assert.strictEqual(vCola.item.id, 'gaseosa_manaos_cola_225l');
console.log('  ✅ [PASS] validarEntrada({ producto: "Manaos Cola", 2.25, "L" }) -> gaseosa_manaos_cola_225l');

const vNaranja = catalogo.validarEntrada({ producto: 'Manaos Naranja', cantidad: 2.25, unidad: 'L' });
assert.strictEqual(vNaranja.valido, true);
assert.strictEqual(vNaranja.item.id, 'gaseosa_manaos_naranja_225l');
console.log('  ✅ [PASS] validarEntrada({ producto: "Manaos Naranja", 2.25, "L" }) -> gaseosa_manaos_naranja_225l');

const vLima = catalogo.validarEntrada({ producto: 'Manaos Lima Limón', cantidad: 2.25, unidad: 'L' });
assert.strictEqual(vLima.valido, true);
assert.strictEqual(vLima.item.id, 'gaseosa_manaos_lima_limon_225l');
console.log('  ✅ [PASS] validarEntrada({ producto: "Manaos Lima Limón", 2.25, "L" }) -> gaseosa_manaos_lima_limon_225l');

// 3. Validación Semántica Cruzada (validador.validarCoincidencia)
console.log('\n🔎 3. Validación Semántica Cruzada (validador.validarCoincidencia)...');

// Aceptaciones
const mColaOk = validador.validarCoincidencia('Manaos Cola 2.25L', { nombre: 'Gaseosa Cola Manaos 2.25l', precio: 1500 });
assert.strictEqual(mColaOk.estado, 'VALIDADA');
console.log('  ✅ [PASS] Aceptación: Manaos Cola con "Gaseosa Cola Manaos 2.25l"');

const mNaranjaOk = validador.validarCoincidencia('Manaos Naranja 2.25L', { nombre: 'Gaseosa Naranja Manaos 2.25l', precio: 1500 });
assert.strictEqual(mNaranjaOk.estado, 'VALIDADA');
console.log('  ✅ [PASS] Aceptación: Manaos Naranja con "Gaseosa Naranja Manaos 2.25l"');

const mLimaOk = validador.validarCoincidencia('Manaos Lima Limón 2.25L', { nombre: 'Gaseosa Lima Limón Manaos 2.25l', precio: 1500 });
assert.strictEqual(mLimaOk.estado, 'VALIDADA');
console.log('  ✅ [PASS] Aceptación: Manaos Lima Limón con "Gaseosa Lima Limón Manaos 2.25l"');

// Rechazos de cruce de sabor (El error que reportó el usuario)
const mNaranjaVsCola = validador.validarCoincidencia('Manaos Naranja 2.25L', { nombre: 'Gaseosa Cola Manaos 2.25l', precio: 1500 });
assert.strictEqual(mNaranjaVsCola.estado, 'COINCIDENCIA NO VÁLIDA', 'Manaos Naranja NO debe aceptar Cola');
console.log('  ✅ [PASS] Rechazo estricto: Búsqueda de Manaos Naranja rechaza sabor Cola');

const mLimaVsCola = validador.validarCoincidencia('Manaos Lima Limón 2.25L', { nombre: 'Gaseosa Cola Manaos 2.25l', precio: 1500 });
assert.strictEqual(mLimaVsCola.estado, 'COINCIDENCIA NO VÁLIDA', 'Manaos Lima Limón NO debe aceptar Cola');
console.log('  ✅ [PASS] Rechazo estricto: Búsqueda de Manaos Lima Limón rechaza sabor Cola');

const mColaVsNaranja = validador.validarCoincidencia('Manaos Cola 2.25L', { nombre: 'Gaseosa Naranja Manaos 2.25l', precio: 1500 });
assert.strictEqual(mColaVsNaranja.estado, 'COINCIDENCIA NO VÁLIDA', 'Manaos Cola NO debe aceptar Naranja');
console.log('  ✅ [PASS] Rechazo estricto: Búsqueda de Manaos Cola rechaza sabor Naranja');

const mColaVsLima = validador.validarCoincidencia('Manaos Cola 2.25L', { nombre: 'Gaseosa Lima Limón Manaos 2.25l', precio: 1500 });
assert.strictEqual(mColaVsLima.estado, 'COINCIDENCIA NO VÁLIDA', 'Manaos Cola NO debe aceptar Lima Limón');
console.log('  ✅ [PASS] Rechazo estricto: Búsqueda de Manaos Cola rechaza sabor Lima Limón');

// 4. Simulación de extracción en tarjetas de supermercado
console.log('\n🤖 4. Simulación de selección entre tarjetas simultáneas de Carrefour/COTO/Día...');
const tarjetasSimultaneas = [
    { name: 'Gaseosa Cola Manaos 2.25l', price: '$ 1.500' },
    { name: 'Gaseosa Naranja Manaos 2.25l', price: '$ 1.500' },
    { name: 'Gaseosa Lima Limón Manaos 2.25l', price: '$ 1.500' }
];

function seleccionarMejorTarjeta(itemObj) {
    const itemCat = catalogo.buscarEnCatalogo(itemObj);
    const queryStr = itemObj.producto || itemObj.nombre_completo || '';
    const baseConfig = validador.obtenerConfiguracionBusqueda(queryStr);
    const config = {
        ...baseConfig,
        marca: itemCat ? itemCat.marca : baseConfig.marca,
        variante: itemCat ? itemCat.variante : (baseConfig.variantesRequeridas[0] || null),
        cantidad: itemCat ? itemCat.cantidad : null,
        unidad: itemCat ? itemCat.unidad : null,
        palabrasMarca: ['manaos'],
        marcasCompetidoras: Array.from(validador.MARCAS_CONOCIDAS || []),
        nombresSupermercados: (itemCat && itemCat.nombres_supermercados) ? itemCat.nombres_supermercados.map(n => validador.normalizar(n)) : []
    };

    function cleanText(s) {
        return s.toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '').replace(/(\d+)\s*%/g, '$1%').replace(/[.,;:!¡?¿()[\]\"'\-_/]/g, ' ').replace(/\s+/g, ' ').trim();
    }
    function contienePalabra(texto, palabra) {
        var rx = new RegExp('(?:^|\\s)' + palabra + '(?:$|\\s)', 'i');
        return rx.test(texto);
    }

    let best = null;
    let bestScore = -1;

    for (const c of tarjetasSimultaneas) {
        const nClean = cleanText(c.name);
        
        if (config.variante) {
            var varNorm = cleanText(config.variante);
            var esBase = ['original', 'tradicional', 'clasica', 'clasico', 'comun', 'entera', 'suave'].some(b => varNorm.indexOf(b) > -1);
            if (!esBase) {
                if (varNorm.indexOf('lima') > -1 || varNorm.indexOf('limon') > -1) {
                    if (nClean.indexOf('lima') === -1 && nClean.indexOf('limon') === -1) continue;
                    if (['cola', 'naranja', 'pomelo', 'tonica', 'guarana'].some(vOp => contienePalabra(nClean, vOp))) continue;
                } else if (varNorm.indexOf('naranja') > -1) {
                    if (nClean.indexOf('naranja') === -1) continue;
                    if (['cola', 'pomelo', 'lima', 'limon', 'tonica', 'guarana'].some(vOp => contienePalabra(nClean, vOp))) continue;
                } else if (varNorm.indexOf('cola') > -1) {
                    if (nClean.indexOf('cola') === -1) continue;
                    if (['naranja', 'pomelo', 'lima', 'limon', 'tonica', 'guarana'].some(vOp => contienePalabra(nClean, vOp))) continue;
                } else if (nClean.indexOf(varNorm) === -1) {
                    continue;
                }
            } else {
                if (['zero', 'light', 'diet', 'sin azucar'].some(vOp => contienePalabra(nClean, vOp))) continue;
                if (varNorm.indexOf('cola') > -1) {
                    if (['naranja', 'pomelo', 'lima', 'limon', 'tonica', 'guarana'].some(vOp => contienePalabra(nClean, vOp))) continue;
                }
            }
        }

        let score = 50;
        if (config.nombresSupermercados) {
            for (const alias of config.nombresSupermercados) {
                if (alias === nClean) { score += 250; break; }
                else if (nClean.includes(alias) || alias.includes(nClean)) { score += 180; break; }
            }
        }
        if (score > bestScore) {
            bestScore = score;
            best = { name: c.name, score };
        }
    }
    return best;
}

const selNaranja = seleccionarMejorTarjeta({ id: 'gaseosa_manaos_naranja_225l', producto: 'Manaos Naranja 2.25 L', variante: 'Naranja', cantidad: 2.25, unidad: 'L' });
assert.strictEqual(selNaranja.name, 'Gaseosa Naranja Manaos 2.25l', 'Búsqueda Naranja debe elegir la tarjeta de Naranja');
console.log('  ✅ [PASS] Cuando se busca Manaos Naranja -> Elige "Gaseosa Naranja Manaos 2.25l" (Score: ' + selNaranja.score + ')');

const selLima = seleccionarMejorTarjeta({ id: 'gaseosa_manaos_lima_limon_225l', producto: 'Manaos Lima Limón 2.25 L', variante: 'Lima Limón', cantidad: 2.25, unidad: 'L' });
assert.strictEqual(selLima.name, 'Gaseosa Lima Limón Manaos 2.25l', 'Búsqueda Lima Limón debe elegir la tarjeta de Lima Limón');
console.log('  ✅ [PASS] Cuando se busca Manaos Lima Limón -> Elige "Gaseosa Lima Limón Manaos 2.25l" (Score: ' + selLima.score + ')');

const selCola = seleccionarMejorTarjeta({ id: 'gaseosa_manaos_cola_225l', producto: 'Manaos Cola 2.25 L', variante: 'Cola', cantidad: 2.25, unidad: 'L' });
assert.strictEqual(selCola.name, 'Gaseosa Cola Manaos 2.25l', 'Búsqueda Cola debe elegir la tarjeta de Cola');
console.log('  ✅ [PASS] Cuando se busca Manaos Cola -> Elige "Gaseosa Cola Manaos 2.25l" (Score: ' + selCola.score + ')');

console.log('\n----------------------------------------------------------------------');
console.log('  🎉 TODOS LOS TESTS DE DIFERENCIACIÓN DE SABORES PASARON CON ÉXITO.');
console.log('======================================================================');
