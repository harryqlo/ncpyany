"""
Blueprint de Auditorías de Inventario — North Chrome v2

Endpoints:
  GET    /api/auditorias/estadisticas
  GET    /api/auditorias/clasificacion-abc
  GET    /api/auditorias/planes
  POST   /api/auditorias/planes
  PUT    /api/auditorias/planes/<id>
  GET    /api/auditorias/sesiones
  POST   /api/auditorias/sesiones
  GET    /api/auditorias/sesiones/<id>
  PUT    /api/auditorias/sesiones/<id>/estado
  POST   /api/auditorias/sesiones/<id>/conteo
  POST   /api/auditorias/sesiones/<id>/conteo-lote
  POST   /api/auditorias/sesiones/<id>/aplicar-ajustes
  GET    /api/auditorias/sesiones/<id>/reporte-html
  POST   /api/auditorias/recalcular-abc
"""
from flask import Blueprint, jsonify, request
from app.db import get_db
from app.search_utils import contains_terms_where
from datetime import datetime, date, timedelta

bp = Blueprint('auditorias', __name__, url_prefix='/api/auditorias')


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS INTERNOS
# ─────────────────────────────────────────────────────────────────────────────

def _semana_iso(d=None):
    d = d or date.today()
    return d.strftime('%G-W%V')


def _mes_periodo(d=None):
    d = d or date.today()
    return d.strftime('%Y-%m')


def _tabla_existe(c, nombre):
    row = c.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?", [nombre]
    ).fetchone()
    return row is not None


def _ensure_auditorias_schema(c):
    """Crea el esquema y los planes base del módulo si aún no existen."""
    c.execute("""
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
    """)
    c.execute("""
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
    """)
    c.execute("""
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
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS auditorias_ajustes (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            sesion_id     INTEGER NOT NULL REFERENCES auditorias_sesiones(id),
            detalle_id    INTEGER REFERENCES auditorias_detalle(id),
            item_sku      TEXT    NOT NULL,
            stock_antes   REAL,
            stock_despues REAL,
            diferencia    REAL,
            motivo        TEXT    DEFAULT 'Ajuste por auditoría',
            aplicado_en   TEXT    DEFAULT (datetime('now')),
            aplicado_por  TEXT
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS items_clasificacion_abc (
            item_sku               TEXT PRIMARY KEY,
            clase                  TEXT NOT NULL CHECK(clase IN ('A','B','C')),
            valor_anual            REAL DEFAULT 0,
            pct_acumulado          REAL DEFAULT 0,
            frecuencia_conteo_dias INTEGER DEFAULT 30,
            ultimo_conteo          TEXT,
            proximo_conteo         TEXT,
            updated_at             TEXT DEFAULT (date('now'))
        )
    """)

    c.execute("CREATE INDEX IF NOT EXISTS idx_aud_ses_tipo   ON auditorias_sesiones(tipo)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_aud_ses_estado ON auditorias_sesiones(estado)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_aud_ses_semana ON auditorias_sesiones(semana_iso)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_aud_ses_mes    ON auditorias_sesiones(mes_periodo)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_aud_det_sesion ON auditorias_detalle(sesion_id)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_aud_det_sku    ON auditorias_detalle(item_sku)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_aud_ajuste_ses ON auditorias_ajustes(sesion_id)")

    hoy = date.today()
    dias_lunes = (7 - hoy.weekday()) % 7 or 7
    proximo_lunes = (hoy + timedelta(days=dias_lunes)).isoformat()
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
            'dia_semana': 5,
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

    for plan in planes:
        existe = c.execute(
            "SELECT id FROM auditorias_planes WHERE tipo=? AND activo=1",
            [plan['tipo']]
        ).fetchone()
        if existe:
            continue
        c.execute(
            """INSERT INTO auditorias_planes
               (nombre, tipo, total_ciclos, dia_semana, dia_mes, fecha_proxima, creado_por)
               VALUES (:nombre, :tipo, :total_ciclos, :dia_semana, :dia_mes, :fecha_proxima, 'sistema')""",
            plan
        )

    c.commit()


