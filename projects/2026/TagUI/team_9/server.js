const path = require('path');
const fs = require('fs');

function cargarVariablesEntorno() {
    const archivo = path.join(__dirname, '.env');
    if (!fs.existsSync(archivo)) return;

    for (const linea of fs.readFileSync(archivo, 'utf8').split(/\r?\n/)) {
        const coincidencia = linea.match(/^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*?)\s*$/);
        if (!coincidencia) continue;

        const clave = coincidencia[1];
        let valor = coincidencia[2].trim();
        if ((valor.startsWith('"') && valor.endsWith('"')) || (valor.startsWith("'") && valor.endsWith("'"))) {
            valor = valor.slice(1, -1);
        }
        if (typeof process.env[clave] === 'undefined') process.env[clave] = valor;
    }
}

// Node.js no carga .env por defecto. Cargarlo antes del notificador y de leer la configuración.
cargarVariablesEntorno();

const express = require('express');
const http = require('http');
const { WebSocketServer } = require('ws');
const { exec, execSync } = require('child_process');
const notificador = require('./notificador.js');
const historial = require('./historial.js');

function getValidador() {
    try {
        delete require.cache[require.resolve('./validador.js')];
    } catch(e) {}
    return require('./validador.js');
}

function getCatalogo() {
    try {
        delete require.cache[require.resolve('./catalogo.js')];
    } catch(e) {}
    return require('./catalogo.js');
}

function getRpaRunner() {
    try {
        delete require.cache[require.resolve('./rpa_runner.js')];
    } catch(e) {}
    return require('./rpa_runner.js');
}

// ==============================================================================
// ALERTAS DE TELEGRAM E HISTORIAL DE PRECIOS
// ==============================================================================
const UMBRAL_BAJA_PCT = parseFloat(process.env.UMBRAL_BAJA_PCT) || 10;

// Resultados válidos y con precio de un modo ('compra_mes' o 'individual')
function itemsValidos(modo, registrosFuente) {
    const v = getValidador();
    const registros = Array.isArray(registrosFuente) ? registrosFuente : v.leerResultadosCSV();
    return registros
        .filter(it => it.modo === modo && it.precio !== null && v.validarCoincidencia(it.producto, it).valido)
        .map(it => ({ modo: it.modo, producto: it.producto, supermercado: it.supermercado, precio: it.precio }));
}

// Compara los precios nuevos contra el historial guardado
function detectarAlertas(previo, actuales) {
    const alertas = [];
    const fecha = new Date().toISOString();
    for (const it of actuales) {
        const hist = previo.filter(h => h.producto === it.producto
            && h.supermercado === it.supermercado
            && (!h.modo || !it.modo || h.modo === it.modo)
            && Number.isFinite(Number(h.precio)));
        if (hist.length === 0) continue;

        const ultimo = Number(hist[hist.length - 1].precio);
        const minimo = Math.min(...hist.map(h => Number(h.precio)));
        const precioNuevo = Number(it.precio);
        if (!(ultimo > 0) || !Number.isFinite(precioNuevo)) continue;
        const pct = ((ultimo - precioNuevo) / ultimo) * 100;
        const base = { fecha, modo: it.modo, producto: it.producto, supermercado: it.supermercado, precioNuevo };

        if (pct >= UMBRAL_BAJA_PCT) {
            alertas.push({ ...base, tipo: 'BAJA', precioAnterior: ultimo, pct: Math.round(pct) });
        } else if (hist.length >= 2 && precioNuevo < minimo) {
            alertas.push({ ...base, tipo: 'MINIMO_HISTORICO', precioAnterior: minimo, pct: Math.round(((minimo - precioNuevo) / minimo) * 100) });
        }
    }
    return alertas;
}

function textoAlerta(a) {
    const m = getValidador().formatoMoneda;
    if (a.tipo === 'BAJA') {
        return `📉 ${a.producto} en ${a.supermercado}: ${m(a.precioAnterior)} → ${m(a.precioNuevo)} (-${a.pct}%)`;
    }
    return `🔥 ${a.producto} en ${a.supermercado}: ${m(a.precioNuevo)}, nuevo mínimo histórico (el anterior era ${m(a.precioAnterior)})`;
}

// Resumen acotado a la canasta y los resultados de una ejecución concreta.
function resumenCanasta(productosSolicitados, resultadosEjecucion) {
    const v = getValidador();
    const supermercados = ['Carrefour', 'COTO', 'Día %'];
    const solicitados = Array.isArray(productosSolicitados) ? productosSolicitados : [];
    const items = Array.isArray(resultadosEjecucion)
        ? resultadosEjecucion.filter(it => it.modo === 'compra_mes')
        : [];
    const porProducto = new Map();
    for (const it of items) {
        const clave = claveProductoDashboard(it.producto);
        if (!clave) continue;
        if (!porProducto.has(clave)) porProducto.set(clave, {});
        porProducto.get(clave)[it.supermercado] = it;
    }

    const cobertura = Object.fromEntries(supermercados.map(s => [s, 0]));
    const totales = Object.fromEntries(supermercados.map(s => [s, 0]));
    for (const solicitado of solicitados) {
        const producto = typeof solicitado === 'string' ? solicitado : solicitado.producto;
        const filas = porProducto.get(claveProductoDashboard(producto)) || {};
        for (const supermercado of supermercados) {
            const fila = filas[supermercado];
            const precio = fila && fila.precio !== null && fila.precio !== undefined
                ? Number(fila.precio)
                : (fila ? v.parsePrecio(fila.precioStr) : null);
            if (!fila || !Number.isFinite(precio) || precio <= 0) continue;
            cobertura[supermercado]++;
            totales[supermercado] += precio;
        }
    }

    const totalProductos = solicitados.length;
    const rankingCompleto = Object.entries(totales)
        .filter(([s]) => totalProductos > 0 && cobertura[s] === totalProductos)
        .sort((a, b) => a[1] - b[1]);
    const nombresCanasta = solicitados.map(item => typeof item === 'string' ? item : item.producto).filter(Boolean);
    const lineasTotales = supermercados.map(s => {
        const completa = totalProductos > 0 && cobertura[s] === totalProductos;
        const titulo = completa ? `${s}:` : `${s} (suma parcial):`;
        return `${s === 'Carrefour' ? '🔵' : (s === 'COTO' ? '🔴' : '🟡')} ${titulo} ${cobertura[s] ? v.formatoMoneda(totales[s]) : 'sin precio'}`;
    });
    const listadoProductos = nombresCanasta.map(producto => `• ${producto}`).join('\n');
    const conveniencia = rankingCompleto.length >= 2
        ? `✨ Conviene ${rankingCompleto[0][0]}: ahorras ${v.formatoMoneda(rankingCompleto[rankingCompleto.length - 1][1] - rankingCompleto[0][1])} frente a ${rankingCompleto[rankingCompleto.length - 1][0]}.`
        : '✨ No hay precios completos en al menos dos supermercados para comparar la canasta.';

    return `🛒 CANASTA PROCESADA · ${totalProductos} productos\n${listadoProductos}\n\n`
        + `💵 TOTALES OBSERVADOS\n${lineasTotales.join('\n')}\n\n${conveniencia}`;
}

