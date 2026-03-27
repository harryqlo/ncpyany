"""
Configuración para pytest - Fixtures compartidas
"""
import pytest
import os
import tempfile
import sys
from pathlib import Path

# Agregar el directorio raíz al path para imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from servidor import app, get_db

@pytest.fixture
def client():
    """Cliente de prueba para hacer requests a la API"""
    # Usar base de datos temporal
    db_fd, db_path = tempfile.mkstemp()
    app.config['DATABASE'] = db_path
    app.config['TESTING'] = True
    
    with app.test_client() as client:
        with app.app_context():
            init_test_db(db_path)
        yield client
    
    # Limpiar
    os.close(db_fd)
    try:
        os.unlink(db_path)
    except PermissionError:
        # file still in use by sqlite; ignore for tests
        pass

@pytest.fixture
def runner(app):
    """Runner para comandos CLI dentro de tests"""
    return app.test_cli_runner()

def init_test_db(db_path):
    """Inicializa una base de datos de prueba con esquema"""
    import sqlite3
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    
    # Crear tablas (esquema simplificado)
    c.executescript("""
        DROP TABLE IF EXISTS movimientos_consumo;
        DROP TABLE IF EXISTS movimientos_ingreso;
        DROP TABLE IF EXISTS items;
        DROP TABLE IF EXISTS ordenes_trabajo;
        DROP TABLE IF EXISTS herramientas_planes_mantenimiento;
        DROP TABLE IF EXISTS herramientas_mantenimiento;
        DROP TABLE IF EXISTS herramientas_movimientos;
        DROP TABLE IF EXISTS herramientas;
        DROP TABLE IF EXISTS empleados;

        CREATE TABLE IF NOT EXISTS items (
            c1 INTEGER PRIMARY KEY,
            sku TEXT UNIQUE NOT NULL,
            nombre TEXT NOT NULL,
            stock_actual INTEGER DEFAULT 0,
            unidad_medida_nombre TEXT,
            ubicacion_nombre TEXT,
            sku_alternativo TEXT,
            categoria_nombre TEXT,
            subcategoria_nombre TEXT,
            proveedor_principal_nombre TEXT,
            precio_unitario_promedio REAL DEFAULT 0,
            ingresos_totales_historicos INTEGER DEFAULT 0,
            consumos_totales_historicos INTEGER DEFAULT 0,
            ajuste_total_historico INTEGER DEFAULT 0,
            valor_stock_final REAL DEFAULT 0,
            stock_minimo REAL DEFAULT 0,
            stock_maximo REAL DEFAULT 0
        );
        
        CREATE TABLE IF NOT EXISTS movimientos_ingreso (
            c1 INTEGER PRIMARY KEY,
            mes TEXT,
            fecha_orden TEXT,
            item_sku TEXT,
            cantidad INTEGER,
            descripcion_item TEXT,
            categoria_item TEXT,
            unidad_medida_item TEXT,
            precio_unitario REAL,
            descuento_monto REAL,
            descuento_porcentaje REAL,
            total_ingreso REAL,
            proveedor_nombre TEXT,
            numero_factura TEXT,
            numero_guia_despacho TEXT,
            numero_orden_compra TEXT,
            transportista_nombre TEXT,
            observaciones TEXT
        );
        
        CREATE TABLE IF NOT EXISTS movimientos_consumo (
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
        );
        
        CREATE TABLE IF NOT EXISTS ordenes_trabajo (
            id INTEGER PRIMARY KEY,
            estado_ingreso TEXT,
            registro_referencia TEXT,
            descripcion_componente TEXT,
            cliente_nombre TEXT,
            fecha_ot TEXT,
            codigo_referencia TEXT,
            listado_materiales TEXT
        );
        
        -- Tablas del Pañol (esquema real de producción)
        CREATE TABLE IF NOT EXISTS empleados (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            numero_identificacion TEXT UNIQUE NOT NULL,
            nombre TEXT NOT NULL,
            departamento TEXT,
            puesto TEXT,
            telefono TEXT,
            email TEXT,
            estado TEXT DEFAULT 'activo' CHECK(estado IN ('activo', 'inactivo')),
            fecha_ingreso TEXT,
            observaciones TEXT,
            fecha_creacion TEXT DEFAULT (date('now'))
        );
        
        CREATE TABLE IF NOT EXISTS herramientas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sku TEXT UNIQUE NOT NULL,
            nombre TEXT NOT NULL,
            categoria_nombre TEXT,
            subcategoria_nombre TEXT,
            numero_serie TEXT,
            modelo TEXT,
            fabricante TEXT,
            ubicacion_nombre TEXT,
            condicion TEXT DEFAULT 'operativa' CHECK(condicion IN ('operativa', 'mantenimiento', 'defectuosa', 'baja')),
            fecha_adquisicion TEXT,
            precio_unitario REAL DEFAULT 0.0,
            requiere_calibracion INTEGER DEFAULT 0,
            frecuencia_calibracion_dias INTEGER,
            ultima_calibracion TEXT,
            certificado_calibracion TEXT,
            observaciones TEXT,
            cantidad_total INTEGER DEFAULT 1,
            cantidad_disponible INTEGER DEFAULT 1,
            fecha_creacion TEXT DEFAULT (date('now'))
        );
        
        CREATE TABLE IF NOT EXISTS herramientas_movimientos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            herramienta_id INTEGER NOT NULL,
            empleado_id INTEGER,
            empleado_nombre TEXT NOT NULL,
            fecha_salida TEXT NOT NULL,
            fecha_retorno TEXT,
            cantidad INTEGER DEFAULT 1,
            estado_salida TEXT DEFAULT 'operativa',
            estado_retorno TEXT,
            observaciones_salida TEXT,
            observaciones_retorno TEXT,
            orden_trabajo_id INTEGER,
            foto_path TEXT,
            usuario_registro TEXT DEFAULT 'system',
            fecha_registro TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (herramienta_id) REFERENCES herramientas(id) ON DELETE CASCADE,
            FOREIGN KEY (empleado_id) REFERENCES empleados(id) ON DELETE SET NULL,
            FOREIGN KEY (orden_trabajo_id) REFERENCES ordenes_trabajo(id) ON DELETE SET NULL
        );
        
        CREATE TABLE IF NOT EXISTS herramientas_mantenimiento (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            herramienta_id INTEGER NOT NULL,
            fecha_mantenimiento TEXT NOT NULL,
            tipo TEXT NOT NULL CHECK(tipo IN ('preventivo', 'correctivo', 'calibracion')),
            descripcion TEXT NOT NULL,
            responsable_nombre TEXT,
            proveedor_nombre TEXT,
            costo REAL DEFAULT 0.0,
            proxima_fecha TEXT,
            certificado_path TEXT,
            observaciones TEXT,
            usuario_registro TEXT DEFAULT 'system',
            fecha_registro TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (herramienta_id) REFERENCES herramientas(id) ON DELETE CASCADE
        );
        
        CREATE TABLE IF NOT EXISTS herramientas_planes_mantenimiento (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            herramienta_id INTEGER NOT NULL,
            frecuencia_dias INTEGER NOT NULL,
            tipo_mantenimiento TEXT NOT NULL CHECK(tipo_mantenimiento IN ('preventivo', 'calibracion')),
            descripcion TEXT,
            costo_estimado REAL DEFAULT 0.0,
            activo INTEGER DEFAULT 1,
            fecha_creacion TEXT DEFAULT (date('now')),
            FOREIGN KEY (herramienta_id) REFERENCES herramientas(id) ON DELETE CASCADE
        );
    """)
    conn.commit()
    conn.close()
