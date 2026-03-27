"""
API endpoints para sistema de mantenimiento profesional con fotos comprimidas.
Incluye registro completo de mantenimientos, carga de fotos y reportes.
"""
from flask import Blueprint, request, jsonify, send_file
from app.db import get_db
from app.services.compresor_fotos import CompresorFotos
from logger_config import logger
from datetime import datetime, timedelta
import base64
import io

bp = Blueprint('mantenimiento', __name__, url_prefix='/api/mantenimiento')


# ========================================================================
# ENDPOINTS DE MANTENIMIENTO PROFESIONAL
# ========================================================================

@bp.route('/registrar-completo/<int:herramienta_id>', methods=['POST'], strict_slashes=False)
def api_registrar_mantenimiento_completo(herramienta_id):
    """
    Registra un mantenimiento completo con fotos, documentos y seguimiento.
    
    JSON body:
    {
        "tipo": "preventivo|correctivo|calibracion",
        "descripcion": "...",
        "fecha_mantenimiento": "YYYY-MM-DD",
        "responsable_nombre": "Juan Pérez",
        "tecnico_nombre": "Carlos López",
        "taller_nombre": "Taller Central",
        "numero_orden_trabajo": "OT-2026-001",
        "presupuesto": 150000,
        "tiempo_estimado_horas": 3.5,
        "tiempo_real_horas": 2.5,
        "proveedor_nombre": "Mecánica Industrial S.A.",
        "costo_final": 125000,
        "proxima_fecha": "2026-04-15",
        "observaciones": "Revisión general completada",
        "nota_interna": "Cliente solicitó cambio de aceite adicional"
    }
    """
    c = get_db()
    try:
        # Validar herramienta existe
        h = c.execute(
            'SELECT id, nombre FROM herramientas WHERE id = ?',
            [herramienta_id]
        ).fetchone()
        
        if not h:
            return jsonify({'ok': False, 'msg': 'Herramienta no encontrada'}), 404
        
        data = request.json or {}
        
        # Validar campos requeridos
        campos_requeridos = ['tipo', 'descripcion', 'fecha_mantenimiento', 'responsable_nombre']
        if not all(data.get(c) for c in campos_requeridos):
            return jsonify({'ok': False, 'msg': 'Campos requeridos faltantes'}), 400
        
        if data['tipo'] not in ['preventivo', 'correctivo', 'calibracion']:
            return jsonify({'ok': False, 'msg': 'Tipo de mantenimiento inválido'}), 400
        
        # Insertar registro de mantenimiento
        cursor = c.execute('''
            INSERT INTO herramientas_mantenimiento (
                herramienta_id, fecha_mantenimiento, tipo, descripcion,
                responsable_nombre, tecnico_nombre, taller_nombre,
                numero_orden_trabajo, presupuesto, costo_final,
                tiempo_estimado_horas, tiempo_real_horas,
                proveedor_nombre, proxima_fecha, observaciones,
                nota_interna, estado_mant, usuario_registro
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', [
            herramienta_id,
            data.get('fecha_mantenimiento'),
            data.get('tipo'),
            data.get('descripcion'),
            data.get('responsable_nombre'),
            data.get('tecnico_nombre'),
            data.get('taller_nombre'),
            data.get('numero_orden_trabajo'),
            data.get('presupuesto', 0),
            data.get('costo_final', 0),
            data.get('tiempo_estimado_horas', 0),
            data.get('tiempo_real_horas', 0),
            data.get('proveedor_nombre'),
            data.get('proxima_fecha'),
            data.get('observaciones'),
            data.get('nota_interna'),
            'completado',  # Estado por defecto
            'api'
        ])
        
        mantenimiento_id = cursor.lastrowid
        
        # Actualizar estado de herramienta si es correctivo
        if data['tipo'] == 'correctivo':
            c.execute('UPDATE herramientas SET condicion = ? WHERE id = ?', ['operativa', herramienta_id])
        
        # Actualizar calibración si aplica
        if data['tipo'] == 'calibracion':
            c.execute('''
                UPDATE herramientas
                SET ultima_calibracion = ?, requiere_calibracion = 0
                WHERE id = ?
            ''', [data.get('fecha_mantenimiento'), herramienta_id])
        
        c.commit()
        
        logger.info(f"Mantenimiento #{mantenimiento_id} registrado para herramienta #{herramienta_id}")
        
        return jsonify({
            'ok': True,
            'msg': 'Mantenimiento registrado correctamente',
            'mantenimiento_id': mantenimiento_id,
            'herramienta': {'id': h[0], 'nombre': h[1]}
        }), 201
    
    except Exception as e:
        logger.error(f"Error registrando mantenimiento completo: {e}")
        return jsonify({'ok': False, 'msg': str(e)}), 500
    finally:
        c.close()


@bp.route('/agregar-foto/<int:mantenimiento_id>', methods=['POST'], strict_slashes=False)
def api_agregar_foto_mantenimiento(mantenimiento_id):
    """
    Agrega una foto comprimida a un mantenimiento.
    
    Multipart form-data:
    - foto: Archivo de imagen
    - tipo_foto: 'antes|durante|despues|documentacion'
    - descripcion: (opcional) Descripción de la foto
    """
    c = get_db()
    try:
        # Verificar que el mantenimiento existe
        mant = c.execute('''
            SELECT id, herramienta_id FROM herramientas_mantenimiento WHERE id = ?
        ''', [mantenimiento_id]).fetchone()
        
        if not mant:
            return jsonify({'ok': False, 'msg': 'Mantenimiento no encontrado'}), 404
        
        herramienta_id = mant[1]
        
        # Verificar tipo_foto
        tipo_foto = request.form.get('tipo_foto', 'documentacion')
        if tipo_foto not in ['antes', 'durante', 'despues', 'documentacion']:
            return jsonify({'ok': False, 'msg': 'Tipo de foto inválido'}), 400
        
        # Obtener archivo
        if 'foto' not in request.files:
            return jsonify({'ok': False, 'msg': 'No se encontró archivo de foto'}), 400
        
        archivo = request.files['foto']
        if archivo.filename == '':
            return jsonify({'ok': False, 'msg': 'Archivo vacío'}), 400
        
        # Leer bytes del archivo
        archivo_bytes = archivo.read()
        
        # Comprimir imagen
        resultado = CompresorFotos.comprimir_imagen(archivo_bytes, tipo_foto)
        
        if not resultado['ok']:
            return jsonify({
                'ok': False,
                'msg': resultado.get('mensaje', 'Error comprimiendo imagen')
            }), 400
        
        # Guardar en BD
        cursor = c.execute('''
            INSERT INTO herramientas_mantenimiento_fotos (
                mantenimiento_id, herramienta_id,
                nombre_original, tipo_foto, descripcion,
                foto_blob, tamaño_kb, ancho, alto,
                formato, usuario_uploaded
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', [
            mantenimiento_id,
            herramienta_id,
            archivo.filename,
            tipo_foto,
            request.form.get('descripcion', ''),
            resultado['foto_blob'],
            resultado['tamaño_kb'],
            resultado['ancho'],
            resultado['alto'],
            resultado['formato'],
            'api_upload'
        ])
        
        foto_id = cursor.lastrowid
        
        # Actualizar contador en mantenimiento
        c.execute('''
            UPDATE herramientas_mantenimiento
            SET cantidad_fotos = (
                SELECT COUNT(*) FROM herramientas_mantenimiento_fotos
                WHERE mantenimiento_id = ?
            )
            WHERE id = ?
        ''', [mantenimiento_id, mantenimiento_id])
        
        c.commit()
        
        logger.info(f"Foto agregada al mantenimiento #{mantenimiento_id}: {resultado['tamaño_kb']}KB")
        
        return jsonify({
            'ok': True,
            'msg': 'Foto guardada correctamente',
            'foto_id': foto_id,
            'estadisticas': {
                'tamaño_original_kb': resultado['tamaño_original_kb'],
                'tamaño_comprimido_kb': resultado['tamaño_kb'],
                'ratio_reduccion': f"{resultado['ratio_reduccion']}%",
                'dimensiones': f"{resultado['ancho']}x{resultado['alto']}"
            }
        }), 201
    
    except Exception as e:
        logger.error(f"Error agregando foto: {e}")
        return jsonify({'ok': False, 'msg': str(e)}), 500
    finally:
        c.close()


