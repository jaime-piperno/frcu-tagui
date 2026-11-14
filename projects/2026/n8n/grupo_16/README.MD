# 📌 UTN FRCU – Tecnologías para la Automatización 2026

## 👥 Team
- **Team number:** 16
- **Members:**
  - Guido Mariano
  - Haffner Ignacio
  - Haffner Federico
  - Lares Danisa
  - Wulfsohn Yaco

---

## 🤖 Bot Description
- **Description:**
n8n workflow that automates the reconciliation of bank transfers against their PDF receipts. It extracts the embedded text of each receipt (no OCR needed), parses the date, amount, recipient and operation reference with regular expressions, and compares them against the real bank movements stored in a Google Sheet. Each receipt is classified as **Conciliada** (matched), **No encontrada** (not found) or **Requiere revisión** (needs manual review, when a key field could not be extracted). Results are appended to the `Resultado` sheet, the original PDF is archived in a `Procesados` subfolder so it is never processed twice, and a single consolidated summary email is sent via Gmail.

  The workflow has two entry points that share the same processing:
  - **Assisted mode (web form):** an operator opens the form, sees the bank movements registered in the sheet, uploads one or more PDFs and gets the status of each receipt on screen at the end.
  - **Scheduled mode (daily):** every day at 9:00 the workflow looks for new PDFs in the Google Drive input folder, processes them and moves them to `Procesados`.
- **Technology used:** n8n (open-source workflow automation) + Google Drive + Google Sheets + Gmail, with JavaScript Code nodes. Unlike classic RPA tools that drive the GUI, n8n connects directly to the services' APIs; the functional result is equivalent.

---

