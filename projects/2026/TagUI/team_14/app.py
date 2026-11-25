"""
Servidor Web FastAPI para la Conciliación Automatizada de Mercado Pago.
Permite subir el extracto original vía navegador (o desde el bot de Telegram), descargar el
resultado conciliado y consultar el historial de corridas.
"""
from __future__ import annotations

import hmac
import logging
import os
import shutil
import tempfile
import time
import uuid
import zipfile
from contextlib import asynccontextmanager
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Optional

from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from openpyxl.utils.exceptions import InvalidFileException
from starlette.background import BackgroundTask

from entorno import cargar_env

# En modo local (sin Docker) toma API_KEY y BOT_CODIGO_ACCESO del .env, antes de importar el resto.
cargar_env()

import db  # noqa: E402
import exportar  # noqa: E402
from conciliar import (
    PATRON_PERIODO,
    asociar_cargos,
    calcular_metricas,
    calcular_totales,
    cargar_datos,
    comparar_con_anterior,
    detalle_pendientes,
    huella_datos,
    detectar_periodo,
    generar_excel,
    validar_cuadre_excel,
)

logger = logging.getLogger("rpa_mercadopago")

VERSION = "2.3.0"
API_KEY = os.getenv("API_KEY", "").strip()
BOT_CODIGO_ACCESO = os.getenv("BOT_CODIGO_ACCESO", "").strip()
CANALES_VALIDOS = {"web", "telegram"}
LIMITE_HISTORIAL_MAX = 50
MEDIA_TYPES = {
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "pdf": "application/pdf",
    "csv": "text/csv; charset=utf-8",
    "csv-pendientes": "text/csv; charset=utf-8",
}
FORMATOS_RESUMEN = {"pdf", "csv"}


@asynccontextmanager
async def lifespan(_app: FastAPI):
    db.init_db()
    yield


