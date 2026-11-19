"""
Persistencia del historial de conciliaciones (SQLite).

- corridas:           una fila por ejecución (web, Telegram o consola) con métricas y cuadre.
- movimientos:        detalle de la hoja principal de cada corrida (para resúmenes por rango de fechas).
- cargos_pendientes:  cargos no conciliados de cada corrida.
- usuarios_bot:       usuarios de Telegram vinculados mediante código de acceso.

Para no acumular detalle repetido, al registrar una corrida se borra el detalle (movimientos y
pendientes) de las corridas anteriores del mismo período; el resumen de esas corridas se conserva.
Los importes del detalle se guardan en centavos (INTEGER) para sumar en SQL sin errores de redondeo.
"""
from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from datetime import date, datetime
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = Path(os.getenv('DB_PATH', str(BASE_DIR / 'data' / 'conciliaciones.db')))
ZONA_HORARIA = os.getenv('TZ', 'America/Argentina/Buenos_Aires')
CENT = Decimal('0.01')


def ahora() -> datetime:
    """Fecha y hora actual en la zona horaria configurada (por defecto Argentina), independiente del contenedor."""
    try:
        return datetime.now(ZoneInfo(ZONA_HORARIA))
    except ZoneInfoNotFoundError:
        return datetime.now().astimezone()


CAMPOS_MONTO = (
    'monto_pendiente', 'ingresos', 'egresos', 'balance',
    'total_sircupa', 'total_sirtac', 'total_idc', 'total_gastos', 'diferencia_cuadre',
)
CAMPOS_ENTEROS = ('movimientos', 'cargos_totales', 'cargos_asociados', 'cargos_pendientes')

ESQUEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS corridas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fecha_ejecucion TEXT NOT NULL,
    periodo TEXT NOT NULL,
    archivo TEXT NOT NULL,
    canal TEXT NOT NULL CHECK (canal IN ('web', 'telegram', 'cli')),
    chat_id TEXT,
    usuario TEXT,
    huella TEXT,
    movimientos INTEGER NOT NULL,
    cargos_totales INTEGER NOT NULL,
    cargos_asociados INTEGER NOT NULL,
    cargos_pendientes INTEGER NOT NULL,
    porcentaje_asociado REAL NOT NULL,
    monto_pendiente TEXT NOT NULL,
    ingresos TEXT NOT NULL,
    egresos TEXT NOT NULL,
    balance TEXT NOT NULL,
    total_sircupa TEXT NOT NULL,
    total_sirtac TEXT NOT NULL,
    total_idc TEXT NOT NULL,
    total_gastos TEXT NOT NULL,
    cuadre_ok INTEGER NOT NULL CHECK (cuadre_ok IN (0, 1)),
    diferencia_cuadre TEXT NOT NULL,
    filas_con_error INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS ix_corridas_periodo ON corridas (periodo, id);

CREATE TABLE IF NOT EXISTS movimientos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    corrida_id INTEGER NOT NULL REFERENCES corridas (id) ON DELETE CASCADE,
    periodo TEXT NOT NULL,
    fecha TEXT NOT NULL,                 -- YYYY-MM-DD (RELEASE_DATE)
    tipo TEXT NOT NULL,
    reference_id TEXT NOT NULL,
    neto_cent INTEGER NOT NULL,
    sircupa_cent INTEGER NOT NULL,
    sirtac_cent INTEGER NOT NULL,
    idc_cent INTEGER NOT NULL,
    gastos_cent INTEGER NOT NULL,
    mov_total_cent INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_movimientos_corrida_fecha ON movimientos (corrida_id, fecha);
CREATE INDEX IF NOT EXISTS ix_movimientos_periodo ON movimientos (periodo);

CREATE TABLE IF NOT EXISTS cargos_pendientes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    corrida_id INTEGER NOT NULL REFERENCES corridas (id) ON DELETE CASCADE,
    periodo TEXT NOT NULL,
    hoja TEXT NOT NULL,
    fila INTEGER NOT NULL,
    operacion_id TEXT NOT NULL,
    fecha TEXT NOT NULL,                 -- YYYY-MM-DD (fecha de la retención)
    importe_cent INTEGER NOT NULL,
    motivo TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_pendientes_corrida_fecha ON cargos_pendientes (corrida_id, fecha);
