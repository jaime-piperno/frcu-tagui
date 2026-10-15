"""
Servidor Web FastAPI para la Conciliación Automatizada de Mercado Pago.
Permite subir el extracto original vía navegador y descargar el resultado conciliado.
"""
from __future__ import annotations

import re
import shutil
import tempfile
import time
import uuid
from decimal import Decimal
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from conciliar import ZERO, asociar_cargos, calcular_totales, cargar_datos, generar_excel

app = FastAPI(title="RPA Conciliador Mercado Pago", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
TEMP_DIR = Path(tempfile.gettempdir()) / "rpa_mercadopago_cache"
TEMP_DIR.mkdir(parents=True, exist_ok=True)

# Almacén en memoria de descargas temporales: {token: {path, filename, timestamp}}
DOWNLOAD_CACHE: dict[str, dict] = {}


def limpiar_cache_antiguo(max_segundos: int = 3600):
    """Elimina archivos generados hace más de 1 hora."""
    ahora = time.time()
    expirados = [
        token for token, data in DOWNLOAD_CACHE.items()
        if ahora - data["timestamp"] > max_segundos
    ]
    for token in expirados:
        data = DOWNLOAD_CACHE.pop(token, None)
        if data and data["path"].exists():
            try:
                data["path"].unlink()
            except OSError:
                pass


@app.get("/api/salud")
def salud():
    return {"status": "ok", "app": "RPA Conciliador Mercado Pago", "version": "2.0.0"}


@app.post("/api/conciliar")
async def conciliar_archivo(
    archivo: UploadFile = File(...),
    periodo: Optional[str] = Form(None),
    hoja: str = Form("sheet0")
):
    """Recibe el archivo Excel de Mercado Pago, ejecuta la conciliación y retorna resumen con token de descarga."""
    if not archivo.filename or not archivo.filename.lower().endswith(".xlsx"):
        raise HTTPException(status_code=400, detail="El archivo debe ser un libro de Excel (.xlsx)")

    limpiar_cache_antiguo()

    # Detección del período (YYYY-MM) si no vino especificado
    periodo_seleccionado = periodo.strip() if periodo else None
    if not periodo_seleccionado:
        m = re.search(r"20\d{2}-\d{2}", archivo.filename)
        periodo_seleccionado = m.group(0) if m else time.strftime("%Y-%m")

    # Guardar archivo de entrada temporalmente
    temp_id = str(uuid.uuid4())
    archivo_entrada = TEMP_DIR / f"input_{temp_id}.xlsx"
    archivo_salida = TEMP_DIR / f"conciliacion_{periodo_seleccionado}_{temp_id}.xlsx"

    try:
        with open(archivo_entrada, "wb") as buffer:
            shutil.copyfileobj(archivo.file, buffer)

        # 1. Cargar datos
        movimientos, cargos = cargar_datos(archivo_entrada, periodo_seleccionado, hoja)
        if not movimientos:
            raise HTTPException(
                status_code=422,
                detail=f"No se encontraron movimientos para el período '{periodo_seleccionado}' en la hoja '{hoja}'."
            )

        # 2. Asociar cargos
        asociar_cargos(movimientos, cargos)
        cargos_pendientes = [c for c in cargos if c["target"] is None]
        cargos_asociados = len(cargos) - len(cargos_pendientes)

        # 3. Calcular totales
        resultados = calcular_totales(movimientos)

        # 4. Generar Excel final
        nombre_descarga = f"conciliacion_{periodo_seleccionado}.xlsx"
        generar_excel(
            archivo_origen=archivo_entrada,
            archivo_destino=archivo_salida,
            resultados=resultados,
            hoja_tp=hoja,
            cargos_pendientes=cargos_pendientes,
            movimientos=movimientos,
            todos_los_cargos=cargos,
            periodo=periodo_seleccionado
        )

        # Guardar en caché de descarga
        token_descarga = str(uuid.uuid4())
        DOWNLOAD_CACHE[token_descarga] = {
            "path": archivo_salida,
            "filename": nombre_descarga,
            "timestamp": time.time()
        }

        # Métricas calculadas
        total_cargos_num = len(cargos)
        porcentaje_asociado = round((cargos_asociados / total_cargos_num * 100), 2) if total_cargos_num > 0 else 100.0
        monto_pendiente = float(sum((c["amount"] for c in cargos_pendientes), ZERO))

        return {
            "status": "success",
            "periodo": periodo_seleccionado,
            "nombre_archivo": archivo.filename,
            "descarga_token": token_descarga,
            "archivo_salida": nombre_descarga,
            "metricas": {
                "movimientos_totales": len(movimientos),
                "cargos_totales": total_cargos_num,
                "cargos_asociados": cargos_asociados,
                "cargos_pendientes": len(cargos_pendientes),
                "porcentaje_asociado": porcentaje_asociado,
                "monto_pendiente": monto_pendiente
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error durante la conciliación: {e}")
    finally:
        if archivo_entrada.exists():
            try:
                archivo_entrada.unlink()
            except OSError:
                pass


@app.get("/api/descargar/{token}")
def descargar_archivo(token: str):
    """Entrega el archivo Excel procesado como descarga directa al navegador."""
    item = DOWNLOAD_CACHE.get(token)
    if not item or not item["path"].exists():
        raise HTTPException(status_code=404, detail="El archivo solicitado ha expirado o no existe.")

    return FileResponse(
        path=item["path"],
        filename=item["filename"],
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )


# Servir archivos estáticos del frontend
if STATIC_DIR.exists():
    app.mount("/", StaticFiles(directory=str(STATIC_DIR), html=True), name="static")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