let ultimaCanastaDashboard = null;

function claveProductoDashboard(producto) {
    return String(producto || '')
        .normalize('NFD')
        .replace(/[\u0300-\u036f]/g, '')
        .toLowerCase()
        .replace(/[^a-z0-9]+/g, ' ')
        .trim();
}

function resumenCanastaDashboard() {
    const v = getValidador();
    const supermercados = ['Carrefour', 'COTO', 'Día %'];
    const registros = v.leerResultadosCSV().filter(it => it.modo === 'compra_mes');
    let solicitados = ultimaCanastaDashboard && Array.isArray(ultimaCanastaDashboard.productosSolicitados)
        ? ultimaCanastaDashboard.productosSolicitados
        : [];

    // Después de reiniciar el servidor, reconstruir la última canasta desde sus filas guardadas.
    if (!solicitados.length) {
        const vistos = new Set();
        solicitados = registros.reduce((lista, it) => {
            const clave = claveProductoDashboard(it.producto);
            if (clave && !vistos.has(clave)) {
                vistos.add(clave);
                lista.push({ producto: it.producto, cantidad: it.cantidad, unidad: it.unidad });
            }
            return lista;
        }, []);
    }
    if (!solicitados.length) return null;

    const filasPorProducto = new Map();
    for (const it of registros) {
        const clave = claveProductoDashboard(it.producto);
        if (!clave) continue;
        if (!filasPorProducto.has(clave)) filasPorProducto.set(clave, {});
        // Si hay más de una fila para tienda y producto, conservar la última registrada.
        filasPorProducto.get(clave)[it.supermercado] = it;
    }

    const cobertura = Object.fromEntries(supermercados.map(s => [s, 0]));
    const totalesParciales = Object.fromEntries(supermercados.map(s => [s, 0]));
    const productos = solicitados.map(solicitado => {
        const producto = typeof solicitado === 'string' ? solicitado : solicitado.producto;
        const filas = filasPorProducto.get(claveProductoDashboard(producto)) || {};
        const precios = {};
        const estados = {};
        for (const supermercado of supermercados) {
            const fila = filas[supermercado];
            const validacion = fila ? v.validarCoincidencia(producto, fila) : null;
            const precio = fila && (fila.precio !== null && fila.precio !== undefined
                ? Number(fila.precio)
                : v.parsePrecio(fila.precioStr));
            const precioEncontrado = fila && Number.isFinite(precio) && precio > 0;
            precios[supermercado] = precioEncontrado ? precio : null;
            if (fila && precioEncontrado) {
                cobertura[supermercado]++;
                totalesParciales[supermercado] += precio;
            }
            estados[supermercado] = fila
                ? (validacion ? validacion.estado : 'Sin resultado')
                : 'Sin resultado';
        }

        const disponibles = supermercados.filter(s => Number.isFinite(precios[s]));
        const ganador = disponibles.length >= 2
            ? disponibles.reduce((mejor, s) => precios[s] < precios[mejor] ? s : mejor, disponibles[0])
            : null;
        return { producto, precios, estados, ganador };
    });

    const cantidadProductos = productos.length;
    const totales = Object.fromEntries(supermercados.map(s => [
        s,
        cobertura[s] === cantidadProductos ? totalesParciales[s] : null
    ]));
    const rankingCompleto = Object.entries(totales)
        .filter(([, total]) => Number.isFinite(total))
        .sort((a, b) => a[1] - b[1]);

    return {
        productos,
        cantidadProductos,
        cobertura,
        totales,
        totalesParciales,
        mejor: rankingCompleto.length >= 2 ? rankingCompleto[0][0] : null,
        peor: rankingCompleto.length >= 2 ? rankingCompleto[rankingCompleto.length - 1][0] : null,
        ahorro: rankingCompleto.length >= 2
            ? rankingCompleto[rankingCompleto.length - 1][1] - rankingCompleto[0][1]
            : null
    };
}

process.on('uncaughtException', (err) => {
    console.error('[UNCAUGHT EXCEPTION]:', err);
});
process.on('unhandledRejection', (reason, promise) => {
    console.error('[UNHANDLED REJECTION]:', reason);
});

const app = express();
const server = http.createServer(app);
const PORT = 3000;