CREATE INDEX IF NOT EXISTS ix_pendientes_periodo ON cargos_pendientes (periodo);

CREATE TABLE IF NOT EXISTS usuarios_bot (
    chat_id TEXT PRIMARY KEY,
    nombre TEXT,
    vinculado_en TEXT NOT NULL,
    activo INTEGER NOT NULL DEFAULT 1 CHECK (activo IN (0, 1)),
    desvinculado_en TEXT
);
"""


@contextmanager
def conectar():
    """Abre una conexión nueva por operación (seguro para el pool de hilos de FastAPI)."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys = ON')
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# Columnas agregadas después de la primera versión del esquema: se crean en bases existentes.
MIGRACIONES_CORRIDAS = {
    'usuario': 'ALTER TABLE corridas ADD COLUMN usuario TEXT',
    'huella': 'ALTER TABLE corridas ADD COLUMN huella TEXT',
}


def init_db() -> None:
    with conectar() as conn:
        existentes = {f['name'] for f in conn.execute("PRAGMA table_info('corridas')")}
        if existentes:
            for columna, sentencia in MIGRACIONES_CORRIDAS.items():
                if columna not in existentes:
                    conn.execute(sentencia)
        conn.executescript(ESQUEMA)


# ---------------------------------------------------------------------------
# Conversión de importes y fechas
# ---------------------------------------------------------------------------

def a_centavos(valor) -> int:
    if valor is None:
        return 0
    return int((Decimal(str(valor)) * 100).quantize(Decimal('1'), rounding=ROUND_HALF_UP))


def de_centavos(valor) -> Decimal:
    return (Decimal(int(valor or 0)) / 100).quantize(CENT)


def _fecha_iso(valor) -> str:
    if isinstance(valor, datetime):
        return valor.date().isoformat()
    if isinstance(valor, date):
        return valor.isoformat()
    texto = str(valor).strip()
    for formato in ('%d/%m/%Y', '%d-%m-%Y', '%Y-%m-%d'):
        try:
            return datetime.strptime(texto, formato).date().isoformat()
        except ValueError:
            pass
    raise ValueError(f'Fecha inválida: {valor!r}')


# ---------------------------------------------------------------------------
# Corridas
# ---------------------------------------------------------------------------

