📌 **UTN FRCU – Tecnologías para la Automatización 2025**

👥 **Team**  
**Team number:** 7  
**Members:**  
- Oscar Haunau  
- Eric Espinosa  
- Brian Turin  
- Baltazar Franz  

---

🤖 **Bot Description**  
**Description:**  
This bot automates the extraction of movie reviews from the FilmAffinity website.  
It navigates through the review pages of a selected movie, collects each comment and its corresponding rating, and automatically exports the data to an Excel file (`DataSet.xlsx`).  

**Technology used:** OpenRPA  

---

🛠️ **Usage Instructions**  
1. Download and install [OpenRPA](https://openrpa.dk/openrpa).  
2. Clone or download the workflow file `WebScrapperOpenRPA.json`.  
3. In OpenRPA, go to **Import**, and select the `.json` file.  
4. Open [FilmAffinity](https://www.filmaffinity.com/ar/main.html) in your browser.  
5. Navigate to any movie and press **Play** in OpenRPA to start the bot.  
6. The bot will iterate through all available review pages and export an Excel file (`DataSet.xlsx`) with all collected comments and ratings.  

📊 The repository also includes screenshots showing the OpenRPA flow and the generated Excel output.

---

📂 **Project Structure**

projects/

└── 2025/

└── OpenRPA/

└── team_7/

├── Readme.md

├── WebScrapperOpenRPA.json

└── DOCUMENTACION_WEB_SCRAPER_OPENRPA.pdf


---

📝 **Additional Notes**  
**Challenges faced / technical decisions made:**  
- Adjusting element selectors to navigate between review pages.  
- Handling pagination and dynamic content loading on FilmAffinity.  
- Ensuring correct data export into the Excel file.  

**Current limitations:**  
- Works with one movie at a time.  
- May not display a completion message depending on browser latency.  

**Potential improvements for the future:**  
- Add support for multiple movies in a single run.  
- Include visual notifications for success or errors.  
- Implement retry logic for pages that fail to load.  