app = FastAPI(title="RPA Conciliador Mercado Pago", version=VERSION, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
TEMP_DIR = Path(tempfile.gettempdir()) / "rpa_mercadopago_cache"
TEMP_DIR.mkdir(parents=True, exist_ok=True)

# Almacén en memoria de descargas temporales:
# {token: {"timestamp": float, "archivos": {formato: {"path": Path, "filename": str}}}}
DOWNLOAD_CACHE: dict[str, dict] = {}


def _borrar(path: Path) -> None:
    try:
        path.unlink(missing_ok=True)
    except OSError:
        pass


def limpiar_cache_antiguo(max_segundos: int = 3600):
    """Elimina los archivos generados hace más de 1 hora."""
    ahora = time.time()
    expirados = [
        token for token, data in DOWNLOAD_CACHE.items()
        if ahora - data["timestamp"] > max_segundos
    ]
    for token in expirados:
        data = DOWNLOAD_CACHE.pop(token, None)
        if data:
            for archivo in data["archivos"].values():
                _borrar(archivo["path"])


def a_json(valor):
    """Convierte Decimal (también dentro de dicts y listas) a float para la respuesta JSON."""
    if isinstance(valor, Decimal):
        return float(valor)
    if isinstance(valor, dict):
        return {k: a_json(v) for k, v in valor.items()}
    if isinstance(valor, (list, tuple)):
        return [a_json(v) for v in valor]
    return valor


def validar_periodo(valor: str, nombre: str) -> str:
    valor = (valor or "").strip()
    if not PATRON_PERIODO.fullmatch(valor):
        raise HTTPException(status_code=400, detail=f"El parámetro '{nombre}' debe tener formato YYYY-MM (recibido: '{valor}').")
    return valor


def meses_entre(desde: str, hasta: str) -> list[str]:
    anio, mes = map(int, desde.split("-"))
    anio_fin, mes_fin = map(int, hasta.split("-"))
    meses = []
    while (anio, mes) <= (anio_fin, mes_fin):
        meses.append(f"{anio:04d}-{mes:02d}")
        mes += 1
        if mes == 13:
            anio, mes = anio + 1, 1
    return meses


def corrida_a_json(c: dict) -> dict:
    return a_json({
        "id": c["id"],
        "fecha_ejecucion": c["fecha_ejecucion"],
        "periodo": c["periodo"],
        "archivo": c["archivo"],
        "canal": c["canal"],
        "usuario": c.get("usuario"),
        "comparacion": c.get("comparacion"),
        "movimientos": c["movimientos"],
        "cargos_totales": c["cargos_totales"],
        "cargos_asociados": c["cargos_asociados"],
        "cargos_pendientes": c["cargos_pendientes"],
        "porcentaje_asociado": c["porcentaje_asociado"],
        "monto_pendiente": c["monto_pendiente"],
        "ingresos": c["ingresos"],
        "egresos": c["egresos"],
        "balance": c["balance"],
        "totales_retenciones": {
            "sircupa": c["total_sircupa"],
            "sirtac": c["total_sirtac"],
            "idc": c["total_idc"],
            "gastos": c["total_gastos"],
        },
        "cuadre_ok": c["cuadre_ok"],
        "diferencia_cuadre": c["diferencia_cuadre"],
        "filas_con_error": c["filas_con_error"],
    })


@app.get("/api/salud")
def salud():
    return {"status": "ok", "app": "RPA Conciliador Mercado Pago", "version": VERSION}


@app.post("/api/conciliar")
def conciliar_archivo(
    archivo: UploadFile = File(...),
    periodo: Optional[str] = Form(None),
    hoja: str = Form("sheet0"),
    canal: str = Form("web"),
    chat_id: Optional[str] = Form(None),
    usuario: Optional[str] = Form(None),
):
    """Recibe el Excel de Mercado Pago, ejecuta la conciliación, registra la corrida y devuelve métricas con token de descarga."""
    if not archivo.filename or not archivo.filename.lower().endswith(".xlsx"):
        raise HTTPException(status_code=400, detail="El archivo debe ser un libro de Excel (.xlsx)")

    canal = (canal or "web").strip().lower()
    if canal not in CANALES_VALIDOS:
        raise HTTPException(status_code=400, detail=f"Canal inválido: '{canal}'.")

    limpiar_cache_antiguo()

    # Período: el indicado explícitamente o el que figura en el nombre del archivo
    if periodo and periodo.strip():
        periodo_seleccionado = validar_periodo(periodo, "periodo")
    else:
        periodo_seleccionado = detectar_periodo(archivo.filename)
        if not periodo_seleccionado:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"No se pudo detectar el período en el nombre '{archivo.filename}'. "
                    "Renombrá el archivo como 'MP YYYY-MM (M).xlsx' o indicá el período (YYYY-MM)."
                ),
            )

    temp_id = str(uuid.uuid4())
    archivo_entrada = TEMP_DIR / f"input_{temp_id}.xlsx"
    archivo_salida = TEMP_DIR / f"conciliacion_{periodo_seleccionado}_{temp_id}.xlsx"

    try:
        with open(archivo_entrada, "wb") as buffer:
            shutil.copyfileobj(archivo.file, buffer)

        # 1. Cargar datos
        try:
            movimientos, cargos = cargar_datos(archivo_entrada, periodo_seleccionado, hoja)
        except (zipfile.BadZipFile, InvalidFileException):
            raise HTTPException(status_code=400, detail="El archivo no es un libro de Excel (.xlsx) válido.")
        except KeyError:
            raise HTTPException(
                status_code=422,
                detail=f"El archivo no tiene la hoja de movimientos '{hoja}' (ni 'sheet0', 'TP' o 'Detallado')."
            )
        if not movimientos:
            raise HTTPException(
                status_code=422,
                detail=f"No se encontraron movimientos para el período '{periodo_seleccionado}' en la hoja '{hoja}'."
            )

        # Huella de los datos leídos: identifica el mismo extracto aunque cambie el nombre del archivo
        huella = huella_datos(movimientos, cargos)

        # 2. Asociar cargos
        asociar_cargos(movimientos, cargos)
        cargos_pendientes = [c for c in cargos if c["target"] is None]

        # 3. Calcular totales
        resultados = calcular_totales(movimientos)

        # 4. Generar Excel final
        nombre_descarga = f"conciliacion_{periodo_seleccionado}.xlsx"
        guardado_en = generar_excel(
            archivo_origen=archivo_entrada,
            archivo_destino=archivo_salida,
            resultados=resultados,
            hoja_tp=hoja,
            cargos_pendientes=cargos_pendientes,
            movimientos=movimientos,
            todos_los_cargos=cargos,
            periodo=periodo_seleccionado
        )

        # 5. Control de cuadre sobre el archivo generado y métricas de la corrida
        cuadre = validar_cuadre_excel(guardado_en, cargos)
        metricas = calcular_metricas(movimientos, cargos, resultados)
        pendientes = detalle_pendientes(movimientos, cargos)

        # 6. Comparación con la corrida anterior del mismo mes y registro en el historial
        #    (si falla, la conciliación igual se entrega)
        corrida_id = None
        anterior = None
        estado_comparacion = None
        try:
            anterior = db.ultima_corrida(periodo_seleccionado)
            estado_comparacion = comparar_con_anterior(anterior, huella)
            corrida_id = db.registrar_corrida(
                periodo=periodo_seleccionado,
                archivo=archivo.filename,
                canal=canal,
                chat_id=chat_id,
                usuario=usuario,
                huella=huella,
                metricas=metricas,
                cuadre=cuadre,
                resultados=resultados,
                pendientes=pendientes,
            )
        except Exception:
            logger.exception("No se pudo registrar la corrida en el historial")

        comparacion = {"estado": estado_comparacion, "corrida_anterior": None}
        if anterior is not None:
            comparacion["corrida_anterior"] = {
                "id": anterior["id"],
                "fecha_ejecucion": anterior["fecha_ejecucion"],
                "canal": anterior["canal"],
                "usuario": anterior.get("usuario"),
                "chat_id": anterior.get("chat_id"),
                "archivo": anterior["archivo"],
                "movimientos": anterior["movimientos"],
                "cargos_pendientes": anterior["cargos_pendientes"],
                "monto_pendiente": anterior["monto_pendiente"],
                "balance": anterior["balance"],
            }

        # 7. Exportaciones PDF y CSV (si fallan, el Excel igual se entrega)
        archivos = {"xlsx": {"path": guardado_en, "filename": nombre_descarga}}
        try:
            ruta_pdf = TEMP_DIR / f"conciliacion_{periodo_seleccionado}_{temp_id}.pdf"
            exportar.pdf_conciliacion(
                ruta_pdf,
                periodo=periodo_seleccionado,
                archivo=archivo.filename,
                metricas=metricas,
                cuadre=cuadre,
                pendientes=pendientes,
            )
            archivos["pdf"] = {"path": ruta_pdf, "filename": f"conciliacion_{periodo_seleccionado}.pdf"}

            ruta_csv = TEMP_DIR / f"conciliacion_{periodo_seleccionado}_{temp_id}.csv"
            exportar.csv_hoja_principal(guardado_en, ruta_csv)
            archivos["csv"] = {"path": ruta_csv, "filename": f"conciliacion_{periodo_seleccionado}.csv"}

            if pendientes:
                ruta_pend = TEMP_DIR / f"pendientes_{periodo_seleccionado}_{temp_id}.csv"
                exportar.csv_pendientes(pendientes, ruta_pend)
                archivos["csv-pendientes"] = {"path": ruta_pend, "filename": f"pendientes_{periodo_seleccionado}.csv"}
        except Exception:
            logger.exception("No se pudieron generar las exportaciones PDF/CSV")

        token_descarga = str(uuid.uuid4())
        DOWNLOAD_CACHE[token_descarga] = {
            "timestamp": time.time(),
            "archivos": archivos,
        }

        return a_json({
            "status": "success",
            "periodo": periodo_seleccionado,
            "nombre_archivo": archivo.filename,
            "descarga_token": token_descarga,
            "archivo_salida": nombre_descarga,
            "corrida_id": corrida_id,
            "historial_guardado": corrida_id is not None,
            "huella": huella,
            "comparacion": comparacion,
            "exportaciones": list(archivos),
            "metricas": {
                "movimientos_totales": metricas["movimientos_totales"],
                "cargos_totales": metricas["cargos_totales"],
                "cargos_asociados": metricas["cargos_asociados"],
                "cargos_pendientes": metricas["cargos_pendientes"],
                "porcentaje_asociado": metricas["porcentaje_asociado"],
                "monto_pendiente": metricas["monto_pendiente"],
                "ingresos": metricas["ingresos"],
                "egresos": metricas["egresos"],
                "balance": metricas["balance"],
                "totales_retenciones": metricas["totales_retenciones"],
                "cuadre": {
                    "ok": cuadre["ok"],
                    "diferencia": cuadre["total"]["diferencia"],
                    "mov_total_ok": cuadre["mov_total_ok"],
                    "filas_validadas": cuadre["filas_validadas"],
                    "filas_con_error": len(cuadre["filas_con_error"]),
                    "detalle_por_hoja": [
                        {
                            "hoja": d["hoja"],
                            "origen": d["origen"],
                            "imputado": d["imputado"],
                            "pendiente": d["pendiente"],
                            "diferencia": d["diferencia"],
                            "ok": d["ok"],
                        }
                        for d in cuadre["detalle"]
                    ],
                },
            },
            "pendientes": pendientes,
        })

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error durante la conciliación")
        raise HTTPException(status_code=500, detail=f"Error durante la conciliación: {e}")
    finally:
        if archivo_entrada.exists():
            try:
                archivo_entrada.unlink()
            except OSError:
                pass