def registrar_corrida(
    *,
    periodo: str,
    archivo: str,
    canal: str,
    chat_id: str | None,
    metricas: dict,
    cuadre: dict,
    usuario: str | None = None,
    huella: str | None = None,
    resultados: list[dict] | None = None,
    pendientes: list[dict] | None = None,
) -> int:
    """
    Guarda una corrida y, si se pasan, su detalle de movimientos y cargos pendientes.
    `metricas` viene de conciliar.calcular_metricas, `cuadre` de calcular_cuadre,
    `resultados` de calcular_totales y `pendientes` de detalle_pendientes.
    """
    ret = metricas['totales_retenciones']
    valores = {
        'fecha_ejecucion': ahora().isoformat(timespec='seconds'),
        'periodo': periodo,
        'archivo': archivo,
        'canal': canal,
        'chat_id': str(chat_id) if chat_id else None,
        'usuario': (usuario or '').strip() or None,
        'huella': huella,
        'movimientos': metricas['movimientos_totales'],
        'cargos_totales': metricas['cargos_totales'],
        'cargos_asociados': metricas['cargos_asociados'],
        'cargos_pendientes': metricas['cargos_pendientes'],
        'porcentaje_asociado': float(metricas['porcentaje_asociado']),
        'monto_pendiente': str(metricas['monto_pendiente']),
        'ingresos': str(metricas['ingresos']),
        'egresos': str(metricas['egresos']),
        'balance': str(metricas['balance']),
        'total_sircupa': str(ret['sircupa']),
        'total_sirtac': str(ret['sirtac']),
        'total_idc': str(ret['idc']),
        'total_gastos': str(ret['gastos']),
        'cuadre_ok': 1 if cuadre['ok'] else 0,
        'diferencia_cuadre': str(cuadre['total']['diferencia']),
        'filas_con_error': len(cuadre['filas_con_error']),
    }
    columnas = ', '.join(valores)
    marcadores = ', '.join(f':{c}' for c in valores)

    with conectar() as conn:
        corrida_id = int(conn.execute(f'INSERT INTO corridas ({columnas}) VALUES ({marcadores})', valores).lastrowid)

        if resultados is not None:
            conn.execute('DELETE FROM movimientos WHERE periodo = ? AND corrida_id <> ?', (periodo, corrida_id))
            conn.executemany(
                """INSERT INTO movimientos (corrida_id, periodo, fecha, tipo, reference_id, neto_cent,
                                            sircupa_cent, sirtac_cent, idc_cent, gastos_cent, mov_total_cent)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                [
                    (
                        corrida_id, periodo, _fecha_iso(r['fecha']), r['tipo'], r['reference_id'],
                        a_centavos(r['neto']), a_centavos(r['sircupa']), a_centavos(r['sirtac']),
                        a_centavos(r['idc']), a_centavos(r['gastos']),
                        a_centavos(r['neto'] if r['total'] is None else r['total']),
                    )
                    for r in resultados
                ],
            )

        if pendientes is not None:
            conn.execute('DELETE FROM cargos_pendientes WHERE periodo = ? AND corrida_id <> ?', (periodo, corrida_id))
            conn.executemany(
                """INSERT INTO cargos_pendientes (corrida_id, periodo, hoja, fila, operacion_id, fecha, importe_cent, motivo)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                [
                    (corrida_id, periodo, p['hoja'], p['fila'], p['id'], _fecha_iso(p['fecha']),
                     a_centavos(p['importe']), p['motivo'])
                    for p in pendientes
                ],
            )

        return corrida_id


def _fila_a_dict(fila: sqlite3.Row) -> dict:
    d = dict(fila)
    for campo in CAMPOS_MONTO:
        d[campo] = Decimal(d[campo])
    d['cuadre_ok'] = bool(d['cuadre_ok'])
    return d


def ultima_por_periodo(desde: str, hasta: str) -> list[dict]:
    """Última corrida de cada período entre `desde` y `hasta` (YYYY-MM, inclusive), ordenadas por período."""
    consulta = """
        SELECT c.*
        FROM corridas c
        JOIN (
            SELECT periodo, MAX(id) AS max_id
            FROM corridas
            WHERE periodo BETWEEN ? AND ?
            GROUP BY periodo
        ) u ON c.id = u.max_id
        ORDER BY c.periodo
    """
    with conectar() as conn:
        return [_fila_a_dict(f) for f in conn.execute(consulta, (desde, hasta)).fetchall()]


def ultima_corrida(periodo: str) -> dict | None:
    """Última corrida registrada de un período, o None si no hay."""
    with conectar() as conn:
        fila = conn.execute(
            'SELECT * FROM corridas WHERE periodo = ? ORDER BY id DESC LIMIT 1', (periodo,)
        ).fetchone()
        return _fila_a_dict(fila) if fila else None


def historial(limite: int = 10) -> list[dict]:
    """
    Últimas corridas registradas, de la más reciente a la más antigua. Cada una indica cómo se compara
    con la corrida anterior del mismo período: 'nuevo', 'identico', 'distinto' o 'sin_huella'.
    """
    consulta = """
        SELECT * FROM (
            SELECT c.*,
                   LAG(c.id) OVER (PARTITION BY c.periodo ORDER BY c.id) AS id_anterior,
                   LAG(c.huella) OVER (PARTITION BY c.periodo ORDER BY c.id) AS huella_anterior
            FROM corridas c
        )
        ORDER BY id DESC
        LIMIT ?
    """
    with conectar() as conn:
        resultado = []
        for fila in conn.execute(consulta, (limite,)).fetchall():
            d = _fila_a_dict(fila)
            if d['id_anterior'] is None:
                d['comparacion'] = 'nuevo'
            elif not d['huella'] or not d['huella_anterior']:
                d['comparacion'] = 'sin_huella'
            else:
                d['comparacion'] = 'identico' if d['huella'] == d['huella_anterior'] else 'distinto'
            resultado.append(d)
        return resultado


