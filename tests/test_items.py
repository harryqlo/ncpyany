"""
Tests para endpoints de items
"""
import json
import pytest

def test_dashboard(client):
    """Test endpoint GET /api/dashboard and basic JSON structure"""
    response = client.get('/api/dashboard')
    assert response.status_code == 200
    data = json.loads(response.data)

    # Verificar estructura básica
    for key in ['total_items', 'items_con_stock', 'items_sin_stock', 'valor_total']:
        assert key in data
    assert isinstance(data['total_items'], int)
    # nuevos campos de series deberían estar presentes aunque vacíos
    assert isinstance(data.get('series_ingresos', []), list)
    assert isinstance(data.get('series_consumos', []), list)

    # the detailed endpoint should return a list matching the total
    resp_detail = client.get('/api/dashboard/detalle-valor')
    assert resp_detail.status_code == 200
    dd = json.loads(resp_detail.data)
    assert 'detail' in dd and 'total' in dd
    # total should match valor_total from main dashboard (rounded)
    assert dd['total'] == round(data['valor_total'])

    # probar que los filtros no rompen la ruta
    resp2 = client.get('/api/dashboard?from=2000-01-01&to=2000-01-01')
    assert resp2.status_code == 200
    print("✅ test_dashboard PASSED")


def test_dashboard_flag_and_cleanup(client):
    """Dashboard reports invalid_items and cleanup API removes them"""
    from app.db import get_db
    # perform writes inside app context so correct DB is used
    with client.application.app_context():
        db = get_db()
        # insert an invalid row using empty SKU (NULL not allowed by schema)
        db.execute("INSERT INTO items (sku,nombre,stock_actual,precio_unitario_promedio) VALUES ('', 'Bad2', 2, 2)")
        db.commit()
        db.close()

    # dashboard should report >0 invalid
    resp = client.get('/api/dashboard'); d=json.loads(resp.data)
    assert d.get('invalid_items',0) >= 1
    # cleanup endpoint
    resp2 = client.post('/api/items/clean')
    assert resp2.status_code == 200
    dd = json.loads(resp2.data)
    assert dd.get('ok')
    assert dd.get('deleted',0) >= 1
    # after cleanup invalid count should drop
    resp3 = client.get('/api/dashboard'); d3=json.loads(resp3.data)
    assert d3.get('invalid_items',0) == 0
    print("✅ test_dashboard_flag_and_cleanup PASSED")

def test_dashboard_filters(client):
    """La API debe aceptar parámetros from/to/categoria y devolver series"""
    from app.db import get_db
    from tests.conftest import init_test_db

    # perform direct DB manipulations inside app context so get_db points to the
    # temporary database created for this test.
    with client.application.app_context():
        db = get_db()
        # ensure consumo table has categoria_item column (recreate from scratch)
        db.execute('DROP TABLE IF EXISTS movimientos_consumo')
        db.execute('''
            CREATE TABLE movimientos_consumo (
                c1 INTEGER PRIMARY KEY,
                item_sku TEXT,
                descripcion_item TEXT,
                fecha_consumo TEXT,
                solicitante_nombre TEXT,
                cantidad_consumida INTEGER,
                precio_unitario REAL,
                total_consumo REAL,
                orden_trabajo_id INTEGER,
                stock_actual_en_consumo INTEGER,
                observaciones TEXT,
                categoria_item TEXT
            )
        ''')
        db.commit()
        print('pragma consumo after recreate:', db.execute("PRAGMA table_info(movimientos_consumo)").fetchall())
        db.execute("INSERT INTO items (sku,nombre,stock_actual,precio_unitario_promedio,categoria_nombre) VALUES ('ABC','X',10,5,'Cat1')")
        db.execute("INSERT INTO movimientos_ingreso (fecha_orden,item_sku,cantidad,categoria_item) VALUES ('2023-01-10','ABC',3,'Cat1')")
        db.execute("INSERT INTO movimientos_consumo (fecha_consumo,item_sku,cantidad_consumida,categoria_item) VALUES ('2023-01-15','ABC',1,'Cat1')")
        db.commit()
        db.close()

    resp = client.get('/api/dashboard?from=2023-01-01&to=2023-12-31&category=Cat1')
    assert resp.status_code == 200
    d = json.loads(resp.data)
    print('dashboard response:', d)
    assert d['categorias'] == [{'nombre':'Cat1','cantidad':1}]
    # series should contain at least one entry
    assert any(entry['period'].startswith('2023-01') for entry in d['series_ingresos'])
    assert any(entry['period'].startswith('2023-01') for entry in d['series_consumos'])
    print("✅ test_dashboard_filters PASSED")


