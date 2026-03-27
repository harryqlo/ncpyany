from flask import Blueprint, jsonify, request
from datetime import datetime
from app.db import get_db, date_to_excel, excel_to_date
from app.search_utils import contains_terms_where
import re
import csv
import os

bp = Blueprint('sellos', __name__, url_prefix='/api/sellos')

MATERIALES_BOCINA = ['FPM', 'H-NBR', 'HPU', 'NBR', 'POM', 'PTFE D46', 'PTFE I', 'PTFE II', 'PTFE REIN', 'PTFE']


def _ensure_column(c, table_name, column_name, column_def):
    cols = {row[1] for row in c.execute(f'PRAGMA table_info({table_name})').fetchall()}
    if column_name not in cols:
        c.execute(f'ALTER TABLE {table_name} ADD COLUMN {column_name} {column_def}')


def _to_float(value):
    if value is None:
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    txt = str(value).strip().replace(',', '.')
    if not txt:
        return 0.0
    try:
        return float(txt)
    except Exception:
        return 0.0


def _ensure_sellos_schema(c):
    c.execute('''
        CREATE TABLE IF NOT EXISTS movimientos_sellos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha_produccion REAL,
            bocina_sku TEXT NOT NULL,
            bocina_descripcion TEXT,
            cantidad_sellos REAL NOT NULL DEFAULT 0,
            largo_sello_mm REAL NOT NULL DEFAULT 0,
            consumo_mm REAL NOT NULL DEFAULT 0,
            stock_bocina_en_mov REAL,
            observaciones TEXT,
            creado_en TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    c.execute('CREATE INDEX IF NOT EXISTS idx_sellos_bocina ON movimientos_sellos(bocina_sku)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_sellos_fecha ON movimientos_sellos(fecha_produccion)')
    _ensure_column(c, 'movimientos_sellos', 'bocina_codigo_interno', 'TEXT')
    _ensure_column(c, 'movimientos_sellos', 'ot_id', 'TEXT')
    c.execute('''
        CREATE TABLE IF NOT EXISTS sellos_codigos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_sku TEXT UNIQUE NOT NULL,
            codigo_bocina TEXT,
            material_sello TEXT,
            largo_referencia_mm REAL,
            nombre_origen TEXT,
            actualizado_en TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    c.execute('CREATE INDEX IF NOT EXISTS idx_sellos_codigos_item ON sellos_codigos(item_sku)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_sellos_codigos_codigo ON sellos_codigos(codigo_bocina)')
    c.execute('''
        CREATE TABLE IF NOT EXISTS sellos_bocinas_stock (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            codigo_interno TEXT UNIQUE NOT NULL,
            sku_proveedor TEXT,
            material_sello TEXT,
            descripcion TEXT,
            medida TEXT,
            largo_nominal_mm REAL NOT NULL DEFAULT 0,
            cantidad_bocinas REAL NOT NULL DEFAULT 0,
            mm_total REAL NOT NULL DEFAULT 0,
            mm_disponible REAL NOT NULL DEFAULT 0,
            origen TEXT,
            actualizado_en TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    c.execute('CREATE INDEX IF NOT EXISTS idx_sellos_stock_codigo ON sellos_bocinas_stock(codigo_interno)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_sellos_stock_sku ON sellos_bocinas_stock(sku_proveedor)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_sellos_stock_mat_med ON sellos_bocinas_stock(material_sello,medida,largo_nominal_mm)')
    c.execute('''
        CREATE TABLE IF NOT EXISTS sellos_ingresos_bocinas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha_ingreso REAL,
            referencia_doc TEXT,
            sku_proveedor TEXT,
            material_sello TEXT,
            medida TEXT,
            largo_nominal_mm REAL,
            cantidad_bocinas INTEGER,
            codigos_generados TEXT,
            observaciones TEXT,
            creado_en TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    c.execute('CREATE INDEX IF NOT EXISTS idx_sellos_ingresos_fecha ON sellos_ingresos_bocinas(fecha_ingreso)')


def _parse_codigo_bocina(sku, nombre):
    texto = f"{sku or ''} {nombre or ''}".upper()
    m = re.search(r'\b(\d{3})\b', texto)
    return m.group(1) if m else ''


def _parse_largo_mm(nombre):
    if not nombre:
        return None
    m = re.search(r'(\d+(?:[\.,]\d+)?)\s*MM\b', str(nombre).upper())
    if not m:
        return None
    return float(m.group(1).replace(',', '.'))


def _parse_material(nombre):
    txt = (nombre or '').upper()
    for mat in MATERIALES_BOCINA:
        if mat in txt:
            return mat
    return ''


def _parse_medida(nombre):
    txt = (nombre or '').upper()
    m = re.search(r'(\d{3})\s*[-/]\s*(\d{3})', txt)
    if not m:
        return ''
    return f"{m.group(1)}-{m.group(2)}"


def _next_internal_code(c):
    rows = c.execute('SELECT codigo_interno FROM sellos_bocinas_stock WHERE codigo_interno LIKE "NCB-%"').fetchall()
    mx = 0
    for row in rows:
        val = (row[0] or '').strip().upper()
        m = re.match(r'NCB-(\d+)$', val)
        if m:
            mx = max(mx, int(m.group(1)))
    return f"NCB-{mx + 1:03d}"


def _build_unified_key(sku_proveedor, material, medida, largo_mm):
    return f"{(sku_proveedor or '').strip().upper()}|{(material or '').strip().upper()}|{(medida or '').strip().upper()}|{round(_to_float(largo_mm), 3)}"


def _rebuild_unitary_stock(c, grouped_rows):
    c.execute('DELETE FROM sellos_bocinas_stock')
    try:
        c.execute("DELETE FROM sqlite_sequence WHERE name='sellos_bocinas_stock'")
    except Exception:
        pass

    next_num = 1
    created = 0

    def _sort_key(item):
        return (
            (item.get('material_sello') or ''),
            (item.get('medida') or ''),
            (item.get('sku_proveedor') or ''),
            _to_float(item.get('largo_nominal_mm'))
        )

    for item in sorted(grouped_rows, key=_sort_key):
        sku_proveedor = (item.get('sku_proveedor') or '').strip()
        material = (item.get('material_sello') or '').strip().upper()
        descripcion = (item.get('descripcion') or '').strip()
        medida = (item.get('medida') or '').strip()
        largo_nominal_mm = max(0.0, _to_float(item.get('largo_nominal_mm')))
        unidades = int(max(0, round(_to_float(item.get('cantidad_bocinas')))))
        origen = (item.get('origen') or '').strip()

        if unidades <= 0:
            continue

        for _ in range(unidades):
            codigo_interno = f"NCB-{next_num:03d}"
            next_num += 1
            c.execute(
                '''INSERT INTO sellos_bocinas_stock
                   (codigo_interno,sku_proveedor,material_sello,descripcion,medida,largo_nominal_mm,cantidad_bocinas,mm_total,mm_disponible,origen,actualizado_en)
                   VALUES (?,?,?,?,?,?,?,?,?,?,CURRENT_TIMESTAMP)''',
                [codigo_interno, sku_proveedor, material, descripcion, medida, largo_nominal_mm, 1, largo_nominal_mm, largo_nominal_mm, origen]
            )
            created += 1

    return created


def _is_candidate_bocina(row):
    sku = (row[0] or '').upper()
    nombre = (row[1] or '').upper()
    categoria = (row[2] or '').upper()
    txt = f"{sku} {nombre} {categoria}"
    return (
        'BOCINA' in txt
        or 'MM' in txt
        or any(mat in txt for mat in MATERIALES_BOCINA)
    )


def _build_display_descripcion(material, medida, largo_mm):
    mat = (material or '').strip().upper() or 'BOCINA'
    med = (medida or '').strip() or '---'
    return f'{mat} {med} x {round(_to_float(largo_mm), 2)}MM'


def _parse_packing_description(desc):
    txt = (desc or '').strip().upper()
    if not txt:
        return '', '', 0.0

    m = re.search(r'([A-Z\- ]+)\s*(\d{1,4})\s*[Xx]\s*(\d{1,4})\s*[Xx]\s*(\d{1,4}(?:[\.,]\d+)?)\s*MM', txt)
    if m:
        material = (m.group(1) or '').strip()
        mi = m.group(2).zfill(3)
        me = m.group(3).zfill(3)
        largo = _to_float(m.group(4))
        return material, f'{mi}-{me}', largo

    material = _parse_material(txt)
    medida = _parse_medida(txt)
    largo = _parse_largo_mm(txt) or 0.0
    return material, medida, largo


def _create_bocina_units(c, *, fecha_excel, referencia_doc, material, medida, largo_nominal_mm, cantidad_bocinas, sku_proveedor='', observaciones=''):
    descripcion = _build_display_descripcion(material, medida, largo_nominal_mm)
    codigos = []
    for _ in range(cantidad_bocinas):
        codigo_interno = _next_internal_code(c)
        c.execute(
            '''INSERT INTO sellos_bocinas_stock
               (codigo_interno,sku_proveedor,material_sello,descripcion,medida,largo_nominal_mm,cantidad_bocinas,mm_total,mm_disponible,origen,actualizado_en)
               VALUES (?,?,?,?,?,?,?,?,?,?,CURRENT_TIMESTAMP)''',
            [codigo_interno, sku_proveedor, material, descripcion, medida, largo_nominal_mm, 1, largo_nominal_mm, largo_nominal_mm, 'manual']
        )
        codigos.append(codigo_interno)

    c.execute(
        '''INSERT INTO sellos_ingresos_bocinas
           (fecha_ingreso,referencia_doc,sku_proveedor,material_sello,medida,largo_nominal_mm,cantidad_bocinas,codigos_generados,observaciones)
           VALUES (?,?,?,?,?,?,?,?,?)''',
        [
            fecha_excel,
            referencia_doc,
            sku_proveedor,
            material,
            medida,
            largo_nominal_mm,
            cantidad_bocinas,
            ','.join(codigos),
            observaciones
        ]
    )

    return codigos


def _upsert_codigo(c, item_sku, codigo_bocina, material_sello, largo_mm, nombre_origen):
    c.execute(
        '''INSERT INTO sellos_codigos
           (item_sku,codigo_bocina,material_sello,largo_referencia_mm,nombre_origen,actualizado_en)
           VALUES (?,?,?,?,?,CURRENT_TIMESTAMP)
           ON CONFLICT(item_sku) DO UPDATE SET
             codigo_bocina=excluded.codigo_bocina,
             material_sello=excluded.material_sello,
             largo_referencia_mm=excluded.largo_referencia_mm,
             nombre_origen=excluded.nombre_origen,
             actualizado_en=CURRENT_TIMESTAMP''',
        [item_sku, codigo_bocina, material_sello, largo_mm, nombre_origen]
    )


@bp.route('/migrar-codigos', methods=['POST'], strict_slashes=False)
def api_sellos_migrar_codigos():
    """
    Migra códigos de bocina desde el inventario general (`items`) hacia el catálogo de Sellos.
    """
    c = get_db()
    try:
        _ensure_sellos_schema(c)
        body = request.json or {}
        force_all = bool(body.get('force_all', False))

        rows = c.execute(
            '''SELECT sku,nombre,categoria_nombre,COALESCE(stock_actual,0)
               FROM items
               WHERE sku IS NOT NULL AND TRIM(sku)<>''
               ORDER BY sku'''
        ).fetchall()

        migrados = 0
        omitidos = 0
        grouped = {}
        for row in rows:
            sku = (row[0] or '').strip()
            nombre = row[1] or ''
            if not sku:
                omitidos += 1
                continue

            if not force_all and not _is_candidate_bocina(row):
                omitidos += 1
                continue

            codigo = _parse_codigo_bocina(sku, nombre)
            material = _parse_material(nombre)
            largo_mm = _parse_largo_mm(nombre)
            medida = _parse_medida(nombre)
            cantidad_bocinas = max(0.0, _to_float(row[3]))

            _upsert_codigo(c, sku, codigo, material, largo_mm, nombre)
            key = _build_unified_key(sku, material, medida, largo_mm or 0)
            current = grouped.get(key)
            if not current:
                grouped[key] = {
                    'sku_proveedor': sku,
                    'material_sello': material,
                    'descripcion': nombre,
                    'medida': medida,
                    'largo_nominal_mm': largo_mm or 0,
                    'cantidad_bocinas': cantidad_bocinas,
                    'origen': 'items'
                }
            else:
                current['cantidad_bocinas'] = max(current['cantidad_bocinas'], cantidad_bocinas)
                if len(nombre) > len(current.get('descripcion') or ''):
                    current['descripcion'] = nombre
            migrados += 1

        bocinas_creadas = _rebuild_unitary_stock(c, list(grouped.values()))

        c.commit()
        total_catalogo = c.execute('SELECT COUNT(*) FROM sellos_codigos').fetchone()[0]
        total_unificados = c.execute('SELECT COUNT(*) FROM sellos_bocinas_stock').fetchone()[0]
        return jsonify({
            'ok': True,
            'msg': f'Migración completada: {migrados} código(s) traspasado(s) y {bocinas_creadas} bocina(s) interna(s) generada(s)',
            'migrados': migrados,
            'omitidos': omitidos,
            'total_catalogo': total_catalogo,
            'unificados': len(grouped),
            'bocinas_creadas': bocinas_creadas,
            'total_unificados': total_unificados
        })
    except Exception as e:
        c.rollback()
        return jsonify({'ok': False, 'msg': str(e)}), 400
    finally:
        c.close()


@bp.route('/ingresos', strict_slashes=False)
def api_sellos_ingresos_list():
    """
    Lista ingresos manuales de bocinas del sistema Sellos (independiente).
    """
    c = get_db()
    try:
        _ensure_sellos_schema(c)
        rows = c.execute(
            '''SELECT id,fecha_ingreso,referencia_doc,sku_proveedor,material_sello,medida,
                      largo_nominal_mm,cantidad_bocinas,codigos_generados,observaciones
               FROM sellos_ingresos_bocinas
               ORDER BY id DESC
               LIMIT 100'''
        ).fetchall()

        items = [{
            'id': r[0],
            'fecha': excel_to_date(r[1]),
            'referencia_doc': r[2] or '',
            'sku_proveedor': r[3] or '',
            'material_sello': r[4] or '',
            'medida': r[5] or '',
            'largo_nominal_mm': float(r[6] or 0),
            'cantidad_bocinas': int(r[7] or 0),
            'codigos_generados': (r[8] or '').split(',') if (r[8] or '').strip() else [],
            'observaciones': r[9] or ''
        } for r in rows]
        return jsonify({'items': items, 'total': len(items)})
    finally:
        c.close()


@bp.route('/ingresos', methods=['POST'], strict_slashes=False)
def api_sellos_ingresos_create():
    """
    Registra llegada de nuevas bocinas de forma independiente al inventario general.
    Genera códigos internos NCB únicos por cada unidad física.
    """
    c = get_db()
    try:
        _ensure_sellos_schema(c)
        d = request.json or {}

        fecha = d.get('fecha') or datetime.now().strftime('%Y-%m-%d')
        fecha_excel = date_to_excel(fecha)

        material = (d.get('material_sello') or '').strip().upper()
        medida = (d.get('medida') or '').strip()
        if not medida:
            mi = (d.get('medida_interna') or '').strip()
            me = (d.get('medida_externa') or '').strip()
            if mi and me:
                medida = f'{mi.zfill(3)}-{me.zfill(3)}'

        largo_nominal_mm = _to_float(d.get('largo_nominal_mm'))
        cantidad_bocinas = int(max(0, round(_to_float(d.get('cantidad_bocinas')))))
        sku_proveedor = (d.get('sku_proveedor') or '').strip()
        referencia_doc = (d.get('referencia_doc') or '').strip()
        observaciones = (d.get('observaciones') or '').strip()

        if not material:
            return jsonify({'ok': False, 'msg': 'Material requerido'}), 400
        if not medida:
            return jsonify({'ok': False, 'msg': 'Medida requerida (interna-externa)'}), 400
        if largo_nominal_mm <= 0:
            return jsonify({'ok': False, 'msg': 'Largo nominal debe ser mayor a 0'}), 400
        if cantidad_bocinas <= 0:
            return jsonify({'ok': False, 'msg': 'Cantidad de bocinas debe ser mayor a 0'}), 400

        codigos = _create_bocina_units(
            c,
            fecha_excel=fecha_excel,
            referencia_doc=referencia_doc,
            material=material,
            medida=medida,
            largo_nominal_mm=largo_nominal_mm,
            cantidad_bocinas=cantidad_bocinas,
            sku_proveedor=sku_proveedor,
            observaciones=observaciones
        )

        c.commit()
        return jsonify({
            'ok': True,
            'msg': f'Ingreso registrado: {cantidad_bocinas} bocina(s) creada(s)',
            'cantidad_bocinas': cantidad_bocinas,
            'codigos_generados': codigos
        })
    except Exception as e:
        c.rollback()
        return jsonify({'ok': False, 'msg': str(e)}), 400
    finally:
        c.close()


@bp.route('/ingresos/packing-list', methods=['POST'], strict_slashes=False)
def api_sellos_ingresos_packing_list():
    """
    Carga masiva desde packing list en texto.
    Formato por línea sugerido: SKU;DESCRIPCION;CANTIDAD
    También soporta líneas tipo: SKU DESCRIPCION CANTIDAD
    """
    c = get_db()
    try:
        _ensure_sellos_schema(c)
        d = request.json or {}
        fecha = d.get('fecha') or datetime.now().strftime('%Y-%m-%d')
        fecha_excel = date_to_excel(fecha)
        referencia_doc = (d.get('referencia_doc') or '').strip()
        texto = (d.get('texto') or '').strip()
        observaciones = (d.get('observaciones') or '').strip()

        if not texto:
            return jsonify({'ok': False, 'msg': 'Texto de packing list requerido'}), 400

        created_codes = []
        procesadas = 0
        omitidas = 0

        for raw_line in texto.splitlines():
            line = raw_line.strip()
            if not line:
                continue

            sku = ''
            descripcion = ''
            cantidad_txt = ''

            parts = [p.strip() for p in line.split(';') if p is not None]
            if len(parts) >= 3:
                sku, descripcion, cantidad_txt = parts[0], parts[1], parts[2]
            else:
                m = re.match(r'^(\S+)\s+(.+?)\s+(\d+(?:[\.,]\d+)?)$', line)
                if not m:
                    omitidas += 1
                    continue
                sku, descripcion, cantidad_txt = m.group(1), m.group(2), m.group(3)

            cantidad = int(max(0, round(_to_float(cantidad_txt))))
            if cantidad <= 0:
                omitidas += 1
                continue

            material, medida, largo_mm = _parse_packing_description(descripcion)
            if not material or not medida or largo_mm <= 0:
                omitidas += 1
                continue

            codes = _create_bocina_units(
                c,
                fecha_excel=fecha_excel,
                referencia_doc=referencia_doc,
                material=material,
                medida=medida,
                largo_nominal_mm=largo_mm,
                cantidad_bocinas=cantidad,
                sku_proveedor=sku,
                observaciones=observaciones or 'Ingreso packing list'
            )
            created_codes.extend(codes)
            procesadas += 1

        c.commit()
        return jsonify({
            'ok': True,
            'msg': f'Packing list procesado: {procesadas} línea(s) cargada(s)',
            'lineas_cargadas': procesadas,
            'lineas_omitidas': omitidas,
            'bocinas_creadas': len(created_codes),
            'codigos_generados': created_codes[:20]
        })
    except Exception as e:
        c.rollback()
        return jsonify({'ok': False, 'msg': str(e)}), 400
    finally:
        c.close()


@bp.route('/importar-csv', methods=['POST'], strict_slashes=False)
def api_sellos_importar_csv():
    """
    Importa listado completo de bocinas desde CSV y unifica a códigos internos NCB.
    """
    c = get_db()
    try:
        _ensure_sellos_schema(c)
        body = request.json or {}
        csv_path = (body.get('csv_path') or '').strip()
        if not csv_path:
            return jsonify({'ok': False, 'msg': 'Ruta CSV requerida'}), 400

        if not os.path.exists(csv_path):
            return jsonify({'ok': False, 'msg': f'Archivo no existe: {csv_path}'}), 404

        agrupado = {}
        procesadas = 0
        omitidas = 0

        with open(csv_path, 'r', encoding='utf-8-sig', newline='') as fh:
            reader = csv.DictReader(fh, delimiter=';')
            for raw in reader:
                sku = (raw.get('SKU') or '').strip()
                material = (raw.get('BOCINA') or '').strip().upper()
                descripcion = (raw.get('Descripcion') or '').strip()
                inventario = _to_float(raw.get('Inventario'))

                if not sku and not descripcion:
                    omitidas += 1
                    continue
                if not sku:
                    omitidas += 1
                    continue

                if not material:
                    material = _parse_material(descripcion)

                medida = _parse_medida(descripcion)
                largo_mm = _parse_largo_mm(descripcion) or 0

                key = _build_unified_key(sku, material, medida, largo_mm)
                prev = agrupado.get(key)
                if not prev:
                    agrupado[key] = {
                        'sku_proveedor': sku,
                        'material_sello': material,
                        'descripcion': descripcion,
                        'medida': medida,
                        'largo_nominal_mm': largo_mm,
                        'cantidad_bocinas': max(0.0, inventario),
                        'origen': 'csv'
                    }
                else:
                    prev['cantidad_bocinas'] = max(prev['cantidad_bocinas'], max(0.0, inventario))
                    if len(descripcion) > len(prev.get('descripcion') or ''):
                        prev['descripcion'] = descripcion
                procesadas += 1

        grouped_values = list(agrupado.values())
        bocinas_creadas = _rebuild_unitary_stock(c, grouped_values)

        for item in grouped_values:
            sku = item['sku_proveedor']
            _upsert_codigo(
                c,
                sku,
                _parse_codigo_bocina(sku, item['descripcion']),
                item['material_sello'],
                item['largo_nominal_mm'],
                item['descripcion']
            )

        c.commit()
        total_unificados = c.execute('SELECT COUNT(*) FROM sellos_bocinas_stock').fetchone()[0]
        return jsonify({
            'ok': True,
            'msg': f'CSV importado: {bocinas_creadas} bocina(s) interna(s) creada(s)',
            'filas_procesadas': procesadas,
            'filas_omitidas': omitidas,
            'unificadas': len(agrupado),
            'bocinas_creadas': bocinas_creadas,
            'total_unificados': total_unificados
        })
    except Exception as e:
        c.rollback()
        return jsonify({'ok': False, 'msg': str(e)}), 400
    finally:
        c.close()


@bp.route('/codigos', strict_slashes=False)
def api_sellos_codigos_list():
    """
    Lista catálogo de códigos migrados para Sellos.
    """
    c = get_db()
    try:
        _ensure_sellos_schema(c)
        q = (request.args.get('q') or '').strip()
        w, p = [], []
        if q:
            search_where, search_params = contains_terms_where(q, ['item_sku', 'codigo_bocina', 'material_sello', 'nombre_origen'])
            if search_where:
                w.append(search_where)
                p += search_params
        ws = (' WHERE ' + ' AND '.join(w)) if w else ''

        rows = c.execute(
            f'''SELECT sc.item_sku,sc.codigo_bocina,sc.material_sello,sc.largo_referencia_mm,
                       sc.nombre_origen,COALESCE(i.stock_actual,0)
                FROM sellos_codigos sc
                LEFT JOIN items i ON i.sku=sc.item_sku
                {ws}
                ORDER BY sc.item_sku
                LIMIT 200''',
            p
        ).fetchall()

        items = [{
            'item_sku': r[0],
            'codigo_bocina': r[1] or '',
            'material_sello': r[2] or '',
            'largo_referencia_mm': float(r[3] or 0),
            'nombre_origen': r[4] or '',
            'stock_actual': float(r[5] or 0)
        } for r in rows]
        return jsonify({'items': items, 'total': len(items)})
    finally:
        c.close()


@bp.route('/bocinas', strict_slashes=False)
def api_sellos_bocinas():
    """
    Busca bocinas disponibles en inventario.
    Prioriza items que contienen "bocina" en SKU/nombre/categoría.
    """
    c = get_db()
    try:
        _ensure_sellos_schema(c)
        q = (request.args.get('q') or '').strip()

        stock_count = c.execute('SELECT COUNT(*) FROM sellos_bocinas_stock').fetchone()[0]
        if stock_count > 0:
            where = ''
            params = []
            if q:
                search_where, search_params = contains_terms_where(q, ['sbs.codigo_interno', 'sbs.sku_proveedor', 'sbs.descripcion', 'sbs.material_sello', 'sbs.medida'])
                if search_where:
                    where = f'WHERE {search_where}'
                    params = search_params

            rows = c.execute(
                f'''SELECT sbs.codigo_interno,sbs.sku_proveedor,sbs.descripcion,sbs.material_sello,sbs.medida,
                           sbs.largo_nominal_mm,sbs.cantidad_bocinas,sbs.mm_total,sbs.mm_disponible
                    FROM sellos_bocinas_stock sbs
                    {where}
                    ORDER BY sbs.codigo_interno
                    LIMIT 200''',
                params
            ).fetchall()

            items = [{
                'codigo_interno': r[0],
                'sku': r[1] or '',
                'nombre': r[2] or '',
                'material_sello': r[3] or '',
                'medida': r[4] or '',
                'largo_referencia_mm': float(r[5] or 0),
                'cantidad_bocinas': float(r[6] or 0),
                'mm_total': float(r[7] or 0),
                'stock': float(r[8] or 0),
                'unidad': 'mm',
                'categoria': 'Sellos-Unificado'
            } for r in rows]
            return jsonify(items)

        if q:
            search_where, search_params = contains_terms_where(q, ['sku', 'nombre', 'categoria_nombre'])
            where_sql = f'AND ({search_where})' if search_where else ''
            rows = c.execute(
                f'''SELECT sku,nombre,stock_actual,unidad_medida_nombre,categoria_nombre
                   FROM items
                   WHERE sku IS NOT NULL AND sku<>''
                     {where_sql}
                   ORDER BY
                     CASE WHEN LOWER(COALESCE(categoria_nombre,'')) LIKE '%bocina%' THEN 0 ELSE 1 END,
                     CASE WHEN LOWER(COALESCE(nombre,'')) LIKE '%bocina%' THEN 0 ELSE 1 END,
                     nombre
                   LIMIT 30''',
                search_params
            ).fetchall()
        else:
            rows = c.execute(
                '''SELECT sku,nombre,stock_actual,unidad_medida_nombre,categoria_nombre
                   FROM items
                   WHERE sku IS NOT NULL AND sku<>''
                     AND (
                       LOWER(COALESCE(categoria_nombre,'')) LIKE '%bocina%'
                       OR LOWER(COALESCE(nombre,'')) LIKE '%bocina%'
                       OR LOWER(COALESCE(sku,'')) LIKE '%bocina%'
                     )
                   ORDER BY nombre
                   LIMIT 30'''
            ).fetchall()

        items = [{
            'sku': r[0],
            'nombre': r[1] or '',
            'stock': float(r[2] or 0),
            'unidad': r[3] or '',
            'categoria': r[4] or ''
        } for r in rows]

        return jsonify(items)
    finally:
        c.close()


@bp.route('', strict_slashes=False)
def api_sellos_list():
    """
    Historial de producción de sellos con paginación.
    """
    c = get_db()
    try:
        _ensure_sellos_schema(c)
        pg = int(request.args.get('page', 1))
        pp2 = int(request.args.get('per_page', 50))
        se = (request.args.get('search') or '').strip()

        w, p = [], []
        if se:
            search_where, search_params = contains_terms_where(se, ['ms.bocina_sku', 'ms.bocina_descripcion', 'ms.observaciones', 'ms.bocina_codigo_interno', 'ms.ot_id'])
            if search_where:
                w.append(search_where)
                p += search_params
        ws = (' WHERE ' + ' AND '.join(w)) if w else ''

        t = c.execute(f'SELECT COUNT(*) FROM movimientos_sellos ms{ws}', p).fetchone()[0]
        o = (pg - 1) * pp2

        rows = c.execute(
            f'''SELECT ms.id,ms.fecha_produccion,ms.bocina_codigo_interno,ms.bocina_sku,ms.bocina_descripcion,
                       ms.cantidad_sellos,ms.largo_sello_mm,ms.consumo_mm,ms.stock_bocina_en_mov,
                       ms.ot_id,ms.observaciones,COALESCE(sbs.mm_disponible,ms.stock_bocina_en_mov,0)
                FROM movimientos_sellos ms
                LEFT JOIN sellos_bocinas_stock sbs ON sbs.codigo_interno=ms.bocina_codigo_interno
                {ws}
                ORDER BY ms.id DESC
                LIMIT ? OFFSET ?''',
            p + [pp2, o]
        ).fetchall()

        items = [{
            'id': r[0],
            'fecha': excel_to_date(r[1]),
            'bocina_codigo_interno': r[2] or '',
            'bocina_sku': r[3],
            'bocina_descripcion': r[4] or '',
            'cantidad_sellos': float(r[5] or 0),
            'largo_sello_mm': float(r[6] or 0),
            'consumo_mm': float(r[7] or 0),
            'stock_bocina_en_mov': float(r[8] or 0),
            'ot_id': r[9] or '',
            'observaciones': r[10] or '',
            'stock_actual_bocina': float(r[11] or 0)
        } for r in rows]

        resumen = c.execute(
            f'''SELECT
                    COALESCE(SUM(cantidad_sellos),0),
                    COALESCE(SUM(consumo_mm),0)
                FROM movimientos_sellos ms{ws}''',
            p
        ).fetchone()

        total_sellos = float(resumen[0] or 0)
        total_mm = float(resumen[1] or 0)

        return jsonify({
            'items': items,
            'total': t,
            'page': pg,
            'per_page': pp2,
            'total_pages': max(1, -(-t // pp2)),
            'resumen': {
                'total_sellos': total_sellos,
                'total_mm_consumidos': total_mm,
                'sellos_por_1000mm': round((total_sellos / total_mm) * 1000, 2) if total_mm > 0 else 0
            }
        })
    finally:
        c.close()


@bp.route('', methods=['POST'], strict_slashes=False)
def api_sellos_create():
    """
    Registra producción de sellos y descuenta mm de bocina unificada (NCB).
    """
    c = get_db()
    try:
        _ensure_sellos_schema(c)
        d = request.json or {}

        codigo_interno = (d.get('bocina_codigo_interno') or '').strip().upper()
        sku = (d.get('bocina_sku') or '').strip()
        if not codigo_interno and not sku:
            return jsonify({'ok': False, 'msg': 'Bocina requerida'}), 400

        fecha = d.get('fecha') or datetime.now().strftime('%Y-%m-%d')
        fecha_excel = date_to_excel(fecha)
        ot_id = (d.get('ot_id') or '').strip()

        cantidad_sellos = float(d.get('cantidad_sellos') or 0)
        largo_sello_mm = float(d.get('largo_sello_mm') or 0)
        consumo_mm = float(d.get('consumo_mm') or 0)

        if not ot_id:
            return jsonify({'ok': False, 'msg': 'OT requerida'}), 400

        if cantidad_sellos <= 0:
            return jsonify({'ok': False, 'msg': 'Cantidad de sellos debe ser mayor a 0'}), 400
        if largo_sello_mm <= 0:
            return jsonify({'ok': False, 'msg': 'Largo por sello (mm) debe ser mayor a 0'}), 400

        if consumo_mm <= 0:
            consumo_mm = cantidad_sellos * largo_sello_mm

        bocina = None
        if codigo_interno:
            bocina = c.execute(
                '''SELECT codigo_interno,sku_proveedor,descripcion,mm_disponible
                   FROM sellos_bocinas_stock
                   WHERE codigo_interno=?''',
                [codigo_interno]
            ).fetchone()
        elif sku:
            bocina = c.execute(
                '''SELECT codigo_interno,sku_proveedor,descripcion,mm_disponible
                   FROM sellos_bocinas_stock
                   WHERE sku_proveedor=?
                   ORDER BY mm_disponible DESC
                   LIMIT 1''',
                [sku]
            ).fetchone()

        if bocina:
            codigo_interno = bocina[0]
            sku = bocina[1]
            descripcion = bocina[2] or ''
            stock_actual_mm = float(bocina[3] or 0)

            if consumo_mm > stock_actual_mm:
                return jsonify({'ok': False, 'msg': f'Stock insuficiente de bocina ({round(stock_actual_mm,2)} mm)'}), 400

            nuevo_stock_mm = stock_actual_mm - consumo_mm
            c.execute('UPDATE sellos_bocinas_stock SET mm_disponible=?, actualizado_en=CURRENT_TIMESTAMP WHERE codigo_interno=?', [nuevo_stock_mm, codigo_interno])
            c.execute(
                '''INSERT INTO movimientos_sellos
                   (fecha_produccion,bocina_codigo_interno,bocina_sku,bocina_descripcion,cantidad_sellos,largo_sello_mm,consumo_mm,stock_bocina_en_mov,ot_id,observaciones)
                   VALUES (?,?,?,?,?,?,?,?,?,?)''',
                [
                    fecha_excel,
                    codigo_interno,
                    sku,
                    descripcion,
                    cantidad_sellos,
                    largo_sello_mm,
                    consumo_mm,
                    nuevo_stock_mm,
                    ot_id,
                    (d.get('observaciones') or '').strip()
                ]
            )
            c.commit()
            return jsonify({
                'ok': True,
                'msg': f'Producción registrada. Disponible {codigo_interno}: {round(nuevo_stock_mm, 2)} mm',
                'consumo_mm': round(consumo_mm, 2),
                'stock_bocina': round(nuevo_stock_mm, 2),
                'bocina_codigo_interno': codigo_interno
            })

        item = c.execute('SELECT nombre,stock_actual FROM items WHERE sku=?', [sku]).fetchone()
        if not item:
            return jsonify({'ok': False, 'msg': 'Bocina no encontrada en stock unificado ni inventario'}), 404

        stock_actual = float(item[1] or 0)
        if consumo_mm > stock_actual:
            return jsonify({'ok': False, 'msg': f'Stock insuficiente de bocina ({stock_actual})'}), 400

        nuevo_stock = stock_actual - consumo_mm
        c.execute(
            '''INSERT INTO movimientos_sellos
               (fecha_produccion,bocina_sku,bocina_descripcion,cantidad_sellos,largo_sello_mm,consumo_mm,stock_bocina_en_mov,ot_id,observaciones)
               VALUES (?,?,?,?,?,?,?,?,?)''',
            [fecha_excel, sku, item[0] or '', cantidad_sellos, largo_sello_mm, consumo_mm, nuevo_stock, ot_id, (d.get('observaciones') or '').strip()]
        )
        c.execute('UPDATE items SET stock_actual=? WHERE sku=?', [nuevo_stock, sku])
        c.commit()

        return jsonify({
            'ok': True,
            'msg': f'Producción registrada. Stock bocina: {round(nuevo_stock, 2)}',
            'consumo_mm': round(consumo_mm, 2),
            'stock_bocina': round(nuevo_stock, 2)
        })
    except Exception as e:
        c.rollback()
        return jsonify({'ok': False, 'msg': str(e)}), 400
    finally:
        c.close()


@bp.route('/<int:mov_id>', methods=['DELETE'], strict_slashes=False)
def api_sellos_delete(mov_id):
    """
    Elimina un registro de sellos y restaura el stock de la bocina.
    """
    c = get_db()
    try:
        _ensure_sellos_schema(c)
        row = c.execute(
            'SELECT bocina_codigo_interno,bocina_sku,consumo_mm FROM movimientos_sellos WHERE id=?',
            [mov_id]
        ).fetchone()
        if not row:
            return jsonify({'ok': False, 'msg': 'Registro no encontrado'}), 404

        codigo_interno = (row[0] or '').strip().upper()
        sku = row[1]
        consumo_mm = float(row[2] or 0)

        restored = False
        if codigo_interno:
            bocina = c.execute('SELECT mm_disponible FROM sellos_bocinas_stock WHERE codigo_interno=?', [codigo_interno]).fetchone()
            if bocina:
                actual = float(bocina[0] or 0)
                c.execute('UPDATE sellos_bocinas_stock SET mm_disponible=?, actualizado_en=CURRENT_TIMESTAMP WHERE codigo_interno=?', [actual + consumo_mm, codigo_interno])
                restored = True

        if not restored and sku:
            item = c.execute('SELECT stock_actual FROM items WHERE sku=?', [sku]).fetchone()
            if item:
                stock_actual = float(item[0] or 0)
                c.execute('UPDATE items SET stock_actual=? WHERE sku=?', [stock_actual + consumo_mm, sku])

        c.execute('DELETE FROM movimientos_sellos WHERE id=?', [mov_id])
        c.commit()
        return jsonify({'ok': True, 'msg': 'Registro eliminado y stock restaurado'})
    except Exception as e:
        c.rollback()
        return jsonify({'ok': False, 'msg': str(e)}), 400
    finally:
        c.close()