@app.get("/api/descargar/{token}")
def descargar_archivo(
    token: str,
    formato: str = Query("xlsx", description="xlsx (default), pdf, csv o csv-pendientes"),
):
    """Entrega el resultado de una conciliación en el formato pedido."""
    formato = (formato or "xlsx").strip().lower()
    if formato not in MEDIA_TYPES:
        raise HTTPException(status_code=400, detail=f"Formato inválido: '{formato}'. Opciones: {', '.join(MEDIA_TYPES)}.")

    item = DOWNLOAD_CACHE.get(token)
    if not item:
        raise HTTPException(status_code=404, detail="El archivo solicitado expiró (se conserva 1 hora) o no existe.")
    archivo = item["archivos"].get(formato)
    if not archivo:
        detalle = (
            "No hay cargos no conciliados en esta corrida."
            if formato == "csv-pendientes" else f"El formato '{formato}' no está disponible para esta corrida."
        )
        raise HTTPException(status_code=404, detail=detalle)
    if not archivo["path"].exists():
        raise HTTPException(status_code=404, detail="El archivo solicitado expiró (se conserva 1 hora) o no existe.")

    return FileResponse(path=archivo["path"], filename=archivo["filename"], media_type=MEDIA_TYPES[formato])


def obtener_resumen(desde: str, hasta: Optional[str]) -> dict:
    """Valida el rango y arma el resumen (montos en Decimal) con la última corrida de cada período."""
    desde = validar_periodo(desde, "desde")
    hasta = validar_periodo(hasta, "hasta") if hasta else desde
    if desde > hasta:
        raise HTTPException(status_code=400, detail="'desde' no puede ser posterior a 'hasta'.")

    corridas = db.ultima_por_periodo(desde, hasta)
    if not corridas:
        raise HTTPException(status_code=404, detail=f"No hay corridas registradas entre {desde} y {hasta}.")

    con_datos = {c["periodo"] for c in corridas}
    return {
        "desde": desde,
        "hasta": hasta,
        "meses": corridas,
        "meses_sin_datos": [m for m in meses_entre(desde, hasta) if m not in con_datos],
        "totales": db.resumir(corridas),
    }


