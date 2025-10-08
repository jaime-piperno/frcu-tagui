from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import os
import pickle


# ----------------------
# Configuración de credenciales
# ----------------------
SCOPES = ['https://www.googleapis.com/auth/gmail.modify']
creds = None


# Usar token previo si existe
if os.path.exists('token.pickle'):
   with open('token.pickle', 'rb') as token:
       creds = pickle.load(token)


# Si no hay credenciales válidas, abrir flujo OAuth
if not creds or not creds.valid:
   if creds and creds.expired and creds.refresh_token:
       creds.refresh(Request())
   else:
       flow = InstalledAppFlow.from_client_secrets_file('credenciales.json', SCOPES)
       creds = flow.run_local_server(port=0)
   with open('token.pickle', 'wb') as token:
       pickle.dump(creds, token)


# ----------------------
# Conectar a Gmail API
# ----------------------
service = build('gmail', 'v1', credentials=creds)


# ----------------------
# Buscar hasta 5 correos mayores a 30 días que no sean importantes
# ----------------------
query = "older_than:30d -is:important"
results = service.users().messages().list(userId='me', q=query, maxResults=5).execute()
messages = results.get('messages', [])


if not messages:
   print("No se encontraron mensajes que cumplan el criterio.")
else:
   eliminados = []


   for msg in messages:
       # Obtener detalles del mensaje
       full_msg = service.users().messages().get(
           userId='me',
           id=msg['id'],
           format='metadata',
           metadataHeaders=['From','Subject','Date']
       ).execute()


       headers = {h['name']: h['value'] for h in full_msg['payload']['headers']}
       from_field = headers.get('From', 'N/A')
       subject_field = headers.get('Subject', '(sin asunto)')
       date_field = headers.get('Date', 'N/A')


       # Mover a Papelera
       service.users().messages().modify(
           userId='me',
           id=msg['id'],
           body={'removeLabelIds':['INBOX'], 'addLabelIds':['TRASH']}
       ).execute()


       # Guardar detalle
       eliminados.append(
           f"De: {from_field}\nAsunto: {subject_field}\nFecha: {date_field}\nID: {msg['id']}\n{'-'*50}\n"
       )


       print(f"Movido a papelera: {subject_field} ({from_field})")


   # ----------------------
   # Guardar detalles en eliminados.txt (append)
   # ----------------------
   with open("eliminados.txt", "a", encoding="utf-8") as f:
       f.writelines(eliminados)


   print(f"\nSe eliminaron {len(eliminados)} correos. Detalles guardados en eliminados.txt")