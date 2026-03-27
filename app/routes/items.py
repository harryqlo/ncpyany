
from flask import Blueprint, jsonify, request, g
from app.db import get_db, parse_price, excel_to_date
from app.search_utils import contains_terms_where
import re

bp = Blueprint('items', __name__, url_prefix='/api/items')


def _can_override_stock_update():
    user = getattr(g, 'current_user', None) or {}
    permissions = set(user.get('permissions') or [])
    return '*' in permissions or 'auditorias.manage' in permissions


def _get_accumulated_consumo(c, sku):
    cols = {row[1] for row in c.execute('PRAGMA table_info(items)').fetchall()}
    has_historical_ot = 'consumo_historico_ot' in cols
    if has_historical_ot:
        row = c.execute(
            'SELECT sku,nombre,consumos_totales_historicos,stock_actual,precio_unitario_promedio,COALESCE(consumo_historico_ot,\'\') FROM items WHERE sku=?',
            [sku]
        ).fetchone()
    else:
        row = c.execute(
            'SELECT sku,nombre,consumos_totales_historicos,stock_actual,precio_unitario_promedio,\'\' FROM items WHERE sku=?',
            [sku]
        ).fetchone()
    if not row:
        return None

    cantidad = row[2] or 0
    if cantidad <= 0:
        return None

    precio = parse_price(row[4])
    return {
        'sku': row[0],
        'descripcion': row[1],
        'cantidad': cantidad,
        'stock_post': row[3],
        'precio': precio,
        'total': round(cantidad * precio, 2),
        'ot': row[5] or ''
    }

def suggest_sku(prefix):
    """
    Sugiere el siguiente SKU disponible para un prefijo dado.
    
    Args:
        prefix: Prefijo del SKU (ej. 'NCI')
        
    Returns:
        str: SKU sugerido (ej. 'NCI-001')
    """
    c = get_db()
    try:
        pref = (prefix or '').strip().upper()
        if not pref:
            pref = 'NCI'

        rows = c.execute(
            'SELECT sku FROM items WHERE sku LIKE ? COLLATE NOCASE',
            [f"{pref}-%"]
        ).fetchall()

        used_numbers = set()
        used_skus = set()
        pattern = re.compile(rf'^{re.escape(pref)}-(\d+)$', re.IGNORECASE)

        for row in rows:
            sku = (row[0] or '').strip().upper()
            if not sku:
                continue
            used_skus.add(sku)
            match = pattern.match(sku)
            if match:
                try:
                    used_numbers.add(int(match.group(1)))
                except ValueError:
                    continue

        if not used_numbers:
            return f"{pref}-001"

        next_num = max(used_numbers) + 1
        attempts = 0
        while attempts < 100000:
            candidate = f"{pref}-{next_num:03d}"
            if candidate not in used_skus:
                return candidate
            next_num += 1
            attempts += 1

        # Fallback extremo: buscar el primer hueco
        probe = 1
        while probe < 100000:
            if probe not in used_numbers:
                return f"{pref}-{probe:03d}"
            probe += 1

        raise RuntimeError('No fue posible sugerir un SKU disponible')
    finally:
        c.close()

@bp.route('/suggest-sku', strict_slashes=False)
def api_suggest_sku():
    """
    Sugiere un SKU basado en un prefijo
    """
    prefix = request.args.get('prefix', '').strip().upper()
    if not prefix:
        return jsonify({'ok': False, 'msg': 'Prefijo requerido'}), 400
    
    try:
        suggested = suggest_sku(prefix)
        resp = jsonify({'ok': True, 'sku': suggested})
        resp.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        resp.headers['Pragma'] = 'no-cache'
        resp.headers['Expires'] = '0'
        return resp
    except Exception as e:
        return jsonify({'ok': False, 'msg': str(e)}), 500

