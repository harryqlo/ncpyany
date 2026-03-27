
from flask import Blueprint, jsonify, request
from app.db import get_db, date_to_excel, excel_to_date
from app.search_utils import contains_terms_where
from app.services.ingresos_pdf_service import parse_ingreso_pdf
from datetime import datetime
import re
import unicodedata

bp = Blueprint('ingresos', __name__, url_prefix='/api/ingresos')


def _ensure_ingresos_schema(c):
    cols = {row[1] for row in c.execute('PRAGMA table_info(movimientos_ingreso)').fetchall()}
    if 'numero_documento_transportista' not in cols:
        c.execute('ALTER TABLE movimientos_ingreso ADD COLUMN numero_documento_transportista TEXT')


def _begin_write_tx(c):
    c.execute('BEGIN IMMEDIATE')


def _recalc_item_avg_price(c, sku):
    """
    Recalcula y persiste el precio_unitario_promedio de un item
    en base a su historial de ingresos.
    """
    if not sku:
        return

    row = c.execute(
        '''SELECT
               COALESCE(SUM(COALESCE(cantidad,0) * COALESCE(precio_unitario,0)),0) AS total_valor,
               COALESCE(SUM(COALESCE(cantidad,0)),0) AS total_cantidad
           FROM movimientos_ingreso
           WHERE item_sku=?''',
        [sku]
    ).fetchone()

    total_valor = float((row[0] if row else 0) or 0)
    total_cantidad = float((row[1] if row else 0) or 0)
    avg = round(total_valor / total_cantidad, 4) if total_cantidad > 0 else 0

    c.execute('UPDATE items SET precio_unitario_promedio=? WHERE sku=?', [avg, sku])


