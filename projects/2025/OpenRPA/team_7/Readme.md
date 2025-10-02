# 📌 UTN FRCU – Tecnologías para la Automatización 2025

## 👥 Team
- **Team number**: 7
- **Members**:  
  - Oscar Haunau  
  - Eric Espinosa  
  - Brian Turin  
  - Baltazar Franz  

## 🤖 Bot Description
- **Description**: Web scraper que ingresa a FilmAffinity, accede a las críticas de una película y guarda automáticamente los comentarios con sus puntuaciones en un archivo Excel.  
- **Technology used**: OpenRPA  

## 🛠️ Usage Instructions
1. Descargar e instalar [OpenRPA](https://openrpa.dk/openrpa) :contentReference[oaicite:0]{index=0}.  
2. Clonar o descargar el archivo `WebScrapperOpenRPA.json`.  
3. Abrir OpenRPA → `Import` → seleccionar el archivo.  
4. Abrir [FilmAffinity](https://www.filmaffinity.com/ar/main.html).  
5. Entrar a cualquier película y presionar **Play** en OpenRPA.  
6. El bot recorrerá todas las páginas de críticas y exportará un Excel (`DataSet.xlsx`) en el escritorio:contentReference[oaicite:1]{index=1}.  

*(Incluí capturas de pantalla mostrando el flujo en OpenRPA y un ejemplo del Excel generado.)*

## 📝 Additional Notes
- **Challenges faced**:  
  - Configuración de los selectores para navegar entre páginas.  
  - El bot no siempre muestra el mensaje de finalización.  
- **Current limitations**:  
  - Funciona con una película a la vez.  
- **Potential improvements**:  
  - Extenderlo para múltiples películas en un solo run.  
  - Mejor manejo de notificaciones de éxito/fracaso.  