def _seleccionar_items(c, tipo, ciclo=None, total_ciclos=None,
                       filtro_categoria=None, filtro_clase=None):
    """
    Devuelve la lista de ítems a incluir en la sesión según el tipo:
      - rotativo : divide el inventario en `total_ciclos` grupos; toma el `ciclo`-ésimo
      - semanal  : todos los ítems (con filtros opcionales)
      - mensual  : todos los ítems (con filtros opcionales)
      - spot     : filtros libres
    """
    w = ["i.sku IS NOT NULL", "i.sku <> ''"]
    p = []

    if filtro_categoria:
        w.append("i.categoria_nombre = ?")
        p.append(filtro_categoria)

    if filtro_clase:
        w.append("COALESCE(abc.clase,'C') = ?")
        p.append(filtro_clase)

    sql = """
        SELECT
            i.sku,
            i.nombre,
            i.categoria_nombre,
            COALESCE(abc.clase, 'C')           AS clase_abc,
            COALESCE(i.stock_actual, 0)        AS stock_sistema,
            COALESCE(abc.frecuencia_conteo_dias, 30) AS frecuencia
        FROM items i
        LEFT JOIN (
            SELECT item_sku,
                   MAX(clase)                    AS clase,
                   MAX(frecuencia_conteo_dias)   AS frecuencia_conteo_dias
            FROM items_clasificacion_abc
            GROUP BY item_sku
        ) abc ON abc.item_sku = i.sku
        WHERE {where}
        GROUP BY i.sku
        ORDER BY i.rowid
    """.format(where=' AND '.join(w))

    rows = c.execute(sql, p).fetchall()

    # Rotativo: distribuir en ciclos rotativos
    if tipo == 'rotativo' and total_ciclos and total_ciclos > 1 and ciclo is not None:
        ciclo_idx = (ciclo - 1) % total_ciclos
        rows = [r for idx, r in enumerate(rows) if idx % total_ciclos == ciclo_idx]

    return rows


# ─────────────────────────────────────────────────────────────────────────────
# ESTADÍSTICAS GENERALES
# ─────────────────────────────────────────────────────────────────────────────

@bp.route('/estadisticas', strict_slashes=False)
def estadisticas():
    c = get_db()
    try:
        _ensure_auditorias_schema(c)

        total_ses = c.execute("SELECT COUNT(*) FROM auditorias_sesiones").fetchone()[0]
        completadas = c.execute(
            "SELECT COUNT(*) FROM auditorias_sesiones WHERE estado='completada'"
        ).fetchone()[0]
        pendientes = c.execute(
            "SELECT COUNT(*) FROM auditorias_sesiones WHERE estado IN ('pendiente','en_progreso')"
        ).fetchone()[0]

        ajuste_row = c.execute(
            "SELECT COUNT(*), COALESCE(SUM(ABS(diferencia)),0) FROM auditorias_ajustes"
        ).fetchone()

        abc_rows = c.execute(
            "SELECT clase, COUNT(*) FROM items_clasificacion_abc GROUP BY clase"
        ).fetchall()
        clasificacion_abc = {r[0]: r[1] for r in abc_rows}

        proximas = c.execute("""
            SELECT nombre, tipo, fecha_proxima, ciclo_actual, total_ciclos
            FROM auditorias_planes
            WHERE activo=1
            ORDER BY fecha_proxima
            LIMIT 5
        """).fetchall()

        historial = c.execute("""
            SELECT
                strftime('%Y-%m', created_at)  AS mes,
                COUNT(*)                        AS sesiones,
                SUM(COALESCE(items_con_diferencia,0)) AS diferencias,
                SUM(COALESCE(ajustes_aplicados,0))    AS ajustes
            FROM auditorias_sesiones
            GROUP BY mes
            ORDER BY mes DESC
            LIMIT 12
        """).fetchall()

        items_pendientes_conteo = c.execute("""
            SELECT COUNT(*) FROM items_clasificacion_abc
            WHERE proximo_conteo <= date('now')
        """).fetchone()[0]

        return jsonify({
            'ok': True,
            'total_sesiones': total_ses,
            'completadas': completadas,
            'pendientes': pendientes,
            'total_ajustes': ajuste_row[0],
            'valor_ajustes': round(ajuste_row[1], 2),
            'clasificacion_abc': clasificacion_abc,
            'items_pendientes_conteo': items_pendientes_conteo,
            'proximas_auditorias': [dict(r) for r in proximas],
            'historial_mensual': [dict(r) for r in historial],
        })
    except ValueError as e:
        return jsonify({'ok': False, 'msg': str(e), 'setup_required': True}), 400
    finally:
        c.close()


# ─────────────────────────────────────────────────────────────────────────────
# CLASIFICACIÓN ABC
# ─────────────────────────────────────────────────────────────────────────────

