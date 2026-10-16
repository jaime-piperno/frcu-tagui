const express = require('express');
const http = require('http');
const { WebSocketServer } = require('ws');
const { exec, execSync } = require('child_process');
const path = require('path');
const fs = require('fs');
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
                try {
                    execSync('taskkill /F /T /PID ' + currentTaguiProcess.pid, { windowsHide: true, stdio: 'ignore' });
                } catch (e) {}
                currentTaguiProcess = null;
            }
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
                resolve({ success: false, output: stdout, error: stderr });
            } else {
                resolve({ success: true, output: stdout });
            }
        });
    });
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

    try {
        // Cerrar Excel obligatoriamente si el usuario lo tiene abierto para evitar bloqueos EBUSY
        try {
            execSync('taskkill /F /IM EXCEL.EXE', { windowsHide: true, stdio: 'ignore' });
        } catch (eKill) {}

        // Limpiar registros de compra del mes anteriores para iniciar con datos frescos
        getValidador().limpiarResultados('1');

        console.log("Iniciando compra del mes...");
        
        // Leer input.csv validado
        let itemsCanasta = [];
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

        ultimoProcesoData = {
            producto: 'Compra del Mes',
            cantidad: itemsCanasta.length,
            unidad: 'ítems',
            items: resultados
        };

        // Generar Excel consolidado
        try {
            execSync('taskkill /F /IM EXCEL.EXE', { windowsHide: true, stdio: 'ignore' });
        } catch (eKill) {}
        await runCommand('node generar_excel.js');

        // Abrir automáticamente el archivo Excel con los resultados al terminar la búsqueda
        try {
            await runCommand('start "" "reporte_supermercados.xlsx"');
        } catch (errOpen) {
            console.warn("Aviso al abrir Excel automáticamente:", errOpen.message);
        }

        if (!res.headersSent && !res.destroyed) {
            res.json({
                success: true,
                message: "Compra del mes finalizada exitosamente. Reporte Excel abierto.",
                data: ultimoProcesoData
            });
        }
    } catch (e) {
        console.error("Error en compra del mes:", e);
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

// Función para cerrar ÚNICAMENTE la ventana/instancia de Chrome iniciada por TagUI
// Se filtra por la línea de comandos de TagUI (remote-debugging-port=9222 o tagui_user_profile)
// de modo que NUNCA cierre la pestaña del frontend (http://localhost:3000) ni las pestañas del usuario.
function cerrarNavegadorTagUI() {
    // 1. Cerrar pestañas abiertas en el puerto 9222 vía CDP
    try {
        const http = require('http');
        const req = http.get('http://127.0.0.1:9222/json', (res) => {
            let data = '';
            res.on('data', chunk => data += chunk);
            res.on('end', () => {
                try {
                    const tabs = JSON.parse(data);
                    if (Array.isArray(tabs)) {
                        for (const tab of tabs) {
                            if (tab && tab.id) {
                                http.get(`http://127.0.0.1:9222/json/close/${tab.id}`, () => {}).on('error', () => {});
                            }
                        }
                    }
                } catch(e) {}
            });
        });
        req.on('error', () => {});
        req.setTimeout(800, () => req.destroy());
    } catch(e) {}

    // 2. Terminar procesos iniciados por TagUI (filtrando estrictamente por tagui en la línea de comandos)
    try {
        const { spawnSync } = require('child_process');
        const res = spawnSync('powershell', [
            '-NoProfile',
            '-Command',
            "(Get-CimInstance Win32_Process -Filter \"CommandLine LIKE '%tagui%'\").ProcessId"
        ]);
        const pids = res.stdout.toString().split(/\r?\n/).map(s => s.trim()).filter(s => /^\d+$/.test(s));
        for (const pid of pids) {
            try {
                process.kill(parseInt(pid, 10), 'SIGKILL');
            } catch (eKill) {}
        }
    } catch (e) {}
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
        const taguiPromise = new Promise((resolve, reject) => {
            const child = spawn('tagui', ['supermercados.tag', 'temp_input.csv'], {
                cwd: __dirname,
                shell: true
            });
            currentTaguiProcess = child;

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
                    }
                }
            });

            child.stderr.on('data', (data) => {
                const text = data.toString();
                console.error('[TagUI stderr]:', text);
            });

            child.on('error', (err) => {
                currentTaguiProcess = null;
                reject(err);
            });

            child.on('close', (code) => {
                currentTaguiProcess = null;
                if (code === 0) {
                    resolve();
                } else {
                    reject(new Error(`TagUI finalizó con código de salida ${code}`));
                }
            });
        });

        await taguiPromise;

        // Cerrar únicamente la ventana de Chrome abierta por TagUI (protegiendo el frontend)
        cerrarNavegadorTagUI();

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
        await runCommand('node generar_excel.js');

        // Abrir automáticamente el archivo Excel con los resultados al terminar la búsqueda
        try {
            await runCommand('start "" "reporte_supermercados.xlsx"');
        } catch (errOpen) {
            console.warn("Aviso al abrir Excel automáticamente:", errOpen.message);
        }

        broadcast({ type: 'status', state: 'finished', message: 'Búsqueda individual con TagUI completada con éxito.' });

        if (!res.headersSent && !res.destroyed) {
            res.json({
                success: true,
                message: `Búsqueda individual de "${producto}" completada exclusivamente con TagUI. Reporte Excel abierto.`,
                data: ultimoProcesoData
            });
        }
    } catch (e) {
        console.error("Error en búsqueda individual TagUI:", e);
        const errMsg = 'ERROR EN BÚSQUEDA INDIVIDUAL TAGUI: ' + e.message;
        broadcast({ type: 'status', state: 'error', message: errMsg });
        broadcast({ type: 'log', message: errMsg });
        if (!res.headersSent && !res.destroyed) {
            res.status(500).json({ success: false, message: errMsg });
        }
    } finally {
        cerrarNavegadorTagUI();
        if (fs.existsSync('temp_input.csv')) {
            try { fs.unlinkSync('temp_input.csv'); } catch(e) {}
        }
        currentTaguiProcess = null;
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
app.all('/api/abort', (req, res) => {
    console.log('[API] Solicitud de abortar RPA recibida.');
    if (currentTaguiProcess) {
        try {
            execSync('taskkill /F /T /PID ' + currentTaguiProcess.pid, { windowsHide: true, stdio: 'ignore' });
        } catch (e) {}
        cerrarNavegadorTagUI();
        currentTaguiProcess = null;
    }
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
        await runCommand('node generar_excel.js');
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
});
