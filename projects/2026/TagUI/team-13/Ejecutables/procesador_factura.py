"""Lee una foto de factura usando una IA web manejada con TagUI.

La sesion de la IA debe estar iniciada en el Chrome de TagUI. Los selectores
dependen del proveedor y se configuran en CONFIG_IA o con variables de entorno.
"""

import argparse
import os
import platform
import sys
import time
from pathlib import Path

import rpa as r
from configuracion import leer_configuracion_factura


class ErrorProcesadorFactura(Exception):
    """La automatizacion no pudo obtener una lectura de la factura."""


def _configuracion_actual():
    return leer_configuracion_factura()


def _validar_configuracion(config):
    faltantes = [
        clave for clave in (
            "url", "selector_adjunto", "selector_opcion_subir", "selector_prompt",
            "selector_respuesta"
        )
        if not config[clave]
    ]
    if faltantes:
        raise ErrorProcesadorFactura(
            f"Falta configurar {', '.join(faltantes)}. Revisa Ejecutables/configuracion.py."
        )
    try:
        if int(config["tiempo_maximo"]) < 1:
            raise ValueError
    except ValueError:
        raise ErrorProcesadorFactura("FACTURA_TIEMPO_MAXIMO tiene que ser un entero positivo.")


def construir_prompt(ingredientes_conocidos):
    """Arma una instruccion compacta con los nombres y unidades del stock."""
    if isinstance(ingredientes_conocidos, dict):
        nombres = sorted({
            f"{valor[0]} ({valor[1]})" for valor in ingredientes_conocidos.values()
        })
    else:
        nombres = sorted({str(nombre) for nombre in ingredientes_conocidos})
    conocidos = ", ".join(nombres) if nombres else "ninguno"
    plantilla = _configuracion_actual()["prompt_template"]
    return plantilla.format(ingredientes_conocidos=conocidos)


def _iniciar_tagui():
    if platform.system() != "Linux":
        return r.init()

    openssl_conf = os.environ.get("OPENSSL_CONF")
    os.environ["OPENSSL_CONF"] = os.devnull
    try:
        return r.init()
    finally:
        if openssl_conf is None:
            os.environ.pop("OPENSSL_CONF", None)
        else:
            os.environ["OPENSSL_CONF"] = openssl_conf


SELECTORES_ADJUNTO_FALLBACK = (
    '//*[@id="xap-skip-link-target"]/div/chat-window/div[2]/input-container/div/input-area-v2/div/fieldset/div/div[2]/simplified-input-menu/div/span/gem-icon-button/button',
    '//input-area-v2//simplified-input-menu//button',
    '//simplified-input-menu//button',
    '//button[contains(@aria-label,"Añadir") or contains(@aria-label,"Adjuntar") or contains(@aria-label,"Subir") or contains(@aria-label,"Upload") or contains(@aria-label,"Add")]',
    '//button[.//mat-icon[contains(@data-mat-icon-name,"add") or contains(@data-mat-icon-name,"attach")]]',
)

SELECTORES_OPCION_SUBIR_FALLBACK = (
    '//*[starts-with(@id,"cdk-overlay-")]/mat-card/mat-action-list/div[1]/uploader/div/div/div[1]/images-files-uploader/gem-button/button',
    '//*[starts-with(@id,"cdk-overlay-")]//images-files-uploader//button',
    '//mat-action-list//uploader//button',
    '//uploader//images-files-uploader//button',
    '//*[starts-with(@id,"cdk-overlay-")]//button[contains(.,"Subir") or contains(.,"Upload") or contains(.,"archivo") or contains(.,"Foto")]',
)

SELECTORES_ARCHIVO_FALLBACK = (
    "images-files-uploader input[type='file']",
    "uploader input[type='file']",
    "input[type='file']",
)


def _esperar(selector, segundos, deadline=None):
    limite = int(segundos)
    if deadline is not None:
        restante = int(deadline - time.monotonic())
        limite = min(limite, max(0, restante))
    for _ in range(limite):
        if r.present(selector):
            return True
        r.wait(1)
    return bool(r.present(selector))


def _esperar_cualquiera(selectores, segundos, deadline=None):
    limite = int(segundos)
    if deadline is not None:
        restante = int(deadline - time.monotonic())
        limite = min(limite, max(0, restante))
    for _ in range(limite):
        for sel in selectores:
            if sel and r.present(sel):
                return sel
        r.wait(1)
    for sel in selectores:
        if sel and r.present(sel):
            return sel
    return None



def _clic_enviar(config, deadline):
    for selector in config["selectores_enviar"]:
        if _esperar(selector, 3, deadline) and r.click(selector):
            return True
    return False


def _leer_respuesta(selector):
    try:
        if not r.present(selector):
            return ""
        return r.read(selector).strip()
    except Exception:
        return ""



def _diagnosticar_adjunto():
    return r.dom(
        'return JSON.stringify({opciones:Array.from(document.querySelectorAll('
        '"[role=menuitem], [role=option], button, [role=button]"))'
        '.map(e=>({texto:(e.innerText||"").trim(),aria:e.getAttribute("aria-label"),'
        'titulo:e.getAttribute("title")}))'
        '.filter(e=>/upload|subir|archivo|file/i.test([e.texto,e.aria,e.titulo].join(" "))),'
        'archivos:Array.from(document.querySelectorAll("input[type=file]"))'
        '.map(e=>({accept:e.accept,visible:!!(e.offsetWidth||e.offsetHeight||e.getClientRects().length)}))})'
    )

