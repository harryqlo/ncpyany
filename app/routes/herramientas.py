"""
Rutas API para gestión de herramientas del pañol
Incluye: CRUD maestro, préstamos (checkout/checkin), mantenimiento
Refactorizado para usar service layer y mantener código limpio y profesional
"""
from flask import Blueprint, jsonify, request
from datetime import datetime, timedelta
from app.db import get_db
from app.search_utils import contains_terms_where
from app.services import PaniolService
from logger_config import logger

bp = Blueprint('herramientas', __name__, url_prefix='/api/herramientas')


# =========================================================================
# CRUD - HERRAMIENTAS
# =========================================================================

@bp.route('/suggest-sku', strict_slashes=False)
def api_suggest_sku():
    """Sugiere el próximo SKU disponible (tipo NC-001, NC-002, etc)"""
    from config import HERRAMIENTAS_PREFIX_DEFAULT, HERRAMIENTAS_SKU_SEPARATOR
    
    c = get_db('paniol')  # Usar BD de pañol
    try:
        prefix = request.args.get('prefix', HERRAMIENTAS_PREFIX_DEFAULT).strip().upper()
        if not prefix:
            return jsonify({'ok': False, 'msg': 'Prefijo requerido'}), 400
        
        rows = c.execute(
            'SELECT sku FROM herramientas WHERE sku LIKE ? ORDER BY sku DESC LIMIT 1',
            [f"{prefix}{HERRAMIENTAS_SKU_SEPARATOR}%"]
        ).fetchall()
        
        if not rows:
            suggested = f"{prefix}{HERRAMIENTAS_SKU_SEPARATOR}001"
        else:
            try:
                last_num = int(rows[0][0].split(HERRAMIENTAS_SKU_SEPARATOR)[-1])
                suggested = f"{prefix}{HERRAMIENTAS_SKU_SEPARATOR}{last_num + 1:03d}"
            except (ValueError, IndexError):
                suggested = f"{prefix}{HERRAMIENTAS_SKU_SEPARATOR}001"
        
        return jsonify({
            'ok': True, 'sku': suggested, 'prefix': prefix, 'separator': HERRAMIENTAS_SKU_SEPARATOR
        })
    except Exception as e:
        logger.error(f"Error sugiriendo SKU: {e}")
        return jsonify({'ok': False, 'msg': str(e)}), 500
    finally:
        c.close()


@bp.route('', strict_slashes=False)
def api_herramientas():
    """Lista herramientas con filtros y paginación"""
    pg = int(request.args.get('page', 1))
    pp = int(request.args.get('per_page', 50))
    search = request.args.get('search', '').strip()
    condicion = request.args.get('condicion', '').strip()
    categoria = request.args.get('categoria', '').strip()
    ubicacion = request.args.get('ubicacion', '').strip()
    calibracion_vencida = request.args.get('calibracion_vencida', '') == '1'
    disponible = request.args.get('disponible', '') == '1'
    sort_field = request.args.get('sort', 'nombre')
    sort_dir = request.args.get('dir', 'asc')
    
    result = PaniolService.obtener_herramientas(
        pg=pg, pp=pp, search=search, condicion=condicion, categoria=categoria,
        ubicacion=ubicacion, calibracion_vencida=calibracion_vencida,
        disponible=disponible, sort_field=sort_field, sort_dir=sort_dir
    )
    
    return jsonify(result)


@bp.route('', methods=['POST'], strict_slashes=False)
def api_crear_herramienta():
    """Crea nueva herramienta"""
    result = PaniolService.crear_herramienta(request.json)
    status = 400 if not result.get('ok') else 200
    return jsonify(result), status


@bp.route('/<int:herramienta_id>', methods=['PUT'], strict_slashes=False)
def api_actualizar_herramienta(herramienta_id):
    """Actualiza herramienta existente"""
    result = PaniolService.actualizar_herramienta(herramienta_id, request.json)
    status = 400 if not result.get('ok') else 200
    return jsonify(result), status


@bp.route('/<int:herramienta_id>', methods=['DELETE'], strict_slashes=False)
def api_eliminar_herramienta(herramienta_id):
    """Elimina herramienta"""
    result = PaniolService.eliminar_herramienta(herramienta_id)
    status = 400 if not result.get('ok') else 200
    return jsonify(result), status


@bp.route('/search', strict_slashes=False)
def api_buscar_herramientas():
    """Búsqueda rápida de herramientas (autocomplete)"""
    c = get_db()
    try:
        q = request.args.get('q', '').strip()
        if len(q) < 1:
            return jsonify([])
        
        solo_disponibles = request.args.get('solo_disponibles', '1') == '1'
        solo_operativas = request.args.get('solo_operativas', '1') == '1'
        
        where_clauses = []
        params = []
        search_where, search_params = contains_terms_where(q, ['sku', 'nombre', 'modelo'])
        if search_where:
            where_clauses.append(search_where)
            params += search_params
        
        if solo_disponibles:
            where_clauses.append("cantidad_disponible > 0")
        if solo_operativas:
            where_clauses.append("condicion = 'operativa'")
        
        where_sql = ' WHERE ' + ' AND '.join(where_clauses)
        
        rows = c.execute(f'''
            SELECT id, sku, nombre, modelo, condicion, cantidad_total, cantidad_disponible, ubicacion_nombre
            FROM herramientas {where_sql}
            ORDER BY nombre LIMIT 20
        ''', params).fetchall()
        
        herramientas = [{
            'id': r[0], 'sku': r[1], 'nombre': r[2], 'modelo': r[3],
            'condicion': r[4], 'cantidad_total': r[5] or 1,
            'cantidad_disponible': r[6] or 1, 'ubicacion': r[7]
        } for r in rows]
        
        return jsonify({'herramientas': herramientas})
        
    except Exception as e:
        logger.error(f"Error buscando herramientas: {e}")
        return jsonify([]), 500
    finally:
        c.close()


