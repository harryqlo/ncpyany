"""
Rutas API para gestión de empleados del pañol
"""
from flask import Blueprint, jsonify, request
from datetime import datetime
from app.db import get_db
from app.search_utils import contains_terms_where
from logger_config import logger

bp = Blueprint('empleados', __name__, url_prefix='/api/empleados')


def suggest_numero_empleado(prefix='E'):
    """
    Sugiere el siguiente número de empleado disponible.
    
    Args:
        prefix: Prefijo del número de empleado (default: 'E')
        
    Returns:
        str: Número sugerido (ej. 'E021')
    """
    c = get_db()
    try:
        # Buscar el último número con ese prefijo
        rows = c.execute(
            """SELECT numero_identificacion FROM empleados 
               WHERE numero_identificacion LIKE ? 
               ORDER BY numero_identificacion DESC LIMIT 1""",
            [f"{prefix}%"]
        ).fetchall()
        
        if not rows:
            return f"{prefix}001"
        
        last_num = rows[0][0]
        
        # Intentar extraer el número
        try:
            num_part = last_num[len(prefix):]
            num = int(num_part)
            next_num = num + 1
            return f"{prefix}{next_num:03d}"
        except (ValueError, IndexError):
            return f"{prefix}001"
            
    finally:
        c.close()


@bp.route('/suggest-numero', strict_slashes=False)
def api_suggest_numero():
    """
    Sugiere un número de identificación para un nuevo empleado
    
    Query params:
        prefix: Prefijo del número (default: 'E')
    """
    prefix = request.args.get('prefix', 'E').strip().upper()
    if not prefix:
        return jsonify({'ok': False, 'msg': 'Prefijo requerido'}), 400
    
    try:
        suggested = suggest_numero_empleado(prefix)
        return jsonify({'ok': True, 'numero': suggested})
    except Exception as e:
        logger.error(f"Error sugiriendo número empleado: {e}")
        return jsonify({'ok': False, 'msg': str(e)}), 500