def _norm_provider(value):
    text = (value or '').strip().lower()
    if not text:
        return ''
    text = ''.join(ch for ch in unicodedata.normalize('NFD', text) if unicodedata.category(ch) != 'Mn')
    text = re.sub(r'[^a-z0-9\s]', ' ', text)
    text = re.sub(r'\b(spa|ltda|s\s*a|s\s*a\s*\.|eirl|limitada|sociedad\s+anonima)\b', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def _canonical_provider_name(c, provided_name):
    incoming = (provided_name or '').strip()
    if not incoming:
        return ''

    incoming_norm = _norm_provider(incoming)
    if not incoming_norm:
        return incoming

    rows = c.execute(
        '''SELECT proveedor_nombre
           FROM movimientos_ingreso
           WHERE proveedor_nombre IS NOT NULL AND TRIM(proveedor_nombre)<>''
           GROUP BY proveedor_nombre
           ORDER BY COUNT(*) DESC, proveedor_nombre ASC'''
    ).fetchall()

    for row in rows:
        existing = (row[0] or '').strip()
        if existing and _norm_provider(existing) == incoming_norm:
            return existing

    return incoming


@bp.route('/proveedores', strict_slashes=False)
def api_ing_proveedores():
    """Devuelve sugerencias de proveedores para autocompletar."""
    c = get_db()
    try:
        _ensure_ingresos_schema(c)
        q = (request.args.get('q', '') or '').strip()
        q_norm = _norm_provider(q)
        rows = c.execute(
            '''SELECT proveedor_nombre, COUNT(*) AS usos
               FROM movimientos_ingreso
               WHERE proveedor_nombre IS NOT NULL AND TRIM(proveedor_nombre)<>''
               GROUP BY proveedor_nombre
               ORDER BY usos DESC, proveedor_nombre ASC
               LIMIT 250'''
        ).fetchall()

        items = []
        seen_norm = set()
        for row in rows:
            name = (row[0] or '').strip()
            if not name:
                continue
            norm = _norm_provider(name)
            if not norm or norm in seen_norm:
                continue
            if q_norm and q_norm not in norm:
                continue
            seen_norm.add(norm)
            items.append({'nombre': name, 'usos': row[1] or 0})
            if len(items) >= 40:
                break

        return jsonify({'ok': True, 'items': items})
    finally:
        c.close()


@bp.route('/preview-pdf', methods=['POST'], strict_slashes=False)
def api_ing_preview_pdf():
    """
    Analiza un PDF de proveedor y devuelve una previsualización editable.
    No registra datos en BD. Requiere confirmación humana en frontend.
    """
    c = get_db()
    try:
        _ensure_ingresos_schema(c)
        file = request.files.get('pdf')
        if not file:
            return jsonify({'ok': False, 'msg': 'Debes adjuntar un archivo PDF'}), 400

        filename = (file.filename or '').strip().lower()
        if not filename.endswith('.pdf'):
            return jsonify({'ok': False, 'msg': 'Formato no válido: solo se permite PDF'}), 400

        file.stream.seek(0, 2)
        size = file.stream.tell()
        file.stream.seek(0)
        max_size_bytes = 12 * 1024 * 1024
        if size > max_size_bytes:
            return jsonify({'ok': False, 'msg': 'PDF demasiado grande (máximo 12MB)'}), 400

        try:
            preview = parse_ingreso_pdf(file.stream, c)
        except RuntimeError as dep_err:
            return jsonify({'ok': False, 'msg': str(dep_err)}), 500

        return jsonify({
            'ok': True,
            'msg': 'PDF analizado. Revisa y confirma antes de registrar.',
            'preview': preview,
        })
    except Exception as e:
        return jsonify({'ok': False, 'msg': f'Error analizando PDF: {e}'}), 400
    finally:
        c.close()

@bp.route('', strict_slashes=False)
def api_ing():
    """
    Obtiene listado de ingresos con filtros y paginación.
    También devuelve totales agregados (cantidad y valor) sobre el conjunto.
    """
    c=get_db()
    try:
        _ensure_ingresos_schema(c)
        pg=int(request.args.get('page',1)); pp2=int(request.args.get('per_page',50))
        se=request.args.get('search','').strip(); ff=request.args.get('from',''); ft=request.args.get('to','')
        w,p=[],[]
        if se:
            search_where, search_params = contains_terms_where(
                se,
                ['item_sku', 'descripcion_item', 'proveedor_nombre', 'numero_factura', 'numero_guia_despacho', 'numero_orden_compra', 'transportista_nombre', 'numero_documento_transportista']
            )
            if search_where:
                w.append(search_where)
                p += search_params
        if ff:
            s=date_to_excel(ff)
            if s: w.append("CAST(fecha_orden AS REAL)>=?"); p.append(s)
        if ft:
            s=date_to_excel(ft)
            if s: w.append("CAST(fecha_orden AS REAL)<=?"); p.append(s)
        ws=(' WHERE '+' AND '.join(w)) if w else ''
        # total de filas para paginación
        t=c.execute(f'SELECT COUNT(*) FROM movimientos_ingreso{ws}',p).fetchone()[0]
        # totales agregados sobre el filtro
        sum_qty=c.execute(f'SELECT SUM(cantidad) FROM movimientos_ingreso{ws}',p).fetchone()[0] or 0
        sum_total=c.execute(f'SELECT SUM(total_ingreso) FROM movimientos_ingreso{ws}',p).fetchone()[0] or 0
        o=(pg-1)*pp2
        rows=c.execute(f'SELECT rowid,mes,fecha_orden,item_sku,cantidad,descripcion_item,categoria_item,unidad_medida_item,precio_unitario,descuento_monto,descuento_porcentaje,total_ingreso,proveedor_nombre,numero_factura,numero_guia_despacho,numero_orden_compra,transportista_nombre,numero_documento_transportista,observaciones FROM movimientos_ingreso{ws} ORDER BY CAST(fecha_orden AS REAL) DESC LIMIT ? OFFSET ?',p+[pp2,o]).fetchall()
        items=[{'rowid':r[0],'mes':r[1],'fecha':excel_to_date(r[2]),'sku':r[3],'cantidad':r[4],'descripcion':r[5],'categoria':r[6],'unidad':r[7],'precio':r[8] or 0,'descuento':r[9] or 0,'desc_pct':r[10] or 0,'total':r[11] or 0,'proveedor':r[12],'factura':r[13],'guia':r[14],'oc':r[15],'transportista':r[16],'transportista_doc':r[17],'obs':r[18]} for r in rows]
        return jsonify({'items':items,'total':t,'page':pg,'per_page':pp2,'total_pages':max(1,-(-t//pp2)),'sum_qty':sum_qty,'sum_total':sum_total})
    finally: c.close()

@bp.route('', methods=['POST'], strict_slashes=False)
def api_ci2():
    """
    Crea un nuevo ingreso (entrada) de producto
    """
    c=get_db()
    try:
        _ensure_ingresos_schema(c)
        d=request.json; fs=date_to_excel(d.get('fecha',datetime.now().strftime('%Y-%m-%d'))); q=float(d.get('cantidad',0)); pr=float(d.get('precio',0))
        prov = _canonical_provider_name(c, d.get('proveedor', ''))
        _begin_write_tx(c)
        c.execute('INSERT INTO movimientos_ingreso (mes,fecha_orden,item_sku,cantidad,descripcion_item,categoria_item,unidad_medida_item,precio_unitario,total_ingreso,proveedor_nombre,numero_factura,numero_guia_despacho,numero_orden_compra,transportista_nombre,numero_documento_transportista,observaciones) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',[d.get('mes',''),fs,d['sku'],q,d.get('descripcion',''),d.get('categoria',''),d.get('unidad',''),pr,q*pr,prov,d.get('factura',''),d.get('guia',''),d.get('oc',''),d.get('transportista',''),d.get('transportista_doc',''),d.get('observaciones','')])
        c.execute('UPDATE items SET stock_actual=COALESCE(stock_actual,0)+? WHERE sku=?',[q,d['sku']])
        _recalc_item_avg_price(c, d['sku'])
        c.commit()
        return jsonify({'ok':True,'msg':'Ingreso registrado'})
    except Exception as e:
        c.rollback()
        return jsonify({'ok':False,'msg':str(e)}),400
    finally: c.close()

@bp.route('/batch', methods=['POST'], strict_slashes=False)
def api_ib():
    """
    Crea múltiples ingresos en una sola transacción (batch)
    """
    c=get_db()
    try:
        _ensure_ingresos_schema(c)
        d=request.json; fs=date_to_excel(d.get('fecha',datetime.now().strftime('%Y-%m-%d')))
        prov=_canonical_provider_name(c, d.get('proveedor','')); fact=d.get('factura',''); guia=d.get('guia',''); oc=d.get('oc',''); transp=d.get('transportista',''); transp_doc=d.get('transportista_doc',''); obs=d.get('observaciones','')
        items=d.get('items',[]); reg=0; err=[]
        if not items: return jsonify({'ok':False,'msg':'Sin productos'}),400
        _begin_write_tx(c)
        skus_tocados = set()
        for it in items:
            sk=it.get('sku','').strip(); q=float(it.get('cantidad',0)); pr=float(it.get('precio',0)); dp=float(it.get('descuento_pct',0))
            dm=round(q*pr*dp/100,2); tot=round(q*pr-dm,2)
            if not sk or q<=0: err.append(f'{sk}: inválido'); continue
            row=c.execute('SELECT nombre,categoria_nombre,unidad_medida_nombre FROM items WHERE sku=?',[sk]).fetchone()
            desc=row[0] if row else it.get('descripcion',''); cat=row[1] if row else ''; uni=row[2] if row else ''
            fecha_str=d.get('fecha','')
            c.execute('INSERT INTO movimientos_ingreso (mes,fecha_orden,item_sku,cantidad,descripcion_item,categoria_item,unidad_medida_item,precio_unitario,descuento_monto,descuento_porcentaje,total_ingreso,proveedor_nombre,numero_factura,numero_guia_despacho,numero_orden_compra,transportista_nombre,numero_documento_transportista,observaciones) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',[fecha_str[:7] if fecha_str else '',fs,sk,q,desc,cat,uni,pr,dm,dp,tot,prov,fact,guia,oc,transp,transp_doc,obs])
            c.execute('UPDATE items SET stock_actual=COALESCE(stock_actual,0)+? WHERE sku=?',[q,sk]); reg+=1
            skus_tocados.add(sk)

        for sku in skus_tocados:
            _recalc_item_avg_price(c, sku)

        c.commit(); msg=f'{reg} producto(s) ingresado(s)'
        if err: msg+=f'. Errores: {"; ".join(err)}'
        return jsonify({'ok':reg>0,'msg':msg,'registrados':reg,'errores':err})
    except Exception as e: c.rollback(); return jsonify({'ok':False,'msg':str(e)}),400
    finally: c.close()

@bp.route('/<int:ing_id>', strict_slashes=False)
def api_ig_detail(ing_id):
    """
    Obtiene el detalle completo de un ingreso específico
    """
    c = get_db()
    try:
        _ensure_ingresos_schema(c)
        row = c.execute('SELECT rowid, fecha_orden, proveedor_nombre, numero_factura, numero_guia_despacho, numero_orden_compra, transportista_nombre, numero_documento_transportista, observaciones FROM movimientos_ingreso WHERE rowid=?', [ing_id]).fetchone()
        if not row:
            return jsonify({'ok': False, 'msg': 'No encontrado'}), 404
        
        # Agrupar items del mismo ingreso
        items_rows = c.execute('SELECT item_sku, cantidad, precio_unitario, descuento_porcentaje, descripcion_item, unidad_medida_item FROM movimientos_ingreso WHERE rowid=?', [ing_id]).fetchall()
        items = [{'sku': r[0], 'cantidad': r[1], 'precio': r[2] or 0, 'descuento_pct': r[3] or 0, 'nombre': r[4], 'unidad': r[5]} for r in items_rows]
        
        return jsonify({
            'ok': True,
            'data': {
                'id': row[0],
                'fecha': excel_to_date(row[1]),
                'proveedor': row[2],
                'factura': row[3],
                'guia': row[4],
                'oc': row[5],
                'transportista': row[6],
                'transportista_doc': row[7],
                'observaciones': row[8],
                'items': items
            }
        })
    finally:
        c.close()

@bp.route('/<int:ing_id>', methods=['PUT'], strict_slashes=False)
def api_ig_update(ing_id):
    """
    Actualiza un ingreso existente
    """
    c = get_db()
    try:
        _ensure_ingresos_schema(c)
        d = request.json
        _begin_write_tx(c)
        
        # Obtener ingreso actual (una sola fila)
        old = c.execute('SELECT item_sku,cantidad,fecha_orden,proveedor_nombre,numero_factura,numero_guia_despacho,numero_orden_compra,transportista_nombre,numero_documento_transportista,observaciones FROM movimientos_ingreso WHERE rowid=?', [ing_id]).fetchone()
        if not old:
            c.rollback()
            return jsonify({'ok': False, 'msg': 'No encontrado'}), 404
        # revertir stock de la fila antigua
        old_sku, old_q = old[0], old[1]
        c.execute('UPDATE items SET stock_actual=COALESCE(stock_actual,0)-? WHERE sku=?', [old_q, old_sku])
        
        # preparar valores nuevos (usar primer item si se envía array)
        it = None
        if isinstance(d.get('items'), list) and d['items']:
            it = d['items'][0]
        # fecha y otros campos
        prov = _canonical_provider_name(c, d.get('proveedor', old[3] or ''))
        fact = d.get('factura', old[4] or '')
        guia = d.get('guia', old[5] or '')
        oc = d.get('oc', old[6] or '')
        transp = d.get('transportista', old[7] or '')
        transp_doc = d.get('transportista_doc', old[8] or '')
        obs = d.get('observaciones', old[9] or '')
        # manejo de fecha: si se envía un string, convertir; si no, mantener valor antiguo
        if 'fecha' in d and d['fecha']:
            fecha_str = d['fecha']
            fs = date_to_excel(fecha_str)
        else:
            fecha_str = old[2]
            fs = fecha_str  # ya es serial/número
        
        # datos de SKU/cantidad/precio/etc
        if it:
            sk = it.get('sku', old_sku).strip()
            q = float(it.get('cantidad', old_q))
            pr = float(it.get('precio', 0))
            dp = float(it.get('descuento_pct', 0))
        else:
            sk = d.get('sku', old_sku).strip()
            q = float(d.get('cantidad', old_q))
            pr = float(d.get('precio', 0))
            dp = float(d.get('descuento_pct', 0))
        dm = round(q * pr * dp / 100, 2)
        tot = round(q * pr - dm, 2)
        
        # obtener descripción, categoría, unidad actuales si SKU cambió
        row = c.execute('SELECT nombre, categoria_nombre, unidad_medida_nombre FROM items WHERE sku=?', [sk]).fetchone()
        desc = row[0] if row else ''
        cat = row[1] if row else ''
        uni = row[2] if row else ''
        
        # actualizar la fila existente
        # mes almacenado como primeros 7 caracteres si fecha_str es string
        let_mes = ''
        if isinstance(fecha_str, str) and fecha_str:
            let_mes = fecha_str[:7]
        c.execute('UPDATE movimientos_ingreso SET mes=?, fecha_orden=?, item_sku=?, cantidad=?, descripcion_item=?, categoria_item=?, unidad_medida_item=?, precio_unitario=?, descuento_monto=?, descuento_porcentaje=?, total_ingreso=?, proveedor_nombre=?, numero_factura=?, numero_guia_despacho=?, numero_orden_compra=?, transportista_nombre=?, numero_documento_transportista=?, observaciones=? WHERE rowid=?',
               [let_mes, fs, sk, q, desc, cat, uni, pr, dm, dp, tot, prov, fact, guia, oc, transp, transp_doc, obs, ing_id])
        # aplicar stock para nueva cantidad/sku
        c.execute('UPDATE items SET stock_actual=COALESCE(stock_actual,0)+? WHERE sku=?', [q, sk])

        _recalc_item_avg_price(c, old_sku)
        if sk != old_sku:
            _recalc_item_avg_price(c, sk)
        
        c.commit()
        return jsonify({'ok': True, 'msg': 'Ingreso actualizado'})
    except Exception as e:
        c.rollback()
        return jsonify({'ok': False, 'msg': str(e)}), 400
    finally:
        c.close()

@bp.route('/<int:ing_id>', methods=['DELETE'], strict_slashes=False)
def api_ig_delete(ing_id):
    """
    Elimina un ingreso y revierte los cambios de stock
    """
    c = get_db()
    try:
        _ensure_ingresos_schema(c)
        _begin_write_tx(c)
        # Obtener items del ingreso
        items = c.execute('SELECT item_sku, cantidad FROM movimientos_ingreso WHERE rowid=?', [ing_id]).fetchall()
        
        if not items:
            c.rollback()
            return jsonify({'ok': False, 'msg': 'No encontrado'}), 404
        
        # Revertir stock
        skus_tocados = set()
        for sk, q in items:
            c.execute('UPDATE items SET stock_actual=COALESCE(stock_actual,0)-? WHERE sku=?', [q, sk])
            skus_tocados.add(sk)
        
        # Eliminar ingreso
        c.execute('DELETE FROM movimientos_ingreso WHERE rowid=?', [ing_id])

        for sku in skus_tocados:
            _recalc_item_avg_price(c, sku)

        c.commit()
        
        return jsonify({'ok': True, 'msg': 'Ingreso eliminado'})
    except Exception as e:
        c.rollback()
        return jsonify({'ok': False, 'msg': str(e)}), 400
    finally:
        c.close()


@bp.route('/documento', methods=['PUT'], strict_slashes=False)
def api_ig_document_update():
    """
    Edita un documento de ingreso completo en una sola transacción.
    Permite actualizar, agregar y eliminar líneas del documento.
    """
    c = get_db()
    try:
        _ensure_ingresos_schema(c)
        d = request.json or {}
        items = d.get('items', [])
        if not items:
            return jsonify({'ok': False, 'msg': 'Documento sin insumos'}), 400

        _begin_write_tx(c)

        fecha = d.get('fecha', datetime.now().strftime('%Y-%m-%d'))
        fs = date_to_excel(fecha)
        proveedor = _canonical_provider_name(c, d.get('proveedor', ''))
        factura = (d.get('factura') or '').strip()
        guia = (d.get('guia') or '').strip()
        oc = (d.get('oc') or '').strip()
        transportista = (d.get('transportista') or '').strip()
        transportista_doc = (d.get('transportista_doc') or '').strip()
        observaciones = (d.get('observaciones') or '').strip()

        normalized_items = []
        rowids = []
        seen_existing = set()

        for raw in items:
            sku = (raw.get('sku') or '').strip()
            cantidad = float(raw.get('cantidad', 0) or 0)
            precio = float(raw.get('precio', 0) or 0)
            descuento_pct = float(raw.get('descuento_pct', 0) or 0)

            rowid = raw.get('rowid')
            if rowid not in (None, ''):
                rowid = int(rowid)
            else:
                rowid = None

            if not sku:
                return jsonify({'ok': False, 'msg': 'Hay un insumo sin SKU'}), 400
            if cantidad <= 0:
                continue
            if rowid is not None:
                if rowid in seen_existing:
                    return jsonify({'ok': False, 'msg': 'Hay filas duplicadas en el documento'}), 400
                seen_existing.add(rowid)
                rowids.append(rowid)

            normalized_items.append({
                'rowid': rowid,
                'sku': sku,
                'cantidad': cantidad,
                'precio': precio,
                'descuento_pct': descuento_pct,
            })

        if not normalized_items:
            return jsonify({'ok': False, 'msg': 'Documento sin cantidades válidas'}), 400

        existing_rows = []
        existing_map = {}
        if rowids:
            marks = ','.join(['?'] * len(rowids))
            existing_rows = c.execute(
                f'SELECT rowid,item_sku,cantidad FROM movimientos_ingreso WHERE rowid IN ({marks})',
                rowids
            ).fetchall()
            existing_map = {int(row[0]): row for row in existing_rows}
            if len(existing_map) != len(set(rowids)):
                return jsonify({'ok': False, 'msg': 'Algunas filas del documento ya no existen'}), 404

        touched_skus = set()

        for row in existing_rows:
            old_sku = row[1]
            old_q = float(row[2] or 0)
            c.execute('UPDATE items SET stock_actual=COALESCE(stock_actual,0)-? WHERE sku=?', [old_q, old_sku])
            touched_skus.add(old_sku)

        updated_rowids = set()
        created = 0
        removed = 0

        for item in normalized_items:
            sku = item['sku']
            cantidad = item['cantidad']
            precio = item['precio']
            descuento_pct = item['descuento_pct']
            rowid = item['rowid']

            row_item = c.execute(
                'SELECT nombre,categoria_nombre,unidad_medida_nombre FROM items WHERE sku=?',
                [sku]
            ).fetchone()
            if not row_item:
                raise ValueError(f'SKU no encontrado: {sku}')

            descripcion = row_item[0] or ''
            categoria = row_item[1] or ''
            unidad = row_item[2] or ''
            descuento_monto = round(cantidad * precio * descuento_pct / 100, 2)
            total = round(cantidad * precio - descuento_monto, 2)
            mes = fecha[:7] if isinstance(fecha, str) and fecha else ''

            c.execute('UPDATE items SET stock_actual=COALESCE(stock_actual,0)+? WHERE sku=?', [cantidad, sku])
            touched_skus.add(sku)

            if rowid is not None:
                c.execute(
                    '''UPDATE movimientos_ingreso
                       SET mes=?,fecha_orden=?,item_sku=?,cantidad=?,descripcion_item=?,categoria_item=?,unidad_medida_item=?,
                           precio_unitario=?,descuento_monto=?,descuento_porcentaje=?,total_ingreso=?,proveedor_nombre=?,
                           numero_factura=?,numero_guia_despacho=?,numero_orden_compra=?,transportista_nombre=?,numero_documento_transportista=?,observaciones=?
                       WHERE rowid=?''',
                    [mes, fs, sku, cantidad, descripcion, categoria, unidad, precio, descuento_monto, descuento_pct,
                     total, proveedor, factura, guia, oc, transportista, transportista_doc, observaciones, rowid]
                )
                updated_rowids.add(rowid)
            else:
                c.execute(
                    '''INSERT INTO movimientos_ingreso
                       (mes,fecha_orden,item_sku,cantidad,descripcion_item,categoria_item,unidad_medida_item,
                        precio_unitario,descuento_monto,descuento_porcentaje,total_ingreso,proveedor_nombre,
                        numero_factura,numero_guia_despacho,numero_orden_compra,transportista_nombre,numero_documento_transportista,observaciones)
                       VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
                    [mes, fs, sku, cantidad, descripcion, categoria, unidad, precio, descuento_monto, descuento_pct,
                     total, proveedor, factura, guia, oc, transportista, transportista_doc, observaciones]
                )
                created += 1

        for row in existing_rows:
            existing_rowid = int(row[0])
            if existing_rowid not in updated_rowids:
                c.execute('DELETE FROM movimientos_ingreso WHERE rowid=?', [existing_rowid])
                removed += 1

        for sku in touched_skus:
            _recalc_item_avg_price(c, sku)

        c.commit()
        return jsonify({
            'ok': True,
            'msg': 'Documento de ingreso actualizado',
            'creados': created,
            'eliminados': removed,
            'actualizados': len(updated_rowids)
        })
    except Exception as e:
        c.rollback()
        return jsonify({'ok': False, 'msg': str(e)}), 400
    finally:
        c.close()


@bp.route('/documento', methods=['DELETE'], strict_slashes=False)
def api_ig_document_delete():
    """
    Elimina un documento completo de ingreso y revierte stock.
    """
    c = get_db()
    try:
        _ensure_ingresos_schema(c)
        d = request.json or {}
        rowids = [int(rowid) for rowid in (d.get('rowids') or []) if rowid not in (None, '')]
        if not rowids:
            return jsonify({'ok': False, 'msg': 'Documento sin filas válidas'}), 400

        _begin_write_tx(c)

        marks = ','.join(['?'] * len(rowids))
        rows = c.execute(
            f'SELECT rowid,item_sku,cantidad FROM movimientos_ingreso WHERE rowid IN ({marks})',
            rowids
        ).fetchall()
        if len(rows) != len(set(rowids)):
            c.rollback()
            return jsonify({'ok': False, 'msg': 'Algunas filas del documento ya no existen'}), 404

        touched_skus = set()
        for row in rows:
            sku = row[1]
            cantidad = float(row[2] or 0)
            c.execute('UPDATE items SET stock_actual=COALESCE(stock_actual,0)-? WHERE sku=?', [cantidad, sku])
            touched_skus.add(sku)

        c.execute(f'DELETE FROM movimientos_ingreso WHERE rowid IN ({marks})', rowids)

        for sku in touched_skus:
            _recalc_item_avg_price(c, sku)

        c.commit()
        return jsonify({'ok': True, 'msg': f'Documento eliminado. {len(rows)} insumo(s) revertido(s)'})
    except Exception as e:
        c.rollback()
        return jsonify({'ok': False, 'msg': str(e)}), 400
    finally:
        c.close()
