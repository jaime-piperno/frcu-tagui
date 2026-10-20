// ==============================================================================
// UTN FRCU - Tecnologías para la Automatización (Año 2026)
// rpa_runner.js - Motor de Automatización RPA 100% Visible Paso a Paso
// ==============================================================================

let puppeteerInstance = null;
async function getPuppeteer() {
    if (!puppeteerInstance) {
        const mod = await import('puppeteer-core');
        puppeteerInstance = mod.default || mod;
    }
    return puppeteerInstance;
}
const fs = require('fs');
const path = require('path');
const { spawnSync } = require('child_process');
const validador = require('./validador.js');
const catalogo = require('./catalogo.js');

const CSV_PATH = path.join(__dirname, 'resultados.csv');
const MOUSE_HELPER_PATH = path.join(__dirname, 'mouse_helper.exe');

// ==============================================================================
// CONSTANTES CENTRALIZADAS DE VELOCIDAD Y TIEMPOS (MODO DEMOSTRACIÓN VISIBLE)
// ==============================================================================
const CONFIG = {
    DEMO_MODE: true,
    TYPING_DELAY: 50,          // 50ms por carácter (tipeo humano visible)
    MOUSE_MOVE_DURATION: 600,  // 600ms de movimiento fluido del cursor
    PAUSE_BEFORE_CLICK: 450,   // Pausa de posicionamiento antes del click
    PAUSE_AFTER_CLICK: 650,    // Pausa posterior al click para asimilar la acción
    PAUSE_AFTER_PAGE_LOAD: 2500, // Pausa tras cargar la página principal
    PAUSE_AFTER_SEARCH: 2500,  // Pausa tras ejecutar la búsqueda
    PAUSE_AFTER_FILTER: 2200,  // Pausa tras aplicar el ordenamiento
    SCROLL_STEP_DELAY: 350     // Pausa entre pasos de scroll progresivo
};

// Control de aborto global e instantáneo (Kill-Switch y FailSafe de Movimiento de Mouse)
const FAILSAFE_FLAG_PATH = path.join(__dirname, 'failsafe.flag');
const FAILSAFE_STATE_PATH = path.join(__dirname, 'failsafe.state');

let isAborted = false;
let abortReason = null;
let activeBrowser = null;
let watchdogProcess = null;

function startMouseWatchdog(onFailsafe) {
    stopMouseWatchdog();
    try {
        const { spawn } = require('child_process');
        watchdogProcess = spawn(MOUSE_HELPER_PATH, ['watchdog'], {
            windowsHide: true,
            stdio: ['ignore', 'pipe', 'pipe']
        });

        if (watchdogProcess.stdout) {
            watchdogProcess.stdout.on('data', (data) => {
                const str = data.toString();
                if (str.includes('USER_MOUSE_INTERVENTION')) {
                    console.warn('[FAILSAFE] 🛑 Movimiento manual de mouse detectado por watchdog.');
                    abortCurrentRun('USER_MOUSE_INTERVENTION');
                    if (onFailsafe) onFailsafe('USER_MOUSE_INTERVENTION');
                }
            });
        }

        watchdogProcess.on('exit', (code) => {
            if (code === 99 || fs.existsSync(FAILSAFE_FLAG_PATH)) {
                console.warn('[FAILSAFE] 🛑 Watchdog finalizó tras detectar intervención manual del mouse.');
                abortCurrentRun('USER_MOUSE_INTERVENTION');
                if (onFailsafe) onFailsafe('USER_MOUSE_INTERVENTION');
            }
        });
    } catch (e) {
        console.error('[FAILSAFE] Error al iniciar watchdog de mouse:', e);
    }
}

function stopMouseWatchdog() {
    if (watchdogProcess) {
        try {
            watchdogProcess.kill();
        } catch (e) {}
        watchdogProcess = null;
    }
    try {
        if (fs.existsSync(FAILSAFE_FLAG_PATH)) fs.unlinkSync(FAILSAFE_FLAG_PATH);
    } catch (e) {}
    try {
        if (fs.existsSync(FAILSAFE_STATE_PATH)) fs.unlinkSync(FAILSAFE_STATE_PATH);
    } catch (e) {}
}

function abortCurrentRun(reason = 'RPA_ABORTED_BY_USER') {
    isAborted = true;
    abortReason = reason;
    if (watchdogProcess) {
        try { watchdogProcess.kill(); } catch (e) {}
        watchdogProcess = null;
    }
    try {
        require('child_process').execSync('taskkill /F /IM mouse_helper.exe', { windowsHide: true, stdio: 'ignore' });
    } catch (e) {}
    if (activeBrowser) {
        try {
            activeBrowser.close().catch(() => {});
        } catch (e) {}
        activeBrowser = null;
    }
}

function checkAborted() {
    if (!isAborted && fs.existsSync(FAILSAFE_FLAG_PATH)) {
        abortCurrentRun('USER_MOUSE_INTERVENTION');
    }
    if (isAborted) {
        throw new Error(abortReason || 'RPA_ABORTED_BY_USER');
    }
}

// Pausa asíncrona e interrumpible
async function sleep(ms) {
    const interval = 50;
    let elapsed = 0;
    while (elapsed < ms) {
        checkAborted();
        const chunk = Math.min(interval, ms - elapsed);
        await new Promise(resolve => setTimeout(resolve, chunk));
        elapsed += chunk;
    }
}

// Detecta el ejecutable de Google Chrome en Windows
function getChromePath() {
    const paths = [
        'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',
        'C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe',
        path.join(process.env.LOCALAPPDATA || '', 'Google\\Chrome\\Application\\chrome.exe'),
        'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe',
        'C:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe'
    ];
    for (const p of paths) {
        if (p && fs.existsSync(p)) return p;
    }
    throw new Error('No se encontró Google Chrome en las rutas estándar del sistema.');
}

function getFechaHoy() {
    const hoy = new Date();
    let m = (hoy.getMonth() + 1).toString();
    let d = hoy.getDate().toString();
    if (m.length < 2) m = '0' + m;
    if (d.length < 2) d = '0' + d;
    return `${hoy.getFullYear()}-${m}-${d}`;
}

function asegurarCSV() {
    if (!fs.existsSync(CSV_PATH)) {
        const header = 'modo,producto_solicitado,nombre_encontrado,precio,supermercado,url,fecha,stock_status,cantidad,unidad\n';
        fs.writeFileSync(CSV_PATH, header, 'utf8');
    }
}

// El consentimiento y los modales emergentes se cierran para permitir la interacción visible limpia
async function eliminarCookies(page) {
    try {
        await page.evaluate(() => {
            const candidates = Array.from(document.querySelectorAll('button, a, div[role="button"]'));
            for (const el of candidates) {
                const txt = (el.innerText || el.textContent || '').trim().toLowerCase();
                if (txt === 'seguí navegando' || txt === 'segui navegando' || txt === 'aceptar todo' || txt === 'rechazar todo' || txt === 'entendido') {
                    el.click();
                }
            }
            const closeBtns = document.querySelectorAll('.vtex-modal__close-button, [class*="modal__close"], [aria-label*="Cerrar" i], [aria-label="Close"]');
            for (const cb of closeBtns) {
                cb.click();
            }
        });
    } catch (e) {}

    const selectors = [
        '#onetrust-accept-btn-handler', '#onetrust-reject-all-handler',
        'button[id*="cookie" i]', 'button[class*="cookie" i]',
        'button[aria-label*="Aceptar" i]', '.vtex-modal__close-button'
    ];
    for (const selector of selectors) {
        try {
            const el = await page.$(selector);
            if (el) {
                await visibleClick(page, selector, 300);
                return true;
            }
        } catch (e) {}
    }
    return false;
}

// ==============================================================================
// GESTIÓN DEL CURSOR EN PÁGINA
// ==============================================================================
// El puntero DOM sintético que quedaba en el centro de la pantalla ha sido removido.
// mouse_helper.exe maneja exclusivamente el cursor físico real de Windows mediante la Win32 API.
async function asegurarCursorEnPagina(page) {
    try {
        await page.evaluate(() => {
            const root = document.getElementById('rpa-virtual-cursor-root');
            if (root) root.remove();
        });
    } catch (e) {}
}

// Lectura interna: ubica un elemento, pero nunca lo enfoca ni lo desplaza.
async function getElementViewportPos(page, selector) {
    try {
        return await page.evaluate((sel) => {
            const elements = Array.from(document.querySelectorAll(sel));
            const el = elements.find(e => {
                const r = e.getBoundingClientRect();
                return r.width > 20 && r.height > 10 && e.offsetParent !== null;
            });
            if (!el) return null;
            const r = el.getBoundingClientRect();
            return {
                x: Math.round(r.left + r.width / 2),
                y: Math.round(r.top + r.height / 2),
                top: Math.round(r.top), bottom: Math.round(r.bottom),
                left: Math.round(r.left), right: Math.round(r.right),
                innerWidth: window.innerWidth, innerHeight: window.innerHeight,
                outerWidth: window.outerWidth, outerHeight: window.outerHeight
            };
        }, selector);
    } catch (e) {
        return null;
    }
}

async function revealElementVisibly(page, selector) {
    for (let attempt = 0; attempt < 8; attempt++) {
        checkAborted();
        const pos = await getElementViewportPos(page, selector);
        if (!pos) return null;
        if (pos.top >= 0 && pos.bottom <= pos.innerHeight && pos.left >= 0 && pos.right <= pos.innerWidth) return pos;
        await visibleScroll(page, pos.top < 0 ? -360 : 360, 2);
    }
    return null;
}

function runMouseHelper(args) {
    if (!fs.existsSync(MOUSE_HELPER_PATH)) {
        throw new Error('No se encontró mouse_helper.exe; no se permite un fallback invisible.');
    }
    checkAborted();
    const result = spawnSync(MOUSE_HELPER_PATH, args, { windowsHide: true, encoding: 'utf8', timeout: 30000 });
    if (fs.existsSync(FAILSAFE_FLAG_PATH) || (result.stdout && result.stdout.includes('USER_MOUSE_INTERVENTION')) || result.status === 99) {
        abortCurrentRun('USER_MOUSE_INTERVENTION');
        throw new Error('USER_MOUSE_INTERVENTION');
    }
    if (result.error || result.status !== 0) {
        checkAborted();
        throw new Error(`mouse_helper.exe no pudo ejecutar ${args[0]}.`);
    }
    return (result.stdout || '').trim();
}

function viewportArgs(command, pos, durationMs) {
    return [command, pos.x, pos.y, pos.outerWidth, pos.outerHeight, pos.innerWidth, pos.innerHeight, Math.max(durationMs || 0, 0)]
        .map(String);
}

// ==============================================================================
// ACCIONES VISIBLES PRIMARIAS (INTERACCIÓN REAL DE USUARIO)
// ==============================================================================