@bp.route('/foto/<int:foto_id>', methods=['GET'], strict_slashes=False)
def api_obtener_foto(foto_id):
    """Obtiene la foto comprimida para mostrar"""
    c = get_db()
    try:
        foto = c.execute('''
            SELECT foto_blob, formato, ancho, alto
            FROM herramientas_mantenimiento_fotos
            WHERE id = ?
        ''', [foto_id]).fetchone()
        
        if not foto:
            return jsonify({'ok': False, 'msg': 'Foto no encontrada'}), 404
        
        # Determinar mimetype
        mimetype_map = {
            'webp': 'image/webp',
            'jpeg': 'image/jpeg',
            'jpg': 'image/jpeg',
            'png': 'image/png'
        }
        
        mimetype = mimetype_map.get(foto[1], 'image/webp')
        
        return send_file(
            io.BytesIO(foto[0]),
            mimetype=mimetype,
            as_attachment=False,
            download_name=f'foto_{foto_id}.{foto[1]}'
        )
    
    except Exception as e:
        logger.error(f"Error obteniendo foto: {e}")
        return jsonify({'ok': False, 'msg': str(e)}), 500
    finally:
        c.close()


@bp.route('/fotos/<int:mantenimiento_id>', methods=['GET'], strict_slashes=False)
def api_listar_fotos_mantenimiento(mantenimiento_id):
    """Obtiene todas las fotos de un mantenimiento (con miniaturas en base64)"""
    c = get_db()
    try:
        fotos = c.execute('''
            SELECT id, nombre_original, tipo_foto, descripcion,
                   tamaño_kb, ancho, alto, formato, fecha_uploaded,
                   foto_blob
            FROM herramientas_mantenimiento_fotos
            WHERE mantenimiento_id = ?
            ORDER BY tipo_foto, fecha_uploaded DESC
        ''', [mantenimiento_id]).fetchall()
        
        resultado = []
        for foto in fotos:
            # Generar miniatura base64
            miniatura = CompresorFotos.obtener_miniatura(foto[9], (150, 150))
            miniatura_b64 = base64.b64encode(miniatura).decode() if miniatura else None
            
            resultado.append({
                'id': foto[0],
                'nombre': foto[1],
                'tipo': foto[2],
                'descripcion': foto[3],
                'tamaño_kb': foto[4],
                'dimensiones': f"{foto[5]}x{foto[6]}",
                'formato': foto[7],
                'fecha': foto[8],
                'miniatura_b64': miniatura_b64,
                'url_completa': f'/api/mantenimiento/foto/{foto[0]}'
            })
        
        return jsonify({
            'ok': True,
            'cantidad': len(resultado),
            'fotos': resultado
        })
    
    except Exception as e:
        logger.error(f"Error listando fotos: {e}")
        return jsonify({'ok': False, 'msg': str(e)}), 500
    finally:
        c.close()


