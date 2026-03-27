"""
Tests para el módulo del Pañol
Pruebas de empleados, herramientas, préstamos y mantenimiento
"""
import pytest
import json
from datetime import datetime, timedelta

def test_empleados_list(client):
    """Test listar empleados con paginación"""
    response = client.get('/api/empleados')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert 'empleados' in data
    assert 'total' in data
    assert 'page' in data

def test_empleados_create(client):
    """Test crear nuevo empleado"""
    nuevo_empleado = {
        'numero_identificacion': 'TEST001',
        'nombre': 'Juan Pérez Test',
        'email': 'juan.test@empresa.cl',
        'puesto': 'Técnico',
        'departamento': 'Mantención',
        'telefono': '+56912345678',
        'estado': 'activo'
    }
    
    response = client.post('/api/empleados',
                          data=json.dumps(nuevo_empleado),
                          content_type='application/json')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['ok'] is True
    assert 'id' in data

def test_empleados_suggest_numero(client):
    """Test sugerir próximo número de empleado"""
    response = client.get('/api/empleados/suggest-numero')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert 'numero' in data
    # El formato puede variar, solo verificar que existe

def test_empleados_get_by_id(client):
    """Test obtener empleado por ID"""
    # Primero crear un empleado
    nuevo = {
        'numero_identificacion': 'TEST002',
        'nombre': 'María Test',
        'puesto': 'Operario',
        'estado': 'activo'
    }
    create_response = client.post('/api/empleados',
                                 data=json.dumps(nuevo),
                                 content_type='application/json')
    emp_id = json.loads(create_response.data)['id']
    
    # Obtener el empleado
    response = client.get(f'/api/empleados/{emp_id}')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['empleado']['nombre'] == 'María Test'

def test_empleados_update(client):
    """Test actualizar empleado"""
    # Crear empleado
    nuevo = {
        'numero_identificacion': 'TEST003',
        'nombre': 'Pedro Test',
        'estado': 'activo'
    }
    create_response = client.post('/api/empleados',
                                 data=json.dumps(nuevo),
                                 content_type='application/json')
    emp_id = json.loads(create_response.data)['id']
    
    # Actualizar
    update_data = {
        'numero_identificacion': 'TEST003',
        'nombre': 'Pedro Test Actualizado',
        'puesto': 'Supervisor',
        'estado': 'activo'
    }
    response = client.put(f'/api/empleados/{emp_id}',
                         data=json.dumps(update_data),
                         content_type='application/json')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['ok'] is True

def test_empleados_delete(client):
    """Test eliminar empleado"""
    # Crear empleado
    nuevo = {
        'numero_identificacion': 'TEST004',
        'nombre': 'Ana Test',
        'estado': 'activo'
    }
    create_response = client.post('/api/empleados',
                                 data=json.dumps(nuevo),
                                 content_type='application/json')
    emp_id = json.loads(create_response.data)['id']
    
    # Eliminar
    response = client.delete(f'/api/empleados/{emp_id}')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['ok'] is True

def test_herramientas_list(client):
    """Test listar herramientas con paginación"""
    response = client.get('/api/herramientas')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert 'herramientas' in data
    assert 'total' in data

def test_herramientas_create(client):
    """Test crear nueva herramienta"""
    nueva_herramienta = {
        'sku': 'HERR-TEST-001',
        'nombre': 'Taladro Test',
        'categoria_nombre': 'Herramientas Eléctricas',
        'fabricante': 'Bosch',
        'modelo': 'GSB 13 RE',
        'cantidad_total': 5,
        'cantidad_disponible': 5,
        'ubicacion_nombre': 'Pañol A-01',
        'condicion': 'operativa',
        'precio_unitario': 85000,
        'requiere_calibracion': 0
    }
    
    response = client.post('/api/herramientas',
                          data=json.dumps(nueva_herramienta),
                          content_type='application/json')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['ok'] is True
    assert 'id' in data

def test_herramientas_suggest_sku(client):
    """Test sugerir próximo SKU"""
    response = client.get('/api/herramientas/suggest-sku')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert 'sku' in data
    assert data['sku'].startswith('NC-')  # Prefijo automático North Chrome