// 1. Navegación Visible por la Barra de Direcciones de Chrome
async function visibleNavigate(page, targetUrl, typingDelay = CONFIG.TYPING_DELAY, maxAttempts = 2) {
    checkAborted();
    const targetHost = new URL(targetUrl).hostname;

    for (let attempt = 1; attempt <= maxAttempts; attempt++) {
        checkAborted();
        try {
            console.log(`[RPA] Navegación visible hacia ${targetUrl} (Intento ${attempt}/${maxAttempts})...`);

            // Asegurar que Chrome esté al frente antes de manipular la Omnibox
            try {
                await page.bringToFront();
            } catch (e) {}
            runMouseHelper(['focus']);
            await sleep(200);

            // Secuencia física real de mouse_helper.exe: Omnibox -> click -> Ctrl+L -> TypeText -> Enter
            runMouseHelper(['nav', targetUrl, Math.max(typingDelay, 25).toString()]);

            // Esperar que la navegación se concrete por el Enter en la barra de direcciones
            let arrived = false;
            for (let t = 0; t < 80; t++) {
                await sleep(250);
                checkAborted();
                const curUrl = page.url();
                if (curUrl.includes(targetHost)) {
                    arrived = true;
                    break;
                }
            }

            if (arrived) {
                console.log(`[RPA] Navegación visible a ${targetHost} confirmada exitosamente.`);
                await sleep(CONFIG.PAUSE_AFTER_PAGE_LOAD);
                await asegurarCursorEnPagina(page);
                await eliminarCookies(page);
                return;
            }

            console.warn(`[RPA] ⚠️ Intento ${attempt} no alcanzó la URL destino ${targetHost}. URL actual: ${page.url()}`);
        } catch (err) {
            if (err.message === 'RPA_ABORTED_BY_USER' || isAborted) throw err;
            console.error(`[RPA] ⚠️ Error en intento ${attempt} de navegación visible: ${err.message}`);
        }

        // Si falló el primer intento, registrar error, recuperar el foco de Chrome y reintentar la navegación visible
        if (attempt < maxAttempts) {
            console.log(`[RPA] Recuperando foco de Chrome para reintentar la navegación visible a ${targetUrl}...`);
            try {
                await page.bringToFront();
            } catch (e) {}
            runMouseHelper(['focus']);
            await sleep(600);
        }
    }

    // Está estrictamente prohibido recurrir a page.goto() como solución silenciosa.
    throw new Error(`La navegación visible no llegó a ${targetHost} tras ${maxAttempts} intentos.`);
}

// 2. Movimiento Visible hacia un Elemento
async function visibleMove(page, selectorOrCoords, durationMs = CONFIG.MOUSE_MOVE_DURATION) {
    checkAborted();
    let pos;
    if (typeof selectorOrCoords === 'string') {
        pos = await revealElementVisibly(page, selectorOrCoords);
        if (!pos) return false;
    } else if (selectorOrCoords && selectorOrCoords.x !== undefined) {
        pos = selectorOrCoords;
    } else {
        return false;
    }
    runMouseHelper(viewportArgs('moveviewport', pos, durationMs));
    return true;
}

// 3. Click Real y Visible
async function visibleClick(page, selector, durationMs = CONFIG.MOUSE_MOVE_DURATION) {
    checkAborted();
    const pos = await revealElementVisibly(page, selector);
    if (!pos) return false;
    await visibleMove(page, pos, durationMs);
    await sleep(CONFIG.PAUSE_BEFORE_CLICK);
    runMouseHelper(viewportArgs('clickviewport', pos, 0));
    await sleep(CONFIG.PAUSE_AFTER_CLICK);
    return true;
}

// 4. Escritura Visible Progresiva (Carácter por Carácter con Teclado Real)
async function visibleType(page, selector, text, delayMs = CONFIG.TYPING_DELAY, durationMs = CONFIG.MOUSE_MOVE_DURATION) {
    checkAborted();
    const pos = await revealElementVisibly(page, selector);
    if (!pos) return false;
    await visibleMove(page, pos, durationMs);
    await sleep(CONFIG.PAUSE_BEFORE_CLICK);
    runMouseHelper(viewportArgs('clickviewport', pos, 0));
    // La escritura ocurre en el campo que acaba de recibir el click físico.
    runMouseHelper(['key', '^a']);
    runMouseHelper(['key', '{BACKSPACE}']);
    await sleep(150);
    runMouseHelper(['type', text, Math.max(delayMs, 25).toString()]);
    await sleep(CONFIG.PAUSE_AFTER_CLICK);
    return true;
}

// 5. Scroll Progresivo y Visible por la Página
async function visibleScroll(page, totalPixels = 500, steps = 3) {
    checkAborted();
    const stepPixels = Math.floor(totalPixels / steps);
    for (let i = 0; i < steps; i++) {
        runMouseHelper(['scroll', stepPixels.toString(), '1', Math.max(CONFIG.SCROLL_STEP_DELAY, 100).toString()]);
        await sleep(CONFIG.SCROLL_STEP_DELAY);
    }
}

async function visibleKey(keys) {
    checkAborted();
    runMouseHelper(['key', keys]);
    await sleep(CONFIG.PAUSE_AFTER_CLICK);
}

async function getTextElementViewportPos(page, selector, text) {
    try {
        return await page.evaluate((sel, expected) => {
            const normalize = (value) => (value || '').replace(/\s+/g, ' ').trim().toLocaleLowerCase('es-AR');
            const wanted = normalize(expected);
            const element = Array.from(document.querySelectorAll(sel)).find((candidate) => {
                const rect = candidate.getBoundingClientRect();
                const label = normalize(candidate.innerText || candidate.textContent);
                return rect.width > 20 && rect.height > 10 && candidate.offsetParent !== null && label.includes(wanted);
            });
            if (!element) return null;
            const r = element.getBoundingClientRect();
            return { x: Math.round(r.left + r.width / 2), y: Math.round(r.top + r.height / 2), top: Math.round(r.top), bottom: Math.round(r.bottom), left: Math.round(r.left), right: Math.round(r.right), innerWidth: window.innerWidth, innerHeight: window.innerHeight, outerWidth: window.outerWidth, outerHeight: window.outerHeight };
        }, selector, text);
    } catch (e) { return null; }
}

async function visibleClickText(page, selector, text, durationMs = CONFIG.MOUSE_MOVE_DURATION) {
    const pos = await getTextElementViewportPos(page, selector, text);
    if (!pos || pos.top < 0 || pos.bottom > pos.innerHeight) return false;
    await visibleMove(page, pos, durationMs);
    await sleep(CONFIG.PAUSE_BEFORE_CLICK);
    runMouseHelper(viewportArgs('clickviewport', pos, 0));
    await sleep(CONFIG.PAUSE_AFTER_CLICK);
    return true;
}

async function visibleSelectOption(page, selector, value, durationMs = CONFIG.MOUSE_MOVE_DURATION) {
    const pos = await revealElementVisibly(page, selector);
    if (!pos) return false;
    const optionIndex = await page.evaluate((sel, optionValue) => {
        const select = document.querySelector(sel);
        return select ? Array.from(select.options).findIndex((option) => option.value === optionValue) : -1;
    }, selector, value);
    if (optionIndex < 0) return false;
    await visibleClick(page, selector, durationMs);
    await visibleKey('{HOME}');
    for (let i = 0; i < optionIndex; i++) await visibleKey('{DOWN}');
    await visibleKey('{ENTER}');
    return true;
}

function determinarUnidadDefault(producto, unidadIngresada) {
    if (unidadIngresada && unidadIngresada.trim()) return unidadIngresada.trim();
    const p = producto.toLowerCase();
    if (p.includes('arroz') || p.includes('fideos')) return '500g';
    if (p.includes('leche')) return '1L';
    if (p.includes('coca') || p.includes('gaseosa') || p.includes('manaos') || p.includes('pepsi')) return '2L';
    if (p.includes('aceite')) return '1.5L';
    if (p.includes('yerba')) return '500g';
    if (p.includes('azucar') || p.includes('azúcar')) return '1kg';
    if (p.includes('cafe') || p.includes('café')) return '170g';
    if (p.includes('galletitas')) return '300g';
    if (p.includes('papel')) return '4 un.';
    return '500g';
}

// ==============================================================================
// MÓDULOS DE INTERACCIÓN VISIBLE POR SUPERMERCADO
// ==============================================================================

