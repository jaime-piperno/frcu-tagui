# 📌 UTN FRCU – Tecnologías para la Automatización [year]

## 👥 Team
- Team 5
- Members:
  - Benedetti, Brian Agustin
  - Bre, Lucas
  - Lima, Martín Sebastián
  - Vaschchuk, Gonzalo
  - Weber, Thiago


---

## 🤖 Bot Description
The process consists of a kind of daily summary:

	1. Access different websites to extract information:
		- Weather: meteorological data from an official portal.
		- News: two or three relevant news articles.
		- Dollar price: current exchange rate from a financial site.

	2. Process the collected information and generate an automatic summary with the most relevant data.

	3.Send the summary by email to a predefined recipient.

- **Technology used:**
The selected tool is TagUI, a robotic process automation (RPA) software developed by AI Singapore and open-source.

---

## 🛠️ Usage Instructions
1. [Step 1: what to install or configure]

Steps to install TagUI:

		1. Go to this link: https://github.com/aisingapore/TagUI
		2. Click on Releases.
		3. Click on the .zip file corresponding to your operating system.
			Note: the file you click will automatically be downloaded.
		4. Unzip the file and place the tagui folder wherever you prefer (recommendation: don’t leave it in Downloads).
		5. After placing the folder, enter it and locate the src folder.
		6. Enter the src folder and copy the path.
		7. In Windows search, look for “Edit the system environment variables” and click it.
		8. A window will appear, select the ‘Environment Variables’ button.
		9. Another window will appear; select PATH and click Edit.
		10. A new window will appear, click New.
		11. Paste the path you copied earlier and click OK.
		12. Finally, open CMD and run the command tagui; it should execute and show the TagUI help.

2. [Step 2: how to run the bot]

		1. First, have the files automatizar.bat, resumen_diario.tag and send_resumen.py in the same folder.
		2. Open the Send_Resumen.py, look for the To_emails = [""] line and place the email (We tried it with a gmail we do not know if it works with another) to which the summary will be sent inside the quotes.
		3. In case of not having the chrome browser installed they must do it since it is the browser that uses the bot.
		4. Execute the automatize.bat file.

3. [Step 3: expected output]

The summary will reach the spam section of your email and have an equal format to this:

Resumen Diario

Fuente Weather

Clima: 19° - Despejado

---------------------------------------------------------------------------------------
Noticias:

Fuente BBC Mundo

- Qué es un "swap" de monedas como el que negocia Argentina con el gobierno de Trump (y las dudas que genera)
- "Ninguna de nosotras pidió jamás un trato especial": veteranas del ejército de EE.UU. responden al polémico discurso del secretario de Defensa sobre la masculinidad
- Israel detiene a los activistas de la flotilla de ayuda humanitaria que intentaba llegar a Gaza y asegura que los deportará
---------------------------------------------------------------------------------------
Dólar Blue:

Fuente Dolar Hoy

Valor Compra: $1430

Valor Venta: $1450

---

## 📝 Additional Notes
- [Challenges faced / technical decisions made]
- [Current limitations of the bot]
- [Potential improvements for the future]