@bp.route('/detalle/<int:mantenimiento_id>', methods=['GET'], strict_slashes=False)
def api_detalle_mantenimiento(mantenimiento_id):
    """Obtiene detalle completo del mantenimiento con fotos y estadísticas"""
    c = get_db()
    try:
        mant = c.execute('''
            SELECT id, herramienta_id, fecha_mantenimiento, tipo,
                   descripcion, responsable_nombre, tecnico_nombre,
                   taller_nombre, numero_orden_trabajo, presupuesto,
                   costo_final, tiempo_estimado_horas, tiempo_real_horas,
                   proveedor_nombre, proxima_fecha, observaciones,
                   nota_interna, estado_mant, cantidad_fotos, cantidad_documentos,
                   fecha_registro
            FROM herramientas_mantenimiento
            WHERE id = ?
        ''', [mantenimiento_id]).fetchone()
        
        if not mant:
            return jsonify({'ok': False, 'msg': 'Mantenimiento no encontrado'}), 404
        
        # Obtener info de herramienta
        herr = c.execute(
            'SELECT nombre, sku FROM herramientas WHERE id = ?',
            [mant[1]]
        ).fetchone()
        
        # Obtener fotos (solo metadatos)
        fotos = c.execute('''
            SELECT id, tipo_foto, tamaño_kb
            FROM herramientas_mantenimiento_fotos
            WHERE mantenimiento_id = ?
        ''', [mantenimiento_id]).fetchall()
        
        # Calcular estadísticas de ahorro de espacio
        tamaño_total_fotos = sum(f[2] for f in fotos) if fotos else 0
        
        return jsonify({
            'ok': True,
            'mantenimiento': {
                'id': mant[0],
                'herramienta': {'id': mant[1], 'nombre': herr[0] if herr else '', 'sku': herr[1] if herr else ''},
                'tipo': mant[3],
                'descripcion': mant[4],
                'fecha': mant[2],
                'responsable': mant[5],
                'tecnico': mant[6],
                'taller': mant[7],
                'numero_orden': mant[8],
                'presupuesto': mant[9],
                'costo_final': mant[10],
                'tiempo_estimado': mant[11],
                'tiempo_real': mant[12],
                'proveedor': mant[13],
                'proxima_fecha': mant[14],
                'observaciones': mant[15],
                'nota_interna': mant[16],
                'estado': mant[17],
                'cantidad_fotos': mant[18],
                'cantidad_documentos': mant[19],
                'fecha_registro': mant[20],
            },
            'fotos': [
                {'id': f[0], 'tipo': f[1], 'tamaño_kb': f[2]}
                for f in fotos
            ],
            'estadisticas': {
                'tamaño_total_fotos_kb': round(tamaño_total_fotos, 2),
                'costo_diferencia': (mant[9] - mant[10]) if mant[9] and mant[10] else None,
                'eficiencia_tiempo': ((mant[11] - mant[12]) / mant[11] * 100) if mant[11] and mant[12] and mant[11] > 0 else None,
            }
        })
    
    except Exception as e:
        logger.error(f"Error obteniendo detalle mantenimiento: {e}")
        return jsonify({'ok': False, 'msg': str(e)}), 500
    finally:
        c.close()


