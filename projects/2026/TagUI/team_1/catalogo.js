// ==============================================================================
// UTN FRCU - Tecnologías para la Automatización (Año 2026)
// catalogo.js - Motor de Catálogo Cerrado Centralizado y Validación Estricta
// ==============================================================================

const fs = require('fs');
const path = require('path');

const CATALOGO_PATH = path.join(__dirname, 'catalogo.json');

let catalogoCache = null;
let itemsPlanosCache = null;

function normalizarTexto(texto) {
    if (!texto || typeof texto !== 'string') return '';
    return texto
        .toLowerCase()
        .normalize('NFD')
        .replace(/[\u0300-\u036f]/g, '') // elimina tildes
        .replace(/(\d+)\s*%/g, '$1%')    // normaliza "3 %" a "3%"
        .replace(/[\.,;:!¡?¿\(\)\[\]"'\-_/]/g, ' ')
        .replace(/\s+/g, ' ')
        .trim();
}

function cargarCatalogo() {
    if (catalogoCache && itemsPlanosCache) {
        return { catalogo: catalogoCache, items: itemsPlanosCache };
    }

    if (!fs.existsSync(CATALOGO_PATH)) {
        throw new Error('No se encontró el archivo catalogo.json en ' + CATALOGO_PATH);
    }

    const raw = fs.readFileSync(CATALOGO_PATH, 'utf8');
    catalogoCache = JSON.parse(raw);

    const items = [];
    for (const cat of Object.keys(catalogoCache)) {
        const prods = catalogoCache[cat];
        for (const item of prods) {
            const nombresSupers = Array.isArray(item.nombres_supermercados) ? item.nombres_supermercados : [];
            items.push(Object.assign({}, item, {
                categoria: cat,
                nombres_supermercados: nombresSupers,
                _normMarca: normalizarTexto(item.marca),
                _normProducto: normalizarTexto(item.producto),
                _normVariante: normalizarTexto(item.variante || ''),
                _normCompleto: normalizarTexto(item.nombre_completo || ''),
                _normTermino: normalizarTexto(item.termino_busqueda || ''),
                _normId: normalizarTexto(item.id || ''),
                _normCategoria: normalizarTexto(cat || ''),
                _normNombresSupermercados: nombresSupers.map(n => normalizarTexto(n)),
                _searchBlob: normalizarTexto([
                    item.nombre_completo,
                    item.producto,
                    item.marca,
                    item.variante,
                    cat,
                    item.termino_busqueda,
                    item.id,
                    nombresSupers.join(' ')
                ].filter(Boolean).join(' '))
            }));
        }
    }
    itemsPlanosCache = items;
    return { catalogo: catalogoCache, items: itemsPlanosCache };
}

// Normalización matemática dimensional exacta de volumen y peso
function normalizarPresentacion(cantidad, unidad) {
    if (cantidad === undefined || cantidad === null) return null;
    const num = typeof cantidad === 'number' ? cantidad : parseFloat(String(cantidad).replace(',', '.'));
    if (isNaN(num) || num <= 0) return null;

    const uNorm = normalizarTexto(unidad || '');
    if (uNorm.startsWith('l') || uNorm.includes('litro') || uNorm === 'lt' || uNorm === 'lts') {
        return { valorBase: num, tipo: 'litros', unidadBase: 'L' };
    }
    if (uNorm.startsWith('m') || uNorm === 'cc' || uNorm.includes('mili')) {
        return { valorBase: num / 1000, tipo: 'litros', unidadBase: 'L' };
    }
    if (uNorm.startsWith('k') || uNorm.includes('kilo') || uNorm === 'kg' || uNorm === 'kgs') {
        return { valorBase: num, tipo: 'kilos', unidadBase: 'kg' };
    }
    if (uNorm.startsWith('g') || uNorm.includes('gram')) {
        return { valorBase: num / 1000, tipo: 'kilos', unidadBase: 'kg' };
    }
    if (uNorm.includes('un') || uNorm.includes('rollo') || uNorm.includes('u')) {
        return { valorBase: num, tipo: 'unidades', unidadBase: 'un' };
    }

    return { valorBase: num, tipo: 'generico', unidadBase: uNorm };
}

// Compara dos presentaciones exigiendo igualdad dimensional exacta (tolerancia cero a diferencias de tamaño)
function esPresentacionEquivalente(cantA, unidA, cantB, unidB) {
    const pA = normalizarPresentacion(cantA, unidA);
    const pB = normalizarPresentacion(cantB, unidB);
    if (!pA || !pB) return false;
    if (pA.tipo !== pB.tipo) return false;
    return Math.abs(pA.valorBase - pB.valorBase) < 0.001;
}

// Parsea un string que contiene texto y posible presentación (ej: "Coca Cola 2.25L", "Arroz Gallo 1kg", "Criollitas 100 g. x 3 uni", "3x 100gramos")
function parsearStringProducto(str) {
    if (!str || typeof str !== 'string') return { texto: '', cantidad: null, unidad: '' };
    const raw = str.trim();

    // 1. Multipack previo de peso: "3x 100gramos", "3 x 100g", "pack 3 x 100g", "pack x 3 de 100 g"
    const mMultiPesoPrev = raw.match(/(?:pack\s*(?:x\s*)?|x\s*)?(\d+)\s*(?:x|\*|de)\s*(\d+(?:[.,]\d+)?)\s*(kilos?|kilogramos?|kgs?|kg|k|gramos?|grs?|gr|g)\b/i);
    if (mMultiPesoPrev) {
        const count = parseInt(mMultiPesoPrev[1], 10);
        const uVal = parseFloat(mMultiPesoPrev[2].replace(',', '.'));
        const isG = mMultiPesoPrev[3].toLowerCase().startsWith('g');
        const total = (isG ? uVal : uVal * 1000) * count;
        const texto = raw.replace(mMultiPesoPrev[0], '').replace(/\s+/g, ' ').trim();
        return { texto, cantidad: isG ? total : total / 1000, unidad: isG ? 'g' : 'kg' };
    }

    // 2. Multipack posterior de peso: "100 g. x 3 uni", "100g x 3", "100 grs x 3", "100 g x 3 u"
    const mMultiPesoPost = raw.match(/(\d+(?:[.,]\d+)?)\s*(kilos?|kilogramos?|kgs?|kg|k|gramos?|grs?|gr|g)\b(?:\s*\.?)?\s*(?:x|\*)\s*(\d+)\s*(?:unidades?|unids?|unid|uni|un|u|paquetes?|paqs?|sobres?)?\b/i);
    if (mMultiPesoPost) {
        const uValP = parseFloat(mMultiPesoPost[1].replace(',', '.'));
        const isGP = mMultiPesoPost[2].toLowerCase().startsWith('g');
        const countP = parseInt(mMultiPesoPost[3], 10);
        const totalP = (isGP ? uValP : uValP * 1000) * countP;
        const texto = raw.replace(mMultiPesoPost[0], '').replace(/\s+/g, ' ').trim();
        return { texto, cantidad: isGP ? totalP : totalP / 1000, unidad: isGP ? 'g' : 'kg' };
    }

    // 3. Multipack previo de volumen: "6 x 500 ml", "pack x 2 de 1.5 l"
    const mMultiVolPrev = raw.match(/(?:pack\s*(?:x\s*)?|x\s*)?(\d+)\s*(?:x|\*|de)\s*(\d+(?:[.,]\d+)?)\s*(litros?|lts?|lt|l|mililitros?|mls?|ml|cc)\b/i);
    if (mMultiVolPrev) {
        const countV = parseInt(mMultiVolPrev[1], 10);
        const uValV = parseFloat(mMultiVolPrev[2].replace(',', '.'));
        const isMl = mMultiVolPrev[3].toLowerCase().startsWith('m') || mMultiVolPrev[3].toLowerCase() === 'cc';
        const totalV = (isMl ? uValV : uValV * 1000) * countV;
        const texto = raw.replace(mMultiVolPrev[0], '').replace(/\s+/g, ' ').trim();
        return { texto, cantidad: isMl ? totalV : totalV / 1000, unidad: isMl ? 'ml' : 'L' };
    }

    // 4. Multipack posterior de volumen: "500 ml x 6 uni", "1.5 l x 2"
    const mMultiVolPost = raw.match(/(\d+(?:[.,]\d+)?)\s*(litros?|lts?|lt|l|mililitros?|mls?|ml|cc)\b(?:\s*\.?)?\s*(?:x|\*)\s*(\d+)\s*(?:unidades?|unids?|unid|uni|un|u|botellas?|latas?|packs?)?\b/i);
    if (mMultiVolPost) {
        const uValVP = parseFloat(mMultiVolPost[1].replace(',', '.'));
        const isMlP = mMultiVolPost[2].toLowerCase().startsWith('m') || mMultiVolPost[2].toLowerCase() === 'cc';
        const countVP = parseInt(mMultiVolPost[3], 10);
        const totalVP = (isMlP ? uValVP : uValVP * 1000) * countVP;
        const texto = raw.replace(mMultiVolPost[0], '').replace(/\s+/g, ' ').trim();
        return { texto, cantidad: isMlP ? totalVP : totalVP / 1000, unidad: isMlP ? 'ml' : 'L' };
    }

    // Detectar volumen simple
    const mVol = raw.match(/(\d+(?:[.,]\d+)?)\s*(litros?|lts?|lt|l|mililitros?|mls?|ml|cc)\b/i);
    if (mVol) {
        const c = parseFloat(mVol[1].replace(',', '.'));
        const u = mVol[2].toLowerCase().startsWith('m') || mVol[2].toLowerCase() === 'cc' ? 'ml' : 'L';
        const texto = raw.replace(mVol[0], '').trim();
        return { texto, cantidad: c, unidad: u };
    }

    // Detectar peso simple
    const mPeso = raw.match(/(\d+(?:[.,]\d+)?)\s*(kilos?|kilogramos?|kgs?|kg|k|gramos?|grs?|gr|g)\b/i);
    if (mPeso) {
        const c = parseFloat(mPeso[1].replace(',', '.'));
        const u = mPeso[2].toLowerCase().startsWith('g') ? 'g' : 'kg';
        const texto = raw.replace(mPeso[0], '').trim();
        return { texto, cantidad: c, unidad: u };
    }

    // Detectar unidades
    const mUn = raw.match(/(?:pack\s*x?\s*|x\s*)?(\d+)\s*(?:unidades?|unids?|unid|uni|uds?|ud|un|rollos?|u)\b/i);
    if (mUn) {
        const c = parseInt(mUn[1], 10);
        const texto = raw.replace(mUn[0], '').trim();
        return { texto, cantidad: c, unidad: 'un' };
    }

    return { texto: raw, cantidad: null, unidad: '' };
}

// Extrae todas las subcadenas relevantes de un texto (palabras individuales, n-gramas de frases y sub-raíces)
function extraerSubcadenas(texto, minLen = 2) {
    if (!texto || typeof texto !== 'string') return [];
    const norm = normalizarTexto(texto);
    if (!norm) return [];

    const subcadenas = new Set();
    const tokens = norm.split(/\s+/).filter(t => t.length >= minLen);

    // 1. Tokens individuales (palabras)
    for (const t of tokens) {
        subcadenas.add(t);
        // Prefijos y sub-raíces de palabras largas (longitud >= 4)
        if (t.length >= 4) {
            for (let l = 3; l < t.length; l++) {
                subcadenas.add(t.substring(0, l));
            }
        }
    }

    // 2. N-gramas continuos de palabras (secuencias consecutivas)
    for (let l = 2; l <= tokens.length; l++) {
        for (let i = 0; i <= tokens.length - l; i++) {
            const ngram = tokens.slice(i, i + l).join(' ');
            if (ngram.length >= minLen) {
                subcadenas.add(ngram);
            }
        }
    }

    // 3. Cadena completa normalizada
    if (norm.length >= minLen) {
        subcadenas.add(norm);
    }

    return Array.from(subcadenas);
}

/**
 * Busca productos en el catálogo mediante coincidencia por subcadenas,
 * obteniendo la mayor cantidad de coincidencias posibles ordenadas por relevancia y afinidad.
 * 
 * @param {string|object} queryOAtributos Texto de búsqueda u objeto con atributos del producto
 * @param {object} opciones { minLongitudSubcadena: 2, limite: 0 (todos), soloValidos: false }
 * @returns {Array<object>} Lista de productos coincidentes con detalle de subcadenas y score
 */
function buscarPorSubcadenas(queryOAtributos, opciones = {}) {
    const { items } = cargarCatalogo();
    if (!queryOAtributos) return [];

    const minLen = opciones.minLongitudSubcadena || 2;
    const limite = opciones.limite || 0;

    let targetTexto = '';
    let targetCant = null;
    let targetUnid = '';
    let targetMarca = '';
    let targetVariante = '';

    if (typeof queryOAtributos === 'string') {
        const parsed = parsearStringProducto(queryOAtributos);
        targetTexto = normalizarTexto(parsed.texto || queryOAtributos);
        targetCant = parsed.cantidad;
        targetUnid = parsed.unidad;
    } else if (typeof queryOAtributos === 'object') {
        const strBase = (queryOAtributos.producto || queryOAtributos.marca || '') + ' ' + (queryOAtributos.variante || '') + ' ' + (queryOAtributos.nombre || '');
        const parsed = parsearStringProducto(strBase);
        targetTexto = normalizarTexto(parsed.texto || strBase);
        targetCant = queryOAtributos.cantidad !== undefined ? queryOAtributos.cantidad : parsed.cantidad;
        targetUnid = queryOAtributos.unidad || parsed.unidad;
        targetMarca = normalizarTexto(queryOAtributos.marca || '');
        targetVariante = normalizarTexto(queryOAtributos.variante || '');
    }

    if (!targetTexto && targetCant === null) return [];

    const subcadenasQuery = extraerSubcadenas(targetTexto, minLen);
    const tokensQuery = targetTexto.split(/\s+/).filter(t => t.length >= minLen);

    const resultados = [];

    for (const item of items) {
        const searchBlob = item._searchBlob || normalizarTexto([
            item.nombre_completo, item.producto, item.marca, item.variante, item.categoria, item.termino_busqueda, item.id
        ].filter(Boolean).join(' '));

        const normCompleto = item._normCompleto || normalizarTexto(item.nombre_completo);
        const normProducto = item._normProducto || normalizarTexto(item.producto);
        const normMarca = item._normMarca || normalizarTexto(item.marca);
        const normVariante = item._normVariante || normalizarTexto(item.variante || '');
        const normCategoria = normalizarTexto(item.categoria || '');

        const subcadenasCoincidentes = new Set();
        let score = 0;
        let tokensCoincidentes = 0;

        // 1. Coincidencia exacta de nombre o ID
        if (normCompleto === targetTexto || item.id === targetTexto) {
            subcadenasCoincidentes.add(targetTexto);
            score += 150;
        }

        // 2. Query completa dentro del producto o viceversa
        if (targetTexto && searchBlob.includes(targetTexto)) {
            subcadenasCoincidentes.add(targetTexto);
            score += 60;
        }
        if (normCompleto && targetTexto.includes(normCompleto)) {
            subcadenasCoincidentes.add(normCompleto);
            score += 50;
        }

        // 3. Chequeo de subcadenas extraídas de la consulta
        for (const sub of subcadenasQuery) {
            if (sub.length < minLen) continue;
            let coincide = false;
            if (searchBlob.includes(sub)) {
                coincide = true;
            } else if (normMarca.includes(sub) || normProducto.includes(sub) || normVariante.includes(sub) || normCategoria.includes(sub)) {
                coincide = true;
            }

            if (coincide) {
                subcadenasCoincidentes.add(sub);
                score += (sub.includes(' ') ? 15 : 8) + Math.min(sub.length, 10);
            }
        }

        // 4. Coincidencia de tokens bidireccionales
        const tokensItem = searchBlob.split(/\s+/).filter(t => t.length >= minLen);
        for (const tq of tokensQuery) {
            let matchedToken = false;
            for (const ti of tokensItem) {
                if (ti === tq) {
                    matchedToken = true;
                    subcadenasCoincidentes.add(tq);
                    score += 12;
                    break;
                } else if ((tq.length >= 2 && ti.includes(tq)) || (ti.length >= 2 && tq.includes(ti))) {
                    matchedToken = true;
                    subcadenasCoincidentes.add(tq.length <= ti.length ? tq : ti);
                    score += 6;
                    break;
                }
            }
            if (matchedToken) tokensCoincidentes++;
        }

        // 5. Coincidencias de campos semánticos
        const coincideMarca = normMarca && (
            (searchBlob.includes(normMarca) && targetTexto.includes(normMarca)) ||
            (targetMarca && normMarca.includes(targetMarca)) ||
            (targetTexto.includes(normMarca))
        );
        if (coincideMarca) {
            score += 35;
            subcadenasCoincidentes.add(normMarca);
        }

        const coincideProducto = normProducto && (
            targetTexto.includes(normProducto) ||
            normProducto.split(/\s+/).some(p => p.length >= 3 && targetTexto.includes(p))
        );
        if (coincideProducto) {
            score += 25;
            subcadenasCoincidentes.add(normProducto);
        }

        const coincideVariante = normVariante && (
            targetTexto.includes(normVariante) ||
            (targetVariante && normVariante.includes(targetVariante))
        );
        if (coincideVariante) {
            score += 20;
            subcadenasCoincidentes.add(normVariante);
        }

        const coincideCategoria = normCategoria && targetTexto.includes(normCategoria);
        if (coincideCategoria) {
            score += 15;
            subcadenasCoincidentes.add(normCategoria);
        }

        // 5.5. Coincidencias con nombres del diccionario de supermercados
        let coincideNombreSupermercado = false;
        let nombreSuperCoincidente = null;
        if (item._normNombresSupermercados && item._normNombresSupermercados.length > 0) {
            for (let sIdx = 0; sIdx < item._normNombresSupermercados.length; sIdx++) {
                const nSup = item._normNombresSupermercados[sIdx];
                if (nSup === targetTexto || (targetTexto.length >= 6 && nSup.includes(targetTexto)) || (nSup.length >= 6 && targetTexto.includes(nSup))) {
                    coincideNombreSupermercado = true;
                    nombreSuperCoincidente = item.nombres_supermercados[sIdx];
                    subcadenasCoincidentes.add(nombreSuperCoincidente);
                    score += 65;
                    break;
                }
            }
        }

        // 6. Evaluación de presentación dimensional
        let coincidePresentacion = false;
        if (targetCant !== null && targetUnid) {
            coincidePresentacion = esPresentacionEquivalente(item.cantidad, item.unidad, targetCant, targetUnid);
            if (coincidePresentacion) {
                score += 40;
                subcadenasCoincidentes.add(`${item.cantidad} ${item.unidad}`);
            } else {
                score = Math.max(1, score - 20);
            }
        }

const STOP_WORDS_CATALOGO = new Set([
    'de', 'del', 'en', 'para', 'con', 'sin', 'el', 'la', 'los', 'las', 'un', 'una',
    'unos', 'unas', 'tipo', 'x', 'al', 'por', 'y', 'o'
]);

        const cantidadCoincidencias = subcadenasCoincidentes.size;

        // INCLUSIÓN: Obtener la mayor cantidad de coincidencias posibles
        if (cantidadCoincidencias > 0) {
            // Si la consulta contiene palabras que no son stop-words, debe coincidir al menos una subcadena relevante
            const tieneTokensRelevantes = tokensQuery.some(t => !STOP_WORDS_CATALOGO.has(t));
            if (tieneTokensRelevantes) {
                const tieneSubcadenaRelevante = Array.from(subcadenasCoincidentes).some(s => !STOP_WORDS_CATALOGO.has(s));
                if (!tieneSubcadenaRelevante) continue;
            }

            const porcentajeTokens = tokensQuery.length > 0 ? (tokensCoincidentes / tokensQuery.length) : 0;
            resultados.push({
                item: item,
                score: score,
                cantidadCoincidencias: cantidadCoincidencias,
                subcadenasCoincidentes: Array.from(subcadenasCoincidentes),
                tokensCoincidentes: tokensCoincidentes,
                porcentajeTokens: Math.round(porcentajeTokens * 100) / 100,
                coincideMarca: Boolean(coincideMarca),
                coincideProducto: Boolean(coincideProducto),
                coincideVariante: Boolean(coincideVariante),
                coincideCategoria: Boolean(coincideCategoria),
                coincidePresentacion: Boolean(coincidePresentacion),
                coincideNombreSupermercado: Boolean(coincideNombreSupermercado),
                nombreSuperCoincidente: nombreSuperCoincidente
            });
        }
    }

    resultados.sort((a, b) => {
        if (b.score !== a.score) return b.score - a.score;
        if (b.cantidadCoincidencias !== a.cantidadCoincidencias) return b.cantidadCoincidencias - a.cantidadCoincidencias;
        return b.porcentajeTokens - a.porcentajeTokens;
    });

    if (limite > 0 && resultados.length > limite) {
        return resultados.slice(0, limite);
    }

    return resultados;
}

// Obtiene el diccionario completo de nombres de supermercados agrupados por producto
function obtenerDiccionarioSupermercados() {
    const { items } = cargarCatalogo();
    const diccionario = {};
    for (const item of items) {
        diccionario[item.id] = {
            id: item.id,
            producto: item.producto,
            marca: item.marca,
            variante: item.variante,
            cantidad: item.cantidad,
            unidad: item.unidad,
            nombre_completo: item.nombre_completo,
            nombres_supermercados: item.nombres_supermercados || []
        };
    }
    return diccionario;
}

// Busca un producto a partir de cualquiera de sus nombres conocidos en plataformas de supermercados
function buscarPorDiccionarioSupermercado(texto) {
    if (!texto || typeof texto !== 'string') return null;
    const { items } = cargarCatalogo();
    const tNorm = normalizarTexto(texto);
    if (!tNorm) return null;

    // 1. Coincidencia exacta con nombre de supermercado
    for (const item of items) {
        const nombresNorm = item._normNombresSupermercados || [];
        for (let i = 0; i < nombresNorm.length; i++) {
            if (nombresNorm[i] === tNorm) {
                return {
                    match: true,
                    tipo: 'EXACTO',
                    item: item,
                    nombreCoincidente: item.nombres_supermercados[i],
                    score: 100
                };
            }
        }
    }

    // 2. Coincidencia por contención bidireccional (si la cadena contiene o está contenida)
    let mejorMatch = null;
    let maxLen = 0;

    for (const item of items) {
        const nombresNorm = item._normNombresSupermercados || [];
        for (let i = 0; i < nombresNorm.length; i++) {
            const nNorm = nombresNorm[i];
            const tokensT = tNorm.split(/\s+/).filter(Boolean);
            const coincideMarcaEnT = item._normMarca && (tNorm.includes(item._normMarca) || item._normMarca.includes(tNorm));
            const coincideProdEnT = item._normProducto && (tNorm.includes(item._normProducto) || item._normProducto.includes(tNorm));
            const contencionValida = tNorm.includes(nNorm) || (tokensT.length >= 2 && nNorm.includes(tNorm) && (coincideMarcaEnT || coincideProdEnT));

            if (nNorm.length >= 6 && contencionValida) {
                if (nNorm.length > maxLen) {
                    maxLen = nNorm.length;
                    mejorMatch = {
                        match: true,
                        tipo: 'CONTENCION',
                        item: item,
                        nombreCoincidente: item.nombres_supermercados[i],
                        score: 85
                    };
                }
            }
        }
    }

    return mejorMatch;
}

// Permite agregar un nuevo alias de supermercado al producto
function agregarNombreSupermercado(idOProducto, nuevoNombre, guardarEnArchivo = false) {
    if (!idOProducto || !nuevoNombre) return false;
    const { catalogo: cat, items } = cargarCatalogo();
    const target = normalizarTexto(idOProducto);
    const item = items.find(it => it.id === idOProducto || normalizarTexto(it.nombre_completo) === target || normalizarTexto(it.producto) === target);
    if (!item) return false;

    if (!item.nombres_supermercados) item.nombres_supermercados = [];
    const normNuevo = normalizarTexto(nuevoNombre);
    const existe = item.nombres_supermercados.some(n => normalizarTexto(n) === normNuevo);
    if (!existe) {
        item.nombres_supermercados.push(nuevoNombre.trim());
        if (!item._normNombresSupermercados) item._normNombresSupermercados = [];
        item._normNombresSupermercados.push(normNuevo);
        item._searchBlob = normalizarTexto(item._searchBlob + ' ' + normNuevo);

        if (guardarEnArchivo) {
            try {
                fs.writeFileSync(CATALOGO_PATH, JSON.stringify(cat, null, 2), 'utf8');
            } catch (e) {
                console.error('Error guardando en catalogo.json:', e);
            }
        }
        return true;
    }
    return false;
}

// Busca un producto estrictamente en el catálogo cerrado
function buscarEnCatalogo(queryOAtributos) {
    const { items } = cargarCatalogo();
    if (!queryOAtributos) return null;

    let targetTexto = '';
    let targetCant = null;
    let targetUnid = '';

    if (typeof queryOAtributos === 'string') {
        const parsed = parsearStringProducto(queryOAtributos);
        targetTexto = normalizarTexto(parsed.texto);
        targetCant = parsed.cantidad;
        targetUnid = parsed.unidad;
    } else if (typeof queryOAtributos === 'object') {
        if (queryOAtributos.id) {
            const byId = items.find(it => it.id === queryOAtributos.id);
            if (byId) return byId;
        }
        const strBase = (queryOAtributos.nombre_completo || queryOAtributos.producto || queryOAtributos.marca || '') + ' ' + (queryOAtributos.variante || '');
        const parsed = parsearStringProducto(strBase);
        targetTexto = normalizarTexto(parsed.texto || strBase);
        targetCant = queryOAtributos.cantidad !== undefined ? queryOAtributos.cantidad : parsed.cantidad;
        targetUnid = queryOAtributos.unidad || parsed.unidad;
    }

    if (!targetTexto) return null;

    // 0. Coincidencia directa contra diccionario de nombres de supermercado
    const matchDict = buscarPorDiccionarioSupermercado(targetTexto);
    if (matchDict && matchDict.item) {
        if (targetCant !== null && targetUnid) {
            if (esPresentacionEquivalente(matchDict.item.cantidad, matchDict.item.unidad, targetCant, targetUnid)) {
                return matchDict.item;
            }
        } else {
            return matchDict.item;
        }
    }

    // 1. Coincidencia exacta de nombre completo o ID
    for (const item of items) {
        if (item.id === targetTexto || item._normCompleto === targetTexto) {
            if (targetCant !== null && targetUnid) {
                if (!esPresentacionEquivalente(item.cantidad, item.unidad, targetCant, targetUnid)) continue;
            }
            return item;
        }
    }

    // 2. Coincidencia estricta por marca y/o producto con presentación
    const VARIANTES_CONOCIDAS = ['pomelo', 'naranja', 'limon', 'cola', 'manzana', 'frambuesa', 'vainilla', 'chocolate', 'original', 'zero', 'light', 'diet', 'largo fino', 'doble carolina', 'parboil', 'tallarin', 'tallarines', 'tirabuzon', 'entera', 'descremada', 'girasol', 'oliva', 'maiz', 'tradicional', 'con palo', 'despalada', 'sin gas', 'con gas', 'restauracion', 'limpieza'];

    for (const item of items) {
        const palabrasTarget = targetTexto.split(' ');
        const tieneMarca = palabrasTarget.includes(item._normMarca) || targetTexto.includes(item._normMarca) || targetTexto.includes(item._normProducto) || ((item._normMarca === 'lucchetti' || item._normMarca === 'luchetti') && (targetTexto.includes('lucchetti') || targetTexto.includes('luchetti')));
        if (!tieneMarca) continue;

        // Si targetTexto menciona alguna variante conocida, debe estar presente en item._normVariante
        let contradiceVariante = false;
        if (item._normVariante) {
            for (const v of VARIANTES_CONOCIDAS) {
                if (item._normMarca.includes(v)) continue;
                if (targetTexto.includes(v) && !item._normVariante.includes(v)) {
                    if ((v === 'tallarin' || v === 'tallarines') && (item._normVariante.includes('tallarin') || item._normVariante.includes('tallarines'))) {
                        continue;
                    }
                    contradiceVariante = true;
                    break;
                }
            }
        }
        if (contradiceVariante) continue;

        // Si se especificó variante en el objeto de consulta, verificarla
        if (typeof queryOAtributos === 'object' && queryOAtributos.variante) {
            const vBuscada = normalizarTexto(queryOAtributos.variante);
            const esEquivTallarin = (vBuscada.includes('tallarin') || vBuscada.includes('tallarines')) && (item._normVariante.includes('tallarin') || item._normVariante.includes('tallarines'));
            if (!esEquivTallarin && item._normVariante && !item._normVariante.includes(vBuscada) && !vBuscada.includes(item._normVariante)) {
                continue;
            }
        }

        // Si se especificó presentación, debe ser estrictamente equivalente
        if (targetCant !== null && targetUnid) {
            if (esPresentacionEquivalente(item.cantidad, item.unidad, targetCant, targetUnid)) {
                return item;
            }
        } else {
            return item;
        }
    }

    return null;
}

// Valida si una entrada es válida contra el catálogo cerrado utilizando búsqueda por subcadenas
function validarEntrada(entrada) {
    const item = buscarEnCatalogo(entrada);
    const coincidencias = buscarPorSubcadenas(entrada);

    if (item) {
        return {
            valido: true,
            item: item,
            motivo: 'Producto perteneciente al catálogo cerrado.',
            coincidencias: coincidencias,
            totalCoincidencias: coincidencias.length
        };
    }

    const { catalogo, items } = cargarCatalogo();
    const categoriasDisponibles = Object.keys(catalogo);
    const opcionesPermitidas = items.map(it => it.nombre_completo);

    return {
        valido: false,
        item: null,
        motivo: 'El producto ingresado no pertenece al catálogo cerrado.',
        coincidencias: coincidencias,
        totalCoincidencias: coincidencias.length,
        categorias: categoriasDisponibles,
        opciones: coincidencias.length > 0 ? coincidencias.map(c => c.item.nombre_completo) : opcionesPermitidas
    };
}

// Valida un archivo CSV (ej: input.csv) contra el catálogo
function validarArchivoCSV(filePath) {
    const csvPath = filePath || path.join(__dirname, 'input.csv');
    if (!fs.existsSync(csvPath)) {
        return { valido: false, error: 'Archivo no encontrado: ' + csvPath, filasValidas: [], filasInvalidas: [] };
    }

    const raw = fs.readFileSync(csvPath, 'utf8');
    const lines = raw.split(/\r?\n/).map(l => l.trim()).filter(l => l.length > 0);
    if (lines.length <= 1) {
        return { valido: false, error: 'El archivo CSV está vacío.', filasValidas: [], filasInvalidas: [] };
    }

    const filasValidas = [];
    const filasInvalidas = [];

    for (let i = 1; i < lines.length; i++) {
        const line = lines[i];
        const parts = line.split(',').map(p => p.trim());
        const prod = parts[0] || '';
        const cant = parts[1] !== undefined ? parts[1] : 1;
        const unid = parts[2] || '';
        const unidades = parts[3] !== undefined ? parseInt(parts[3], 10) : 1;

        const val = validarEntrada({ producto: prod, cantidad: cant, unidad: unid });
        if (val.valido) {
            filasValidas.push({
                fila: i + 1,
                original: line,
                itemCatalogo: val.item,
                unidades: unidades || 1
            });
        } else {
            filasInvalidas.push({
                fila: i + 1,
                original: line,
                producto: prod,
                cantidad: cant,
                unidad: unid,
                motivo: val.motivo
            });
        }
    }

    return {
        valido: filasInvalidas.length === 0,
        totalFilas: lines.length - 1,
        filasValidas,
        filasInvalidas
    };
}

// Lista todas las categorías disponibles
function listarCategorias() {
    const { catalogo } = cargarCatalogo();
    return Object.keys(catalogo);
}

// Lista los productos de una categoría específica
function listarProductos(categoria) {
    const { catalogo } = cargarCatalogo();
    if (!categoria) return [];
    const catNorm = normalizarTexto(categoria);
    return catalogo[catNorm] || [];
}

// Exportación modular y ejecución CLI
if (require.main === module) {
    const args = process.argv.slice(2);
    if (args.includes('--listar')) {
        const { catalogo } = cargarCatalogo();
        console.log('======================================================================');
        console.log('            📦 CATÁLOGO CERRADO DE PRODUCTOS DISPONIBLES             ');
        console.log('======================================================================\n');
        for (const cat of Object.keys(catalogo)) {
            console.log(`📂 Categoría: [${cat.toUpperCase()}]`);
            catalogo[cat].forEach(it => {
                console.log(`   • ${it.nombre_completo} (Marca: ${it.marca} | Variante: ${it.variante || 'N/A'})`);
            });
            console.log('');
        }
    } else if (args.includes('--validar-csv')) {
        const file = args[args.indexOf('--validar-csv') + 1] || 'input.csv';
        const res = validarArchivoCSV(file);
        if (res.valido) {
            console.log(`[OK] Todas las filas de ${file} pertenecen válidamente al catálogo cerrado (${res.filasValidas.length} productos).`);
            process.exit(0);
        } else {
            console.error(`[ERROR] Se detectaron productos en ${file} que NO pertenecen al catálogo cerrado:`);
            res.filasInvalidas.forEach(f => {
                console.error(`   - Fila ${f.fila}: "${f.original}" -> ${f.motivo}`);
            });
            process.exit(1);
        }
    } else if (args.includes('--validar')) {
        const prod = args[args.indexOf('--validar') + 1] || '';
        const res = validarEntrada(prod);
        if (res.valido) {
            console.log(`[OK] "${prod}" es válido en el catálogo: ${res.item.nombre_completo}`);
            process.exit(0);
        } else {
            console.error(`[ERROR] "${prod}" NO pertenece al catálogo cerrado.`);
            console.error('Opciones válidas permitidas:');
            res.opciones.slice(0, 10).forEach(op => console.error('   • ' + op));
            console.error('   ... (usa --listar para ver el catálogo completo)');
            process.exit(1);
        }
    } else if (args.includes('--subcadenas') || args.includes('--buscar')) {
        const queryIdx = args.includes('--subcadenas') ? args.indexOf('--subcadenas') : args.indexOf('--buscar');
        const query = args.slice(queryIdx + 1).join(' ').trim();
        const resultados = buscarPorSubcadenas(query);
        console.log('======================================================================');
        console.log('       🔍 BÚSQUEDA POR SUBCADENAS EN CATÁLOGO CERRADO (catalogo.js)');
        console.log(`       Consulta: "${query}"`);
        console.log(`       Total de coincidencias obtenidas: ${resultados.length}`);
        console.log('======================================================================\n');
        resultados.forEach((r, idx) => {
            console.log(`${idx + 1}. ${r.item.nombre_completo} [Score: ${r.score} | Coincidencias: ${r.cantidadCoincidencias}]`);
            console.log(`   • Subcadenas coincidentes: ${r.subcadenasCoincidentes.join(', ')}`);
        });
    } else if (args.includes('--diccionario')) {
        const queryIdx = args.indexOf('--diccionario');
        const query = args.slice(queryIdx + 1).join(' ').trim();
        if (query) {
            const match = buscarPorDiccionarioSupermercado(query);
            console.log('======================================================================');
            console.log('       📖 CONSULTA AL DICCIONARIO DE SUPERMERCADOS (catalogo.js)');
            console.log(`       Texto buscado: "${query}"`);
            console.log('======================================================================\n');
            if (match && match.item) {
                console.log(`[OK] Coincidencia encontrada (${match.tipo} - Score: ${match.score}):`);
                console.log(`   • Producto catálogo : ${match.item.nombre_completo} (ID: ${match.item.id})`);
                console.log(`   • Alias coincidente : "${match.nombreCoincidente}"`);
                console.log(`   • Categoría         : ${match.item.categoria}`);
                console.log(`   • Marca             : ${match.item.marca}`);
            } else {
                console.log(`[SIN COINCIDENCIA DIRECTA] No se encontró coincidencia en el diccionario para "${query}".`);
            }
        } else {
            const dicc = obtenerDiccionarioSupermercados();
            console.log('======================================================================');
            console.log('       📖 DICCIONARIO OFICIAL DE NOMBRES EN SUPERMERCADOS');
            console.log('======================================================================\n');
            for (const id in dicc) {
                const prod = dicc[id];
                console.log(`📦 [${prod.nombre_completo}] (ID: ${prod.id})`);
                if (prod.nombres_supermercados && prod.nombres_supermercados.length > 0) {
                    prod.nombres_supermercados.forEach(alias => console.log(`   • "${alias}"`));
                } else {
                    console.log('   (Sin nombres registrados)');
                }
                console.log('');
            }
        }
    } else if (args.includes('--menu-individual')) {
        const { items } = cargarCatalogo();
        console.log('==============================================================================');
        console.log('       🛒 BÚSQUEDA RÁPIDA: CATÁLOGO CERRADO OFICIAL (20 PRODUCTOS)');
        console.log('==============================================================================\n');
        const half = Math.ceil(items.length / 2);
        for (let i = 0; i < half; i++) {
            const it1 = items[i];
            const num1 = String(i + 1).padStart(2, ' ');
            const col1 = ` [${num1}] ${it1.nombre_completo}`.padEnd(38, ' ');

            let col2 = '';
            if (i + half < items.length) {
                const it2 = items[i + half];
                const num2 = String(i + half + 1).padStart(2, ' ');
                col2 = ` [${num2}] ${it2.nombre_completo}`;
            }
            console.log(col1 + col2);
        }
        console.log('\n==============================================================================');
    } else if (args.includes('--obtener-producto')) {
        const inputArg = args.slice(args.indexOf('--obtener-producto') + 1).join(' ').trim();
        const { items } = cargarCatalogo();
        const num = parseInt(inputArg, 10);
        if (!isNaN(num) && num >= 1 && num <= items.length && String(num) === inputArg) {
            console.log(items[num - 1].nombre_completo);
            process.exit(0);
        }
        const res = validarEntrada(inputArg);
        if (res.valido && res.item) {
            console.log(res.item.nombre_completo);
            process.exit(0);
        }
        process.exit(1);
    } else {
        console.log('Uso: node catalogo.js [--listar] | [--menu-individual] | [--obtener-producto <num|nombre>] | [--diccionario ["texto"]] | [--validar "producto"] | [--subcadenas "texto"] | [--validar-csv input.csv]');
    }
}

module.exports = {
    normalizarTexto,
    cargarCatalogo,
    normalizarPresentacion,
    esPresentacionEquivalente,
    parsearStringProducto,
    extraerSubcadenas,
    buscarPorSubcadenas,
    obtenerDiccionarioSupermercados,
    buscarPorDiccionarioSupermercado,
    agregarNombreSupermercado,
    buscarEnCatalogo,
    validarEntrada,
    validarArchivoCSV,
    listarCategorias,
    listarProductos
};