def resumir(corridas: list[dict]) -> dict:
    """Totales acumulados de un conjunto de corridas (una por período)."""
    total = {campo: Decimal('0') for campo in CAMPOS_MONTO if campo != 'diferencia_cuadre'}
    enteros = {campo: 0 for campo in CAMPOS_ENTEROS}
    for c in corridas:
        for campo in total:
            total[campo] += c[campo]
        for campo in enteros:
            enteros[campo] += c[campo]
    porcentaje = (
        round(enteros['cargos_asociados'] * 100 / enteros['cargos_totales'], 2)
        if enteros['cargos_totales'] else 100.0
    )
    return {
        **enteros,
        **total,
        'porcentaje_asociado': porcentaje,
        'periodos': len(corridas),
        'periodos_con_pendientes': sum(1 for c in corridas if c['cargos_pendientes'] > 0),
        'periodos_descuadrados': sum(1 for c in corridas if not c['cuadre_ok']),
    }


# ---------------------------------------------------------------------------
# Resumen por rango de fechas
# ---------------------------------------------------------------------------

def resumen_por_dias(corrida_ids: list[int], desde: str, hasta: str) -> dict:
    """
    Agrega el detalle de las corridas indicadas entre dos fechas (YYYY-MM-DD, inclusive).
    Devuelve los totales, el detalle por día y los ids de corridas que no tienen detalle guardado.
    """
    if not corrida_ids:
        return {'dias': [], 'totales': _totales_dias_vacios(), 'corridas_sin_detalle': []}

    marcadores = ', '.join('?' for _ in corrida_ids)
    with conectar() as conn:
        con_detalle = {
            f['corrida_id'] for f in conn.execute(
                f'SELECT DISTINCT corrida_id FROM movimientos WHERE corrida_id IN ({marcadores})', corrida_ids
            )
        }
        filas = conn.execute(
            f"""SELECT fecha,
                       COUNT(*) AS movimientos,
                       SUM(CASE WHEN neto_cent > 0 THEN neto_cent ELSE 0 END) AS ingresos,
                       SUM(CASE WHEN neto_cent < 0 THEN -neto_cent ELSE 0 END) AS egresos,
                       SUM(neto_cent) AS balance,
                       SUM(sircupa_cent) AS sircupa,
                       SUM(sirtac_cent) AS sirtac,
                       SUM(idc_cent) AS idc,
                       SUM(gastos_cent) AS gastos,
                       SUM(mov_total_cent) AS mov_total
                FROM movimientos
                WHERE corrida_id IN ({marcadores}) AND fecha BETWEEN ? AND ?
                GROUP BY fecha
                ORDER BY fecha""",
            [*corrida_ids, desde, hasta],
        ).fetchall()
        pend = conn.execute(
            f"""SELECT COUNT(*) AS cantidad, COALESCE(SUM(importe_cent), 0) AS importe
                FROM cargos_pendientes
                WHERE corrida_id IN ({marcadores}) AND fecha BETWEEN ? AND ?""",
            [*corrida_ids, desde, hasta],
        ).fetchone()
        pend_por_dia = {
            f['fecha']: (f['cantidad'], f['importe'])
            for f in conn.execute(
                f"""SELECT fecha, COUNT(*) AS cantidad, SUM(importe_cent) AS importe
                    FROM cargos_pendientes
                    WHERE corrida_id IN ({marcadores}) AND fecha BETWEEN ? AND ?
                    GROUP BY fecha""",
                [*corrida_ids, desde, hasta],
            )
        }

    dias = []
    for f in filas:
        cant_pend, imp_pend = pend_por_dia.get(f['fecha'], (0, 0))
        dias.append({
            'fecha': f['fecha'],
            'movimientos': f['movimientos'],
            'ingresos': de_centavos(f['ingresos']),
            'egresos': de_centavos(f['egresos']),
            'balance': de_centavos(f['balance']),
            'sircupa': de_centavos(f['sircupa']),
            'sirtac': de_centavos(f['sirtac']),
            'idc': de_centavos(f['idc']),
            'gastos': de_centavos(f['gastos']),
            'mov_total': de_centavos(f['mov_total']),
            'cargos_pendientes': cant_pend,
            'monto_pendiente': de_centavos(imp_pend),
        })

    totales = _totales_dias_vacios()
    for d in dias:
        totales['movimientos'] += d['movimientos']
        for campo in ('ingresos', 'egresos', 'balance', 'sircupa', 'sirtac', 'idc', 'gastos', 'mov_total'):
            totales[campo] += d[campo]
    totales['dias_con_movimientos'] = len(dias)
    totales['cargos_pendientes'] = pend['cantidad']
    totales['monto_pendiente'] = de_centavos(pend['importe'])

    return {
        'dias': dias,
        'totales': totales,
        'corridas_sin_detalle': [i for i in corrida_ids if i not in con_detalle],
    }


