"""Módulo de notificaciones automáticas para Telegram (Grupo 12 RPA).

Filtra las ofertas más óptimas (precio mínimo con stock y variante confirmada)
y envía una alerta formateada a Telegram al finalizar la ejecución del pipeline.
"""
from datetime import datetime
import html
import json
import os
from pathlib import Path
import sys

# Carga de variables de entorno (.env)
ROOT = Path(__file__).resolve().parents[1]
try:
    from dotenv import load_dotenv
    # Busca .env en la carpeta de Grupo12 o en la raíz del proyecto
    env_file = ROOT / '.env'
    if not env_file.is_file():
        env_file = ROOT.parent / '.env'
    load_dotenv(dotenv_path=env_file if env_file.is_file() else None)
except ImportError:
    # Fallback simple si python-dotenv no está presente
    for candidate in [ROOT / '.env', ROOT.parent / '.env']:
        if candidate.is_file():
            try:
                for line in candidate.read_text(encoding='utf-8').splitlines():
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        k, v = line.split('=', 1)
                        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
            except Exception:
                pass


def formatear_moneda(valor):
    """Formatea un número decimal/float al estilo monetario argentino ($ 12.345,67)."""
    if valor is None:
        return "$ 0,00"
    try:
        val = float(valor)
        entero = int(val)
        decimales = int(round((val - entero) * 100))
        partes = f"{entero:,}".replace(',', '.')
        if decimales > 0:
            return f"$ {partes},{decimales:02d}"
        return f"$ {partes}"
    except (ValueError, TypeError):
        return f"$ {valor}"


def filtrar_mejores_ofertas(payload):
    """Extrae la mejor oferta confirmada (status == 'ok' y min(price)) por cada producto.

    Args:
        payload (dict): Diccionario retornado por process_run con 'results', 'products', 'providers'.

    Returns:
        list[dict]: Lista de mejores ofertas enriquecidas con metadatos del producto y proveedor.
    """
    if not isinstance(payload, dict):
        return []

    results = payload.get('results', [])
    products_raw = payload.get('products', [])
    providers_raw = payload.get('providers', [])

    # Indexar productos y proveedores para enriquecer los resultados
    products = {}
    if isinstance(products_raw, list):
        for p in products_raw:
            if isinstance(p, dict) and p.get('id'):
                products[p['id']] = p
    elif isinstance(products_raw, dict):
        products = products_raw

    providers = {}
    if isinstance(providers_raw, list):
        for prv in providers_raw:
            if isinstance(prv, dict) and prv.get('id'):
                providers[prv['id']] = prv.get('name') or prv['id']
    elif isinstance(providers_raw, dict):
        for k, v in providers_raw.items():
            providers[k] = v.get('name', k) if isinstance(v, dict) else str(v)

    # Filtrar solo resultados válidos con stock y precio confirmado
    valid_results = []
    for r in results:
        if not isinstance(r, dict):
            continue
        status = r.get('status')
        price = r.get('price')
        if status == 'ok' and price is not None:
            try:
                numeric_price = float(price)
                if numeric_price > 0:
                    valid_results.append((numeric_price, r))
            except (ValueError, TypeError):
                continue

    if not valid_results:
        return []

    # Agrupar por producto y seleccionar la oferta con el menor precio
    by_product = {}
    for price, item in valid_results:
        pid = item.get('product_id')
        if not pid:
            continue
        if pid not in by_product or price < by_product[pid]['numeric_price']:
            by_product[pid] = {
                'numeric_price': price,
                'raw': item
            }

    # Enriquecer cada oferta seleccionada
    mejores_ofertas = []
    for pid, data in by_product.items():
        raw = data['raw']
        prod_meta = products.get(pid, {})
        prv_id = raw.get('provider', '')
        prv_name = providers.get(prv_id, prv_id.title() if prv_id else 'Tienda')

        oferta = {
            'product_id': pid,
            'product_name': prod_meta.get('name') or raw.get('title') or f"Producto {pid}",
            'product_brand': prod_meta.get('brand', ''),
            'category': prod_meta.get('category', ''),
            'provider_id': prv_id,
            'provider_name': prv_name,
            'price': data['numeric_price'],
            'price_formatted': formatear_moneda(data['numeric_price']),
            'method': (raw.get('method') or '').strip(),
            'title': (raw.get('title') or '').strip(),
            'url': (raw.get('url') or raw.get('candidate_url') or '').strip(),
            'checked_at': raw.get('checked_at')
        }
        mejores_ofertas.append(oferta)

    # Ordenar por nombre del producto
    mejores_ofertas.sort(key=lambda x: x['product_name'].lower())
    return mejores_ofertas