def test_herramientas_stats(client):
    """Test obtener estadísticas de herramientas"""
    response = client.get('/api/herramientas/stats')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert 'total_herramientas' in data
    assert 'operativas' in data
    assert 'prestamos_activos' in data
    assert 'calibraciones_vencidas' in data

def test_herramientas_search(client):
    """Test buscar herramientas"""
    # Primero crear una herramienta
    nueva = {
        'sku': 'HERR-SEARCH-001',
        'nombre': 'Martillo de Búsqueda',
        'cantidad_total': 3,
        'cantidad_disponible': 3,
        'condicion': 'operativa',
        'requiere_calibracion': 0
    }
    client.post('/api/herramientas',
                data=json.dumps(nueva),
                content_type='application/json')
    
    # Buscar
    response = client.get('/api/herramientas/search?q=Búsqueda')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert 'herramientas' in data
    assert len(data['herramientas']) > 0

def test_checkout_herramientas(client):
    """Test préstamo de herramientas (checkout)"""
    # Crear empleado
    empleado = {
        'numero_identificacion': 'EMP-CHECKOUT-01',
        'nombre': 'Empleado Checkout Test',
        'estado': 'activo'
    }
    emp_response = client.post('/api/empleados',
                               data=json.dumps(empleado),
                               content_type='application/json')
    
    # Crear herramienta
    herramienta = {
        'sku': 'HERR-CHECKOUT-001',
        'nombre': 'Herramienta para Checkout',
        'cantidad_total': 10,
        'cantidad_disponible': 10,
        'condicion': 'operativa',
        'requiere_calibracion': 0
    }
    herr_response = client.post('/api/herramientas',
                                data=json.dumps(herramienta),
                                content_type='application/json')
    herr_id = json.loads(herr_response.data)['id']
    
    # Hacer checkout
    checkout_data = {
        'fecha': datetime.now().strftime('%Y-%m-%d'),
        'empleado': 'EMP-CHECKOUT-01',
        'observaciones': 'Test de préstamo',
        'herramientas': [
            {
                'herramienta_id': herr_id,
                'cantidad': 2
            }
        ]
    }
    
    response = client.post('/api/herramientas/checkout',
                          data=json.dumps(checkout_data),
                          content_type='application/json')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['ok'] is True


def test_prestamos_por_usuario(client):
    """Test préstamos activos agrupados por usuario"""
    empleado = {
        'numero_identificacion': 'EMP-GRUPO-01',
        'nombre': 'Usuario Agrupado',
        'estado': 'activo'
    }
    client.post('/api/empleados',
                data=json.dumps(empleado),
                content_type='application/json')

    herramienta_1 = {
        'sku': 'HERR-GRUPO-001',
        'nombre': 'Llave Grupo 1',
        'cantidad_total': 3,
        'cantidad_disponible': 3,
        'condicion': 'operativa',
        'requiere_calibracion': 0
    }
    herramienta_2 = {
        'sku': 'HERR-GRUPO-002',
        'nombre': 'Llave Grupo 2',
        'cantidad_total': 2,
        'cantidad_disponible': 2,
        'condicion': 'operativa',
        'requiere_calibracion': 0
    }

    herr_1_response = client.post('/api/herramientas',
                                  data=json.dumps(herramienta_1),
                                  content_type='application/json')
    herr_2_response = client.post('/api/herramientas',
                                  data=json.dumps(herramienta_2),
                                  content_type='application/json')

    herr_1_id = json.loads(herr_1_response.data)['id']
    herr_2_id = json.loads(herr_2_response.data)['id']

    checkout_data = {
        'fecha': datetime.now().strftime('%Y-%m-%d'),
        'empleado': 'EMP-GRUPO-01',
        'herramientas': [
            {'herramienta_id': herr_1_id, 'cantidad': 1},
            {'herramienta_id': herr_2_id, 'cantidad': 1}
        ]
    }

    checkout_response = client.post('/api/herramientas/checkout',
                                    data=json.dumps(checkout_data),
                                    content_type='application/json')
    assert checkout_response.status_code == 200

    response = client.get('/api/herramientas/prestamos-por-usuario')
    assert response.status_code == 200
    data = json.loads(response.data)

    assert data['ok'] is True
    assert data['total_usuarios'] >= 1
    assert any(
        usuario['empleado_nombre'] == 'Usuario Agrupado'
        and len(usuario['herramientas']) == 2
        for usuario in data['usuarios']
    )


