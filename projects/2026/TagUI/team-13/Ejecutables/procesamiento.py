"""Coordina el cálculo de compras y el envío mediante el robot RPA."""

import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

import compras

MINUTOS_MAXIMOS_ROBOT = 3


class ErrorDeEjecucion(Exception):
    """El robot no pudo completar el envío por Telegram Web."""


@dataclass
class ResultadoPedido:
    faltantes: list
    advertencias: list
    mensaje: str = ""
    captura: Path | None = None
    error_robot: str = ""


def _ejecutar_robot(mensaje, grupo):
    try:
        import robot_telegram_web
    except ImportError as error:
        raise ErrorDeEjecucion(f"no pude cargar el módulo del robot: {error}") from error

    captura = robot_telegram_web.CAPTURA
    captura.unlink(missing_ok=True)
    try:
        proceso = subprocess.run(
            [sys.executable, str(Path(robot_telegram_web.__file__).resolve()), "--enviar", grupo],
            input=mensaje.encode("utf-8"), capture_output=True,
            timeout=MINUTOS_MAXIMOS_ROBOT * 60,
            cwd=Path(robot_telegram_web.__file__).resolve().parent,
        )
    except subprocess.TimeoutExpired:
        robot_telegram_web.terminar_procesos_tagui()
        raise ErrorDeEjecucion(
            f"tardó más de {MINUTOS_MAXIMOS_ROBOT} minutos y lo corté. ¿La PC está "
            "bloqueada? Con la sesión bloqueada Chrome no dibuja las páginas"
        )

    if proceso.returncode != 0:
        errores = proceso.stderr.decode("utf-8", errors="replace").strip().splitlines()
        detalle = errores[-1] if errores else "falló sin dar detalles"
        raise ErrorDeEjecucion(detalle)
    return captura


def procesar_pedido(seleccionadas, grupo):
    """Calcula faltantes y trata de enviarlos; no realiza llamadas a Telegram."""
    faltantes, advertencias = compras.calcular_lista(seleccionadas)
    if not faltantes:
        return ResultadoPedido(faltantes, advertencias)

    mensaje = compras.armar_mensaje(faltantes)
    compras.guardar_evidencia(mensaje)
    try:
        captura = _ejecutar_robot(mensaje, grupo)
    except ErrorDeEjecucion as error:
        return ResultadoPedido(faltantes, advertencias, mensaje, error_robot=str(error))
    return ResultadoPedido(faltantes, advertencias, mensaje, captura=captura)