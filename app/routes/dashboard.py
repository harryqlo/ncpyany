
from flask import Blueprint, jsonify, request, render_template_string
from app.db import get_db, parse_price
from datetime import datetime

bp = Blueprint('dashboard', __name__, url_prefix='/api/dashboard')


def _apply_date_filter(query_base, params, from_date, to_date, date_col):
    """Append WHERE clauses for range filtering and update params list."""
    if from_date:
        query_base += f" AND {date_col}>=?"
        params.append(from_date)
    if to_date:
        query_base += f" AND {date_col}<=?"
        params.append(to_date)
    return query_base


def _get_accumulated_consumos(c, category=None):
    sql = (
        "SELECT sku,nombre,COALESCE(consumos_totales_historicos,0) AS cantidad,categoria_nombre "
        "FROM items WHERE sku IS NOT NULL AND sku<>'' AND COALESCE(consumos_totales_historicos,0) > 0"
    )
    params = []
    if category:
        sql += ' AND categoria_nombre=?'
        params.append(category)
    sql += ' ORDER BY cantidad DESC'
    return c.execute(sql, params).fetchall()


@bp.route('', strict_slashes=False)
def api_dashboard():
    """
    Obtiene el resumen general del sistema (dashboard principal).

    Además de los valores básicos, el endpoint acepta filtros opcionales
    mediante query params:

        /api/dashboard?from=2025-01-01&to=2025-03-31&category=Consumibles

    Se devuelve un objeto JSON con los mismos campos anteriores y, en
    adición:

        "series_ingresos": [{"period":"YYYY-MM","total":number},...]
        "series_consumos": [{"period":"YYYY-MM","total":number},...]

    Los periodos se agrupan por mes y respetan los filtros de fecha/categoría.
    """
    args = request.args
    from_date = args.get('from')
    to_date = args.get('to')
    category = args.get('category')

    c = get_db()
    try:
        # básicos de inventario
        ti = c.execute("SELECT COUNT(*) FROM items WHERE sku IS NOT NULL AND sku<>''").fetchone()[0]
        cs = c.execute("SELECT COUNT(*) FROM items WHERE sku IS NOT NULL AND sku<>'' AND stock_actual>0").fetchone()[0]
        ss = c.execute("SELECT COUNT(*) FROM items WHERE (sku IS NULL OR sku='') OR stock_actual<=0 OR stock_actual IS NULL").fetchone()[0]
        rows = c.execute(
            "SELECT stock_actual,precio_unitario_promedio FROM items "
            "WHERE sku IS NOT NULL AND sku<>'' "
            "AND stock_actual IS NOT NULL "
            "AND precio_unitario_promedio IS NOT NULL AND precio_unitario_promedio>0"
        ).fetchall()
        vt = sum((r[0] or 0) * parse_price(r[1]) for r in rows)
        # Items críticos: stock actual menor o igual al mínimo definido (o <=5 si no tiene mínimo definido)
        cr = c.execute(
            'SELECT COUNT(*) FROM items '
            'WHERE stock_actual>0 '
            'AND (stock_actual <= COALESCE(NULLIF(stock_minimo,0),5))'
        ).fetchone()[0]
        invalid = c.execute("SELECT COUNT(*) FROM items WHERE sku IS NULL OR sku='' ").fetchone()[0]

        # distribucion por categoría (aplica filtro de categoría si existe)
        cats_sql = 'SELECT categoria_nombre,COUNT(*) FROM items WHERE categoria_nombre IS NOT NULL'
        cats_params = []
        if category:
            cats_sql += ' AND categoria_nombre=?'
            cats_params.append(category)
        cats_sql += ' GROUP BY categoria_nombre ORDER BY COUNT(*) DESC'
        cats = [
            {'nombre': r[0], 'cantidad': r[1]}
            for r in c.execute(cats_sql, cats_params).fetchall()
        ]

        accumulated_consumos = _get_accumulated_consumos(c, category)

        # top consumos, con filtros de fecha y categoría
        top_sql = 'SELECT item_sku,descripcion_item,SUM(cantidad_consumida) FROM movimientos_consumo WHERE 1=1'
        top_params = []
        if category:
            top_sql += ' AND categoria_item=?'
            top_params.append(category)
        if from_date or to_date:
            top_sql = _apply_date_filter(top_sql, top_params, from_date, to_date, 'fecha_consumo')
        top_sql += ' GROUP BY item_sku ORDER BY SUM(cantidad_consumida) DESC LIMIT 10'
        top_map = {}
        for r in c.execute(top_sql, top_params).fetchall():
            top_map[r[0]] = {
                'sku': r[0],
                'nombre': r[1],
                'total': r[2] or 0,
            }
        if not from_date and not to_date:
            for r in accumulated_consumos:
                sku = r[0]
                if sku in top_map:
                    top_map[sku]['total'] += r[2] or 0
                    if not top_map[sku]['nombre']:
                        top_map[sku]['nombre'] = r[1]
                else:
                    top_map[sku] = {'sku': sku, 'nombre': r[1], 'total': r[2] or 0}
        top = sorted(top_map.values(), key=lambda row: row['total'], reverse=True)[:10]

        # Items críticos: stock <= mínimo (o <=5 si no tiene mínimo), ordenados por porcentaje usado del mínimo
        crd = [
            {'sku': r[0], 'nombre': r[1], 'stock': r[2], 'unidad': r[3], 'categoria': r[4], 'precio': parse_price(r[5]), 'stock_min': r[6] or 0, 'stock_max': r[7] or 0}
            for r in c.execute(
                'SELECT sku,nombre,stock_actual,unidad_medida_nombre,categoria_nombre,precio_unitario_promedio,stock_minimo,stock_maximo '
                'FROM items '
                'WHERE stock_actual>0 '
                'AND stock_actual <= COALESCE(NULLIF(stock_minimo,0),5) '
                'ORDER BY (stock_actual * 1.0 / COALESCE(NULLIF(stock_minimo,0),5)) ASC '
                'LIMIT 20'
            ).fetchall()
        ]

        # series mensuales para ingresos/consumos
        def _series(table, date_col):
            # use appropriate quantity field per table
            qty_col = 'cantidad' if table == 'movimientos_ingreso' else 'cantidad_consumida'
            sql = f"SELECT substr({date_col},1,7) as period, SUM({qty_col}) FROM {table} WHERE 1=1"
            params = []
            if from_date or to_date:
                sql = _apply_date_filter(sql, params, from_date, to_date, date_col)
            if category and table == 'movimientos_consumo':
                sql += ' AND categoria_item=?'
                params.append(category)
            sql += ' GROUP BY period ORDER BY period'
            return [
                {'period': r[0], 'total': r[1] or 0}
                for r in c.execute(sql, params).fetchall()
            ]

        series_ingresos = _series('movimientos_ingreso', 'fecha_orden')
        series_consumos = _series('movimientos_consumo', 'fecha_consumo')
        if not from_date and not to_date:
            total_acumulado = sum((r[2] or 0) for r in accumulated_consumos)
            if total_acumulado > 0:
                series_consumos.append({'period': 'Acumulado', 'total': total_acumulado})

        result = {
            'total_items': ti,
            'items_con_stock': cs,
            'items_sin_stock': ss,
            'valor_total': round(vt),
            'criticos': cr,
            'invalid_items': invalid,
            'total_ingresos': c.execute('SELECT COUNT(*) FROM movimientos_ingreso').fetchone()[0],
            'total_consumos': c.execute('SELECT COUNT(*) FROM movimientos_consumo').fetchone()[0] + (len(accumulated_consumos) if not from_date and not to_date else 0),
            'total_consumos_acumulados': sum((r[2] or 0) for r in accumulated_consumos) if not from_date and not to_date else 0,
            'total_ots': c.execute('SELECT COUNT(*) FROM ordenes_trabajo').fetchone()[0],
            'categorias': cats,
            'top_consumo': top,
            'criticos_detail': crd,
            'series_ingresos': series_ingresos,
            'series_consumos': series_consumos,
        }
        return jsonify(result)
    finally:
        c.close()