@bp.route('/historial/<int:herramienta_id>', methods=['GET'], strict_slashes=False)
def api_historial_mantenimientos(herramienta_id):
    """
    Obtiene historial completo de mantenimientos de una herramienta.
    Query params:
    - tipo: Filtrar por tipo (preventivo|correctivo|calibracion)
    - limit: Cantidad de registros (default 50)
    - offset: Paginación (default 0)
    """
    c = get_db()
    try:
        # Validar herramienta
        h = c.execute('SELECT id, nombre FROM herramientas WHERE id = ?', [herramienta_id]).fetchone()
        if not h:
            return jsonify({'ok': False, 'msg': 'Herramienta no encontrada'}), 404
        
        # Filtros
        tipo_filtro = request.args.get('tipo')
        limit = int(request.args.get('limit', 50))
        offset = int(request.args.get('offset', 0))
        
        query = '''
            SELECT id, fecha_mantenimiento, tipo, descripcion,
                   responsable_nombre, costo_final, proxima_fecha, cantidad_fotos
            FROM herramientas_mantenimiento
            WHERE herramienta_id = ?
        '''
        params = [herramienta_id]
        
        if tipo_filtro and tipo_filtro in ['preventivo', 'correctivo', 'calibracion']:
            query += ' AND tipo = ?'
            params.append(tipo_filtro)
        
        query += ' ORDER BY fecha_mantenimiento DESC LIMIT ? OFFSET ?'
        params.extend([limit, offset])
        
        mantenimientos = c.execute(query, params).fetchall()
        
        # Convertir a dict
        resultado = []
        for m in mantenimientos:
            resultado.append({
                'id': m[0],
                'fecha': m[1],
                'tipo': m[2],
                'descripcion': m[3],
                'responsable': m[4],
                'costo': m[5] or 0,
                'proxima_fecha': m[6],
                'cantidad_fotos': m[7] or 0,
            })
        
        return jsonify({
            'ok': True,
            'herramienta': {'id': h[0], 'nombre': h[1]},
            'total': len(resultado),
            'mantenimientos': resultado
        })
    
    except Exception as e:
        logger.error(f"Error obteniendo historial: {e}")
        return jsonify({'ok': False, 'msg': str(e)}), 500
    finally:
        c.close()


