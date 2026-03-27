"""
Tests para endpoints de ingresos y consumos
"""
import json
import pytest

def test_list_ingresos_empty(client):
    """Test listar ingresos sin datos"""
    response = client.get('/api/ingresos?page=1')
    assert response.status_code == 200
    data = json.loads(response.data)
    
    assert 'items' in data
    assert 'total' in data
    assert 'sum_qty' in data  # new aggregate field
    assert 'sum_total' in data
    assert isinstance(data['items'], list)
    print("✅ test_list_ingresos_empty PASSED")

def test_list_consumos_empty(client):
    """Test listar consumos sin datos"""
    response = client.get('/api/consumos?page=1')
    assert response.status_code == 200
    data = json.loads(response.data)
    
    assert 'items' in data
    assert 'total' in data
    assert isinstance(data['items'], list)
    print("✅ test_list_consumos_empty PASSED")

def test_list_ordenes_empty(client):
    """Test listar órdenes sin datos"""
    response = client.get('/api/ordenes?page=1')
    assert response.status_code == 200
    data = json.loads(response.data)
    
    assert 'items' in data
    assert 'total' in data
    assert isinstance(data['items'], list)
    print("✅ test_list_ordenes_empty PASSED")

def test_create_ingreso_without_item(client):
    """Test crear ingreso sin item existente (fallará)"""
    payload = {
        'sku': 'NOEXISTE',
        'cantidad': 10,
        'precio': 100.0,
        'proveedor': 'Proveedor A'
    }
    response = client.post('/api/ingresos',
                          json=payload,
                          content_type='application/json')
    # Puede fallar porque el SKU no existe en items
    # (Esto depende de si hay validación de FK)
    assert response.status_code in [200, 400, 404]
    print("✅ test_create_ingreso_without_item PASSED")

def test_create_consumo_without_item(client):
    """Test crear consumo sin item existente (fallará)"""
    payload = {
        'sku': 'NOEXISTE',
        'cantidad': 5,
        'solicitante': 'Depto A'
    }
    response = client.post('/api/consumos',
                          json=payload,
                          content_type='application/json')
    # Debe fallar porque el SKU no existe
    assert response.status_code in [400, 404]
    print("✅ test_create_consumo_without_item PASSED")

def test_create_orden_trabajo(client):
    """Test crear orden de trabajo"""
    payload = {
        'cliente': 'Cliente Test',
        'descripcion': 'Reparación de equipo',
        'estado': 'En progreso'
    }
    response = client.post('/api/ordenes',
                          json=payload,
                          content_type='application/json')
    assert response.status_code in [200, 201]
    data = json.loads(response.data)
    assert data.get('ok') == True
    print("✅ test_create_orden_trabajo PASSED")

def test_export_csv_items(client):
    """Test exportar inventario a CSV"""
    response = client.get('/api/export/csv')
    assert response.status_code == 200
    assert 'text/csv' in response.content_type
    # Debería contener headers CSV
    assert b'SKU' in response.data
    print("✅ test_export_csv_items PASSED")

def test_export_csv_ingresos(client):
    """Test exportar ingresos a CSV"""
    response = client.get('/api/export/ingresos')
    assert response.status_code == 200
    assert 'text/csv' in response.content_type
    assert b'Fecha' in response.data
    # also verify filtered export works (should at least return headers)
    response2 = client.get('/api/export/ingresos?search=XYZ')
    assert response2.status_code == 200
    assert b'Fecha' in response2.data
    print("✅ test_export_csv_ingresos PASSED")

def test_export_csv_consumos(client):
    """Test exportar consumos a CSV"""
    response = client.get('/api/export/consumos')
    assert response.status_code == 200
    assert 'text/csv' in response.content_type
    assert b'Fecha' in response.data
    print("✅ test_export_csv_consumos PASSED")