def test_dashboard_includes_accumulated_consumos_without_date_filters(client):
    """El dashboard debe incluir consumos acumulados en métricas, top y series cuando no hay filtro de fechas"""
    from app.db import get_db

    with client.application.app_context():
        db = get_db()
        db.execute(
            "INSERT INTO items (sku,nombre,stock_actual,precio_unitario_promedio,categoria_nombre,consumos_totales_historicos) VALUES ('DASH-HIST-001','Producto Dashboard',6,50,'CatDash',4)"
        )
        db.commit()
        db.close()

    response = client.get('/api/dashboard')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['total_consumos'] >= 1
    assert data['total_consumos_acumulados'] >= 4
    assert any(entry['period'] == 'Acumulado' and entry['total'] >= 4 for entry in data['series_consumos'])
    assert any(entry['sku'] == 'DASH-HIST-001' and entry['total'] >= 4 for entry in data['top_consumo'])


def test_dashboard_excludes_accumulated_series_when_date_filtered(client):
    """Con filtro de fechas, los consumos acumulados sin fecha no deben contaminar la serie"""
    from app.db import get_db

    with client.application.app_context():
        db = get_db()
        db.execute(
            "INSERT INTO items (sku,nombre,stock_actual,precio_unitario_promedio,categoria_nombre,consumos_totales_historicos) VALUES ('DASH-HIST-002','Producto Dashboard 2',8,75,'CatDash',3)"
        )
        db.commit()
        db.close()

    response = client.get('/api/dashboard?from=2025-01-01&to=2025-12-31')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['total_consumos_acumulados'] == 0
    assert all(entry['period'] != 'Acumulado' for entry in data['series_consumos'])


def test_dashboard_ignores_null_sku(client):
    """El valor total no debe aumentar al agregar producto sin SKU"""
    from app.db import get_db
    # obtain current inventory value
    r0 = client.get('/api/dashboard'); v0 = json.loads(r0.data)['valor_total']
    # insert a row with empty SKU (null not allowed)
    with client.application.app_context():
        db = get_db()
        db.execute("INSERT INTO items (sku,nombre,stock_actual,precio_unitario_promedio) VALUES ('', 'Fake', 100, 999999)")
        db.commit()
        db.close()
    r1 = client.get('/api/dashboard'); v1 = json.loads(r1.data)['valor_total']
    # la diferencia debe ser menor que el hipotético valor del item
    assert v1 - v0 < 999999
    print("✅ test_dashboard_ignores_null_sku PASSED")

def test_list_items_empty(client):
    """Test listar items cuando no hay datos"""
    response = client.get('/api/items?page=1')
    assert response.status_code == 200
    data = json.loads(response.data)
    
    assert 'items' in data
    assert 'total' in data
    assert 'page' in data
    assert isinstance(data['items'], list)
    print("✅ test_list_items_empty PASSED")

def test_create_item(client):
    """Test crear nuevo item"""
    payload = {
        'sku': 'TEST-001',
        'nombre': 'Producto de Prueba',
        'stock': 10,
        'precio': 100.50,
        'categoria': 'Test',
        'unidad': 'PZA'
    }
    response = client.post('/api/items',
                          json=payload,
                          content_type='application/json')
    assert response.status_code in [200, 201]
    data = json.loads(response.data)
    assert data.get('ok') == True
    print("✅ test_create_item PASSED")

def test_list_items_after_create(client):
    """Test listar items después de crear uno"""
    # Crear un item
    payload = {
        'sku': 'TEST-002',
        'nombre': 'Producto 2',
        'stock': 5,
        'precio': 50.0
    }
    client.post('/api/items', json=payload, content_type='application/json')
    
    # Listar items
    response = client.get('/api/items?page=1')
    assert response.status_code == 200
    data = json.loads(response.data)
    
    assert len(data['items']) > 0
    print("✅ test_list_items_after_create PASSED")