@app.get("/api/resumen")
def resumen(
    desde: str = Query(..., description="Período inicial YYYY-MM"),
    hasta: Optional[str] = Query(None, description="Período final YYYY-MM (opcional)"),
):
    """Resumen de un mes o de un rango de meses, usando la última corrida registrada de cada período."""
    datos = obtener_resumen(desde, hasta)
    return a_json({**datos, "meses": [corrida_a_json(c) for c in datos["meses"]]})


@app.get("/api/resumen/exportar")
def exportar_resumen(
    desde: str = Query(..., description="Período inicial YYYY-MM"),
    hasta: Optional[str] = Query(None, description="Período final YYYY-MM (opcional)"),
    formato: str = Query("pdf", description="pdf o csv"),
):
    """Exporta el resumen de un mes o rango a PDF o CSV."""
    formato = (formato or "pdf").strip().lower()
    if formato not in FORMATOS_RESUMEN:
        raise HTTPException(status_code=400, detail=f"Formato inválido: '{formato}'. Opciones: pdf, csv.")

    datos = obtener_resumen(desde, hasta)
    sufijo = datos["desde"] if datos["desde"] == datos["hasta"] else f"{datos['desde']}_{datos['hasta']}"
    destino = TEMP_DIR / f"resumen_{sufijo}_{uuid.uuid4()}.{formato}"
    if formato == "pdf":
        exportar.pdf_resumen(datos, destino)
    else:
        exportar.csv_resumen(datos, destino)

    return FileResponse(
        path=destino,
        filename=f"resumen_{sufijo}.{formato}",
        media_type=MEDIA_TYPES[formato],
        background=BackgroundTask(_borrar, destino),
    )