def _totales_dias_vacios() -> dict:
    return {
        'movimientos': 0,
        'dias_con_movimientos': 0,
        'ingresos': Decimal('0.00'),
        'egresos': Decimal('0.00'),
        'balance': Decimal('0.00'),
        'sircupa': Decimal('0.00'),
        'sirtac': Decimal('0.00'),
        'idc': Decimal('0.00'),
        'gastos': Decimal('0.00'),
        'mov_total': Decimal('0.00'),
        'cargos_pendientes': 0,
        'monto_pendiente': Decimal('0.00'),
    }


# ---------------------------------------------------------------------------
# Usuarios del bot
# ---------------------------------------------------------------------------

def usuario_activo(chat_id: str | int) -> bool:
    with conectar() as conn:
        fila = conn.execute('SELECT activo FROM usuarios_bot WHERE chat_id = ?', (str(chat_id),)).fetchone()
        return bool(fila and fila['activo'])


def vincular_usuario(chat_id: str | int, nombre: str | None) -> bool:
    """Activa al usuario. Devuelve True si ya estaba vinculado."""
    ya_estaba = usuario_activo(chat_id)
    with conectar() as conn:
        conn.execute(
            """INSERT INTO usuarios_bot (chat_id, nombre, vinculado_en, activo, desvinculado_en)
               VALUES (?, ?, ?, 1, NULL)
               ON CONFLICT (chat_id) DO UPDATE SET
                   nombre = excluded.nombre,
                   vinculado_en = CASE WHEN usuarios_bot.activo = 1 THEN usuarios_bot.vinculado_en ELSE excluded.vinculado_en END,
                   activo = 1,
                   desvinculado_en = NULL""",
            (str(chat_id), nombre, ahora().isoformat(timespec='seconds')),
        )
    return ya_estaba


def desvincular_usuario(chat_id: str | int) -> bool:
    """Desactiva al usuario. Devuelve True si estaba vinculado."""
    with conectar() as conn:
        cur = conn.execute(
            'UPDATE usuarios_bot SET activo = 0, desvinculado_en = ? WHERE chat_id = ? AND activo = 1',
            (ahora().isoformat(timespec='seconds'), str(chat_id)),
        )
        return cur.rowcount > 0


def listar_usuarios(solo_activos: bool = True) -> list[dict]:
    consulta = 'SELECT * FROM usuarios_bot'
    if solo_activos:
        consulta += ' WHERE activo = 1'
    consulta += ' ORDER BY vinculado_en'
    with conectar() as conn:
        return [{**dict(f), 'activo': bool(f['activo'])} for f in conn.execute(consulta).fetchall()]
