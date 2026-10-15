FROM python:3.12-slim-bookworm

ENV PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive

# TagUI necesita php-cli, procps (ps/kill) y Google Chrome
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates curl gnupg php-cli procps \
    && curl -fsSL https://dl.google.com/linux/linux_signing_key.pub \
        | gpg --dearmor -o /usr/share/keyrings/google-chrome.gpg \
    && echo "deb [arch=amd64 signed-by=/usr/share/keyrings/google-chrome.gpg] http://dl.google.com/linux/chrome/deb/ stable main" \
        > /etc/apt/sources.list.d/google-chrome.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends google-chrome-stable \
    && rm -rf /var/lib/apt/lists/*

# TagUI lanza el comando "google-chrome" sin flags extra, pero en un
# contenedor Chrome necesita --no-sandbox (corre como root) y --headless
# (no hay pantalla; con ventana no expone el puerto de depuración que usa
# TagUI). Este wrapper (/usr/local/bin va antes que /usr/bin en el PATH)
# agrega los flags necesarios.
RUN printf '#!/bin/sh\nexec /opt/google/chrome/chrome --headless=new --no-sandbox --disable-dev-shm-usage "$@"\n' \
        > /usr/local/bin/google-chrome \
    && chmod +x /usr/local/bin/google-chrome

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# descarga TagUI (~200MB) a ~/.tagui en el build, para no bajarlo cada vez
# que arranca el contenedor
RUN python -c "import tagui; assert tagui.setup() is not False"

COPY . .

CMD ["python", "main.py"]
