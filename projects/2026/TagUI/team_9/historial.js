const fs = require('fs');
const path = require('path');

const ARCHIVO_PRECIOS = path.join(__dirname, 'historial_precios.jsonl');
const ARCHIVO_ALERTAS = path.join(__dirname, 'alertas_emitidas.jsonl');

function leerJsonl(archivo) {
    if (!fs.existsSync(archivo)) return [];
    const filas = [];
    for (const linea of fs.readFileSync(archivo, 'utf8').split(/\r?\n/)) {
        if (!linea.trim()) continue;
        try { filas.push(JSON.parse(linea)); } catch (e) { /* línea dañada: se ignora */ }
    }
    return filas;
}

function agregarJsonl(archivo, filas) {
    if (!filas.length) return;
    fs.appendFileSync(archivo, filas.map(f => JSON.stringify(f)).join('\n') + '\n', 'utf8');
}

// items: [{ modo, producto, supermercado, precio }]
function guardarCorrida(items) {
    const fecha = new Date().toISOString();
    agregarJsonl(ARCHIVO_PRECIOS, items.map(it => ({ fecha, ...it })));
}

function guardarAlertas(alertas) {
    agregarJsonl(ARCHIVO_ALERTAS, alertas);
}

module.exports = {
    leerHistorial: () => leerJsonl(ARCHIVO_PRECIOS),
    leerAlertas: () => leerJsonl(ARCHIVO_ALERTAS),
    guardarCorrida,
    guardarAlertas
};