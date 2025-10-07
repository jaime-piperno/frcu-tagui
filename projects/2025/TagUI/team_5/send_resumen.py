import os, base64, requests
from datetime import datetime

# ==== CONFIG ====
#SG_API_KEY = os.getenv("SG_API_KEY")  # Cargar API key antes de correr!!
SG_API_KEY = "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"
FROM_EMAIL = "lucasbrejoaco@gmail.com"
TO_EMAILS  = [""]
SUBJECT    = f"Resumen Diario - {datetime.now().strftime('%Y-%m-%d')}"
RESUMEN_PATH = "resumen.txt"

if not SG_API_KEY:
    raise RuntimeError("❌ Falta SG_API_KEY en variables de entorno.")

# ==== LECTURA DEL ARCHIVO ====
if not os.path.exists(RESUMEN_PATH):
    raise FileNotFoundError(f"No se encontró {RESUMEN_PATH}")

with open(RESUMEN_PATH, "r", encoding="utf-8") as f:
    contenido = f.read()

# ==== PAYLOAD SENDGRID ====
payload = {
    "personalizations": [
                        {"to": [{"email": e} for e in TO_EMAILS]}
    ],
    "from": {"email": FROM_EMAIL},
    "subject": SUBJECT,
    "content": [{"type": "text/plain", "value": contenido}],
    "attachments": [{
      "content": base64.b64encode(contenido.encode("utf-8")).decode("ascii"),
      "type": "text/plain",
      "filename": "resumen.txt"
    }]
}

# ==== ENVÍO ====
print(f"[INFO] Enviando mail desde {FROM_EMAIL} a {TO_EMAILS} ...")
resp = requests.post(
    "https://api.sendgrid.com/v3/mail/send",
    headers={"Authorization": f"Bearer {SG_API_KEY}"},
    json=payload,
    timeout=30
)

print("Status:", resp.status_code)
print("Body:", resp.text if resp.text else "(vacío)")

if resp.status_code == 202:
    print("Resumen enviado con éxito por SendGrid API.")
    try:
        os.remove(RESUMEN_PATH)
        print(f"🗑️ Archivo {RESUMEN_PATH} borrado correctamente.")
    except OSError as e:
        print(f"⚠️ No se pudo borrar {RESUMEN_PATH}: {e}")
else:
    print("Hubo un error, revisá el código de estado arriba.")