server.on('error', (err) => {
    console.error('[HTTP SERVER ERROR]:', err);
});

// Servidor WebSocket integrado en /ws/rpa-stream
const wss = new WebSocketServer({ server, path: '/ws/rpa-stream' });
const wsClients = new Set();

wss.on('error', (err) => {
    console.error('[WSS ERROR]:', err);
});

// Control de concurrencia: máximo 1 ejecución simultánea
let isRpaRunning = false;
let ultimoProcesoData = null;
let currentTaguiProcess = null;
let currentTaguiChromePidsBefore = null;

wss.on('connection', (ws) => {
    wsClients.add(ws);
    // Enviar estado actual al cliente que recién se conecta
    if (isRpaRunning) {
        ws.send(JSON.stringify({ type: 'status', state: 'live', message: 'Navegador RPA conectado' }));
    } else {
        ws.send(JSON.stringify({ type: 'status', state: 'idle', message: 'RPA en espera' }));
    }

    ws.on('close', () => {
        wsClients.delete(ws);
        // Si el usuario cierra la pestaña o ventana del frontend mientras corre el RPA, abortar de inmediato
        if (wsClients.size === 0 && isRpaRunning) {
            console.log('[WS] Frontend desconectado. Abortando RPA inmediatamente...');
            if (currentTaguiProcess) {
                terminarProcesoTagUI(currentTaguiProcess);
                currentTaguiProcess = null;
            }
            cerrarNavegadorTagUI(currentTaguiChromePidsBefore).catch(() => {});
            try {
                getRpaRunner().abortCurrentRun();
            } catch (e) {}
            isRpaRunning = false;
        }
    });

    ws.on('error', () => {
        wsClients.delete(ws);
    });
});

function broadcast(msgObj) {
    const payload = JSON.stringify(msgObj);
    for (const ws of wsClients) {
        if (ws.readyState === ws.OPEN) {
            try {
                ws.send(payload);
            } catch (e) {}
        }
    }
}

app.use(express.json());
app.use(express.static(path.join(__dirname, 'public')));

function runCommand(command) {
    return new Promise((resolve) => {
        exec(command, (error, stdout, stderr) => {
            if (error) {
                console.error(`Error ejecutando: ${command}`);
                console.error(stderr);
                resolve({ success: false, output: stdout, error: error.message || stderr });
            } else {
                resolve({ success: true, output: stdout });
            }
        });
    });
}

async function generarReporteExcel() {
    const resultado = await runCommand('node generar_excel.js');
    if (!resultado.success) throw new Error(`No se pudo generar el reporte Excel: ${resultado.error}`);
    if (!fs.existsSync(path.join(__dirname, 'reporte_supermercados.xlsx'))) {
        throw new Error('El generador terminó, pero no se encontró reporte_supermercados.xlsx.');
    }
}

// Endpoint para obtener último proceso
app.get('/api/ultimo-proceso', (req, res) => {
    res.json({ success: true, data: ultimoProcesoData });
});

// Endpoint para obtener todos los datos procesados para el mini-navegador interactivo
app.get('/api/datos-completos', (req, res) => {
    try {
        const csvPath = path.join(__dirname, 'resultados.csv');
        if (!fs.existsSync(csvPath)) {
            return res.json({ success: true, items: [], ultimoProceso: ultimoProcesoData });
        }
        const vEngine = getValidador();
        const items = vEngine.leerResultadosCSV(csvPath);
        items.forEach(it => {
            const v = vEngine.validarCoincidencia(it.producto, it);
            it.estado = v.estado;
            it.valido = v.valido;
            it.motivo = v.motivo;
            it.intencion = v.intencion;
        });
        res.json({ success: true, items, ultimoProceso: ultimoProcesoData });
    } catch(e) {
        res.status(500).json({ success: false, message: e.message });
    }
});

// Endpoint para obtener el catálogo cerrado estructurado o filtrar por subcadenas
app.get('/api/catalogo', (req, res) => {
    try {
        const catEngine = getCatalogo();
        const { catalogo: catData, items } = catEngine.cargarCatalogo();
        const categorias = catEngine.listarCategorias();
        const q = req.query.q || req.query.buscar || req.query.subcadena;
        let coincidencias = null;
        if (q && typeof q === 'string') {
            coincidencias = catEngine.buscarPorSubcadenas(q.trim());
        }
        res.json({ success: true, catalogo: catData, items, categorias, coincidencias });
    } catch(e) {
        res.status(500).json({ success: false, message: e.message });
    }
});

// Endpoint para búsqueda de productos por subcadenas con máxima cantidad de coincidencias
app.get('/api/buscar-subcadenas', (req, res) => {
    try {
        const q = req.query.q || req.query.buscar || '';
        const catEngine = getCatalogo();
        const coincidencias = catEngine.buscarPorSubcadenas(q);
        res.json({ success: true, query: q, total: coincidencias.length, coincidencias });
    } catch(e) {
        res.status(500).json({ success: false, message: e.message });
    }
});

// Endpoint para descargar reporte_supermercados.xlsx
app.get('/api/descargar-excel', (req, res) => {
    const file = path.join(__dirname, 'reporte_supermercados.xlsx');
    if (fs.existsSync(file)) {
        res.download(file, 'reporte_supermercados.xlsx');
    } else {
        res.status(404).send('Reporte no encontrado');
    }
});

// Endpoint para descargar resultados.csv
app.get('/api/descargar-csv', (req, res) => {
    const file = path.join(__dirname, 'resultados.csv');
    if (fs.existsSync(file)) {
        res.download(file, 'resultados.csv');
    } else {
        res.status(404).send('Archivo CSV no encontrado');
    }
});