// ------------------------------------------------------------------------------
// 1. CARREFOUR ARGENTINA
// ------------------------------------------------------------------------------
async function searchCarrefour(page, prodClean, options = {}) {
    const { onStatus, typingDelay, mouseDuration, itemObj, cantidad, unidad } = options;
    checkAborted();

    const itemCat = catalogo.buscarEnCatalogo(itemObj) || catalogo.buscarEnCatalogo(prodClean);
    const baseTexto = (itemCat && itemCat.termino_busqueda) ? itemCat.termino_busqueda : ((itemObj && itemObj.terminoBusqueda) ? itemObj.terminoBusqueda : prodClean);
    const textoATipear = validador.adaptarTerminoSupermercado(baseTexto, 'Carrefour');

    const yaEnCarrefour = page.url().includes('carrefour.com.ar');
    const reusarBusqueda = yaEnCarrefour && options.ultimoTerminoBuscado && (options.ultimoTerminoBuscado.toLowerCase().trim() === textoATipear.toLowerCase().trim());

    if (!reusarBusqueda) {
        if (!yaEnCarrefour) {
            if (onStatus) {
                onStatus({ type: 'log', message: '[SUPERMERCADO 1] Navegando visualmente a https://www.carrefour.com.ar...' });
            }
            // 1. Navegar por barra de direcciones
            await visibleNavigate(page, 'https://www.carrefour.com.ar', typingDelay);
            await sleep(CONFIG.PAUSE_AFTER_PAGE_LOAD);
            await eliminarCookies(page);
            await sleep(400);
        } else {
            await page.evaluate(() => window.scrollTo(0, 0)).catch(() => {});
            await eliminarCookies(page);
            await sleep(250);
        }

        // 2. Localizar buscador
        if (onStatus) onStatus({ type: 'log', message: `[SUPERMERCADO 1] Localizando buscador para: "${textoATipear}"...` });
        const searchSel = 'input[placeholder*="buscando" i], input.vtex-styleguide-9-x-input';
        await page.waitForSelector(searchSel, { timeout: 10000 }).catch(() => {});

        // 3. Escribir carácter por carácter de forma visible el término específico
        let typedCarrefour = await visibleType(page, searchSel, textoATipear, typingDelay, mouseDuration);
        if (!typedCarrefour) {
            await visibleNavigate(page, 'https://www.carrefour.com.ar', typingDelay);
            await sleep(CONFIG.PAUSE_AFTER_PAGE_LOAD);
            await eliminarCookies(page);
            await sleep(500);
            typedCarrefour = await visibleType(page, searchSel, textoATipear, typingDelay, mouseDuration);
        }
        if (!typedCarrefour) {
            throw new Error('No se encontró un buscador visible de Carrefour.');
        }

        // 4. Ejecutar búsqueda con Enter
        await sleep(300);
        await visibleKey('{ENTER}');

        if (onStatus) onStatus({ type: 'log', message: '[SUPERMERCADO 1] Esperando resultados de búsqueda...' });
        for (let w = 0; w < 20; w++) {
            await sleep(500);
            const curU = page.url();
            if (curU.includes(encodeURIComponent(prodClean)) || curU.includes(encodeURIComponent(textoATipear)) || curU.includes('_q=') || curU.includes('almacen')) {
                break;
            }
            if (w === 3) {
                await visibleKey('{ENTER}');
                await visibleClick(page, 'button[class*="searchIcon"], button[type="submit"], [class*="search-bar"] button', mouseDuration);
            }
        }
        await sleep(CONFIG.PAUSE_AFTER_SEARCH);
        await eliminarCookies(page);
    } else {
        if (onStatus) onStatus({ type: 'log', message: `[SUPERMERCADO 1] Término de catálogo idéntico al anterior ("${textoATipear}"). Reutilizando resultados en pantalla para extraer "${prodClean}"...` });
        await page.evaluate(() => window.scrollTo(0, 0)).catch(() => {});
        await sleep(CONFIG.PAUSE_AFTER_SEARCH / 3);
    }

    // 5. Extracción directa del mejor producto según relevancia de búsqueda específica
    if (onStatus) onStatus({ type: 'log', message: '[SUPERMERCADO 1] Extrayendo datos del producto seleccionado...' });
    const baseConfig = validador.obtenerConfiguracionBusqueda(prodClean);
    const queryConfig = {
        ...baseConfig,
        marca: itemCat ? itemCat.marca : baseConfig.marca,
        variante: itemCat ? itemCat.variante : (baseConfig.variantesRequeridas[0] || null),
        cantidad: itemCat ? itemCat.cantidad : (cantidad || null),
        unidad: itemCat ? itemCat.unidad : (unidad || null),
        palabrasMarca: (itemCat ? validador.normalizar(itemCat.marca) : (baseConfig.marca ? validador.normalizar(baseConfig.marca) : '')).split(/\s+/).filter(w => w.length >= 2 && !['la', 'el', 'los', 'las', 'de', 'del'].includes(w)),
        marcasCompetidoras: Array.from(validador.MARCAS_CONOCIDAS || []),
        nombresSupermercados: (itemCat && itemCat.nombres_supermercados) ? itemCat.nombres_supermercados.map(n => validador.normalizar(n)) : []
    };

    const cData = await page.evaluate((config) => {
        function cleanText(s) {
            if (!s) return '';
            return s.toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '').replace(/(\d+)\s*%/g, '$1%').replace(/[.,;:!¡?¿()[\]"'\-_/]/g, ' ').replace(/\s+/g, ' ').trim();
        }
        function contienePalabra(texto, palabra) {
            if (!texto || !palabra) return false;
            if (palabra.length <= 4) {
                var rx = new RegExp('(?:^|\\s)' + palabra.replace(/[-\/\\^$*+?.()|[\]{}]/g, '\\$&') + '(?:$|\\s)', 'i');
                return rx.test(texto);
            }
            return texto.indexOf(palabra) > -1;
        }

        const cards = Array.from(document.querySelectorAll('article, [class*="product-summary"], [class*="vtex-search-result-3-x-galleryItem"], [class*="galleryItem"]'));
        var bestCandidate = null;
        var bestScore = -1;

        for (var i = 0; i < cards.length; i++) {
            var c = cards[i];
            var nEl = c.querySelector('h3, h2, [class*="productBrand"], [class*="nameContainer"], [data-testid="product-summary-name"], [class*="productName"]');
            var pEl = c.querySelector('[class*="sellingPrice"], [class*="currencyContainer"], [class*="price_sellingPrice"]');
            var lEl = c.querySelector('a[href*="/p"]') || c.querySelector('a');
            if (!nEl) continue;

            var nameVal = nEl.innerText.trim();
            if (!nameVal) continue;

            var priceVal = 'N/D';
            if (pEl && pEl.innerText && pEl.innerText.includes('$')) {
                priceVal = pEl.innerText.replace(/\n/g, ' ').replace(/\s+/g, ' ').trim();
            } else {
                var m = (c.innerText || '').match(/\$\s*[\d.,]+/g);
                if (m && m.length > 0) priceVal = m[0].trim();
            }
            var urlVal = lEl ? lEl.href : window.location.href;
            var cardText = (c.innerText || '').toLowerCase();
            var unavail = (c.querySelector('[class*="unavailable"], [class*="outOfStock"]') !== null) || cardText.indexOf('agotado') > -1 || cardText.indexOf('sin stock') > -1;
            if (priceVal === 'N/D' || priceVal === '' || priceVal === '$0' || priceVal === '$0,00') unavail = true;

            var nClean = cleanText(nameVal);

            // A) Filtro de términos incompatibles (accesorios u otras categorías)
            if (config.terminosIncompatibles && config.terminosIncompatibles.length > 0) {
                var inc = false;
                for (var k = 0; k < config.terminosIncompatibles.length; k++) {
                    if (contienePalabra(nClean, config.terminosIncompatibles[k])) { inc = true; break; }
                }
                if (inc) continue;
            }

            // A.2) Verificación estricta de categoría láctea
            if (config.categoria === 'leche' || (config.queryOriginal && config.queryOriginal.toLowerCase().indexOf('leche') > -1)) {
                // Descartar bebidas vegetales
                var esVegetal = ['vegetal', 'almendra', 'almendras', 'coco', 'soja', 'avena', 'mani', 'castana', 'castanas'].some(function(v) {
                    return contienePalabra(nClean, v);
                });
                if (esVegetal) continue;

                // Debe contener término lácteo si no coincide con diccionario oficial
                var tieneTerminoLeche = ['leche', 'lactea', 'uht'].some(function(t) {
                    return contienePalabra(nClean, t);
                });
                var esAliasDicc = config.nombresSupermercados && config.nombresSupermercados.some(function(alias) {
                    return alias === nClean || nClean.indexOf(alias) > -1 || alias.indexOf(nClean) > -1;
                });
                if (!tieneTerminoLeche && !esAliasDicc) continue;
            }

            // B) REQUISITO ESTRICTO DE MARCA: Jamás devolver Manaos si se buscó Coca Cola
            if (config.palabrasMarca && config.palabrasMarca.length > 0) {
                var esAliasDiccMarca = config.nombresSupermercados && config.nombresSupermercados.some(function(alias) {
                    return alias === nClean || nClean.indexOf(alias) > -1 || alias.indexOf(nClean) > -1;
                });
                var tieneMarcaReq = esAliasDiccMarca || config.palabrasMarca.every(function(w) {
                    if (w === 'lucchetti' || w === 'luchetti') {
                        return contienePalabra(nClean, 'lucchetti') || contienePalabra(nClean, 'luchetti');
                    }
                    return contienePalabra(nClean, w);
                });
                if (!tieneMarcaReq) continue; // Descarte de marcas ajenas

                // Descartar si menciona otra marca competidora
                var marcaBuscadaNorm = cleanText(config.marca || '');
                var tieneMarcaComp = false;
                if (config.marcasCompetidoras && config.marcasCompetidoras.length > 0) {
                    for (var mIdx = 0; mIdx < config.marcasCompetidoras.length; mIdx++) {
                        var mOtra = cleanText(config.marcasCompetidoras[mIdx]);
                        var esMisma = mOtra === marcaBuscadaNorm ||
                            marcaBuscadaNorm.includes(mOtra) ||
                            mOtra.includes(marcaBuscadaNorm) ||
                            ((marcaBuscadaNorm === 'lucchetti' || marcaBuscadaNorm === 'luchetti') && (mOtra === 'lucchetti' || mOtra === 'luchetti'));
                        if (!esMisma) {
                            if (contienePalabra(nClean, mOtra)) {
                                tieneMarcaComp = true;
                                break;
                            }
                        }
                    }
                }
                if (tieneMarcaComp) continue;
            }

            // C) REQUISITO DE VARIANTE (si aplica, ej: Pomelo vs Cola)
            if (config.variante) {
                var varNorm = cleanText(config.variante);
                var esAliasDicc = config.nombresSupermercados && config.nombresSupermercados.some(function(alias) {
                    return alias === nClean || nClean.indexOf(alias) > -1 || alias.indexOf(nClean) > -1;
                });
                var esBase = ['original', 'tradicional', 'clasica', 'clasico', 'comun', 'entera', 'suave'].some(function(b) {
                    return varNorm.indexOf(b) > -1;
                });
                if (!esAliasDicc && !esBase) {
                    if (varNorm.indexOf('lima') > -1 || varNorm.indexOf('limon') > -1) {
                        if (nClean.indexOf('lima') === -1 && nClean.indexOf('limon') === -1) continue;
                        if (['cola', 'naranja', 'pomelo', 'tonica', 'guarana'].some(function(vOp) { return contienePalabra(nClean, vOp); })) {
                            continue;
                        }
                    } else if (varNorm.indexOf('naranja') > -1) {
                        if (nClean.indexOf('naranja') === -1) continue;
                        if (['cola', 'pomelo', 'lima', 'limon', 'tonica', 'guarana'].some(function(vOp) { return contienePalabra(nClean, vOp); })) {
                            continue;
                        }
                    } else if (varNorm.indexOf('cola') > -1) {
                        if (nClean.indexOf('cola') === -1) continue;
                        if (['naranja', 'pomelo', 'lima', 'limon', 'tonica', 'guarana'].some(function(vOp) { return contienePalabra(nClean, vOp); })) {
                            continue;
                        }
                    } else if (varNorm.indexOf('tallarin') > -1) {
                        if (nClean.indexOf('tallarin') === -1 && nClean.indexOf('tallarines') === -1) continue;
                    } else if (nClean.indexOf(varNorm) === -1) {
                        continue;
                    }
                } else if (!esAliasDicc) {
                    if (['zero', 'light', 'diet', 'sin azucar'].some(function(vOp) { return contienePalabra(nClean, vOp); })) {
                        continue;
                    }
                    if (varNorm.indexOf('cola') > -1) {
                        if (['naranja', 'pomelo', 'lima', 'limon', 'tonica', 'guarana'].some(function(vOp) { return contienePalabra(nClean, vOp); })) {
                            continue;
                        }
                    }
                    if (varNorm.indexOf('lima') > -1 || varNorm.indexOf('limon') > -1) {
                        if (['cola', 'naranja', 'pomelo', 'tonica', 'guarana'].some(function(vOp) { return contienePalabra(nClean, vOp); })) {
                            continue;
                        }
                    }
                    if (varNorm.indexOf('naranja') > -1) {
                        if (['cola', 'pomelo', 'lima', 'limon', 'tonica', 'guarana'].some(function(vOp) { return contienePalabra(nClean, vOp); })) {
                            continue;
                        }
                    }
                    if (config.categoria === 'leche' || (config.queryOriginal && config.queryOriginal.toLowerCase().indexOf('leche') > -1)) {
                        if (['descremada', 'deslactosada', 'chocolatada', 'liviana', 'sin lactosa', 'protein', 'proteina', 'proteinas', 'extra protein', 'calcio', 'fibra', 'cardio', 'hierro', 'bio'].some(function(vOp) { return contienePalabra(nClean, vOp); })) {
                            continue;
                        }
                    }
                    if (config.categoria === 'limpieza' || config.categoria === 'papel_higienico' || (config.queryOriginal && (config.queryOriginal.toLowerCase().indexOf('papel higienico') > -1 || config.queryOriginal.toLowerCase().indexOf('higienol') > -1))) {
                        var qLowerC = (config.queryOriginal || '').toLowerCase();
                        var varLowerC = (config.variante || '').toLowerCase();
                        var pideMaxC = qLowerC.indexOf('max') > -1 || varLowerC.indexOf('max') > -1 || qLowerC.indexOf('100') > -1 || varLowerC.indexOf('100') > -1;
                        var esMaxC = contienePalabra(nClean, 'max') || nClean.indexOf('100 mts') > -1 || nClean.indexOf('100 m') > -1 || nClean.indexOf('100m') > -1 || nClean.indexOf('mega') > -1;

                        if (!pideMaxC && esMaxC) continue;
                        if (pideMaxC && !esMaxC) continue;
                    }
                }
            }

            // D) SCORING COMPLETO Y EXHAUSTIVO
            var score = 50;

            // Coincidencia con diccionario oficial de supermercados (máxima prioridad)
            if (config.nombresSupermercados && config.nombresSupermercados.length > 0) {
                for (var d = 0; d < config.nombresSupermercados.length; d++) {
                    var aliasNorm = config.nombresSupermercados[d];
                    if (aliasNorm === nClean) {
                        score += 250;
                        break;
                    } else if (nClean.indexOf(aliasNorm) > -1 || aliasNorm.indexOf(nClean) > -1) {
                        score += 180;
                        break;
                    }
                }
            }

            // Coincidencia de variante solicitada (ej: "clasica", "entera", "3%")
            if (config.variante) {
                var vNorm = cleanText(config.variante);
                if (vNorm.indexOf('clasica') > -1 || vNorm.indexOf('entera') > -1) {
                    if (nClean.indexOf('clasica') > -1 || nClean.indexOf('clasico') > -1) score += 70;
                    if (nClean.indexOf('entera') > -1) score += 60;
                    if (nClean.indexOf('3%') > -1 || nClean.indexOf('3 %') > -1) score += 70;
                } else if (vNorm.indexOf('original') > -1) {
                    if (nClean.indexOf('original') > -1) score += 70;
                } else if (vNorm.indexOf('largo fino') > -1) {
                    if (nClean.indexOf('largo fino') > -1) score += 70;
                } else if (vNorm.indexOf('tallarines') > -1 || vNorm.indexOf('tallarin') > -1) {
                    if (nClean.indexOf('tallarin') > -1 || nClean.indexOf('tallarines') > -1) score += 70;
                    if (nClean.indexOf('n5') > -1 || nClean.indexOf('n 5') > -1) score += 40;
                } else if (vNorm.indexOf('cola') > -1) {
                    if (contienePalabra(nClean, 'cola')) score += 70;
                } else if (vNorm.indexOf('naranja') > -1) {
                    if (contienePalabra(nClean, 'naranja')) score += 70;
                } else if (vNorm.indexOf('lima') > -1 || vNorm.indexOf('limon') > -1) {
                    if (contienePalabra(nClean, 'lima') || contienePalabra(nClean, 'limon')) score += 70;
                }
            }

            // Scoring por presentación
            if (config.cantidad && config.unidad) {
                var cantStr = String(config.cantidad).replace('.', ',');
                var cantDot = String(config.cantidad);
                var cantSpace = String(config.cantidad).replace('.', ' ');
                if (nClean.indexOf(cantStr) > -1 || nClean.indexOf(cantDot) > -1 || nClean.indexOf(cantSpace) > -1) {
                    score += 50;
                }
                if (config.unidad === 'L') {
                    if (config.cantidad === 1 && (nClean.indexOf('1l') > -1 || nClean.indexOf('1 l') > -1 || nClean.indexOf('1 lt') > -1 || nClean.indexOf('1lt') > -1 || nClean.indexOf('1000ml') > -1)) {
                        score += 50;
                    } else if (config.cantidad === 1.5 && (nClean.indexOf('1 5') > -1 || nClean.indexOf('1,5') > -1 || nClean.indexOf('1.5') > -1 || nClean.indexOf('1500ml') > -1)) {
                        score += 50;
                    } else if (config.cantidad === 2.25 && (nClean.indexOf('2 25') > -1 || nClean.indexOf('2,25') > -1 || nClean.indexOf('2.25') > -1 || nClean.indexOf('2250') > -1)) {
                        score += 50;
                    }
                }
                if (config.unidad === 'kg' && (nClean.indexOf('1kg') > -1 || nClean.indexOf('1 kg') > -1 || nClean.indexOf('1000g') > -1 || nClean.indexOf('1000 g') > -1)) {
                    score += 50;
                }
                if (config.unidad === 'g' && (nClean.indexOf(cantStr + 'g') > -1 || nClean.indexOf(cantDot + 'g') > -1 || nClean.indexOf(cantDot + ' g') > -1)) {
                    score += 50;
                }
                if (config.unidad === 'un' && (nClean.indexOf(cantDot + ' un') > -1 || nClean.indexOf(cantDot + ' uni') > -1 || nClean.indexOf(cantDot + ' ud') > -1 || nClean.indexOf(cantDot + ' rollos') > -1)) {
                    score += 50;
                }
            }

            // Término de categoría explícito
            if (config.categoria && nClean.indexOf(cleanText(config.categoria)) > -1) {
                score += 30;
            }

            if (score > bestScore) {
                bestScore = score;
                bestCandidate = {
                    name: nameVal,
                    price: priceVal,
                    url: urlVal,
                    stock: unavail ? 'SIN STOCK' : 'DISPONIBLE'
                };
            }
        }

        return bestCandidate;
    }, queryConfig);

    return cData ? { ...cData, terminoBuscado: textoATipear } : { name: 'No encontrado', price: 'N/D', url: page.url(), stock: 'NO ENCONTRADO', terminoBuscado: textoATipear };
}

// ------------------------------------------------------------------------------
// 2. COTO DIGITAL
// ------------------------------------------------------------------------------
async function searchCoto(page, prodClean, options = {}) {
    const { onStatus, typingDelay, mouseDuration, itemObj, cantidad, unidad } = options;
    checkAborted();

    const itemCat = catalogo.buscarEnCatalogo(itemObj) || catalogo.buscarEnCatalogo(prodClean);
    const baseTexto = (itemCat && itemCat.termino_busqueda) ? itemCat.termino_busqueda : ((itemObj && itemObj.terminoBusqueda) ? itemObj.terminoBusqueda : prodClean);
    const textoATipear = validador.adaptarTerminoSupermercado(baseTexto, 'COTO');

    const yaEnCoto = page.url().includes('coto.com.ar');
    const reusarBusqueda = yaEnCoto && options.ultimoTerminoBuscado && (options.ultimoTerminoBuscado.toLowerCase().trim() === textoATipear.toLowerCase().trim());

    if (!reusarBusqueda) {
        if (!yaEnCoto) {
            if (onStatus) {
                onStatus({ type: 'log', message: '[SUPERMERCADO 2] Navegando visualmente a https://www.coto.com.ar...' });
            }
            // 1. Navegar por barra de direcciones
            await visibleNavigate(page, 'https://www.coto.com.ar', typingDelay);
            await sleep(CONFIG.PAUSE_AFTER_PAGE_LOAD);
            await eliminarCookies(page);
        } else {
            await page.evaluate(() => window.scrollTo(0, 0)).catch(() => {});
            await eliminarCookies(page);
            await sleep(250);
        }

        // 2. Localizar buscador de COTO
        if (onStatus) onStatus({ type: 'log', message: `[SUPERMERCADO 2] Localizando buscador para: "${textoATipear}"...` });
        const cotoSearchSel = 'input#cio-autocomplete-0-input, input.cio-input, input[placeholder*="comprar" i], input[type="search"]';
        await page.waitForSelector(cotoSearchSel, { visible: true, timeout: 10000 }).catch(() => {});

        // 3. Tipear carácter por carácter
        let typedOkCt = await visibleType(page, cotoSearchSel, textoATipear, typingDelay, mouseDuration);
        if (!typedOkCt) {
            await visibleNavigate(page, 'https://www.coto.com.ar', typingDelay);
            await sleep(CONFIG.PAUSE_AFTER_PAGE_LOAD);
            await eliminarCookies(page);
            typedOkCt = await visibleType(page, cotoSearchSel, textoATipear, typingDelay, mouseDuration);
        }
        if (!typedOkCt) {
            throw new Error('No se encontró un buscador visible de COTO.');
        }

        // 4. Ejecutar búsqueda
        const cotoBtnSel = 'button.cio-submit-btn, button[type="submit"], .cio-search-submit';
        const clickedBtnCt = await visibleClick(page, cotoBtnSel, mouseDuration);
        if (!clickedBtnCt) {
            await visibleKey('{ENTER}');
        }

        if (onStatus) onStatus({ type: 'log', message: '[SUPERMERCADO 2] Esperando resultados de búsqueda...' });
        await sleep(CONFIG.PAUSE_AFTER_SEARCH);
        await eliminarCookies(page);
    } else {
        if (onStatus) onStatus({ type: 'log', message: `[SUPERMERCADO 2] Término de catálogo idéntico al anterior ("${textoATipear}"). Reutilizando resultados en pantalla para extraer "${prodClean}"...` });
        await page.evaluate(() => window.scrollTo(0, 0)).catch(() => {});
        await sleep(CONFIG.PAUSE_AFTER_SEARCH / 3);
    }

    // 5. Extracción directa del mejor producto según relevancia de búsqueda específica
    if (onStatus) onStatus({ type: 'log', message: '[SUPERMERCADO 2] Extrayendo datos del producto seleccionado...' });
    const baseConfig = validador.obtenerConfiguracionBusqueda(prodClean);
    const queryConfig = {
        ...baseConfig,
        marca: itemCat ? itemCat.marca : baseConfig.marca,
        variante: itemCat ? itemCat.variante : (baseConfig.variantesRequeridas[0] || null),
        cantidad: itemCat ? itemCat.cantidad : (cantidad || null),
        unidad: itemCat ? itemCat.unidad : (unidad || null),
        palabrasMarca: (itemCat ? validador.normalizar(itemCat.marca) : (baseConfig.marca ? validador.normalizar(baseConfig.marca) : '')).split(/\s+/).filter(w => w.length >= 2 && !['la', 'el', 'los', 'las', 'de', 'del'].includes(w)),
        marcasCompetidoras: Array.from(validador.MARCAS_CONOCIDAS || []),
        nombresSupermercados: (itemCat && itemCat.nombres_supermercados) ? itemCat.nombres_supermercados.map(n => validador.normalizar(n)) : []
    };

    const ctData = await page.evaluate((config) => {
        function cleanText(s) {
            if (!s) return '';
            return s.toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '').replace(/(\d+)\s*%/g, '$1%').replace(/[.,;:!¡?¿()[\]"'\-_/]/g, ' ').replace(/\s+/g, ' ').trim();
        }
        function contienePalabra(texto, palabra) {
            if (!texto || !palabra) return false;
            if (palabra.length <= 4) {
                var rx = new RegExp('(?:^|\\s)' + palabra.replace(/[-\/\\^$*+?.()|[\]{}]/g, '\\$&') + '(?:$|\\s)', 'i');
                return rx.test(texto);
            }
            return texto.indexOf(palabra) > -1;
        }

        var items = Array.from(document.querySelectorAll('constructor-result-item, .product-card, article')).slice(0, 25);
        if (items.length === 0) return null;

        var bestCandidate = null;
        var bestScore = -1;

        for (var i = 0; i < items.length; i++) {
            var it = items[i];
            var nEl = it.querySelector('.nombre-producto, h3, h2, [class*="title"]');
            var pEl = it.querySelector('.card-title, h4, [class*="price"]');
            var lEl = it.querySelector('a');
            if (!nEl) continue;

            var nameVal = nEl.innerText.trim();
            if (!nameVal) continue;

            var priceVal = pEl ? pEl.innerText.replace(/\n/g, ' ').replace(/\s+/g, ' ').trim() : 'N/D';
            var urlVal = lEl ? lEl.href : window.location.href;
            var itText = (it.innerText || '').toLowerCase();
            var unavail = itText.indexOf('sin stock') > -1 || itText.indexOf('agotado') > -1 || itText.indexOf('no disponible') > -1;
            if (priceVal === 'N/D' || priceVal === '' || priceVal === '$0' || priceVal === '$0,00') unavail = true;

            var nClean = cleanText(nameVal);

            // A) Filtro de términos incompatibles (accesorios u otras categorías)
            if (config.terminosIncompatibles && config.terminosIncompatibles.length > 0) {
                var inc = false;
                for (var k = 0; k < config.terminosIncompatibles.length; k++) {
                    if (contienePalabra(nClean, config.terminosIncompatibles[k])) { inc = true; break; }
                }
                if (inc) continue;
            }

            // A.2) Verificación estricta de categoría láctea
            if (config.categoria === 'leche' || (config.queryOriginal && config.queryOriginal.toLowerCase().indexOf('leche') > -1)) {
                // Descartar bebidas vegetales
                var esVegetal = ['vegetal', 'almendra', 'almendras', 'coco', 'soja', 'avena', 'mani', 'castana', 'castanas'].some(function(v) {
                    return contienePalabra(nClean, v);
                });
                if (esVegetal) continue;

                // Debe contener término lácteo si no coincide con diccionario oficial
                var tieneTerminoLeche = ['leche', 'lactea', 'uht'].some(function(t) {
                    return contienePalabra(nClean, t);
                });
                var esAliasDicc = config.nombresSupermercados && config.nombresSupermercados.some(function(alias) {
                    return alias === nClean || nClean.indexOf(alias) > -1 || alias.indexOf(nClean) > -1;
                });
                if (!tieneTerminoLeche && !esAliasDicc) continue;
            }

            // B) REQUISITO ESTRICTO DE MARCA: Jamás devolver Manaos si se buscó Coca Cola
            if (config.palabrasMarca && config.palabrasMarca.length > 0) {
                var esAliasDiccMarcaCt = config.nombresSupermercados && config.nombresSupermercados.some(function(alias) {
                    return alias === nClean || nClean.indexOf(alias) > -1 || alias.indexOf(nClean) > -1;
                });
                var tieneMarcaReq = esAliasDiccMarcaCt || config.palabrasMarca.every(function(w) {
                    if (w === 'lucchetti' || w === 'luchetti') {
                        return contienePalabra(nClean, 'lucchetti') || contienePalabra(nClean, 'luchetti');
                    }
                    return contienePalabra(nClean, w);
                });
                if (!tieneMarcaReq) continue;

                // Descartar si menciona otra marca competidora
                var marcaBuscadaNorm = cleanText(config.marca || '');
                var tieneMarcaComp = false;
                if (config.marcasCompetidoras && config.marcasCompetidoras.length > 0) {
                    for (var mIdx = 0; mIdx < config.marcasCompetidoras.length; mIdx++) {
                        var mOtra = cleanText(config.marcasCompetidoras[mIdx]);
                        var esMisma = mOtra === marcaBuscadaNorm ||
                            marcaBuscadaNorm.includes(mOtra) ||
                            mOtra.includes(marcaBuscadaNorm) ||
                            ((marcaBuscadaNorm === 'lucchetti' || marcaBuscadaNorm === 'luchetti') && (mOtra === 'lucchetti' || mOtra === 'luchetti'));
                        if (!esMisma) {
                            if (contienePalabra(nClean, mOtra)) {
                                tieneMarcaComp = true;
                                break;
                            }
                        }
                    }
                }
                if (tieneMarcaComp) continue;
            }

            // C) REQUISITO DE VARIANTE
            if (config.variante) {
                var varNorm = cleanText(config.variante);
                var esAliasDicc = config.nombresSupermercados && config.nombresSupermercados.some(function(alias) {
                    return alias === nClean || nClean.indexOf(alias) > -1 || alias.indexOf(nClean) > -1;
                });
                var esBase = ['original', 'tradicional', 'clasica', 'clasico', 'comun', 'entera', 'suave'].some(function(b) {
                    return varNorm.indexOf(b) > -1;
                });
                if (!esAliasDicc && !esBase) {
                    if (varNorm.indexOf('lima') > -1 || varNorm.indexOf('limon') > -1) {
                        if (nClean.indexOf('lima') === -1 && nClean.indexOf('limon') === -1) continue;
                        if (['cola', 'naranja', 'pomelo', 'tonica', 'guarana'].some(function(vOp) { return contienePalabra(nClean, vOp); })) {
                            continue;
                        }
                    } else if (varNorm.indexOf('naranja') > -1) {
                        if (nClean.indexOf('naranja') === -1) continue;
                        if (['cola', 'pomelo', 'lima', 'limon', 'tonica', 'guarana'].some(function(vOp) { return contienePalabra(nClean, vOp); })) {
                            continue;
                        }
                    } else if (varNorm.indexOf('cola') > -1) {
                        if (nClean.indexOf('cola') === -1) continue;
                        if (['naranja', 'pomelo', 'lima', 'limon', 'tonica', 'guarana'].some(function(vOp) { return contienePalabra(nClean, vOp); })) {
                            continue;
                        }
                    } else if (varNorm.indexOf('tallarin') > -1) {
                        if (nClean.indexOf('tallarin') === -1 && nClean.indexOf('tallarines') === -1) continue;
                    } else if (nClean.indexOf(varNorm) === -1) {
                        continue;
                    }
                } else if (!esAliasDicc) {
                    if (['zero', 'light', 'diet', 'sin azucar'].some(function(vOp) { return contienePalabra(nClean, vOp); })) {
                        continue;
                    }
                    if (varNorm.indexOf('cola') > -1) {
                        if (['naranja', 'pomelo', 'lima', 'limon', 'tonica', 'guarana'].some(function(vOp) { return contienePalabra(nClean, vOp); })) {
                            continue;
                        }
                    }
                    if (varNorm.indexOf('lima') > -1 || varNorm.indexOf('limon') > -1) {
                        if (['cola', 'naranja', 'pomelo', 'tonica', 'guarana'].some(function(vOp) { return contienePalabra(nClean, vOp); })) {
                            continue;
                        }
                    }
                    if (varNorm.indexOf('naranja') > -1) {
                        if (['cola', 'pomelo', 'lima', 'limon', 'tonica', 'guarana'].some(function(vOp) { return contienePalabra(nClean, vOp); })) {
                            continue;
                        }
                    }
                    if (config.categoria === 'leche' || (config.queryOriginal && config.queryOriginal.toLowerCase().indexOf('leche') > -1)) {
                        if (['descremada', 'deslactosada', 'chocolatada', 'liviana', 'sin lactosa', 'protein', 'proteina', 'proteinas', 'extra protein', 'calcio', 'fibra', 'cardio', 'hierro', 'bio'].some(function(vOp) { return contienePalabra(nClean, vOp); })) {
                            continue;
                        }
                    }
                    if (config.categoria === 'limpieza' || config.categoria === 'papel_higienico' || (config.queryOriginal && (config.queryOriginal.toLowerCase().indexOf('papel higienico') > -1 || config.queryOriginal.toLowerCase().indexOf('higienol') > -1))) {
                        var qLowerCo = (config.queryOriginal || '').toLowerCase();
                        var varLowerCo = (config.variante || '').toLowerCase();
                        var pideMaxCo = qLowerCo.indexOf('max') > -1 || varLowerCo.indexOf('max') > -1 || qLowerCo.indexOf('100') > -1 || varLowerCo.indexOf('100') > -1;
                        var esMaxCo = contienePalabra(nClean, 'max') || nClean.indexOf('100 mts') > -1 || nClean.indexOf('100 m') > -1 || nClean.indexOf('100m') > -1 || nClean.indexOf('mega') > -1;

                        if (!pideMaxCo && esMaxCo) continue;
                        if (pideMaxCo && !esMaxCo) continue;
                    }
                }
            }

            // D) SCORING COMPLETO Y EXHAUSTIVO
            var score = 50;

            // Coincidencia con diccionario oficial de supermercados (máxima prioridad)
            if (config.nombresSupermercados && config.nombresSupermercados.length > 0) {
                for (var d = 0; d < config.nombresSupermercados.length; d++) {
                    var aliasNorm = config.nombresSupermercados[d];
                    if (aliasNorm === nClean) {
                        score += 250;
                        break;
                    } else if (nClean.indexOf(aliasNorm) > -1 || aliasNorm.indexOf(nClean) > -1) {
                        score += 180;
                        break;
                    }
                }
            }

            // Coincidencia de variante solicitada (ej: "clasica", "entera", "3%")
            if (config.variante) {
                var vNorm = cleanText(config.variante);
                if (vNorm.indexOf('clasica') > -1 || vNorm.indexOf('entera') > -1) {
                    if (nClean.indexOf('clasica') > -1 || nClean.indexOf('clasico') > -1) score += 70;
                    if (nClean.indexOf('entera') > -1) score += 60;
                    if (nClean.indexOf('3%') > -1 || nClean.indexOf('3 %') > -1) score += 70;
                } else if (vNorm.indexOf('original') > -1) {
                    if (nClean.indexOf('original') > -1) score += 70;
                } else if (vNorm.indexOf('largo fino') > -1) {
                    if (nClean.indexOf('largo fino') > -1) score += 70;
                } else if (vNorm.indexOf('tallarines') > -1 || vNorm.indexOf('tallarin') > -1) {
                    if (nClean.indexOf('tallarin') > -1 || nClean.indexOf('tallarines') > -1) score += 70;
                    if (nClean.indexOf('n5') > -1 || nClean.indexOf('n 5') > -1) score += 40;
                } else if (vNorm.indexOf('cola') > -1) {
                    if (contienePalabra(nClean, 'cola')) score += 70;
                } else if (vNorm.indexOf('naranja') > -1) {
                    if (contienePalabra(nClean, 'naranja')) score += 70;
                } else if (vNorm.indexOf('lima') > -1 || vNorm.indexOf('limon') > -1) {
                    if (contienePalabra(nClean, 'lima') || contienePalabra(nClean, 'limon')) score += 70;
                }
            }

            // Scoring por presentación
            if (config.cantidad && config.unidad) {
                var cantStr = String(config.cantidad).replace('.', ',');
                var cantDot = String(config.cantidad);
                var cantSpace = String(config.cantidad).replace('.', ' ');
                if (nClean.indexOf(cantStr) > -1 || nClean.indexOf(cantDot) > -1 || nClean.indexOf(cantSpace) > -1) {
                    score += 50;
                }
                if (config.unidad === 'L') {
                    if (config.cantidad === 1 && (nClean.indexOf('1l') > -1 || nClean.indexOf('1 l') > -1 || nClean.indexOf('1 lt') > -1 || nClean.indexOf('1lt') > -1 || nClean.indexOf('1000ml') > -1)) {
                        score += 50;
                    } else if (config.cantidad === 1.5 && (nClean.indexOf('1 5') > -1 || nClean.indexOf('1,5') > -1 || nClean.indexOf('1.5') > -1 || nClean.indexOf('1500ml') > -1)) {
                        score += 50;
                    } else if (config.cantidad === 2.25 && (nClean.indexOf('2 25') > -1 || nClean.indexOf('2,25') > -1 || nClean.indexOf('2.25') > -1 || nClean.indexOf('2250') > -1)) {
                        score += 50;
                    }
                }
                if (config.unidad === 'kg' && (nClean.indexOf('1kg') > -1 || nClean.indexOf('1 kg') > -1 || nClean.indexOf('1000g') > -1 || nClean.indexOf('1000 g') > -1)) {
                    score += 50;
                }
                if (config.unidad === 'g' && (nClean.indexOf(cantStr + 'g') > -1 || nClean.indexOf(cantDot + 'g') > -1 || nClean.indexOf(cantDot + ' g') > -1)) {
                    score += 50;
                }
            }

            // Término de categoría explícito
            if (config.categoria && nClean.indexOf(cleanText(config.categoria)) > -1) {
                score += 30;
            }

            if (score > bestScore) {
                bestScore = score;
                bestCandidate = {
                    name: nameVal,
                    price: priceVal,
                    url: urlVal,
                    stock: unavail ? 'SIN STOCK' : 'DISPONIBLE'
                };
            }
        }

        return bestCandidate;
    }, queryConfig);

    return ctData ? { ...ctData, terminoBuscado: textoATipear } : { name: 'No encontrado', price: 'N/D', url: page.url(), stock: 'NO ENCONTRADO', terminoBuscado: textoATipear };
}

// ------------------------------------------------------------------------------
// 3. DÍA %
// ------------------------------------------------------------------------------
async function searchDia(page, prodClean, options = {}) {
    const { onStatus, typingDelay, mouseDuration, itemObj, cantidad, unidad } = options;
    checkAborted();

    const itemCat = catalogo.buscarEnCatalogo(itemObj) || catalogo.buscarEnCatalogo(prodClean);
    const baseTexto = (itemCat && itemCat.termino_busqueda) ? itemCat.termino_busqueda : ((itemObj && itemObj.terminoBusqueda) ? itemObj.terminoBusqueda : prodClean);
    const textoATipear = validador.adaptarTerminoSupermercado(baseTexto, 'Día %');

    const yaEnDia = page.url().includes('supermercadosdia.com.ar');
    const reusarBusqueda = yaEnDia && options.ultimoTerminoBuscado && (options.ultimoTerminoBuscado.toLowerCase().trim() === textoATipear.toLowerCase().trim());

    if (!reusarBusqueda) {
        if (!yaEnDia) {
            if (onStatus) {
                onStatus({ type: 'log', message: '[SUPERMERCADO 3] Navegando visualmente a https://diaonline.supermercadosdia.com.ar...' });
            }
            // 1. Navegar por barra de direcciones
            await visibleNavigate(page, 'https://diaonline.supermercadosdia.com.ar', typingDelay);
            await sleep(CONFIG.PAUSE_AFTER_PAGE_LOAD);
            await eliminarCookies(page);
        } else {
            await page.evaluate(() => window.scrollTo(0, 0)).catch(() => {});
            await eliminarCookies(page);
            await sleep(250);
        }

        // 2. Localizar buscador de Día %
        if (onStatus) onStatus({ type: 'log', message: `[SUPERMERCADO 3] Localizando buscador para: "${textoATipear}"...` });
        const diaSearchSel = 'input[placeholder*="busc" i], input.vtex-styleguide-9-x-input';
        await page.waitForSelector(diaSearchSel, { timeout: 10000 }).catch(() => {});

        // 3. Tipear carácter por carácter de forma visible
        let typedOkDia = await visibleType(page, diaSearchSel, textoATipear, typingDelay, mouseDuration);
        if (!typedOkDia) {
            await visibleNavigate(page, 'https://diaonline.supermercadosdia.com.ar', typingDelay);
            await sleep(CONFIG.PAUSE_AFTER_PAGE_LOAD);
            await eliminarCookies(page);
            typedOkDia = await visibleType(page, diaSearchSel, textoATipear, typingDelay, mouseDuration);
        }
        if (!typedOkDia) {
            throw new Error('No se encontró un buscador visible de Día %.');
        }

        // 4. Ejecutar búsqueda con Enter
        await sleep(300);
        await visibleKey('{ENTER}');

        if (onStatus) onStatus({ type: 'log', message: '[SUPERMERCADO 3] Esperando resultados de búsqueda...' });
        for (let w = 0; w < 20; w++) {
            await sleep(500);
            const curU = page.url();
            if (curU.includes(encodeURIComponent(prodClean)) || curU.includes(encodeURIComponent(textoATipear)) || curU.includes('_q=')) {
                break;
            }
            if (w === 3) {
                await visibleKey('{ENTER}');
                await visibleClick(page, 'button[class*="searchIcon"], button[type="submit"], [class*="search-bar"] button', mouseDuration);
            }
        }
        await sleep(CONFIG.PAUSE_AFTER_SEARCH);
        await eliminarCookies(page);
    } else {
        if (onStatus) onStatus({ type: 'log', message: `[SUPERMERCADO 3] Término de catálogo idéntico al anterior ("${textoATipear}"). Reutilizando resultados en pantalla para extraer "${prodClean}"...` });
        await page.evaluate(() => window.scrollTo(0, 0)).catch(() => {});
        await sleep(CONFIG.PAUSE_AFTER_SEARCH / 3);
    }

    // 5. Extracción directa del mejor producto según relevancia de búsqueda específica
    if (onStatus) onStatus({ type: 'log', message: '[SUPERMERCADO 3] Extrayendo datos del producto seleccionado...' });
    const baseConfig = validador.obtenerConfiguracionBusqueda(prodClean);
    const queryConfig = {
        ...baseConfig,
        marca: itemCat ? itemCat.marca : baseConfig.marca,
        variante: itemCat ? itemCat.variante : (baseConfig.variantesRequeridas[0] || null),
        cantidad: itemCat ? itemCat.cantidad : (cantidad || null),
        unidad: itemCat ? itemCat.unidad : (unidad || null),
        palabrasMarca: (itemCat ? validador.normalizar(itemCat.marca) : (baseConfig.marca ? validador.normalizar(baseConfig.marca) : '')).split(/\s+/).filter(w => w.length >= 2 && !['la', 'el', 'los', 'las', 'de', 'del'].includes(w)),
        marcasCompetidoras: Array.from(validador.MARCAS_CONOCIDAS || []),
        nombresSupermercados: (itemCat && itemCat.nombres_supermercados) ? itemCat.nombres_supermercados.map(n => validador.normalizar(n)) : []
    };

    const dData = await page.evaluate((config) => {
        function cleanText(s) {
            if (!s) return '';
            return s.toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '').replace(/(\d+)\s*%/g, '$1%').replace(/[.,;:!¡?¿()[\]"'\-_/]/g, ' ').replace(/\s+/g, ' ').trim();
        }
        function contienePalabra(texto, palabra) {
            if (!texto || !palabra) return false;
            if (palabra.length <= 4) {
                var rx = new RegExp('(?:^|\\s)' + palabra.replace(/[-\/\\^$*+?.()|[\]{}]/g, '\\$&') + '(?:$|\\s)', 'i');
                return rx.test(texto);
            }
            return texto.indexOf(palabra) > -1;
        }

        const cards = Array.from(document.querySelectorAll('article, section[class*="product-summary"], [class*="galleryItem"]'));
        var bestCandidate = null;
        var bestScore = -1;

        for (var i = 0; i < cards.length; i++) {
            var c = cards[i];
            var nEl = c.querySelector('h3, h2, [class*="productBrand"], [class*="nameContainer"], [class*="productName"]');
            var pEl = c.querySelector('[class*="sellingPriceValue"], [class*="sellingPrice"], [class*="currencyContainer"], [class*="price"]');
            var lEl = c.querySelector('a[href*="/p"]') || c.querySelector('a');
            if (!nEl) continue;

            var nameVal = nEl.innerText.trim();
            if (!nameVal) continue;

            var priceVal = 'N/D';
            if (pEl && pEl.innerText && pEl.innerText.includes('$')) {
                priceVal = pEl.innerText.replace(/\n/g, ' ').replace(/\s+/g, ' ').trim();
            } else {
                var m = (c.innerText || '').match(/\$\s*[\d.,]+/g);
                if (m && m.length > 0) priceVal = (m[1] || m[0]).trim();
            }
            var urlVal = lEl ? lEl.href : window.location.href;
            var cardText = (c.innerText || '').toLowerCase();
            var unavail = (c.querySelector('[class*="unavailable"], [class*="outOfStock"]') !== null) || cardText.indexOf('agotado') > -1 || cardText.indexOf('sin stock') > -1;
            if (priceVal === 'N/D' || priceVal === '' || priceVal === '$0' || priceVal === '$0,00') unavail = true;

            var nClean = cleanText(nameVal);

            // A) Filtro de términos incompatibles (accesorios u otras categorías)
            if (config.terminosIncompatibles && config.terminosIncompatibles.length > 0) {
                var inc = false;
                for (var k = 0; k < config.terminosIncompatibles.length; k++) {
                    if (contienePalabra(nClean, config.terminosIncompatibles[k])) { inc = true; break; }
                }
                if (inc) continue;
            }

            // A.2) Verificación estricta de categoría láctea
            if (config.categoria === 'leche' || (config.queryOriginal && config.queryOriginal.toLowerCase().indexOf('leche') > -1)) {
                // Descartar bebidas vegetales
                var esVegetal = ['vegetal', 'almendra', 'almendras', 'coco', 'soja', 'avena', 'mani', 'castana', 'castanas'].some(function(v) {
                    return contienePalabra(nClean, v);
                });
                if (esVegetal) continue;

                // Debe contener término lácteo si no coincide con diccionario oficial
                var tieneTerminoLeche = ['leche', 'lactea', 'uht'].some(function(t) {
                    return contienePalabra(nClean, t);
                });
                var esAliasDicc = config.nombresSupermercados && config.nombresSupermercados.some(function(alias) {
                    return alias === nClean || nClean.indexOf(alias) > -1 || alias.indexOf(nClean) > -1;
                });
                if (!tieneTerminoLeche && !esAliasDicc) continue;
            }

            // B) REQUISITO ESTRICTO DE MARCA: Jamás devolver Manaos si se buscó Coca Cola
            if (config.palabrasMarca && config.palabrasMarca.length > 0) {
                var esAliasDiccMarcaDia = config.nombresSupermercados && config.nombresSupermercados.some(function(alias) {
                    return alias === nClean || nClean.indexOf(alias) > -1 || alias.indexOf(nClean) > -1;
                });
                var tieneMarcaReq = esAliasDiccMarcaDia || config.palabrasMarca.every(function(w) {
                    if (w === 'lucchetti' || w === 'luchetti') {
                        return contienePalabra(nClean, 'lucchetti') || contienePalabra(nClean, 'luchetti');
                    }
                    return contienePalabra(nClean, w);
                });
                if (!tieneMarcaReq) continue;

                // Descartar si menciona otra marca competidora
                var marcaBuscadaNorm = cleanText(config.marca || '');
                var tieneMarcaComp = false;
                if (config.marcasCompetidoras && config.marcasCompetidoras.length > 0) {
                    for (var mIdx = 0; mIdx < config.marcasCompetidoras.length; mIdx++) {
                        var mOtra = cleanText(config.marcasCompetidoras[mIdx]);
                        var esMisma = mOtra === marcaBuscadaNorm ||
                            marcaBuscadaNorm.includes(mOtra) ||
                            mOtra.includes(marcaBuscadaNorm) ||
                            ((marcaBuscadaNorm === 'lucchetti' || marcaBuscadaNorm === 'luchetti') && (mOtra === 'lucchetti' || mOtra === 'luchetti'));
                        if (!esMisma) {
                            if (contienePalabra(nClean, mOtra)) {
                                tieneMarcaComp = true;
                                break;
                            }
                        }
                    }
                }
                if (tieneMarcaComp) continue;
            }

            // C) REQUISITO DE VARIANTE
            if (config.variante) {
                var varNorm = cleanText(config.variante);
                var esAliasDicc = config.nombresSupermercados && config.nombresSupermercados.some(function(alias) {
                    return alias === nClean || nClean.indexOf(alias) > -1 || alias.indexOf(nClean) > -1;
                });
                var esBase = ['original', 'tradicional', 'clasica', 'clasico', 'comun', 'entera', 'suave'].some(function(b) {
                    return varNorm.indexOf(b) > -1;
                });
                if (!esAliasDicc && !esBase) {
                    if (varNorm.indexOf('lima') > -1 || varNorm.indexOf('limon') > -1) {
                        if (nClean.indexOf('lima') === -1 && nClean.indexOf('limon') === -1) continue;
                        if (['cola', 'naranja', 'pomelo', 'tonica', 'guarana'].some(function(vOp) { return contienePalabra(nClean, vOp); })) {
                            continue;
                        }
                    } else if (varNorm.indexOf('naranja') > -1) {
                        if (nClean.indexOf('naranja') === -1) continue;
                        if (['cola', 'pomelo', 'lima', 'limon', 'tonica', 'guarana'].some(function(vOp) { return contienePalabra(nClean, vOp); })) {
                            continue;
                        }
                    } else if (varNorm.indexOf('cola') > -1) {
                        if (nClean.indexOf('cola') === -1) continue;
                        if (['naranja', 'pomelo', 'lima', 'limon', 'tonica', 'guarana'].some(function(vOp) { return contienePalabra(nClean, vOp); })) {
                            continue;
                        }
                    } else if (varNorm.indexOf('tallarin') > -1) {
                        if (nClean.indexOf('tallarin') === -1 && nClean.indexOf('tallarines') === -1) continue;
                    } else if (nClean.indexOf(varNorm) === -1) {
                        continue;
                    }
                } else if (!esAliasDicc) {
                    if (['zero', 'light', 'diet', 'sin azucar'].some(function(vOp) { return contienePalabra(nClean, vOp); })) {
                        continue;
                    }
                    if (varNorm.indexOf('cola') > -1) {
                        if (['naranja', 'pomelo', 'lima', 'limon', 'tonica', 'guarana'].some(function(vOp) { return contienePalabra(nClean, vOp); })) {
                            continue;
                        }
                    }
                    if (varNorm.indexOf('lima') > -1 || varNorm.indexOf('limon') > -1) {
                        if (['cola', 'naranja', 'pomelo', 'tonica', 'guarana'].some(function(vOp) { return contienePalabra(nClean, vOp); })) {
                            continue;
                        }
                    }
                    if (varNorm.indexOf('naranja') > -1) {
                        if (['cola', 'pomelo', 'lima', 'limon', 'tonica', 'guarana'].some(function(vOp) { return contienePalabra(nClean, vOp); })) {
                            continue;
                        }
                    }
                    if (config.categoria === 'leche' || (config.queryOriginal && config.queryOriginal.toLowerCase().indexOf('leche') > -1)) {
                        if (['descremada', 'deslactosada', 'chocolatada', 'liviana', 'sin lactosa', 'protein', 'proteina', 'proteinas', 'extra protein', 'calcio', 'fibra', 'cardio', 'hierro', 'bio'].some(function(vOp) { return contienePalabra(nClean, vOp); })) {
                            continue;
                        }
                    }
                    if (config.categoria === 'limpieza' || config.categoria === 'papel_higienico' || (config.queryOriginal && (config.queryOriginal.toLowerCase().indexOf('papel higienico') > -1 || config.queryOriginal.toLowerCase().indexOf('higienol') > -1))) {
                        var qLowerD = (config.queryOriginal || '').toLowerCase();
                        var varLowerD = (config.variante || '').toLowerCase();
                        var pideMaxD = qLowerD.indexOf('max') > -1 || varLowerD.indexOf('max') > -1 || qLowerD.indexOf('100') > -1 || varLowerD.indexOf('100') > -1;
                        var esMaxD = contienePalabra(nClean, 'max') || nClean.indexOf('100 mts') > -1 || nClean.indexOf('100 m') > -1 || nClean.indexOf('100m') > -1 || nClean.indexOf('mega') > -1;

                        if (!pideMaxD && esMaxD) continue;
                        if (pideMaxD && !esMaxD) continue;
                    }
                }
            }

            // D) SCORING COMPLETO Y EXHAUSTIVO
            var score = 50;

            // Coincidencia con diccionario oficial de supermercados (máxima prioridad)
            if (config.nombresSupermercados && config.nombresSupermercados.length > 0) {
                for (var d = 0; d < config.nombresSupermercados.length; d++) {
                    var aliasNorm = config.nombresSupermercados[d];
                    if (aliasNorm === nClean) {
                        score += 250;
                        break;
                    } else if (nClean.indexOf(aliasNorm) > -1 || aliasNorm.indexOf(nClean) > -1) {
                        score += 180;
                        break;
                    }
                }
            }

            // Coincidencia de variante solicitada (ej: "clasica", "entera", "3%")
            if (config.variante) {
                var vNorm = cleanText(config.variante);
                if (vNorm.indexOf('clasica') > -1 || vNorm.indexOf('entera') > -1) {
                    if (nClean.indexOf('clasica') > -1 || nClean.indexOf('clasico') > -1) score += 70;
                    if (nClean.indexOf('entera') > -1) score += 60;
                    if (nClean.indexOf('3%') > -1 || nClean.indexOf('3 %') > -1) score += 70;
                } else if (vNorm.indexOf('original') > -1) {
                    if (nClean.indexOf('original') > -1) score += 70;
                } else if (vNorm.indexOf('largo fino') > -1) {
                    if (nClean.indexOf('largo fino') > -1) score += 70;
                } else if (vNorm.indexOf('tallarines') > -1 || vNorm.indexOf('tallarin') > -1) {
                    if (nClean.indexOf('tallarin') > -1 || nClean.indexOf('tallarines') > -1) score += 70;
                    if (nClean.indexOf('n5') > -1 || nClean.indexOf('n 5') > -1) score += 40;
                } else if (vNorm.indexOf('cola') > -1) {
                    if (contienePalabra(nClean, 'cola')) score += 70;
                } else if (vNorm.indexOf('naranja') > -1) {
                    if (contienePalabra(nClean, 'naranja')) score += 70;
                } else if (vNorm.indexOf('lima') > -1 || vNorm.indexOf('limon') > -1) {
                    if (contienePalabra(nClean, 'lima') || contienePalabra(nClean, 'limon')) score += 70;
                }
            }

            // Scoring por presentación
            if (config.cantidad && config.unidad) {
                var cantStr = String(config.cantidad).replace('.', ',');
                var cantDot = String(config.cantidad);
                var cantSpace = String(config.cantidad).replace('.', ' ');
                if (nClean.indexOf(cantStr) > -1 || nClean.indexOf(cantDot) > -1 || nClean.indexOf(cantSpace) > -1) {
                    score += 50;
                }
                if (config.unidad === 'L') {
                    if (config.cantidad === 1 && (nClean.indexOf('1l') > -1 || nClean.indexOf('1 l') > -1 || nClean.indexOf('1 lt') > -1 || nClean.indexOf('1lt') > -1 || nClean.indexOf('1000ml') > -1)) {
                        score += 50;
                    } else if (config.cantidad === 1.5 && (nClean.indexOf('1 5') > -1 || nClean.indexOf('1,5') > -1 || nClean.indexOf('1.5') > -1 || nClean.indexOf('1500ml') > -1)) {
                        score += 50;
                    } else if (config.cantidad === 2.25 && (nClean.indexOf('2 25') > -1 || nClean.indexOf('2,25') > -1 || nClean.indexOf('2.25') > -1 || nClean.indexOf('2250') > -1)) {
                        score += 50;
                    }
                }
                if (config.unidad === 'kg' && (nClean.indexOf('1kg') > -1 || nClean.indexOf('1 kg') > -1 || nClean.indexOf('1000g') > -1 || nClean.indexOf('1000 g') > -1)) {
                    score += 50;
                }
                if (config.unidad === 'g' && (nClean.indexOf(cantStr + 'g') > -1 || nClean.indexOf(cantDot + 'g') > -1 || nClean.indexOf(cantDot + ' g') > -1)) {
                    score += 50;
                }
            }

            // Término de categoría explícito
            if (config.categoria && nClean.indexOf(cleanText(config.categoria)) > -1) {
                score += 30;
            }

            if (score > bestScore) {
                bestScore = score;
                bestCandidate = {
                    name: nameVal,
                    price: priceVal,
                    url: urlVal,
                    stock: unavail ? 'SIN STOCK' : 'DISPONIBLE'
                };
            }
        }

        return bestCandidate;
    }, queryConfig);

    return dData ? { ...dData, terminoBuscado: textoATipear } : { name: 'No encontrado', price: 'N/D', url: page.url(), stock: 'NO ENCONTRADO', terminoBuscado: textoATipear };
}

// ==============================================================================
// FUNCIÓN PRINCIPAL DE EJECUCIÓN RPA (ORQUESTADOR)
// ==============================================================================
async function runRPA({
    modo = 'compra_mes',
    items = [],
    demoMode = CONFIG.DEMO_MODE,
    typingDelay = CONFIG.TYPING_DELAY,
    mouseDuration = CONFIG.MOUSE_MOVE_DURATION,
    onStatus = null
}) {
    if (modo === 'individual') {
        const err = new Error('La Búsqueda Rápida Individual debe ejecutarse exclusivamente con TagUI mediante: tagui supermercados.tag <archivo_de_entrada>. rpa_runner.js está reservado exclusivamente para Compra del Mes.');
        if (onStatus) onStatus({ type: 'error', message: err.message });
        throw err;
    }

    isAborted = false;
    abortReason = null;
    asegurarCSV();
    const chromePath = getChromePath();
    const fechaHoy = getFechaHoy();

    const currentTypingDelay = typingDelay || CONFIG.TYPING_DELAY;
    const currentMouseDuration = mouseDuration || CONFIG.MOUSE_MOVE_DURATION;

    if (onStatus) {
        onStatus({
            type: 'init',
            message: 'Iniciando Google Chrome en modo 100% VISIBLE paso a paso...'
        });
    }

    let browser = null;
    const resultadosSesion = [];

    try {
        const puppeteer = await getPuppeteer();
        browser = await puppeteer.launch({
            executablePath: chromePath,
            headless: false, // 100% VISIBLE en el escritorio del usuario
            defaultViewport: null, // Ventana completa
            args: [
                '--start-maximized',
                '--window-position=0,0',
                '--window-size=1920,1080',
                '--no-first-run',
                '--no-default-browser-check',
                '--disable-blink-features=AutomationControlled',
                '--deny-permission-prompts',
                '--use-fake-ui-for-media-stream',
                '--lang=es-419,es'
            ]
        });

        try {
            const context = browser.defaultBrowserContext();
            await context.overridePermissions('https://www.carrefour.com.ar', []);
            await context.overridePermissions('https://www.coto.com.ar', []);
            await context.overridePermissions('https://diaonline.supermercadosdia.com.ar', []);
        } catch (ePerm) {}

        activeBrowser = browser;
        const chromePid = browser.process() ? browser.process().pid : 0;

        // Kill-switch: abortar inmediatamente si el usuario cierra la ventana de Chrome
        browser.on('disconnected', () => {
            console.log('[RPA] Navegador Chrome cerrado por el usuario.');
            abortCurrentRun();
        });

        const pages = await browser.pages();
        const page = pages[0] || await browser.newPage();

        page.on('close', () => {
            console.log('[RPA] Pestaña de Chrome cerrada.');
            abortCurrentRun();
        });

        // 1. Forzar maximizado interno vía CDP (Chrome DevTools Protocol)
        try {
            const session = await page.target().createCDPSession();
            const { windowId } = await session.send('Browser.getWindowForTarget');
            await session.send('Browser.setWindowBounds', {
                windowId,
                bounds: { windowState: 'maximized' }
            });
        } catch (eCDP) {}

        // 2. Traer al frente, des-minimizar y enfocar en el escritorio de Windows con mouse_helper
        try {
            const { spawnSync } = require('child_process');
            spawnSync(MOUSE_HELPER_PATH, ['focus', chromePid ? chromePid.toString() : '0'], { windowsHide: true });
        } catch (eFoc) {}

        try {
            await page.bringToFront();
        } catch (eBtf) {}

        checkAborted();

        if (onStatus) {
            onStatus({
                type: 'connected',
                message: 'Chrome abierto y en pantalla completa. El robot tomará el control visible en 2 segundos...'
            });
        }

        // Gracia de 2 segundos para que el usuario suelte el mouse cómodamente viendo la pantalla completa
        await sleep(2000);
        checkAborted();

        // 3. Activar la regla estricta de vigilancia de mouse una vez que Chrome ya está en pantalla
        startMouseWatchdog((reason) => {
            if (onStatus) {
                onStatus({
                    type: 'error',
                    state: 'aborted',
                    message: '🛑 Regla estricta activada: Se detectó movimiento manual del mouse. El proceso de automatización se ha detenido de inmediato.'
                });
            }
        });

        const totalItems = items.length;
        const totalPasos = totalItems * 3;
        let pasosCompletados = 0;

        // ==============================================================================
        // 1. CARREFOUR ARGENTINA (Buscar todos los productos consecutivamente)
        // ==============================================================================
        if (onStatus) {
            onStatus({ type: 'log', message: '========================================' });
            onStatus({ type: 'log', message: '[SUPERMERCADO 1] Iniciando Carrefour Argentina...' });
        }
        let ultimoTerminoCarrefour = null;
        for (let i = 0; i < totalItems; i++) {
            checkAborted();
            const itemObj = items[i];
            const productoOriginal = (typeof itemObj === 'string') ? itemObj : itemObj.producto;
            const cantidad = (itemObj.cantidad && parseFloat(itemObj.cantidad) > 0) ? parseFloat(itemObj.cantidad) : 1;
            const unidad = determinarUnidadDefault(productoOriginal, itemObj.unidad);
            const prodClean = productoOriginal.replace(/"/g, '').replace(/'/g, '').trim();

            pasosCompletados++;
            const pct = Math.round((pasosCompletados / totalPasos) * 100);
            if (onStatus) {
                onStatus({
                    type: 'progress',
                    percent: pct,
                    message: `[SUPERMERCADO 1 - Carrefour] [${i + 1}/${totalItems}] "${prodClean}" (x${cantidad} ${unidad})`
                });
            }

            const stepOptions = {
                onStatus,
                typingDelay: currentTypingDelay,
                mouseDuration: currentMouseDuration,
                itemObj,
                cantidad,
                unidad,
                itemIndex: i,
                ultimoTerminoBuscado: ultimoTerminoCarrefour
            };

            try {
                checkAborted();
                const cData = await searchCarrefour(page, prodClean, stepOptions);
                if (cData && cData.terminoBuscado) {
                    ultimoTerminoCarrefour = cData.terminoBuscado;
                }

                const carrefourItem = {
                    modo,
                    producto: prodClean,
                    nombre_encontrado: cData ? cData.name : 'No encontrado',
                    precio: cData ? cData.price : 'N/D',
                    supermercado: 'Carrefour',
                    url: cData ? cData.url : 'https://www.carrefour.com.ar',
                    fecha: fechaHoy,
                    stock_status: cData ? cData.stock : 'NO ENCONTRADO',
                    cantidad,
                    unidad
                };

                const rowC = `"${carrefourItem.modo}","${carrefourItem.producto}","${carrefourItem.nombre_encontrado.replace(/"/g, '""')}","${carrefourItem.precio}","${carrefourItem.supermercado}","${carrefourItem.url}","${carrefourItem.fecha}","${carrefourItem.stock_status}","${cantidad}","${unidad}"\n`;
                fs.appendFileSync(CSV_PATH, rowC, 'utf8');
                resultadosSesion.push(carrefourItem);

                if (onStatus) {
                    onStatus({ type: 'log', message: `[SUPERMERCADO 1] [${i + 1}/${totalItems}] Extraído: ${carrefourItem.nombre_encontrado} | ${carrefourItem.precio} | ${carrefourItem.stock_status}` });
                }
            } catch (errC) {
                console.error('Error en Carrefour:', errC);
                if (onStatus) onStatus({ type: 'log', message: `[SUPERMERCADO 1] Advertencia: ${errC.message}. Continuando...` });
            }
        }
        if (onStatus) {
            onStatus({ type: 'log', message: '[SUPERMERCADO 1] Finalizado.' });
        }

        // ==============================================================================
        // 2. COTO DIGITAL (Buscar todos los productos consecutivamente)
        // ==============================================================================
        if (onStatus) {
            onStatus({ type: 'log', message: '========================================' });
            onStatus({ type: 'log', message: '[SUPERMERCADO 2] Iniciando COTO Digital...' });
        }
        let ultimoTerminoCoto = null;
        for (let i = 0; i < totalItems; i++) {
            checkAborted();
            const itemObj = items[i];
            const productoOriginal = (typeof itemObj === 'string') ? itemObj : itemObj.producto;
            const cantidad = (itemObj.cantidad && parseFloat(itemObj.cantidad) > 0) ? parseFloat(itemObj.cantidad) : 1;
            const unidad = determinarUnidadDefault(productoOriginal, itemObj.unidad);
            const prodClean = productoOriginal.replace(/"/g, '').replace(/'/g, '').trim();

            pasosCompletados++;
            const pct = Math.round((pasosCompletados / totalPasos) * 100);
            if (onStatus) {
                onStatus({
                    type: 'progress',
                    percent: pct,
                    message: `[SUPERMERCADO 2 - COTO] [${i + 1}/${totalItems}] "${prodClean}" (x${cantidad} ${unidad})`
                });
            }

            const stepOptions = {
                onStatus,
                typingDelay: currentTypingDelay,
                mouseDuration: currentMouseDuration,
                itemObj,
                cantidad,
                unidad,
                itemIndex: i,
                ultimoTerminoBuscado: ultimoTerminoCoto
            };

            try {
                checkAborted();
                const ctData = await searchCoto(page, prodClean, stepOptions);
                if (ctData && ctData.terminoBuscado) {
                    ultimoTerminoCoto = ctData.terminoBuscado;
                }

                const cotoItem = {
                    modo,
                    producto: prodClean,
                    nombre_encontrado: ctData ? ctData.name : 'No encontrado',
                    precio: ctData ? ctData.price : 'N/D',
                    supermercado: 'COTO',
                    url: ctData ? ctData.url : 'https://www.coto.com.ar',
                    fecha: fechaHoy,
                    stock_status: ctData ? ctData.stock : 'NO ENCONTRADO',
                    cantidad,
                    unidad
                };

                const rowCt = `"${cotoItem.modo}","${cotoItem.producto}","${cotoItem.nombre_encontrado.replace(/"/g, '""')}","${cotoItem.precio}","${cotoItem.supermercado}","${cotoItem.url}","${cotoItem.fecha}","${cotoItem.stock_status}","${cantidad}","${unidad}"\n`;
                fs.appendFileSync(CSV_PATH, rowCt, 'utf8');
                resultadosSesion.push(cotoItem);

                if (onStatus) {
                    onStatus({ type: 'log', message: `[SUPERMERCADO 2] [${i + 1}/${totalItems}] Extraído: ${cotoItem.nombre_encontrado} | ${cotoItem.precio} | ${cotoItem.stock_status}` });
                }
            } catch (errCt) {
                console.error('Error en COTO:', errCt);
                if (onStatus) onStatus({ type: 'log', message: `[SUPERMERCADO 2] Advertencia: ${errCt.message}. Continuando...` });
            }
        }
        if (onStatus) {
            onStatus({ type: 'log', message: '[SUPERMERCADO 2] Finalizado.' });
        }

        // ==============================================================================
        // 3. DÍA % (Buscar todos los productos consecutivamente)
        // ==============================================================================
        if (onStatus) {
            onStatus({ type: 'log', message: '========================================' });
            onStatus({ type: 'log', message: '[SUPERMERCADO 3] Iniciando Supermercados Día %...' });
        }
        let ultimoTerminoDia = null;
        for (let i = 0; i < totalItems; i++) {
            checkAborted();
            const itemObj = items[i];
            const productoOriginal = (typeof itemObj === 'string') ? itemObj : itemObj.producto;
            const cantidad = (itemObj.cantidad && parseFloat(itemObj.cantidad) > 0) ? parseFloat(itemObj.cantidad) : 1;
            const unidad = determinarUnidadDefault(productoOriginal, itemObj.unidad);
            const prodClean = productoOriginal.replace(/"/g, '').replace(/'/g, '').trim();

            pasosCompletados++;
            const pct = Math.round((pasosCompletados / totalPasos) * 100);
            if (onStatus) {
                onStatus({
                    type: 'progress',
                    percent: pct,
                    message: `[SUPERMERCADO 3 - Día %] [${i + 1}/${totalItems}] "${prodClean}" (x${cantidad} ${unidad})`
                });
            }

            const stepOptions = {
                onStatus,
                typingDelay: currentTypingDelay,
                mouseDuration: currentMouseDuration,
                itemObj,
                cantidad,
                unidad,
                itemIndex: i,
                ultimoTerminoBuscado: ultimoTerminoDia
            };

            try {
                checkAborted();
                const dData = await searchDia(page, prodClean, stepOptions);
                if (dData && dData.terminoBuscado) {
                    ultimoTerminoDia = dData.terminoBuscado;
                }

                const diaItem = {
                    modo,
                    producto: prodClean,
                    nombre_encontrado: dData ? dData.name : 'No encontrado',
                    precio: dData ? dData.price : 'N/D',
                    supermercado: 'Día %',
                    url: dData ? dData.url : 'https://diaonline.supermercadosdia.com.ar',
                    fecha: fechaHoy,
                    stock_status: dData ? dData.stock : 'NO ENCONTRADO',
                    cantidad,
                    unidad
                };

                const rowD = `"${diaItem.modo}","${diaItem.producto}","${diaItem.nombre_encontrado.replace(/"/g, '""')}","${diaItem.precio}","${diaItem.supermercado}","${diaItem.url}","${diaItem.fecha}","${diaItem.stock_status}","${cantidad}","${unidad}"\n`;
                fs.appendFileSync(CSV_PATH, rowD, 'utf8');
                resultadosSesion.push(diaItem);

                if (onStatus) {
                    onStatus({ type: 'log', message: `[SUPERMERCADO 3] [${i + 1}/${totalItems}] Extraído: ${diaItem.nombre_encontrado} | ${diaItem.precio} | ${diaItem.stock_status}` });
                }
            } catch (errD) {
                console.error('Error en Día %:', errD);
                if (onStatus) onStatus({ type: 'log', message: `[SUPERMERCADO 3] Advertencia: ${errD.message}. Continuando...` });
            }
        }
        if (onStatus) {
            onStatus({ type: 'log', message: '[SUPERMERCADO 3] Finalizado.' });
        }

        // Finalización
        if (onStatus) {
            onStatus({ type: 'log', message: '----------------------------------------' });
            onStatus({ type: 'log', message: '[ RPA FINALIZADO ]' });
            onStatus({ type: 'log', message: '3 supermercados procesados con automatización 100% visible.' });
            onStatus({ type: 'finished', message: 'Automatización completada con éxito.' });
        }

        await sleep(1500);
        return resultadosSesion;
    } catch (error) {
        if (error.message === 'USER_MOUSE_INTERVENTION' || abortReason === 'USER_MOUSE_INTERVENTION' || fs.existsSync(FAILSAFE_FLAG_PATH)) {
            console.warn('[RPA] 🛑 PROCESO TERMINADO: Regla estricta activada por movimiento manual del mouse.');
            if (onStatus) {
                onStatus({
                    type: 'error',
                    state: 'aborted',
                    message: '🛑 Regla estricta activada: Se detectó movimiento manual del mouse. El proceso de automatización se ha detenido de inmediato.'
                });
            }
            throw new Error('USER_MOUSE_INTERVENTION');
        }
        if (error.message === 'RPA_ABORTED_BY_USER' || isAborted) {
            console.log('[RPA] Ejecución detenida por el usuario.');
            if (onStatus) onStatus({ type: 'error', state: 'aborted', message: 'RPA detenido inmediatamente por el usuario.' });
            throw new Error('RPA_ABORTED_BY_USER');
        }
        console.error('Error durante la ejecución del RPA:', error);
        if (onStatus) onStatus({ type: 'error', message: error.message });
        throw error;
    } finally {
        stopMouseWatchdog();
        activeBrowser = null;
        if (browser && !isAborted) {
            try {
                await sleep(2000);
                await browser.close();
            } catch (e) {}
        }
    }
}

module.exports = {
    runRPA,
    getChromePath,
    abortCurrentRun,
    searchCarrefour,
    searchCoto,
    searchDia,
    visibleNavigate,
    visibleClick,
    visibleType,
    visibleScroll,
    CONFIG
};