@bp.route('/clasificacion-abc', strict_slashes=False)
def get_clasificacion_abc():
    c = get_db()
    try:
        _ensure_auditorias_schema(c)
        pg = int(request.args.get('page', 1))
        pp = int(request.args.get('per_page', 50))
        clase = request.args.get('clase', '').strip().upper()
        buscar = request.args.get('search', '').strip()

        w, p = [], []
        if clase:
            w.append("a.clase=?"); p.append(clase)
        if buscar:
            search_where, search_params = contains_terms_where(buscar, ['a.item_sku', 'i.nombre'])
            if search_where:
                w.append(search_where)
                p += search_params

        ws = (' WHERE ' + ' AND '.join(w)) if w else ''
        total = c.execute(
            f"SELECT COUNT(*) FROM items_clasificacion_abc a LEFT JOIN items i ON i.sku=a.item_sku{ws}", p
        ).fetchone()[0]

        off = (pg - 1) * pp
        rows = c.execute(f"""
            SELECT a.item_sku, i.nombre, a.clase, a.valor_anual,
                   a.pct_acumulado, a.frecuencia_conteo_dias,
                   a.ultimo_conteo, a.proximo_conteo, a.updated_at,
                   COALESCE(i.stock_actual,0) AS stock_actual,
                   CASE WHEN a.proximo_conteo <= date('now') THEN 1 ELSE 0 END AS vencido
            FROM items_clasificacion_abc a
            LEFT JOIN items i ON i.sku = a.item_sku
            {ws}
            ORDER BY a.pct_acumulado
            LIMIT ? OFFSET ?
        """, p + [pp, off]).fetchall()

        return jsonify({
            'ok': True,
            'items': [dict(r) for r in rows],
            'total': total, 'page': pg, 'per_page': pp,
            'total_pages': max(1, -(-total // pp)),
        })
    except ValueError as e:
        return jsonify({'ok': False, 'msg': str(e), 'setup_required': True}), 400
    finally:
        c.close()


@bp.route('/recalcular-abc', methods=['POST'], strict_slashes=False)
def recalcular_abc():
    """Recalcula la clasificación ABC usando la lógica del script calcular_abc.py."""
    try:
        from calcular_abc import calcular
        d = request.json or {}
        umbral_a = float(d.get('umbral_a', 80.0))
        umbral_b = float(d.get('umbral_b', 95.0))
        resultado = calcular(umbral_a=umbral_a, umbral_b=umbral_b, verbose=False)
        return jsonify({'ok': True, 'resultado': resultado})
    except Exception as e:
        return jsonify({'ok': False, 'msg': str(e)}), 500


# ─────────────────────────────────────────────────────────────────────────────
# PLANES
# ─────────────────────────────────────────────────────────────────────────────

@bp.route('/planes', strict_slashes=False)
def get_planes():
    c = get_db()
    try:
        _ensure_auditorias_schema(c)
        rows = c.execute(
            "SELECT * FROM auditorias_planes ORDER BY tipo, id"
        ).fetchall()
        return jsonify({'ok': True, 'items': [dict(r) for r in rows]})
    except ValueError as e:
        return jsonify({'ok': False, 'msg': str(e), 'setup_required': True}), 400
    finally:
        c.close()


@bp.route('/planes', methods=['POST'], strict_slashes=False)
def crear_plan():
    c = get_db()
    try:
        _ensure_auditorias_schema(c)
        d = request.json or {}
        nombre = d.get('nombre', '').strip()
        tipo = d.get('tipo', 'spot')
        if not nombre:
            return jsonify({'ok': False, 'msg': 'El nombre es requerido'}), 400
        if tipo not in ('rotativo', 'semanal', 'mensual', 'spot'):
            return jsonify({'ok': False, 'msg': 'Tipo inválido'}), 400

        cur = c.execute("""
            INSERT INTO auditorias_planes
                (nombre, tipo, total_ciclos, dia_semana, dia_mes,
                 filtro_categoria, filtro_clase, fecha_proxima, creado_por)
            VALUES (?,?,?,?,?,?,?,?,?)
        """, [
            nombre, tipo,
            int(d.get('total_ciclos', 4)),
            int(d.get('dia_semana', 1)),
            int(d.get('dia_mes', 1)),
            d.get('filtro_categoria') or None,
            d.get('filtro_clase') or None,
            d.get('fecha_proxima') or None,
            d.get('creado_por', 'usuario'),
        ])
        c.commit()
        return jsonify({'ok': True, 'id': cur.lastrowid})
    except ValueError as e:
        return jsonify({'ok': False, 'msg': str(e), 'setup_required': True}), 400
    except Exception as e:
        return jsonify({'ok': False, 'msg': str(e)}), 400
    finally:
        c.close()


@bp.route('/planes/<int:plan_id>', methods=['PUT'], strict_slashes=False)
def actualizar_plan(plan_id):
    c = get_db()
    try:
        _ensure_auditorias_schema(c)
        d = request.json or {}
        campos = []
        valores = []
        PERMITIDOS = {
            'nombre', 'activo', 'total_ciclos', 'dia_semana', 'dia_mes',
            'filtro_categoria', 'filtro_clase', 'fecha_proxima'
        }
        for k, v in d.items():
            if k in PERMITIDOS:
                campos.append(f"{k}=?")
                valores.append(v)
        if not campos:
            return jsonify({'ok': False, 'msg': 'Sin campos para actualizar'}), 400
        valores.append(plan_id)
        c.execute(f"UPDATE auditorias_planes SET {','.join(campos)} WHERE id=?", valores)
        c.commit()
        return jsonify({'ok': True})
    except ValueError as e:
        return jsonify({'ok': False, 'msg': str(e)}), 400
    finally:
        c.close()


# ─────────────────────────────────────────────────────────────────────────────
# SESIONES
# ─────────────────────────────────────────────────────────────────────────────

@bp.route('/sesiones', strict_slashes=False)
def get_sesiones():
    c = get_db()
    try:
        _ensure_auditorias_schema(c)
        pg = int(request.args.get('page', 1))
        pp = int(request.args.get('per_page', 20))
        tipo = request.args.get('tipo', '').strip()
        estado = request.args.get('estado', '').strip()
        mes = request.args.get('mes', '').strip()

        w, p = [], []
        if tipo:
            w.append("tipo=?"); p.append(tipo)
        if estado:
            w.append("estado=?"); p.append(estado)
        if mes:
            w.append("mes_periodo=?"); p.append(mes)

        ws = (' WHERE ' + ' AND '.join(w)) if w else ''
        total = c.execute(f"SELECT COUNT(*) FROM auditorias_sesiones{ws}", p).fetchone()[0]
        off = (pg - 1) * pp
        rows = c.execute(
            f"SELECT * FROM auditorias_sesiones{ws} ORDER BY id DESC LIMIT ? OFFSET ?",
            p + [pp, off]
        ).fetchall()

        return jsonify({
            'ok': True,
            'items': [dict(r) for r in rows],
            'total': total, 'page': pg, 'per_page': pp,
            'total_pages': max(1, -(-total // pp)),
        })
    except ValueError as e:
        return jsonify({'ok': False, 'msg': str(e), 'setup_required': True}), 400
    finally:
        c.close()


@bp.route('/sesiones', methods=['POST'], strict_slashes=False)
def crear_sesion():
    """
    Crea una nueva sesión de auditoría y puebla `auditorias_detalle`
    con un snapshot del stock actual de los ítems seleccionados.
    """
    c = get_db()
    try:
        _ensure_auditorias_schema(c)
        d = request.json or {}
        tipo = d.get('tipo', 'spot')
        plan_id = d.get('plan_id')
        auditado_por = d.get('auditado_por', 'usuario')
        filtro_categoria = d.get('filtro_categoria') or None
        filtro_clase = d.get('filtro_clase') or None

        ciclo = None
        total_ciclos = None
        if plan_id:
            plan = c.execute(
                "SELECT * FROM auditorias_planes WHERE id=?", [plan_id]
            ).fetchone()
            if not plan:
                return jsonify({'ok': False, 'msg': f'Plan {plan_id} no encontrado'}), 404
            if not filtro_categoria:
                filtro_categoria = plan['filtro_categoria']
            if not filtro_clase:
                filtro_clase = plan['filtro_clase']
            ciclo = plan['ciclo_actual']
            total_ciclos = plan['total_ciclos']

        items = _seleccionar_items(
            c, tipo, ciclo, total_ciclos, filtro_categoria, filtro_clase
        )

        if not items:
            return jsonify({
                'ok': False,
                'msg': 'Sin ítems para auditar con los filtros indicados. '
                       'Verifica que existan ítems en el inventario y ejecuta calcular_abc.py.'
            }), 400

        ahora = datetime.now().isoformat(timespec='seconds')
        cur = c.execute("""
            INSERT INTO auditorias_sesiones
                (plan_id, tipo, estado, fecha_inicio, auditado_por,
                 total_items, ciclo_numero, semana_iso, mes_periodo)
            VALUES (?,?,?,?,?,?,?,?,?)
        """, [
            plan_id, tipo, 'pendiente', ahora, auditado_por,
            len(items), ciclo, _semana_iso(), _mes_periodo()
        ])
        sesion_id = cur.lastrowid

        for it in items:
            c.execute("""
                INSERT OR IGNORE INTO auditorias_detalle
                    (sesion_id, item_sku, item_nombre, categoria,
                     clase_abc, stock_sistema)
                VALUES (?,?,?,?,?,?)
            """, [
                sesion_id, it['sku'], it['nombre'],
                it['categoria_nombre'], it['clase_abc'], it['stock_sistema']
            ])

        # Avanzar ciclo en plan rotativo
        if plan_id and tipo == 'rotativo' and total_ciclos:
            nuevo_ciclo = (ciclo % total_ciclos) + 1
            prox = (date.today() + timedelta(days=7)).isoformat()
            c.execute(
                "UPDATE auditorias_planes SET ciclo_actual=?, fecha_proxima=? WHERE id=?",
                [nuevo_ciclo, prox, plan_id]
            )
        elif plan_id and tipo == 'semanal':
            prox = (date.today() + timedelta(weeks=1)).isoformat()
            c.execute(
                "UPDATE auditorias_planes SET fecha_proxima=? WHERE id=?",
                [prox, plan_id]
            )
        elif plan_id and tipo == 'mensual':
            hoy = date.today()
            if hoy.month == 12:
                prox = date(hoy.year + 1, 1, 1).isoformat()
            else:
                prox = date(hoy.year, hoy.month + 1, 1).isoformat()
            c.execute(
                "UPDATE auditorias_planes SET fecha_proxima=? WHERE id=?",
                [prox, plan_id]
            )

        c.commit()
        return jsonify({
            'ok': True,
            'sesion_id': sesion_id,
            'total_items': len(items),
            'tipo': tipo,
            'ciclo': ciclo,
        })
    except ValueError as e:
        return jsonify({'ok': False, 'msg': str(e)}), 400
    except Exception as e:
        c.rollback()
        return jsonify({'ok': False, 'msg': str(e)}), 500
    finally:
        c.close()


@bp.route('/sesiones/<int:sid>', strict_slashes=False)
def get_sesion(sid):
    c = get_db()
    try:
        _ensure_auditorias_schema(c)
        sesion = c.execute(
            "SELECT * FROM auditorias_sesiones WHERE id=?", [sid]
        ).fetchone()
        if not sesion:
            return jsonify({'ok': False, 'msg': 'Sesión no encontrada'}), 404

        items = c.execute("""
            SELECT d.*,
                   COALESCE(i.stock_actual, d.stock_sistema) AS stock_real_actual
            FROM auditorias_detalle d
            LEFT JOIN items i ON i.sku = d.item_sku
            WHERE d.sesion_id = ?
            ORDER BY d.clase_abc, d.item_nombre
        """, [sid]).fetchall()

        return jsonify({
            'ok': True,
            'sesion': dict(sesion),
            'items': [dict(i) for i in items],
        })
    except ValueError as e:
        return jsonify({'ok': False, 'msg': str(e)}), 400
    finally:
        c.close()


@bp.route('/sesiones/<int:sid>/estado', methods=['PUT'], strict_slashes=False)
def cambiar_estado(sid):
    c = get_db()
    try:
        _ensure_auditorias_schema(c)
        d = request.json or {}
        nuevo = d.get('estado', '')
        VALIDOS = ('pendiente', 'en_progreso', 'completada', 'cancelada')
        if nuevo not in VALIDOS:
            return jsonify({'ok': False, 'msg': f'Estado inválido. Use: {VALIDOS}'}), 400

        sets = ["estado=?"]
        params = [nuevo]
        if nuevo in ('completada', 'cancelada'):
            sets.append("fecha_fin=?")
            params.append(datetime.now().isoformat(timespec='seconds'))
        if d.get('observaciones'):
            sets.append("observaciones=?")
            params.append(d['observaciones'])
        params.append(sid)

        c.execute(f"UPDATE auditorias_sesiones SET {','.join(sets)} WHERE id=?", params)
        c.commit()
        return jsonify({'ok': True})
    except ValueError as e:
        return jsonify({'ok': False, 'msg': str(e)}), 400
    finally:
        c.close()


@bp.route('/sesiones/<int:sid>/conteo', methods=['POST'], strict_slashes=False)
def registrar_conteo(sid):
    """Registra el conteo físico de un único ítem en la sesión."""
    c = get_db()
    try:
        _ensure_auditorias_schema(c)
        sesion = c.execute(
            "SELECT estado FROM auditorias_sesiones WHERE id=?", [sid]
        ).fetchone()
        if not sesion:
            return jsonify({'ok': False, 'msg': 'Sesión no encontrada'}), 404
        if sesion['estado'] in ('completada', 'cancelada'):
            return jsonify({'ok': False, 'msg': 'La sesión está cerrada y no admite nuevos conteos'}), 400

        d = request.json or {}
        sku = (d.get('sku') or '').strip()
        if not sku:
            return jsonify({'ok': False, 'msg': 'SKU requerido'}), 400

        try:
            contado = float(d['stock_contado'])
        except (KeyError, ValueError, TypeError):
            return jsonify({'ok': False, 'msg': 'stock_contado numérico requerido'}), 400

        row = c.execute(
            "SELECT id, stock_sistema FROM auditorias_detalle WHERE sesion_id=? AND item_sku=?",
            [sid, sku]
        ).fetchone()
        if not row:
            return jsonify({'ok': False, 'msg': 'Ítem no pertenece a esta sesión'}), 404

        sistema = row['stock_sistema'] or 0
        diferencia = round(contado - sistema, 6)
        pct = round(abs(diferencia / sistema * 100), 2) if sistema != 0 else (0.0 if diferencia == 0 else 100.0)

        c.execute("""
            UPDATE auditorias_detalle
            SET stock_contado=?, diferencia=?, pct_desviacion=?,
                fecha_conteo=datetime('now'),
                contado_por=?, observaciones=?
            WHERE id=?
        """, [contado, diferencia, pct, d.get('contado_por', ''), d.get('observaciones', ''), row['id']])

        # Actualizar contadores en la sesión
        nums = c.execute("""
            SELECT
                COUNT(*) FILTER (WHERE stock_contado IS NOT NULL)      AS contados,
                COUNT(*) FILTER (WHERE diferencia <> 0
                                   AND stock_contado IS NOT NULL)      AS con_dif
            FROM auditorias_detalle WHERE sesion_id=?
        """, [sid]).fetchone()
        c.execute("""
            UPDATE auditorias_sesiones
            SET items_contados=?, items_con_diferencia=?, estado='en_progreso'
            WHERE id=? AND estado != 'completada'
        """, [nums['contados'], nums['con_dif'], sid])

        c.commit()
        return jsonify({'ok': True, 'diferencia': diferencia, 'pct_desviacion': pct})
    except ValueError as e:
        return jsonify({'ok': False, 'msg': str(e)}), 400
    except Exception as e:
        return jsonify({'ok': False, 'msg': str(e)}), 500
    finally:
        c.close()


@bp.route('/sesiones/<int:sid>/conteo-lote', methods=['POST'], strict_slashes=False)
def registrar_conteo_lote(sid):
    """
    Registra múltiples conteos en una sola transacción.
    Body: { "items": [{"sku": "SKU-001", "stock_contado": 10, "contado_por": "Juan"}, ...] }
    """
    c = get_db()
    try:
        _ensure_auditorias_schema(c)
        sesion = c.execute(
            "SELECT estado, total_items FROM auditorias_sesiones WHERE id=?", [sid]
        ).fetchone()
        if not sesion:
            return jsonify({'ok': False, 'msg': 'Sesión no encontrada'}), 404
        if sesion['estado'] in ('completada', 'cancelada'):
            return jsonify({'ok': False, 'msg': 'La sesión está cerrada y no admite carga masiva'}), 400

        d = request.json or {}
        items_in = d.get('items', [])
        if not items_in:
            return jsonify({'ok': False, 'msg': 'Sin ítems'}), 400

        ok_count = 0
        errores = []

        for it in items_in:
            sku = (it.get('sku') or '').strip()
            if not sku:
                continue
            try:
                contado = float(it['stock_contado'])
            except (KeyError, ValueError, TypeError):
                errores.append(f'{sku}: stock_contado inválido')
                continue

            row = c.execute(
                "SELECT id, stock_sistema FROM auditorias_detalle WHERE sesion_id=? AND item_sku=?",
                [sid, sku]
            ).fetchone()
            if not row:
                errores.append(f'{sku}: no pertenece a esta sesión')
                continue

            sistema = row['stock_sistema'] or 0
            diferencia = round(contado - sistema, 6)
            pct = round(abs(diferencia / sistema * 100), 2) if sistema != 0 else (0.0 if diferencia == 0 else 100.0)

            c.execute("""
                UPDATE auditorias_detalle
                SET stock_contado=?, diferencia=?, pct_desviacion=?,
                    fecha_conteo=datetime('now'), contado_por=?, observaciones=?
                WHERE id=?
            """, [contado, diferencia, pct, it.get('contado_por', ''), it.get('observaciones', ''), row['id']])
            ok_count += 1

        if ok_count > 0:
            nums = c.execute("""
                SELECT
                    COUNT(*) FILTER (WHERE stock_contado IS NOT NULL)      AS contados,
                    COUNT(*) FILTER (WHERE diferencia <> 0
                                       AND stock_contado IS NOT NULL)      AS con_dif
                FROM auditorias_detalle WHERE sesion_id=?
            """, [sid]).fetchone()
            c.execute("""
                UPDATE auditorias_sesiones
                SET items_contados=?, items_con_diferencia=?, estado='en_progreso'
                WHERE id=? AND estado != 'completada'
            """, [nums['contados'], nums['con_dif'], sid])
            c.commit()

        resumen = c.execute(
            """SELECT total_items, items_contados, items_con_diferencia, estado
               FROM auditorias_sesiones WHERE id=?""", [sid]
        ).fetchone()
        total_items = resumen['total_items'] or 0
        items_contados = resumen['items_contados'] or 0
        avance_pct = round((items_contados / total_items) * 100, 2) if total_items > 0 else 0.0

        return jsonify({
            'ok': True,
            'procesados': ok_count,
            'errores': errores,
            'analisis': {
                'total_items': total_items,
                'items_contados': items_contados,
                'items_con_diferencia': resumen['items_con_diferencia'] or 0,
                'avance_pct': avance_pct,
                'estado': resumen['estado']
            }
        })
    except Exception as e:
        c.rollback()
        return jsonify({'ok': False, 'msg': str(e)}), 500
    finally:
        c.close()


@bp.route('/sesiones/<int:sid>/aplicar-ajustes', methods=['POST'], strict_slashes=False)
def aplicar_ajustes(sid):
    """
    Aplica los ajustes de stock para los ítems con diferencia en la sesión.
    Parámetros opcionales:
      - skus: lista de SKUs específicos (null = todos)
      - umbral_pct: solo ajustar si pct_desviacion >= N (default 0)
      - aplicado_por: nombre del responsable
    """
    c = get_db()
    try:
        _ensure_auditorias_schema(c)
        d = request.json or {}
        aplicado_por = d.get('aplicado_por', 'auditor')
        solo_skus = d.get('skus') or None
        umbral = float(d.get('umbral_pct', 0))

        c.execute("BEGIN IMMEDIATE")

        # Verificar que la sesión existe y no está cancelada
        sesion = c.execute(
            "SELECT estado FROM auditorias_sesiones WHERE id=?", [sid]
        ).fetchone()
        if not sesion:
            return jsonify({'ok': False, 'msg': 'Sesión no encontrada'}), 404
        if sesion['estado'] == 'cancelada':
            return jsonify({'ok': False, 'msg': 'No se puede ajustar una sesión cancelada'}), 400

        q = """
            SELECT id, item_sku, stock_sistema, stock_contado, diferencia, pct_desviacion
            FROM auditorias_detalle
            WHERE sesion_id=?
              AND stock_contado IS NOT NULL
              AND diferencia <> 0
              AND ajustado = 0
              AND pct_desviacion >= ?
        """
        params = [sid, umbral]
        if solo_skus:
            placeholders = ','.join('?' * len(solo_skus))
            q += f" AND item_sku IN ({placeholders})"
            params += list(solo_skus)

        pendientes = c.execute(q, params).fetchall()
        if not pendientes:
            return jsonify({'ok': True, 'ajustados': 0, 'msg': 'Sin diferencias pendientes para ajustar'})

        ajustados = 0
        for row in pendientes:
            sku = row['item_sku']
            nuevo_stock = row['stock_contado']
            stock_antes = row['stock_sistema']

            mark = c.execute(
                "UPDATE auditorias_detalle SET ajustado=1 WHERE id=? AND ajustado=0",
                [row['id']]
            )
            if (mark.rowcount or 0) == 0:
                continue

            c.execute("UPDATE items SET stock_actual=? WHERE sku=?", [nuevo_stock, sku])
            c.execute("""
                INSERT INTO auditorias_ajustes
                    (sesion_id, detalle_id, item_sku, stock_antes, stock_despues,
                     diferencia, aplicado_por)
                VALUES (?,?,?,?,?,?,?)
            """, [sid, row['id'], sku, stock_antes, nuevo_stock, row['diferencia'], aplicado_por])
            # Actualizar último conteo ABC
            c.execute("""
                UPDATE items_clasificacion_abc
                SET ultimo_conteo  = date('now'),
                    proximo_conteo = date('now', '+' || frecuencia_conteo_dias || ' days')
                WHERE item_sku = ?
            """, [sku])
            ajustados += 1

        c.execute("""
            UPDATE auditorias_sesiones
            SET ajustes_aplicados = ajustes_aplicados + ?,
                estado = 'completada',
                fecha_fin = datetime('now')
            WHERE id=?
        """, [ajustados, sid])
        c.commit()

        return jsonify({'ok': True, 'ajustados': ajustados})
    except ValueError as e:
        c.rollback()
        return jsonify({'ok': False, 'msg': str(e)}), 400
    except Exception as e:
        c.rollback()
        return jsonify({'ok': False, 'msg': str(e)}), 500
    finally:
        c.close()


# ─────────────────────────────────────────────────────────────────────────────
# REPORTE HTML DE AUDITORÍA
# ─────────────────────────────────────────────────────────────────────────────

@bp.route('/sesiones/<int:sid>/reporte-html', methods=['GET'], strict_slashes=False)
def reporte_html(sid):
    """Genera reporte HTML exportable a PDF con detalle completo de la auditoría."""
    from datetime import datetime
    c = get_db()
    try:
        _ensure_auditorias_schema(c)
        
        # Cargar sesión
        sesion = c.execute(
            """SELECT id, tipo, estado, fecha_inicio, fecha_fin, auditado_por,
                      total_items, items_contados, items_con_diferencia, ajustes_aplicados,
                      semana_iso, mes_periodo, ciclo_numero
               FROM auditorias_sesiones WHERE id=?""", [sid]
        ).fetchone()
        if not sesion:
            return '<h1>Sesión no encontrada</h1>', 404

        # Cargar detalle
        detalle = c.execute(
            """SELECT item_sku, item_nombre, clase_abc, stock_sistema, stock_contado, 
                      diferencia, pct_desviacion, ajustado
               FROM auditorias_detalle WHERE sesion_id=? ORDER BY clase_abc, item_sku""",
            [sid]
        ).fetchall()

        # Stats
        stats = c.execute(
            """SELECT COUNT(*) as total, 
                      SUM(CASE WHEN diferencia <> 0 THEN 1 ELSE 0 END) as con_dif,
                      SUM(CASE WHEN ajustado = 1 THEN 1 ELSE 0 END) as ajustados
               FROM auditorias_detalle WHERE sesion_id=?""",
            [sid]
        ).fetchone()

        c.close()
        
        # Generar tabla de detalle
        tabla_html = '<table><thead><tr><th>SKU</th><th>Producto</th><th>Clase</th><th>Sistema</th><th>Contado</th><th>Dif</th><th>%</th><th>Estado</th></tr></thead><tbody>'
        for row in detalle:
            diff = row['diferencia'] or 0
            pct = row['pct_desviacion'] or 0
            stock_contado = row['stock_contado']
            stock_contado_txt = f"{stock_contado:.2f}" if stock_contado is not None else '—'
            dif_color = '#27ae60' if diff > 0 else ('#e74c3c' if diff < 0 else '#999')
            dif_sign = '+' if diff > 0 else ''
            estado = '✓ Ajustado' if row['ajustado'] else ('⚠' if diff != 0 else '✓')
            tabla_html += f'<tr><td>{row["item_sku"]}</td><td>{row["item_nombre"] or "—"}</td><td><b>{row["clase_abc"]}</b></td><td style="text-align:right">{row["stock_sistema"]:.2f}</td><td style="text-align:right">{stock_contado_txt}</td><td style="color:{dif_color};text-align:right"><b>{dif_sign}{diff:.2f}</b></td><td style="text-align:right">{pct:.1f}%</td><td>{estado}</td></tr>'
        tabla_html += '</tbody></table>'

        # Generar HTML completo
        fecha_gen = datetime.now().strftime('%d/%m/%Y %H:%M')
        html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>Auditoría #{sid}</title>
<style>
@page{{ size: A4; margin: 15mm; }}
*{{ margin:0; padding:0; box-sizing:border-box; }}
body{{ font-family: Arial, sans-serif; color: #333; background:#fff; }}
.header{{ border-bottom: 3px solid #0533d1; padding-bottom: 15px; margin-bottom: 20px; }}
.header h1{{ color: #0533d1; font-size: 20px; margin-bottom: 5px; }}
.header p{{ color: #666; font-size: 12px; margin: 2px 0; }}
.stats{{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; margin-bottom: 20px; }}
.stat{{ background: #0533d1; color: white; padding: 12px; border-radius: 4px; text-align: center; }}
.stat .num{{ font-size: 24px; font-weight: bold; }}
.stat .label{{ font-size: 10px; margin-top: 5px; }}
h2{{ font-size: 14px; color: #333; margin: 20px 0 10px 0; border-bottom: 2px solid #ddd; padding-bottom: 8px; }}
table{{ width: 100%; border-collapse: collapse; font-size: 11px; margin-bottom: 20px; }}
th{{ background: #f0f0f0; padding: 8px; text-align: left; font-weight: bold; border-bottom: 2px solid #ddd; }}
td{{ padding: 7px 8px; border-bottom: 1px solid #e0e0e0; }}
tr:hover{{ background: #f9f9f9; }}
.footer{{ margin-top: 30px; padding-top: 15px; border-top: 1px solid #ddd; font-size: 10px; color: #999; text-align: center; }}
button{{ background: #0533d1; color: white; border: none; padding: 8px 16px; border-radius: 4px; cursor: pointer; margin-bottom: 15px; font-size: 12px; }}
button:hover{{ background: #0327a0; }}
@media print{{ button {{ display: none; }} }}
</style>
</head>
<body>
<button onclick="window.print()">🖨️ Imprimir / Guardar PDF</button>

<div class="header">
    <h1>Reporte de Auditoría #{sid}</h1>
    <p><b>Estado:</b> {sesion['estado'].upper()} | <b>Tipo:</b> {sesion['tipo'].upper()} | <b>Auditor:</b> {sesion['auditado_por'] or '—'}</p>
    <p><b>Generado:</b> {fecha_gen} | <b>Período:</b> {sesion['semana_iso'] or sesion['mes_periodo'] or '—'}</p>
</div>

<div class="stats">
    <div class="stat">
        <div class="num">{stats['total'] or 0}</div>
        <div class="label">Items Auditados</div>
    </div>
    <div class="stat" style="background: #27ae60">
        <div class="num">{stats['con_dif'] or 0}</div>
        <div class="label">Con Diferencia</div>
    </div>
    <div class="stat" style="background: #e67e22">
        <div class="num">{stats['ajustados'] or 0}</div>
        <div class="label">Ajustados</div>
    </div>
    <div class="stat" style="background: #e74c3c">
        <div class="num">{sesion['ajustes_aplicados']}</div>
        <div class="label">Total Aplicado</div>
    </div>
</div>

<h2>Detalle de Conteos</h2>
{tabla_html}

<div class="footer">
    <p>North Chrome - Gestión de Bodega v2 • Auditoría #{sid} • {fecha_gen}</p>
    <p>Reporte confidencial - Debe ser preservado según políticas de retención</p>
</div>
</body>
</html>"""
        return html, 200, {'Content-Type': 'text/html; charset=utf-8'}
    except Exception as e:
        c.close()
        return f'<h1>Error al generar reporte</h1><p>{str(e)}</p>', 500