def test_export_formato_ot_historicos_excel(client):
    """Debe descargar plantilla Excel para completar OT históricas"""
    response = client.get('/api/export/consumos/historicos/formato.xlsx')
    assert response.status_code == 200
    assert response.content_type.startswith('application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    assert b'PK' == response.data[:2]

def test_search_ingresos(client):
    """Test búsqueda en ingresos"""
    response = client.get('/api/ingresos?search=PROD')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert 'items' in data
    assert 'sum_qty' in data
    assert 'sum_total' in data
    # si hay ítems, cada uno debe incluir precio
    if data['items']:
        assert all('precio' in it for it in data['items'])
    print("✅ test_search_ingresos PASSED")

def test_search_consumos(client):
    """Test búsqueda en consumos"""
    response = client.get('/api/consumos?search=PROD')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert 'items' in data
    print("✅ test_search_consumos PASSED")

def test_pagination_ingresos(client):
    """Test paginación de ingresos"""
    response = client.get('/api/ingresos?page=1&per_page=10')
    assert response.status_code == 200
    data = json.loads(response.data)
    
    assert 'page' in data
    assert 'per_page' in data
    assert 'total' in data
    assert data['page'] == 1
    print("✅ test_pagination_ingresos PASSED")

def test_pagination_consumos(client):
    """Test paginación de consumos"""
    response = client.get('/api/consumos?page=1&per_page=10')
    assert response.status_code == 200
    data = json.loads(response.data)
    
    assert 'page' in data
    assert 'per_page' in data
    assert 'total' in data
    print("✅ test_pagination_consumos PASSED")


def test_consumo_acumulado_list_and_update(client):
    """Los consumos acumulados deben mantenerse históricos al actualizar OT"""
    client.post('/api/items', json={'sku': 'HIST001', 'nombre': 'Item Historico'})

    from servidor import get_db
    db = get_db()
    db.execute(
        'UPDATE items SET stock_actual=?, consumos_totales_historicos=?, precio_unitario_promedio=? WHERE sku=?',
        [8, 4, 2500, 'HIST001']
    )
    db.commit()
    db.close()

    response = client.get('/api/consumos?search=HIST001')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert len(data['items']) == 1
    assert data['items'][0]['source'] == 'acumulado'
    assert data['items'][0]['cantidad'] == 4
    assert data['items'][0]['ot_id'] == ''

    update_payload = {
        'fecha': '2026-03-11',
        'solicitante': 'Bodega',
        'cantidad': 3,
        'ot_id': 'OT-77',
        'observaciones': 'Regularizado'
    }
    update_response = client.put('/api/consumos/historico/HIST001', json=update_payload, content_type='application/json')
    assert update_response.status_code == 200
    update_data = json.loads(update_response.data)
    assert update_data['ok'] is True

    response_after = client.get('/api/consumos?search=HIST001')
    data_after = json.loads(response_after.data)
    assert len(data_after['items']) == 1
    assert data_after['items'][0]['source'] == 'acumulado'
    assert data_after['items'][0]['cantidad'] == 4
    assert data_after['items'][0]['ot_id'] == 'OT-77'


def test_consumo_acumulado_delete_restore_stock(client):
    """Eliminar un acumulado debe restaurar stock y ocultarlo de la lista"""
    client.post('/api/items', json={'sku': 'HIST002', 'nombre': 'Item Acumulado'})

    from servidor import get_db
    db = get_db()
    db.execute(
        'UPDATE items SET stock_actual=?, consumos_totales_historicos=? WHERE sku=?',
        [5, 2, 'HIST002']
    )
    db.commit()
    db.close()

    delete_response = client.delete('/api/consumos/historico/HIST002')
    assert delete_response.status_code == 200
    delete_data = json.loads(delete_response.data)
    assert delete_data['ok'] is True

    response_after = client.get('/api/consumos?search=HIST002')
    data_after = json.loads(response_after.data)
    assert data_after['items'] == []

    export_response = client.get('/api/export/consumos')
    assert export_response.status_code == 200
    assert b'HIST002' not in export_response.data

def test_pagination_ordenes(client):
    """Test paginación de órdenes"""
    response = client.get('/api/ordenes?page=1&per_page=10')
    assert response.status_code == 200
    data = json.loads(response.data)
    
    assert 'page' in data
    assert 'per_page' in data
    assert 'total' in data
    print("✅ test_pagination_ordenes PASSED")


def test_get_ingreso_detail(client):
    """Test obtener detalle de un ingreso"""
    # puede que no exista ningún ingreso todavía, aceptamos 404
    response = client.get('/api/ingresos/1')
    assert response.status_code in [200, 404]
    if response.status_code == 200:
        data = json.loads(response.data)
        assert 'data' in data
        items = data['data'].get('items', [])
        assert isinstance(items, list)
        if items:
            assert 'precio' in items[0]
    print("✅ test_get_ingreso_detail PASSED")


def test_create_update_delete_ingreso(client):
    """Create a batch ingreso, update it, then delete it"""
    # first add an item to ensure SKU exists
    client.post('/api/items', json={'sku':'TESTSKU','nombre':'Test Item'})
    payload = {
        'fecha': '2025-01-01',
        'proveedor': 'Prov',
        'items': [{'sku':'TESTSKU','cantidad':5,'precio':10}]
    }
    response = client.post('/api/ingresos/batch', json=payload, content_type='application/json')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data.get('ok')
    # list ingresos to grab id
    r2 = client.get('/api/ingresos?search=TESTSKU')
    assert r2.status_code == 200
    res2 = json.loads(r2.data)
    assert res2['items']
    rid = res2['items'][0]['rowid']
    # get detail
    r3 = client.get(f'/api/ingresos/{rid}')
    assert r3.status_code == 200
    d3 = json.loads(r3.data)['data']
    assert d3['proveedor'] == 'Prov'
    # update ingreso
    upd = {'proveedor':'Prov2'}
    r4 = client.put(f'/api/ingresos/{rid}', json=upd, content_type='application/json')
    assert r4.status_code == 200
    r5 = client.get(f'/api/ingresos/{rid}')
    assert json.loads(r5.data)['data']['proveedor']=='Prov2'
    # delete
    r6 = client.delete(f'/api/ingresos/{rid}')
    assert r6.status_code == 200
    r7 = client.get(f'/api/ingresos/{rid}')
    assert r7.status_code == 404
    print("✅ test_create_update_delete_ingreso PASSED")
