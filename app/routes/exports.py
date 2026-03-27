
import csv
import io
from flask import Blueprint, Response, request
from app.db import get_db, parse_price, excel_to_date
from app.search_utils import contains_terms_where
from openpyxl import Workbook

bp = Blueprint('exports', __name__, url_prefix='/api/export')

@bp.route('/csv')
def exp_inv():
    """
    Exporta el inventario completo en formato CSV
    """
    c=get_db()
    try:
        rows=c.execute('SELECT sku,nombre,stock_actual,unidad_medida_nombre,ubicacion_nombre,categoria_nombre,proveedor_principal_nombre,precio_unitario_promedio,valor_stock_final FROM items ORDER BY nombre').fetchall()
        o=io.StringIO(); w=csv.writer(o); w.writerow(['SKU','Nombre','Stock','Unidad','Ubicación','Categoría','Proveedor','Precio Unit.','Valor Stock'])
        for r in rows: w.writerow([r[0],r[1],r[2],r[3],r[4],r[5],r[6],parse_price(r[7]),r[8]])
        o.seek(0); return Response(o.getvalue(),mimetype='text/csv',headers={'Content-Disposition':'attachment; filename=inventario.csv'})
    finally: c.close()

@bp.route('/ingresos')
def exp_ing():
    """
    Exporta el historial de ingresos en formato CSV.
    Se admiten los mismos filtros que la API principal: search, from, to.
    """
    c=get_db()
    try:
        se=request.args.get('search','').strip(); ff=request.args.get('from',''); ft=request.args.get('to','')
        w,p=[],[]
        if se:
            search_where, search_params = contains_terms_where(
                se,
                ['item_sku', 'descripcion_item', 'proveedor_nombre', 'numero_factura', 'numero_guia_despacho']
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
        rows=c.execute(f'SELECT fecha_orden,item_sku,descripcion_item,cantidad,precio_unitario,total_ingreso,proveedor_nombre,numero_factura,numero_guia_despacho,numero_orden_compra,observaciones FROM movimientos_ingreso{ws} ORDER BY CAST(fecha_orden AS REAL) DESC',p).fetchall()
        o=io.StringIO(); w=csv.writer(o); w.writerow(['Fecha','SKU','Producto','Cantidad','Precio','Total','Proveedor','Factura','Guía','OC','Obs'])
        for r in rows: w.writerow([excel_to_date(r[0]),r[1],r[2],r[3],r[4],r[5],r[6],r[7],r[8],r[9],r[10]])
        o.seek(0); return Response(o.getvalue(),mimetype='text/csv',headers={'Content-Disposition':'attachment; filename=ingresos.csv'})
    finally: c.close()

@bp.route('/consumos')
def exp_con():
    """
    Exporta el historial de consumos en formato CSV
    """
    c=get_db()
    try:
        rows_mov=c.execute('SELECT fecha_consumo,item_sku,descripcion_item,cantidad_consumida,precio_unitario,total_consumo,solicitante_nombre,orden_trabajo_id,observaciones,stock_actual_en_consumo FROM movimientos_consumo ORDER BY rowid DESC').fetchall()
        skus_con_mov = {r[1] for r in rows_mov}
        rows_hist = c.execute('SELECT sku,nombre,consumos_totales_historicos,stock_actual,precio_unitario_promedio,COALESCE(consumo_historico_ot,\'\') FROM items WHERE COALESCE(consumos_totales_historicos,0) > 0 ORDER BY consumos_totales_historicos DESC').fetchall()
        o=io.StringIO(); w=csv.writer(o); w.writerow(['Fecha','SKU','Producto','Cantidad','Precio','Total','Solicitante','OT','Obs','Stock Post'])
        for r in rows_mov:
            w.writerow([excel_to_date(r[0]),r[1],r[2],r[3],r[4],r[5],r[6],r[7],r[8],r[9]])
        for r in rows_hist:
            if r[0] in skus_con_mov:
                continue
            precio = parse_price(r[4])
            cantidad = r[2] or 0
            w.writerow(['',r[0],r[1],cantidad,precio,round(cantidad * precio, 2),'',r[5],'',r[3]])
        o.seek(0); return Response(o.getvalue(),mimetype='text/csv',headers={'Content-Disposition':'attachment; filename=consumos.csv'})
    finally: c.close()


@bp.route('/consumos/historicos/formato')
def exp_con_hist_format():
    """
    Exporta plantilla CSV para completar OT de consumos históricos.
    """
    c = get_db()
    try:
        rows = c.execute(
            'SELECT sku,nombre,COALESCE(consumos_totales_historicos,0),COALESCE(consumo_historico_ot,\'\') '
            'FROM items '
            'WHERE COALESCE(consumos_totales_historicos,0) > 0 '
            'ORDER BY sku'
        ).fetchall()

        o = io.StringIO()
        w = csv.writer(o)
        w.writerow(['SKU', 'OT', 'Producto', 'Consumo Historico'])
        for r in rows:
            w.writerow([r[0], r[3], r[1], r[2]])

        o.seek(0)
        content = '\ufeff' + o.getvalue()
        return Response(
            content,
            mimetype='text/csv',
            headers={'Content-Disposition': 'attachment; filename=formato_ot_consumos_historicos.csv'}
        )
    finally:
        c.close()


@bp.route('/consumos/historicos/formato.xlsx')
def exp_con_hist_format_xlsx():
    """
    Exporta plantilla Excel para completar OT de consumos históricos.
    """
    c = get_db()
    try:
        rows = c.execute(
            'SELECT sku,nombre,COALESCE(consumos_totales_historicos,0),COALESCE(consumo_historico_ot,\'\') '
            'FROM items '
            'WHERE COALESCE(consumos_totales_historicos,0) > 0 '
            'ORDER BY sku'
        ).fetchall()

        wb = Workbook()
        ws = wb.active
        ws.title = 'OT Historicos'
        ws.append(['SKU', 'OT', 'Producto', 'Consumo Historico'])

        for r in rows:
            ws.append([r[0], r[3], r[1], r[2]])

        output = io.BytesIO()
        wb.save(output)
        output.seek(0)

        return Response(
            output.getvalue(),
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            headers={'Content-Disposition': 'attachment; filename=formato_ot_consumos_historicos.xlsx'}
        )
    finally:
        c.close()
