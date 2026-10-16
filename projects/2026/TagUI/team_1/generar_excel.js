// ==============================================================================
// UTN FRCU - Tecnologías para la Automatización (Año 2026)
// generar_excel.js - Generador de Reporte Simplificado en Excel (.xlsx)
//
// 2 Hojas Claras y Directas:
// 1. 🛒 Canasta Mensual (Matriz comparativa, disponibilidad, ganador por ítem y síntesis del súper más barato descartando no encontrados)
// 2. 🔎 Consultas Individuales (Historial de búsquedas unitarias con comparativa y veredicto)
// ==============================================================================

const fs = require('fs');
const path = require('path');
const ExcelJS = require('exceljs');
const validador = require('./validador.js');
const catalogo = require('./catalogo.js');

const CSV_PATH = path.join(__dirname, 'resultados.csv');
const XLSX_PATH = path.join(__dirname, 'reporte_supermercados.xlsx');

// Paleta corporativa armónica
const COLOR_AZUL_OSCURO = '1F4E79';
const COLOR_AZUL_TITULO = '2F5597';
const COLOR_AZUL_CLARO = 'D9E1F2';
const COLOR_VERDE_PASTEL = 'E2EFDA';
const COLOR_VERDE_TEXTO = '276A3C';
const COLOR_ROJO_PASTEL = 'FCE4D6';
const COLOR_ROJO_TEXTO = 'C00000';
const COLOR_AMARILLO_PASTEL = 'FFF2CC';
const COLOR_AMARILLO_TEXTO = '9C6500';
const COLOR_GRIS_FONDO = 'F2F4F7';
const COLOR_BORDE = 'D9D9D9';

function aplicarBordes(ws, cIni, fIni, cFin, fFin) {
    var cols = [];
    for (var c = cIni.charCodeAt(0); c <= cFin.charCodeAt(0); c++) {
        cols.push(String.fromCharCode(c));
    }
    cols.forEach(function (col) {
        for (var r = fIni; r <= fFin; r++) {
            var cell = ws.getCell(col + r);
            cell.border = {
                top: { style: 'thin', color: { argb: COLOR_BORDE } },
                bottom: { style: 'thin', color: { argb: COLOR_BORDE } },
                left: { style: 'thin', color: { argb: COLOR_BORDE } },
                right: { style: 'thin', color: { argb: COLOR_BORDE } }
            };
        }
    });
}

