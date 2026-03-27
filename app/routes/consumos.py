
from flask import Blueprint, jsonify, request
from app.db import get_db, date_to_excel, excel_to_date, parse_price
from app.search_utils import contains_terms_where
from datetime import datetime

bp = Blueprint('consumos', __name__, url_prefix='/api/consumos')


def _ensure_consumos_schema(c):
    cols = {row[1] for row in c.execute('PRAGMA table_info(movimientos_consumo)').fetchall()}
    if 'documento_ref' not in cols:
        c.execute('ALTER TABLE movimientos_consumo ADD COLUMN documento_ref TEXT')
    cols_items = {row[1] for row in c.execute('PRAGMA table_info(items)').fetchall()}
    if 'consumo_historico_ot' not in cols_items:
        c.execute('ALTER TABLE items ADD COLUMN consumo_historico_ot TEXT')


def _generate_documento_ref():
    return datetime.utcnow().strftime('CON-%Y%m%d%H%M%S%f')


def _get_doc_ref(row):
    try:
        return row['documento_ref']
    except Exception:
        return row[11] if len(row) > 11 else None


def _normalize_consumo_row(row):
    return {
        'rowid': row[0],
        'sku': row[1],
        'descripcion': row[2],
        'fecha': excel_to_date(row[3]),
        'solicitante': row[4],
        'cantidad': row[5],
        'precio': row[6] or 0,
        'total': row[7] or 0,
        'ot_id': row[8],
        'obs': row[9],
        'stock_en_consumo': row[10],
        'documento_ref': _get_doc_ref(row),
        'source': 'movimiento'
    }


def _normalize_historical_consumo_row(row):
    cantidad = row[2] or 0
    precio = parse_price(row[4])
    return {
        'rowid': None,
        'sku': row[0],
        'descripcion': row[1],
        'fecha': None,
        'solicitante': '',
        'cantidad': cantidad,
        'precio': precio,
        'total': round(cantidad * precio, 2),
        'ot_id': row[5] or '',
        'obs': '',
        'stock_en_consumo': row[3],
        'documento_ref': None,
        'source': 'acumulado'
    }


def _begin_write_tx(c):
    c.execute('BEGIN IMMEDIATE')


def _deduct_stock_atomic(c, sku, cantidad):
    cur = c.execute(
        'UPDATE items SET stock_actual = COALESCE(stock_actual,0) - ? '
        'WHERE sku=? AND COALESCE(stock_actual,0) >= ?',
        [cantidad, sku, cantidad]
    )
    return (cur.rowcount or 0) > 0

