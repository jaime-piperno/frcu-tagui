# 🔬 Paper News - Sistema Automatizado de Procesamiento de Papers Científicos

📖 **Available in other languages:** [English](README.md) | **[Español](README.es.md)**

## Índice de Contenidos
- [📋 Descripción General](#-descripción-general)
- [🏗️ Arquitectura del Sistema](#️-arquitectura-del-sistema)
- [🚀 Componentes del Sistema](#-componentes-del-sistema)
- [⚙️ Requisitos del Sistema](#️-requisitos-del-sistema)
- [🔐 Configuración Inicial Crítica](#-configuración-inicial-crítica)
- [📊 Configuración de Categorías](#-configuración-de-categorías)
- [📱 Configuración de WhatsApp](#-configuración-de-whatsapp)
- [🔄 Flujo de Trabajo](#-flujo-de-trabajo)
- [🐧 Ejecución en Linux](#-ejecución-en-linux)
  - [Modo 1: Portal HTML](#modo-1-portal-html-)
  - [Modo 2: WhatsApp](#modo-2-whatsapp-)
  - [Ejecución Manual por Componentes](#ejecución-manual-por-componentes)
  - [Personalización de Parámetros](#personalización-de-parámetros)
- [🪟 Ejecución en Windows](#-ejecución-en-windows)
  - [Archivos Disponibles](#archivos-disponibles)
  - [Configuración de Rutas Críticas](#configuración-de-rutas-críticas)
  - [Modo 1: Portal HTML](#modo-1-portal-html--1)
  - [Modo 2: WhatsApp](#modo-2-whatsapp--1)
- [🛠️ Solución de Problemas](#️-solución-de-problemas)
- [🔧 Personalización Avanzada](#-personalización-avanzada)
- [📊 Formato de Datos](#-formato-de-datos)
- [🎓 Información Académica](#-información-académica)
- [🆘 Soporte y Mantenimiento](#-soporte-y-mantenimiento)

## 📋 Descripción General

Paper News es un sistema automatizado que extrae, procesa y distribuye papers científicos desde arXiv utilizando TagUI para automatización web y DeepSeek AI para procesamiento inteligente de contenido. El sistema puede generar tanto portales web interactivos como enviar resúmenes directamente a WhatsApp.

## 🏗️ Arquitectura del Sistema

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   arXiv.org     │───▶│   AutoPapper     │───▶│ generar_prompts │
│ (Extracción)    │    │    (.tag)        │    │     (.py)       │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                                         │
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│     WhatsApp    │◀───│  AIOverview.tag  │◀───│   DeepSeek AI   │
│   (Distribución)│    │   (Procesamiento)│    │ (Procesamiento) │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                │
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Portal HTML   │◀───│  generar_portal  │◀───│   AICSV.tag     │
│   (Portal Web)  │    │     (.py)        │    │ (Procesamiento) │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

## 🚀 Componentes del Sistema

### 📁 Estructura de Archivos
```
Papper-News/
├── AutoPapper.tag              # Extracción de papers desde arXiv
├── generar_prompts.py          # Generación de prompts para IA
├── AIOverview.tag              # Procesamiento IA → WhatsApp
├── AICSV.tag                   # Procesamiento IA → CSV
├── generar_portal.py           # Generación de portal HTML
├── PapperNewsHTML.sh           # Script completo → Portal Web
├── PapperNewsWhatsapp.sh       # Script completo → WhatsApp
├── IN/
│   └── xpaths.csv             # Configuración de categorías arXiv
└── OUT/                       # Directorio de archivos generados
    ├── AutoPapper.csv         # Papers extraídos (temporal)
    ├── Prompts.csv            # Prompts generados (temporal)
    ├── ProcessedPapers.csv    # Papers procesados por IA
    └── portal_noticias.html   # Portal web generado
```

### 🔧 Componentes Principales

#### 1. **AutoPapper.tag** - Extractor de Papers
- Navega por arXiv según categorías configuradas
- Extrae título, descripción, URL y categoría de cada paper
- Genera `OUT/AutoPapper.csv` con todos los papers encontrados

#### 2. **generar_prompts.py** - Generador de Prompts
- Procesa el CSV de papers extraídos
- Agrupa papers en lotes (default: 10 por lote)
- Genera prompts optimizados para DeepSeek AI
- Incluye instrucciones de formato JSON y categorización

#### 3. **AIOverview.tag** - Procesador IA → WhatsApp
- Envía prompts a DeepSeek AI para procesamiento
- Extrae respuestas JSON con títulos, resúmenes y categorías
- Envía automáticamente a grupo de WhatsApp configurado
- Procesa múltiples lotes secuencialmente

#### 4. **AICSV.tag** - Procesador IA → CSV
- Similar a AIOverview pero guarda resultados en CSV
- Genera `OUT/ProcessedPapers.csv` con papers procesados
- Incluye campos: título, categoría, resumen, puntos clave, enlace, fecha

#### 5. **generar_portal.py** - Generador de Portal
- Convierte CSV procesado en portal HTML interactivo
- Diseño moderno estilo YouTube Music
- Categorización automática y contador de papers
- Responsive design con efectos visuales

## ⚙️ Requisitos del Sistema

### Software Necesario
- **Python 3.7+** con pip
- **TagUI** (última versión)
- **Google Chrome**
- **Conexión a Internet** estable

### Dependencias Python
```bash
pip install pandas requests beautifulsoup4
```

### Cuentas Requeridas
- **DeepSeek AI**: Cuenta gratuita en [chat.deepseek.com](https://chat.deepseek.com/)
- **WhatsApp Web**: Acceso al grupo de destino (Usted lo puede cambiar en la linea 181 de AIOverview.tag por defecto está con el nombre "Papper News 9129324123").

## 🔐 Configuración Inicial Crítica

> **⚠️ IMPORTANTE**: TagUI utiliza un perfil de Chrome separado del navegador normal del usuario.

### Paso 1: Configurar Perfil TagUI
Antes de ejecutar cualquier script, es **obligatorio** configurar el perfil de Chrome de TagUI:

```tagui
// Abrir TagUI con tiempo de espera extendido
https://google.com 

wait 1000
```

### Paso 2: Registro en Servicios
Durante el tiempo de espera (1000 segundos = ~16 minutos):

1. **Configurar DeepSeek AI**:
   - Navegar a `https://chat.deepseek.com/`
   - Crear cuenta o iniciar sesión
   - Mantener la sesión activa

2. **Configurar WhatsApp Web**:
   - Navegar a `https://web.whatsapp.com/`
   - Escanear código QR con teléfono
   - Verificar acceso al grupo objetivo
   - Mantener sesión activa

3. **Verificar Configuraciones**:
   - Confirmar que ambos servicios funcionan correctamente
   - Probar envío de mensaje de prueba en WhatsApp
   - Verificar respuesta de DeepSeek AI

> **💡 Tip**: Es recomendable mantener estas sesiones activas para evitar reconfiguración constante.

## 📊 Configuración de Categorías

### Archivo `IN/xpaths.csv`
Configura las categorías de arXiv a extraer:

```csv
xpath, category
//*[@id="cs.SE"], "Software Engineering"
//*[@id="cs.CE"], "Engineering, Finance, and Science"
//*[@id="cs.AI"], "Artificial Intelligence"
//*[@id="cs.LG"], "Machine Learning"
```

Para cambiar las categorias puede ir a la página arXiv y inspeccionar la web, para copiar el Xpath de la categoría que usted desee y pegarlo en el archivo IN/xpath.csv junto con el nombre de la categoria.

## 📱 Configuración de WhatsApp

### Cambiar Grupo de Destino
Editar `AIOverview.tag`, línea:
```tagui
click Papper News 9129324123
```

Cambiar por el nombre del grupo deseado:
```tagui
click Mi Grupo Científico
```

## 🔄 Flujo de Trabajo

### Proceso General:
1. **Extracción**: AutoPapper navega arXiv y extrae papers nuevos
2. **Preparación**: generar_prompts agrupa papers en lotes para IA
3. **Procesamiento**: IA analiza y genera resúmenes estructurados
4. **Distribución**: Envío a WhatsApp o generación de portal web
5. **Limpieza**: Eliminación de archivos temporales

### Datos Procesados:
- **Entrada**: Papers raw desde arXiv
- **Procesamiento**: Títulos traducidos, categorías, resúmenes, puntos clave
- **Salida**: Contenido estructurado con emojis y formato optimizado

---

## 🐧 Ejecución en Linux

### Modo 1: Portal HTML 🌐
Genera un portal web interactivo con todos los papers procesados:

```bash
./PapperNewsHTML.sh
```

**Proceso interno:**
1. Ejecuta `AutoPapper.tag` para extraer papers
2. Genera prompts con `generar_prompts.py`
3. Procesa con IA usando `AICSV.tag`
4. Crea portal HTML con `generar_portal.py`
5. Limpia archivos temporales

**Resultado:**
- `portal_noticias.html` - Portal web interactivo

### Modo 2: WhatsApp 📱
Envía papers directamente al grupo de WhatsApp configurado:

```bash
./PapperNewsWhatsapp.sh
```

**Proceso interno:**
1. Ejecuta `AutoPapper.tag` para extraer papers
2. Genera prompts con `generar_prompts.py`  
3. Procesa con IA usando `AIOverview.tag`
4. Envía automáticamente a WhatsApp Web
5. Limpia archivos temporales

**Resultado:**
- Mensajes enviados al grupo WhatsApp configurado

### Ejecución Manual por Componentes

#### Extracción de Papers:
```bash
OPENSSL_CONF="" tagui AutoPapper.tag IN/xpaths.csv -t
```

#### Generación de Prompts:
```bash
python generar_prompts.py OUT/AutoPapper.csv OUT/Prompts.csv
```

#### Procesamiento IA → CSV:
```bash
OPENSSL_CONF="" tagui AICSV.tag -t
```

#### Procesamiento IA → WhatsApp:
```bash
OPENSSL_CONF="" tagui AIOverview.tag -t
```

#### Generación de Portal:
```bash
python generar_portal.py OUT/ProcessedPapers.csv portal_noticias.html
```

### Personalización de Parámetros

#### Cambiar Tamaño de Lotes:
```bash
python generar_prompts.py OUT/AutoPapper.csv OUT/Prompts.csv --batch-size 15
```

#### Ajustar Líneas por Resumen:
```bash
python generar_prompts.py OUT/AutoPapper.csv OUT/Prompts.csv --max-lines 5
```

### Permisos de Ejecución
```bash
chmod +x PapperNewsHTML.sh
chmod +x PapperNewsWhatsapp.sh
```

### Variables de Entorno
```bash
# Limpiar configuración OpenSSL para evitar conflictos
export OPENSSL_CONF=""
```

## 🛠️ Solución de Problemas

### Error: "TagUI no reconocido"
```bash
# Reinstalar TagUI o actualizar si es necesario
tagui update
```

## 🔧 Personalización Avanzada

### Modificar Prompts de IA
Editar `generar_prompts.py`, función `build_prompt_for_batch()`:
- Cambiar instrucciones de formato
- Ajustar longitud de resúmenes
- Modificar estructura JSON

### Personalizar Portal HTML
Editar `generar_portal.py`:
- Cambiar tema visual
- Modificar estructura de categorías
- Ajustar responsividad

### Configurar Tiempos de Espera
En archivos `.tag`, ajustar líneas `wait`:
```tagui
wait 120  # Espera 2 minutos para respuesta IA
wait 7    # Espera 7 segundos para cargar WhatsApp
```

## 📊 Formato de Datos

### CSV de Papers Extraídos (`AutoPapper.csv`):
```csv
name,Description,URL,Category
"Título del paper","Descripción completa","https://arxiv.org/abs/...","Computer Science"
```

### CSV de Papers Procesados (`ProcessedPapers.csv`):
```csv
titulo,categoria,resumen,puntos_clave,enlace,fecha_procesado
"🤖 Título traducido","📂 Categoría","📝 Resumen","🎯 Puntos clave","🔗 URL","2025-09-24"
```

### Formato JSON de IA:
```json
{
  "papers": [
    {
      "titulo_español": "🤖 Título con emoji",
      "categoria": "📂 Categoría",
      "resumen": "📝 Resumen en 3 líneas máximo",
      "puntos_clave": "🎯 Aspectos importantes",
      "enlace": "🔗 URL del paper"
    }
  ]
}
```

---

## 🪟 Ejecución en Windows

### Archivos Disponibles
- `PapperNewsHTML.bat` - Script completo → Portal Web
- `PapperNewsWhatsapp.bat` - Script completo → WhatsApp

### Configuración de Rutas Críticas

> **⚠️ IMPORTANTE**: Si experimentas errores de archivos no encontrados en Windows, revisa y ajusta estas rutas según tu sistema:

| Archivo | Línea | Ruta Actual (Linux) | Ruta Windows | Descripción |
|---------|-------|-------------------|--------------|-------------|
| `AutoPapper.tag` | 2 | `OUT/AutoPapper.csv` | `OUT\AutoPapper.csv` | Archivo de salida de papers |
| `AutoPapper.tag` | 68 | `OUT/AutoPapper.csv` | `OUT\AutoPapper.csv` | Escritura de papers |
| `AIOverview.tag` | 2 | `OUT/Prompts.csv` | `OUT\Prompts.csv` | Carga de prompts |
| `AICSV.tag` | 2 | `OUT/ProcessedPapers.csv` | `OUT\ProcessedPapers.csv` | Headers del CSV de salida |
| `AICSV.tag` | 5 | `OUT/Prompts.csv` | `OUT\Prompts.csv` | Carga de prompts |
| `AICSV.tag` | 157 | `OUT/ProcessedPapers.csv` | `OUT\ProcessedPapers.csv` | Escritura de papers procesados |

### Modo 1: Portal HTML 🌐
```cmd
PapperNewsHTML.bat
```

**Proceso:**
1. Extrae papers de arXiv con `AutoPapper.tag`
2. Genera prompts con `generar_prompts.py`
3. Procesa con IA usando `AICSV.tag`
4. Crea portal HTML con `generar_portal.py`
5. Limpia archivos temporales

**Resultado:**
- `portal_noticias.html` - Portal web interactivo

### Modo 2: WhatsApp 📱
```cmd
PapperNewsWhatsapp.bat
```

**Proceso:**
1. Extrae papers de arXiv con `AutoPapper.tag`
2. Genera prompts con `generar_prompts.py`
3. Procesa con IA usando `AIOverview.tag`
4. Envía automáticamente a WhatsApp Web
5. Limpia archivos temporales

**Resultado:**
- Mensajes enviados al grupo WhatsApp configurado

### Notas Importantes para Windows
- Los archivos `.tag` y `.py` son los mismos que en Linux
- Solo cambian los separadores de ruta (`/` → `\`)
- La configuración inicial con `tagui -> "https://google.com -> wait 1000"` es **igualmente importante**
- Asegurar que Python y TagUI estén en el PATH del sistema

---

## 🎓 Información Académica

### Contexto del Proyecto
Este proyecto fue desarrollado para la cátedra **"Tecnologías para la Automatización"** de la **Universidad Tecnológica Nacional, Facultad Regional Concepción del Uruguay** (UTN FRCU), como parte de la carrera **Ingeniería en Sistemas de Información**.

### Equipo de Desarrollo - Grupo 11 (2025)
- **Leal, Pablo Valentín**
- **Martínez, Ignacio Gabriel**
- **Moreyra, Omar Sebastián** 
- **Schultheis, Valentín**
- **Fraisinet, Máximo Exequiel**

### 📄 Licencia y Propósito Educativo
Este proyecto se distribuye bajo la licencia **Unlicense** para garantizar máxima accesibilidad con fines educativos. Fomentamos su uso por:

- ✅ **Estudiantes** de UTN FRCU o cualquier institución académica
- ✅ **Investigadores** interesados en tecnologías de automatización
- ✅ **Desarrolladores** que deseen aprender automatización web e integración con IA
- ✅ **Cualquier persona** interesada en sistemas de procesamiento de papers científicos

**Siéntete libre de usar, modificar y distribuir este código para aprender, enseñar o implementar funcionalidades similares.**

### 🏛️ Información Institucional
- **Universidad**: Universidad Tecnológica Nacional (UTN)
- **Facultad**: Facultad Regional Concepción del Uruguay (FRCU)
- **Carrera**: Ingeniería en Sistemas de Información
- **Cátedra**: Tecnologías para la Automatización
- **Año Académico**: 2025

---

## 🆘 Soporte y Mantenimiento

### Logs y Debugging
- TagUI genera logs automáticos en ejecución
- Verificar archivos en `OUT/` para debugging

### Actualizaciones
```bash
# Actualizar TagUI
tagui update

# Actualizar dependencias Python
pip install --upgrade pandas requests beautifulsoup4
```