async function main() {
    if (!fs.existsSync(CSV_PATH)) {
        console.log('[ERROR] No se encontró el archivo resultados.csv');
        return;
    }

    var items = validador.leerResultadosCSV(CSV_PATH);
    if (items.length === 0) {
        console.log('[INFO] El archivo resultados.csv no contiene registros procesables.');
        return;
    }

    // Validar cada elemento con el motor semántico
    items.forEach(function (it) {
        var v = validador.validarCoincidencia(it.producto, it);
        it.estado = v.estado;
        it.valido = v.valido;
        it.motivo = v.motivo;
        it.intencion = v.intencion;
    });

    var itemsMensual = items.filter(function (x) { return x.modo === 'compra_mes'; });
    var itemsIndividual = items.filter(function (x) { return x.modo === 'individual'; });

    // Si no hay diferenciación de modo, tratamos todos como compra mensual
    if (itemsMensual.length === 0 && itemsIndividual.length === 0) {
        itemsMensual = items;
    }

    var workbook = new ExcelJS.Workbook();
    workbook.creator = 'RPA Bot - UTN FRCU';
    workbook.created = new Date();

    // ==============================================================================
    // 1. ANÁLISIS DE LA CANASTA MENSUAL
    // ==============================================================================
    var productosMensualUnicos = [];
    var grupoMensual = {};

    itemsMensual.forEach(function (it) {
        var itemCat = catalogo.buscarEnCatalogo({
            producto: it.producto,
            cantidad: it.cantidad,
            unidad: it.unidad
        }) || catalogo.buscarEnCatalogo(it.producto);

        var key = itemCat ? itemCat.id : validador.normalizar(it.producto);
        var label = itemCat ? itemCat.nombre_completo : it.producto;

        if (!grupoMensual[key]) {
            grupoMensual[key] = { label: label, items: [] };
            productosMensualUnicos.push(key);
        }
        grupoMensual[key].items.push(it);
    });

    var supersList = ['Carrefour', 'COTO', 'Día %'];
    var totalesCanasta = { 'Carrefour': 0, 'COTO': 0, 'Día %': 0 };
    var conteoEncontrados = { 'Carrefour': 0, 'COTO': 0, 'Día %': 0 };
    var conteoGanados = { 'Carrefour': 0, 'COTO': 0, 'Día %': 0 };

    var filasCanasta = [];
    var costoOptimoCombinado = 0;

    productosMensualUnicos.forEach(function (prodKey) {
        var grupo = grupoMensual[prodKey];
        var itemsDelProd = grupo.items;
        var labelProd = grupo.label;
        var preciosPorSuper = {};
        var itemsPorSuper = {};
        var validosProd = [];

        supersList.forEach(function (s) {
            var found = itemsDelProd.filter(function (x) { return x.supermercado === s; }).pop();
            itemsPorSuper[s] = found || null;
            if (found && found.valido && found.precio !== null && found.precio > 0) {
                var precioItem = found.precio;
                preciosPorSuper[s] = precioItem;
                totalesCanasta[s] += precioItem;
                conteoEncontrados[s]++;
                validosProd.push({ superm: s, precio: precioItem, item: found });
            } else {
                preciosPorSuper[s] = null;
            }
        });

        // Ordenar opciones válidas de menor a mayor precio
        validosProd.sort(function (a, b) { return a.precio - b.precio; });

        var ganadorProd = validosProd.length > 0 ? validosProd[0] : null;
        var masCaroProd = validosProd.length > 1 ? validosProd[validosProd.length - 1] : null;
        var ahorroProd = (ganadorProd && masCaroProd) ? (masCaroProd.precio - ganadorProd.precio) : 0;

        if (ganadorProd) {
            costoOptimoCombinado += ganadorProd.precio;
            conteoGanados[ganadorProd.superm]++;
        }

        filasCanasta.push({
            productoKey: prodKey,
            label: labelProd,
            carrefour: itemsPorSuper['Carrefour'],
            coto: itemsPorSuper['COTO'],
            dia: itemsPorSuper['Día %'],
            cantidadTotalValidos: validosProd.length,
            ganador: ganadorProd,
            masCaro: masCaroProd,
            ahorro: ahorroProd
        });
    });

    // Determinar Supermercado Recomendado (en el que se gasta menos)
    // Descartando supermercados que no encontraron la canasta o tienen faltantes
    var maxEncontrados = 0;
    supersList.forEach(function (s) {
        if (conteoEncontrados[s] > maxEncontrados) maxEncontrados = conteoEncontrados[s];
    });

    var superRecomendado = 'N/D';
    var menorCostoCanasta = Infinity;
    var mayorCostoCanasta = 0;

    supersList.forEach(function (s) {
        if (conteoEncontrados[s] > 0 && conteoEncontrados[s] === maxEncontrados) {
            if (totalesCanasta[s] < menorCostoCanasta) {
                menorCostoCanasta = totalesCanasta[s];
                superRecomendado = s;
            }
            if (totalesCanasta[s] > mayorCostoCanasta) {
                mayorCostoCanasta = totalesCanasta[s];
            }
        }
    });

    var ahorroCanastaRecomendada = (mayorCostoCanasta > menorCostoCanasta && menorCostoCanasta !== Infinity)
        ? (mayorCostoCanasta - menorCostoCanasta)
        : 0;
    var ahorroCombinadoMaximo = (mayorCostoCanasta > costoOptimoCombinado && costoOptimoCombinado > 0)
        ? (mayorCostoCanasta - costoOptimoCombinado)
        : 0;

    // ==============================================================================
    // PESTAÑA 1: 🛒 CANASTA MENSUAL
    // ==============================================================================
    var ws1 = workbook.addWorksheet('🛒 Canasta Mensual', { views: [{ showGridLines: true }] });

    // Título Principal
    ws1.mergeCells('B2:H2');
    var tWs1 = ws1.getCell('B2');
    tWs1.value = '🛒 COMPARATIVA DE PRECIOS — CANASTA COMPLETA';
    tWs1.font = { name: 'Segoe UI', size: 14, bold: true, color: { argb: 'FFFFFFFF' } };
    tWs1.alignment = { vertical: 'middle', horizontal: 'center' };
    tWs1.fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: COLOR_AZUL_OSCURO } };
    ws1.getRow(2).height = 34;

    // Subtítulo
    ws1.mergeCells('B3:H3');
    var stWs1 = ws1.getCell('B3');
    stWs1.value = 'Relevamiento en Carrefour, COTO y Día % • Si un producto no se encuentra se descarta su precio del total para comparar equitativamente.';
    stWs1.font = { size: 9, italic: true, color: { argb: 'FF666666' } };
    stWs1.alignment = { vertical: 'middle', horizontal: 'center' };
    ws1.getRow(3).height = 20;

    // Cabecera de la tabla de productos
    var hWs1 = [
        { col: 'B', text: 'Producto Solicitado' },
        { col: 'C', text: 'Carrefour' },
        { col: 'D', text: 'COTO' },
        { col: 'E', text: 'Día %' },
        { col: 'F', text: 'Estado / Encontrado' },
        { col: 'G', text: '🏆 Supermercado Ganador' },
        { col: 'H', text: 'Precio Ganador' }
    ];
    ws1.getRow(5).height = 24;
    hWs1.forEach(function (h) {
        var cell = ws1.getCell(h.col + '5');
        cell.value = h.text;
        cell.font = { size: 10, bold: true, color: { argb: 'FFFFFFFF' } };
        cell.alignment = { vertical: 'middle', horizontal: 'center' };
        cell.fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: COLOR_AZUL_TITULO } };
    });

    var rWs1 = 6;
    filasCanasta.forEach(function (f) {
        ws1.getRow(rWs1).height = 22;

        // Nombre del producto
        ws1.getCell('B' + rWs1).value = (f.label || f.productoKey).toUpperCase();
        ws1.getCell('B' + rWs1).font = { bold: true, size: 9.5 };
        ws1.getCell('B' + rWs1).alignment = { vertical: 'middle', horizontal: 'left' };

        // Columnas por supermercado: Carrefour, COTO, Día %
        var mapeoSuper = [
            { col: 'C', superm: 'Carrefour', obj: f.carrefour },
            { col: 'D', superm: 'COTO', obj: f.coto },
            { col: 'E', superm: 'Día %', obj: f.dia }
        ];

        mapeoSuper.forEach(function (m) {
            var cCell = ws1.getCell(m.col + rWs1);
            if (!m.obj || !m.obj.valido || m.obj.precio === null || m.obj.precio <= 0) {
                var etiqueta = m.obj ? (m.obj.estado === 'SIN STOCK' ? '⚠️ Sin Stock' : '❌ No Encontrado') : '❌ No Encontrado';
                cCell.value = etiqueta;
                cCell.font = { size: 8.5, color: { argb: COLOR_ROJO_TEXTO }, italic: true };
                cCell.alignment = { vertical: 'middle', horizontal: 'center' };
                cCell.fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: COLOR_ROJO_PASTEL } };
            } else {
                cCell.value = m.obj.precio;
                cCell.numFmt = '"$"#,##0.00';
                cCell.alignment = { vertical: 'middle', horizontal: 'right' };
                var esGanadorDeProd = f.ganador && f.ganador.superm === m.superm;
                if (esGanadorDeProd) {
                    cCell.fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: COLOR_VERDE_PASTEL } };
                    cCell.font = { bold: true, color: { argb: COLOR_VERDE_TEXTO }, size: 9.5 };
                } else {
                    cCell.font = { size: 9.5 };
                }
            }
        });

        // Columna F: Estado / Encontrado
        var stProdCell = ws1.getCell('F' + rWs1);
        if (f.cantidadTotalValidos === 3) {
            stProdCell.value = '✅ Encontrado en los 3';
            stProdCell.font = { bold: true, color: { argb: COLOR_VERDE_TEXTO }, size: 9 };
            stProdCell.fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: COLOR_VERDE_PASTEL } };
        } else if (f.cantidadTotalValidos > 0) {
            stProdCell.value = '⚠️ Encontrado en ' + f.cantidadTotalValidos + ' de 3';
            stProdCell.font = { bold: true, color: { argb: COLOR_AMARILLO_TEXTO }, size: 9 };
            stProdCell.fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: COLOR_AMARILLO_PASTEL } };
        } else {
            stProdCell.value = '❌ No encontrado';
            stProdCell.font = { bold: true, color: { argb: COLOR_ROJO_TEXTO }, size: 9 };
            stProdCell.fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: COLOR_ROJO_PASTEL } };
        }
        stProdCell.alignment = { vertical: 'middle', horizontal: 'center' };

        // Columna G: Supermercado Ganador
        var gCell = ws1.getCell('G' + rWs1);
        if (f.ganador) {
            gCell.value = '🏆 ' + f.ganador.superm;
            gCell.font = { bold: true, color: { argb: COLOR_VERDE_TEXTO }, size: 9.5 };
            gCell.fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: COLOR_VERDE_PASTEL } };
        } else {
            gCell.value = 'Sin opción válida';
            gCell.font = { italic: true, color: { argb: 'FF888888' }, size: 9 };
        }
        gCell.alignment = { vertical: 'middle', horizontal: 'center' };

        // Columna H: Precio Ganador
        var pGanCell = ws1.getCell('H' + rWs1);
        if (f.ganador) {
            pGanCell.value = f.ganador.precio;
            pGanCell.numFmt = '"$"#,##0.00';
            pGanCell.font = { bold: true, color: { argb: COLOR_VERDE_TEXTO }, size: 9.5 };
            pGanCell.fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: COLOR_VERDE_PASTEL } };
            pGanCell.alignment = { vertical: 'middle', horizontal: 'right' };
        } else {
            pGanCell.value = '-';
            pGanCell.font = { color: { argb: 'FF888888' } };
            pGanCell.alignment = { vertical: 'middle', horizontal: 'center' };
        }

        rWs1++;
    });

    // Fila Total al pie de la tabla
    ws1.getRow(rWs1).height = 26;
    ws1.getCell('B' + rWs1).value = 'TOTAL GASTADO EN PRODUCTOS ENCONTRADOS';
    ws1.getCell('B' + rWs1).font = { bold: true, size: 9.5 };
    ws1.getCell('B' + rWs1).alignment = { vertical: 'middle', horizontal: 'left' };

    ['C', 'D', 'E'].forEach(function (col, idx) {
        var s = supersList[idx];
        var cell = ws1.getCell(col + rWs1);
        cell.value = totalesCanasta[s] > 0 ? totalesCanasta[s] : 0;
        cell.numFmt = '"$"#,##0.00';
        cell.alignment = { vertical: 'middle', horizontal: 'right' };
        if (s === superRecomendado) {
            cell.fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: COLOR_VERDE_PASTEL } };
            cell.font = { bold: true, color: { argb: COLOR_VERDE_TEXTO }, size: 10 };
        } else {
            cell.font = { bold: true, size: 9.5 };
        }
    });

    ws1.getCell('F' + rWs1).value = 'Compra Combinada';
    ws1.getCell('F' + rWs1).font = { bold: true, color: { argb: COLOR_VERDE_TEXTO }, size: 9 };
    ws1.getCell('F' + rWs1).alignment = { vertical: 'middle', horizontal: 'center' };

    var optCell = ws1.getCell('G' + rWs1);
    optCell.value = '⚡ Mínimo Posible';
    optCell.font = { bold: true, color: { argb: COLOR_VERDE_TEXTO }, size: 9 };
    optCell.alignment = { vertical: 'middle', horizontal: 'center' };

    var optValCell = ws1.getCell('H' + rWs1);
    optValCell.value = costoOptimoCombinado;
    optValCell.numFmt = '"$"#,##0.00';
    optValCell.font = { bold: true, color: { argb: COLOR_VERDE_TEXTO }, size: 10 };
    optValCell.alignment = { vertical: 'middle', horizontal: 'right' };
    optValCell.fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: COLOR_VERDE_PASTEL } };

    aplicarBordes(ws1, 'B', 5, 'H', rWs1);

    // ==============================================================================
    // SÍNTESIS FINAL: EN QUÉ SUPERMERCADO GASTÁS MENOS
    // ==============================================================================
    var rSint = rWs1 + 2;
    ws1.mergeCells('B' + rSint + ':H' + rSint);
    var tSint = ws1.getCell('B' + rSint);
    tSint.value = '📊 SÍNTESIS FINAL: ¿EN QUÉ SUPERMERCADO GASTÁS MENOS?';
    tSint.font = { name: 'Segoe UI', size: 11, bold: true, color: { argb: 'FFFFFFFF' } };
    tSint.alignment = { vertical: 'middle', horizontal: 'left' };
    tSint.fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: COLOR_AZUL_TITULO } };
    ws1.getRow(rSint).height = 24;

    // Tabla Comparativa de Síntesis
    var rTablaSintHead = rSint + 1;
    ws1.getRow(rTablaSintHead).height = 22;
    var hSint = [
        { col: 'B', text: 'Supermercado' },
        { col: 'C', text: 'Costo Total' },
        { col: 'D', text: 'Productos Encontrados' },
        { col: 'E', text: 'Precios Ganados' },
        { col: 'F', text: 'Diferencia vs Mejor' },
        { col: 'G', text: 'Veredicto' },
        { col: 'H', text: 'Ahorro Máximo' }
    ];
    hSint.forEach(function (h) {
        var cell = ws1.getCell(h.col + rTablaSintHead);
        cell.value = h.text;
        cell.font = { size: 9.5, bold: true, color: { argb: COLOR_AZUL_OSCURO } };
        cell.alignment = { vertical: 'middle', horizontal: 'center' };
        cell.fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: COLOR_AZUL_CLARO } };
    });

    var rSintRow = rTablaSintHead + 1;
    supersList.forEach(function (s) {
        ws1.getRow(rSintRow).height = 22;
        var esGanador = (s === superRecomendado && superRecomendado !== 'N/D');

        ws1.getCell('B' + rSintRow).value = s;
        ws1.getCell('B' + rSintRow).font = { bold: true };
        ws1.getCell('B' + rSintRow).alignment = { vertical: 'middle', horizontal: 'left' };

        var cCosto = ws1.getCell('C' + rSintRow);
        if (conteoEncontrados[s] > 0) {
            cCosto.value = totalesCanasta[s];
            cCosto.numFmt = '"$"#,##0.00';
            cCosto.font = { bold: true, color: { argb: esGanador ? COLOR_VERDE_TEXTO : 'FF333333' } };
            cCosto.alignment = { vertical: 'middle', horizontal: 'right' };
        } else {
            cCosto.value = 'Sin productos';
            cCosto.font = { italic: true, color: { argb: 'FF888888' }, size: 9 };
            cCosto.alignment = { vertical: 'middle', horizontal: 'center' };
        }

        var cEnc = ws1.getCell('D' + rSintRow);
        cEnc.value = conteoEncontrados[s] + ' de ' + productosMensualUnicos.length;
        cEnc.alignment = { vertical: 'middle', horizontal: 'center' };

        var cGan = ws1.getCell('E' + rSintRow);
        cGan.value = conteoGanados[s] + ' productos';
        cGan.alignment = { vertical: 'middle', horizontal: 'center' };
        cGan.font = { bold: conteoGanados[s] > 0 };

        var cDif = ws1.getCell('F' + rSintRow);
        if (conteoEncontrados[s] === 0) {
            cDif.value = 'Sin stock';
            cDif.font = { color: { argb: 'FF888888' } };
        } else if (conteoEncontrados[s] < maxEncontrados) {
            cDif.value = 'Faltan productos';
            cDif.font = { color: { argb: COLOR_AMARILLO_TEXTO }, bold: true };
        } else if (esGanador) {
            cDif.value = '🥇 Mejor opción';
            cDif.font = { bold: true, color: { argb: COLOR_VERDE_TEXTO } };
        } else if (totalesCanasta[s] > 0 && menorCostoCanasta !== Infinity) {
            var dif = totalesCanasta[s] - menorCostoCanasta;
            cDif.value = '+$' + dif.toLocaleString('es-AR', { minimumFractionDigits: 2 });
            cDif.font = { color: { argb: COLOR_ROJO_TEXTO } };
        } else {
            cDif.value = '-';
            cDif.font = { color: { argb: 'FF777777' } };
        }
        cDif.alignment = { vertical: 'middle', horizontal: 'center' };

        var cVerd = ws1.getCell('G' + rSintRow);
        if (conteoEncontrados[s] === 0) {
            cVerd.value = 'Descartado (Sin stock)';
            cVerd.font = { color: { argb: COLOR_ROJO_TEXTO }, size: 9 };
            cVerd.fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: COLOR_ROJO_PASTEL } };
        } else if (conteoEncontrados[s] < maxEncontrados) {
            cVerd.value = 'Descartado (Incompleto)';
            cVerd.font = { color: { argb: COLOR_AMARILLO_TEXTO }, size: 9, bold: true };
            cVerd.fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: COLOR_AMARILLO_PASTEL } };
        } else if (esGanador) {
            cVerd.value = '🏆 RECOMENDADO';
            cVerd.fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: COLOR_VERDE_PASTEL } };
            cVerd.font = { bold: true, color: { argb: COLOR_VERDE_TEXTO } };
        } else {
            cVerd.value = 'Más costoso';
            cVerd.font = { color: { argb: 'FF666666' } };
        }
        cVerd.alignment = { vertical: 'middle', horizontal: 'center' };

        var cAho = ws1.getCell('H' + rSintRow);
        if (esGanador && ahorroCanastaRecomendada > 0) {
            cAho.value = '-$' + ahorroCanastaRecomendada.toLocaleString('es-AR', { minimumFractionDigits: 2 });
            cAho.font = { bold: true, color: { argb: COLOR_VERDE_TEXTO } };
            cAho.fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: COLOR_VERDE_PASTEL } };
        } else {
            cAho.value = '-';
            cAho.font = { color: { argb: 'FF888888' } };
        }
        cAho.alignment = { vertical: 'middle', horizontal: 'center' };

        rSintRow++;
    });
    aplicarBordes(ws1, 'B', rTablaSintHead, 'H', rSintRow - 1);

    // Conclusión explicativa en tarjeta limpia
    var rCard = rSintRow + 1;
    ws1.mergeCells('B' + rCard + ':H' + (rCard + 3));
    var concNarrativa = ws1.getCell('B' + rCard);
    concNarrativa.value = '💡 CONCLUSIÓN FINAL DEL BOT RPA:\n' +
        '• En un solo supermercado: ' + (superRecomendado !== 'N/D' ? ('Te conviene comprar en ' + superRecomendado + ' con un gasto total de $' + menorCostoCanasta.toLocaleString('es-AR', { minimumFractionDigits: 2 }) + ' (descartando opciones con faltantes para comparar con equidad).') : 'No hay supermercados con stock completo suficiente para comparar.') + '\n' +
        '• Compra combinada (cada producto en su súper ganador): Pagás solo $' + costoOptimoCombinado.toLocaleString('es-AR', { minimumFractionDigits: 2 }) + ', ahorrando un total de $' + ahorroCombinadoMaximo.toLocaleString('es-AR', { minimumFractionDigits: 2 }) + ' en tu canasta.\n' +
        '• Para revisar búsquedas individuales, consultá la pestaña contigua "🔎 Consultas Individuales".';
    concNarrativa.font = { name: 'Segoe UI', size: 9.5, color: { argb: 'FF1F4E79' } };
    concNarrativa.fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: 'FFEBF1F5' } };
    concNarrativa.alignment = { vertical: 'middle', horizontal: 'left', wrapText: true };
    aplicarBordes(ws1, 'B', rCard, 'H', rCard + 3);

    // Ajustar anchos de columna en Hoja 1
    ws1.getColumn('A').width = 4;
    ws1.getColumn('B').width = 40;
    ws1.getColumn('C').width = 18;
    ws1.getColumn('D').width = 18;
    ws1.getColumn('E').width = 20;
    ws1.getColumn('F').width = 24;
    ws1.getColumn('G').width = 26;
    ws1.getColumn('H').width = 20;

    // ==============================================================================
    // PESTAÑA 2: 🔎 CONSULTAS INDIVIDUALES
    // ==============================================================================
    var ws2 = workbook.addWorksheet('🔎 Consultas Individuales', { views: [{ showGridLines: true }] });

    ws2.mergeCells('B2:G2');
    var tWs2 = ws2.getCell('B2');
    tWs2.value = '🎯 CONSULTA INDIVIDUAL: ¿DÓNDE TE CONVIENE COMPRAR?';
    tWs2.font = { name: 'Segoe UI', size: 14, bold: true, color: { argb: 'FFFFFFFF' } };
    tWs2.alignment = { vertical: 'middle', horizontal: 'center' };
    tWs2.fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: COLOR_AZUL_OSCURO } };
    ws2.getRow(2).height = 34;

    if (itemsIndividual.length === 0) {
        ws2.mergeCells('B4:G4');
        var vacioCell = ws2.getCell('B4');
        vacioCell.value = 'No se registraron consultas individuales aún. Realizá una búsqueda rápida desde el panel web para ver la comparativa aquí.';
        vacioCell.font = { italic: true, color: { argb: 'FF777777' }, size: 10 };
        vacioCell.alignment = { vertical: 'middle', horizontal: 'center' };
        ws2.getRow(4).height = 30;
    } else {
        // Última consulta realizada
        var ultimoItem = itemsIndividual[itemsIndividual.length - 1];
        var itemCatUltimo = catalogo.buscarEnCatalogo({
            producto: ultimoItem.producto,
            cantidad: ultimoItem.cantidad,
            unidad: ultimoItem.unidad
        }) || catalogo.buscarEnCatalogo(ultimoItem.producto);

        var ultimoKey = itemCatUltimo ? itemCatUltimo.id : validador.normalizar(ultimoItem.producto);
        var tituloProducto = itemCatUltimo ? itemCatUltimo.nombre_completo : ultimoItem.producto;
        var ultimaFecha = ultimoItem.fecha;

        var itemsUltimaConsulta = [];
        for (var i = itemsIndividual.length - 1; i >= 0; i--) {
            var curr = itemsIndividual[i];
            var currCat = catalogo.buscarEnCatalogo({
                producto: curr.producto,
                cantidad: curr.cantidad,
                unidad: curr.unidad
            }) || catalogo.buscarEnCatalogo(curr.producto);
            var currKey = currCat ? currCat.id : validador.normalizar(curr.producto);

            if (currKey === ultimoKey || curr.producto.toLowerCase().trim() === ultimoItem.producto.toLowerCase().trim()) {
                itemsUltimaConsulta.unshift(curr);
                if (itemsUltimaConsulta.length === 3) break;
            } else {
                break;
            }
        }
        if (itemsUltimaConsulta.length === 0) {
            itemsUltimaConsulta = itemsIndividual.slice(-3);
        }

        var validosUltima = itemsUltimaConsulta.filter(function (x) { return x.valido && x.precio !== null && x.precio > 0; });
        validosUltima.sort(function (a, b) { return a.precio - b.precio; });

        var ganadorUltima = validosUltima.length > 0 ? validosUltima[0] : null;
        var masCaroUltima = validosUltima.length > 1 ? validosUltima[validosUltima.length - 1] : null;
        var ahorroUltima = (ganadorUltima && masCaroUltima) ? (masCaroUltima.precio - ganadorUltima.precio) : 0;
        var ahorroUltimaPct = (masCaroUltima && masCaroUltima.precio > 0) ? ((ahorroUltima / masCaroUltima.precio) * 100) : 0;

        // Tarjeta del producto
        ws2.mergeCells('B4:G4');
        var prodCell = ws2.getCell('B4');
        prodCell.value = '🔎 PRODUCTO CONSULTADO:  "' + tituloProducto.toUpperCase() + '"';
        prodCell.font = { name: 'Segoe UI', size: 14, bold: true, color: { argb: 'FFFFFFFF' } };
        prodCell.fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: COLOR_AZUL_TITULO } };
        prodCell.alignment = { vertical: 'middle', horizontal: 'center' };
        ws2.getRow(4).height = 34;

        ws2.mergeCells('B5:G5');
        var stSub = ws2.getCell('B5');
        stSub.value = 'Fecha: ' + ultimaFecha + '  │  Supermercados relevados: Carrefour, COTO y Día %';
        stSub.font = { name: 'Segoe UI', size: 9.5, italic: true, color: { argb: 'FF555555' } };
        stSub.alignment = { vertical: 'middle', horizontal: 'center' };
        ws2.getRow(5).height = 20;
        aplicarBordes(ws2, 'B', 4, 'G', 5);

        // Banner de veredicto
        ws2.mergeCells('B7:G8');
        var bannerCell = ws2.getCell('B7');

        if (ganadorUltima) {
            bannerCell.value = '🏆 TE CONVIENE COMPRAR EN: ' + ganadorUltima.supermercado + ' (' + validador.formatoMoneda(ganadorUltima.precio) + ')\n' +
                (ahorroUltima > 0
                    ? '💰 AHORRO POTENCIAL: ' + validador.formatoMoneda(ahorroUltima) + ' (' + ahorroUltimaPct.toFixed(0) + '% menos que en ' + masCaroUltima.supermercado + ')'
                    : 'ℹ️ Mismo precio en las opciones disponibles.');
            bannerCell.fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: COLOR_VERDE_PASTEL } };
            bannerCell.font = { name: 'Segoe UI', size: 12, bold: true, color: { argb: COLOR_VERDE_TEXTO } };
        } else {
            bannerCell.value = '⚠️ NINGÚN SUPERMERCADO ARROJÓ UNA COINCIDENCIA VÁLIDA DISPONIBLE';
            bannerCell.fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: COLOR_ROJO_PASTEL } };
            bannerCell.font = { name: 'Segoe UI', size: 11, bold: true, color: { argb: COLOR_ROJO_TEXTO } };
        }
        bannerCell.alignment = { vertical: 'middle', horizontal: 'center', wrapText: true };
        ws2.getRow(7).height = 28;
        ws2.getRow(8).height = 28;
        aplicarBordes(ws2, 'B', 7, 'G', 8);

        // Cabecera tabla comparativa
        ws2.getRow(10).height = 26;
        var hIndiv = [
            { col: 'B', text: 'Supermercado' },
            { col: 'C', text: 'Precio Vigente' },
            { col: 'D', text: 'Estado / Validación' },
            { col: 'E', text: 'Producto Encontrado en Góndola' },
            { col: 'F', text: 'Veredicto' },
            { col: 'G', text: 'Enlace Web Directo' }
        ];
        hIndiv.forEach(function (h) {
            var cell = ws2.getCell(h.col + '10');
            cell.value = h.text;
            cell.font = { name: 'Segoe UI', size: 10, bold: true, color: { argb: 'FFFFFFFF' } };
            cell.alignment = { vertical: 'middle', horizontal: 'center' };
            cell.fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: COLOR_AZUL_TITULO } };
        });

        var rWs2Ind = 11;
        itemsUltimaConsulta.forEach(function (it) {
            ws2.getRow(rWs2Ind).height = 26;
            var esGanador = ganadorUltima && (it.supermercado === ganadorUltima.supermercado) && it.valido;

            var supCell = ws2.getCell('B' + rWs2Ind);
            supCell.value = it.supermercado;
            supCell.alignment = { vertical: 'middle', horizontal: 'center' };
            supCell.font = { name: 'Segoe UI', bold: true, size: 9.5 };

            var preCell = ws2.getCell('C' + rWs2Ind);
            if (it.precio !== null && it.precio > 0) {
                preCell.value = it.precio;
                preCell.numFmt = '"$"#,##0.00';
            } else {
                preCell.value = it.precioStr || 'N/D';
            }
            preCell.alignment = { vertical: 'middle', horizontal: 'right' };

            var estCell = ws2.getCell('D' + rWs2Ind);
            estCell.alignment = { vertical: 'middle', horizontal: 'center' };

            var verdCell = ws2.getCell('F' + rWs2Ind);
            verdCell.alignment = { vertical: 'middle', horizontal: 'center' };

            if (esGanador) {
                preCell.font = { name: 'Segoe UI', bold: true, size: 10, color: { argb: COLOR_VERDE_TEXTO } };
                estCell.value = '✅ VALIDADA';
                estCell.fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: COLOR_VERDE_PASTEL } };
                estCell.font = { name: 'Segoe UI', bold: true, size: 9.5, color: { argb: COLOR_VERDE_TEXTO } };
                verdCell.value = '🏆 GANADOR';
                verdCell.font = { name: 'Segoe UI', bold: true, size: 9.5, color: { argb: COLOR_VERDE_TEXTO } };
                verdCell.fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: COLOR_VERDE_PASTEL } };
            } else if (it.valido) {
                preCell.font = { name: 'Segoe UI', bold: true, size: 9.5, color: { argb: 'FF333333' } };
                estCell.value = '✅ VALIDADA';
                estCell.fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: COLOR_AZUL_CLARO } };
                estCell.font = { name: 'Segoe UI', bold: true, size: 9.5, color: { argb: COLOR_AZUL_TITULO } };
                verdCell.value = 'Más caro';
                verdCell.font = { name: 'Segoe UI', size: 9, color: { argb: 'FF666666' } };
            } else {
                preCell.font = { name: 'Segoe UI', strike: true, italic: true, size: 9.5, color: { argb: 'FF888888' } };
                preCell.fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: 'FFF9EAE1' } };
                estCell.value = '❌ ' + it.estado;
                estCell.fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: COLOR_ROJO_PASTEL } };
                estCell.font = { name: 'Segoe UI', bold: true, size: 9, color: { argb: COLOR_ROJO_TEXTO } };
                verdCell.value = 'Descartado';
                verdCell.font = { name: 'Segoe UI', size: 8.5, color: { argb: 'FF888888' } };
            }

            var nomCell = ws2.getCell('E' + rWs2Ind);
            nomCell.value = it.nombre;
            nomCell.alignment = { vertical: 'middle', horizontal: 'left', wrapText: true };
            nomCell.font = { name: 'Segoe UI', size: 9.5, bold: esGanador };

            var lnkCell = ws2.getCell('G' + rWs2Ind);
            if (it.url && it.url.startsWith('http')) {
                lnkCell.value = { text: '🔗 Ver en ' + it.supermercado, hyperlink: it.url };
                lnkCell.font = { name: 'Segoe UI', color: { argb: 'FF0563C1' }, underline: true, size: 9 };
            } else {
                lnkCell.value = '-';
            }
            lnkCell.alignment = { vertical: 'middle', horizontal: 'center' };

            if (esGanador) {
                supCell.fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: COLOR_VERDE_PASTEL } };
                nomCell.fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: COLOR_VERDE_PASTEL } };
                lnkCell.fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: COLOR_VERDE_PASTEL } };
            }

            rWs2Ind++;
        });
        aplicarBordes(ws2, 'B', 10, 'G', rWs2Ind - 1);
    }

    ws2.getColumn('A').width = 4;
    ws2.getColumn('B').width = 18;
    ws2.getColumn('C').width = 18;
    ws2.getColumn('D').width = 24;
    ws2.getColumn('E').width = 44;
    ws2.getColumn('F').width = 20;
    ws2.getColumn('G').width = 22;

    // Guardar el libro consolidado con reintentos seguros contra bloqueos de Windows/Excel
    for (var intento = 1; intento <= 3; intento++) {
        try {
            try {
                require('child_process').execSync('taskkill /F /IM EXCEL.EXE', { windowsHide: true, stdio: 'ignore' });
            } catch (eKill) {}
            await new Promise(function (r) { setTimeout(r, 450); });
            await workbook.xlsx.writeFile(XLSX_PATH);
            console.log('[OK] Reporte Excel generado exitosamente en: ' + XLSX_PATH);
            break;
        } catch (err) {
            if (intento < 3 && (err.code === 'EBUSY' || (err.message && err.message.includes('EBUSY')))) {
                console.warn('\n[AVISO] Archivo bloqueado por Excel (intento ' + intento + '/3). Reintentando tras cerrar Microsoft Excel...');
                await new Promise(function (r) { setTimeout(r, 800); });
            } else {
                console.error('[ERROR] No se pudo guardar el archivo Excel:', err.message);
                break;
            }
        }
    }
}

main().catch(console.error);
