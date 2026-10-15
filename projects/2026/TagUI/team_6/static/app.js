/**
 * Mercado Pago RPA Conciliator - Client Logic
 */

document.addEventListener('DOMContentLoaded', () => {
  // Elements
  const dropzone = document.getElementById('dropzone');
  const fileInput = document.getElementById('fileInput');
  const dropzoneEmpty = document.getElementById('dropzoneEmpty');
  const filePreview = document.getElementById('filePreview');
  const fileName = document.getElementById('fileName');
  const fileSize = document.getElementById('fileSize');
  const btnRemoveFile = document.getElementById('btnRemoveFile');
  const formOptions = document.getElementById('formOptions');
  const periodoInput = document.getElementById('periodoInput');
  const hojaInput = document.getElementById('hojaInput');
  const btnSubmit = document.getElementById('btnSubmit');
  const conciliarForm = document.getElementById('conciliarForm');

  const uploadSection = document.getElementById('uploadSection');
  const loadingSection = document.getElementById('loadingSection');
  const resultsSection = document.getElementById('resultsSection');
  const errorBanner = document.getElementById('errorBanner');
  const errorMessage = document.getElementById('errorMessage');
  const btnCloseError = document.getElementById('btnCloseError');

  // Results elements
  const resumenTitulo = document.getElementById('resumenTitulo');
  const resumenSub = document.getElementById('resumenSub');
  const badgeEstado = document.getElementById('badgeEstado');
  const porcentajeMetric = document.getElementById('porcentajeMetric');
  const kpiMovimientos = document.getElementById('kpiMovimientos');
  const kpiCargos = document.getElementById('kpiCargos');
  const kpiAsociados = document.getElementById('kpiAsociados');
  const kpiPendientes = document.getElementById('kpiPendientes');
  const kpiPendientesLabel = document.getElementById('kpiPendientesLabel');
  const calloutMessage = document.getElementById('calloutMessage');
  const btnDownload = document.getElementById('btnDownload');
  const btnDownloadLabel = document.getElementById('btnDownloadLabel');
  const btnReset = document.getElementById('btnReset');

  let selectedFile = null;

  // Format File Size
  function formatBytes(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
  }

  // Format Currency
  function formatMoney(amount) {
    return new Intl.NumberFormat('es-AR', {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2
    }).format(amount);
  }

  // Format Number
  function formatNumber(num) {
    return new Intl.NumberFormat('es-AR').format(num);
  }

  // Handle Selected File
  function handleFile(file) {
    if (!file) return;

    if (!file.name.toLowerCase().endsWith('.xlsx')) {
      showError('Formato inválido. Por favor selecciona un archivo Excel (.xlsx).');
      return;
    }

    selectedFile = file;
    fileName.textContent = file.name;
    fileSize.textContent = formatBytes(file.size);

    // Auto-detect period from filename (e.g. MP 2025-11 (M).xlsx -> 2025-11)
    const match = file.name.match(/20\d{2}-\d{2}/);
    if (match) {
      periodoInput.value = match[0];
    } else {
      const now = new Date();
      const y = now.getFullYear();
      const m = String(now.getMonth() + 1).padStart(2, '0');
      periodoInput.value = `${y}-${m}`;
    }

    // Toggle view states
    dropzoneEmpty.style.display = 'none';
    filePreview.style.display = 'flex';
    formOptions.style.display = 'grid';
    btnSubmit.disabled = false;
    hideError();
  }

  // Reset file selection
  function resetFileSelection() {
    selectedFile = null;
    fileInput.value = '';
    dropzoneEmpty.style.display = 'block';
    filePreview.style.display = 'none';
    formOptions.style.display = 'none';
    btnSubmit.disabled = true;
  }

  // Error notifications
  function showError(msg) {
    errorMessage.textContent = msg;
    errorBanner.style.display = 'flex';
  }

  function hideError() {
    errorBanner.style.display = 'none';
  }

  // Drag and Drop Events
  ['dragenter', 'dragover'].forEach(eventName => {
    dropzone.addEventListener(eventName, (e) => {
      e.preventDefault();
      e.stopPropagation();
      dropzone.classList.add('dragover');
    });
  });

  ['dragleave', 'drop'].forEach(eventName => {
    dropzone.addEventListener(eventName, (e) => {
      e.preventDefault();
      e.stopPropagation();
      dropzone.classList.remove('dragover');
    });
  });

  dropzone.addEventListener('drop', (e) => {
    const dt = e.dataTransfer;
    const files = dt.files;
    if (files.length > 0) {
      handleFile(files[0]);
    }
  });

  fileInput.addEventListener('change', (e) => {
    if (e.target.files.length > 0) {
      handleFile(e.target.files[0]);
    }
  });

  btnRemoveFile.addEventListener('click', (e) => {
    e.stopPropagation();
    resetFileSelection();
  });

  btnCloseError.addEventListener('click', hideError);

  // Form Submit (AJAX)
  conciliarForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    if (!selectedFile) return;

    hideError();
    uploadSection.style.display = 'none';
    loadingSection.style.display = 'block';

    const formData = new FormData();
    formData.append('archivo', selectedFile);
    formData.append('periodo', periodoInput.value.trim());
    formData.append('hoja', hojaInput.value.trim() || 'sheet0');

    try {
      const response = await fetch('/api/conciliar', {
        method: 'POST',
        body: formData
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || 'Ocurrió un error al procesar el archivo.');
      }

      // Populate results
      renderResults(data);

    } catch (err) {
      loadingSection.style.display = 'none';
      uploadSection.style.display = 'block';
      showError(err.message || 'Error de conexión con el servidor.');
    }
  });

  // Render Results Card
  function renderResults(res) {
    loadingSection.style.display = 'none';
    resultsSection.style.display = 'block';

    const m = res.metricas;
    const isFull = m.cargos_pendientes === 0;

    resumenTitulo.textContent = `Período ${res.periodo}`;
    resumenSub.textContent = `Archivo procesado: ${res.nombre_archivo}`;

    // Circular metric & Badge
    porcentajeMetric.textContent = `${m.porcentaje_asociado}%`;
    if (isFull) {
      badgeEstado.textContent = '100% Conciliado';
      badgeEstado.className = 'badge-success';
      porcentajeMetric.parentElement.style.borderColor = 'var(--success)';
      porcentajeMetric.parentElement.style.boxShadow = '0 0 25px var(--success-glow)';
      
      calloutMessage.innerHTML = '<strong>¡Excelente!</strong> Todas las deducciones (SIRCUPA, SIRTAC, IDC y Gastos) fueron vinculadas a sus operaciones comerciales.';
    } else {
      badgeEstado.textContent = 'Revisión Pendiente';
      badgeEstado.className = 'badge-success badge-warning';
      porcentajeMetric.parentElement.style.borderColor = 'var(--amber)';
      porcentajeMetric.parentElement.style.boxShadow = '0 0 25px var(--amber-glow)';
      
      calloutMessage.innerHTML = `Se identificaron <strong>${m.cargos_pendientes} cargos sin asociar</strong> por un total de <strong>$ ${formatMoney(m.monto_pendiente)}</strong>. Podés auditarlos en la pestaña <strong>No Conciliados</strong> del Excel.`;
    }

    // KPI Numbers
    kpiMovimientos.textContent = formatNumber(m.movimientos_totales);
    kpiCargos.textContent = formatNumber(m.cargos_totales);
    kpiAsociados.textContent = formatNumber(m.cargos_asociados);
    kpiPendientes.textContent = formatNumber(m.cargos_pendientes);

    if (m.cargos_pendientes > 0) {
      kpiPendientesLabel.textContent = `$ ${formatMoney(m.monto_pendiente)}`;
    } else {
      kpiPendientesLabel.textContent = 'Cargos Pendientes';
    }

    // Download Button Link
    btnDownload.href = `/api/descargar/${res.descarga_token}`;
    btnDownloadLabel.textContent = `Descargar ${res.archivo_salida}`;
  }

  // Reset to Upload Another File
  btnReset.addEventListener('click', () => {
    resultsSection.style.display = 'none';
    uploadSection.style.display = 'block';
    resetFileSelection();
  });
});