// Endpoint para leer contenido de resultados.csv
app.get('/api/csv-raw', (req, res) => {
    try {
        const file = path.join(__dirname, 'resultados.csv');
        if (fs.existsSync(file)) {
            const data = fs.readFileSync(file, 'utf8');
            res.json({ success: true, csv: data });
        } else {
            res.json({ success: true, csv: '' });
        }
    } catch(e) {
        res.status(500).json({ success: false, message: e.message });
    }
});

app.get('/api/historial', (req, res) => {
    try {
        const registros = historial.leerHistorial().filter(it => it.precio !== null && it.precio !== '' && Number.isFinite(Number(it.precio)));
        const productos = [...new Set(registros.map(it => it.producto).filter(Boolean))]
            .sort((a, b) => a.localeCompare(b, 'es'));
        const solicitado = typeof req.query.producto === 'string' ? req.query.producto : '';
        const producto = solicitado || productos[0] || null;
        const serie = producto
            ? registros.filter(it => it.producto === producto).sort((a, b) => String(a.fecha || '').localeCompare(String(b.fecha || '')))
            : [];
        res.json({ success: true, productos, producto, serie });
    } catch (e) {
        res.status(500).json({ success: false, message: e.message });
    }
});

app.get('/api/alertas', (req, res) => {
    try {
        const alertas = historial.leerAlertas().sort((a, b) => String(b.fecha || '').localeCompare(String(a.fecha || '')));
        res.json({ success: true, alertas });
    } catch (e) {
        res.status(500).json({ success: false, message: e.message });
    }
});

app.get('/api/resumen-canasta', (req, res) => {
    try {
        res.json({ success: true, resumen: resumenCanastaDashboard() });
    } catch (e) {
        res.status(500).json({ success: false, message: e.message });
    }
});

// Endpoint para Compra del Mes
app.post('/api/compra-mes', async (req, res) => {
    if (isRpaRunning) {
        return res.status(409).json({ success: false, message: "El RPA ya está ejecutándose." });
    }

    // Validación estricta previa contra el catálogo cerrado
    const catEngine = getCatalogo();
    const valCsv = catEngine.validarArchivoCSV('input.csv');
    if (!valCsv.valido) {
        return res.status(400).json({
            success: false,
            message: 'El archivo input.csv contiene productos que no pertenecen al catálogo cerrado.',
            filasInvalidas: valCsv.filasInvalidas
        });
    }

    isRpaRunning = true;
    broadcast({ type: 'status', state: 'connecting', message: 'Conectando con el navegador...' });
    let itemsCanasta = [];

    try {
        // Cerrar Excel obligatoriamente si el usuario lo tiene abierto para evitar bloqueos EBUSY
        try {
            execSync('taskkill /F /IM EXCEL.EXE', { windowsHide: true, stdio: 'ignore' });
        } catch (eKill) {}

        // Limpiar registros de compra del mes anteriores para iniciar con datos frescos
        // (el historial de precios vive aparte, en historial_precios.jsonl)
        getValidador().limpiarResultados('1');

        console.log("Iniciando compra del mes...");

        // Leer input.csv validado
        if (fs.existsSync('input.csv')) {
            const lines = fs.readFileSync('input.csv', 'utf8').split('\n');
            for (let i = 1; i < lines.length; i++) {
                const line = lines[i].trim();
                if (line) {
                    const parts = line.split(',');
                    const prod = parts[0] ? parts[0].trim() : '';
                    const cant = parts[1] ? (parseFloat(parts[1]) || 1) : 1;
                    const unid = parts[2] ? parts[2].trim() : '';
                    const unidades = parts[3] ? (parseInt(parts[3], 10) || 1) : 1;
                    if (prod) itemsCanasta.push({ producto: prod, cantidad: cant, unidad: unid, unidades });
                }
            }
        }

        if (itemsCanasta.length === 0) {
            itemsCanasta = [
                { producto: 'Leche La Serenísima Clásica 1 L', cantidad: 1, unidad: 'L' },
                { producto: 'Arroz Gallo Largo Fino 1 kg', cantidad: 1, unidad: 'kg' },
                { producto: 'Fideos Matarazzo Tallarines 500 g', cantidad: 500, unidad: 'g' },
                { producto: 'Aceite Cocinero Girasol 1.5 L', cantidad: 1.5, unidad: 'L' }
            ];
        }

        const productosSolicitados = itemsCanasta.map(item => ({ ...item }));
        ultimaCanastaDashboard = { productosSolicitados, fecha: new Date().toISOString() };
        ultimoProcesoData = {
            producto: 'Compra del Mes',
            cantidad: productosSolicitados.length,
            unidad: 'ítems',
            productosSolicitados,
            items: []
        };

        broadcast({ type: 'log', message: `Iniciando compra mensual para ${itemsCanasta.length} productos...` });

        const { demoMode = true, typingDelay = 50, mouseDuration = 600 } = req.body || {};

        const resultados = await getRpaRunner().runRPA({
            modo: 'compra_mes',
            items: itemsCanasta,
            demoMode,
            typingDelay,
            mouseDuration,
            onStatus: (st) => {
                if (st.type === 'log') {
                    broadcast({ type: 'log', message: st.message });
                } else if (st.type === 'progress') {
                    broadcast({ type: 'progress', percent: st.percent, message: st.message });
                    broadcast({ type: 'log', message: st.message });
                } else if (st.type === 'connected') {
                    broadcast({ type: 'status', state: 'live', message: st.message });
                } else if (st.type === 'finished') {
                    broadcast({ type: 'status', state: 'finished', message: st.message });
                } else if (st.type === 'nav') {
                    broadcast(st);
                } else if (st.type === 'error') {
                    broadcast({ type: 'status', state: st.state || 'error', message: st.message });
                    broadcast({ type: 'log', message: st.message });
                }
            }
        });

        const resultadosNormalizados = getValidador().leerResultadosCSV()
            .filter(it => it.modo === 'compra_mes');
        ultimoProcesoData = {
            producto: 'Compra del Mes',
            cantidad: itemsCanasta.length,
            unidad: 'ítems',
            productosSolicitados: itemsCanasta.map(item => ({ ...item })),
            items: resultadosNormalizados.length ? resultadosNormalizados : resultados
        };

        // Generar Excel consolidado
        try {
            execSync('taskkill /F /IM EXCEL.EXE', { windowsHide: true, stdio: 'ignore' });
        } catch (eKill) {}
        await generarReporteExcel();

        // Historial de precios + alertas de Telegram
        const actuales = itemsValidos('compra_mes', resultadosNormalizados);
        const alertas = detectarAlertas(historial.leerHistorial(), actuales);  // primero comparar...
        historial.guardarCorrida(actuales);                                    // ...y después guardar
        historial.guardarAlertas(alertas);

        const mensajesTelegram = [];
        if (alertas.length > 0) {
            const extra = alertas.length > 20 ? `\n...y ${alertas.length - 20} más` : '';
            mensajesTelegram.push('🔔 Alertas de precio:\n' + alertas.slice(0, 20).map(textoAlerta).join('\n') + extra);
        }
        mensajesTelegram.push(`✅ Compra del mes terminada: ${itemsCanasta.length} productos comparados.`);
        const resumen = resumenCanasta(itemsCanasta, resultadosNormalizados);
        if (resumen) mensajesTelegram.push(resumen);
        await Promise.all(mensajesTelegram.map(notificador.enviar));

        if (!res.headersSent && !res.destroyed) {
            res.json({
                success: true,
                message: "Compra del mes finalizada. Resultados visibles en el dashboard; puedes descargar el reporte Excel.",
                data: ultimoProcesoData
            });
        }
    } catch (e) {
        console.error("Error en compra del mes:", e);
        if (itemsCanasta.length) {
            const productosSolicitados = itemsCanasta.map(item => ({ ...item }));
            const resultadosParciales = getValidador().leerResultadosCSV()
                .filter(it => it.modo === 'compra_mes');
            ultimaCanastaDashboard = { productosSolicitados, fecha: new Date().toISOString() };
            ultimoProcesoData = {
                producto: 'Compra del Mes',
                cantidad: productosSolicitados.length,
                unidad: 'ítems',
                productosSolicitados,
                items: resultadosParciales
            };
        }
        const isFailsafe = e.message && e.message.includes('USER_MOUSE_INTERVENTION');
        const isAborted = e.message && e.message.includes('RPA_ABORTED_BY_USER');

        let errMsg = 'RPA FINALIZADO CON ERROR: ' + e.message;
        let state = 'error';

        if (isFailsafe) {
            errMsg = '🛑 Regla estricta activada: Se detectó movimiento manual del mouse. El proceso de automatización se ha detenido de inmediato.';
            state = 'aborted';
        } else if (isAborted) {
            errMsg = 'RPA detenido inmediatamente por el usuario.';
            state = 'aborted';
        }

        broadcast({ type: 'status', state, message: errMsg });
        broadcast({ type: 'log', message: errMsg });
        await notificador.enviar(errMsg);
        if (!res.headersSent && !res.destroyed) {
            res.status(isFailsafe || isAborted ? 400 : 500).json({ success: false, message: errMsg });
        }
    } finally {
        isRpaRunning = false;
        setTimeout(() => {
            broadcast({ type: 'status', state: 'idle', message: 'RPA en espera' });
        }, 5000);
    }
});

