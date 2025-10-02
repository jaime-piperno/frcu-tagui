# 📌 UTN FRCU – Tecnologías para la Automatización 2025

## 👥 Team
- **Team number:** 8
- **Members:**
  - Grandi, Tobías
  - Irungaray, Francis
  - Noir, Dardo
  - Orcellet, Nicolás

---

## 🤖 Bot Description
- **Description:** 
This bot automates the download of PDF resources from the Moodle virtual campus of UTN FRCU.  
It logs into the platform using provided credentials, navigates through courses and sections, and downloads PDF files to a local folder while skipping non-PDF resources. It also keeps track of files that could not be downloaded.

- **Technology used:**
Python 3, Selenium, Requests, Pandas, python-dotenv

---

## 🛠️ Usage Instructions
1. **Install dependencies:** 
 Make sure you have Python 3 installed. Then install required packages using:
  ```
   pip install -r requirements.txt
  ```
2. **Configure environment variables:** 
Create a `.env` file in the project root with the following variables:
```
USER=your_username
PASSWORD=your_password
DEST_FOLDER=path_to_download_folder
HEADLESS=True
YEARS=year1, year2  # optional, comma-separated
```

3. **Run the bot:**
Execute the main script:
```
python Main.py
```

4.**Expected output:**
* PDFs downloaded into subfolders by course and section inside the DEST_FOLDER.

* A `no_downloaded.csv` file listing skipped non-PDF resources.


---

## 📂 Project Structure
- `Main.py` : Main script to run the bot.
- `MoodleSession.py` : Handles login and course navigation.
- `Course.py` : Handles course interactions.
- `Section.py` : Handles sections and resource retrieval.
- `ResourceDownloader.py` : Downloads PDFs from Moodle.
- `Config.py` : Loads configuration from `.env`.
- `.env` : Stores user credentials and settings.

---

## 📝 Additional Notes
* Challenges faced / technical decisions made
  * Handling dynamic content on Moodle using Selenium waits.
  * Differentiating between PDF resources and other types.
  * Ensuring file paths and names are sanitized for Windows compatibility.

* Current limitations of the bot
  * Only downloads PDF files; other resource types are logged but not downloaded.

  * Slow internet connections may cause the bot to fail due to timing issues between Selenium actions and page loading.

  * Does not handle large-scale parallel downloads (single-threaded).

* Potential improvements for the future
  * Add support for downloading other resource types (Word, Excel, links, Google Drive hosted files).

  * Add support for downloading from Google Classroom.

  * Add filter to download only specific courses.

  * Add an error log tracker.

  * Implement multi-threaded downloads for faster execution.

  * Add a GUI for easier configuration and execution.
