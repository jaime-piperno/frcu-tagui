# prueba_conexion.py
# Verifica que el token de config.txt sea válido, SIN mandarle un mensaje a
# nadie. Llama al método getMe de la Bot API, que solo devuelve los datos del
# bot. Es la primera prueba a correr cuando algo no anda.
#
# CÓMO SE EJECUTA
#   Windows:  py prueba_conexion.py
#   Linux:    python3 prueba_conexion.py

import requests

from configuracion import leer_config

config = leer_config(obligatorias=["TELEGRAM_TOKEN"])
respuesta = requests.get(f"https://api.telegram.org/bot{config['TELEGRAM_TOKEN']}/getMe", timeout=20)
resultado = respuesta.json()

if resultado.get("ok"):
    print(f"OK - el token es válido. Bot: @{resultado['result']['username']}")
else:
    print(f"FALLO. Respuesta de Telegram: {resultado}")
    print("Si dice 'Unauthorized', el token de config.txt está mal o fue revocado en BotFather.")
