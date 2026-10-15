#!/bin/sh
# Lanzador para Linux / macOS. Mientras esta terminal este abierta, el bot
# atiende en Telegram.
cd "$(dirname "$0")"
python3 bot.py