def parsear_fecha(valor: str, nombre: str) -> date:
    texto = (valor or "").strip()
    for formato in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y"):
        try:
            return datetime.strptime(texto, formato).date()
        except ValueError:
            pass
    raise HTTPException(
        status_code=400,
        detail=f"El parámetro '{nombre}' debe ser una fecha DD-MM-AAAA o AAAA-MM-DD (recibido: '{texto}')."
    )


def obtener_resumen_dias(desde: str, hasta: Optional[str]) -> dict:
    """Resumen entre dos fechas usando el detalle guardado de la última corrida de cada mes involucrado."""
    f_desde = parsear_fecha(desde, "desde")
    f_hasta = parsear_fecha(hasta, "hasta") if hasta else f_desde
    if f_desde > f_hasta:
        raise HTTPException(status_code=400, detail="'desde' no puede ser posterior a 'hasta'.")

    periodos = meses_entre(f_desde.strftime("%Y-%m"), f_hasta.strftime("%Y-%m"))
    corridas = db.ultima_por_periodo(periodos[0], periodos[-1])
    rango = f"{f_desde.strftime('%d/%m/%Y')} y {f_hasta.strftime('%d/%m/%Y')}"
    if not corridas:
        raise HTTPException(status_code=404, detail=f"No hay corridas registradas para los meses entre {rango}.")

    detalle = db.resumen_por_dias([c["id"] for c in corridas], f_desde.isoformat(), f_hasta.isoformat())
    sin_detalle = {c["periodo"] for c in corridas if c["id"] in detalle["corridas_sin_detalle"]}
    if len(sin_detalle) == len(corridas):
        raise HTTPException(
            status_code=404,
            detail=(
                f"Las corridas de {', '.join(sorted(sin_detalle))} no tienen detalle diario guardado "
                "(se registraron antes de esta función). Volvé a procesar esos extractos."
            ),
        )

    con_datos = {c["periodo"] for c in corridas}
    return {
        "desde": f_desde.isoformat(),
        "hasta": f_hasta.isoformat(),
        "periodos_consultados": sorted(con_datos - sin_detalle),
        "meses_sin_datos": [m for m in periodos if m not in con_datos],
        "meses_sin_detalle": sorted(sin_detalle),
        "dias": detalle["dias"],
        "totales": detalle["totales"],
    }


