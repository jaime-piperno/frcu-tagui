# 🔬 Paper News - Automated Scientific Papers Processing System

📖 **Available in other languages:** **[English](README.md)** | [Español](README.es.md)

## Table of Contents
- [📋 General Description](#-general-description)
- [🏗️ System Architecture](#️-system-architecture)
- [🚀 System Components](#-system-components)
- [⚙️ System Requirements](#️-system-requirements)
- [🔐 Critical Initial Setup](#-critical-initial-setup)
- [📊 Categories Configuration](#-categories-configuration)
- [📱 WhatsApp Configuration](#-whatsapp-configuration)
- [🔄 Workflow](#-workflow)
- [🐧 Linux Execution](#-linux-execution)
  - [Mode 1: HTML Portal](#mode-1-html-portal-)
  - [Mode 2: WhatsApp](#mode-2-whatsapp-)
  - [Manual Execution by Components](#manual-execution-by-components)
  - [Parameter Customization](#parameter-customization)
- [🪟 Windows Execution](#-windows-execution)
  - [Available Files](#available-files)
  - [Critical Path Configuration](#critical-path-configuration)
  - [Mode 1: HTML Portal](#mode-1-html-portal--1)
  - [Mode 2: WhatsApp](#mode-2-whatsapp--1)
- [🛠️ Troubleshooting](#️-troubleshooting)
- [🔧 Advanced Customization](#-advanced-customization)
- [📊 Data Formats](#-data-formats)
- [🎓 Academic Information](#-academic-information)
- [🆘 Support and Maintenance](#-support-and-maintenance)

## 📋 General Description

Paper News is an automated system that extracts, processes, and distributes scientific papers from arXiv using TagUI for web automation and DeepSeek AI for intelligent content processing. The system can generate both interactive web portals and send summaries directly to WhatsApp.

## 🏗️ System Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   arXiv.org     │───▶│   AutoPapper     │───▶│ generar_prompts │
│  (Extraction)   │    │    (.tag)        │    │     (.py)       │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                                         │
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│     WhatsApp    │◀───│  AIOverview.tag  │◀───│   DeepSeek AI   │
│  (Distribution) │    │   (Processing)   │    │  (Processing)   │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                │
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   HTML Portal   │◀───│  generar_portal  │◀───│   AICSV.tag     │
│   (Web Portal)  │    │     (.py)        │    │  (Processing)   │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

## 🚀 System Components

### 📁 File Structure
```
Papper-News/
├── AutoPapper.tag              # Papers extraction from arXiv
├── generar_prompts.py          # AI prompt generation
├── AIOverview.tag              # AI processing → WhatsApp
├── AICSV.tag                   # AI processing → CSV
├── generar_portal.py           # HTML portal generation
├── PapperNewsHTML.sh           # Complete script → Web Portal
├── PapperNewsWhatsapp.sh       # Complete script → WhatsApp
├── PapperNewsHTML.bat          # Windows script → Web Portal
├── PapperNewsWhatsapp.bat      # Windows script → WhatsApp
├── IN/
│   └── xpaths.csv             # arXiv categories configuration
└── OUT/                       # Generated files directory
    ├── AutoPapper.csv         # Extracted papers (temporary)
    ├── Prompts.csv            # Generated prompts (temporary)
    ├── ProcessedPapers.csv    # AI-processed papers
    └── portal_noticias.html   # Generated web portal
```

### 🔧 Main Components

#### 1. **AutoPapper.tag** - Papers Extractor
- Navigates arXiv based on configured categories
- Extracts title, description, URL, and category from each paper
- Generates `OUT/AutoPapper.csv` with all found papers

#### 2. **generar_prompts.py** - Prompt Generator
- Processes the extracted papers CSV
- Groups papers into batches (default: 10 per batch)
- Generates optimized prompts for DeepSeek AI
- Includes JSON formatting and categorization instructions

#### 3. **AIOverview.tag** - AI Processor → WhatsApp
- Sends prompts to DeepSeek AI for processing
- Extracts JSON responses with titles, summaries, and categories
- Automatically sends to configured WhatsApp group
- Processes multiple batches sequentially

#### 4. **AICSV.tag** - AI Processor → CSV
- Similar to AIOverview but saves results to CSV
- Generates `OUT/ProcessedPapers.csv` with processed papers
- Includes fields: title, category, summary, key points, link, date

#### 5. **generar_portal.py** - Portal Generator
- Converts processed CSV into interactive HTML portal
- Modern YouTube Music-style design
- Automatic categorization and paper counter
- Responsive design with visual effects

## ⚙️ System Requirements

### Required Software
- **Python 3.7+** with pip
- **TagUI** (latest version)
- **Google Chrome**
- **Stable Internet Connection**

### Python Dependencies
```bash
pip install pandas requests beautifulsoup4
```

### Required Accounts
- **DeepSeek AI**: Free account at [chat.deepseek.com](https://chat.deepseek.com/)
- **WhatsApp Web**: Access to target group

## 🔐 Critical Initial Setup

> **⚠️ IMPORTANT**: TagUI uses a separate Chrome profile from the user's normal browser.

### Step 1: Configure TagUI Profile
Before running any script, it is **mandatory** to configure TagUI's Chrome profile:

```tagui
// Open TagUI with extended wait time
https://google.com 

wait 1000
```

### Step 2: Service Registration
During the wait time (1000 seconds = ~16 minutes):

1. **Configure DeepSeek AI**:
   - Navigate to `https://chat.deepseek.com/`
   - Create account or log in
   - Keep session active

2. **Configure WhatsApp Web**:
   - Navigate to `https://web.whatsapp.com/`
   - Scan QR code with phone
   - Verify access to target group
   - Keep session active

3. **Verify Configurations**:
   - Confirm both services work correctly
   - Test sending a test message on WhatsApp
   - Verify DeepSeek AI response

> **💡 Tip**: It's recommended to keep these sessions active to avoid constant reconfiguration.

## 📊 Categories Configuration

### `IN/xpaths.csv` File
Configure arXiv categories to extract:

```csv
xpath, category
//*[@id="cs.SE"], "Software Engineering"
//*[@id="cs.CE"], "Engineering, Finance, and Science"
//*[@id="cs.AI"], "Artificial Intelligence"
//*[@id="cs.LG"], "Machine Learning"
```

**To change categories:** Inspect arXiv category buttons and extract their XPath using browser developer tools.

## 📱 WhatsApp Configuration

### Change Target Group
Edit `AIOverview.tag`, line 181:
```tagui
click Papper News 9129324123
```

Change to desired group name:
```tagui
click My Scientific Group
```

## 🔄 Workflow

### General Process:
1. **Extraction**: AutoPapper navigates arXiv and extracts new papers
2. **Preparation**: generar_prompts groups papers into batches for AI
3. **Processing**: AI analyzes and generates structured summaries
4. **Distribution**: Send to WhatsApp or generate web portal
5. **Cleanup**: Remove temporary files

### Processed Data:
- **Input**: Raw papers from arXiv
- **Processing**: Translated titles, categories, summaries, key points
- **Output**: Structured content with emojis and optimized formatting

---

## 🐧 Linux Execution

### Mode 1: HTML Portal 🌐
Generates an interactive web portal with all processed papers:

```bash
./PapperNewsHTML.sh
```

**Internal Process:**
1. Executes `AutoPapper.tag` to extract papers
2. Generates prompts with `generar_prompts.py`
3. Processes with AI using `AICSV.tag`
4. Creates HTML portal with `generar_portal.py`
5. Cleans temporary files

**Result:**
- `portal_noticias.html` - Interactive web portal

### Mode 2: WhatsApp 📱
Sends papers directly to configured WhatsApp group:

```bash
./PapperNewsWhatsapp.sh
```

**Internal Process:**
1. Executes `AutoPapper.tag` to extract papers
2. Generates prompts with `generar_prompts.py`
3. Processes with AI using `AIOverview.tag`
4. Automatically sends to WhatsApp Web
5. Cleans temporary files

**Result:**
- Messages sent to configured WhatsApp group

### Manual Execution by Components

#### Papers Extraction:
```bash
OPENSSL_CONF="" tagui AutoPapper.tag IN/xpaths.csv -t
```

#### Prompt Generation:
```bash
python generar_prompts.py OUT/AutoPapper.csv OUT/Prompts.csv
```

#### AI Processing → CSV:
```bash
OPENSSL_CONF="" tagui AICSV.tag -t
```

#### AI Processing → WhatsApp:
```bash
OPENSSL_CONF="" tagui AIOverview.tag -t
```

#### Portal Generation:
```bash
python generar_portal.py OUT/ProcessedPapers.csv portal_noticias.html
```

### Parameter Customization

#### Change Batch Size:
```bash
python generar_prompts.py OUT/AutoPapper.csv OUT/Prompts.csv --batch-size 15
```

#### Adjust Lines per Summary:
```bash
python generar_prompts.py OUT/AutoPapper.csv OUT/Prompts.csv --max-lines 5
```

### Execution Permissions
```bash
chmod +x PapperNewsHTML.sh
chmod +x PapperNewsWhatsapp.sh
```

### Environment Variables
```bash
# Clear OpenSSL configuration to avoid conflicts
export OPENSSL_CONF=""
```

---

## 🪟 Windows Execution

### Available Files
- `PapperNewsHTML.bat` - Complete script → Web Portal
- `PapperNewsWhatsapp.bat` - Complete script → WhatsApp

### Critical Path Configuration

> **⚠️ IMPORTANT**: If you experience file not found errors in Windows, review and adjust these paths according to your system:

| File | Line | Current Path (Linux) | Windows Path | Description |
|------|------|---------------------|--------------|-------------|
| `AutoPapper.tag` | 2 | `OUT/AutoPapper.csv` | `OUT\AutoPapper.csv` | Papers output file |
| `AutoPapper.tag` | 68 | `OUT/AutoPapper.csv` | `OUT\AutoPapper.csv` | Papers writing |
| `AIOverview.tag` | 2 | `OUT/Prompts.csv` | `OUT\Prompts.csv` | Prompts loading |
| `AICSV.tag` | 2 | `OUT/ProcessedPapers.csv` | `OUT\ProcessedPapers.csv` | Output CSV headers |
| `AICSV.tag` | 5 | `OUT/Prompts.csv` | `OUT\Prompts.csv` | Prompts loading |
| `AICSV.tag` | 157 | `OUT/ProcessedPapers.csv` | `OUT\ProcessedPapers.csv` | Processed papers writing |

### Mode 1: HTML Portal 🌐
```cmd
PapperNewsHTML.bat
```

**Process:**
1. Extracts papers from arXiv with `AutoPapper.tag`
2. Generates prompts with `generar_prompts.py`
3. Processes with AI using `AICSV.tag`
4. Creates HTML portal with `generar_portal.py`
5. Cleans temporary files

**Result:**
- `portal_noticias.html` - Interactive web portal

### Mode 2: WhatsApp 📱
```cmd
PapperNewsWhatsapp.bat
```

**Process:**
1. Extracts papers from arXiv with `AutoPapper.tag`
2. Generates prompts with `generar_prompts.py`
3. Processes with AI using `AIOverview.tag`
4. Automatically sends to WhatsApp Web
5. Cleans temporary files

**Result:**
- Messages sent to configured WhatsApp group

### Important Notes for Windows
- The `.tag` and `.py` files are the same as in Linux
- Only path separators change (`/` → `\`)
- Initial configuration with `tagui -> "https://google.com -> wait 1000"` is **equally important**
- Ensure Python and TagUI are in system PATH

---

## 🛠️ Troubleshooting

### Error: "TagUI not recognized"
```bash
# Reinstall or update TagUI if necessary
tagui update
```

## 🔧 Advanced Customization

### Modify AI Prompts
Edit `generar_prompts.py`, function `build_prompt_for_batch()`:
- Change format instructions
- Adjust summary length
- Modify JSON structure

### Customize HTML Portal
Edit `generar_portal.py`:
- Change visual theme
- Modify category structure
- Adjust responsiveness

### Configure Wait Times
In `.tag` files, adjust `wait` lines:
```tagui
wait 120  # Wait 2 minutes for AI response
wait 7    # Wait 7 seconds to load WhatsApp
```

## 📊 Data Formats

### Extracted Papers CSV (`AutoPapper.csv`):
```csv
name,Description,URL,Category
"Paper title","Complete description","https://arxiv.org/abs/...","Computer Science"
```

### Processed Papers CSV (`ProcessedPapers.csv`):
```csv
titulo,categoria,resumen,puntos_clave,enlace,fecha_procesado
"🤖 Translated title","📂 Category","📝 Summary","🎯 Key points","🔗 URL","2025-09-24"
```

### AI JSON Format:
```json
{
  "papers": [
    {
      "titulo_español": "🤖 Title with emoji",
      "categoria": "📂 Category",
      "resumen": "📝 Summary in maximum 3 lines",
      "puntos_clave": "🎯 Important aspects",
      "enlace": "🔗 Paper URL"
    }
  ]
}
```

---

## 🎓 Academic Information

### Project Background
This project was developed for the **"Tecnologías para la Automatización"** (Automation Technologies) course at **Universidad Tecnológica Nacional, Facultad Regional Concepción del Uruguay** (UTN FRCU), as part of the **Ingeniería en Sistemas de Información** (Information Systems Engineering) degree program.

### Development Team - Group 11 (2025)
- **Leal, Pablo Valentín**
- **Martínez, Ignacio Gabriel** 
- **Moreyra, Omar Sebastián**
- **Schultheis, Valentín**
- **Fraisinet, Máximo Exequiel**

### 📄 License & Educational Purpose
This project is released under the **Unlicense** to ensure maximum accessibility for educational purposes. We encourage:

- ✅ **Students** from UTN FRCU or any academic institution
- ✅ **Researchers** interested in automation technologies
- ✅ **Developers** seeking to learn web automation and AI integration
- ✅ **Anyone** interested in scientific paper processing systems

**Feel free to use, modify, and distribute this code for learning, teaching, or implementing similar functionality.**

### 🏛️ Institution Information
- **University**: Universidad Tecnológica Nacional (UTN)
- **Faculty**: Facultad Regional Concepción del Uruguay (FRCU)
- **Program**: Ingeniería en Sistemas de Información
- **Course**: Tecnologías para la Automatización
- **Academic Year**: 2025

---

## 🆘 Support and Maintenance

### Logs and Debugging
- TagUI generates automatic logs during execution
- Check files in `OUT/` for debugging

### Updates
```bash
# Update TagUI
tagui update

# Update Python dependencies
pip install --upgrade pandas requests beautifulsoup4
```