@bp.route('', strict_slashes=False)
def api_empleados():
    """
    Obtiene listado de empleados con filtros y paginación
    
    Query params:
        page: Número de página (default: 1)
        per_page: Registros por página (default: 50)
        search: Búsqueda en nombre, número ID, departamento
        estado: Filtro por estado (activo/inactivo)
        departamento: Filtro por departamento
        sort: Campo de ordenamiento (nombre, numero_identificacion, departamento)
        dir: Dirección (asc/desc)
    """
    c = get_db()
    try:
        # Parámetros de paginación
        pg = int(request.args.get('page', 1))
        pp = int(request.args.get('per_page', 50))
        
        # Filtros
        search = request.args.get('search', '').strip()
        estado = request.args.get('estado', '').strip()
        departamento = request.args.get('departamento', '').strip()
        
        # Ordenamiento
        sort_field = request.args.get('sort', 'nombre')
        sort_dir = request.args.get('dir', 'asc')
        
        # Construir query
        where_clauses = []
        params = []
        
        if search:
            search_where, search_params = contains_terms_where(search, ['numero_identificacion', 'nombre', 'departamento', 'email'])
            if search_where:
                where_clauses.append(search_where)
                params.extend(search_params)
        
        if estado:
            where_clauses.append("estado = ?")
            params.append(estado)
        
        if departamento:
            where_clauses.append("departamento = ?")
            params.append(departamento)
        
        where_sql = (' WHERE ' + ' AND '.join(where_clauses)) if where_clauses else ''
        
        # Validar campo de ordenamiento
        valid_sorts = {
            'nombre': 'nombre',
            'numero': 'numero_identificacion',
            'numero_identificacion': 'numero_identificacion',
            'departamento': 'departamento',
            'puesto': 'puesto',
            'estado': 'estado'
        }
        sort_col = valid_sorts.get(sort_field, 'nombre')
        sort_direction = 'DESC' if sort_dir == 'desc' else 'ASC'
        
        # Contar total
        total = c.execute(
            f'SELECT COUNT(*) FROM empleados{where_sql}',
            params
        ).fetchone()[0]
        
        # Obtener registros paginados
        offset = (pg - 1) * pp
        rows = c.execute(f'''
            SELECT id, numero_identificacion, nombre, departamento, puesto, 
                   telefono, email, estado, fecha_ingreso, observaciones,
                   fecha_creacion
            FROM empleados
            {where_sql}
            ORDER BY CASE WHEN {sort_col} IS NULL THEN 1 ELSE 0 END, {sort_col} {sort_direction}
            LIMIT ? OFFSET ?
        ''', params + [pp, offset]).fetchall()
        
        empleados = []
        for r in rows:
            empleados.append({
                'id': r[0],
                'numero_identificacion': r[1],
                'nombre': r[2],
                'departamento': r[3],
                'puesto': r[4],
                'telefono': r[5],
                'email': r[6],
                'estado': r[7],
                'fecha_ingreso': r[8],
                'observaciones': r[9],
                'fecha_creacion': r[10]
            })
        
        # Obtener listas de departamentos únicos para filtros
        departamentos = [r[0] for r in c.execute(
            'SELECT DISTINCT departamento FROM empleados WHERE departamento IS NOT NULL ORDER BY departamento'
        ).fetchall()]
        
        total_pages = max(1, -(-total // pp))  # Ceiling division
        
        return jsonify({
            'empleados': empleados,
            'total': total,
            'page': pg,
            'per_page': pp,
            'total_pages': total_pages,
            'departamentos': departamentos
        })
        
    except Exception as e:
        logger.error(f"Error obteniendo empleados: {e}")
        return jsonify({'ok': False, 'msg': str(e)}), 500
    finally:
        c.close()


@bp.route('', methods=['POST'], strict_slashes=False)
def api_crear_empleado():
    """
    Crea un nuevo empleado
    
    Body JSON:
        numero_identificacion: String único requerido
        nombre: String requerido
        departamento: String opcional
        puesto: String opcional
        telefono: String opcional
        email: String opcional
        estado: String (activo/inactivo) default: activo
        fecha_ingreso: String fecha ISO opcional
        observaciones: String opcional
    """
    c = get_db()
    try:
        data = request.json
        
        # Validaciones
        if not data.get('numero_identificacion'):
            return jsonify({'ok': False, 'msg': 'Número de identificación requerido'}), 400
        
        if not data.get('nombre'):
            return jsonify({'ok': False, 'msg': 'Nombre requerido'}), 400
        
        # Verificar que el número de identificación no exista
        exists = c.execute(
            'SELECT COUNT(*) FROM empleados WHERE numero_identificacion = ?',
            [data.get('numero_identificacion')]
        ).fetchone()[0]
        
        if exists > 0:
            return jsonify({'ok': False, 'msg': 'Número de identificación ya existe'}), 400
        
        # Insertar empleado
        cursor = c.cursor()
        cursor.execute('''
            INSERT INTO empleados (
                numero_identificacion, nombre, departamento, puesto,
                telefono, email, estado, fecha_ingreso, observaciones
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', [
            data.get('numero_identificacion'),
            data.get('nombre'),
            data.get('departamento'),
            data.get('puesto'),
            data.get('telefono'),
            data.get('email'),
            data.get('estado', 'activo'),
            data.get('fecha_ingreso'),
            data.get('observaciones')
        ])
        
        c.commit()
        
        empleado_id = cursor.lastrowid
        
        logger.info(f"Empleado creado: {data.get('numero_identificacion')} - {data.get('nombre')}")
        
        return jsonify({
            'ok': True,
            'msg': 'Empleado creado correctamente',
            'id': empleado_id
        })
        
    except Exception as e:
        logger.error(f"Error creando empleado: {e}")
        return jsonify({'ok': False, 'msg': str(e)}), 400
    finally:
        c.close()


@bp.route('/<int:empleado_id>', methods=['PUT'], strict_slashes=False)
def api_actualizar_empleado(empleado_id):
    """
    Actualiza un empleado existente
    
    Path params:
        empleado_id: ID del empleado
        
    Body JSON: mismos campos que crear
    """
    c = get_db()
    try:
        data = request.json
        
        # Verificar que el empleado existe
        empleado = c.execute(
            'SELECT id, numero_identificacion FROM empleados WHERE id = ?',
            [empleado_id]
        ).fetchone()
        
        if not empleado:
            return jsonify({'ok': False, 'msg': 'Empleado no encontrado'}), 404
        
        # Validaciones
        if not data.get('nombre'):
            return jsonify({'ok': False, 'msg': 'Nombre requerido'}), 400
        
        # Verificar unicidad de número de identificación (excluyendo el actual)
        if data.get('numero_identificacion') != empleado[1]:
            exists = c.execute(
                'SELECT COUNT(*) FROM empleados WHERE numero_identificacion = ? AND id != ?',
                [data.get('numero_identificacion'), empleado_id]
            ).fetchone()[0]
            
            if exists > 0:
                return jsonify({'ok': False, 'msg': 'Número de identificación ya existe'}), 400
        
        # Actualizar empleado
        c.execute('''
            UPDATE empleados SET
                numero_identificacion = ?,
                nombre = ?,
                departamento = ?,
                puesto = ?,
                telefono = ?,
                email = ?,
                estado = ?,
                fecha_ingreso = ?,
                observaciones = ?
            WHERE id = ?
        ''', [
            data.get('numero_identificacion'),
            data.get('nombre'),
            data.get('departamento'),
            data.get('puesto'),
            data.get('telefono'),
            data.get('email'),
            data.get('estado', 'activo'),
            data.get('fecha_ingreso'),
            data.get('observaciones'),
            empleado_id
        ])
        
        c.commit()
        
        logger.info(f"Empleado actualizado: {empleado_id} - {data.get('nombre')}")
        
        return jsonify({
            'ok': True,
            'msg': 'Empleado actualizado correctamente'
        })
        
    except Exception as e:
        logger.error(f"Error actualizando empleado: {e}")
        return jsonify({'ok': False, 'msg': str(e)}), 400
    finally:
        c.close()


@bp.route('/<int:empleado_id>', methods=['DELETE'], strict_slashes=False)
def api_eliminar_empleado(empleado_id):
    """
    Elimina (desactiva) un empleado
    
    Soft delete: cambia estado a 'inactivo'
    No permite eliminar si tiene préstamos activos
    
    Path params:
        empleado_id: ID del empleado
    """
    c = get_db()
    try:
        # Verificar que el empleado existe
        empleado = c.execute(
            'SELECT id, nombre, estado FROM empleados WHERE id = ?',
            [empleado_id]
        ).fetchone()
        
        if not empleado:
            return jsonify({'ok': False, 'msg': 'Empleado no encontrado'}), 404
        
        # Verificar que no tenga préstamos activos
        prestamos_activos = c.execute(
            'SELECT COUNT(*) FROM herramientas_movimientos WHERE empleado_id = ? AND fecha_retorno IS NULL',
            [empleado_id]
        ).fetchone()[0]
        
        if prestamos_activos > 0:
            return jsonify({
                'ok': False,
                'msg': f'No se puede desactivar: tiene {prestamos_activos} préstamo(s) activo(s)'
            }), 400
        
        # Soft delete: cambiar estado a inactivo
        c.execute(
            'UPDATE empleados SET estado = ? WHERE id = ?',
            ['inactivo', empleado_id]
        )
        
        c.commit()
        
        logger.info(f"Empleado desactivado: {empleado_id} - {empleado[1]}")
        
        return jsonify({
            'ok': True,
            'msg': 'Empleado desactivado correctamente'
        })
        
    except Exception as e:
        logger.error(f"Error eliminando empleado: {e}")
        return jsonify({'ok': False, 'msg': str(e)}), 500
    finally:
        c.close()


@bp.route('/search', strict_slashes=False)
def api_buscar_empleados():
    """
    Búsqueda rápida de empleados (autocomplete)
    
    Query params:
        q: Término de búsqueda
        solo_activos: Si es 1, solo devuelve empleados activos (default: 1)
    """
    c = get_db()
    try:
        q = request.args.get('q', '').strip()
        solo_activos = request.args.get('solo_activos', '1') == '1'
        
        if len(q) < 1:
            return jsonify([])
        
        search_where, params = contains_terms_where(q, ['numero_identificacion', 'nombre', 'departamento'])
        where_clause = f"WHERE {search_where}" if search_where else ""
        
        if solo_activos:
            where_clause += " AND estado = 'activo'"
        
        rows = c.execute(f'''
            SELECT id, numero_identificacion, nombre, departamento, puesto, estado
            FROM empleados
            {where_clause}
            ORDER BY nombre
            LIMIT 20
        ''', params).fetchall()
        
        return jsonify([{
            'id': r[0],
            'numero_identificacion': r[1],
            'nombre': r[2],
            'departamento': r[3],
            'puesto': r[4],
            'estado': r[5]
        } for r in rows])
        
    except Exception as e:
        logger.error(f"Error buscando empleados: {e}")
        return jsonify({'ok': False, 'msg': str(e)}), 500
    finally:
        c.close()


@bp.route('/<int:empleado_id>', strict_slashes=False)
def api_obtener_empleado(empleado_id):
    """
    Obtiene detalles de un empleado específico
    
    Path params:
        empleado_id: ID del empleado
    """
    c = get_db()
    try:
        empleado = c.execute('''
            SELECT id, numero_identificacion, nombre, departamento, puesto,
                   telefono, email, estado, fecha_ingreso, observaciones,
                   fecha_creacion
            FROM empleados
            WHERE id = ?
        ''', [empleado_id]).fetchone()
        
        if not empleado:
            return jsonify({'ok': False, 'msg': 'Empleado no encontrado'}), 404
        
        # Obtener estadísticas de préstamos
        stats = c.execute('''
            SELECT 
                COUNT(*) as total_prestamos,
                COUNT(CASE WHEN fecha_retorno IS NULL THEN 1 END) as prestamos_activos,
                COUNT(CASE WHEN fecha_retorno IS NOT NULL THEN 1 END) as prestamos_completados
            FROM herramientas_movimientos
            WHERE empleado_id = ?
        ''', [empleado_id]).fetchone()

        herramientas_a_cargo = c.execute('''
            SELECT m.id, m.herramienta_id, m.fecha_salida, m.cantidad,
                   h.sku, h.nombre, h.condicion
            FROM herramientas_movimientos m
            INNER JOIN herramientas h ON h.id = m.herramienta_id
            WHERE m.empleado_id = ?
              AND m.fecha_retorno IS NULL
            ORDER BY m.fecha_salida DESC, h.nombre ASC
        ''', [empleado_id]).fetchall()

        hoy = datetime.now()

        herramientas_activas = []
        for item in herramientas_a_cargo:
            try:
                fecha_salida_dt = datetime.strptime(item[2], '%Y-%m-%d')
                dias_prestado = (hoy - fecha_salida_dt).days
            except Exception:
                dias_prestado = 0

            herramientas_activas.append({
                'movimiento_id': item[0],
                'herramienta_id': item[1],
                'fecha_salida': item[2],
                'cantidad': item[3],
                'sku': item[4],
                'nombre': item[5],
                'condicion': item[6],
                'dias_prestado': dias_prestado
            })
        
        return jsonify({
            'ok': True,
            'empleado': {
                'id': empleado[0],
                'numero_identificacion': empleado[1],
                'nombre': empleado[2],
                'departamento': empleado[3],
                'puesto': empleado[4],
                'telefono': empleado[5],
                'email': empleado[6],
                'estado': empleado[7],
                'fecha_ingreso': empleado[8],
                'observaciones': empleado[9],
                'fecha_creacion': empleado[10],
                'stats': {
                    'total_prestamos': stats[0],
                    'prestamos_activos': stats[1],
                    'prestamos_completados': stats[2]
                },
                'herramientas_a_cargo': herramientas_activas
            }
        })
        
    except Exception as e:
        logger.error(f"Error obteniendo empleado: {e}")
        return jsonify({'ok': False, 'msg': str(e)}), 500
    finally:
        c.close()