const TAGUI_TIMEOUT_MS = 180000;

function obtenerPidsChromeTagUI() {
    try {
        const { spawnSync } = require('child_process');
        const res = spawnSync('powershell', [
            '-NoProfile',
            '-Command',
            "Get-CimInstance Win32_Process -Filter \"Name='chrome.exe'\" | Where-Object { $_.CommandLine -match 'remote-debugging-port=9222|tagui_user_profile' } | ForEach-Object { $_.ProcessId }"
        ], { windowsHide: true, encoding: 'utf8', timeout: 5000 });
        if (res.error || res.status !== 0) return null;
        const pids = (res.stdout || '').split(/\r?\n/).map(s => Number(s.trim())).filter(pid => Number.isInteger(pid) && pid > 0);
        return new Set(pids);
    } catch (e) {
        return null;
    }
}

function obtenerPidsChromePerfilTagUI() {
    try {
        const { spawnSync } = require('child_process');
        const res = spawnSync('powershell', [
            '-NoProfile',
            '-Command',
            "Get-CimInstance Win32_Process -Filter \"Name='chrome.exe'\" | Where-Object { $_.CommandLine -match 'tagui_user_profile' } | ForEach-Object { $_.ProcessId }"
        ], { windowsHide: true, encoding: 'utf8', timeout: 5000 });
        if (res.error || res.status !== 0) return null;
        const pids = (res.stdout || '').split(/\r?\n/).map(s => Number(s.trim())).filter(pid => Number.isInteger(pid) && pid > 0);
        return new Set(pids);
    } catch (e) {
        return null;
    }
}

function terminarProcesoTagUI(child) {
    if (!child || !Number.isInteger(child.pid) || child.pid <= 0) return;
    try {
        execSync('taskkill /F /T /PID ' + child.pid, { windowsHide: true, stdio: 'ignore' });
    } catch (e) {
        try { child.kill('SIGKILL'); } catch (eKill) {}
    }
}

