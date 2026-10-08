# Installation Guide - Telegram Courses Bot (RPA)

## 1. System Requirements
- Windows 10/11
- Google Chrome installed (recommended)
- Java JRE/JDK **64-bit** (version 8+).
- Python 3.x installed and accessible from the PATH (`python`)

## 2. TagUI v6.114 Installation
1. Download TagUI v6.114 (the version used in this project).
2. Unzip into `C:\tagui\` (recommended path). Verify that `C:\tagui\src\tagui.cmd` exists.
3. Add `C:\tagui\src` to the Windows PATH (optional) to run `tagui` from any directory.


## 3. Repository Provisioning and Local Deployment
To maintain source integrity and track deployment history, the workspace must be provisioned by cloning the central GitHub repository to the local machine:

## 4. Initial Configuration
1. Open Telegram Web A (`https://web.telegram.org/a/`) in Chrome and keep the session logged in. TagUI opens its own Chrome window in automation mode, but an already authenticated account is required.
2. Verify that Python reads/writes correctly: the `procesar_consulta.py` script calculates its absolute paths from its own location, so it works from any folder.

## 5. Execution
From the project root (the folder where the repository was cloned, for example `C:\RPA\Automatizacion-RPA`):
```cmd
tagui src/bot_telegram.tag
```
The bot keeps monitoring the sidebar in an infinite loop. To stop it, close the Chrome window or end the process with `Ctrl+C` in the terminal.

## 6. Verification
- Upon receiving messages with a notification badge, the bot replies to the **chat with the oldest message** (FIFO by real time: it compares the visible time of each chat; if there is no time, it takes the lowest one in the sidebar).
- The responses include a menu, course search (exact + fuzzy matching), and farewell detection.
- The exchange files `in.txt`, `out.txt` and `bot.log` are generated in the project root during execution and are ignored by Git.