def test_search_items(client):
    """Test búsqueda de items"""
    # Crear un item
    payload = {
        'sku': 'BUSCAR-001',
        'nombre': 'Producto Buscable',
        'stock': 15
    }
    client.post('/api/items', json=payload, content_type='application/json')
    
    # Buscar
    response = client.get('/api/items/search?q=Buscable')
    assert response.status_code == 200
    data = json.loads(response.data)
    
    # Debe encontrar el producto creado
    assert len(data) > 0
    print("✅ test_search_items PASSED")

def test_search_empty(client):
    """Test búsqueda sin resultados"""
    response = client.get('/api/items/search?q=NOEXISTE')
    assert response.status_code == 200
    data = json.loads(response.data)
    
    # Si no hay resultados, debe retornar lista vacía
    assert isinstance(data, list)
    print("✅ test_search_empty PASSED")

def test_update_item(client):
    """Test actualizar item"""
    # Crear
    payload_create = {
        'sku': 'UPDATE-001',
        'nombre': 'Producto Original',
        'stock': 10
    }
    client.post('/api/items', json=payload_create, content_type='application/json')
    
    # Actualizar
    payload_update = {
        'nombre': 'Producto Actualizado',
        'stock': 20
    }
    response = client.put('/api/items/UPDATE-001',
                         json=payload_update,
                         content_type='application/json')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data.get('ok') == True
    print("✅ test_update_item PASSED")

def test_delete_item(client):
    """Test eliminar item"""
    # Crear
    payload = {
        'sku': 'DELETE-001',
        'nombre': 'Producto a Eliminar',
        'stock': 5
    }
    client.post('/api/items', json=payload, content_type='application/json')
    
    # Eliminar
    response = client.delete('/api/items/DELETE-001')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data.get('ok') == True
    print("✅ test_delete_item PASSED")


def test_item_ficha_endpoint(client):
    """Verificar que la ruta /api/items/<sku>/ficha devuelve datos correctos"""
    payload = {
        'sku': 'FICHA-001',
        'nombre': 'Producto Ficha',
        'stock': 20,
        'precio': 30.0
    }
    client.post('/api/items', json=payload, content_type='application/json')
    response = client.get('/api/items/FICHA-001/ficha')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data.get('ok') is True
    assert data['data']['sku'] == 'FICHA-001'
    assert 'ultimos_ingresos' in data['data']
    assert 'ultimos_consumos' in data['data']
    print("✅ test_item_ficha_endpoint PASSED")


def test_item_ficha_includes_accumulated_consumo(client):
    """La ficha debe incluir consumos acumulados dentro de los totales y últimos registros"""
    client.post('/api/items', json={'sku': 'FICHA-HIST-001', 'nombre': 'Producto con Acumulado', 'stock': 12, 'precio': 100.0}, content_type='application/json')

    from app.db import get_db
    with client.application.app_context():
        db = get_db()
        db.execute('ALTER TABLE items ADD COLUMN consumo_historico_ot TEXT')
        db.execute(
            'UPDATE items SET consumos_totales_historicos=?, precio_unitario_promedio=?, stock_actual=?, consumo_historico_ot=? WHERE sku=?',
            [5, 100, 12, 'OT-HIST-001', 'FICHA-HIST-001']
        )
        db.commit()
        db.close()

    response = client.get('/api/items/FICHA-HIST-001/ficha')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['data']['total_consumido'] == 5
    assert data['data']['total_consumos_count'] == 1
    assert len(data['data']['ultimos_consumos']) == 1
    assert data['data']['ultimos_consumos'][0]['fecha'] is None
    assert data['data']['ultimos_consumos'][0]['cantidad'] == 5
    assert data['data']['ultimos_consumos'][0]['ot'] == 'OT-HIST-001'