def construir_mensaje_telegram(ofertas, timestamp=None, max_chars=3900):
    """Construye uno o más mensajes HTML optimizados para la visualización en Telegram.

    Args:
        ofertas (list[dict]): Lista devuelta por filtrar_mejores_ofertas.
        timestamp (str, optional): Fecha/hora para el encabezado.
        max_chars (int): Longitud máxima por fragmento para respetar el límite de 4096 caracteres.

    Returns:
        list[str]: Lista de fragmentos HTML listos para enviar por la API.
    """
    ts = timestamp or datetime.now().strftime('%d/%m/%Y %H:%M')

    if not ofertas:
        msg = (
            "ℹ️ <b>REPORTE DE PRECIOS | GRUPO 12 RPA</b> ℹ️\n"
            f"<i>Fecha: {ts}</i>\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "No se encontraron ofertas con coincidencia exacta y stock confirmado en esta corrida.\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "📁 <i>El archivo Excel fue generado con los resultados completos.</i>"
        )
        return [msg]

    header = (
        "🚨 <b>MEJORES OFERTAS DETECTADAS | GRUPO 12</b> 🚨\n"
        f"<i>Fecha de análisis: {ts}</i>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    )

    footer = (
        "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📊 <b>Total de ofertas óptimas:</b> {len(ofertas)}\n"
        "📁 <i>Consolidado completo guardado en Excel.</i>"
    )

    # Construir bloques por cada oferta
    bloques = []
    for o in ofertas:
        nombre = html.escape(o['product_name'])
        marca = f" - {html.escape(o['product_brand'])}" if o.get('product_brand') else ""
        tienda = html.escape(o['provider_name'])
        precio = o['price_formatted']
        metodo = f" ({html.escape(o['method'])})" if o.get('method') else ""
        url = o.get('url')

        linea_url = f'• Enlace: <a href="{html.escape(url)}">Ir a la oferta directa</a>\n' if url else ''

        bloque = (
            f"💊 <b>{nombre}{marca}</b>\n"
            f"• Tienda: <code>{tienda}</code>\n"
            f"• Mejor Precio: <b>{precio}</b>{metodo}\n"
            f"{linea_url}\n"
        )
        bloques.append(bloque)

    # Agrupar en fragmentos respetando el tamaño máximo
    mensajes = []
    contenido_actual = header

    for b in bloques:
        # Si agregar el bloque + footer supera el límite, cerrar el mensaje actual
        if len(contenido_actual) + len(b) + len(footer) > max_chars:
            mensajes.append(contenido_actual.rstrip())
            contenido_actual = header + b
        else:
            contenido_actual += b

    contenido_actual += footer
    mensajes.append(contenido_actual)

    return mensajes


def enviar_alerta_telegram(mensaje, token=None, chat_id=None, timeout=None):
    """Envía un mensaje formateado a la API de Telegram con manejo de timeouts y fallos.

    Args:
        mensaje (str or list[str]): Contenido HTML a enviar.
        token (str, optional): Bot token. Si no se provee, se toma de TELEGRAM_BOT_TOKEN.
        chat_id (str, optional): Chat ID. Si no se provee, se toma de TELEGRAM_CHAT_ID.
        timeout (int, optional): Timeout en segundos.

    Returns:
        bool: True si el envío fue exitoso en todas sus partes, False si falló.
    """
    token = token or os.getenv('TELEGRAM_BOT_TOKEN', '').strip()
    chat_id = chat_id or os.getenv('TELEGRAM_CHAT_ID', '').strip()

    if not token or not chat_id:
        print("[Telegram] Advertencia: TELEGRAM_BOT_TOKEN o TELEGRAM_CHAT_ID no configurados.", flush=True)
        return False

    timeout_val = float(timeout or os.getenv('TELEGRAM_TIMEOUT_SECONDS', '10'))
    url = f"https://api.telegram.org/bot{token}/sendMessage"

    fragmentos = [mensaje] if isinstance(mensaje, str) else mensaje
    todos_ok = True

    for i, fragmento in enumerate(fragmentos):
        payload_data = {
            'chat_id': chat_id,
            'text': fragmento,
            'parse_mode': 'HTML',
            'disable_web_page_preview': True
        }

        enviado = False
        # Intento vía requests si está disponible
        try:
            import requests
            resp = requests.post(url, json=payload_data, timeout=(5.0, timeout_val))
            if resp.status_code == 200:
                enviado = True
            else:
                err_detail = resp.text
                try:
                    err_json = resp.json()
                    err_detail = err_json.get('description', resp.text)
                except Exception:
                    pass
                print(f"[Telegram] Error API ({resp.status_code}): {err_detail}", flush=True)
        except ImportError:
            # Fallback a urllib si requests no estuviera instalado
            try:
                import urllib.request
                data_bytes = json.dumps(payload_data).encode('utf-8')
                req = urllib.request.Request(
                    url,
                    data=data_bytes,
                    headers={'Content-Type': 'application/json'}
                )
                with urllib.request.urlopen(req, timeout=timeout_val) as resp:
                    if resp.status == 200:
                        enviado = True
            except Exception as e_urllib:
                print(f"[Telegram] Error de red (urllib): {e_urllib}", flush=True)
        except Exception as err:
            print(f"[Telegram] Error al conectar con Telegram: {err}", flush=True)

        if not enviado:
            todos_ok = False

    return todos_ok


def notificar_mejores_ofertas(payload, folder=None, token=None, chat_id=None):
    """Punto de entrada principal para invocar desde main.py.

    Ejecuta el filtrado, formateo y envío a Telegram de forma completamente resiliente.
    Nunca propaga excepciones hacia el flujo principal.
    """
    try:
        enabled = os.getenv('TELEGRAM_NOTIFY_ENABLED', 'true').strip().lower() in ('1', 'true', 'si', 'yes')
        if not enabled:
            print("[Telegram] Notificaciones desactivadas por TELEGRAM_NOTIFY_ENABLED.", flush=True)
            return False

        token = token or os.getenv('TELEGRAM_BOT_TOKEN', '').strip()
        chat_id = chat_id or os.getenv('TELEGRAM_CHAT_ID', '').strip()

        if not token or not chat_id:
            print("[Telegram] Notificaciones omitidas: falta configurar TELEGRAM_BOT_TOKEN o TELEGRAM_CHAT_ID en .env", flush=True)
            return False

        ofertas = filtrar_mejores_ofertas(payload)
        mensajes = construir_mensaje_telegram(ofertas)

        print(f"[Telegram] Enviando reporte con {len(ofertas)} mejores ofertas encontradas...", flush=True)
        ok = enviar_alerta_telegram(mensajes, token=token, chat_id=chat_id)
        if ok:
            print(f"[Telegram] Alerta enviada con éxito al chat {chat_id}.", flush=True)
        else:
            print("[Telegram] No se pudo entregar la alerta en Telegram (revisar logs de conexión o token).", flush=True)
        return ok
    except Exception as general_err:
        # Garantía de contención: un fallo de Telegram jamás rompe la corrida del RPA
        print(f"[Telegram] Error no controlado en módulo de notificaciones: {general_err}", flush=True)
        return False