// Solo termina los procesos Chrome marcados para TagUI que aparecieron durante esta corrida.
async function cerrarNavegadorTagUI(pidsAntes) {
    const pidsPerfil = obtenerPidsChromePerfilTagUI();
    if (pidsPerfil instanceof Set) {
        for (const pid of pidsPerfil) {
            try { execSync('taskkill /F /T /PID ' + pid, { windowsHide: true, stdio: 'ignore' }); } catch (e) {}
        }
    }

    if (!(pidsAntes instanceof Set)) return;
    const pidsDespues = obtenerPidsChromeTagUI();
    if (!(pidsDespues instanceof Set)) return;

    for (const pid of pidsDespues) {
        if (pidsAntes.has(pid)) continue;
        try {
            execSync('taskkill /F /T /PID ' + pid, { windowsHide: true, stdio: 'ignore' });
        } catch (e) {}
    }
}

// Endpoint para Búsqueda Individual (Exclusiva con TagUI)
app.post('/api/buscar-individual', async (req, res) => {
    if (isRpaRunning) {
        return res.status(409).json({ success: false, message: "El RPA ya está ejecutándose." });
    }

    const { id, producto, variante, nombre_completo, terminoBusqueda, cantidad = 1, unidad = '' } = req.body || {};
    if ((!producto || !producto.trim()) && !id && !nombre_completo) {
        return res.status(400).json({ success: false, message: "No se proporcionó un producto." });
    }

    const cantNum = parseFloat(cantidad) > 0 ? parseFloat(cantidad) : 1;

    // Validación estricta previa contra el catálogo cerrado
    const catEngine = getCatalogo();
    const queryValidar = id ? { id, cantidad: cantNum, unidad: String(unidad).trim() } : { id, producto: (producto || nombre_completo || '').trim(), nombre_completo, variante, cantidad: cantNum, unidad: String(unidad).trim() };
    const valCat = catEngine.validarEntrada(queryValidar);
    if (!valCat.valido) {
        return res.status(400).json({
            success: false,
            message: `El producto "${producto || nombre_completo || id}" no pertenece al catálogo cerrado.`,
            opciones: valCat.opciones ? valCat.opciones.slice(0, 10) : [],
            coincidencias: valCat.coincidencias ? valCat.coincidencias.slice(0, 10) : [],
            totalCoincidencias: valCat.totalCoincidencias || 0
        });
    }

    // Usar término oficial del catálogo
    const prodOficial = valCat.item ? (valCat.item.nombre_completo || valCat.item.producto) : (producto || nombre_completo || '').trim();
    const cantOficial = valCat.item ? valCat.item.cantidad : cantNum;
    const unidOficial = valCat.item ? valCat.item.unidad : String(unidad).trim();

    isRpaRunning = true;
    broadcast({ type: 'status', state: 'connecting', message: 'Iniciando TagUI...' });
    let chromePidsBeforeTagUI = null;
    let taguiBrowserCleanupAttempted = false;

    try {
        // Cerrar Excel obligatoriamente si el usuario lo tiene abierto para evitar bloqueos EBUSY
        try {
            execSync('taskkill /F /IM EXCEL.EXE', { windowsHide: true, stdio: 'ignore' });
        } catch (eKill) {}

        console.log(`[TagUI] Iniciando búsqueda individual para: ${prodOficial} (x${cantOficial} ${unidOficial})`);
        broadcast({ type: 'log', message: `Búsqueda individual con TagUI: "${prodOficial}" (Cantidad: ${cantOficial}, Unidad: ${unidOficial || 'Automática'})` });

        // Limpieza de consulta previa y creación de temp_input.csv para TagUI
        getValidador().limpiarResultados('2');
        getValidador().crearTempInput(prodOficial, cantOficial, unidOficial);

        // Ejecución exclusiva con TagUI mediante: tagui supermercados.tag temp_input.csv
        const { spawn } = require('child_process');
        chromePidsBeforeTagUI = obtenerPidsChromeTagUI();
        currentTaguiChromePidsBefore = chromePidsBeforeTagUI;
        const taguiPromise = new Promise((resolve, reject) => {
            const child = spawn('tagui', ['supermercados.tag', 'temp_input.csv'], {
                cwd: __dirname,
                shell: true
            });
            currentTaguiProcess = child;
            let settled = false;
            let flowFinished = false;
            let timeoutId = null;
            let completionId = null;

            const settle = (callback, value) => {
                if (settled) return;
                settled = true;
                clearTimeout(timeoutId);
                clearTimeout(completionId);
                callback(value);
            };

            timeoutId = setTimeout(() => {
                terminarProcesoTagUI(child);
                settle(reject, new Error('TagUI superó el límite de 3 minutos; se detuvo el proceso.'));
            }, TAGUI_TIMEOUT_MS);

            broadcast({ type: 'status', state: 'live', message: 'TagUI ejecutando búsqueda en Carrefour, COTO y Día %...' });

            child.stdout.on('data', (data) => {
                const text = data.toString();
                const lines = text.split(/\r?\n/).filter(l => l.trim().length > 0);
                for (const line of lines) {
                    broadcast({ type: 'log', message: line });
                    if (line.includes('[SUPERMERCADO 1]')) {
                        broadcast({ type: 'progress', percent: 25, message: line });
                    } else if (line.includes('[SUPERMERCADO 2]')) {
                        broadcast({ type: 'progress', percent: 55, message: line });
                    } else if (line.includes('[SUPERMERCADO 3]')) {
                        broadcast({ type: 'progress', percent: 85, message: line });
                    } else if (line.includes('[ RPA FINALIZADO ]')) {
                        broadcast({ type: 'progress', percent: 100, message: line });
                        flowFinished = true;
                        if (!completionId) {
                            completionId = setTimeout(() => {
                                terminarProcesoTagUI(child);
                                settle(resolve);
                            }, 1500);
                        }
                    }
                }
            });

            child.stderr.on('data', (data) => {
                const text = data.toString();
                console.error('[TagUI stderr]:', text);
            });

            child.on('error', (err) => {
                if (currentTaguiProcess === child) currentTaguiProcess = null;
                settle(reject, err);
            });

            child.on('close', (code) => {
                if (currentTaguiProcess === child) currentTaguiProcess = null;
                if (flowFinished || code === 0) {
                    settle(resolve);
                } else {
                    settle(reject, new Error(`TagUI finalizó con código de salida ${code}`));
                }
            });
        });

        await taguiPromise;

        // Cerrar únicamente la ventana de Chrome abierta por TagUI (protegiendo el frontend)
        await cerrarNavegadorTagUI(chromePidsBeforeTagUI);
        taguiBrowserCleanupAttempted = true;

        // Leer resultados extraídos por TagUI en resultados.csv
        const vEngine = getValidador();
        const todosItems = vEngine.leerResultadosCSV('resultados.csv');
        const itemsIndividual = todosItems.filter(it => it.modo === 'individual');

        ultimoProcesoData = {
            id: valCat.item ? valCat.item.id : id,
            producto: prodOficial,
            cantidad: cantOficial,
            unidad: unidOficial,
            items: itemsIndividual
        };

        // Reporte en consola y actualización de Excel
        await runCommand(`node validador.js --reporte-individual "${prodOficial}"`);
        try {
            execSync('taskkill /F /IM EXCEL.EXE', { windowsHide: true, stdio: 'ignore' });
        } catch (eKill) {}
        await generarReporteExcel();

        // Historial de precios + alertas de oportunidad + aviso de Telegram
        const actuales = itemsValidos('individual', itemsIndividual);
        const alertas = detectarAlertas(historial.leerHistorial(), actuales);
        historial.guardarCorrida(actuales);
        historial.guardarAlertas(alertas);
        const validosInd = actuales.map(item => {
            const original = itemsIndividual.find(it => it.supermercado === item.supermercado);
            const normalizado = vEngine.calcularPrecioNormalizado({
                nombre: original ? original.nombre : item.producto,
                precio: Number(item.precio),
                precioStr: original ? original.precioStr : ''
            });
            return {
                ...item,
                precio: Number(item.precio),
                precioNormalizado: normalizado ? normalizado.precioNormalizado : Number(item.precio),
                unidadBase: normalizado ? normalizado.unidadBase : 'unidad'
            };
        });
        const ganadorIndividual = validosInd.reduce((mejor, item) => {
            if (!mejor || item.precioNormalizado < mejor.precioNormalizado) return item;
            return mejor;
        }, null);
        const detallePrecios = itemsIndividual.map(item => {
            const validacion = vEngine.validarCoincidencia(prodOficial, item);
            const precio = item.precio !== null ? item.precio : vEngine.parsePrecio(item.precioStr);
            const base = precio !== null ? `${item.supermercado}: ${vEngine.formatoMoneda(precio)}` : `${item.supermercado}: sin precio`;
            if (!validacion.valido) return `⚠️ ${base} — descartado: ${validacion.motivo}`;
            const normalizado = vEngine.calcularPrecioNormalizado({ nombre: item.nombre, precio, precioStr: item.precioStr });
            return `✅ ${base}${normalizado ? ` (${normalizado.descripcion})` : ''}`;
        });
        const masBarato = ganadorIndividual
            ? `🏆 Menor precio comparable: ${ganadorIndividual.supermercado} (${vEngine.formatoMoneda(ganadorIndividual.precio)}; ${vEngine.formatoMoneda(ganadorIndividual.precioNormalizado)} por ${ganadorIndividual.unidadBase})`
            : '⚠️ Ningún supermercado devolvió una coincidencia válida.';
        const mensajesTelegram = [];
        if (alertas.length > 0) {
            const extra = alertas.length > 20 ? `\n...y ${alertas.length - 20} más` : '';
            mensajesTelegram.push('🔔 Alertas de precio:\n' + alertas.slice(0, 20).map(textoAlerta).join('\n') + extra);
        }
        mensajesTelegram.push(`✅ Búsqueda individual terminada: "${prodOficial}"\n${detallePrecios.join('\n')}\n${masBarato}`);
        await Promise.all(mensajesTelegram.map(notificador.enviar));

        broadcast({ type: 'status', state: 'finished', message: 'Búsqueda individual con TagUI completada con éxito.' });

        if (!res.headersSent && !res.destroyed) {
            res.json({
                success: true,
                message: `Búsqueda individual de "${producto}" completada con TagUI. Resultados visibles en el dashboard; puedes descargar el reporte Excel.`,
                data: ultimoProcesoData
            });
        }
    } catch (e) {
        console.error("Error en búsqueda individual TagUI:", e);
        const errMsg = 'ERROR EN BÚSQUEDA INDIVIDUAL TagUI: ' + e.message;
        if (currentTaguiProcess) terminarProcesoTagUI(currentTaguiProcess);
        if (!taguiBrowserCleanupAttempted) {
            await cerrarNavegadorTagUI(chromePidsBeforeTagUI);
            taguiBrowserCleanupAttempted = true;
        }
        await notificador.enviar(errMsg);
        broadcast({ type: 'status', state: 'error', message: errMsg });
        broadcast({ type: 'log', message: errMsg });
        if (!res.headersSent && !res.destroyed) {
            res.status(500).json({ success: false, message: errMsg });
        }
    } finally {
        if (currentTaguiProcess) terminarProcesoTagUI(currentTaguiProcess);
        if (!taguiBrowserCleanupAttempted) await cerrarNavegadorTagUI(chromePidsBeforeTagUI);
        if (fs.existsSync('temp_input.csv')) {
            try { fs.unlinkSync('temp_input.csv'); } catch(e) {}
        }
        currentTaguiProcess = null;
        currentTaguiChromePidsBefore = null;
        isRpaRunning = false;
        setTimeout(() => {
            broadcast({ type: 'status', state: 'idle', message: 'RPA en espera' });
        }, 5000);
    }
});