@bp.route('/detalle-valor', strict_slashes=False)
def api_valor_detalle():
    """
    Devuelve el desglose del valor del inventario por item.

    Esto es útil para diagnosticar discrepancias en la suma que
    se muestra en el dashboard. Cada fila incluye SKU, nombre,
    stock actual, precio promedio y el valor calculado (stock * precio).
    También se retorna el total redondeado.

    NOTA: Solo se incluyen items con información completa:
    - SKU válido (no nulo, no vacío)
    - Stock actual definido (no nulo)
    - Precio unitario válido (no nulo y > 0)
    """
    c = get_db()
    try:
        rows = c.execute(
            "SELECT sku,nombre,stock_actual,precio_unitario_promedio "
            "FROM items WHERE sku IS NOT NULL AND sku<>'' "
            "AND stock_actual IS NOT NULL "
            "AND precio_unitario_promedio IS NOT NULL AND precio_unitario_promedio>0"
        ).fetchall()
        detail = []
        total = 0
        for r in rows:
            stock = r['stock_actual']
            precio = parse_price(r['precio_unitario_promedio'])
            valor = stock * precio
            total += valor
            detail.append({
                'sku': r['sku'],
                'nombre': r['nombre'],
                'stock': stock,
                'precio': precio,
                'valor': valor,
            })
        return jsonify({'detail': detail, 'total': round(total)})
    finally:
        c.close()