def test_empleado_detalle_herramientas_a_cargo(client):
    """Test detalle de empleado incluye herramientas a cargo"""
    empleado = {
        'numero_identificacion': 'EMP-CARGO-01',
        'nombre': 'Usuario Cargo',
        'estado': 'activo'
    }
    emp_response = client.post('/api/empleados',
                               data=json.dumps(empleado),
                               content_type='application/json')
    emp_id = json.loads(emp_response.data)['id']

    herramienta = {
        'sku': 'HERR-CARGO-001',
        'nombre': 'Herramienta Cargo',
        'cantidad_total': 4,
        'cantidad_disponible': 4,
        'condicion': 'operativa',
        'requiere_calibracion': 0
    }
    herr_response = client.post('/api/herramientas',
                                data=json.dumps(herramienta),
                                content_type='application/json')
    herr_id = json.loads(herr_response.data)['id']

    checkout_data = {
        'fecha': datetime.now().strftime('%Y-%m-%d'),
        'empleado_id': emp_id,
        'herramientas': [{'herramienta_id': herr_id, 'cantidad': 1}]
    }
    checkout_response = client.post('/api/herramientas/checkout',
                                    data=json.dumps(checkout_data),
                                    content_type='application/json')
    assert checkout_response.status_code == 200

    response = client.get(f'/api/empleados/{emp_id}')
    assert response.status_code == 200
    data = json.loads(response.data)

    assert data['ok'] is True
    assert len(data['empleado']['herramientas_a_cargo']) == 1
    assert data['empleado']['herramientas_a_cargo'][0]['sku'] == 'HERR-CARGO-001'

def test_checkout_validacion_disponibilidad(client):
    """Test validación de disponibilidad en checkout"""
    # Crear empleado
    empleado = {
        'numero_identificacion': 'EMP-VAL-01',
        'nombre': 'Empleado Validación',
        'estado': 'activo'
    }
    client.post('/api/empleados',
                data=json.dumps(empleado),
                content_type='application/json')
    
    # Crear herramienta con stock limitado
    herramienta = {
        'sku': 'HERR-VAL-001',
        'nombre': 'Herramienta Stock Limitado',
        'cantidad_total': 2,
        'cantidad_disponible': 2,
        'condicion': 'operativa',
        'requiere_calibracion': 0
    }
    herr_response = client.post('/api/herramientas',
                                data=json.dumps(herramienta),
                                content_type='application/json')
    herr_id = json.loads(herr_response.data)['id']
    
    # Intentar prestar más de lo disponible
    checkout_data = {
        'fecha': datetime.now().strftime('%Y-%m-%d'),
        'empleado': 'EMP-VAL-01',
        'herramienta': [
            {
                'herramienta_id': herr_id,
                'cantidad': 5  # Más de las 2 disponibles
            }
        ]
    }
    
    response = client.post('/api/herramientas/checkout',
                          data=json.dumps(checkout_data),
                          content_type='application/json')
    assert response.status_code == 400 or (response.status_code == 200 and not json.loads(response.data)['ok'])

def test_prestamos_activos(client):
    """Test listar préstamos activos"""
    response = client.get('/api/herramientas/prestamos-activos')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert 'prestamos' in data

