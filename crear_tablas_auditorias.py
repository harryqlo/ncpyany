"""
Script de setup para el módulo de Auditorías de Inventario.
Crea las tablas necesarias en la BD y los planes base.
Ejecutar una sola vez: python crear_tablas_auditorias.py
"""
import sqlite3
import os
import sys
from datetime import date, timedelta

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

try:
    from config import DB_PATH
except ImportError:
    DB_PATH = os.path.join(BASE_DIR, 'system', 'system.db')


DDL = [
    # ── Planes de auditoría (configuración recurrente) ──────────────────────
    """
    CREATE TABLE IF NOT EXISTS auditorias_planes (
        id                INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre            TEXT    NOT NULL,
        tipo              TEXT    NOT NULL
                          CHECK(tipo IN ('rotativo','semanal','mensual','spot')),
        activo            INTEGER NOT NULL DEFAULT 1,
        total_ciclos      INTEGER NOT NULL DEFAULT 4,
        ciclo_actual      INTEGER NOT NULL DEFAULT 1,
        dia_semana        INTEGER DEFAULT 1,
        dia_mes           INTEGER DEFAULT 1,
        filtro_categoria  TEXT,
        filtro_clase      TEXT,
        fecha_creacion    TEXT    DEFAULT (date('now')),
        fecha_proxima     TEXT,
        creado_por        TEXT    DEFAULT 'sistema'
    )
    """,
    # ── Sesiones (instancias ejecutadas de cada plan) ────────────────────────
    """
    CREATE TABLE IF NOT EXISTS auditorias_sesiones (
        id                   INTEGER PRIMARY KEY AUTOINCREMENT,
        plan_id              INTEGER REFERENCES auditorias_planes(id),
        tipo                 TEXT    NOT NULL,
        estado               TEXT    NOT NULL DEFAULT 'pendiente'
                             CHECK(estado IN ('pendiente','en_progreso','completada','cancelada')),
        fecha_inicio         TEXT,
        fecha_fin            TEXT,
        auditado_por         TEXT,
        total_items          INTEGER DEFAULT 0,
        items_contados       INTEGER DEFAULT 0,
        items_con_diferencia INTEGER DEFAULT 0,
        ciclo_numero         INTEGER,
        semana_iso           TEXT,
        mes_periodo          TEXT,
        observaciones        TEXT,
        ajustes_aplicados    INTEGER DEFAULT 0,
        created_at           TEXT    DEFAULT (datetime('now'))
    )
    """,
    # ── Detalle ítem × sesión ─────────────────────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS auditorias_detalle (
        id             INTEGER PRIMARY KEY AUTOINCREMENT,
        sesion_id      INTEGER NOT NULL
                       REFERENCES auditorias_sesiones(id) ON DELETE CASCADE,
        item_sku       TEXT    NOT NULL,
        item_nombre    TEXT,
        categoria      TEXT,
        clase_abc      TEXT    DEFAULT 'C',
        stock_sistema  REAL,
        stock_contado  REAL,
        diferencia     REAL,
        pct_desviacion REAL,
        ajustado       INTEGER NOT NULL DEFAULT 0,
        observaciones  TEXT,
        fecha_conteo   TEXT,
        contado_por    TEXT,
        UNIQUE(sesion_id, item_sku)
    )
    """,
    # ── Ajustes de stock generados por auditoría ────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS auditorias_ajustes (
        id            INTEGER PRIMARY KEY AUTOINCREMENT,
        sesion_id     INTEGER NOT NULL
                      REFERENCES auditorias_sesiones(id),
        detalle_id    INTEGER REFERENCES auditorias_detalle(id),
        item_sku      TEXT    NOT NULL,
        stock_antes   REAL,
        stock_despues REAL,
        diferencia    REAL,
        motivo        TEXT    DEFAULT 'Ajuste por auditoría',
        aplicado_en   TEXT    DEFAULT (datetime('now')),
        aplicado_por  TEXT
    )
    """,
    # ── Clasificación ABC por ítem ──────────────────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS items_clasificacion_abc (
        item_sku              TEXT PRIMARY KEY,
        clase                 TEXT NOT NULL CHECK(clase IN ('A','B','C')),
        valor_anual           REAL DEFAULT 0,
        pct_acumulado         REAL DEFAULT 0,
        frecuencia_conteo_dias INTEGER DEFAULT 30,
        ultimo_conteo         TEXT,
        proximo_conteo        TEXT,
        updated_at            TEXT DEFAULT (date('now'))
    )
    """,
]

INDICES = [
    "CREATE INDEX IF NOT EXISTS idx_aud_ses_tipo    ON auditorias_sesiones(tipo)",
    "CREATE INDEX IF NOT EXISTS idx_aud_ses_estado  ON auditorias_sesiones(estado)",
    "CREATE INDEX IF NOT EXISTS idx_aud_ses_semana  ON auditorias_sesiones(semana_iso)",
    "CREATE INDEX IF NOT EXISTS idx_aud_ses_mes     ON auditorias_sesiones(mes_periodo)",
    "CREATE INDEX IF NOT EXISTS idx_aud_det_sesion  ON auditorias_detalle(sesion_id)",
    "CREATE INDEX IF NOT EXISTS idx_aud_det_sku     ON auditorias_detalle(item_sku)",
    "CREATE INDEX IF NOT EXISTS idx_aud_ajuste_ses  ON auditorias_ajustes(sesion_id)",
]


def crear_tablas(conn):
    c = conn.cursor()
    for ddl in DDL:
        c.execute(ddl)
    for idx in INDICES:
        c.execute(idx)
    conn.commit()
    print("✓ Tablas de auditorías creadas / verificadas")


def insertar_planes_base(conn):
    c = conn.cursor()
    hoy = date.today()

    # Próximo lunes
    dias_lunes = (7 - hoy.weekday()) % 7 or 7
    proximo_lunes = (hoy + timedelta(days=dias_lunes)).isoformat()

    # Primer día del próximo mes
    if hoy.month == 12:
        proximo_mes = date(hoy.year + 1, 1, 1).isoformat()
    else:
        proximo_mes = date(hoy.year, hoy.month + 1, 1).isoformat()

    planes = [
        {
            'nombre': 'Inventario Rotativo (4 Ciclos)',
            'tipo': 'rotativo',
            'total_ciclos': 4,
            'dia_semana': 1,
            'dia_mes': 1,
            'fecha_proxima': proximo_lunes,
        },
        {
            'nombre': 'Inventario Semanal Completo',
            'tipo': 'semanal',
            'total_ciclos': 1,
            'dia_semana': 5,   # viernes
            'dia_mes': 1,
            'fecha_proxima': proximo_lunes,
        },
        {
            'nombre': 'Inventario Mensual Completo',
            'tipo': 'mensual',
            'total_ciclos': 1,
            'dia_semana': 1,
            'dia_mes': 1,
            'fecha_proxima': proximo_mes,
        },
    ]

    creados = 0
    for p in planes:
        existe = c.execute(
            "SELECT id FROM auditorias_planes WHERE tipo=? AND activo=1",
            [p['tipo']]
        ).fetchone()
        if not existe:
            c.execute(
                """INSERT INTO auditorias_planes
                   (nombre,tipo,total_ciclos,dia_semana,dia_mes,fecha_proxima,creado_por)
                   VALUES (:nombre,:tipo,:total_ciclos,:dia_semana,:dia_mes,:fecha_proxima,'sistema')""",
                p
            )
            creados += 1

    conn.commit()
    if creados:
        print(f"✓ {creados} plan(es) base insertados")
    else:
        print("  (planes base ya existen, sin cambios)")


if __name__ == '__main__':
    db_path = str(DB_PATH)
    print(f"Base de datos: {db_path}")

    if not os.path.exists(db_path):
        print(f"✗ No se encontró la BD en: {db_path}")
        sys.exit(1)

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")

    try:
        crear_tablas(conn)
        insertar_planes_base(conn)
        print("\n✅ Setup de auditorías completado.")
        print("   → Ejecuta 'python calcular_abc.py' para clasificar los ítems.")
    except Exception as e:
        conn.rollback()
        print(f"✗ Error durante el setup: {e}")
        sys.exit(1)
    finally:
        conn.close()