@bp.route('/<int:herramienta_id>', strict_slashes=False)
def api_obtener_herramienta(herramienta_id):
    """Obtiene detalles completos de una herramienta"""
    c = get_db()
    try:
        h = c.execute('''
            SELECT id, sku, nombre, categoria_nombre, subcategoria_nombre,
                   numero_serie, modelo, fabricante, ubicacion_nombre, condicion,
                   fecha_adquisicion, precio_unitario, requiere_calibracion,
                   frecuencia_calibracion_dias, ultima_calibracion, certificado_calibracion,
                   observaciones, cantidad_total, cantidad_disponible, fecha_creacion
            FROM herramientas WHERE id = ?
        ''', [herramienta_id]).fetchone()
        
        if not h:
            return jsonify({'ok': False, 'msg': 'Herramienta no encontrada'}), 404
        
        stats = c.execute('''
            SELECT 
                COUNT(*) as total_prestamos,
                COUNT(CASE WHEN fecha_retorno IS NULL THEN 1 END) as activos,
                COUNT(CASE WHEN fecha_retorno IS NOT NULL THEN 1 END) as completados
            FROM herramientas_movimientos WHERE herramienta_id = ?
        ''', [herramienta_id]).fetchone()
        
        return jsonify({
            'ok': True,
            'herramienta': {
                'id': h[0], 'sku': h[1], 'nombre': h[2], 'categoria': h[3],
                'subcategoria': h[4], 'numero_serie': h[5], 'modelo': h[6],
                'fabricante': h[7], 'ubicacion': h[8], 'condicion': h[9],
                'fecha_adquisicion': h[10], 'precio_unitario': h[11] or 0,
                'requiere_calibracion': bool(h[12]), 'frecuencia_calibracion_dias': h[13],
                'ultima_calibracion': h[14], 'certificado_calibracion': h[15],
                'observaciones': h[16], 'cantidad_total': h[17] or 1,
                'cantidad_disponible': h[18] or 1, 'fecha_creacion': h[19],
                'stats': {
                    'total_prestamos': stats[0],
                    'prestamos_activos': stats[1],
                    'prestamos_completados': stats[2]
                }
            }
        })
        
    except Exception as e:
        logger.error(f"Error obteniendo herramienta: {e}")
        return jsonify({'ok': False, 'msg': str(e)}), 500
    finally:
        c.close()


# =========================================================================
# OPERACIONES - CHECKOUT/CHECKIN
# =========================================================================

@bp.route('/checkout', methods=['POST'], strict_slashes=False)
def api_checkout():
    """Registra préstamo batch de herramientas"""
    result = PaniolService.checkout_herramientas(request.json)
    status = 400 if not result.get('ok') else 200
    return jsonify(result), status


@bp.route('/checkin', methods=['POST'], strict_slashes=False)
def api_checkin():
    """Registra devolución de herramienta"""
    try:
        data = request.json
        movimiento_id = data.get('movimiento_id')
        
        if not movimiento_id:
            # Si es single, convertir a formato esperado
            if not data.get('devoluciones'):
                return jsonify({'ok': False, 'msg': 'Datos inválidos'}), 400
            devoluciones = data.get('devoluciones', [])
        else:
            # Formato single checkin
            devoluciones = [{
                'movimiento_id': movimiento_id,
                'estado_retorno': data.get('estado_devolucion', data.get('estado_retorno', 'operativa')),
                'observaciones_retorno': data.get('observaciones_devolucion', data.get('observaciones_retorno', '')),
                'cantidad_devuelta': data.get('cantidad_devuelta')
            }]
        
        movimientos_ok = []
        for item in devoluciones:
            result = PaniolService.checkin_herramienta(
                item.get('movimiento_id'),
                item.get('estado_retorno', 'operativa'),
                item.get('observaciones_retorno', ''),
                item.get('cantidad_devuelta')
            )
            if not result.get('ok'):
                return jsonify(result), 400
            movimientos_ok.append(item.get('movimiento_id'))
        
        return jsonify({
            'ok': True,
            'msg': f'{len(movimientos_ok)} herramienta(s) devuelta(s) correctamente'
        })
        
    except Exception as e:
        logger.error(f"Error en checkin: {e}")
        return jsonify({'ok': False, 'msg': str(e)}), 500


@bp.route('/prestamos-activos', strict_slashes=False)
def api_prestamos_activos():
    """Lista todos los préstamos activos"""
    result = PaniolService.obtener_prestamos_activos()
    return jsonify(result)


@bp.route('/prestamos-por-usuario', strict_slashes=False)
def api_prestamos_por_usuario():
    """Agrupa préstamos activos por usuario/empleado"""
    result = PaniolService.obtener_prestamos_por_usuario(
        search=request.args.get('search', '').strip()
    )
    status = 400 if not result.get('ok', True) else 200
    return jsonify(result), status