def test_item_kardex_includes_accumulated_consumo(client):
    """El kardex debe mostrar el saldo inicial de consumo acumulado"""
    client.post('/api/items', json={'sku': 'KAR-HIST-001', 'nombre': 'Producto Kardex', 'stock': 9, 'precio': 200.0}, content_type='application/json')

    from app.db import get_db
    with client.application.app_context():
        db = get_db()
        db.execute('ALTER TABLE items ADD COLUMN consumo_historico_ot TEXT')
        db.execute(
            'UPDATE items SET consumos_totales_historicos=?, precio_unitario_promedio=?, stock_actual=?, consumo_historico_ot=? WHERE sku=?',
            [4, 200, 9, 'OT-HIST-002', 'KAR-HIST-001']
        )
        db.commit()
        db.close()

    response = client.get('/api/items/KAR-HIST-001/kardex?page=1&per_page=20')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['total'] == 1
    assert data['items'][0]['tipo'] == 'CONSUMO'
    assert data['items'][0]['cant'] == 4
    assert data['items'][0]['fecha'] is None
    assert data['items'][0]['ref2'] == 'OT-HIST-002'
    assert data['items'][0]['obs'] == 'Saldo inicial de consumo'
    assert data['items'][0]['saldo'] == -4

def test_pagination(client):
    """Test paginación"""
    # Crear varios items
    for i in range(5):
        payload = {
            'sku': f'PAGE-{i:03d}',
            'nombre': f'Producto {i}',
            'stock': i * 10
        }
        client.post('/api/items', json=payload, content_type='application/json')
    
    # Probar con per_page=2
    response = client.get('/api/items?page=1&per_page=2')
    assert response.status_code == 200
    data = json.loads(response.data)
    
    assert len(data['items']) <= 2
    assert data['per_page'] == 2
    print("✅ test_pagination PASSED")

def test_invalid_pagina(client):
    """Test página inválida"""
    response = client.get('/api/items?page=0&per_page=10')
    # No debe fallar, pero puede retornar lista vacía
    assert response.status_code == 200
    print("✅ test_invalid_pagina PASSED")


def test_null_sku_not_listed(client):
    """Un item con SKU NULL/empty no debe aparecer en listados"""
    # insert raw empty sku using db connection inside app context
    from app.db import get_db
    with client.application.app_context():
        db = get_db()
        try:
            db.execute("INSERT INTO items (sku,nombre) VALUES ('', 'Sin SKU')")
            db.commit()
        finally:
            db.close()
    response = client.get('/api/items?page=1')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert all(it['sku'] is not None and it['sku'] != '' for it in data['items'])
    print("✅ test_null_sku_not_listed PASSED")


def test_delete_invalid_sku(client):
    """Eliminar con SKU inválido debe retornar error"""
    response = client.delete('/api/items/null')
    assert response.status_code == 400
    data = json.loads(response.data)
    assert data.get('ok') == False
    print("✅ test_delete_invalid_sku PASSED")

def test_suggest_sku_new_prefix(client):
    """Test sugerir SKU para prefijo nuevo"""
    # clean up any existing TESTSKU to make prefix fresh
    from app.db import get_db
    db = get_db()
    db.execute("DELETE FROM items WHERE sku LIKE 'TESTSKU-%'")
    db.commit()

    response = client.get('/api/items/suggest-sku?prefix=TESTSKU')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data.get('ok') == True
    assert data.get('sku') == 'TESTSKU-001'
    print("✅ test_suggest_sku_new_prefix PASSED")

def test_suggest_sku_existing_prefix(client):
    """Test sugerir SKU para prefijo existente"""
    from app.db import get_db
    # Crear algunos items con prefijo TESTSKU y confirmar éxito
    for i in range(1, 4):
        payload = {
            'sku': f'TESTSKU-{i:03d}',
            'nombre': f'Producto TESTSKU {i}',
            'stock': 10
        }
        resp = client.post('/api/items', json=payload, content_type='application/json')
        assert resp.status_code in (200,201), resp.data
    # inspeccionar registros directos en DB
    with client.application.app_context():
        db = get_db()
        rows = db.execute("SELECT sku FROM items ORDER BY sku").fetchall()
        print('items in db for suggest test:', rows)
        db.close()

    # Sugerir siguiente
    response = client.get('/api/items/suggest-sku?prefix=TESTSKU')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data.get('ok') == True
    assert data.get('sku') == 'TESTSKU-004'
    print("✅ test_suggest_sku_existing_prefix PASSED")

def test_suggest_sku_no_prefix(client):
    """Test sugerir SKU sin prefijo"""
    response = client.get('/api/items/suggest-sku')
    assert response.status_code == 400
    data = json.loads(response.data)
    assert data.get('ok') == False
    print("✅ test_suggest_sku_no_prefix PASSED")