def _esperar_respuesta_nueva(selector, respuesta_anterior, deadline):
    respuesta = ""
    lecturas_iguales = 0
    while time.monotonic() < deadline:
        r.wait(1)
        actual = _leer_respuesta(selector)
        if actual and actual != respuesta_anterior:
            if actual == respuesta:
                lecturas_iguales += 1
            else:
                respuesta = actual
                lecturas_iguales = 0
            if lecturas_iguales >= 3:
                return respuesta
    raise ErrorProcesadorFactura(
        "Gemini no respondió antes de que se agotara el tiempo configurado."
    )


def procesar_factura(ruta_factura, ingredientes_conocidos):
    """Sube la factura a la IA web y devuelve su respuesta como texto.

    `ingredientes_conocidos` puede ser el diccionario que devuelve
    compras.ingredientes_conocidos() o una lista de nombres.
    """
    ruta = Path(ruta_factura).expanduser().resolve()
    if not ruta.is_file():
        raise ErrorProcesadorFactura(f"No existe el archivo de factura: {ruta}")

    config = _configuracion_actual()
    _validar_configuracion(config)
    tiempo_maximo = int(config["tiempo_maximo"])
    deadline = time.monotonic() + tiempo_maximo
    if not _iniciar_tagui():
        raise ErrorProcesadorFactura("No se pudo iniciar TagUI ni abrir Chrome.")

    try:
        r.url(config["url"])
        if not _esperar(config["selector_prompt"], tiempo_maximo, deadline):
            raise ErrorProcesadorFactura(
                "No encontre la caja de consulta. Inicia sesion en la IA en Chrome "
                "y revisa los selectores configurados."
            )

        # 1. Abrir menú de adjunto
        lista_adjunto = [config["selector_adjunto"]] + [
            s for s in SELECTORES_ADJUNTO_FALLBACK if s != config["selector_adjunto"]
        ]
        selector_adjunto = _esperar_cualquiera(lista_adjunto, 10, deadline)
        if not selector_adjunto:
            diagnostico = _diagnosticar_adjunto()
            raise ErrorProcesadorFactura(
                "No encontre el boton de adjuntar en Gemini. "
                f"Elementos detectados: {diagnostico}. "
                "Revisa FACTURA_SELECTOR_ADJUNTO."
            )
        r.click(selector_adjunto)

        # 2. Si el input file no está visible de inmediato tras abrir el menú,
        # clickear la opción "Subir archivo" del menú desplegado.
        lista_archivo = [config["selector_archivo"]] + [
            s for s in SELECTORES_ARCHIVO_FALLBACK if s != config["selector_archivo"]
        ]
        selector_archivo = _esperar_cualquiera(lista_archivo, 2, deadline)
        if not selector_archivo:
            lista_opcion_subir = [config["selector_opcion_subir"]] + [
                s for s in SELECTORES_OPCION_SUBIR_FALLBACK if s != config["selector_opcion_subir"]
            ]
            selector_opcion = _esperar_cualquiera(lista_opcion_subir, 8, deadline)
            if not selector_opcion:
                diagnostico = _diagnosticar_adjunto()
                raise ErrorProcesadorFactura(
                    "No encontre la opcion de subir archivos. Elementos relacionados "
                    f"detectados en Gemini: {diagnostico}"
                )
            r.click(selector_opcion)

            selector_archivo = _esperar_cualquiera(lista_archivo, 10, deadline)
            if not selector_archivo:
                raise ErrorProcesadorFactura(
                    "No encontre el control para adjuntar archivos. Revisa FACTURA_SELECTOR_ARCHIVO."
                )

        respuesta_anterior = _leer_respuesta(config["selector_respuesta"])
        if not r.upload(selector_archivo, str(ruta)):
            raise ErrorProcesadorFactura(
                "TagUI no pudo adjuntar la imagen; no voy a enviar el prompt sin la factura."
            )
        r.wait(8)
        if not _esperar(config["selector_prompt"], 30, deadline):
            raise ErrorProcesadorFactura(
                "La foto se adjunto, pero Gemini no volvio a mostrar la caja de consulta. "
                "No escribi ni envie el prompt."
            )
        if not r.click(config["selector_prompt"]):
            raise ErrorProcesadorFactura("No pude enfocar la caja de consulta.")
        if not r.type(config["selector_prompt"], construir_prompt(ingredientes_conocidos)):
            raise ErrorProcesadorFactura(
                "No pude escribir el prompt; la consulta no se envio. Revisa el selector de la caja."
            )
        if not _clic_enviar(config, deadline):
            raise ErrorProcesadorFactura(
                "Escribi el prompt, pero no encontre ninguno de los botones Enviar configurados. "
                "La consulta no se envio."
            )
        return _esperar_respuesta_nueva(
            config["selector_respuesta"], respuesta_anterior, deadline
        )
    finally:
        r.close()


def _argumentos_cli():
    parser = argparse.ArgumentParser(
        description="Procesa manualmente una foto de factura con la IA web configurada."
    )
    parser.add_argument("foto", type=Path, help="Ruta a la foto de la factura")
    parser.add_argument(
        "--subir",
        action="store_true",
        help="Confirma que la foto se enviara al servicio externo de IA configurado.",
    )
    return parser.parse_args()


def main():
    args = _argumentos_cli()
    if not args.subir:
        raise SystemExit(
            "La foto se subira a un servicio externo de IA. Revisa la privacidad del ticket "
            "y vuelve a ejecutar agregando --subir si estas de acuerdo."
        )

    try:
        import compras

        respuesta = procesar_factura(args.foto, compras.ingredientes_conocidos())
    except ErrorProcesadorFactura as error:
        print(f"FALLO: {error}", file=sys.stderr)
        raise SystemExit(2)
    print(respuesta)


if __name__ == "__main__":
    main()