@bp.route('/historial-movimientos', strict_slashes=False)
def api_historial_movimientos():
    """Historial completo de movimientos con filtros"""
    c = get_db()
    try:
        pg = int(request.args.get('page', 1))
        pp = int(request.args.get('per_page', 50))
        
        fecha_desde = request.args.get('fecha_desde', '').strip()
        fecha_hasta = request.args.get('fecha_hasta', '').strip()
        empleado_id = request.args.get('empleado_id', '').strip()
        herramienta_id = request.args.get('herramienta_id', '').strip()
        solo_activos = request.args.get('solo_activos', '') == '1'
        
        where_clauses = []
        params = []
        
        if fecha_desde:
            where_clauses.append("m.fecha_salida >= ?")
            params.append(fecha_desde)
        if fecha_hasta:
            where_clauses.append("m.fecha_salida <= ?")
            params.append(fecha_hasta)
        if empleado_id:
            where_clauses.append("m.empleado_id = ?")
            params.append(empleado_id)
        if herramienta_id:
            where_clauses.append("m.herramienta_id = ?")
            params.append(herramienta_id)
        if solo_activos:
            where_clauses.append("m.fecha_retorno IS NULL")
        
        where_sql = (' WHERE ' + ' AND '.join(where_clauses)) if where_clauses else ''
        
        total = c.execute(
            f'SELECT COUNT(*) FROM herramientas_movimientos m {where_sql}',
            params
        ).fetchone()[0]
        
        offset = (pg - 1) * pp
        rows = c.execute(f'''
            SELECT m.id, m.herramienta_id, m.empleado_id, m.empleado_nombre,
                   m.fecha_salida, m.fecha_retorno, m.cantidad,
                   m.estado_salida, m.estado_retorno,
                   m.observaciones_salida, m.observaciones_retorno,
                   h.sku, h.nombre as herramienta_nombre, h.modelo
            FROM herramientas_movimientos m
            INNER JOIN herramientas h ON m.herramienta_id = h.id
            {where_sql}
            ORDER BY m.fecha_salida DESC
            LIMIT ? OFFSET ?
        ''', params + [pp, offset]).fetchall()
        
        movimientos = [{
            'id': r[0], 'herramienta_id': r[1], 'empleado_id': r[2],
            'empleado_nombre': r[3], 'fecha_salida': r[4], 'fecha_retorno': r[5],
            'cantidad': r[6], 'estado_salida': r[7], 'estado_retorno': r[8],
            'observaciones_salida': r[9], 'observaciones_retorno': r[10],
            'herramienta_sku': r[11], 'herramienta_nombre': r[12],
            'herramienta_modelo': r[13]
        } for r in rows]
        
        total_pages = max(1, -(-total // pp))
        
        return jsonify({
            'movimientos': movimientos,
            'total': total,
            'page': pg,
            'per_page': pp,
            'total_pages': total_pages
        })
        
    except Exception as e:
        logger.error(f"Error obteniendo historial: {e}")
        return jsonify({'ok': False, 'msg': str(e)}), 500
    finally:
        c.close()


# =========================================================================
# ESTADÍSTICAS Y REPORTES
# =========================================================================

@bp.route('/stats', strict_slashes=False)
def api_stats_herramientas():
    """Obtiene estadísticas globales del pañol"""
    result = PaniolService.obtener_estadisticas()
    return jsonify(result)


@bp.route('/<int:herramienta_id>/kardex', strict_slashes=False)
def api_kardex_herramienta(herramienta_id):
    """Obtiene el kardex completo de una herramienta"""
    c = get_db()
    try:
        h = c.execute(
            'SELECT id, nombre, sku FROM herramientas WHERE id = ?',
            [herramienta_id]
        ).fetchone()
        
        if not h:
            return jsonify({'ok': False, 'msg': 'Herramienta no encontrada'}), 404
        
        movimientos = c.execute('''
            SELECT id, empleado_nombre, fecha_salida, fecha_retorno, cantidad,
                   estado_salida, estado_retorno, observaciones_salida,
                   observaciones_retorno
            FROM herramientas_movimientos
            WHERE herramienta_id = ?
            ORDER BY fecha_salida DESC
        ''', [herramienta_id]).fetchall()
        
        mantenimientos = c.execute('''
            SELECT id, fecha_mantenimiento, tipo, descripcion, responsable_nombre,
                   proveedor_nombre, costo, proxima_fecha, observaciones
            FROM herramientas_mantenimiento
            WHERE herramienta_id = ?
            ORDER BY fecha_mantenimiento DESC
        ''', [herramienta_id]).fetchall()
        
        kardex = []
        
        for m in movimientos:
            kardex.append({
                'tipo': 'salida' if m[3] is None else 'devolucion',
                'fecha': m[2], 'empleado': m[1], 'cantidad': m[4],
                'estado': m[6] if m[3] else m[5],
                'observaciones': m[8] if m[3] else m[7]
            })
        
        for m in mantenimientos:
            kardex.append({
                'tipo': 'mantenimiento', 'subtipo': m[2],
                'fecha': m[1], 'descripcion': m[3], 'responsable': m[4],
                'proveedor': m[5], 'costo': m[6] or 0, 'proxima_fecha': m[7],
                'observaciones': m[8]
            })
        
        kardex.sort(key=lambda x: x['fecha'], reverse=True)
        
        return jsonify({
            'ok': True,
            'herramienta': {'id': h[0], 'nombre': h[1], 'sku': h[2]},
            'kardex': kardex,
            'movimientos': kardex
        })
        
    except Exception as e:
        logger.error(f"Error obteniendo kardex: {e}")
        return jsonify({'ok': False, 'msg': str(e)}), 500
    finally:
        c.close()


# =========================================================================
# MANTENIMIENTO
# =========================================================================

@bp.route('/<int:herramienta_id>/mantenimiento', methods=['POST'], strict_slashes=False)
def api_registrar_mantenimiento(herramienta_id):
    """Registra un mantenimiento para una herramienta"""
    c = get_db()
    try:
        data = request.json
        
        h = c.execute(
            'SELECT id, nombre, condicion FROM herramientas WHERE id = ?',
            [herramienta_id]
        ).fetchone()
        
        if not h:
            return jsonify({'ok': False, 'msg': 'Herramienta no encontrada'}), 404
        
        if not all([data.get('fecha_mantenimiento'), data.get('tipo'),
                    data.get('descripcion')]):
            return jsonify({'ok': False, 'msg': 'Campos requeridos faltantes'}), 400
        
        if data['tipo'] not in ['preventivo', 'correctivo', 'calibracion']:
            return jsonify({'ok': False, 'msg': 'Tipo inválido'}), 400
        
        cursor = c.execute('''
            INSERT INTO herramientas_mantenimiento (
                herramienta_id, fecha_mantenimiento, tipo, descripcion,
                responsable_nombre, proveedor_nombre, costo, proxima_fecha,
                certificado_path, observaciones
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', [
            herramienta_id, data.get('fecha_mantenimiento'), data.get('tipo'),
            data.get('descripcion'), data.get('responsable_nombre'),
            data.get('proveedor_nombre'), data.get('costo', 0),
            data.get('proxima_fecha'), data.get('certificado_path'),
            data.get('observaciones')
        ])
        
        # Si correctivo y era defectuosa, cambiar a operativa
        if data['tipo'] == 'correctivo' and h[2] == 'defectuosa':
            c.execute("UPDATE herramientas SET condicion = 'operativa' WHERE id = ?", [herramienta_id])
        
        # Si calibración, actualizar última_calibracion
        if data['tipo'] == 'calibracion':
            c.execute('''
                UPDATE herramientas
                SET ultima_calibracion = ?, certificado_calibracion = ?
                WHERE id = ?
            ''', [data.get('fecha_mantenimiento'), data.get('certificado_path'), herramienta_id])
        
        c.commit()
        mantenimiento_id = cursor.lastrowid
        
        logger.info(f"Mantenimiento: {data['tipo']} - Herramienta {herramienta_id}")
        
        return jsonify({
            'ok': True,
            'msg': 'Mantenimiento registrado correctamente',
            'id': mantenimiento_id
        })
        
    except Exception as e:
        logger.error(f"Error en mantenimiento: {e}")
        return jsonify({'ok': False, 'msg': str(e)}), 500
    finally:
        c.close()


@bp.route('/<int:herramienta_id>/mantenimiento', strict_slashes=False)
def api_obtener_mantenimientos(herramienta_id):
    """Obtiene el historial de mantenimientos de una herramienta"""
    c = get_db()
    try:
        h = c.execute('SELECT id, nombre FROM herramientas WHERE id = ?', [herramienta_id]).fetchone()
        
        if not h:
            return jsonify({'ok': False, 'msg': 'Herramienta no encontrada'}), 404
        
        rows = c.execute('''
            SELECT id, fecha_mantenimiento, tipo, descripcion, responsable_nombre,
                   proveedor_nombre, costo, proxima_fecha, certificado_path,
                   observaciones, fecha_registro
            FROM herramientas_mantenimiento
            WHERE herramienta_id = ?
            ORDER BY fecha_mantenimiento DESC
        ''', [herramienta_id]).fetchall()
        
        return jsonify({
            'herramienta': {'id': h[0], 'nombre': h[1]},
            'mantenimientos': [{
                'id': r[0], 'fecha_mantenimiento': r[1], 'tipo': r[2],
                'descripcion': r[3], 'responsable_nombre': r[4],
                'proveedor_nombre': r[5], 'costo': r[6] or 0,
                'proxima_fecha': r[7], 'certificado_path': r[8],
                'observaciones': r[9], 'fecha_registro': r[10]
            } for r in rows]
        })
        
    except Exception as e:
        logger.error(f"Error obteniendo mantenimientos: {e}")
        return jsonify({'ok': False, 'msg': str(e)}), 500
    finally:
        c.close()


@bp.route('/mantenimiento', methods=['POST'], strict_slashes=False)
def api_registrar_mantenimiento_compat():
    """Compatibilidad: registra mantenimiento usando herramienta_id en payload"""
    c = get_db()
    try:
        data = request.json or {}
        herramienta_id = data.get('herramienta_id')

        if not herramienta_id:
            return jsonify({'ok': False, 'msg': 'herramienta_id requerido'}), 400

        h = c.execute(
            'SELECT id, condicion FROM herramientas WHERE id = ?',
            [herramienta_id]
        ).fetchone()

        if not h:
            return jsonify({'ok': False, 'msg': 'Herramienta no encontrada'}), 404

        fecha_mantenimiento = data.get('fecha_mantenimiento') or data.get('fecha')
        responsable = data.get('responsable_nombre') or data.get('realizado_por')

        if not all([fecha_mantenimiento, data.get('tipo'), data.get('descripcion')]):
            return jsonify({'ok': False, 'msg': 'Campos requeridos faltantes'}), 400

        if data['tipo'] not in ['preventivo', 'correctivo', 'calibracion']:
            return jsonify({'ok': False, 'msg': 'Tipo inválido'}), 400

        cursor = c.execute('''
            INSERT INTO herramientas_mantenimiento (
                herramienta_id, fecha_mantenimiento, tipo, descripcion,
                responsable_nombre, proveedor_nombre, costo, proxima_fecha,
                certificado_path, observaciones
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', [
            herramienta_id,
            fecha_mantenimiento,
            data.get('tipo'),
            data.get('descripcion'),
            responsable,
            data.get('proveedor_nombre'),
            data.get('costo', 0),
            data.get('proxima_fecha'),
            data.get('certificado_path'),
            data.get('observaciones')
        ])

        if data['tipo'] == 'correctivo' and h[1] == 'defectuosa':
            c.execute("UPDATE herramientas SET condicion = 'operativa' WHERE id = ?", [herramienta_id])

        if data['tipo'] == 'calibracion':
            c.execute('''
                UPDATE herramientas
                SET ultima_calibracion = ?, certificado_calibracion = ?
                WHERE id = ?
            ''', [fecha_mantenimiento, data.get('certificado_path'), herramienta_id])

        c.commit()
        mantenimiento_id = cursor.lastrowid

        return jsonify({
            'ok': True,
            'msg': 'Mantenimiento registrado correctamente',
            'id': mantenimiento_id
        })

    except Exception as e:
        logger.error(f"Error registrando mantenimiento compat: {e}")
        return jsonify({'ok': False, 'msg': str(e)}), 500
    finally:
        c.close()


@bp.route('/planes-mantenimiento', strict_slashes=False)
def api_planes_mantenimiento():
    """Lista planes de mantenimiento con estado de vencimiento"""
    c = get_db()
    try:
        rows = c.execute('''
            SELECT p.id, p.herramienta_id, h.nombre, h.sku,
                   p.tipo_mantenimiento, p.frecuencia_dias, p.descripcion,
                   p.costo_estimado, p.activo
            FROM herramientas_planes_mantenimiento p
            INNER JOIN herramientas h ON h.id = p.herramienta_id
            WHERE p.activo = 1
            ORDER BY h.nombre ASC
        ''').fetchall()

        hoy = datetime.now().date()
        planes = []

        for r in rows:
            ultimo = c.execute('''
                SELECT MAX(fecha_mantenimiento)
                FROM herramientas_mantenimiento
                WHERE herramienta_id = ? AND tipo = ?
            ''', [r[1], r[4]]).fetchone()[0]

            proximo = None
            estado = 'sin_registro'

            if ultimo:
                try:
                    prox_dt = datetime.strptime(ultimo, '%Y-%m-%d').date() + timedelta(days=r[5])
                    proximo = prox_dt.strftime('%Y-%m-%d')
                    estado = 'vencido' if prox_dt < hoy else 'al_dia'
                except Exception:
                    estado = 'sin_registro'

            planes.append({
                'id': r[0],
                'herramienta_id': r[1],
                'herramienta_nombre': r[2],
                'herramienta_sku': r[3],
                'tipo': r[4],
                'frecuencia_dias': r[5],
                'descripcion': r[6],
                'costo_estimado': r[7] or 0,
                'ultimo_mantenimiento': ultimo,
                'proximo_mantenimiento': proximo,
                'estado': estado
            })

        return jsonify({'ok': True, 'planes': planes})
    except Exception as e:
        logger.error(f"Error listando planes de mantenimiento: {e}")
        return jsonify({'ok': False, 'msg': str(e)}), 500
    finally:
        c.close()


@bp.route('/planes-mantenimiento', methods=['POST'], strict_slashes=False)
def api_crear_plan_mantenimiento():
    """Crea un plan de mantenimiento preventivo/calibracion"""
    c = get_db()
    try:
        data = request.json or {}

        herramienta_id = data.get('herramienta_id')
        tipo = data.get('tipo_mantenimiento') or data.get('tipo')
        frecuencia = data.get('frecuencia_dias')

        if not all([herramienta_id, tipo, frecuencia]):
            return jsonify({'ok': False, 'msg': 'Campos requeridos faltantes'}), 400

        if tipo not in ['preventivo', 'calibracion']:
            return jsonify({'ok': False, 'msg': 'Tipo de plan inválido'}), 400

        existe = c.execute('SELECT id FROM herramientas WHERE id = ?', [herramienta_id]).fetchone()
        if not existe:
            return jsonify({'ok': False, 'msg': 'Herramienta no encontrada'}), 404

        cursor = c.execute('''
            INSERT INTO herramientas_planes_mantenimiento (
                herramienta_id, frecuencia_dias, tipo_mantenimiento,
                descripcion, costo_estimado, activo
            ) VALUES (?, ?, ?, ?, ?, 1)
        ''', [
            herramienta_id,
            int(frecuencia),
            tipo,
            data.get('descripcion'),
            data.get('costo_estimado', 0)
        ])

        c.commit()
        return jsonify({'ok': True, 'msg': 'Plan de mantenimiento creado', 'id': cursor.lastrowid})
    except Exception as e:
        logger.error(f"Error creando plan de mantenimiento: {e}")
        return jsonify({'ok': False, 'msg': str(e)}), 500
    finally:
        c.close()


@bp.route('/planes-mantenimiento/<int:plan_id>', methods=['DELETE'], strict_slashes=False)
def api_eliminar_plan_mantenimiento(plan_id):
    """Desactiva un plan de mantenimiento"""
    c = get_db()
    try:
        existe = c.execute(
            'SELECT id FROM herramientas_planes_mantenimiento WHERE id = ? AND activo = 1',
            [plan_id]
        ).fetchone()

        if not existe:
            return jsonify({'ok': False, 'msg': 'Plan no encontrado'}), 404

        c.execute('UPDATE herramientas_planes_mantenimiento SET activo = 0 WHERE id = ?', [plan_id])
        c.commit()
        return jsonify({'ok': True, 'msg': 'Plan eliminado correctamente'})
    except Exception as e:
        logger.error(f"Error eliminando plan de mantenimiento: {e}")
        return jsonify({'ok': False, 'msg': str(e)}), 500
    finally:
        c.close()


@bp.route('/calibraciones-vencidas', strict_slashes=False)
def api_calibraciones_vencidas():
    """Lista herramientas con calibracion vencida"""
    c = get_db()
    try:
        hoy = datetime.now().strftime('%Y-%m-%d')
        rows = c.execute('''
            SELECT id, sku, nombre, ultima_calibracion, frecuencia_calibracion_dias
            FROM herramientas
            WHERE requiere_calibracion = 1
            AND (
                ultima_calibracion IS NULL
                OR date(ultima_calibracion, '+' || frecuencia_calibracion_dias || ' days') < date(?)
            )
            ORDER BY nombre
        ''', [hoy]).fetchall()

        herramientas = [{
            'id': r[0],
            'sku': r[1],
            'nombre': r[2],
            'ultima_calibracion': r[3],
            'frecuencia_calibracion_dias': r[4]
        } for r in rows]

        return jsonify({'ok': True, 'herramientas': herramientas, 'total': len(herramientas)})
    except Exception as e:
        logger.error(f"Error obteniendo calibraciones vencidas: {e}")
        return jsonify({'ok': False, 'msg': str(e)}), 500
    finally:
        c.close()


@bp.route('/mantenimientos-vencidos', strict_slashes=False)
def api_mantenimientos_vencidos():
    """Lista herramientas con plan de mantenimiento vencido"""
    c = get_db()
    try:
        rows = c.execute('''
            SELECT p.id, p.herramienta_id, h.sku, h.nombre, p.tipo_mantenimiento, p.frecuencia_dias
            FROM herramientas_planes_mantenimiento p
            INNER JOIN herramientas h ON h.id = p.herramienta_id
            WHERE p.activo = 1
        ''').fetchall()

        hoy = datetime.now().date()
        vencidas = []

        for r in rows:
            ultimo = c.execute('''
                SELECT MAX(fecha_mantenimiento)
                FROM herramientas_mantenimiento
                WHERE herramienta_id = ? AND tipo = ?
            ''', [r[1], r[4]]).fetchone()[0]

            if not ultimo:
                vencidas.append({
                    'herramienta_id': r[1],
                    'sku': r[2],
                    'nombre': r[3],
                    'tipo': r[4],
                    'frecuencia_dias': r[5],
                    'ultimo_mantenimiento': None,
                    'proximo_mantenimiento': None
                })
                continue

            try:
                proximo = datetime.strptime(ultimo, '%Y-%m-%d').date() + timedelta(days=r[5])
                if proximo < hoy:
                    vencidas.append({
                        'herramienta_id': r[1],
                        'sku': r[2],
                        'nombre': r[3],
                        'tipo': r[4],
                        'frecuencia_dias': r[5],
                        'ultimo_mantenimiento': ultimo,
                        'proximo_mantenimiento': proximo.strftime('%Y-%m-%d')
                    })
            except Exception:
                continue

        return jsonify({'ok': True, 'herramientas': vencidas, 'total': len(vencidas)})
    except Exception as e:
        logger.error(f"Error obteniendo mantenimientos vencidos: {e}")
        return jsonify({'ok': False, 'msg': str(e)}), 500
    finally:
        c.close()


@bp.route('/costos-mantenimiento', strict_slashes=False)
def api_costos_mantenimiento():
    """Resumen de costos de mantenimiento por mes"""
    c = get_db()
    try:
        meses = int(request.args.get('meses', 6))
        if meses < 1:
            meses = 1

        rows = c.execute('''
            SELECT strftime('%Y-%m', fecha_mantenimiento) as periodo,
                   COUNT(*) as cantidad,
                   COALESCE(SUM(costo), 0) as total
            FROM herramientas_mantenimiento
            WHERE fecha_mantenimiento >= date('now', '-' || ? || ' months')
            GROUP BY periodo
            ORDER BY periodo ASC
        ''', [meses]).fetchall()

        costos = [{
            'periodo': r[0],
            'cantidad': r[1],
            'total': float(r[2] or 0)
        } for r in rows]

        total_periodo = sum(item['total'] for item in costos)

        return jsonify({'ok': True, 'costos': costos, 'total_periodo': total_periodo})
    except Exception as e:
        logger.error(f"Error obteniendo costos de mantenimiento: {e}")
        return jsonify({'ok': False, 'msg': str(e)}), 500
    finally:
        c.close()



# =========================================================================
# OPERACIONES AVANZADAS DE PRÉSTAMOS (PROFESIONALES)
# =========================================================================

@bp.route('/prestamo/<int:movimiento_id>/renovar', methods=['POST'], strict_slashes=False)
def api_renovar_prestamo(movimiento_id):
    """Renueva/extiende un préstamo activo"""
    try:
        data = request.json or {}
        dias_extension = data.get('dias_extension', 7)
        observaciones = data.get('observaciones', '')

        result = PaniolService.renovar_prestamo(movimiento_id, dias_extension, observaciones)
        status = 400 if not result.get('ok') else 200
        return jsonify(result), status
    except Exception as e:
        logger.error(f"Error renovando préstamo: {e}")
        return jsonify({'ok': False, 'msg': str(e)}), 500


@bp.route('/prestamo/<int:movimiento_id>/cambiar-responsable', methods=['POST'], strict_slashes=False)
def api_cambiar_responsable(movimiento_id):
    """Cambia el empleado responsable de un préstamo activo"""
    try:
        data = request.json or {}
        nuevo_empleado_id = data.get('nuevo_empleado_id')
        nuevo_empleado_nombre = data.get('nuevo_empleado_nombre', '')
        motivo = data.get('motivo', '')

        if not nuevo_empleado_nombre:
            return jsonify({'ok': False, 'msg': 'Nombre del nuevo empleado requerido'}), 400

        result = PaniolService.cambiar_responsable_prestamo(
            movimiento_id, nuevo_empleado_id, nuevo_empleado_nombre, motivo
        )
        status = 400 if not result.get('ok') else 200
        return jsonify(result), status
    except Exception as e:
        logger.error(f"Error cambiando responsable: {e}")
        return jsonify({'ok': False, 'msg': str(e)}), 500


@bp.route('/prestamo/<int:movimiento_id>/devolucion-parcial', methods=['POST'], strict_slashes=False)
def api_devolucion_parcial(movimiento_id):
    """(DEPRECATED) Alias que redirige al mecanismo unificado de checkin.
    Se mantiene para compatibilidad con clientes antiguos.
    """
    try:
        data = request.json or {}
        cantidad_devuelta = data.get('cantidad_devuelta')
        estado_devoluciones = data.get('estado_devolucion', 'operativa')
        observaciones_devoluciones = data.get('observaciones_devolucion', '')

        if not cantidad_devuelta:
            return jsonify({'ok': False, 'msg': 'Cantidad devuelta requerida'}), 400

        # reutilizamos la lógica centralizada
        result = PaniolService.checkin_herramienta(
            movimiento_id, estado_devoluciones,
            observaciones_devoluciones, cantidad_devuelta
        )
        status = 400 if not result.get('ok') else 200
        return jsonify(result), status
    except Exception as e:
        logger.error(f"Error en devolución parcial: {e}")
        return jsonify({'ok': False, 'msg': str(e)}), 500


        @bp.route('/prestamos-vencidos', strict_slashes=False)
        def api_prestamos_vencidos():
            """Obtiene préstamos que excedieron el tiempo permitido"""
            try:
                dias_limite = int(request.args.get('dias_limite', 30))
                result = PaniolService.obtener_prestamos_vencidos(dias_limite)
                return jsonify(result)
            except Exception as e:
                logger.error(f"Error obteniendo préstamos vencidos: {e}")
                return jsonify({'ok': False, 'msg': str(e)}), 500


        @bp.route('/prestamo/<int:movimiento_id>/observacion', methods=['POST'], strict_slashes=False)
        def api_registrar_observacion(movimiento_id):
            """Agrega observación/nota a un préstamo activo"""
            try:
                data = request.json or {}
                observacion_nueva = data.get('observacion', '')
                tipo = data.get('tipo', 'general')
        
                if not observacion_nueva:
                    return jsonify({'ok': False, 'msg': 'Observación requerida'}), 400
        
                result = PaniolService.registrar_observacion_prestamo(movimiento_id, observacion_nueva, tipo)
                status = 400 if not result.get('ok') else 200
                return jsonify(result), status
            except Exception as e:
                logger.error(f"Error registrando observación: {e}")
                return jsonify({'ok': False, 'msg': str(e)}), 500


        @bp.route('/prestamo/<int:movimiento_id>/historial-completo', strict_slashes=False)
        def api_historial_completo_prestamo(movimiento_id):
            """Obtiene el historial completo y detallado de un préstamo"""
            try:
                result = PaniolService.obtener_historial_prestamo_completo(movimiento_id)
                status = 400 if not result.get('ok') else 200
                return jsonify(result), status
            except Exception as e:
                logger.error(f"Error obteniendo historial: {e}")
                return jsonify({'ok': False, 'msg': str(e)}), 500


@bp.route('/<int:herramienta_id>/recibir-mantenimiento', methods=['POST'], strict_slashes=False)
def api_recibir_desde_mantenimiento(herramienta_id):
    """Marca una herramienta en mantenimiento como operativa tras su recepcion"""
    c = get_db()
    try:
        data = request.json or {}

        h = c.execute(
            'SELECT id, nombre, condicion, observaciones FROM herramientas WHERE id = ?',
            [herramienta_id]
        ).fetchone()

        if not h:
            return jsonify({'ok': False, 'msg': 'Herramienta no encontrada'}), 404

        if h[2] != 'mantenimiento':
            return jsonify({'ok': False, 'msg': 'La herramienta no esta en mantenimiento'}), 400

        fecha_hoy = datetime.now().strftime('%Y-%m-%d')
        referencia = (data.get('referencia') or '').strip()
        informe = (data.get('informe_tecnico') or '').strip()

        nota_recepcion = f"Recepcion mantencion {fecha_hoy}"
        if referencia:
            nota_recepcion += f" | Ref: {referencia}"
        if informe:
            nota_recepcion += f" | Informe: {informe}"

        observaciones_actuales = h[3] or ''
        nuevas_observaciones = f"{observaciones_actuales}\n{nota_recepcion}".strip()

        # Restaurar condicion y cantidad_disponible
        cantidad_total = c.execute(
            'SELECT cantidad_total FROM herramientas WHERE id = ?', [herramienta_id]
        ).fetchone()[0] or 1

        c.execute('''
            UPDATE herramientas
            SET condicion = 'operativa',
                cantidad_disponible = ?,
                observaciones = ?
            WHERE id = ?
        ''', [cantidad_total, nuevas_observaciones, herramienta_id])

        cursor = c.execute('''
            INSERT INTO herramientas_mantenimiento (
                herramienta_id, fecha_mantenimiento, tipo, descripcion,
                responsable_nombre, observaciones
            ) VALUES (?, ?, 'correctivo', ?, ?, ?)
        ''', [
            herramienta_id,
            fecha_hoy,
            informe or 'Recepcion de herramienta desde mantencion',
            data.get('responsable_nombre') or 'Paniol',
            nota_recepcion
        ])

        c.commit()
        logger.info(f"Herramienta {herramienta_id} recibida de mantención")
        return jsonify({'ok': True, 'msg': f'{h[1]} recibida y marcada como operativa'})
    except Exception as e:
        logger.error(f"Error recibiendo herramienta desde mantenimiento: {e}")
        return jsonify({'ok': False, 'msg': str(e)}), 500
    finally:
        c.close()


@bp.route('/<int:herramienta_id>/enviar-mantenimiento', methods=['POST'], strict_slashes=False)
def api_enviar_a_mantenimiento(herramienta_id):
    """Envía herramienta a mantenimiento: cambia condicion y registra evento"""
    c = get_db()
    try:
        data = request.json or {}
        motivo = (data.get('motivo') or '').strip()
        if not motivo:
            return jsonify({'ok': False, 'msg': 'Motivo requerido'}), 400

        h = c.execute(
            'SELECT id, nombre, condicion FROM herramientas WHERE id = ?',
            [herramienta_id]
        ).fetchone()

        if not h:
            return jsonify({'ok': False, 'msg': 'Herramienta no encontrada'}), 404

        if h[2] == 'mantenimiento':
            return jsonify({'ok': False, 'msg': 'Herramienta ya está en mantenimiento'}), 400

        fecha_hoy = datetime.now().strftime('%Y-%m-%d')

        c.execute(
            'UPDATE herramientas SET condicion = ?, cantidad_disponible = 0 WHERE id = ?',
            ['mantenimiento', herramienta_id]
        )

        c.execute('''
            INSERT INTO herramientas_mantenimiento (
                herramienta_id, fecha_mantenimiento, tipo, descripcion, observaciones
            ) VALUES (?, ?, 'preventivo', ?, 'Inicio de mantención')
        ''', [herramienta_id, fecha_hoy, motivo])

        c.commit()
        logger.info(f"Herramienta {herramienta_id} enviada a mantención")
        return jsonify({'ok': True, 'msg': f'{h[1]} enviada a mantención'})
    except Exception as e:
        logger.error(f"Error enviando herramienta a mantenimiento: {e}")
        return jsonify({'ok': False, 'msg': str(e)}), 500
    finally:
        c.close()


# =========================================================================
# INFORMACIÓN DE MANTENIMIENTO
# =========================================================================

@bp.route('/<int:herramienta_id>/mantenimiento-info', methods=['POST'], strict_slashes=False)
def api_actualizar_mantenimiento_info(herramienta_id):
    """Actualiza información adicional de mantenimiento de una herramienta"""
    c = get_db()
    try:
        data = request.json
        
        h = c.execute(
            'SELECT id, nombre FROM herramientas WHERE id = ?',
            [herramienta_id]
        ).fetchone()
        
        if not h:
            return jsonify({'ok': False, 'msg': 'Herramienta no encontrada'}), 404
        
        info = data.get('info', '').strip()
        
        if not info:
            return jsonify({'ok': False, 'msg': 'Información requerida'}), 400
        
        # Actualizar observaciones
        c.execute(
            'UPDATE herramientas SET observaciones = ? WHERE id = ?',
            [info, herramienta_id]
        )
        
        c.commit()
        logger.info(f"Información de mantenimiento actualizada para herramienta {herramienta_id}")
        
        return jsonify({'ok': True, 'msg': 'Información actualizada'})
        
    except Exception as e:
        logger.error(f"Error actualizando información de mantenimiento: {e}")
        return jsonify({'ok': False, 'msg': str(e)}), 500
    finally:
        c.close()
