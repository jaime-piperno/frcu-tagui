// historial-dashboard.js - Sincronizado con app.js
(function () {
    'use strict';

    const SUPERS = ['Carrefour', 'COTO', 'Día %'];
    const COLORES = { 'Carrefour': '#60a5fa', 'COTO': '#f87171', 'Día %': '#fbbf24' };
    const COLOR_TEXTO = '#94a3b8';
    const COLOR_GRILLA = 'rgba(255, 255, 255, 0.08)';

    const moneda = new Intl.NumberFormat('es-AR', { style: 'currency', currency: 'ARS' });
    const fechaFmt = new Intl.DateTimeFormat('es-AR', { dateStyle: 'short', timeStyle: 'short' });

    const $select = document.getElementById('hist-select-producto');
    const $canvas = document.getElementById('hist-chart');
    const $vacioGrafico = document.getElementById('hist-vacio');
    const $tbodyAlertas = document.getElementById('hist-tbody-alertas');
    const $vacioAlertas = document.getElementById('hist-vacio-alertas');
    const $tbodyResumen = document.getElementById('hist-tbody-resumen');
    const $vacioResumen = document.getElementById('hist-vacio-resumen');
    const $textoResumen = document.getElementById('hist-texto-resumen');
    const $tbodyResultados = document.getElementById('resultados-tbody');
    const $vacioResultados = document.getElementById('resultados-vacio');

    let chart = null;
    let ultimaCarga = 0;

    async function getJson(url) {
        const r = await fetch(url);
        if (!r.ok) throw new Error('HTTP ' + r.status);
        return r.json();
    }

    function celda(texto, clase) {
        const td = document.createElement('td');
        td.textContent = texto;
        if (clase) td.className = clase;
        return td;
    }

    function precioNumerico(valor) {
        if (typeof valor === 'number') return Number.isFinite(valor) && valor > 0 ? valor : null;
        const texto = String(valor == null ? '' : valor).replace(/[^\d.,-]/g, '');
        if (!texto) return null;
        let normalizado = texto;
        if (texto.includes(',')) {
            normalizado = texto.replace(/\./g, '').replace(',', '.');
        } else if (/^\d{1,3}(?:\.\d{3})+$/.test(texto)) {
            normalizado = texto.replace(/\./g, '');
        }
        const numero = Number(normalizado);
        return Number.isFinite(numero) && numero > 0 ? numero : null;
    }

    function dibujarGrafico(serie) {
        if (chart) { chart.destroy(); chart = null; }

        if (typeof Chart === 'undefined') {
            $vacioGrafico.textContent = 'Cargando motor de gráficos...';
            $vacioGrafico.style.display = 'block';
            return;
        }
        if (!serie || !serie.length) {
            $vacioGrafico.textContent = 'Aún no hay historial suficiente para graficar.';
            $vacioGrafico.style.display = 'block';
            return;
        }
        $vacioGrafico.style.display = 'none';

        const fechas = [...new Set(serie.map(f => f.fecha))].sort();
        const labels = fechas.map(f => fechaFmt.format(new Date(f)));
        const datasets = SUPERS.map(s => ({
            label: s,
            data: fechas.map(f => {
                const reg = serie.filter(r => r.fecha === f && r.supermercado === s).pop();
                return reg ? reg.precio : null;
            }),
            borderColor: COLORES[s],
            backgroundColor: COLORES[s],
            tension: 0.25,
            spanGaps: true,
            pointRadius: 4
        }));

        chart = new Chart($canvas, {
            type: 'line',
            data: { labels, datasets },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: { mode: 'index', intersect: false },
                plugins: {
                    legend: { labels: { color: '#f8fafc', font: { family: 'Inter', size: 12 } } },
                    tooltip: {
                        backgroundColor: 'rgba(15, 23, 42, 0.95)',
                        titleColor: '#f8fafc',
                        bodyColor: '#cbd5e1',
                        borderColor: 'rgba(255, 255, 255, 0.1)',
                        borderWidth: 1,
                        callbacks: {
                            label: ctx => ctx.parsed.y === null ? null : `${ctx.dataset.label}: ${moneda.format(ctx.parsed.y)}`
                        }
                    }
                },
                scales: {
                    x: { ticks: { color: COLOR_TEXTO }, grid: { color: COLOR_GRILLA } },
                    y: { ticks: { color: COLOR_TEXTO, callback: v => moneda.format(v) }, grid: { color: COLOR_GRILLA } }
                }
            }
        });
    }

    async function cargarHistorial() {
        if (!$select) return;
        try {
            const elegido = $select.value;
            const url = '/api/historial' + (elegido ? '?producto=' + encodeURIComponent(elegido) : '');
            const data = await getJson(url);

            if (data.productos && data.productos.length) {
                const valorActual = $select.value;
                $select.innerHTML = '';
                for (const p of data.productos) {
                    const op = document.createElement('option');
                    op.value = p;
                    op.textContent = p;
                    $select.appendChild(op);
                }
                $select.value = valorActual || data.producto || data.productos[0];
            }
            dibujarGrafico(data.serie);
        } catch (e) {
            console.warn('[Historial] Error al cargar serie de tiempo:', e);
        }
    }

    async function cargarAlertas() {
        if (!$tbodyAlertas) return;
        try {
            const data = await getJson('/api/alertas');
            $tbodyAlertas.innerHTML = '';
            $vacioAlertas.style.display = (data.alertas && data.alertas.length) ? 'none' : 'block';

            if (data.alertas) {
                for (const a of data.alertas) {
                    const tr = document.createElement('tr');
                    tr.appendChild(celda(fechaFmt.format(new Date(a.fecha))));

                    const tdTipo = document.createElement('td');
                    const badge = document.createElement('span');
                    const esBaja = a.tipo === 'BAJA';
                    badge.className = 'hist-badge ' + (esBaja ? 'hist-badge-baja' : 'hist-badge-min');
                    badge.textContent = esBaja ? '📉 Baja' : '🔥 Mínimo histórico';
                    tdTipo.appendChild(badge);
                    tr.appendChild(tdTipo);

                    tr.appendChild(celda(a.producto));
                    tr.appendChild(celda(a.supermercado));
                    tr.appendChild(celda(moneda.format(a.precioAnterior)));
                    tr.appendChild(celda(moneda.format(a.precioNuevo), 'hist-ganador'));
                    tr.appendChild(celda('-' + a.pct + '%'));
                    $tbodyAlertas.appendChild(tr);
                }
            }
        } catch (e) {
            console.warn('[Historial] Error al cargar alertas:', e);
        }
    }

    async function cargarResumen() {
        if (!$tbodyResumen) return;
        try {
            const data = await getJson('/api/resumen-canasta');
            $tbodyResumen.innerHTML = '';
            $textoResumen.textContent = '';

            const r = data.resumen;
            $vacioResumen.style.display = r ? 'none' : 'block';
            if (!r) return;

            for (const p of r.productos) {
                const tr = document.createElement('tr');
                tr.appendChild(celda(p.producto));
                for (const s of SUPERS) {
                    const precio = p.precios[s];
                    const celdaPrecio = celda(Number.isFinite(precio) ? moneda.format(precio) : '—', s === p.ganador ? 'hist-ganador' : '');
                    if (p.estados && p.estados[s]) celdaPrecio.title = p.estados[s];
                    tr.appendChild(celdaPrecio);
                }
                $tbodyResumen.appendChild(tr);
            }

            const trTotal = document.createElement('tr');
            trTotal.className = 'hist-fila-total';
            trTotal.appendChild(celda('TOTAL'));
            for (const s of SUPERS) {
                const total = r.totales[s];
                const celdaTotal = celda(Number.isFinite(total) ? moneda.format(total) : '—', s === r.mejor ? 'hist-ganador' : '');
                trTotal.appendChild(celdaTotal);
            }
            $tbodyResumen.appendChild(trTotal);

            const comparacion = r.mejor && r.peor
                ? `💰 Conviene ${r.mejor}: ahorras ${moneda.format(r.ahorro)} frente a ${r.peor}.`
                : 'No hay precios completos en al menos dos supermercados para comparar la canasta.';
            $textoResumen.textContent = comparacion;
        } catch (e) {
            console.warn('[Historial] Error al cargar resumen de canasta:', e);
        }
    }

    async function cargarResultados() {
        if (!$tbodyResultados) return;
        try {
            const ultimo = await getJson('/api/ultimo-proceso');
            let items = ultimo.data && Array.isArray(ultimo.data.items) ? ultimo.data.items : [];
            let modoPorDefecto = ultimo.data && ultimo.data.producto === 'Compra del Mes' ? 'compra_mes' : 'individual';

            if (!items.length) {
                const guardados = await getJson('/api/datos-completos');
                items = Array.isArray(guardados.items) ? guardados.items : [];
                items.sort((a, b) => String(a.fecha || '').localeCompare(String(b.fecha || '')));
                items = items.slice(-30).reverse();
                modoPorDefecto = '';
            } else {
                items = items.slice(-30).reverse();
            }

            $tbodyResultados.innerHTML = '';
            if ($vacioResultados) $vacioResultados.style.display = items.length ? 'none' : 'block';

            for (const item of items) {
                const tr = document.createElement('tr');
                const fecha = item.fecha ? new Date(item.fecha) : null;
                tr.appendChild(celda(fecha && !Number.isNaN(fecha.getTime()) ? fechaFmt.format(fecha) : '—'));
                tr.appendChild(celda((item.modo || modoPorDefecto) === 'compra_mes' ? 'Compra del mes' : 'Individual'));
                tr.appendChild(celda(item.producto || item.producto_solicitado || item.nombre_encontrado || '—'));
                tr.appendChild(celda(item.supermercado || '—'));

                const precio = precioNumerico(item.precio != null ? item.precio : item.precioStr);
                const tienePrecio = precio !== null;
                tr.appendChild(celda(tienePrecio ? moneda.format(precio) : '—'));
                tr.appendChild(celda(item.estado || item.stock_status || item.stockRaw || (tienePrecio ? 'Precio encontrado' : 'Sin precio')));
                $tbodyResultados.appendChild(tr);
            }
        } catch (e) {
            console.warn('[Resultados] Error al cargar resultados:', e);
            if ($vacioResultados) {
                $vacioResultados.textContent = 'No se pudieron cargar los resultados.';
                $vacioResultados.style.display = 'block';
            }
        }
    }

    async function recargarTodo(forzar = false) {
        const ahora = Date.now();
        if (!forzar && ahora - ultimaCarga < 1000) return;
        ultimaCarga = ahora;

        await Promise.allSettled([cargarHistorial(), cargarAlertas(), cargarResumen(), cargarResultados()]);
    }

    if ($select) {
        $select.addEventListener('change', () => {
            cargarHistorial();
        });
    }

    // Inicializar tablas al cargar la página
    document.addEventListener('DOMContentLoaded', () => {
        recargarTodo();
    });

    // Exponer función global para refrescar al terminar la automatización sin interferir con WebSocket
    window.refreshHistorialData = recargarTodo;
    window.refreshResultadosData = cargarResultados;
})();