@bp.route('', strict_slashes=False)
def api_con():
    """
    Obtiene listado de consumos con filtros y paginación.
    Combina movimientos detallados + consumos acumulados en una sola vista.
    """
    c=get_db()
    try:
        _ensure_consumos_schema(c)
        pg=int(request.args.get('page',1)); pp2=int(request.args.get('per_page',50)); se=request.args.get('search','').strip()

        # 1) Movimientos detallados
        w,p=[],[]
        if se:
            search_where, search_params = contains_terms_where(se, ['item_sku', 'descripcion_item', 'solicitante_nombre', 'CAST(orden_trabajo_id AS TEXT)', 'observaciones'])
            if search_where:
                w.append(search_where)
                p += search_params
        ws=(' WHERE '+' AND '.join(w)) if w else ''
        rows_mov=c.execute(f'SELECT rowid,item_sku,descripcion_item,fecha_consumo,solicitante_nombre,cantidad_consumida,precio_unitario,total_consumo,orden_trabajo_id,observaciones,stock_actual_en_consumo,documento_ref FROM movimientos_consumo{ws} ORDER BY COALESCE(fecha_consumo,0) DESC, rowid DESC',p).fetchall()
        items_mov=[_normalize_consumo_row(r) for r in rows_mov]

        # 2) Consumos acumulados sin detalle (excluir SKUs que ya tienen movimientos detallados)
        skus_en_mov = set(r[1] for r in rows_mov)
        wh, ph = ['COALESCE(consumos_totales_historicos,0) > 0'], []
        if se:
            search_where_hist, search_params_hist = contains_terms_where(se, ['sku', 'nombre'])
            if search_where_hist:
                wh.append(f'({search_where_hist})')
                ph += search_params_hist
        wsh = ' WHERE ' + ' AND '.join(wh)
        rows_hist = c.execute(
            f'SELECT sku,nombre,consumos_totales_historicos,stock_actual,precio_unitario_promedio,COALESCE(consumo_historico_ot,\'\') FROM items{wsh} ORDER BY consumos_totales_historicos DESC',ph
        ).fetchall()
        items_hist = [_normalize_historical_consumo_row(r) for r in rows_hist if r[0] not in skus_en_mov]

        # 3) Combinar y ordenar siempre por fecha más reciente -> más antigua
        all_items = items_mov + items_hist
        all_items.sort(
            key=lambda x: ((x.get('fecha') is not None), x.get('fecha') or '', x.get('rowid') or 0),
            reverse=True
        )
        t = len(all_items)
        o = (pg - 1) * pp2
        page_items = all_items[o:o + pp2]

        return jsonify({'items':page_items,'total':t,'page':pg,'per_page':pp2,'total_pages':max(1,-(-t//pp2))})
    finally: c.close()

@bp.route('', methods=['POST'], strict_slashes=False)
def api_cc():
    """
    Crea un nuevo consumo (salida) de producto
    """
    c=get_db()
    try:
        _ensure_consumos_schema(c)
        d=request.json; fs=date_to_excel(d.get('fecha',datetime.now().strftime('%Y-%m-%d'))); q=float(d.get('cantidad',0)); sk=(d.get('sku') or '').strip()
        if not sk:
            return jsonify({'ok':False,'msg':'SKU requerido'}),400
        if q <= 0:
            return jsonify({'ok':False,'msg':'Cantidad inválida'}),400

        documento_ref = (d.get('documento_ref') or '').strip() or _generate_documento_ref()
        _begin_write_tx(c)

        item=c.execute('SELECT precio_unitario_promedio,nombre FROM items WHERE sku=?',[sk]).fetchone()
        if not item:
            c.rollback()
            return jsonify({'ok':False,'msg':'No encontrado'}),404

        pr=parse_price(item[0])

        if not _deduct_stock_atomic(c, sk, q):
            c.rollback()
            stock_row = c.execute('SELECT COALESCE(stock_actual,0) FROM items WHERE sku=?', [sk]).fetchone()
            st = (stock_row[0] if stock_row else 0)
            return jsonify({'ok':False,'msg':f'Stock insuficiente ({st})'}),400

        ns_row = c.execute('SELECT COALESCE(stock_actual,0) FROM items WHERE sku=?', [sk]).fetchone()
        ns = ns_row[0] if ns_row else 0

        c.execute('INSERT INTO movimientos_consumo (item_sku,descripcion_item,fecha_consumo,solicitante_nombre,cantidad_consumida,precio_unitario,total_consumo,orden_trabajo_id,observaciones,stock_actual_en_consumo,documento_ref) VALUES (?,?,?,?,?,?,?,?,?,?,?)',[sk,item[1] or '',fs,d.get('solicitante',''),q,pr,round(q*pr,2),d.get('ot_id',''),d.get('observaciones',''),ns,documento_ref])
        c.commit()
        return jsonify({'ok':True,'msg':f'Consumo OK. Stock: {ns}'})
    except Exception as e:
        c.rollback()
        return jsonify({'ok':False,'msg':str(e)}),400
    finally: c.close()

@bp.route('/batch',methods=['POST'])
def api_cb():
    """
    Crea múltiples consumos en una sola transacción (batch)
    """
    c=get_db()
    try:
        _ensure_consumos_schema(c)
        d=request.json; fs=date_to_excel(d.get('fecha',datetime.now().strftime('%Y-%m-%d')))
        sol=d.get('solicitante',''); ot=d.get('ot_id',''); obs=d.get('observaciones','')
        documento_ref = (d.get('documento_ref') or '').strip() or _generate_documento_ref()
        items=d.get('items',[]); reg=0; err=[]
        if not items: return jsonify({'ok':False,'msg':'Sin productos'}),400

        _begin_write_tx(c)

        for it in items:
            sk=it.get('sku','').strip(); q=float(it.get('cantidad',0))
            if not sk or q<=0:
                err.append(f'{sk}: inválido')
                continue

            item=c.execute('SELECT precio_unitario_promedio,nombre FROM items WHERE sku=?',[sk]).fetchone()
            if not item:
                err.append(f'{sk}: no encontrado')
                continue

            pr=parse_price(item[0])
            if not _deduct_stock_atomic(c, sk, q):
                st_row = c.execute('SELECT COALESCE(stock_actual,0) FROM items WHERE sku=?', [sk]).fetchone()
                st = st_row[0] if st_row else 0
                err.append(f'{sk}: stock insuficiente ({st})')
                continue

            ns_row = c.execute('SELECT COALESCE(stock_actual,0) FROM items WHERE sku=?', [sk]).fetchone()
            ns = ns_row[0] if ns_row else 0

            c.execute('INSERT INTO movimientos_consumo (item_sku,descripcion_item,fecha_consumo,solicitante_nombre,cantidad_consumida,precio_unitario,total_consumo,orden_trabajo_id,observaciones,stock_actual_en_consumo,documento_ref) VALUES (?,?,?,?,?,?,?,?,?,?,?)',[sk,item[1] or '',fs,sol,q,pr,round(q*pr,2),ot,obs,ns,documento_ref])
            reg+=1

        c.commit(); msg=f'{reg} producto(s) consumido(s)'
        if err: msg+=f'. Errores: {"; ".join(err)}'
        return jsonify({'ok':reg>0,'msg':msg,'registrados':reg,'errores':err,'documento_ref':documento_ref})
    except Exception as e:
        c.rollback()
        return jsonify({'ok':False,'msg':str(e)}),400
    finally: c.close()

@bp.route('/<int:consumo_id>', methods=['PUT'])
def api_ec(consumo_id):
    """
    Edita un consumo existente (ajusta stock)
    """
    c=get_db()
    try:
        _ensure_consumos_schema(c)
        # Obtener consumo actual
        actual = c.execute('SELECT item_sku,cantidad_consumida FROM movimientos_consumo WHERE rowid=?',[consumo_id]).fetchone()
        if not actual: return jsonify({'ok':False,'msg':'Consumo no encontrado'}),404
        
        sku_ant = actual[0]
        cant_ant = actual[1] or 0
        
        d=request.json
        fs=date_to_excel(d.get('fecha',datetime.now().strftime('%Y-%m-%d')))
        sku_nuevo = d.get('sku',sku_ant)
        cant_nueva = float(d.get('cantidad',cant_ant))
        
        # Si cambió el SKU, revertir stock del anterior y descontar del nuevo
        if sku_ant != sku_nuevo:
            # Devolver stock al item anterior
            c.execute('UPDATE items SET stock_actual = stock_actual + ? WHERE sku=?',[cant_ant,sku_ant])
            
            # Verificar stock del nuevo item
            item_nuevo = c.execute('SELECT stock_actual,precio_unitario_promedio,nombre FROM items WHERE sku=?',[sku_nuevo]).fetchone()
            if not item_nuevo: return jsonify({'ok':False,'msg':'SKU no encontrado'}),404
            st_nuevo = item_nuevo[0] or 0
            if cant_nueva > st_nuevo: return jsonify({'ok':False,'msg':f'Stock insuficiente ({st_nuevo})'}),400
            
            # Descontar del nuevo item
            nuevo_stock = st_nuevo - cant_nueva
            pr = parse_price(item_nuevo[1])
            c.execute('UPDATE items SET stock_actual=? WHERE sku=?',[nuevo_stock,sku_nuevo])
            
            # Actualizar consumo
            c.execute('UPDATE movimientos_consumo SET item_sku=?,descripcion_item=?,fecha_consumo=?,solicitante_nombre=?,cantidad_consumida=?,precio_unitario=?,total_consumo=?,orden_trabajo_id=?,observaciones=?,stock_actual_en_consumo=? WHERE rowid=?',[sku_nuevo,item_nuevo[2],fs,d.get('solicitante',''),cant_nueva,pr,round(cant_nueva*pr,2),d.get('ot_id',''),d.get('observaciones',''),nuevo_stock,consumo_id])
        else:
            # Mismo SKU, solo ajustar diferencia de cantidad
            dif = cant_nueva - cant_ant
            item = c.execute('SELECT stock_actual,precio_unitario_promedio,nombre FROM items WHERE sku=?',[sku_ant]).fetchone()
            if not item: return jsonify({'ok':False,'msg':'Item no encontrado'}),404
            
            st = item[0] or 0
            # Si aumenta el consumo, verificar stock
            if dif > 0 and dif > st:
                return jsonify({'ok':False,'msg':f'Stock insuficiente para incremento ({st})'}),400
            
            nuevo_stock = st - dif
            pr = parse_price(item[1])
            c.execute('UPDATE items SET stock_actual=? WHERE sku=?',[nuevo_stock,sku_ant])
            c.execute('UPDATE movimientos_consumo SET fecha_consumo=?,solicitante_nombre=?,cantidad_consumida=?,precio_unitario=?,total_consumo=?,orden_trabajo_id=?,observaciones=?,stock_actual_en_consumo=? WHERE rowid=?',[fs,d.get('solicitante',''),cant_nueva,pr,round(cant_nueva*pr,2),d.get('ot_id',''),d.get('observaciones',''),nuevo_stock,consumo_id])
        
        c.commit()
        return jsonify({'ok':True,'msg':'Consumo actualizado'})
    except Exception as e: return jsonify({'ok':False,'msg':str(e)}),400
    finally: c.close()


@bp.route('/historico/<string:sku>', methods=['PUT'])
def api_eh(sku):
    """
    Actualiza metadatos del consumo acumulado sin convertirlo a movimiento.
    """
    c = get_db()
    try:
        _ensure_consumos_schema(c)
        item = c.execute(
            'SELECT consumos_totales_historicos,COALESCE(consumo_historico_ot,\'\') FROM items WHERE sku=?',
            [sku]
        ).fetchone()
        if not item:
            return jsonify({'ok': False, 'msg': 'SKU no encontrado'}), 404

        cantidad_historica = float(item[0] or 0)
        if cantidad_historica <= 0:
            return jsonify({'ok': False, 'msg': 'No existe consumo acumulado para este SKU'}), 404

        d = request.json or {}
        ot_id = (d.get('ot_id') or '').strip()
        if not ot_id:
            ot_id = (d.get('solicitante') or '').strip()
        c.execute(
            'UPDATE items SET consumo_historico_ot=? WHERE sku=?',
            [ot_id, sku]
        )
        c.commit()
        return jsonify({'ok': True, 'msg': 'OT del consumo histórico actualizada'} )
    except Exception as e:
        c.rollback()
        return jsonify({'ok': False, 'msg': str(e)}), 400
    finally:
        c.close()

@bp.route('/<int:consumo_id>', methods=['DELETE'])
def api_dc(consumo_id):
    """
    Elimina un consumo y revierte el stock
    """
    c=get_db()
    try:
        _ensure_consumos_schema(c)
        # Obtener datos del consumo
        consumo = c.execute('SELECT item_sku,cantidad_consumida FROM movimientos_consumo WHERE rowid=?',[consumo_id]).fetchone()
        if not consumo: return jsonify({'ok':False,'msg':'Consumo no encontrado'}),404
        
        sku = consumo[0]
        cant = consumo[1] or 0
        
        # Devolver stock
        c.execute('UPDATE items SET stock_actual = stock_actual + ? WHERE sku=?',[cant,sku])
        
        # Eliminar consumo
        c.execute('DELETE FROM movimientos_consumo WHERE rowid=?',[consumo_id])
        
        c.commit()
        return jsonify({'ok':True,'msg':f'Consumo eliminado. Stock de {sku} restaurado'})
    except Exception as e: return jsonify({'ok':False,'msg':str(e)}),400
    finally: c.close()


@bp.route('/historico/<string:sku>', methods=['DELETE'])
def api_dh(sku):
    """
    Elimina un consumo acumulado y restaura el stock asociado.
    """
    c = get_db()
    try:
        _ensure_consumos_schema(c)
        item = c.execute(
            'SELECT stock_actual,consumos_totales_historicos FROM items WHERE sku=?',
            [sku]
        ).fetchone()
        if not item:
            return jsonify({'ok': False, 'msg': 'SKU no encontrado'}), 404

        stock_actual = item[0] or 0
        cantidad = float(item[1] or 0)
        if cantidad <= 0:
            return jsonify({'ok': False, 'msg': 'No existe consumo acumulado para este SKU'}), 404

        c.execute(
            'UPDATE items SET stock_actual=?, consumos_totales_historicos=0, consumo_historico_ot=\'\' WHERE sku=?',
            [stock_actual + cantidad, sku]
        )
        c.commit()
        return jsonify({'ok': True, 'msg': f'Consumo eliminado. Stock de {sku} restaurado'})
    except Exception as e:
        c.rollback()
        return jsonify({'ok': False, 'msg': str(e)}), 400
    finally:
        c.close()


@bp.route('/documento', methods=['PUT'])
def api_edoc():
    """
    Edita un documento completo de consumo en una sola transacción.
    """
    c = get_db()
    try:
        _ensure_consumos_schema(c)
        d = request.json or {}
        items = d.get('items', [])
        if not items:
            return jsonify({'ok': False, 'msg': 'Documento sin insumos'}), 400

        fecha = d.get('fecha', datetime.now().strftime('%Y-%m-%d'))
        fecha_excel = date_to_excel(fecha)
        solicitante = (d.get('solicitante') or '').strip()
        ot_id = (d.get('ot_id') or '').strip()
        observaciones = (d.get('observaciones') or '').strip()
        documento_ref = (d.get('documento_ref') or '').strip() or _generate_documento_ref()

        normalized_items = []
        rowids = []
        seen_existing = set()

        for raw in items:
            sku = (raw.get('sku') or '').strip()
            cantidad = float(raw.get('cantidad', 0) or 0)
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
            normalized_items.append({'rowid': rowid, 'sku': sku, 'cantidad': cantidad})

        if not normalized_items:
            return jsonify({'ok': False, 'msg': 'Documento sin cantidades válidas'}), 400

        existing_rows = []
        existing_map = {}
        if rowids:
            marks = ','.join(['?'] * len(rowids))
            existing_rows = c.execute(
                f'SELECT rowid,item_sku,cantidad_consumida FROM movimientos_consumo WHERE rowid IN ({marks})',
                rowids
            ).fetchall()
            existing_map = {int(row[0]): row for row in existing_rows}
            if len(existing_map) != len(set(rowids)):
                return jsonify({'ok': False, 'msg': 'Algunas filas del documento ya no existen'}), 404

        for row in existing_rows:
            c.execute('UPDATE items SET stock_actual = stock_actual + ? WHERE sku=?', [float(row[2] or 0), row[1]])

        updated_rowids = set()
        created = 0
        removed = 0

        for item in normalized_items:
            sku = item['sku']
            cantidad = item['cantidad']
            rowid = item['rowid']
            item_db = c.execute('SELECT stock_actual,precio_unitario_promedio,nombre FROM items WHERE sku=?', [sku]).fetchone()
            if not item_db:
                raise ValueError(f'SKU no encontrado: {sku}')

            stock_actual = float(item_db[0] or 0)
            if cantidad > stock_actual:
                raise ValueError(f'Stock insuficiente para {sku} ({stock_actual})')

            nuevo_stock = stock_actual - cantidad
            precio = parse_price(item_db[1])
            nombre = item_db[2] or ''
            total = round(cantidad * precio, 2)

            c.execute('UPDATE items SET stock_actual=? WHERE sku=?', [nuevo_stock, sku])

            if rowid is not None:
                c.execute(
                    'UPDATE movimientos_consumo SET item_sku=?,descripcion_item=?,fecha_consumo=?,solicitante_nombre=?,cantidad_consumida=?,precio_unitario=?,total_consumo=?,orden_trabajo_id=?,observaciones=?,stock_actual_en_consumo=?,documento_ref=? WHERE rowid=?',
                    [sku, nombre, fecha_excel, solicitante, cantidad, precio, total, ot_id, observaciones, nuevo_stock, documento_ref, rowid]
                )
                updated_rowids.add(rowid)
            else:
                c.execute(
                    'INSERT INTO movimientos_consumo (item_sku,descripcion_item,fecha_consumo,solicitante_nombre,cantidad_consumida,precio_unitario,total_consumo,orden_trabajo_id,observaciones,stock_actual_en_consumo,documento_ref) VALUES (?,?,?,?,?,?,?,?,?,?,?)',
                    [sku, nombre, fecha_excel, solicitante, cantidad, precio, total, ot_id, observaciones, nuevo_stock, documento_ref]
                )
                created += 1

        for row in existing_rows:
            rowid = int(row[0])
            if rowid not in updated_rowids:
                c.execute('DELETE FROM movimientos_consumo WHERE rowid=?', [rowid])
                removed += 1

        c.commit()
        return jsonify({
            'ok': True,
            'msg': 'Documento de consumo actualizado',
            'documento_ref': documento_ref,
            'creados': created,
            'eliminados': removed,
            'actualizados': len(updated_rowids)
        })
    except Exception as e:
        c.rollback()
        return jsonify({'ok': False, 'msg': str(e)}), 400
    finally:
        c.close()


@bp.route('/documento', methods=['DELETE'])
def api_ddoc():
    """
    Elimina un documento completo de consumo y restaura el stock.
    """
    c = get_db()
    try:
        _ensure_consumos_schema(c)
        d = request.json or {}
        rowids = [int(rowid) for rowid in (d.get('rowids') or []) if rowid not in (None, '')]
        if not rowids:
            return jsonify({'ok': False, 'msg': 'Documento sin filas válidas'}), 400

        marks = ','.join(['?'] * len(rowids))
        rows = c.execute(
            f'SELECT rowid,item_sku,cantidad_consumida FROM movimientos_consumo WHERE rowid IN ({marks})',
            rowids
        ).fetchall()
        if len(rows) != len(set(rowids)):
            return jsonify({'ok': False, 'msg': 'Algunas filas del documento ya no existen'}), 404

        for row in rows:
            c.execute('UPDATE items SET stock_actual = stock_actual + ? WHERE sku=?', [float(row[2] or 0), row[1]])

        c.execute(f'DELETE FROM movimientos_consumo WHERE rowid IN ({marks})', rowids)
        c.commit()
        return jsonify({'ok': True, 'msg': f'Documento eliminado. {len(rows)} insumo(s) restaurado(s)'})
    except Exception as e:
        c.rollback()
        return jsonify({'ok': False, 'msg': str(e)}), 400
    finally:
        c.close()
