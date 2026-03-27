"""
Servicio de lógica de negocio para el Pañol
Centraliza todas las operaciones de herramientas, empleados y movimientos
"""
from datetime import datetime, timedelta
from app.db import get_db
from app.search_utils import contains_terms_where
from logger_config import logger, log_operation


class PaniolService:
    """Servicio para operaciones del sistema de Pañol"""

    @staticmethod
    def _audit_sensitive(action, details, success=True, user='system'):
        """Auditoría centralizada para eventos sensibles de inventario y préstamos."""
        log_operation(
            operation=action,
            resource='herramientas',
            details=details,
            user=user,
            success=success,
        )
    
    # =========================================================================
    # HERRAMIENTAS - CRUD
    # =========================================================================
    
    @staticmethod
    def obtener_herramientas(pg=1, pp=50, search='', condicion='', categoria='', 
                            ubicacion='', calibracion_vencida=False, disponible=False,
                            sort_field='nombre', sort_dir='asc'):
        """
        Obtiene listado de herramientas con filtros y paginación
        
        Returns:
            dict: {'herramientas': [...], 'total': int, 'page': int, 'per_page': int, ...}
        """
        c = get_db('paniol')
        try:
            where_clauses = []
            params = []
            
            if search:
                search_where, search_params = contains_terms_where(search, ['sku', 'nombre', 'modelo', 'fabricante'])
                if search_where:
                    where_clauses.append(search_where)
                    params.extend(search_params)
            
            if condicion:
                where_clauses.append("condicion = ?")
                params.append(condicion)
            
            if categoria:
                where_clauses.append("categoria_nombre = ?")
                params.append(categoria)
            
            if ubicacion:
                where_clauses.append("ubicacion_nombre = ?")
                params.append(ubicacion)
            
            if calibracion_vencida:
                hoy = datetime.now().strftime('%Y-%m-%d')
                where_clauses.append("""
                    requiere_calibracion = 1 
                    AND (
                        ultima_calibracion IS NULL 
                        OR date(ultima_calibracion, '+' || frecuencia_calibracion_dias || ' days') < date(?)
                    )
                """)
                params.append(hoy)
            
            if disponible:
                where_clauses.append("cantidad_disponible > 0")
            
            where_sql = (' WHERE ' + ' AND '.join(where_clauses)) if where_clauses else ''
            
            # Contar total
            total = c.execute(
                f'SELECT COUNT(*) FROM herramientas{where_sql}',
                params
            ).fetchone()[0]
            
            # Validar sort
            valid_sorts = {
                'sku': 'sku',
                'nombre': 'nombre',
                'condicion': 'condicion',
                'categoria': 'categoria_nombre',
                'ubicacion': 'ubicacion_nombre'
            }
            sort_col = valid_sorts.get(sort_field, 'nombre')
            sort_direction = 'DESC' if sort_dir == 'desc' else 'ASC'
            
            offset = (pg - 1) * pp
            rows = c.execute(f'''
                SELECT id, sku, nombre, categoria_nombre, subcategoria_nombre,
                       numero_serie, modelo, fabricante, ubicacion_nombre, condicion,
                       fecha_adquisicion, precio_unitario, requiere_calibracion,
                       frecuencia_calibracion_dias, ultima_calibracion,
                       certificado_calibracion, observaciones, cantidad_total,
                       cantidad_disponible, fecha_creacion
                FROM herramientas
                {where_sql}
                ORDER BY {sort_col} {sort_direction}
                LIMIT ? OFFSET ?
            ''', params + [pp, offset]).fetchall()
            
            herramientas = [PaniolService._mapear_herramienta(r) for r in rows]
            
            # Obtener listas para filtros
            categorias = [r[0] for r in c.execute(
                'SELECT DISTINCT categoria_nombre FROM herramientas '
                'WHERE categoria_nombre IS NOT NULL ORDER BY categoria_nombre'
            ).fetchall()]
            
            ubicaciones = [r[0] for r in c.execute(
                'SELECT DISTINCT ubicacion_nombre FROM herramientas '
                'WHERE ubicacion_nombre IS NOT NULL ORDER BY ubicacion_nombre'
            ).fetchall()]
            
            total_pages = max(1, -(-total // pp))
            
            return {
                'herramientas': herramientas,
                'total': total,
                'page': pg,
                'per_page': pp,
                'total_pages': total_pages,
                'categorias': categorias,
                'ubicaciones': ubicaciones
            }
            
        finally:
            c.close()
    
    @staticmethod
    def crear_herramienta(data):
        """Crea una nueva herramienta"""
        from config import HERRAMIENTAS_PREFIX_DEFAULT, HERRAMIENTAS_SKU_SEPARATOR
        
        c = get_db('paniol')  # Usar BD de pañol
        try:
            # Validaciones
            sku = data.get('sku', '').strip().upper()
            
            if not data.get('nombre'):
                return {'ok': False, 'msg': 'Nombre requerido'}
            
            # Si no se proporciona SKU o no tiene prefijo, generar automáticamente con NC
            if not sku or HERRAMIENTAS_SKU_SEPARATOR not in sku:
                prefix = HERRAMIENTAS_PREFIX_DEFAULT
                # Buscar último número de herramienta con ese prefijo
                rows = c.execute(
                    'SELECT sku FROM herramientas WHERE sku LIKE ? ORDER BY sku DESC LIMIT 1',
                    [f"{prefix}%"]
                ).fetchall()
                
                if not rows:
                    sku = f"{prefix}{HERRAMIENTAS_SKU_SEPARATOR}001"
                else:
                    try:
                        # Extraer número del último SKU
                        last_sku = rows[0][0]
                        if HERRAMIENTAS_SKU_SEPARATOR in last_sku:
                            last_num = int(last_sku.split(HERRAMIENTAS_SKU_SEPARATOR)[-1])
                            new_num = last_num + 1
                            sku = f"{prefix}{HERRAMIENTAS_SKU_SEPARATOR}{new_num:03d}"
                        else:
                            sku = data.get('sku', '')
                    except (ValueError, IndexError):
                        sku = data.get('sku', '')
            
            if not sku:
                return {'ok': False, 'msg': 'No se pudo generar SKU'}
            
            # SKU único
            exists = c.execute(
                'SELECT COUNT(*) FROM herramientas WHERE sku = ?',
                [sku]
            ).fetchone()[0]
            
            if exists > 0:
                return {'ok': False, 'msg': f'SKU {sku} ya existe'}
            
            # Insertar (usar SKU generado/validado)
            cursor = c.cursor()
            cursor.execute('''
                INSERT INTO herramientas (
                    sku, nombre, categoria_nombre, subcategoria_nombre,
                    numero_serie, modelo, fabricante, ubicacion_nombre, condicion,
                    fecha_adquisicion, precio_unitario, requiere_calibracion,
                    frecuencia_calibracion_dias, ultima_calibracion,
                    certificado_calibracion, observaciones, cantidad_total,
                    cantidad_disponible
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', [
                sku,
                data.get('nombre'),
                data.get('categoria'),
                data.get('subcategoria'),
                data.get('numero_serie'),
                data.get('modelo'),
                data.get('fabricante'),
                data.get('ubicacion'),
                data.get('condicion', 'operativa'),
                data.get('fecha_adquisicion'),
                data.get('precio_unitario', 0),
                1 if data.get('requiere_calibracion') else 0,
                data.get('frecuencia_calibracion_dias'),
                data.get('ultima_calibracion'),
                data.get('certificado_calibracion'),
                data.get('observaciones'),
                data.get('cantidad_total', 1),
                data.get('cantidad_disponible', data.get('cantidad_total', 1))
            ])
            
            c.commit()
            herramienta_id = cursor.lastrowid
            
            logger.info(f"Herramienta creada: {data.get('sku')}")
            PaniolService._audit_sensitive(
                action='CREATE',
                details=f"herramienta_id={herramienta_id} sku={sku} nombre={data.get('nombre')}",
            )
            
            return {
                'ok': True,
                'msg': 'Herramienta creada correctamente',
                'id': herramienta_id
            }
            
        except Exception as e:
            logger.error(f"Error creando herramienta: {e}")
            return {'ok': False, 'msg': str(e)}
        finally:
            c.close()
    
    @staticmethod
    def actualizar_herramienta(herramienta_id, data):
        """Actualiza una herramienta existente. Soporta actualización parcial (solo condicion, etc.)"""
        c = get_db('paniol')
        try:
            herramienta = c.execute(
                '''SELECT id, sku, nombre, categoria_nombre, subcategoria_nombre,
                          numero_serie, modelo, fabricante, ubicacion_nombre, condicion,
                          fecha_adquisicion, precio_unitario, requiere_calibracion,
                          frecuencia_calibracion_dias, ultima_calibracion,
                          certificado_calibracion, observaciones, cantidad_total
                   FROM herramientas WHERE id = ?''',
                [herramienta_id]
            ).fetchone()
            
            if not herramienta:
                return {'ok': False, 'msg': 'Herramienta no encontrada'}
            
            # Merge: usar valores existentes si no se proveen en data
            merged = {
                'sku':                     data.get('sku',                     herramienta[1]),
                'nombre':                  data.get('nombre',                  herramienta[2]),
                'categoria':               data.get('categoria',               herramienta[3]),
                'subcategoria':            data.get('subcategoria',            herramienta[4]),
                'numero_serie':            data.get('numero_serie',            herramienta[5]),
                'modelo':                  data.get('modelo',                  herramienta[6]),
                'fabricante':              data.get('fabricante',              herramienta[7]),
                'ubicacion':               data.get('ubicacion',               herramienta[8]),
                'condicion':               data.get('condicion',               herramienta[9]),
                'fecha_adquisicion':       data.get('fecha_adquisicion',       herramienta[10]),
                'precio_unitario':         data.get('precio_unitario',         herramienta[11]),
                'requiere_calibracion':    data.get('requiere_calibracion',    bool(herramienta[12])),
                'frecuencia_calibracion_dias': data.get('frecuencia_calibracion_dias', herramienta[13]),
                'ultima_calibracion':      data.get('ultima_calibracion',      herramienta[14]),
                'certificado_calibracion': data.get('certificado_calibracion', herramienta[15]),
                'observaciones':           data.get('observaciones',           herramienta[16]),
                'cantidad_total':          data.get('cantidad_total',          herramienta[17]),
            }
            data = merged

            if not data.get('nombre'):
                return {'ok': False, 'msg': 'Nombre requerido'}
            
            # Verificar SKU único
            if data.get('sku') != herramienta[1]:
                exists = c.execute(
                    'SELECT COUNT(*) FROM herramientas WHERE sku = ? AND id != ?',
                    [data.get('sku'), herramienta_id]
                ).fetchone()[0]
                
                if exists > 0:
                    return {'ok': False, 'msg': 'SKU ya existe'}
            
            c.execute('''
                UPDATE herramientas SET
                    sku = ?, nombre = ?, categoria_nombre = ?, subcategoria_nombre = ?,
                    numero_serie = ?, modelo = ?, fabricante = ?, ubicacion_nombre = ?,
                    condicion = ?, fecha_adquisicion = ?, precio_unitario = ?,
                    requiere_calibracion = ?, frecuencia_calibracion_dias = ?,
                    ultima_calibracion = ?, certificado_calibracion = ?,
                    observaciones = ?, cantidad_total = ?
                WHERE id = ?
            ''', [
                data.get('sku'),
                data.get('nombre'),
                data.get('categoria'),
                data.get('subcategoria'),
                data.get('numero_serie'),
                data.get('modelo'),
                data.get('fabricante'),
                data.get('ubicacion'),
                data.get('condicion', 'operativa'),
                data.get('fecha_adquisicion'),
                data.get('precio_unitario', 0),
                1 if data.get('requiere_calibracion') else 0,
                data.get('frecuencia_calibracion_dias'),
                data.get('ultima_calibracion'),
                data.get('certificado_calibracion'),
                data.get('observaciones'),
                data.get('cantidad_total', 1),
                herramienta_id
            ])
            
            c.commit()
            logger.info(f"Herramienta actualizada: {herramienta_id}")
            PaniolService._audit_sensitive(
                action='UPDATE',
                details=f"herramienta_id={herramienta_id} sku={data.get('sku')} nombre={data.get('nombre')}",
            )
            
            return {'ok': True, 'msg': 'Herramienta actualizada correctamente'}
            
        except Exception as e:
            logger.error(f"Error actualizando herramienta: {e}")
            return {'ok': False, 'msg': str(e)}
        finally:
            c.close()
    
    @staticmethod
    def eliminar_herramienta(herramienta_id):
        """Elimina una herramienta (validando préstamos activos)"""
        c = get_db('paniol')
        try:
            herramienta = c.execute(
                'SELECT id, nombre FROM herramientas WHERE id = ?',
                [herramienta_id]
            ).fetchone()
            
            if not herramienta:
                return {'ok': False, 'msg': 'Herramienta no encontrada'}
            
            # Verificar préstamos activos
            prestamos_activos = c.execute(
                'SELECT COUNT(*) FROM herramientas_movimientos '
                'WHERE herramienta_id = ? AND fecha_retorno IS NULL',
                [herramienta_id]
            ).fetchone()[0]
            
            if prestamos_activos > 0:
                return {
                    'ok': False,
                    'msg': f'No se puede eliminar: tiene {prestamos_activos} préstamo(s) activo(s)'
                }
            
            c.execute('DELETE FROM herramientas WHERE id = ?', [herramienta_id])
            c.commit()
            
            logger.info(f"Herramienta eliminada: {herramienta_id}")
            PaniolService._audit_sensitive(
                action='DELETE',
                details=f"herramienta_id={herramienta_id} nombre={herramienta[1]}",
            )
            
            return {'ok': True, 'msg': 'Herramienta eliminada correctamente'}
            
        except Exception as e:
            logger.error(f"Error eliminando herramienta: {e}")
            return {'ok': False, 'msg': str(e)}
        finally:
            c.close()
    
    # =========================================================================
    # OPERACIONES - CHECKOUT/CHECKIN
    # =========================================================================
    
    @staticmethod
    def checkout_herramientas(data):
        """
        Registra préstamo de herramientas (batch)
        El data debe contener: empleado_id, empleado_nombre, herramientas[]
        """
        conn = get_db('paniol')
        c = conn.cursor()
        try:
            # Aceptar múltiples formatos de empleado
            empleado_id = data.get('empleado_id')
            empleado_nombre = data.get('empleado_nombre') or data.get('empleado')
            
            if not empleado_id and not empleado_nombre:
                return {'ok': False, 'msg': 'Empleado requerido'}
            
            herramientas = data.get('herramientas', [])
            if not herramientas:
                return {'ok': False, 'msg': 'Debe especificar al menos una herramienta'}
            
            # Validar empleado
            empleado = None
            if empleado_id:
                empleado = c.execute(
                    'SELECT id, nombre, estado FROM empleados WHERE id = ?',
                    [empleado_id]
                ).fetchone()
                
                if not empleado:
                    return {'ok': False, 'msg': 'Empleado no encontrado'}
                
                if empleado[2] != 'activo':
                    return {'ok': False, 'msg': 'Empleado inactivo'}
            elif empleado_nombre:
                # En caso de que sea número de identificación, buscar por eso
                empleado = c.execute(
                    'SELECT id, nombre, estado FROM empleados WHERE numero_identificacion = ? OR nombre = ?',
                    [empleado_nombre, empleado_nombre]
                ).fetchone()
                
                if empleado and empleado[2] != 'activo':
                    return {'ok': False, 'msg': 'Empleado inactivo'}
                
                if not empleado:
                    # Si no existe, usamos el nombre como está
                    pass
                else:
                    empleado_id = empleado[0]
                    empleado_nombre = empleado[1]
            
            nombre_final = empleado[1] if empleado else empleado_nombre
            fecha_salida = datetime.now().strftime('%Y-%m-%d')
            
            # Validar y procesar
            mensajes_error = []
            herramientas_ok = []
            
            for item in herramientas:
                herr_id = item.get('herramienta_id')
                cantidad = item.get('cantidad', 1)
                
                herr = c.execute('''
                    SELECT id, sku, nombre, condicion, cantidad_disponible
                    FROM herramientas WHERE id = ?
                ''', [herr_id]).fetchone()
                
                if not herr:
                    mensajes_error.append(f"Herramienta ID {herr_id} no encontrada")
                    continue
                
                if herr[3] != 'operativa':
                    mensajes_error.append(f"{herr[2]}: No está operativa ({herr[3]})")
                    continue
                
                if herr[4] < cantidad:
                    mensajes_error.append(
                        f"{herr[2]}: Cantidad insuficiente (disp: {herr[4]}, sol: {cantidad})"
                    )
                    continue
                
                herramientas_ok.append({
                    'herramienta_id': herr_id,
                    'cantidad': cantidad,
                    'observaciones': item.get('observaciones')
                })
            
            if mensajes_error:
                return {
                    'ok': False,
                    'msg': 'Errores de validación',
                    'errores': mensajes_error
                }
            
            # Registrar movimientos
            movimientos_creados = []
            for item in herramientas_ok:
                cursor = c.execute('''
                    INSERT INTO herramientas_movimientos (
                        herramienta_id, empleado_id, empleado_nombre, fecha_salida,
                        cantidad, estado_salida, observaciones_salida, orden_trabajo_id
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', [
                    item['herramienta_id'],
                    empleado_id,
                    nombre_final,
                    fecha_salida,
                    item['cantidad'],
                    'operativa',
                    item['observaciones'],
                    data.get('orden_trabajo_id')
                ])
                
                movimiento_id = cursor.lastrowid
                movimientos_creados.append(movimiento_id)
                
                # Actualizar disponible
                c.execute('''
                    UPDATE herramientas
                    SET cantidad_disponible = cantidad_disponible - ?
                    WHERE id = ?
                ''', [item['cantidad'], item['herramienta_id']])
            
            conn.commit()
            logger.info(f"Checkout: {len(movimientos_creados)} herramientas a {nombre_final}")
            PaniolService._audit_sensitive(
                action='CHECKOUT',
                details=(
                    f"movimientos={movimientos_creados} empleado={nombre_final} "
                    f"empleado_id={empleado_id} cantidad_items={len(herramientas_ok)}"
                ),
            )
            
            return {
                'ok': True,
                'msg': f'{len(movimientos_creados)} herramienta(s) prestada(s)',
                'movimientos': movimientos_creados
            }
            
        except Exception as e:
            logger.error(f"Error en checkout: {e}")
            return {'ok': False, 'msg': str(e)}
        finally:
            c.close()
            conn.close()
    
    @staticmethod
    def checkin_herramienta(movimiento_id, estado_retorno, observaciones_retorno, cantidad_devuelta=None):
        """
        Registra devolución de una herramienta. Esta función ahora maneja devoluciones
        totales y parciales dentro de un único flujo. Si la cantidad devuelta es menor
        que la cantidad prestada, se conserva un nuevo movimiento "pendiente" con la
        cantidad restante.

        Args:
            movimiento_id: ID del movimiento original
            estado_retorno: Estado de la herramienta al devolver ('operativa',
                'defectuosa', 'mantenimiento', etc.)
            observaciones_retorno: Texto libre con comentarios sobre la devolución
            cantidad_devuelta: Opcional; si se omite se asume la cantidad completa.
        """
        conn = get_db('paniol')
        c = conn.cursor()
        try:
            # Obtener movimiento
            movimiento = c.execute('''
                SELECT id, herramienta_id, cantidad, fecha_salida, fecha_retorno,
                       estado_salida, orden_trabajo_id, empleado_id, empleado_nombre
                FROM herramientas_movimientos WHERE id = ?
            ''', [movimiento_id]).fetchone()

            if not movimiento:
                return {'ok': False, 'msg': 'Movimiento no encontrado'}

            if movimiento[4] is not None:
                return {'ok': False, 'msg': 'Movimiento ya fue devuelto'}

            # Validaciones
            if estado_retorno != 'operativa' and not observaciones_retorno:
                return {
                    'ok': False,
                    'msg': f'Observaciones requeridas para estado {estado_retorno}'
                }

            cantidad_total = movimiento[2] or 0
            cantidad_dev = cantidad_devuelta if cantidad_devuelta is not None else cantidad_total
            if cantidad_dev > cantidad_total:
                return {'ok': False, 'msg': 'No puede devolver más de lo prestado'}
            if cantidad_dev <= 0:
                return {'ok': False, 'msg': 'Cantidad devuelta debe ser mayor a 0'}

            fecha_retorno = datetime.now().strftime('%Y-%m-%d')

            # Devolución completa
            if cantidad_dev == cantidad_total:
                c.execute('''
                    UPDATE herramientas_movimientos
                    SET fecha_retorno = ?, estado_retorno = ?, observaciones_retorno = ?
                    WHERE id = ?
                ''', [fecha_retorno, estado_retorno, observaciones_retorno, movimiento_id])
                msg = f'Devolución total registrada ({cantidad_total} unidades)'
            else:
                # Parcial: cerrar movimiento actual con la cantidad devuelta y crear uno nuevo
                # para la cantidad restante.
                c.execute('''
                    UPDATE herramientas_movimientos
                    SET fecha_retorno = ?, estado_retorno = ?,
                        observaciones_retorno = ?, cantidad = ?
                    WHERE id = ?
                ''', [fecha_retorno, estado_retorno, observaciones_retorno,
                      cantidad_dev, movimiento_id])

                pendiente = cantidad_total - cantidad_dev
                c.execute('''
                    INSERT INTO herramientas_movimientos (
                        herramienta_id, empleado_id, empleado_nombre, fecha_salida,
                        cantidad, estado_salida, observaciones_salida, orden_trabajo_id,
                        usuario_registro
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', [
                    movimiento[1], movimiento[7], movimiento[8], movimiento[3],
                    pendiente, movimiento[5],
                    f"Devolución parcial. Pendiente: {pendiente}",
                    movimiento[6], 'devolución_parcial'
                ])
                msg = f'Devolución parcial: {cantidad_dev} unidades. Pendiente: {pendiente}'

            # Actualizar disponible
            c.execute('''
                UPDATE herramientas
                SET cantidad_disponible = cantidad_disponible + ?
                WHERE id = ?
            ''', [cantidad_dev, movimiento[1]])

            # Actualizar condición si es defectuosa
            if estado_retorno in ['defectuosa', 'dañada']:
                c.execute(
                    'UPDATE herramientas SET condicion = ? WHERE id = ?',
                    ['defectuosa', movimiento[1]]
                )

            conn.commit()
            logger.info(f"Checkin: movimiento {movimiento_id} devuelto (qty {cantidad_dev})")
            PaniolService._audit_sensitive(
                action='CHECKIN',
                details=(
                    f"movimiento_id={movimiento_id} herramienta_id={movimiento[1]} "
                    f"estado_retorno={estado_retorno} cantidad_devuelta={cantidad_dev}"
                ),
            )

            return {'ok': True, 'msg': msg}

        except Exception as e:
            logger.error(f"Error en checkin: {e}")
            return {'ok': False, 'msg': str(e)}
        finally:
            c.close()
            conn.close()
    
    @staticmethod
    def obtener_prestamos_activos():
        """Obtiene lista de préstamos activos"""
        c = get_db('paniol')
        try:
            rows = c.execute('''
                SELECT m.id, m.herramienta_id, m.empleado_id, m.empleado_nombre,
                       m.fecha_salida, m.cantidad, m.estado_salida,
                       h.sku, h.nombre, h.modelo
                FROM herramientas_movimientos m
                INNER JOIN herramientas h ON m.herramienta_id = h.id
                WHERE m.fecha_retorno IS NULL
                ORDER BY m.fecha_salida DESC
            ''').fetchall()
            
            prestamos = []
            hoy = datetime.now()
            
            for r in rows:
                try:
                    fecha_salida = datetime.strptime(r[4], '%Y-%m-%d')
                    dias_prestado = (hoy - fecha_salida).days
                except:
                    dias_prestado = 0
                
                prestamos.append({
                    'id': r[0],
                    'movimiento_id': r[0],
                    'herramienta_id': r[1],
                    'empleado_id': r[2],
                    'empleado_nombre': r[3],
                    'fecha_salida': r[4],
                    'cantidad': r[5],
                    'estado_salida': r[6],
                    'herramienta_sku': r[7],
                    'herramienta_nombre': r[8],
                    'herramienta_modelo': r[9],
                    'dias_prestado': dias_prestado
                })
            
            return {'prestamos': prestamos, 'total': len(prestamos)}
            
        except Exception as e:
            logger.error(f"Error obteniendo préstamos activos: {e}")
            return {'ok': False, 'msg': str(e)}
        finally:
            c.close()

    @staticmethod
    def obtener_prestamos_por_usuario(search=''):
        """Agrupa los préstamos activos por usuario/empleado responsable"""
        c = get_db('paniol')
        try:
            where_sql = ''
            params = []

            if search:
                search_where, search_params = contains_terms_where(
                    search,
                    ['m.empleado_nombre', "COALESCE(e.numero_identificacion, '')", 'h.nombre', 'h.sku']
                )
                if search_where:
                    where_sql = f'AND ({search_where})'
                    params = search_params

            rows = c.execute(f'''
                SELECT m.id, m.herramienta_id, m.empleado_id, m.empleado_nombre,
                       m.fecha_salida, m.cantidad, h.sku, h.nombre,
                       COALESCE(e.numero_identificacion, '') as numero_identificacion,
                       COALESCE(e.departamento, '') as departamento,
                       COALESCE(e.puesto, '') as puesto
                FROM herramientas_movimientos m
                INNER JOIN herramientas h ON h.id = m.herramienta_id
                LEFT JOIN empleados e ON e.id = m.empleado_id
                WHERE m.fecha_retorno IS NULL
                {where_sql}
                ORDER BY m.empleado_nombre ASC, m.fecha_salida DESC, h.nombre ASC
            ''', params).fetchall()

            hoy = datetime.now()
            usuarios = {}

            for r in rows:
                empleado_key = r[2] if r[2] is not None else f"nombre:{r[3]}"

                try:
                    fecha_salida_dt = datetime.strptime(r[4], '%Y-%m-%d')
                    dias_prestado = (hoy - fecha_salida_dt).days
                except Exception:
                    dias_prestado = 0

                if empleado_key not in usuarios:
                    usuarios[empleado_key] = {
                        'empleado_id': r[2],
                        'empleado_nombre': r[3],
                        'numero_identificacion': r[8],
                        'departamento': r[9],
                        'puesto': r[10],
                        'total_prestamos': 0,
                        'cantidad_total': 0,
                        'desde': r[4],
                        'herramientas': []
                    }

                usuarios[empleado_key]['total_prestamos'] += 1
                usuarios[empleado_key]['cantidad_total'] += r[5] or 0

                if r[4] < usuarios[empleado_key]['desde']:
                    usuarios[empleado_key]['desde'] = r[4]

                usuarios[empleado_key]['herramientas'].append({
                    'movimiento_id': r[0],
                    'herramienta_id': r[1],
                    'fecha_salida': r[4],
                    'cantidad': r[5],
                    'herramienta_sku': r[6],
                    'herramienta_nombre': r[7],
                    'dias_prestado': dias_prestado
                })

            usuarios_list = sorted(
                usuarios.values(),
                key=lambda item: (
                    item['empleado_nombre'] or '',
                    item['numero_identificacion'] or ''
                )
            )

            return {
                'ok': True,
                'usuarios': usuarios_list,
                'total_usuarios': len(usuarios_list),
                'total_prestamos': len(rows)
            }

        except Exception as e:
            logger.error(f"Error obteniendo préstamos por usuario: {e}")
            return {'ok': False, 'msg': str(e)}
        finally:
            c.close()
    
    # =========================================================================
    # ACCIONES AVANZADAS DE PRÉSTAMOS - PROFESIONALES
    # =========================================================================
    
    @staticmethod
    def renovar_prestamo(movimiento_id, dias_extension, observaciones=""):
        """
        Renueva/extiende la fecha de un préstamo activo
        
        Args:
            movimiento_id: ID del movimiento a renovar
            dias_extension: Días a extender (7, 14, 30, etc.)
            observaciones: Motivo o notas de la renovación
        """
        c = get_db('paniol')
        try:
            # Validar movimiento
            movimiento = c.execute('''
                SELECT id, herramienta_id, fecha_salida, fecha_retorno, empleado_nombre
                FROM herramientas_movimientos WHERE id = ?
            ''', [movimiento_id]).fetchone()
            
            if not movimiento:
                return {'ok': False, 'msg': 'Movimiento no encontrado'}
            
            if movimiento[3] is not None:
                return {'ok': False, 'msg': 'Préstamo ya fue devuelto, no se puede renovar'}
            
            if not isinstance(dias_extension, int) or dias_extension <= 0:
                return {'ok': False, 'msg': 'Días de extensión debe ser número positivo'}
            
            # Registrar la renovación como nueva observación
            fecha_ahora = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            observaciones_actual = f"[RENOVACIÓN {fecha_ahora}] +{dias_extension} días. {observaciones}"
            
            c.execute('''
                UPDATE herramientas_movimientos
                SET observaciones_salida = COALESCE(observaciones_salida, '') || '\n' || ?
                WHERE id = ?
            ''', [observaciones_actual, movimiento_id])
            
            c.commit()
            logger.info(f"Préstamo {movimiento_id} renovado por {dias_extension} días")
            
            return {
                'ok': True,
                'msg': f'Préstamo renovado por {dias_extension} días',
                'movimiento_id': movimiento_id,
                'empleado': movimiento[4],
                'dias_extension': dias_extension
            }
            
        except Exception as e:
            logger.error(f"Error renovando préstamo: {e}")
            return {'ok': False, 'msg': str(e)}
        finally:
            c.close()
    
    @staticmethod
    def cambiar_responsable_prestamo(movimiento_id, nuevo_empleado_id, nuevo_empleado_nombre, motivo=""):
        """
        Cambia el empleado responsable de un préstamo activo
        Registra la transferencia de responsabilidad
        
        Args:
            movimiento_id: ID del movimiento
            nuevo_empleado_id: ID del nuevo empleado
            nuevo_empleado_nombre: Nombre del nuevo empleado
            motivo: Motivo del cambio
        """
        c = get_db('paniol')
        try:
            # Validar movimiento
            movimiento = c.execute('''
                SELECT id, herramienta_id, empleado_id, empleado_nombre, cantidad, fecha_salida, fecha_retorno
                FROM herramientas_movimientos WHERE id = ?
            ''', [movimiento_id]).fetchone()
            
            if not movimiento:
                return {'ok': False, 'msg': 'Movimiento no encontrado'}
            
            if movimiento[6] is not None:
                return {'ok': False, 'msg': 'No se puede cambiar responsable de préstamo ya devuelto'}
            
            # Validar nuevo empleado
            nuevo_empleado = None
            if nuevo_empleado_id:
                nuevo_empleado = c.execute(
                    'SELECT id, nombre, estado FROM empleados WHERE id = ?',
                    [nuevo_empleado_id]
                ).fetchone()
                
                if not nuevo_empleado:
                    return {'ok': False, 'msg': 'Nuevo empleado no encontrado'}
                
                if nuevo_empleado[2] != 'activo':
                    return {'ok': False, 'msg': 'Nuevo empleado debe estar activo'}
            
            # Registrar el cambio
            fecha_cambio = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            registro_cambio = f"[CAMBIO RESPONSABLE {fecha_cambio}] De: {movimiento[3]}. A: {nuevo_empleado_nombre}. Motivo: {motivo}"
            
            c.execute('''
                UPDATE herramientas_movimientos
                SET empleado_id = ?, empleado_nombre = ?,
                    observaciones_salida = COALESCE(observaciones_salida, '') || '\n' || ?
                WHERE id = ?
            ''', [nuevo_empleado_id or None, nuevo_empleado_nombre, registro_cambio, movimiento_id])
            
            c.commit()
            logger.info(f"Responsable de préstamo {movimiento_id} cambiado de {movimiento[3]} a {nuevo_empleado_nombre}")
            PaniolService._audit_sensitive(
                action='TRANSFER',
                details=(
                    f"movimiento_id={movimiento_id} responsable_anterior={movimiento[3]} "
                    f"responsable_nuevo={nuevo_empleado_nombre}"
                ),
            )
            
            return {
                'ok': True,
                'msg': f'Responsable cambiado a {nuevo_empleado_nombre}',
                'movimiento_id': movimiento_id,
                'responsable_anterior': movimiento[3],
                'responsable_nuevo': nuevo_empleado_nombre
            }
            
        except Exception as e:
            logger.error(f"Error cambiando responsable: {e}")
            return {'ok': False, 'msg': str(e)}
        finally:
            c.close()
    
    @staticmethod
    # devolucion_parcial se mantiene únicamente por compatibilidad; internamente
    # redirige hacia el método unificado checkin_herramienta.
    def devolucion_parcial(movimiento_id, cantidad_devuelta, estado_devoluciones, observaciones_devoluciones):
        """
        Alias obsoleto. Utiliza :func:`checkin_herramienta` para manejar devoluciones
        totales y parciales bajo el mismo concepto.
        """
        return PaniolService.checkin_herramienta(
            movimiento_id,
            estado_devoluciones,
            observaciones_devoluciones,
            cantidad_devuelta
        )
    
    @staticmethod
    def obtener_prestamos_vencidos(dias_limite=30):
        """
        Obtiene préstamos activos que exceden los días límite sin devolución
        
        Args:
            dias_limite: Días máximos permitidos (default 30)
        """
        c = get_db('paniol')
        try:
            hoy = datetime.now()
            fecha_limite = (hoy - timedelta(days=dias_limite)).strftime('%Y-%m-%d')
            
            rows = c.execute('''
                SELECT m.id, m.herramienta_id, m.empleado_id, m.empleado_nombre,
                       m.fecha_salida, m.cantidad, h.sku, h.nombre,
                       CAST((julianday(?) - julianday(m.fecha_salida)) AS INTEGER) as dias_vencidos
                FROM herramientas_movimientos m
                INNER JOIN herramientas h ON m.herramienta_id = h.id
                WHERE m.fecha_retorno IS NULL AND m.fecha_salida <= ?
                ORDER BY m.fecha_salida ASC
            ''', [hoy.strftime('%Y-%m-%d'), fecha_limite]).fetchall()
            
            prestamos_vencidos = []
            for r in rows:
                prestamos_vencidos.append({
                    'movimiento_id': r[0],
                    'herramienta_id': r[1],
                    'empleado_id': r[2],
                    'empleado_nombre': r[3],
                    'fecha_salida': r[4],
                    'cantidad': r[5],
                    'herramienta_sku': r[6],
                    'herramienta_nombre': r[7],
                    'dias_vencidos': r[8],
                    'nivel_alerta': 'critico' if r[8] > dias_limite * 2 else 'alto' if r[8] > dias_limite else 'medio'
                })
            
            return {
                'ok': True,
                'prestamos_vencidos': prestamos_vencidos,
                'total': len(prestamos_vencidos),
                'dias_limite': dias_limite
            }
            
        except Exception as e:
            logger.error(f"Error obteniendo préstamos vencidos: {e}")
            return {'ok': False, 'msg': str(e)}
        finally:
            c.close()
    
    @staticmethod
    def registrar_observacion_prestamo(movimiento_id, observacion_nueva, tipo="general"):
        """
        Agrega una observación/nota a un préstamo activo
        Útil para seguimiento profesional y auditoría
        
        Args:
            movimiento_id: ID del movimiento
            observacion_nueva: Texto de la observación
            tipo: Tipo de observación ('general', 'requerimiento', 'incidencia', 'visita', etc)
        """
        c = get_db('paniol')
        try:
            # Validar movimiento
            movimiento = c.execute('''
                SELECT id, fecha_retorno FROM herramientas_movimientos WHERE id = ?
            ''', [movimiento_id]).fetchone()
            
            if not movimiento:
                return {'ok': False, 'msg': 'Movimiento no encontrado'}
            
            if movimiento[1] is not None:
                return {'ok': False, 'msg': 'No se pueden agregar observaciones a préstamo devuelto'}
            
            # Agregar observación con timestamp y tipo
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            registro = f"[{timestamp}] [{tipo.upper()}] {observacion_nueva}"
            
            c.execute('''
                UPDATE herramientas_movimientos
                SET observaciones_salida = COALESCE(observaciones_salida, '') || 
                    CASE WHEN observaciones_salida IS NULL THEN '' ELSE '\n' END || ?
                WHERE id = ?
            ''', [registro, movimiento_id])
            
            c.commit()
            logger.info(f"Observación registrada en movimiento {movimiento_id}")
            
            return {
                'ok': True,
                'msg': 'Observación registrada correctamente',
                'movimiento_id': movimiento_id,
                'tipo': tipo
            }
            
        except Exception as e:
            logger.error(f"Error registrando observación: {e}")
            return {'ok': False, 'msg': str(e)}
        finally:
            c.close()
    
    @staticmethod
    def obtener_historial_prestamo_completo(movimiento_id):
        """
        Obtiene el historial completo de un movimiento de préstamo
        Incluye: datos del movimiento, herramienta, empleado y todas las observaciones
        """
        c = get_db('paniol')
        try:
            # Datos del movimiento
            movimiento = c.execute('''
                SELECT m.id, m.herramienta_id, m.empleado_id, m.empleado_nombre,
                       m.fecha_salida, m.fecha_retorno, m.cantidad, m.estado_salida,
                       m.estado_retorno, m.observaciones_salida, m.observaciones_retorno,
                       m.orden_trabajo_id, m.usuario_registro, m.fecha_registro,
                       h.sku, h.nombre, h.modelo, h.condicion,
                       e.numero_identificacion, e.departamento, e.puesto
                FROM herramientas_movimientos m
                INNER JOIN herramientas h ON m.herramienta_id = h.id
                LEFT JOIN empleados e ON m.empleado_id = e.id
                WHERE m.id = ?
            ''', [movimiento_id]).fetchone()
            
            if not movimiento:
                return {'ok': False, 'msg': 'Movimiento no encontrado'}
            
            # Calcular días
            fecha_salida = datetime.strptime(movimiento[4], '%Y-%m-%d')
            if movimiento[5]:
                fecha_retorno = datetime.strptime(movimiento[5], '%Y-%m-%d')
                dias_prestamo = (fecha_retorno - fecha_salida).days
                dias_pendiente = None
            else:
                dias_prestamo = (datetime.now() - fecha_salida).days
                dias_pendiente = dias_prestamo
            
            return {
                'ok': True,
                'movimiento': {
                    'id': movimiento[0],
                    'herramienta_id': movimiento[1],
                    'empleado_id': movimiento[2],
                    'empleado_nombre': movimiento[3],
                    'fecha_salida': movimiento[4],
                    'fecha_retorno': movimiento[5],
                    'cantidad': movimiento[6],
                    'estado_salida': movimiento[7],
                    'estado_retorno': movimiento[8],
                    'observaciones_salida': movimiento[9],
                    'observaciones_retorno': movimiento[10],
                    'orden_trabajo_id': movimiento[11],
                    'usuario_registro': movimiento[12],
                    'fecha_registro': movimiento[13],
                },
                'herramienta': {
                    'sku': movimiento[14],
                    'nombre': movimiento[15],
                    'modelo': movimiento[16],
                    'condicion': movimiento[17]
                },
                'empleado': {
                    'nombre': movimiento[3],
                    'numero_identificacion': movimiento[18],
                    'departamento': movimiento[19],
                    'puesto': movimiento[20]
                },
                'duracion': {
                    'dias_prestamo': dias_prestamo,
                    'dias_pendiente': dias_pendiente,
                    'estado': 'devuelto' if movimiento[5] else 'activo'
                }
            }
            
        except Exception as e:
            logger.error(f"Error obteniendo historial: {e}")
            return {'ok': False, 'msg': str(e)}
        finally:
            c.close()
    
    # =========================================================================
    # ESTADÍSTICAS Y REPORTES
    # =========================================================================
    
    @staticmethod
    def obtener_estadisticas():
        """Obtiene estadísticas globales del pañol"""
        c = get_db('paniol')
        try:
            # Stats por condición
            stats_condicion = c.execute('''
                SELECT condicion, COUNT(*) as total
                FROM herramientas GROUP BY condicion
            ''').fetchall()
            
            # Préstamos activos
            prestamos_activos = c.execute('''
                SELECT COUNT(*) FROM herramientas_movimientos
                WHERE fecha_retorno IS NULL
            ''').fetchone()[0]
            
            # Calibraciones vencidas
            hoy = datetime.now().strftime('%Y-%m-%d')
            calibraciones_vencidas = c.execute('''
                SELECT COUNT(*) FROM herramientas
                WHERE requiere_calibracion = 1
                AND (
                    ultima_calibracion IS NULL
                    OR date(ultima_calibracion, '+' || frecuencia_calibracion_dias || ' days') < date(?)
                )
            ''', [hoy]).fetchone()[0]
            
            # Mantenimientos vencidos
            mantenimientos_vencidos = c.execute('''
                SELECT COUNT(DISTINCT h.id)
                FROM herramientas h
                LEFT JOIN herramientas_mantenimiento m ON h.id = m.herramienta_id
                WHERE m.proxima_fecha IS NOT NULL
                AND m.proxima_fecha < date(?)
                AND m.id = (
                    SELECT id FROM herramientas_mantenimiento
                    WHERE herramienta_id = h.id
                    ORDER BY fecha_mantenimiento DESC LIMIT 1
                )
            ''', [hoy]).fetchone()[0]
            
            total_herramientas = c.execute(
                'SELECT COUNT(*) FROM herramientas'
            ).fetchone()[0]
            
            # Construir respuesta
            condiciones = {r[0]: r[1] for r in stats_condicion}
            
            return {
                'total_herramientas': total_herramientas,
                'por_condicion': condiciones,
                'prestamos_activos': prestamos_activos,
                'calibraciones_vencidas': calibraciones_vencidas,
                'mantenimientos_vencidos': mantenimientos_vencidos,
                'operativas': condiciones.get('operativa', 0),
                'en_mantenimiento': condiciones.get('mantenimiento', 0),
                'defectuosas': condiciones.get('defectuosa', 0),
                'dadas_baja': condiciones.get('baja', 0)
            }
            
        except Exception as e:
            logger.error(f"Error obteniendo estadísticas: {e}")
            return {'ok': False, 'msg': str(e)}
        finally:
            c.close()
    
    # =========================================================================
    # UTILIDADES PRIVADAS
    # =========================================================================
    
    @staticmethod
    def _mapear_herramienta(row):
        """Mapea row de DB a dict de herramienta"""
        hoy = datetime.now()
        calibracion_vencida_flag = False
        dias_vencimiento = None
        proxima_calibracion = None
        
        if row[12] and row[13] and row[14]:  # requiere_calibracion, frecuencia, ultima_calibracion
            try:
                ultima = datetime.strptime(row[14], '%Y-%m-%d')
                proxima = ultima + timedelta(days=row[13])
                proxima_calibracion = proxima.strftime('%Y-%m-%d')
                
                if proxima < hoy:
                    calibracion_vencida_flag = True
                    dias_vencimiento = (hoy - proxima).days
            except:
                pass
        
        return {
            'id': row[0],
            'sku': row[1],
            'nombre': row[2],
            'categoria': row[3],
            'subcategoria': row[4],
            'numero_serie': row[5],
            'modelo': row[6],
            'fabricante': row[7],
            'ubicacion': row[8],
            'condicion': row[9],
            'fecha_adquisicion': row[10],
            'precio_unitario': row[11] or 0,
            'requiere_calibracion': bool(row[12]),
            'frecuencia_calibracion_dias': row[13],
            'ultima_calibracion': row[14],
            'proxima_calibracion': proxima_calibracion,
            'calibracion_vencida': calibracion_vencida_flag,
            'dias_vencimiento_calibracion': dias_vencimiento,
            'certificado_calibracion': row[15],
            'observaciones': row[16],
            'cantidad_total': row[17] or 1,
            'cantidad_disponible': row[18] or 1,
            'fecha_creacion': row[19]
        }