app.post('/api/abrir-excel', async (req, res) => {
    try {
        const file = 'reporte_supermercados.xlsx';
        if (fs.existsSync(file)) {
            await runCommand(`start "" "${file}"`);
            res.json({ success: true, message: "Abriendo Excel..." });
        } else {
            res.json({ success: false, message: "Aún no se ha generado el reporte." });
        }
    } catch (e) {
        res.status(500).json({ success: false, message: e.toString() });
    }
});

// Endpoint Kill-Switch para abortar la búsqueda inmediatamente
app.all('/api/abort', async (req, res) => {
    console.log('[API] Solicitud de abortar RPA recibida.');
    if (currentTaguiProcess) {
        terminarProcesoTagUI(currentTaguiProcess);
        currentTaguiProcess = null;
    }
    await cerrarNavegadorTagUI(currentTaguiChromePidsBefore);
    try {
        getRpaRunner().abortCurrentRun();
    } catch (e) {}
    isRpaRunning = false;
    broadcast({ type: 'status', state: 'idle', message: 'RPA detenido inmediatamente por el usuario.' });
    res.json({ success: true, message: 'RPA abortado exitosamente.' });
});

app.post('/api/limpiar', async (req, res) => {
    try {
        const tipo = req.body.tipo; // 1, 2 o 3
        await runCommand(`node validador.js --limpiar ${tipo}`);
        try {
            execSync('taskkill /F /IM EXCEL.EXE', { windowsHide: true, stdio: 'ignore' });
        } catch (eKill) {}
        await generarReporteExcel();
        res.json({ success: true, message: "Limpieza completada y Excel actualizado." });
    } catch (e) {
        res.status(500).json({ success: false, message: e.toString() });
    }
});

