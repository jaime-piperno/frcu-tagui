# 📌 UTN FRCU – Tecnologías para la Automatización 2026

## 👥 Team
- **Team number:** 4
- **Members:**
  - Delavalle Jeronimo 
  - Irigaray Mateo
  - Masalles Ignacio 
  - Plata Santiago

---

## 🤖 Bot Description
- **Description:**
RPA bot that monitors Telegram Web A (`https://web.telegram.org/a/`), detects chats with new messages (unread badge), extracts the last incoming message, processes the query with a Python NLP module, and sends back an automatic reply (welcome/menu, course info via exact or fuzzy matching, suggestions, farewells, or fallback messages).
- **Technology used:** TagUI v6.114 + Chrome (CDP integration) + Python 3

---

## 🎥 Demo Video
- **Demonstration:** [Watch the bot in action on Google Drive](https://drive.google.com/file/d/1yint_aGlrjSV4lXEGspCgQEhNGyWNQtr/view?usp=drive_link)

---

## 🛠️ Usage Instructions
1. **Install prerequisites**: Windows 10/11, Google Chrome, Python 3 (on PATH) and Java JRE/JDK. Unpack TagUI v6.114 into `C:\tagui\` (verify `C:\tagui\src\tagui.cmd`).
2. **Run the bot**: log in to Telegram Web A in Chrome, then launch from the project root:
   ```bash
   tagui src/bot_telegram.tag
   ```
3. **Expected output**: for every chat with an unread badge, the bot opens the chat with the *oldest* pending message (FIFO), reads the incoming message, generates the reply via `src/procesar_consulta.py` (logs are written to `bot.log`), inserts the text into the composer and sends it with a trusted Enter event (CDP). No SikuliX dependency, so it does not hang.

> 💡 **Need detailed setup instructions?**  
> For step-by-step guidance on environment configuration, Git setup, and troubleshooting, check out our comprehensive guides:
> - 📄 [Spanish Setup Guide (Instructivo en Español)](INSTRUCTIVO_INSTALACION.md)
> - 📄 [English Installation Guide](installation_guide.md)
---

## 📝 Additional Notes

- **Current limitations of the bot:**
  - Depends on the live DOM of Telegram Web A (CSS frameworks/selectors may change across versions).
  - Requires an active Chrome session logged into Telegram.
  - Fuzzy thresholds are fixed constants (0.6/0.7) tuned for the current course dataset.

---