@bp.route('/detalle-valor-html', strict_slashes=False)
def api_valor_detalle_html():
    """
    Renderiza una página HTML visual del desglose del valor del inventario.
    Solo incluye items con información completa (SKU, stock, precio válido).
    """
    c = get_db()
    try:
        rows = c.execute(
            "SELECT sku,nombre,stock_actual,precio_unitario_promedio "
            "FROM items WHERE sku IS NOT NULL AND sku<>'' "
            "AND stock_actual IS NOT NULL "
            "AND precio_unitario_promedio IS NOT NULL AND precio_unitario_promedio>0"
        ).fetchall()
        detail = []
        total = 0
        for r in rows:
            stock = r['stock_actual']
            precio = parse_price(r['precio_unitario_promedio'])
            valor = stock * precio
            total += valor
            detail.append({
                'sku': r['sku'],
                'nombre': r['nombre'],
                'stock': stock,
                'precio': precio,
                'valor': valor,
            })
        
        html = f"""
        <!DOCTYPE html>
        <html lang="es">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Detalle Valor Inventario</title>
            <style>
                * {{ margin: 0; padding: 0; box-sizing: border-box; }}
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    min-height: 100vh;
                    padding: 20px;
                }}
                .container {{
                    max-width: 1200px;
                    margin: 0 auto;
                    background: white;
                    border-radius: 10px;
                    box-shadow: 0 10px 40px rgba(0,0,0,0.2);
                    overflow: hidden;
                }}
                .header {{
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    padding: 30px;
                    text-align: center;
                }}
                .header h1 {{
                    font-size: 28px;
                    margin-bottom: 10px;
                }}
                .header p {{
                    opacity: 0.9;
                    font-size: 14px;
                }}
                .content {{
                    padding: 30px;
                }}
                .table-wrapper {{
                    overflow-x: auto;
                    margin-bottom: 20px;
                }}
                table {{
                    width: 100%;
                    border-collapse: collapse;
                    font-size: 13px;
                }}
                th {{
                    background: #f5f7fa;
                    padding: 12px;
                    text-align: left;
                    font-weight: 600;
                    color: #333;
                    border-bottom: 2px solid #e0e6ed;
                }}
                td {{
                    padding: 12px;
                    border-bottom: 1px solid #e0e6ed;
                }}
                tr:hover {{
                    background: #f9fafb;
                }}
                tr:last-of-type td {{
                    border-bottom: 2px solid #667eea;
                    font-weight: 600;
                    background: #f5f7fa;
                }}
                .sku {{ color: #667eea; font-weight: 600; }}
                .num {{ text-align: right; font-family: 'Courier New', monospace; }}
                .total-row {{
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    font-size: 16px;
                }}
                .total-row td {{
                    padding: 15px 12px;
                    border: none;
                }}
                .stat {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin-bottom: 30px; }}
                .stat-card {{
                    background: #f5f7fa;
                    padding: 20px;
                    border-radius: 8px;
                    text-align: center;
                    border-left: 4px solid #667eea;
                }}
                .stat-card .label {{ font-size: 12px; color: #666; text-transform: uppercase; margin-bottom: 8px; }}
                .stat-card .value {{ font-size: 24px; font-weight: 700; color: #333; }}
                .btn-back {{
                    display: inline-block;
                    background: #667eea;
                    color: white;
                    padding: 10px 20px;
                    border-radius: 5px;
                    text-decoration: none;
                    font-size: 13px;
                    margin-bottom: 20px;
                }}
                .btn-back:hover {{
                    background: #764ba2;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>📊 Detalle del Valor del Inventario</h1>
                    <p>Desglose de SKU, stock, precio y valor total calculado</p>
                </div>
                <div class="content">
                    <a href="/" class="btn-back">← Volver al Dashboard</a>
                    
                    <div class="stat">
                        <div class="stat-card">
                            <div class="label">Total de Ítems</div>
                            <div class="value">{len(detail)}</div>
                        </div>
                        <div class="stat-card">
                            <div class="label">Valor Total Inventario</div>
                            <div class="value">${{round(total):,.0f}}</div>
                        </div>
                        <div class="stat-card">
                            <div class="label">Valor Promedio por Ítem</div>
                            <div class="value">${{{round(total/len(detail)) if detail else 0:,.0f}}}</div>
                        </div>
                    </div>

                    <div class="table-wrapper">
                        <table>
                            <thead>
                                <tr>
                                    <th style="width: 15%;">SKU</th>
                                    <th style="width: 40%;">Nombre del Producto</th>
                                    <th class="num" style="width: 12%;">Stock</th>
                                    <th class="num" style="width: 15%;">Precio Unit.</th>
                                    <th class="num" style="width: 18%;">Valor Total</th>
                                </tr>
                            </thead>
                            <tbody>
        """
        
        for item in detail:
            html += f"""
                                <tr>
                                    <td class="sku">{item['sku']}</td>
                                    <td>{item['nombre']}</td>
                                    <td class="num">{item['stock']:,.0f}</td>
                                    <td class="num">${{item['precio']:,.2f}}</td>
                                    <td class="num">${{item['valor']:,.2f}}</td>
                                </tr>
            """
        
        html += f"""
                                <tr class="total-row">
                                    <td colspan="4" style="text-align: right; padding-right: 12px;">TOTAL INVENTARIO:</td>
                                    <td class="num">${{{round(total):,.0f}}}</td>
                                </tr>
                            </tbody>
                        </table>
                    </div>
                    
                    <p style="text-align: center; color: #999; font-size: 12px; margin-top: 20px;">
                        Generado: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
                    </p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return render_template_string(html)
    finally:
        c.close()