def test_checkin_herramienta(client):
    """Test devolución de herramienta (checkin)"""
    # Crear empleado y herramienta
    empleado = {
        'numero_identificacion': 'EMP-CHECKIN-01',
        'nombre': 'Empleado Checkin Test',
        'estado': 'activo'
    }
    client.post('/api/empleados',
                data=json.dumps(empleado),
                content_type='application/json')
    
    herramienta = {
        'sku': 'HERR-CHECKIN-001',
        'nombre': 'Herramienta para Checkin',
        'cantidad_total': 10,
        'cantidad_disponible': 10,
        'condicion': 'operativa',
        'requiere_calibracion': 0
    }
    herr_response = client.post('/api/herramientas',
                                data=json.dumps(herramienta),
                                content_type='application/json')
    herr_id = json.loads(herr_response.data)['id']
    
    # Hacer checkout
    checkout_data = {
        'fecha': datetime.now().strftime('%Y-%m-%d'),
        'empleado': 'EMP-CHECKIN-01',
        'herramientas': [{'herramienta_id': herr_id, 'cantidad': 2}]
    }
    checkout_resp = client.post('/api/herramientas/checkout',
                                data=json.dumps(checkout_data),
                                content_type='application/json')
    
    # Obtener el movimiento_id del préstamo
    prestamos_resp = client.get('/api/herramientas/prestamos-activos')
    prestamos = json.loads(prestamos_resp.data)['prestamos']
    if prestamos:
        mov_id = prestamos[0]['movimiento_id']
        
        # Hacer checkin
        checkin_data = {
            'movimiento_id': mov_id,
            'fecha_devolucion': datetime.now().strftime('%Y-%m-%d'),
            'estado_devolucion': 'operativa',
            'observaciones_devolucion': 'Devolución en buen estado'
        }
        
        response = client.post('/api/herramientas/checkin',
                              data=json.dumps(checkin_data),
                              content_type='application/json')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['ok'] is True

        # volver a pedir préstamo para chequear devolución parcial
        checkout_resp = client.post('/api/herramientas/checkout',
                                    data=json.dumps(checkout_data),
                                    content_type='application/json')
        prestamos_resp = client.get('/api/herramientas/prestamos-activos')
        mov_id2 = json.loads(prestamos_resp.data)['prestamos'][0]['movimiento_id']

        partial_data = {
            'movimiento_id': mov_id2,
            'fecha_devolucion': datetime.now().strftime('%Y-%m-%d'),
            'estado_devolucion': 'operativa',
            'observaciones_devolucion': 'Solo devuelvo una unidad',
            'cantidad_devuelta': 1
        }
        response = client.post('/api/herramientas/checkin',
                              data=json.dumps(partial_data),
                              content_type='application/json')
        assert response.status_code == 200
        pdata = json.loads(response.data)
        assert pdata['ok'] is True

        # after devolver sólo una unidad debería quedar un préstamo activo
        prestamos_resp2 = client.get('/api/herramientas/prestamos-activos')
        active = json.loads(prestamos_resp2.data)['prestamos']
        assert len(active) == 1
        assert active[0]['cantidad'] == 1
        remaining_id = active[0]['movimiento_id']

        # the legacy endpoint should still accept the same payload (no error)
        legacy_resp = client.post(f'/api/herramientas/prestamo/{remaining_id}/devolucion-parcial',
                                   data=json.dumps({'cantidad_devuelta':1}),
                                   content_type='application/json')
        assert legacy_resp.status_code == 200
        ldata = json.loads(legacy_resp.data)
        assert ldata['ok'] is True

def test_mantenimiento_registro(client):
    """Test registrar mantenimiento"""
    # Crear herramienta
    herramienta = {
        'sku': 'HERR-MANT-001',
        'nombre': 'Herramienta para Mantenimiento',
        'cantidad_total': 5,
        'cantidad_disponible': 5,
        'condicion': 'operativa',
        'requiere_calibracion': 0
    }
    herr_response = client.post('/api/herramientas',
                                data=json.dumps(herramienta),
                                content_type='application/json')
    herr_id = json.loads(herr_response.data)['id']
    
    # Registrar mantenimiento
    mant_data = {
        'herramienta_id': herr_id,
        'tipo': 'preventivo',
        'fecha_mantenimiento': datetime.now().strftime('%Y-%m-%d'),
        'descripcion': 'Mantenimiento preventivo de prueba',
        'costo': 15000,
        'responsable_nombre': 'Técnico Test',
        'observaciones': 'Test completado exitosamente'
    }
    
    response = client.post('/api/herramientas/mantenimiento',
                          data=json.dumps(mant_data),
                          content_type='application/json')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['ok'] is True

