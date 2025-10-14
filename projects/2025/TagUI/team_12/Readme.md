# 📌 UTN FRCU – Tecnologías para la Automatización [2025]

## 👥 Team
- *Team number:* 12
- *Members:*
  - Cergneux Jeremías
  - Chiloteguy Juan Ignacio
  - Gaitan Tomás
  - Mista Mateo
  - Müller Federico
  - Vergara Agustín

---

## 🤖 Bot Description
- *Description:* 
  Un bot desarrollado en Python que utiliza TagUI junto con la API de Gmail para automatizar la limpieza de la bandeja de entrada. El script busca y mueve a la papelera los correos que tienen más de 30 días de antigüedad y no están marcados como importantes. Además, guarda un registro de los correos eliminados en un archivo de texto.

- *Technology used:*
  - Python
  - TagUI
  - Gmail API

---

## 🛠️ Usage Instructions
1. Configuración: 

  - Habilitar la API de Gmail en la Google Cloud Console y descargar el archivo de credenciales en formato .json.
  - Renombrar el archivo de credenciales a “credentials.json” y guardarlo en la misma carpeta que el script. 
  - Instalar las librerías necesarias de Google para Python: pip install --upgrade google-api-python-client google-auth-httplib2 google-auth-oauthlib.

2. Ejecución:

  - Ejecutar el script desde la terminal.
  - La primera vez, se abrirá una ventana del navegador para autorizar el acceso a la cuenta de Gmail. Esto creará un archivo token.pickle para no tener que autorizar en futuras ejecuciones.

3. Resultado esperado:

  - El script buscará hasta 5 correos que cumplan con el criterio. 
  - Los correos encontrados serán movidos a la papelera. 
  - En la consola se imprimirá un mensaje de confirmación por cada correo movido. 
  - Se creará o actualizará un archivo eliminados.txt con los detalles de los correos gestionados. 
  - Si no se encuentran correos, se mostrará un mensaje indicándolo. 

---

## 📝 Additional Notes
- Decisiones técnicas: Se optó por utilizar el flujo de autenticación OAuth 2.0 para un acceso seguro a la API, guardando un token de sesión para facilitar ejecuciones posteriores. El criterio de búsqueda (older_than:30d -is:important) se eligió para enfocarse en correos que son probablemente innecesarios. 

- Limitaciones actuales: El bot procesa un máximo de 5 correos por ejecución. No elimina permanentemente los correos, solo los mueve a la papelera. 

- Mejoras a futuro: Se podría parametrizar el número de correos a eliminar y los criterios de búsqueda. El proceso podría automatizarse para que se ejecute periódicamente sin intervención manual (por ejemplo, con un cron job).