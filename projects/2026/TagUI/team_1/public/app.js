document.addEventListener('DOMContentLoaded', () => {
    const btnCompraMes = document.getElementById('btn-compra-mes');
    const btnBuscarIndividual = document.getElementById('btn-buscar-individual');
    const logContainer = document.getElementById('log-container');
    const statusIndicator = document.getElementById('status-indicator');
    const btnAbort = document.getElementById('btn-abort');
    const abortBar = document.getElementById('abort-bar');

    // Monitor y Pasos de Supermercados
    const monitorStatusText = document.getElementById('monitor-status-text');
    const mainProgressFill = document.getElementById('main-progress-fill');
    const progressPercentBadge = document.getElementById('progress-percent-badge');
    const stepCarrefour = document.getElementById('step-carrefour');
    const statusCarrefour = document.getElementById('status-carrefour');
    const stepCoto = document.getElementById('step-coto');
    const statusCoto = document.getElementById('status-coto');
    const stepDia = document.getElementById('step-dia');
    const statusDia = document.getElementById('status-dia');

    let ws = null;

    function resetSuperSteps() {
        if (stepCarrefour) stepCarrefour.className = 'super-step-card';
        if (statusCarrefour) statusCarrefour.textContent = 'En espera';
        if (stepCoto) stepCoto.className = 'super-step-card';
        if (statusCoto) statusCoto.textContent = 'En espera';
        if (stepDia) stepDia.className = 'super-step-card';
        if (statusDia) statusDia.textContent = 'En espera';
        if (mainProgressFill) mainProgressFill.style.width = '0%';
        if (progressPercentBadge) progressPercentBadge.textContent = '0%';
        if (monitorStatusText) monitorStatusText.textContent = 'RPA EN ESPERA';
    }

    // Conectar WebSocket para logs en vivo del sistema
    function connectStream() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws/rpa-stream`;
        
        ws = new WebSocket(wsUrl);

        ws.onopen = () => {
            console.log("[WebSocket] Conectado con el servidor.");
        };

        ws.onmessage = (event) => {
            try {
                const msg = JSON.parse(event.data);
                if (msg.type === 'log') {
                    addLog(msg.message);
                    parseLogStep(msg.message);
                } else if (msg.type === 'progress') {
                    if (typeof msg.percent === 'number') {
                        if (mainProgressFill) mainProgressFill.style.width = `${msg.percent}%`;
                        if (progressPercentBadge) progressPercentBadge.textContent = `${msg.percent}%`;
                    }
                } else if (msg.type === 'status') {
                    if (monitorStatusText) {
                        if (msg.state === 'live') {
                            monitorStatusText.textContent = '🤖 AUTOMATIZACIÓN EN CURSO';
                        } else if (msg.state === 'connecting') {
                            monitorStatusText.textContent = 'CONECTANDO CON NAVEGADOR...';
                        } else if (msg.state === 'finished') {
                            monitorStatusText.textContent = '✓ RPA FINALIZADO EXITOSAMENTE';
                            if (mainProgressFill) mainProgressFill.style.width = '100%';
                            if (progressPercentBadge) progressPercentBadge.textContent = '100%';
                        } else if (msg.state === 'idle') {
                            monitorStatusText.textContent = 'RPA EN ESPERA';
                        } else if (msg.state === 'aborted') {
                            monitorStatusText.textContent = '🛑 RPA DETENIDO';
                        } else if (msg.state === 'error') {
                            monitorStatusText.textContent = 'ERROR EN LA EJECUCIÓN';
                        }
                    }
                }
            } catch (e) {
                console.error("[WebSocket] Error:", e);
            }
        };

        ws.onclose = () => {
            setTimeout(connectStream, 3000);
        };
    }

    connectStream();

    // Actualiza los pasos de los 3 supermercados según los logs
    function parseLogStep(text) {
        if (!text) return;
        if (text.includes('[SUPERMERCADO 1]')) {
            if (stepCarrefour) stepCarrefour.className = 'super-step-card active';
            if (statusCarrefour) statusCarrefour.textContent = 'En curso...';
            if (mainProgressFill) mainProgressFill.style.width = '25%';
            if (progressPercentBadge) progressPercentBadge.textContent = '25%';
            if (text.includes('Finalizado')) {
                if (stepCarrefour) stepCarrefour.className = 'super-step-card completed';
                if (statusCarrefour) statusCarrefour.textContent = '✓ Completado';
                if (mainProgressFill) mainProgressFill.style.width = '35%';
                if (progressPercentBadge) progressPercentBadge.textContent = '35%';
            }
        } else if (text.includes('[SUPERMERCADO 2]')) {
            if (stepCoto) stepCoto.className = 'super-step-card active';
            if (statusCoto) statusCoto.textContent = 'En curso...';
            if (mainProgressFill) mainProgressFill.style.width = '55%';
            if (progressPercentBadge) progressPercentBadge.textContent = '55%';
            if (text.includes('Finalizado')) {
                if (stepCoto) stepCoto.className = 'super-step-card completed';
                if (statusCoto) statusCoto.textContent = '✓ Completado';
                if (mainProgressFill) mainProgressFill.style.width = '70%';
                if (progressPercentBadge) progressPercentBadge.textContent = '70%';
            }
        } else if (text.includes('[SUPERMERCADO 3]')) {
            if (stepDia) stepDia.className = 'super-step-card active';
            if (statusDia) statusDia.textContent = 'En curso...';
            if (mainProgressFill) mainProgressFill.style.width = '85%';
            if (progressPercentBadge) progressPercentBadge.textContent = '85%';
            if (text.includes('Finalizado')) {
                if (stepDia) stepDia.className = 'super-step-card completed';
                if (statusDia) statusDia.textContent = '✓ Completado';
                if (mainProgressFill) mainProgressFill.style.width = '100%';
                if (progressPercentBadge) progressPercentBadge.textContent = '100%';
            }
        } else if (text.includes('[ RPA FINALIZADO ]')) {
            if (stepCarrefour) stepCarrefour.className = 'super-step-card completed';
            if (stepCoto) stepCoto.className = 'super-step-card completed';
            if (stepDia) stepDia.className = 'super-step-card completed';
            if (mainProgressFill) mainProgressFill.style.width = '100%';
            if (progressPercentBadge) progressPercentBadge.textContent = '100%';
        }
    }

    // Añadir mensajes a la consola virtual
    function addLog(msg, isError = false) {
        const p = document.createElement('p');
        p.textContent = `> ${msg}`;
        if (isError) p.classList.add('log-error');
        logContainer.appendChild(p);
        logContainer.scrollTop = logContainer.scrollHeight;
    }

    // Cambiar estado visual de botones
    function setRunningState(isRunning) {
        const btns = document.querySelectorAll('button:not(#btn-cerrar-modal):not(#btn-abort):not(#btn-toggle-screen)');
        btns.forEach(btn => btn.disabled = isRunning);
        
        if (isRunning) {
            statusIndicator.textContent = "Procesando...";
            statusIndicator.className = "indicator running";
            if (abortBar) abortBar.classList.add('visible');
            if (btnAbort) btnAbort.disabled = false;
        } else {
            statusIndicator.textContent = "Listo";
            statusIndicator.className = "indicator idle";
            if (abortBar) abortBar.classList.remove('visible');
        }
    }

    // Ejecutar llamada a la API
    async function executeAction(endpoint, body = null) {
        resetSuperSteps();
        setRunningState(true);
        addLog(`Iniciando: ${endpoint}...`);

        const payload = Object.assign({}, body || {}, {
            demoMode: true,
            typingDelay: 50,
            mouseDuration: 600,
            headless: true
        });
        
        try {
            const options = {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            };
            
            const response = await fetch(endpoint, options);
            const data = await response.json();
            
            if (data.success) {
                addLog(`✓ ${data.message}`);
            } else {
                addLog(`Error: ${data.message}`, true);
            }
        } catch (error) {
            addLog(`Error de conexión: ${error.message}`, true);
        } finally {
            setRunningState(false);
        }
    }

    // ==========================================================================
    // GESTIÓN DEL CATÁLOGO CERRADO EN EL FRONTEND
    // ==========================================================================
    let catalogoGlobal = null;
    let itemsCatalogoGlobal = [];
    const selectProducto = document.getElementById('select-producto');
    const boxInfoProducto = document.getElementById('box-info-producto');
    const infoMarca = document.getElementById('info-marca');
    const infoVariante = document.getElementById('info-variante');
    const infoPresentacion = document.getElementById('info-presentacion');

    async function cargarCatalogoUI() {
        try {
            const resp = await fetch('/api/catalogo');
            const data = await resp.json();
            if (data.success && data.catalogo) {
                catalogoGlobal = data.catalogo;
                itemsCatalogoGlobal = data.items || [];
                poblarSelectProductosUnificado();
                cargarCanastaActual();
            }
        } catch (e) {
            console.error('Error cargando catálogo:', e);
        }
    }

    function poblarSelectProductosUnificado() {
        if (!selectProducto || !catalogoGlobal) return;
        poblarDesplegableConCatalogo(selectProducto, '', '-- Selecciona un producto del catálogo --');
    }

    function mostrarInfoProducto(item) {
        if (!boxInfoProducto) return;
        if (!item) {
            boxInfoProducto.style.display = 'none';
            return;
        }
        boxInfoProducto.style.display = 'block';
        if (infoMarca) infoMarca.textContent = item.marca;
        if (infoVariante) infoVariante.textContent = item.variante || 'N/A';
        if (infoPresentacion) infoPresentacion.textContent = `${item.cantidad} ${item.unidad}`;
    }

    if (selectProducto) {
        selectProducto.addEventListener('change', (e) => {
            const val = e.target.value;
            if (!val) {
                mostrarInfoProducto(null);
                return;
            }
            const item = itemsCatalogoGlobal.find(it => it.id === val);
            mostrarInfoProducto(item);
        });
    }

    // Iniciar carga del catálogo
    cargarCatalogoUI();

    // ==========================================================================
    // ==========================================================================
    // CANASTA PERSONALIZABLE Y GESTIÓN DE PRODUCTOS A BUSCAR (PRODUCTOS ÚNICOS)
    // ==========================================================================
    let canastaActual = [];
    const countProdsCanasta = document.getElementById('count-prods-canasta');
    const previewCountText = document.getElementById('preview-count-text');
    const quickSelectCanasta = document.getElementById('quick-select-canasta');
    const btnQuickAddProd = document.getElementById('btn-quick-add-prod');
    const canastaSimpleLista = document.getElementById('canasta-simple-lista');

    const modalSelectNuevoProd = document.getElementById('modal-select-nuevo-prod');
    const modalBtnAgregarProd = document.getElementById('modal-btn-agregar-prod');
    const modalTotalCount = document.getElementById('modal-total-count');
    const btnAddEmptyRow = document.getElementById('btn-add-empty-row');

    function escapeHtml(str) {
        if (!str) return '';
        return String(str).replace(/&/g, '&amp;').replace(/"/g, '&quot;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    }

    // Poblar cualquier elemento <select> con los productos del catálogo agrupados por categoría
    function poblarDesplegableConCatalogo(selectEl, selectedId = '', placeholder = '-- Selecciona producto para agregar a la lista --') {
        if (!selectEl || !catalogoGlobal) return;
        selectEl.innerHTML = `<option value="">${placeholder}</option>`;

        const categorias = Object.keys(catalogoGlobal);
        categorias.forEach(cat => {
            const prods = catalogoGlobal[cat];
            if (!prods || prods.length === 0) return;

            const optgroup = document.createElement('optgroup');
            optgroup.label = cat.toUpperCase();

            prods.forEach(p => {
                const opt = document.createElement('option');
                opt.value = p.id;
                opt.textContent = p.nombre_completo;
                if (selectedId && (p.id === selectedId || p.producto.toLowerCase() === selectedId.toLowerCase())) {
                    opt.selected = true;
                }
                optgroup.appendChild(opt);
            });

            selectEl.appendChild(optgroup);
        });
    }

    // Carga la canasta desde input.csv del servidor
    async function cargarCanastaActual() {
        try {
            const resp = await fetch('/api/input');
            const data = await resp.json();
            canastaActual = [];

            if (data.success && data.data) {
                const lines = data.data.split(/\r?\n/).map(l => l.trim()).filter(Boolean);
                for (let i = 1; i < lines.length; i++) {
                    const parts = lines[i].split(',').map(p => p.trim());
                    const prodText = parts[0] || '';
                    const cant = parts[1] ? (parseFloat(parts[1]) || 1) : 1;
                    const unid = parts[2] || '';

                    if (!prodText) continue;

                    const matched = itemsCatalogoGlobal.find(it => 
                        it.id === prodText ||
                        it.producto.toLowerCase() === prodText.toLowerCase() ||
                        it.nombre_completo.toLowerCase() === prodText.toLowerCase() ||
                        it.nombre_completo.toLowerCase().includes(prodText.toLowerCase()) ||
                        it.marca.toLowerCase() === prodText.toLowerCase()
                    );

                    if (matched) {
                        canastaActual.push({
                            id: matched.id,
                            producto: matched.producto,
                            nombre_completo: matched.nombre_completo,
                            cantidad: matched.cantidad,
                            unidad: matched.unidad,
                            categoria: matched.categoria
                        });
                    } else {
                        canastaActual.push({
                            id: '',
                            producto: prodText,
                            nombre_completo: prodText,
                            cantidad: cant,
                            unidad: unid,
                            categoria: ''
                        });
                    }
                }
            }
        } catch (e) {
            console.error('Error al cargar canasta actual:', e);
        }

        renderizarListaSimpleCanasta();
        poblarDesplegableConCatalogo(quickSelectCanasta, '', '-- Selecciona producto para agregar a la lista --');
        poblarDesplegableConCatalogo(modalSelectNuevoProd, '', '-- Selecciona producto disponible del catálogo --');
    }

    // Renderiza la lista limpia y directa en la tarjeta de Compra del Mes (sin mayor decoración)
    function renderizarListaSimpleCanasta() {
        const total = canastaActual.length;
        if (countProdsCanasta) countProdsCanasta.textContent = total;
        if (previewCountText) previewCountText.textContent = total;

        if (!canastaSimpleLista) return;
        canastaSimpleLista.innerHTML = '';

        if (total === 0) {
            canastaSimpleLista.innerHTML = '<li style="padding: 0.6rem; color: var(--text-muted); font-size: 0.8rem; font-style: italic; text-align: center;">No hay productos en la canasta. Selecciona un producto del desplegable superior para agregarlo.</li>';
            return;
        }

        canastaActual.forEach((item, index) => {
            const li = document.createElement('li');
            li.className = 'canasta-item-row';
            li.innerHTML = `
                <div class="canasta-item-info">
                    <span class="canasta-item-num">${index + 1}.</span>
                    <span class="canasta-item-name" title="${escapeHtml(item.nombre_completo || item.producto)}">${escapeHtml(item.nombre_completo || item.producto)}</span>
                </div>
                <button type="button" class="btn-item-del" title="Eliminar este producto de la canasta" aria-label="Eliminar ${escapeHtml(item.nombre_completo || item.producto)}" data-idx="${index}">
                    <i class="fa-solid fa-trash-can"></i>
                    <span>Eliminar</span>
                </button>
            `;

            li.querySelector('.btn-item-del').addEventListener('click', async (e) => {
                e.stopPropagation();
                if (canastaActual.length <= 1) {
                    alert("La canasta debe tener al menos un producto a buscar.");
                    return;
                }
                const prodEliminado = item.nombre_completo || item.producto;
                canastaActual.splice(index, 1);
                await guardarCanastaEnServidor();
                renderizarListaSimpleCanasta();
                addLog(`✓ Se eliminó "${prodEliminado}" de la canasta.`);
            });

            canastaSimpleLista.appendChild(li);
        });
    }

    // Persiste la canasta actual a input.csv en el backend (sin columna de unidades)
    async function guardarCanastaEnServidor() {
        let contenido = "producto,cantidad,unidad\n";
        canastaActual.forEach(item => {
            contenido += `${item.producto},${item.cantidad},${item.unidad}\n`;
        });

        try {
            const res = await fetch('/api/input', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ contenido })
            });
            const data = await res.json();
            return data.success;
        } catch (e) {
            console.error('Error guardando canasta:', e);
            return false;
        }
    }

    // Agrega un producto a la lista cuando se presiona el botón Agregar
    async function agregarProductoACanasta(prodId) {
        if (!prodId) return;

        const itemCatalogo = itemsCatalogoGlobal.find(it => it.id === prodId);
        if (!itemCatalogo) {
            alert("Producto no encontrado en el catálogo.");
            return;
        }

        // Verificar si ya existe en la canasta para evitar duplicados
        const existente = canastaActual.find(it => it.id === prodId || it.producto.toLowerCase() === itemCatalogo.producto.toLowerCase());
        if (existente) {
            alert(`"${itemCatalogo.nombre_completo}" ya está en la lista de la canasta.`);
            return;
        }

        canastaActual.push({
            id: itemCatalogo.id,
            producto: itemCatalogo.producto,
            nombre_completo: itemCatalogo.nombre_completo,
            cantidad: itemCatalogo.cantidad,
            unidad: itemCatalogo.unidad,
            categoria: itemCatalogo.categoria
        });
        addLog(`✓ Se agregó "${itemCatalogo.nombre_completo}" a la canasta.`);

        const guardadoOk = await guardarCanastaEnServidor();
        if (guardadoOk) {
            renderizarListaSimpleCanasta();
            if (quickSelectCanasta) quickSelectCanasta.value = '';
        } else {
            alert("Hubo un error al guardar la canasta en el servidor.");
        }
    }

    // Botón Agregar a la canasta: toma el producto seleccionado en el desplegable y lo agrega a la lista inferior
    if (btnQuickAddProd) {
        btnQuickAddProd.addEventListener('click', () => {
            const prodId = quickSelectCanasta ? quickSelectCanasta.value : '';
            if (!prodId) {
                alert("Por favor selecciona un producto en el desplegable antes de agregarlo.");
                return;
            }
            agregarProductoACanasta(prodId);
        });
    }

    // Eventos de Botones Principales
    btnCompraMes.addEventListener('click', () => {
        executeAction('/api/compra-mes');
    });

    btnBuscarIndividual.addEventListener('click', () => {
        const prodId = selectProducto ? selectProducto.value : '';
        const item = itemsCatalogoGlobal.find(it => it.id === prodId);

        if (!item) {
            addLog("Por favor selecciona un producto del catálogo cerrado.", true);
            return;
        }

        executeAction('/api/buscar-individual', {
            id: item.id,
            producto: item.nombre_completo || item.producto,
            nombre_completo: item.nombre_completo,
            variante: item.variante,
            marca: item.marca,
            terminoBusqueda: item.termino_busqueda || item.nombre_completo,
            cantidad: item.cantidad,
            unidad: item.unidad
        });
    });

    // Manejo del Modal de Edición de Canasta
    const btnEditarLista = document.getElementById('btn-editar-lista');
    const editarModal = document.getElementById('editar-lista-modal');
    const btnCerrarEditarModal = document.getElementById('btn-cerrar-editar-modal');
    const btnCerrarXModal = document.getElementById('btn-cerrar-x-modal');
    const btnGuardarLista = document.getElementById('btn-guardar-lista');
    const modalTbodyCanasta = document.getElementById('modal-tbody-canasta');

    function actualizarContadorModal() {
        if (!modalTbodyCanasta || !modalTotalCount) return;
        const rows = modalTbodyCanasta.querySelectorAll('tr');
        modalTotalCount.textContent = rows.length;
    }

    function crearFilaCanasta(prodItem = null) {
        const tr = document.createElement('tr');
        
        const tdProd = document.createElement('td');
        const select = document.createElement('select');
        select.className = 'modal-input modal-select-prod';
        poblarDesplegableConCatalogo(select, prodItem ? prodItem.id : '', '-- Selecciona producto del catálogo --');
        tdProd.appendChild(select);

        const tdDel = document.createElement('td');
        tdDel.style.textAlign = 'center';
        tdDel.innerHTML = `<button type="button" class="btn-del-row" title="Eliminar este producto"><i class="fa-solid fa-trash"></i></button>`;

        tr.appendChild(tdProd);
        tr.appendChild(tdDel);

        tdDel.querySelector('.btn-del-row').addEventListener('click', () => {
            tr.remove();
            actualizarContadorModal();
        });

        select.addEventListener('change', () => {
            actualizarContadorModal();
        });

        return tr;
    }

    if (btnEditarLista) {
        btnEditarLista.addEventListener('click', async () => {
            editarModal.classList.add('active');
            poblarDesplegableConCatalogo(modalSelectNuevoProd, '', '-- Selecciona producto disponible del catálogo --');

            if (modalTbodyCanasta) {
                modalTbodyCanasta.innerHTML = '<tr><td colspan="2" style="text-align:center; padding: 1.5rem; color: var(--text-muted);"><i class="fa-solid fa-spinner fa-spin"></i> Cargando lista...</td></tr>';
            }

            try {
                const response = await fetch('/api/input');
                const data = await response.json();
                if (modalTbodyCanasta) modalTbodyCanasta.innerHTML = '';

                if (data.success && data.data) {
                    const lines = data.data.split(/\r?\n/).map(l => l.trim()).filter(Boolean);
                    let count = 0;
                    for (let i = 1; i < lines.length; i++) {
                        const parts = lines[i].split(',').map(p => p.trim());
                        const prodText = parts[0] || '';
                        const cant = parts[1] ? (parseFloat(parts[1]) || 1) : 1;
                        const unid = parts[2] || '';

                        const matched = itemsCatalogoGlobal.find(it => 
                            it.id === prodText ||
                            it.producto.toLowerCase() === prodText.toLowerCase() ||
                            it.nombre_completo.toLowerCase() === prodText.toLowerCase() ||
                            it.nombre_completo.toLowerCase().includes(prodText.toLowerCase()) ||
                            it.marca.toLowerCase() === prodText.toLowerCase()
                        );

                        if (prodText) {
                            modalTbodyCanasta.appendChild(crearFilaCanasta(matched || { id: '', producto: prodText, cantidad: cant, unidad: unid }));
                            count++;
                        }
                    }
                    if (count === 0) {
                        modalTbodyCanasta.appendChild(crearFilaCanasta(null));
                    }
                } else if (modalTbodyCanasta) {
                    modalTbodyCanasta.appendChild(crearFilaCanasta(null));
                }
            } catch (e) {
                if (modalTbodyCanasta) {
                    modalTbodyCanasta.innerHTML = '';
                    modalTbodyCanasta.appendChild(crearFilaCanasta(null));
                }
            }

            actualizarContadorModal();
        });
    }

    // Botón Agregar Producto desde el desplegable dentro del Modal
    if (modalBtnAgregarProd) {
        modalBtnAgregarProd.addEventListener('click', () => {
            const prodId = modalSelectNuevoProd ? modalSelectNuevoProd.value : '';
            if (!prodId) {
                alert("Por favor selecciona un producto disponible del catálogo.");
                return;
            }

            const itemCatalogo = itemsCatalogoGlobal.find(it => it.id === prodId);
            if (!itemCatalogo) {
                alert("Producto no encontrado en el catálogo.");
                return;
            }

            if (modalTbodyCanasta) {
                const nuevaFila = crearFilaCanasta(itemCatalogo);
                nuevaFila.classList.add('row-added-highlight');
                modalTbodyCanasta.appendChild(nuevaFila);
                actualizarContadorModal();
                nuevaFila.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
            }

            if (modalSelectNuevoProd) modalSelectNuevoProd.value = '';
        });
    }

    // Botón Añadir fila vacía en el Modal
    if (btnAddEmptyRow) {
        btnAddEmptyRow.addEventListener('click', () => {
            if (modalTbodyCanasta) {
                const filaVacia = crearFilaCanasta(null);
                filaVacia.classList.add('row-added-highlight');
                modalTbodyCanasta.appendChild(filaVacia);
                actualizarContadorModal();
                filaVacia.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
            }
        });
    }

    if (btnCerrarEditarModal) {
        btnCerrarEditarModal.addEventListener('click', () => {
            editarModal.classList.remove('active');
        });
    }

    if (btnCerrarXModal) {
        btnCerrarXModal.addEventListener('click', () => {
            editarModal.classList.remove('active');
        });
    }

    if (btnGuardarLista) {
        btnGuardarLista.addEventListener('click', async () => {
            if (!modalTbodyCanasta) return;
            const rows = modalTbodyCanasta.querySelectorAll('tr');
            let contenido = "producto,cantidad,unidad\n";
            let validCount = 0;
            const nuevaCanasta = [];

            rows.forEach(r => {
                const selProd = r.querySelector('.modal-select-prod');
                if (selProd && selProd.value) {
                    const item = itemsCatalogoGlobal.find(it => it.id === selProd.value);
                    if (item) {
                        contenido += `${item.producto},${item.cantidad},${item.unidad}\n`;
                        nuevaCanasta.push({
                            id: item.id,
                            producto: item.producto,
                            nombre_completo: item.nombre_completo,
                            cantidad: item.cantidad,
                            unidad: item.unidad,
                            categoria: item.categoria
                        });
                        validCount++;
                    }
                }
            });

            if (validCount === 0) {
                alert("Debes agregar al menos un producto del catálogo a la lista.");
                return;
            }

            try {
                const response = await fetch('/api/input', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ contenido })
                });
                const data = await response.json();
                if (data.success) {
                    canastaActual = nuevaCanasta;
                    renderizarListaSimpleCanasta();
                    editarModal.classList.remove('active');
                    addLog(`✓ Canasta guardada exitosamente (${validCount} productos únicos configurados).`);
                } else {
                    alert(`Error al guardar: ${data.message}`);
                }
            } catch (error) {
                alert(`Error al guardar: ${error.message}`);
            }
        });
    }

    // Kill-switch: botón de aborto visible en la interfaz
    if (btnAbort) {
        btnAbort.addEventListener('click', async () => {
            btnAbort.disabled = true;
            addLog('⛔ Solicitando aborto del RPA...');
            try {
                await fetch('/api/abort', { method: 'POST' });
                addLog('✓ RPA detenido por el usuario.');
            } catch (e) {
                addLog('Error al abortar: ' + e.message, true);
            }
            setRunningState(false);
        });
    }

    // Kill-switch: Si el usuario cierra el frontend en el navegador, abortar la búsqueda inmediatamente
    window.addEventListener('beforeunload', () => {
        try {
            navigator.sendBeacon('/api/abort');
        } catch (e) {}
    });
});