@app.get("/api/resumen/dias")
def resumen_dias(
    desde: str = Query(..., description="Fecha inicial (DD-MM-AAAA o AAAA-MM-DD)"),
    hasta: Optional[str] = Query(None, description="Fecha final (opcional)"),
):
    """Resumen de un intervalo de fechas, con detalle por día."""
    return a_json(obtener_resumen_dias(desde, hasta))


@app.get("/api/resumen/dias/exportar")
def exportar_resumen_dias(
    desde: str = Query(..., description="Fecha inicial (DD-MM-AAAA o AAAA-MM-DD)"),
    hasta: Optional[str] = Query(None, description="Fecha final (opcional)"),
    formato: str = Query("pdf", description="pdf o csv"),
):
    """Exporta el resumen de un intervalo de fechas a PDF o CSV."""
    formato = (formato or "pdf").strip().lower()
    if formato not in FORMATOS_RESUMEN:
        raise HTTPException(status_code=400, detail=f"Formato inválido: '{formato}'. Opciones: pdf, csv.")

    datos = obtener_resumen_dias(desde, hasta)
    sufijo = datos["desde"] if datos["desde"] == datos["hasta"] else f"{datos['desde']}_{datos['hasta']}"
    destino = TEMP_DIR / f"resumen_{sufijo}_{uuid.uuid4()}.{formato}"
    if formato == "pdf":
        exportar.pdf_resumen_dias(datos, destino)
    else:
        exportar.csv_resumen_dias(datos, destino)

    return FileResponse(
        path=destino,
        filename=f"resumen_{sufijo}.{formato}",
        media_type=MEDIA_TYPES[formato],
        background=BackgroundTask(_borrar, destino),
    )


# ---------------------------------------------------------------------------
# Usuarios del bot (protegido con la clave interna API_KEY, compartida con el bot)
# ---------------------------------------------------------------------------

def verificar_api_key(x_api_key: Optional[str] = Header(None)) -> None:
    if not API_KEY:
        raise HTTPException(status_code=503, detail="La gestión de usuarios está deshabilitada: falta configurar API_KEY.")
    if not x_api_key or not hmac.compare_digest(x_api_key, API_KEY):
        raise HTTPException(status_code=401, detail="Clave de API inválida.")


@app.get("/api/usuarios", dependencies=[Depends(verificar_api_key)])
def listar_usuarios():
    return {"usuarios": db.listar_usuarios()}


@app.get("/api/usuarios/{chat_id}", dependencies=[Depends(verificar_api_key)])
def consultar_usuario(chat_id: str):
    return {"chat_id": chat_id, "autorizado": db.usuario_activo(chat_id)}


@app.post("/api/usuarios/vincular", dependencies=[Depends(verificar_api_key)])
def vincular_usuario(
    chat_id: str = Form(...),
    codigo: str = Form(...),
    nombre: Optional[str] = Form(None),
):
    if not BOT_CODIGO_ACCESO:
        raise HTTPException(status_code=503, detail="La vinculación por código no está habilitada (falta BOT_CODIGO_ACCESO).")
    if not hmac.compare_digest(codigo.strip(), BOT_CODIGO_ACCESO):
        raise HTTPException(status_code=403, detail="Código de acceso incorrecto.")
    ya_estaba = db.vincular_usuario(chat_id, nombre)
    return {"chat_id": chat_id, "vinculado": True, "ya_estaba_vinculado": ya_estaba}


@app.post("/api/usuarios/desvincular", dependencies=[Depends(verificar_api_key)])
def desvincular_usuario(chat_id: str = Form(...)):
    return {"chat_id": chat_id, "desvinculado": db.desvincular_usuario(chat_id)}


@app.get("/api/historial")
def historial(limite: int = Query(10, ge=1, le=LIMITE_HISTORIAL_MAX)):
    """Últimas corridas registradas (todas las ejecuciones, incluidas las repetidas de un mismo período)."""
    return {"corridas": [corrida_a_json(c) for c in db.historial(limite)]}


# Servir archivos estáticos del frontend
if STATIC_DIR.exists():
    app.mount("/", StaticFiles(directory=str(STATIC_DIR), html=True), name="static")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
