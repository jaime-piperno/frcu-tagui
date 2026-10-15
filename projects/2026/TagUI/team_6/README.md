# Automatización RPA: Conciliación de Mercado Pago

Proyecto de automatización para la conciliación de liquidaciones y ventas de **Mercado Pago**.
Lee el extracto descargado de Mercado Pago y reconstruye el importe bruto total de cada operación comercial (`MOV TOTAL`) a partir del importe neto y las deducciones impositivas y comisiones (**SIRCUPA, SIRTAC, IDC y Gastos**).

Genera un libro Excel resultante con:
- **Pestaña principal (`sheet0` / `TP`)**: Las **10 columnas oficiales** con el bruto comercial reconstruido (`MOV TOTAL`) y deducciones imputadas con precisión centavo a centavo.
- **Pestaña `Control y Cuadre`**: Matriz de balance contable que certifica la conservación exacta de fondos con **diferencia $0.00** entre lo leído en el extracto original, lo imputado en la hoja principal y lo derivado a no conciliados.
- **Pestaña `No Conciliados`**: Detalle analítico de cargos huérfanos o retenciones globales sin contraparte en el período, indicando hoja, fila y motivo.

---

## 🌐 Opción 1: Aplicación Web con Docker (Recomendada)

La forma más sencilla para usuarios finales. No requiere instalar Python ni configurar rutas:

### 1. Iniciar con Docker Compose:

```bash
docker compose up --build
```

*(En Windows podés hacer **doble clic en `iniciar.bat`** y se abrirá solo).*

### 2. Abrir en el navegador:

Navegá a **[http://localhost:8000](http://localhost:8000)**.

- **Arrastrá tu archivo Excel** (`MP YYYY-MM (M).xlsx`).
- El sistema detectará automáticamente el período.
- Presioná **"Iniciar Conciliación RPA"**.
- Visualizá las métricas en tiempo real (% asociado, montos pendientes, totales).
- Descargá el archivo conciliado final directamente a tu computadora.

Para detener el servidor: `docker compose down` (o doble clic en `detener.bat`).

---

## 💻 Opción 2: Servidor Web Local (sin Docker)

Si tenés Python instalado y preferís correr la interfaz web localmente:

```bash
# 1. Instalar dependencias
pip install -r requirements.txt

# 2. Iniciar el servidor web
python -m uvicorn app:app --host 127.0.0.1 --port 8000
```

Abrí [http://localhost:8000](http://localhost:8000) en tu navegador.

---

## ⚙️ Opción 3: Ejecución por Consola (CLI / Batch)

Para procesar archivos masivos por línea de comandos o scripts programados:

```bash
# Procesar archivo por defecto (diciembre):
python conciliar.py

# Procesar cualquier mes (el período se auto-detecta):
python conciliar.py --archivo "docs/MP 2025-09 (M).xlsx"
python conciliar.py --archivo "docs/MP 2025-10 (M).xlsx"
python conciliar.py --archivo "docs/MP 2025-11 (M).xlsx"
```

---

## 📁 Estructura del Proyecto

```text
Proyecto-RPA/
├── conciliar.py            # Motor principal de cruce y conciliación RPA
├── app.py                  # Servidor web FastAPI (endpoints /api/conciliar y /api/descargar)
├── Dockerfile              # Definición del contenedor Docker
├── docker-compose.yml      # Configuración de Docker Compose (puerto 8000)
├── iniciar.bat             # Script de arranque con 1 clic para Windows
├── detener.bat             # Script de detención para Windows
├── requirements.txt        # Dependencias (openpyxl, fastapi, uvicorn, python-multipart)
├── static/                 # Frontend Web (HTML5, Vanilla CSS moderno, JS)
│   ├── index.html          # Interfaz de usuario con Drag & Drop y KPIs
│   ├── style.css           # Estilos modernos con paleta cuidada y micro-animaciones
│   └── app.js              # Lógica de subida asíncrona, renderizado y descarga
├── docs/                   # Reportes originales de Mercado Pago (MP YYYY-MM (M).xlsx)
└── outputs/                # Reportes generados en modo consola (conciliacion_YYYY-MM.xlsx)
```

---

## 🔍 Reglas del Cruce Contable

1. **Lectura Segura:** Abre el Excel en modo solo lectura y corta exactamente al terminar la tabla oficial de Mercado Pago (omite notas o tablas de control pegadas al pie).
2. **Cruce por ID:** Asocia cada retención/comisión al movimiento principal mediante su `REFERENCE_ID`, distinguiendo operaciones regulares de anulaciones o devoluciones.
3. **Resolución de IDC Alfanuméricos:** Para cargos de IDC con códigos internos (ej: `0007eymbh3`), el algoritmo los vincula unívocamente mediante fecha y validación de la ecuación financiera (`neto + deducciones + IDC = base imponible`).
4. **Pestaña de No Conciliados:** Si un cargo no tiene contraparte en el extracto (ej. IDC globales de extracción), se lista en la pestaña `No Conciliados` con motivo e importe.
5. **Protección contra Bloqueos:** Si el archivo destino está abierto en Excel al generar el reporte, crea una copia fechada alternativa sin interrumpir el proceso.
6. **Control de Auditoría y Balance Cero ($0.00):** Verifica matemáticamente que $\text{Total Origen} = \text{Total Imputado} + \text{Total No Conciliados}$. En la pestaña **`Control y Cuadre`** se certifica la diferencia de \$0.00, la cobertura del 100% de los registros analizados y el cuadre de la ecuación de balance comercial.