@bp.route('/alertas-vencimiento', methods=['GET'], strict_slashes=False)
def api_alertas_vencimiento_calibracion():
    """
    Obtiene alertas de herramientas que vencen calibración próximamente.
    Query params:
    - dias: Días para buscar (default 30)
    """
    c = get_db()
    try:
        dias = int(request.args.get('dias', 30))
        fecha_limite = (datetime.now() + timedelta(days=dias)).strftime('%Y-%m-%d')
        
        alertas = c.execute('''
            SELECT id, sku, nombre, ultima_calibracion, 
                   frecuencia_calibracion_dias, condicion
            FROM herramientas
            WHERE requiere_calibracion = 1
            AND (
                ultima_calibracion IS NULL
                OR date(ultima_calibracion, '+' || frecuencia_calibracion_dias || ' days') <= ?
            )
            ORDER BY ultima_calibracion ASC
        ''', [fecha_limite]).fetchall()
        
        resultado = []
        for a in alertas:
            dias_vencido = None
            if a[3]:  # ultima_calibracion
                if a[4]:  # frecuencia_calibracion_dias
                    fecha_vencimiento = datetime.strptime(a[3], '%Y-%m-%d') + timedelta(days=a[4])
                    dias_vencido = (datetime.now() - fecha_vencimiento).days
            
            resultado.append({
                'herramienta_id': a[0],
                'sku': a[1],
                'nombre': a[2],
                'ultima_calibracion': a[3],
                'frecuencia_dias': a[4],
                'estado': a[5],
                'dias_vencido': dias_vencido,
                'urgencia': 'crítica' if dias_vencido and dias_vencido > 0 else 'próxima'
            })
        
        return jsonify({
            'ok': True,
            'cantidad_alertas': len(resultado),
            'alertas': resultado
        })
    
    except Exception as e:
        logger.error(f"Error obteniendo alertas: {e}")
        return jsonify({'ok': False, 'msg': str(e)}), 500
    finally:
        c.close()


@bp.route('/reporte-costos', methods=['GET'], strict_slashes=False)
def api_reporte_costos_mantenimiento():
    """
    Genera reporte de costos de mantenimiento.
    Query params:
    - desde: Fecha inicio (YYYY-MM-DD)
    - hasta: Fecha fin (YYYY-MM-DD)
    - tipo: Filtrar por tipo
    """
    c = get_db()
    try:
        desde = request.args.get('desde', '2026-01-01')
        hasta = request.args.get('hasta', '2026-12-31')
        tipo_filtro = request.args.get('tipo')
        
        query = '''
            SELECT herramienta_id, tipo, COUNT(*) as cantidad,
                   SUM(costo_final) as costo_total, AVG(costo_final) as costo_promedio,
                   SUM(tiempo_real_horas) as horas_total
            FROM herramientas_mantenimiento
            WHERE fecha_mantenimiento BETWEEN ? AND ?
        '''
        params = [desde, hasta]
        
        if tipo_filtro:
            query += ' AND tipo = ?'
            params.append(tipo_filtro)
        
        query += ' GROUP BY herramienta_id, tipo ORDER BY costo_total DESC'
        
        resultados = c.execute(query, params).fetchall()
        
        reporte = []
        total_general = 0
        
        for r in resultados:
            herr = c.execute('SELECT nombre, sku FROM herramientas WHERE id = ?', [r[0]]).fetchone()
            costo = r[4] if r[4] else 0
            total_general += r[3] if r[3] else 0
            
            reporte.append({
                'herramienta': herr[0] if herr else f'ID{r[0]}',
                'sku': herr[1] if herr else '',
                'tipo': r[1],
                'cantidad': r[2],
                'costo_total': r[3] if r[3] else 0,
                'costo_promedio': round(costo, 2),
                'horas': r[5] if r[5] else 0
            })
        
        return jsonify({
            'ok': True,
            'periodo': {'desde': desde, 'hasta': hasta},
            'costo_total': total_general,
            'cantidad_registros': len(reporte),
            'reporte': reporte
        })
    
    except Exception as e:
        logger.error(f"Error generando reporte de costos: {e}")
        return jsonify({'ok': False, 'msg': str(e)}), 500
    finally:
        c.close()