// Endpoints del Diccionario de Supermercados
app.get('/api/diccionario', (req, res) => {
    try {
        const catEngine = getCatalogo();
        const dicc = catEngine.obtenerDiccionarioSupermercados();
        res.json({ success: true, diccionario: dicc });
    } catch (e) {
        res.status(500).json({ success: false, message: e.toString() });
    }
});

app.get('/api/diccionario/buscar', (req, res) => {
    try {
        const query = req.query.q || '';
        if (!query) {
            return res.status(400).json({ success: false, message: 'Parámetro "q" requerido.' });
        }
        const catEngine = getCatalogo();
        const match = catEngine.buscarPorDiccionarioSupermercado(query);
        res.json({ success: true, query, match });
    } catch (e) {
        res.status(500).json({ success: false, message: e.toString() });
    }
});

app.post('/api/diccionario/alias', (req, res) => {
    try {
        const { id, alias } = req.body;
        if (!id || !alias) {
            return res.status(400).json({ success: false, message: 'Se requieren "id" y "alias".' });
        }
        const catEngine = getCatalogo();
        const agregado = catEngine.agregarNombreSupermercado(id, alias, true);
        if (agregado) {
            res.json({ success: true, message: `Alias "${alias}" agregado correctamente al producto "${id}".` });
        } else {
            res.status(400).json({ success: false, message: `No se pudo agregar el alias. Verifica si el producto existe o si el alias ya estaba registrado.` });
        }
    } catch (e) {
        res.status(500).json({ success: false, message: e.toString() });
    }
});

app.get('/api/input', (req, res) => {
    try {
        if (fs.existsSync('input.csv')) {
            const data = fs.readFileSync('input.csv', 'utf8');
            res.json({ success: true, data });
        } else {
            res.json({ success: true, data: "producto,modo\n" });
        }
    } catch (e) {
        res.status(500).json({ success: false, message: e.toString() });
    }
});

app.post('/api/input', (req, res) => {
    try {
        const { contenido } = req.body;
        if (typeof contenido !== 'string') throw new Error("Contenido inválido.");

        // Validar cada línea propuesta contra el catálogo
        const catEngine = getCatalogo();
        const lines = contenido.split(/\r?\n/).map(l => l.trim()).filter(l => l.length > 0);
        const invalidas = [];
        for (let i = 1; i < lines.length; i++) {
            const parts = lines[i].split(',').map(p => p.trim());
            const val = catEngine.validarEntrada({ producto: parts[0], cantidad: parts[1], unidad: parts[2] });
            if (!val.valido) {
                invalidas.push({ fila: i + 1, texto: lines[i], motivo: val.motivo });
            }
        }
        if (invalidas.length > 0) {
            return res.status(400).json({
                success: false,
                message: "No se puede guardar: contiene productos fuera del catálogo cerrado.",
                filasInvalidas: invalidas
            });
        }

        fs.writeFileSync('input.csv', contenido, 'utf8');
        res.json({ success: true, message: "Lista mensual actualizada correctamente y validada con el catálogo." });
    } catch (e) {
        res.status(500).json({ success: false, message: e.toString() });
    }
});

server.listen(PORT, () => {
    console.log(`=========================================`);
    console.log(`Servidor iniciado: http://localhost:${PORT}`);
    console.log(`WebSocket Stream: ws://localhost:${PORT}/ws/rpa-stream`);
    console.log(`=========================================`);

    notificador.enviarBienvenida().then(enviado => {
        if (enviado) console.log('[TELEGRAM] Mensaje de bienvenida enviado al iniciar el bot.');
    });
});