@bp.route('', strict_slashes=False)
def api_items():
    """
    Obtiene listado de productos con filtros y paginación
    """
    c = get_db()
    try:
        pg=int(request.args.get('page',1)); pp2=int(request.args.get('per_page',50))
        se=request.args.get('search','').strip(); ca=request.args.get('categoria','').strip()
        es=request.args.get('estado','').strip(); sb=request.args.get('sort','nombre'); sd=request.args.get('dir','asc')
        # always exclude null/empty SKU rows
        w,p=["sku IS NOT NULL AND sku<>''"],[ ]
        if se:
            search_where, search_params = contains_terms_where(se, ['sku', 'nombre'])
            if search_where:
                w.append(search_where)
                p += search_params
        if ca: w.append("categoria_nombre=?"); p.append(ca)
        if es=='sin_stock': w.append("(stock_actual<=0 OR stock_actual IS NULL)")
        elif es=='critico': w.append("stock_actual>0 AND stock_actual <= COALESCE(NULLIF(stock_minimo,0),5)")
        elif es=='bajo': w.append("stock_actual > COALESCE(NULLIF(stock_minimo,0),5) AND stock_actual <= COALESCE(NULLIF(stock_maximo,0),50)")
        elif es=='normal': w.append("stock_actual > COALESCE(NULLIF(stock_maximo,0),50)")
        ws=(' WHERE '+' AND '.join(w)) if w else ''
        vs={'sku':'sku','nombre':'nombre','stock':'stock_actual','categoria':'categoria_nombre','precio':'precio_unitario_promedio'}
        sc=vs.get(sb,'nombre'); dr='DESC' if sd=='desc' else 'ASC'
        t=c.execute(f'SELECT COUNT(*) FROM items{ws}',p).fetchone()[0]; o=(pg-1)*pp2
        rows=c.execute(
            f'''SELECT
                    sku,
                    nombre,
                    stock_actual,
                    unidad_medida_nombre,
                    ubicacion_nombre,
                    sku_alternativo,
                    categoria_nombre,
                    subcategoria_nombre,
                    COALESCE(
                        (
                            SELECT mi.proveedor_nombre
                            FROM movimientos_ingreso mi
                            WHERE mi.item_sku = items.sku
                              AND mi.proveedor_nombre IS NOT NULL
                              AND TRIM(mi.proveedor_nombre) <> ''
                            ORDER BY CAST(mi.fecha_orden AS REAL) DESC, mi.rowid DESC
                            LIMIT 1
                        ),
                        proveedor_principal_nombre
                    ) AS proveedor_actual,
                    COALESCE(
                        NULLIF(precio_unitario_promedio, 0),
                        (
                            SELECT CASE
                                WHEN COALESCE(SUM(COALESCE(mi2.cantidad, 0)), 0) > 0
                                THEN SUM(COALESCE(mi2.cantidad, 0) * COALESCE(mi2.precio_unitario, 0))
                                     / SUM(COALESCE(mi2.cantidad, 0))
                                ELSE NULL
                            END
                            FROM movimientos_ingreso mi2
                            WHERE mi2.item_sku = items.sku
                        ),
                        0
                    ) AS precio_actual,
                    ingresos_totales_historicos,
                    consumos_totales_historicos,
                    ajuste_total_historico,
                    valor_stock_final,
                    stock_minimo,
                    stock_maximo
                FROM items{ws}
                ORDER BY CASE WHEN {sc} IS NULL THEN 1 ELSE 0 END,{sc} {dr}
                LIMIT ? OFFSET ?''',
            p+[pp2,o]
        ).fetchall()
        items=[{'sku':r[0],'nombre':r[1],'stock':r[2] or 0,'unidad':r[3],'ubicacion':r[4],'sku_alt':r[5],'categoria':r[6],'subcategoria':r[7],'proveedor':r[8],'precio':parse_price(r[9]),'ingresos_hist':r[10] or 0,'consumos_hist':r[11] or 0,'ajuste_hist':r[12] or 0,'valor_stock':r[13] or 0,'stock_min':r[14] or 0,'stock_max':r[15] or 0} for r in rows]
        cats=[r[0] for r in c.execute('SELECT DISTINCT categoria_nombre FROM items WHERE categoria_nombre IS NOT NULL ORDER BY categoria_nombre').fetchall()]
        return jsonify({'items':items,'total':t,'page':pg,'per_page':pp2,'total_pages':max(1,-(-t//pp2)),'categorias':cats})
    finally: c.close()

@bp.route('', methods=['POST'], strict_slashes=False)
def api_ci():
    """
    Crea un nuevo producto
    """
    c=get_db()
    try:
        d = request.json or {}
        sku = (d.get('sku') or '').strip().upper()
        if not sku:
            return jsonify({'ok': False, 'msg': 'SKU requerido'}), 400

        exists = c.execute('SELECT 1 FROM items WHERE UPPER(sku)=? LIMIT 1', [sku]).fetchone()
        if exists:
            suggestion = suggest_sku((sku.split('-')[0] or 'NCI').upper())
            return jsonify({'ok': False, 'msg': f'SKU ya existe: {sku}', 'suggested_sku': suggestion}), 400

        c.execute(
            'INSERT INTO items (sku,nombre,stock_actual,unidad_medida_nombre,ubicacion_nombre,categoria_nombre,subcategoria_nombre,proveedor_principal_nombre,precio_unitario_promedio,stock_minimo,stock_maximo) VALUES (?,?,?,?,?,?,?,?,?,?,?)',
            [sku, d.get('nombre'), d.get('stock',0), d.get('unidad'), d.get('ubicacion'), d.get('categoria'), d.get('subcategoria'), d.get('proveedor'), d.get('precio',0), d.get('stock_min',0), d.get('stock_max',0)]
        )
        c.commit()
        return jsonify({'ok':True,'msg':'Producto creado'})
    except Exception as e: return jsonify({'ok':False,'msg':str(e)}),400
    finally: c.close()

@bp.route('/<sku>', methods=['PUT'], strict_slashes=False)
def api_ui(sku):
    """
    Actualiza un producto existente
    """
    c=get_db()
    try:
        d = request.json or {}
        current = c.execute('SELECT stock_actual FROM items WHERE sku=?', [sku]).fetchone()
        if not current:
            return jsonify({'ok': False, 'msg': 'No encontrado'}), 404

        current_stock = float(current[0] or 0)
        requested_stock = d.get('stock', None)
        allow_override = bool(d.get('allow_stock_edit')) and _can_override_stock_update()

        stock_to_save = current_stock
        if requested_stock is not None:
            try:
                requested_stock = float(requested_stock)
            except (TypeError, ValueError):
                return jsonify({'ok': False, 'msg': 'Stock inválido'}), 400

            if allow_override:
                stock_to_save = requested_stock
            elif abs(requested_stock - current_stock) > 1e-9:
                return jsonify({'ok': False, 'msg': 'Para corregir stock usa Auditorías (conteo físico)'}), 400

        c.execute(
            'UPDATE items SET nombre=?,stock_actual=?,unidad_medida_nombre=?,ubicacion_nombre=?,categoria_nombre=?,subcategoria_nombre=?,proveedor_principal_nombre=?,precio_unitario_promedio=?,stock_minimo=?,stock_maximo=? WHERE sku=?',
            [
                d.get('nombre'), stock_to_save, d.get('unidad'), d.get('ubicacion'), d.get('categoria'),
                d.get('subcategoria'), d.get('proveedor'), d.get('precio'), d.get('stock_min', 0),
                d.get('stock_max', 0), sku
            ]
        )
        c.commit()
        return jsonify({'ok':True,'msg':'Producto actualizado'})
    finally: c.close()

@bp.route('/<sku>', methods=['DELETE'], strict_slashes=False)
def api_di(sku):
    """
    Elimina un producto
    """
    # reject invalid identifiers
    if not sku or sku.lower() in ('null','none'):
        return jsonify({'ok':False,'msg':'SKU inválido'}),400
    c=get_db()
    try:
        cur = c.execute('DELETE FROM items WHERE sku=?',[sku])
        # sqlite cursor has rowcount
        if getattr(cur, 'rowcount', 0) == 0:
            c.commit()
            return jsonify({'ok':False,'msg':'No encontrado'}),404
        c.commit();
        return jsonify({'ok':True,'msg':'Producto eliminado'})
    finally: c.close()

@bp.route('/search', strict_slashes=False)
def api_is():
    """
    Búsqueda rápida de productos (autocomplete)
    """
    c=get_db()
    try:
        q=request.args.get('q','').strip()
        if len(q)<1: return jsonify([])
        search_where, search_params = contains_terms_where(q, ['sku', 'nombre'])
        if not search_where:
            return jsonify([])
        rows=c.execute(f'SELECT sku,nombre,stock_actual,unidad_medida_nombre,stock_minimo,stock_maximo FROM items WHERE {search_where} ORDER BY nombre LIMIT 20', search_params).fetchall()
        return jsonify([{'sku':r[0],'nombre':r[1],'stock':r[2] or 0,'unidad':r[3],'stock_min':r[4] or 0,'stock_max':r[5] or 0} for r in rows])
    finally: c.close()

@bp.route('/<sku>/ficha', strict_slashes=False)
def api_ficha(sku):
    """
    Obtiene ficha técnica completa de un producto
    """
    c=get_db()
    try:
        item=c.execute('SELECT * FROM items WHERE sku=?',[sku]).fetchone()
        if not item: return jsonify({'ok':False}),404
        d=dict(item); d['precio_unitario_promedio']=parse_price(d.get('precio_unitario_promedio'))

        last_supplier = c.execute(
            '''SELECT proveedor_nombre, precio_unitario, fecha_orden
               FROM movimientos_ingreso
               WHERE item_sku=?
                 AND proveedor_nombre IS NOT NULL
                 AND TRIM(proveedor_nombre)<>''
               ORDER BY CAST(fecha_orden AS REAL) DESC, rowid DESC
               LIMIT 1''',
            [sku]
        ).fetchone()

        if last_supplier:
            d['proveedor_ultimo_nombre'] = last_supplier[0]
            d['proveedor_ultimo_precio'] = parse_price(last_supplier[1])
            d['proveedor_ultima_fecha'] = excel_to_date(last_supplier[2])
        else:
            d['proveedor_ultimo_nombre'] = d.get('proveedor_principal_nombre')
            d['proveedor_ultimo_precio'] = None
            d['proveedor_ultima_fecha'] = None

        suppliers = c.execute(
            '''SELECT DISTINCT proveedor_nombre
               FROM movimientos_ingreso
               WHERE item_sku=?
                 AND proveedor_nombre IS NOT NULL
                 AND TRIM(proveedor_nombre)<>''
               ORDER BY proveedor_nombre''',
            [sku]
        ).fetchall()

        proveedores_compra = []
        for row in suppliers:
            prov = row[0]
            latest_row = c.execute(
                '''SELECT precio_unitario, fecha_orden
                   FROM movimientos_ingreso
                   WHERE item_sku=? AND proveedor_nombre=?
                   ORDER BY CAST(fecha_orden AS REAL) DESC, rowid DESC
                   LIMIT 1''',
                [sku, prov]
            ).fetchone()
            count_row = c.execute(
                'SELECT COUNT(*) FROM movimientos_ingreso WHERE item_sku=? AND proveedor_nombre=?',
                [sku, prov]
            ).fetchone()

            proveedores_compra.append({
                'proveedor': prov,
                'precio_ultimo': parse_price(latest_row[0]) if latest_row else 0,
                'fecha_ultima': excel_to_date(latest_row[1]) if latest_row else None,
                'compras': count_row[0] if count_row else 0
            })

        d['proveedores_compra'] = proveedores_compra
        d['proveedores_compra_count'] = len(proveedores_compra)

        price_rows = c.execute(
            '''SELECT precio_unitario, fecha_orden, proveedor_nombre
               FROM movimientos_ingreso
               WHERE item_sku=?
                 AND precio_unitario IS NOT NULL
               ORDER BY CAST(fecha_orden AS REAL) DESC, rowid DESC
               LIMIT 2''',
            [sku]
        ).fetchall()

        variacion_precio = {
            'precio_actual': None,
            'precio_anterior': None,
            'delta_abs': 0,
            'delta_pct': 0,
            'tiene_variacion': False,
            'tendencia': 'sin_datos',
            'fecha_actual': None,
            'fecha_anterior': None,
            'proveedor_actual': None,
            'proveedor_anterior': None,
        }
        if price_rows:
            precio_actual = parse_price(price_rows[0][0])
            variacion_precio['precio_actual'] = precio_actual
            variacion_precio['fecha_actual'] = excel_to_date(price_rows[0][1])
            variacion_precio['proveedor_actual'] = price_rows[0][2]

            if len(price_rows) > 1:
                precio_anterior = parse_price(price_rows[1][0])
                variacion_precio['precio_anterior'] = precio_anterior
                variacion_precio['fecha_anterior'] = excel_to_date(price_rows[1][1])
                variacion_precio['proveedor_anterior'] = price_rows[1][2]

                delta_abs = round(precio_actual - precio_anterior, 2)
                delta_pct = round((delta_abs / precio_anterior) * 100, 2) if precio_anterior > 0 else 0
                variacion_precio['delta_abs'] = delta_abs
                variacion_precio['delta_pct'] = delta_pct
                variacion_precio['tiene_variacion'] = True
                if delta_abs > 0:
                    variacion_precio['tendencia'] = 'alza'
                elif delta_abs < 0:
                    variacion_precio['tendencia'] = 'baja'
                else:
                    variacion_precio['tendencia'] = 'estable'

        d['variacion_precio'] = variacion_precio

        ing=c.execute('SELECT fecha_orden,cantidad,precio_unitario,total_ingreso,proveedor_nombre,numero_factura,numero_guia_despacho FROM movimientos_ingreso WHERE item_sku=? ORDER BY rowid DESC LIMIT 10',[sku]).fetchall()
        d['ultimos_ingresos']=[{'fecha':excel_to_date(r[0]),'cantidad':r[1],'precio':r[2] or 0,'total':r[3] or 0,'proveedor':r[4],'factura':r[5],'guia':r[6]} for r in ing]
        con=c.execute('SELECT rowid,fecha_consumo,cantidad_consumida,solicitante_nombre,orden_trabajo_id,stock_actual_en_consumo,observaciones FROM movimientos_consumo WHERE item_sku=? ORDER BY rowid DESC LIMIT 10',[sku]).fetchall()
        d['ultimos_consumos']=[{'rowid':r[0],'source':'movimiento','sku':sku,'fecha':excel_to_date(r[1]),'cantidad':r[2],'solicitante':r[3],'ot':r[4],'stock_post':r[5],'obs':r[6] or ''} for r in con]
        consumo_acumulado = _get_accumulated_consumo(c, sku)
        if consumo_acumulado:
            d['ultimos_consumos'].append({
                'rowid': None,
                'source': 'acumulado',
                'sku': sku,
                'fecha': None,
                'cantidad': consumo_acumulado['cantidad'],
                'solicitante': '',
                'ot': consumo_acumulado.get('ot', ''),
                'stock_post': consumo_acumulado['stock_post'],
                'obs': ''
            })
        d['total_ingresos_count']=c.execute('SELECT COUNT(*) FROM movimientos_ingreso WHERE item_sku=?',[sku]).fetchone()[0]
        d['total_consumos_count']=c.execute('SELECT COUNT(*) FROM movimientos_consumo WHERE item_sku=?',[sku]).fetchone()[0] + (1 if consumo_acumulado else 0)
        d['total_ingresado']=c.execute('SELECT COALESCE(SUM(cantidad),0) FROM movimientos_ingreso WHERE item_sku=?',[sku]).fetchone()[0]
        d['total_consumido']=c.execute('SELECT COALESCE(SUM(cantidad_consumida),0) FROM movimientos_consumo WHERE item_sku=?',[sku]).fetchone()[0] + (consumo_acumulado['cantidad'] if consumo_acumulado else 0)
        return jsonify({'ok':True,'data':d})
    finally: c.close()

@bp.route('/clean', methods=['POST'], strict_slashes=False)
def api_clean_items():
    """
    Elimina filas de items con SKU nulo o vacío.
    Método: POST (se trata como operación irreversible)
    """
    c = get_db()
    try:
        cur = c.execute("DELETE FROM items WHERE sku IS NULL OR sku='' ")
        deleted = cur.rowcount if hasattr(cur,'rowcount') else None
        c.commit()
        return jsonify({'ok':True,'deleted':deleted})
    finally:
        c.close()

@bp.route('/<sku>/kardex', strict_slashes=False)
def api_kardex(sku):
    """
    Obtiene el kardex (historial de movimientos) de un producto
    """
    c=get_db()
    try:
        pg=int(request.args.get('page',1)); pp2=int(request.args.get('per_page',100))
        ing=c.execute("SELECT rowid,fecha_orden,'INGRESO',cantidad,precio_unitario,proveedor_nombre,numero_factura,numero_guia_despacho,observaciones FROM movimientos_ingreso WHERE item_sku=?",[sku]).fetchall()
        con=c.execute("SELECT rowid,fecha_consumo,'CONSUMO',cantidad_consumida,precio_unitario,solicitante_nombre,CAST(orden_trabajo_id AS TEXT),'',observaciones FROM movimientos_consumo WHERE item_sku=?",[sku]).fetchall()
        consumo_acumulado = _get_accumulated_consumo(c, sku)
        all_m=[]
        for r in ing: all_m.append({'rid':r[0],'rowid':r[0],'source':'ingreso','sku':sku,'fecha':excel_to_date(r[1]),'fr':r[1],'tipo':'INGRESO','cant':r[3],'precio':r[4] or 0,'ref1':r[5],'ref2':r[6],'ref3':r[7],'obs':r[8]})
        for r in con: all_m.append({'rid':r[0],'rowid':r[0],'source':'movimiento','sku':sku,'fecha':excel_to_date(r[1]),'fr':r[1],'tipo':'CONSUMO','cant':r[3],'precio':r[4] or 0,'ref1':r[5],'ref2':r[6],'ref3':r[7],'obs':r[8]})
        if consumo_acumulado:
            all_m.append({'rid':0,'rowid':None,'source':'acumulado','sku':sku,'fecha':None,'fr':None,'tipo':'CONSUMO','cant':consumo_acumulado['cantidad'],'precio':consumo_acumulado['precio'],'ref1':'','ref2':consumo_acumulado.get('ot', ''),'ref3':'','obs':'Saldo inicial de consumo'})
        def sk(m):
            try: return (float(m['fr'] or 0),m['rid'])
            except: return (0,m['rid'])
        all_m.sort(key=sk)
        saldo=0
        for m in all_m:
            saldo += m['cant'] if m['tipo']=='INGRESO' else -m['cant']
            m['saldo']=round(saldo,2)
        t=len(all_m); all_m.reverse(); o=(pg-1)*pp2
        return jsonify({'items':all_m[o:o+pp2],'total':t,'page':pg,'per_page':pp2,'total_pages':max(1,-(-t//pp2))})
    finally: c.close()