def test_planes_mantenimiento_create(client):
    """Test crear plan de mantenimiento"""
    # Crear herramienta
    herramienta = {
        'sku': 'HERR-PLAN-001',
        'nombre': 'Herramienta con Plan',
        'cantidad_total': 3,
        'cantidad_disponible': 3,
        'condicion': 'operativa',
        'requiere_calibracion': 1,
        'frecuencia_calibracion_dias': 365
    }
    herr_response = client.post('/api/herramientas',
                                data=json.dumps(herramienta),
                                content_type='application/json')
    herr_id = json.loads(herr_response.data)['id']
    
    # Crear plan
    plan_data = {
        'herramienta_id': herr_id,
        'tipo_mantenimiento': 'preventivo',
        'frecuencia_dias': 30
    }
    
    response = client.post('/api/herramientas/planes-mantenimiento',
                          data=json.dumps(plan_data),
                          content_type='application/json')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['ok'] is True

def test_planes_mantenimiento_list(client):
    """Test listar planes de mantenimiento"""
    response = client.get('/api/herramientas/planes-mantenimiento')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert 'planes' in data

def test_calibraciones_vencidas(client):
    """Test obtener calibraciones vencidas"""
    response = client.get('/api/herramientas/calibraciones-vencidas')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert 'herramientas' in data

def test_mantenimientos_vencidos(client):
    """Test obtener mantenimientos vencidos"""
    response = client.get('/api/herramientas/mantenimientos-vencidos')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert 'herramientas' in data

def test_costos_mantenimiento(client):
    """Test obtener costos de mantenimiento"""
    response = client.get('/api/herramientas/costos-mantenimiento?meses=6')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert 'costos' in data
    assert 'total_periodo' in data

def test_kardex_herramienta(client):
    """Test obtener kardex de herramienta"""
    # Crear herramienta
    herramienta = {
        'sku': 'HERR-KARDEX-001',
        'nombre': 'Herramienta para Kardex',
        'cantidad_total': 5,
        'cantidad_disponible': 5,
        'condicion': 'operativa',
        'requiere_calibracion': 0
    }
    herr_response = client.post('/api/herramientas',
                                data=json.dumps(herramienta),
                                content_type='application/json')
    herr_id = json.loads(herr_response.data)['id']
    
    # Obtener kardex
    response = client.get(f'/api/herramientas/{herr_id}/kardex')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert 'movimientos' in data

def test_validacion_empleado_requerido(client):
    """Test validación de empleado requerido en checkout"""
    checkout_data = {
        'fecha': datetime.now().strftime('%Y-%m-%d'),
        'herramientas': [{'herramienta_id': 1, 'cantidad': 1}]
        # Falta empleado
    }
    
    response = client.post('/api/herramientas/checkout',
                          data=json.dumps(checkout_data),
                          content_type='application/json')
    # Debe fallar por falta de empleado
    assert response.status_code == 400 or not json.loads(response.data).get('ok', True)

def test_validacion_estado_devolucion(client):
    """Test validación de estado obligatorio en checkin"""
    checkin_data = {
        'movimiento_id': 999,
        'fecha_devolucion': datetime.now().strftime('%Y-%m-%d')
        # Falta estado_devolucion
    }
    
    response = client.post('/api/herramientas/checkin',
                          data=json.dumps(checkin_data),
                          content_type='application/json')
    # Debe fallar por falta de estado
    assert response.status_code == 400 or not json.loads(response.data).get('ok', True)

def test_validacion_campos_mantenimiento(client):
    """Test validación de campos obligatorios en mantenimiento"""
    mant_data = {
        'herramienta_id': 1,
        'tipo': 'preventivo'
        # Faltan fecha_mantenimiento y descripcion
    }
    
    response = client.post('/api/herramientas/mantenimiento',
                          data=json.dumps(mant_data),
                          content_type='application/json')
    # Debe fallar por campos faltantes
    assert response.status_code == 400 or not json.loads(response.data).get('ok', True)