## 🎥 Demo Video
- **Demonstration:** [Watch the bot in action on Google Drive](https://drive.google.com/file/d/1KC6yveazvtX-hrT9J96biFciFHzMtvsM/view?usp=sharing)

---

## 🛠️ Usage Instructions

### Prerequisites
- Node.js **20.19 to 24.x** (LTS recommended).
- A Google account with access to Drive, Sheets and Gmail.
- Your own Google Cloud Console project with an OAuth2 client (when n8n runs locally it is not created automatically — see step 5).

### Installation
1. **Check Node.js**: run `node -v`. If it is missing or older than required, install the LTS version from [nodejs.org](https://nodejs.org).
2. **Start n8n**:
   ```bash
   npx n8n
   ```
   The first run downloads everything needed. Keep this terminal open while using the tool.
3. **Open the UI**: go to `http://localhost:5678` and create the local owner account the first time.
4. **Import the workflow**: in *Workflows → Import from File*, select `grupo_16_workflow.json`.
5. **Create the OAuth client in Google Cloud** ([console.cloud.google.com](https://console.cloud.google.com)):
   1. Create a new project.
   2. Configure the OAuth consent screen as **External** and add your own Google account under **Test users**.
   3. Create an OAuth client ID of type **Web application** with the redirect URI `http://localhost:5678/rest/oauth2-credential/callback`.
   4. Save the **Client ID** and **Client Secret**; they are used for the three credentials in the next step.
6. **Reconnect the credentials**: Google credentials are not exported with the workflow for security reasons. Create each one again from its node, paste the Client ID / Client Secret and click **Sign in with Google**:
   - Google Drive: `Buscar nuevos comprobantes`, `Descargar comprobante`, `Guardar en procesados`, `Mover a procesados`
   - Google Sheets: `Leer movimientos (vista)`, `Leer movimientos`, `Registrar Resultado`
   - Gmail: `Enviar Alerta`
7. **Enable the APIs**: in Google Cloud go to *APIs & Services → Enable APIs and Services* and enable **Google Drive API**, **Google Sheets API** and **Gmail API**. If one is missing, its node fails with a `403 Forbidden` error naming the API.
8. **Create the `Procesados` subfolder** inside the Google Drive folder used by the workflow. Every processed receipt is archived there.
9. **Point the workflow to your own folder and sheet**:
   - Drive input folder ID → `Buscar nuevos comprobantes`
   - `Procesados` subfolder ID → `Guardar en procesados` and `Mover a procesados`
   - Google Sheet ID → `Leer movimientos (vista)`, `Leer movimientos` and `Registrar Resultado`
   - Destination email → `Enviar Alerta`

   The sheet must keep the original structure:

   | Sheet | Columns |
   |---|---|
   | `Movimientos` | Fecha, Monto, Descripción, Referencia |
   | `Resultado` | Fecha, Monto, Destinatario, Referencia, Estado |

   > ⚠️ In `Movimientos`, **Fecha** must be text `dd/mm/yyyy`, **Monto** a number without `$`, and **Referencia** text. With any other format every receipt ends up as *No encontrada*. To use the sample sheet included in the ZIP, upload it to Drive and open it with Google Sheets.
10. **Check the receipt has real text**: before testing, make sure the PDF text is selectable with the mouse in a PDF reader. Scanned images or screenshots converted to PDF are not supported (no OCR).
11. **Test manually**: run the workflow once with **Execute workflow** and check every node.
    - *Form mode*: open the `Formulario de carga` node and use its **Test URL**: the movements are shown, you upload one or more receipts and the result appears on screen.
    - *Scheduled mode*: copy the sample PDFs from the ZIP into the input folder and execute the workflow.
12. **Activate the workflow**: from then on it runs every day at the configured time, and the form is available at its **Production URL** (in the `Formulario de carga` node), which is the one shared with operators. To run at 9:00 Argentina time, set *Settings → Timezone → `America/Argentina/Buenos_Aires`*.

### Expected output
- One row per receipt in the `Resultado` sheet with its `Estado`.
- Each PDF archived in `Procesados` (moved from the input folder, or uploaded directly when it came from the form).
- A single summary email per run with the totals (matched / not found / needs review) and the detail of each receipt.
- In form mode, a final screen showing the operator the status of each receipt.

### 🔄 Workflow overview
In the n8n canvas the workflow is split into four colored blocks (**Obtención, Extracción, Comparación, Resultado**), and every Code node has comments explaining what it does. Both entry points join at `Extraer texto del PDF`; from there `Identificar origen` tags each receipt with its origin (`formulario` or `diario`), which later nodes use to decide whether to upload or move the PDF and whether to show the final screen.

| Node | Type | What it does |
|---|---|---|
| Formulario de carga | Form Trigger | Start of assisted mode. Optionally asks for the operator's name. |
| Leer movimientos (vista) | Google Sheets | Reads the `Movimientos` sheet to show it to the operator. |
| Armar tabla de movimientos | Code | Turns the movements into an HTML table. |
| Subir comprobantes | Form | Form step 2: shows the table and receives the PDFs. |
| Separar comprobantes | Code | Splits the uploaded PDFs (one single item) into one item per file. |
| Ejecucion diaria | Schedule Trigger | Start of scheduled mode, every day at 9:00. |
| Buscar nuevos comprobantes | Google Drive | Lists the `.pdf` files in the input folder. If there are none, the flow ends. |
| Descargar comprobante | Google Drive | Downloads each PDF found. |
| Extraer texto del PDF | Extract from File | Gets the embedded PDF text (no OCR). Both modes join here. |
| Identificar origen | Code | Adds the origin, file name and Drive ID / original PDF to each text. |
| Leer movimientos | Google Sheets | Reads the `Movimientos` sheet once for the comparison. |
| Normalizar y Comparar Datos | Code | Extracts date, amount, recipient and reference with regex and looks for a movement with the same date, amount and reference. Sets the `Estado`. **This is the node to change if the receipt format changes.** |
| ¿Vino del formulario? | If | Splits receipts by origin. |
| Guardar en procesados | Google Drive | (form) Uploads the PDF to `Procesados`. |
| Mover a procesados | Google Drive | (daily) Moves the PDF from the input folder to `Procesados`. |
| Registrar Resultado | Google Sheets | Appends one row per receipt to the `Resultado` sheet. |
| Armar resumen del mail | Code | Builds the email summary and the HTML result screen. |
| Enviar Alerta | Gmail | Sends a single email with the run summary. |
| ¿Mostrar resultado? | If | Continues to the final screen only when the origin is the form. |
| Mostrar resultado | Form (Completion) | Shows the operator the status of each receipt. |

To add a third entry point (e.g. Telegram), connect it to `Extraer texto del PDF` and add its case in `Identificar origen`.

---

## 📝 Additional Notes

- **Current limitations of the bot:**
  - Field recognition depends on the layout of the reference receipt (the labels `CVU` and `N.° de operación` must be on identifiable lines; the recipient is taken from the line after `CVU`). Receipts from other banks or wallets, or a format change, require adjusting the extraction code.
  - Only PDFs with native embedded text are supported; scanned images or screenshots converted to PDF cannot be read (no OCR).
  - Reconciliation requires an exact match of date, amount and reference; there is no tolerance for small differences.
  - In scheduled mode, receipts must be uploaded to the Drive input folder before the run. The form requires the workflow to be active to be available.
  - Nothing prevents uploading the same receipt twice from the form (no duplicate control).

- **Possible improvements (for Stage 2):**
  - Support more than one receipt format by generalizing the recipient/reference extraction.
  - Organize archived files by result (e.g. `Conciliados` vs. a review folder for *No encontrada* and *Requiere revisión*).
  - Tolerance in the comparison (e.g. up to $1 in amount, 2 days in date, partial reference), sending those cases to *Requiere revisión* with a `Motivo` column.
  - Duplicate control: check whether the reference already exists in `Resultado` before appending and warn the operator.
  - OCR for receipts received as JPG/PNG or screenshots.
  - Automatic intake through a Telegram bot that receives PDFs/images and feeds them into the reconciliation flow.

---

## 🔄 Stage 2 – Improvement

- **Team number:** 8
- **Members:**
  - Muga Isaías
  - Poerio Santiago
  - Riolfo Franco
  - Rojas Federico
  - Venturino Diego

The sections above describe the Stage 1 bot and are kept as they were written. This section supersedes them.

### 🚀 Improvement Description

- **What was improved:**
  Two changes to the Stage 1 workflow, both taken from the *Possible improvements* list above. The improved version replaces `grupo_16_workflow.json` in this folder.

  1. **Duplicate control by reference.** A receipt whose `Referencia` was already recorded is classified as `Duplicado` and is not appended to `Resultado`.
     - `Leer resultado` reads the `Resultado` sheet once per run (`executeOnce`, and `alwaysOutputData` so an empty sheet does not stop the flow).
     - `Detectar duplicados` compares the normalized reference against the rows already stored in `Resultado` and against the references seen earlier in the same batch, so the same PDF uploaded twice in one submit is also caught. Duplicates keep their binary, `driveId` and `origen` for the archive step.
     - `¿Es nuevo?` lets only the non-duplicates through to `Registrar Resultado`. Its false branch is left unconnected on purpose.

  2. **Archive by result.** Each PDF is stored in the folder that matches its `Estado`: `Conciliados`, `No encontrados`, `Requiere revisión` or `Duplicados`.
     - `Asignar carpeta destino` runs right after `Detectar duplicados`, adds `carpetaDestino` with the folder ID that corresponds to that item's status, and forwards the binary. Unknown statuses default to `Requiere revisión`.
     - `Guardar en carpeta por estado` and `Mover a carpeta por estado` read `{{ $json.carpetaDestino }}`, so a single Drive node per path archives any number of PDFs in different folders, without a Switch or one branch per status.

  The summary email and the final screen are now built from `Detectar duplicados` instead of `Registrar Resultado`, so a run made only of duplicates still sends the email and shows the screen. The summary also gained a `Duplicados` counter, a blue badge and a footer line stating that duplicates are not written to the sheet.

- **Why:**
  In Stage 1 nothing prevented the same receipt from being appended twice, and every processed PDF ended in a single `Procesados` folder. Uploading a receipt by mistake, or leaving a file in the input folder for a second run, produced repeated rows that altered the totals and had to be cleaned by hand. Finding the PDFs that needed review meant comparing the sheet against a folder full of already reconciled receipts. The two changes remove both manual clean-ups without touching the extraction or the comparison logic.

### 🛠️ Updated Usage Instructions

Only these steps change with respect to Stage 1:

1. **Import `grupo_16_workflow.json`**, which already contains the Stage 2 changes. Credentials are still not exported: create the OAuth client and reconnect Google Drive, Google Sheets and Gmail as described in steps 5–7 above. The Google Sheets credential is now needed by **four** nodes, the new one being `Leer resultado` (`Leer movimientos (vista)`, `Leer movimientos`, `Leer resultado`, `Registrar Resultado`).
2. **Create four folders** inside the `Procesados` folder: `Conciliados`, `No encontrados`, `Requiere revisión` and `Duplicados`. The workflow does not create them.
3. **Copy their IDs** into the `CARPETAS` map at the top of the `Asignar carpeta destino` Code node. That map is the only place where the folder IDs are stored.
4. **Point the nodes to your own Drive and sheet.** This supersedes steps 8 and 9 of Stage 1, because `Guardar en procesados` and `Mover a procesados` no longer exist in this version:
   - Drive input folder ID --> `Buscar nuevos comprobantes`
   - the four folder IDs --> the `CARPETAS` map of `Asignar carpeta destino`. There is no single `Procesados` destination anymore.
   - Google Sheet ID --> `Leer movimientos (vista)`, `Leer movimientos`, `Leer resultado` and `Registrar Resultado`
   - Destination email --> `Enviar Alerta`
5. **Keep the `Referencia` header** in the `Resultado` sheet: it is the column used to detect duplicates. If it is renamed, `Detectar duplicados` stops with an explicit error instead of running without duplicate control. A `Resultado` sheet with only the header row is valid.
6. Everything else stays as in Stage 1: OAuth client, APIs, `Movimientos`/`Resultado` structure, input folder, form, schedule and destination email.

The three sample receipts are now included in `Comprobantes/`, so the repository is enough to reproduce the tests:

| PDF | Extracted data | First run | Second run |
|---|---|---|---|
| `comprobante_prueba_1_conciliado.pdf` | 24/09/2026 · $7,200 · ref 184000111222 | `Conciliada` | `Duplicado` |
| `comprobante_prueba_2_no_encontrada.pdf` | 20/09/2026 · $4,850 · ref 190234455667 | `No encontrada` | `Duplicado` |
| `comprobante_prueba_3_requiere_revision.pdf` | 25/09/2026 · amount not extracted (no `$`) · ref 190555667788 | `Requiere revisión` | `Duplicado` |

In the first run each PDF lands in the folder of its status and one row per receipt is appended. In a second run all three are `Duplicado`, no row is appended and the PDFs go to `Duplicados`.

### 📝 Additional Notes

- Receipts without a readable reference are never treated as duplicates, they keep their status and stay in `Requiere revisión` for manual analysis.
- `Requiere revisión` and `No encontrada` receipts that do have a reference count as a precedent. To process one of them again, delete its row from `Resultado`.
- The duplicate check is per reference, not per file, and it also covers the same PDF uploaded twice in the same submit.
- Remaining limitations are the same as Stage 1: exact match of date, amount and reference, positional parser, no OCR. The four folders are not created by the workflow.
- **Demonstration:** [Watch the improved bot on Google Drive](https://drive.google.com/file/d/1t1Ch9BuBBv2RGd5G3eCxrcN4ITak8V9b/view?usp=sharing)
