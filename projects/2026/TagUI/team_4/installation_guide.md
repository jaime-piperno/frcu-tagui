# Installation Guide - Telegram Courses Bot (RPA)

## 1. System Requirements
- Windows 10/11
- Google Chrome installed.
- Python 3.x installed and accessible from the PATH. Check it with `python --version` in a new terminal: if the Microsoft Store opens, Python is not installed or the Store shortcut takes priority in the PATH.
- **Microsoft Excel** installed: TagUI uses it to read and write the enrollment spreadsheet.
- Java is **not** needed: TagUI only uses it for visual automation (SikuliX), which this bot does not use.

## 2. TagUI v6.114 Installation
Version 6.114 cannot be downloaded directly: install version 6.110 and update it.
1. Download `TagUI_Windows.zip` for version 6.110 from the official page: <https://github.com/aisingapore/TagUI/releases/tag/v6.110.0>.
2. Unzip it into `C:\` with Windows Explorer, so that the folder `C:\tagui` is created. Verify that `C:\tagui\src\tagui.cmd` exists.
3. Update to version 6.114 (requires an internet connection):
   ```cmd
   C:\tagui\src\tagui update
   ```
4. Add `C:\tagui\src` to the user's PATH environment variable to run `tagui` from any folder. Terminals that were already open (including the VS Code one) must be closed and reopened to pick up the change.

## 3. Getting the Project
- **From the delivery ZIP:** unzip the `Bot Cursos-Telegram` folder anywhere, for example `C:\RPA\Bot Cursos-Telegram`.
- **From GitHub:** clone the course repository; the project is in `projects/2026/TagUI/team_4`. The version with the enrollment feature will be there once the improvement is merged into the repository; until then, use the delivery ZIP.
  ```cmd
  git clone https://github.com/jaime-piperno/frcu-tagui.git
  ```

Verify the structure:
- `src/bot_telegram.tag`: main TagUI flow.
- `src/flujos/`: TagUI steps to call Python and to read and write the spreadsheet.
- `src/tagui_local.js`: TagUI helper functions (TagUI loads it automatically).
- `src/procesar_consulta.py`, `src/preinscripcion.py`, `src/cursos.py`, `src/texto.py`: reply and enrollment logic.
- `data/cursos.csv`: course offer, including the `cupo` (seats) column.
- `tests/`: automated tests.

## 4. Initial Configuration
1. **Telegram account:** use an account dedicated to the bot. The bot replies to **every** chat with unread messages, including groups and personal conversations. Testing requires a second account to send messages to it.
2. **Seats:** each course has its seat limit in the `cupo` column of `data/cursos.csv`. Python reads the file on every message, so changes apply without restarting the bot.
3. **Enrollment spreadsheet:** by default it is created on the user's Desktop as `preinscripciones.xlsx`, with the sheet `Preinscripciones`. To use another folder, change the line `js carpeta_planilla = ...` at the beginning of `src/bot_telegram.tag`.
4. **Showing the spreadsheet when enrolling:** with `js mostrar_planilla_al_registrar = true` (default), when an enrollment is confirmed the bot minimizes Telegram, shows the spreadsheet with the new row for a few seconds and restores Telegram. With `false`, the spreadsheet is updated without being shown. The waiting times are in `src/flujos/registrar_en_planilla.tag` (`wait 2` before writing and `wait 3` after).

## 5. Execution
1. **Close Excel.** TagUI uses any Excel instance it finds open: an open spreadsheet may be hidden or closed.
2. From the project root:
   ```cmd
   tagui src\bot_telegram.tag
   ```
3. TagUI opens Chrome with **its own profile** (not the user's). While the window is blank, **do not touch it**: TagUI needs that empty tab to connect.
4. The first time, Telegram Web shows a QR code. Scan it from the phone: **Telegram → Settings → Devices → Link Desktop Device**. The session is kept for the next runs.
5. The bot keeps monitoring the sidebar in an infinite loop. While there are no new messages, the terminal shows "En espera: Sin mensajes pendientes".
6. To stop it: `Ctrl+C` in the terminal (answer `S`/`Y` if asked to terminate the batch job), then close the Chrome window and the minimized "Python Engine" window.

## 6. Verification
1. **Automated tests** (no Telegram or Excel needed), from the project root:
   ```cmd
   python -m unittest discover tests
   ```
2. **Test with Telegram**, sending from the second account:

   | Message | Expected reply |
   |---|---|
   | `hola` | Menu with the courses in `cursos.csv` |
   | `yoga` | Course details and available seats |
   | `INSCRIBIRME` | Asks for full name, DNI, email and phone (each one is validated) |
   | `SÍ` (on the summary) | Shows the spreadsheet with the new row and confirms the enrollment with its number |
   | `CANCELAR` | Leaves the enrollment at any step |

3. In the terminal, the line "Mensaje recibido en el chat ___" must show a number (the chat identifier).
4. While running, `bot.log`, `entrada.json`, `salida.json` and `data/sesiones.json` are generated in the project root. They are ignored by Git (`.gitignore`) and **must not be shared**, because they contain the users' data.

## 7. Troubleshooting
| Problem | Cause and solution |
|---|---|
| The bot does not start and only "[tagui] START - listening for inputs" is shown | That window is the Python engine and is normal. If the bot does not move on, Chrome was probably touched while it was blank: stop the bot, close Chrome and run it again without touching the window. |
| `python` opens the Microsoft Store | Install Python 3 (adding it to the PATH) and open a new terminal. |
| `tagui` is not recognized as a command | Add `C:\tagui\src` to the PATH and open a new terminal, or run `C:\tagui\src\tagui src\bot_telegram.tag`. |
| The spreadsheet stays behind Telegram | Check that `mostrar_planilla_al_registrar` is `true` and that the bot was restarted after any change to the `.tag` files. |
| A new workbook appears ("Book1", "Libro1") or the spreadsheet closes by itself | Excel was open while the bot was running. Close it and run the bot again. |
