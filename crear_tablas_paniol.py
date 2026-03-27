"""
Script para crear las tablas del sistema de pañol en la base de datos.
Incluye: empleados, herramientas, movimientos, mantenimiento y planes.
Ejecutar: python crear_tablas_paniol.py
"""
import sqlite3
import os
import sys
from datetime import datetime, timedelta

# Agregar el directorio raíz al path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

try:
    from config import DB_PATH
    from app.db import date_to_excel
except ImportError:
    SYSTEM_DIR = os.path.join(BASE_DIR, 'system')
    DB_PATH = os.path.join(SYSTEM_DIR, 'system.db')
    # Fallback para date_to_excel
    def date_to_excel(date_string):
        if not date_string:
            return None
        try:
            EXCEL_EPOCH = datetime(1899, 12, 30)
            date_obj = datetime.strptime(date_string[:10], '%Y-%m-%d')
            delta = date_obj - EXCEL_EPOCH
            return delta.days
        except (ValueError, TypeError):
            return None


def crear_tablas(conn):
    """
    Crea las tablas necesarias para el módulo de pañol
    """
    cursor = conn.cursor()
    
    try:
        # Tabla 1: Empleados (maestro de operarios/trabajadores)
        cursor.execute('''
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
            )
        ''')
        
        # Tabla 2: Herramientas (maestro de herramientas del pañol)
        cursor.execute('''
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
            )
        ''')
        
        # Tabla 3: Movimientos de herramientas (préstamos y devoluciones)
        cursor.execute('''
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
            )
        ''')
        
        # Tabla 4: Historial de mantenimientos
        cursor.execute('''
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
            )
        ''')
        
        # Tabla 5: Planes de mantenimiento preventivo
        cursor.execute('''
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
            )
        ''')
        
        conn.commit()
        print("✓ Tablas de pañol creadas correctamente")
        print("  - empleados")
        print("  - herramientas")
        print("  - herramientas_movimientos")
        print("  - herramientas_mantenimiento")
        print("  - herramientas_planes_mantenimiento")
        return True
        
    except Exception as e:
        print(f"✗ Error al crear tablas: {e}")
        conn.rollback()
        return False


def crear_indices(conn):
    """
    Crea índices para mejorar el rendimiento de consultas
    """
    cursor = conn.cursor()
    
    try:
        # Índices tabla empleados
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_emp_numero ON empleados(numero_identificacion)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_emp_nombre ON empleados(nombre)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_emp_estado ON empleados(estado)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_emp_departamento ON empleados(departamento)')
        
        # Índices tabla herramientas
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_herr_sku ON herramientas(sku)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_herr_nombre ON herramientas(nombre)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_herr_condicion ON herramientas(condicion)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_herr_categoria ON herramientas(categoria_nombre)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_herr_ubicacion ON herramientas(ubicacion_nombre)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_herr_calibracion ON herramientas(requiere_calibracion)')
        
        # Índices tabla movimientos
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_mov_herramienta ON herramientas_movimientos(herramienta_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_mov_empleado ON herramientas_movimientos(empleado_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_mov_fecha_salida ON herramientas_movimientos(fecha_salida)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_mov_fecha_retorno ON herramientas_movimientos(fecha_retorno)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_mov_orden ON herramientas_movimientos(orden_trabajo_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_mov_activos ON herramientas_movimientos(herramienta_id, fecha_retorno)')
        
        # Índices tabla mantenimiento
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_mant_herramienta ON herramientas_mantenimiento(herramienta_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_mant_fecha ON herramientas_mantenimiento(fecha_mantenimiento)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_mant_tipo ON herramientas_mantenimiento(tipo)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_mant_proxima ON herramientas_mantenimiento(proxima_fecha)')
        
        # Índices tabla planes
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_plan_herramienta ON herramientas_planes_mantenimiento(herramienta_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_plan_activo ON herramientas_planes_mantenimiento(activo)')
        
        conn.commit()
        print("✓ Índices creados correctamente")
        return True
        
    except Exception as e:
        print(f"✗ Error al crear índices: {e}")
        conn.rollback()
        return False


def insertar_datos_demo(conn):
    """
    Inserta datos de demostración para testing
    """
    cursor = conn.cursor()
    
    try:
        # Verificar si ya existen datos
        cursor.execute('SELECT COUNT(*) FROM empleados')
        if cursor.fetchone()[0] > 0:
            print("⚠ Ya existen datos en las tablas, omitiendo inserción de datos demo")
            return True
        
        print("\n📦 Insertando datos de demostración...")
        
        # 1. Empleados (20)
        empleados_demo = [
            ('E001', 'Juan Pérez Contreras', 'Mantención', 'Mecánico Senior', '+56912345678', 'jperez@empresa.cl', 'activo', '2020-01-15'),
            ('E002', 'María González Silva', 'Operaciones', 'Operador Maquinaria', '+56923456789', 'mgonzalez@empresa.cl', 'activo', '2019-05-20'),
            ('E003', 'Carlos Rodríguez Muñoz', 'Mantención', 'Técnico Eléctrico', '+56934567890', 'crodriguez@empresa.cl', 'activo', '2021-03-10'),
            ('E004', 'Ana Martínez López', 'Operaciones', 'Supervisor Turno', '+56945678901', 'amartinez@empresa.cl', 'activo', '2018-08-05'),
            ('E005', 'Pedro Sánchez Torres', 'Mantención', 'Soldador', '+56956789012', 'psanchez@empresa.cl', 'activo', '2020-11-12'),
            ('E006', 'Laura Fernández Díaz', 'Operaciones', 'Operador CNC', '+56967890123', 'lfernandez@empresa.cl', 'activo', '2022-02-28'),
            ('E007', 'Diego Ramírez Castro', 'Mantención', 'Mecánico Junior', '+56978901234', 'dramirez@empresa.cl', 'activo', '2023-01-15'),
            ('E008', 'Carmen Vega Ruiz', 'Calidad', 'Inspector Calidad', '+56989012345', 'cvega@empresa.cl', 'activo', '2019-09-10'),
            ('E009', 'Roberto Flores Morales', 'Operaciones', 'Operador Grúa', '+56990123456', 'rflores@empresa.cl', 'activo', '2021-07-22'),
            ('E010', 'Patricia Herrera Vargas', 'Mantención', 'Técnico Instrumentación', '+56901234567', 'pherrera@empresa.cl', 'activo', '2020-04-18'),
            ('E011', 'Francisco Molina Ponce', 'Operaciones', 'Operador Producción', '+56912345679', 'fmolina@empresa.cl', 'activo', '2022-06-01'),
            ('E012', 'Isabel Torres Campos', 'Bodega', 'Encargado Bodega', '+56923456780', 'itorres@empresa.cl', 'activo', '2017-12-10'),
            ('E013', 'Andrés Reyes Núñez', 'Mantención', 'Mecánico Diesel', '+56934567891', 'areyes@empresa.cl', 'activo', '2021-10-05'),
            ('E014', 'Mónica Silva Paredes', 'Operaciones', 'Operador Montacargas', '+56945678902', 'msilva@empresa.cl', 'activo', '2020-08-30'),
            ('E015', 'Jorge Castillo Bravo', 'Mantención', 'Técnico Hidráulico', '+56956789013', 'jcastillo@empresa.cl', 'activo', '2019-03-25'),
            ('E016', 'Claudia Morales Rojas', 'Calidad', 'Técnico Metrología', '+56967890124', 'cmorales@empresa.cl', 'activo', '2022-11-08'),
            ('E017', 'Luis Ortiz Mendoza', 'Operaciones', 'Operador Torno', '+56978901235', 'lortiz@empresa.cl', 'activo', '2023-03-14'),
            ('E018', 'Gabriela Pinto Soto', 'Mantención', 'Lubricador', '+56989012346', 'gpinto@empresa.cl', 'activo', '2021-05-19'),
            ('E019', 'Héctor Navarro Vera', 'Operaciones', 'Operador Prensa', '+56990123457', 'hnavarro@empresa.cl', 'activo', '2020-09-23'),
            ('E020', 'Valeria Guzmán Tapia', 'Mantención', 'Técnico Senior', '+56901234568', 'vguzman@empresa.cl', 'inactivo', '2018-01-10'),
        ]
        
        cursor.executemany('''
            INSERT INTO empleados (numero_identificacion, nombre, departamento, puesto, telefono, email, estado, fecha_ingreso)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', empleados_demo)
        
        print(f"  ✓ {len(empleados_demo)} empleados insertados")
        
        # 2. Herramientas (50)
        herramientas_demo = [
            # Herramientas manuales
            ('HERR-001', 'Taladro Percutor 850W', 'Herramientas Eléctricas', 'Taladros', 'TD-850-2023-001', 'HP850', 'Bosch', 'Pañol Principal', 'operativa', '2023-01-15', 89990, 0, None, None, None, 'Incluye maletín y accesorios', 1, 1),
            ('HERR-002', 'Esmeril Angular 7"', 'Herramientas Eléctricas', 'Esmeriles', 'EA-7-2023-002', 'GWS2000', 'Makita', 'Pañol Principal', 'operativa', '2023-01-20', 125000, 0, None, None, None, 'Uso industrial pesado', 1, 1),
            ('HERR-003', 'Multímetro Digital', 'Instrumentos Medición', 'Multímetros', 'MD-PRO-001', 'UT139C', 'UNI-T', 'Pañol Instrumentos', 'operativa', '2022-06-10', 45000, 1, 365, '2025-06-10', None, 'Requiere calibración anual', 1, 1),
            ('HERR-004', 'Torquímetro 40-200 Nm', 'Herramientas Torque', 'Torquímetros', 'TQ-200-2022-001', 'TWR-200', 'Gedore', 'Pañol Instrumentos', 'operativa', '2022-03-15', 185000, 1, 365, '2025-03-15', 'CERT-2025-001', 'Certificado vigente', 1, 1),
            ('HERR-005', 'Soldadora Inverter 200A', 'Equipos Soldadura', 'Soldadoras', 'SI-200-2023-005', 'ARC200', 'Lincoln', 'Pañol Soldadura', 'operativa', '2023-02-20', 320000, 0, None, None, None, 'Electrodo y TIG', 1, 1),
            ('HERR-006', 'Llave Impacto Neumática 1"', 'Herramientas Neumáticas', 'Llaves Impacto', 'LI-1-2022-006', 'IW1000', 'Ingersoll Rand', 'Pañol Principal', 'operativa', '2022-08-05', 275000, 0, None, None, None, 'Uso industrial', 1, 1),
            ('HERR-007', 'Compresor Portátil 50L', 'Equipos Neumáticos', 'Compresores', 'CP-50-2023-007', 'AC5050', 'Stanley', 'Pañol Principal', 'operativa', '2023-03-10', 189990, 0, None, None, None, '8 bar máximo', 1, 1),
            ('HERR-008', 'Juego Llaves Combinadas 21 pcs', 'Herramientas Manuales', 'Llaves', 'LC-21-2021-008', 'K21SET', 'Kendo', 'Pañol Principal', 'operativa', '2021-05-12', 78000, 0, None, None, None, '6mm a 32mm', 3, 3),
            ('HERR-009', 'Entenalla Mecánico 6"', 'Herramientas Banco', 'Entenallas', 'EM-6-2020-009', 'V600', 'Ridgid', 'Taller Mecánica', 'operativa', '2020-09-18', 95000, 0, None, None, None, 'Fija a banco', 1, 1),
            ('HERR-010', 'Calibre Digital 150mm', 'Instrumentos Medición', 'Calibres', 'CD-150-2022-010', 'CD-6"ASX', 'Mitutoyo', 'Pañol Instrumentos', 'operativa', '2022-07-22', 125000, 1, 365, '2025-07-22', 'CERT-2025-002', 'Precisión 0.01mm', 1, 1),
            
            # Herramientas con historial
            ('HERR-011', 'Taladro Manual 650W', 'Herramientas Eléctricas', 'Taladros', 'TM-650-2021-011', 'TD650', 'Black & Decker', 'Pañol Principal', 'operativa', '2021-11-08', 45900, 0, None, None, None, None, 1, 1),
            ('HERR-012', 'Amoladora Recta', 'Herramientas Eléctricas', 'Amoladoras', 'AR-2022-012', 'GGS28', 'Bosch', 'Pañol Principal', 'operativa', '2022-04-15', 89990, 0, None, None, None, None, 1, 1),
            ('HERR-013', 'Pistola Calor 2000W', 'Herramientas Eléctricas', 'Pistolas Calor', 'PC-2000-013', 'HG2000', 'Steinel', 'Pañol Principal', 'operativa', '2022-09-20', 67000, 0, None, None, None, 'Con accesorios', 1, 1),
            ('HERR-014', 'Sierra Circular 7¼"', 'Herramientas Eléctricas', 'Sierras', 'SC-7-2023-014', '5007MG', 'Makita', 'Pañol Principal', 'operativa', '2023-01-25', 145000, 0, None, None, None, '1800W potencia', 1, 1),
            ('HERR-015', 'Nivel Laser Rotativo', 'Instrumentos Medición', 'Niveles', 'NL-ROT-2022-015', 'GRL400H', 'Bosch', 'Pañol Topografía', 'operativa', '2022-05-10', 450000, 1, 365, '2025-05-10', None, 'Con receptor', 1, 1),
            
            # Herramientas que requieren mantención próxima
            ('HERR-016', 'Compresor Industrial 100L', 'Equipos Neumáticos', 'Compresores', 'CI-100-2021-016', 'AC10000', 'Atlas Copco', 'Taller Principal', 'operativa', '2021-03-15', 890000, 0, None, None, None, 'Mantención cada 6 meses', 1, 1),
            ('HERR-017', 'Talha Eléctrica 500kg', 'Equipos Elevación', 'Talhas', 'TE-500-2020-017', 'TE500', 'Yale', 'Bodega Central', 'operativa', '2020-06-20', 675000, 0, None, None, None, 'Inspección mensual requerida', 1, 1),
            ('HERR-018', 'Equipo Oxicorte Completo', 'Equipos Soldadura', 'Oxicorte', 'OC-2021-018', 'OXY300', 'ESAB', 'Pañol Soldadura', 'operativa', '2021-08-12', 425000, 0, None, None, None, 'Con mangueras y manómetros', 1, 1),
            
            # Herramientas que necesitan calibración vencida
            ('HERR-019', 'Micrómetro Exterior 0-25mm', 'Instrumentos Medición', 'Micrómetros', 'ME-25-2020-019', 'M025', 'Starrett', 'Pañol Instrumentos', 'operativa', '2020-04-10', 95000, 1, 365, '2024-04-10', 'CERT-2024-001', 'Calibración vencida', 1, 1),
            ('HERR-020', 'Termómetro Infrarrojo', 'Instrumentos Medición', 'Termómetros', 'TI-2021-020', 'TI-550', 'Fluke', 'Pañol Instrumentos', 'operativa', '2021-07-15', 235000, 1, 365, '2024-07-15', 'CERT-2024-002', 'Requiere recalibración', 1, 1),
            
            # Herramientas defectuosas
            ('HERR-021', 'Esmeril Banco 8"', 'Herramientas Banco', 'Esmeriles', 'EB-8-2019-021', 'GB800', 'Makita', 'Taller Mantención', 'defectuosa', '2019-11-20', 180000, 0, None, None, None, 'Motor quemado - reparación pendiente', 1, 0),
            ('HERR-022', 'Prensa Hidráulica 20 Ton', 'Equipos Hidráulicos', 'Prensas', 'PH-20-2018-022', 'HYD20T', 'Enerpac', 'Taller Mecánica', 'defectuosa', '2018-05-08', 1250000, 0, None, None, None, 'Fuga hidráulica sistema', 1, 0),
            
            # Herramientas en mantenimiento
            ('HERR-023', 'Grúa Horquilla Manual 2.5T', 'Equipos Elevación', 'Grúas', 'GH-25-2020-023', 'PM2500', 'BT', 'Bodega Central', 'mantenimiento', '2020-09-15', 785000, 0, None, None, None, 'Mantención programada en curso', 1, 0),
            
            # Más herramientas operativas
            ('HERR-024', 'Juego Dados Impact 1/2" 40pcs', 'Herramientas Manuales', 'Dados', 'JD-40-2022-024', 'IS40SET', 'Kraftwerk', 'Pañol Principal', 'operativa', '2022-10-05', 125000, 0, None, None, None, '10mm a 32mm', 2, 2),
            ('HERR-025', 'Llave Torque Digital 5-100 Nm', 'Herramientas Torque', 'Llaves Torque', 'LT-100-2023-025', 'DTW100', 'CDI', 'Pañol Instrumentos', 'operativa', '2023-02-12', 295000, 1, 365, '2026-02-12', None, 'Display digital', 1, 1),
            ('HERR-026', 'Cizalla Guillotina Manual', 'Herramientas Corte', 'Cizallas', 'CG-2021-026', 'HS250', 'Roper Whitney', 'Taller Calderería', 'operativa', '2021-12-01', 425000, 0, None, None, None, 'Corte hasta 2mm', 1, 1),
            ('HERR-027', 'Dobladora Tubos Manual', 'Herramientas Conformado', 'Dobladoras', 'DT-2022-027', 'TB300', 'Hilmor', 'Taller Cañería', 'operativa', '2022-08-18', 195000, 0, None, None, None, 'Hasta 1" diámetro', 1, 1),
            ('HERR-028', 'Extractor Rodamientos', 'Herramientas Especiales', 'Extractores', 'ER-2021-028', 'BRP-KIT', 'SKF', 'Taller Mecánica', 'operativa', '2021-06-22', 285000, 0, None, None, None, 'Kit completo 3 garras', 1, 1),
            ('HERR-029', 'Bomba Engrase Manual 20L', 'Equipos Lubricación', 'Bombas', 'BE-20-2022-029', 'LUB20', 'Lincoln', 'Pañol Lubricación', 'operativa', '2022-03-08', 145000, 0, None, None, None, 'Con manguera 3m', 1, 1),
            ('HERR-030', 'Carrito Herramientas 7 Bandejas', 'Muebles Taller', 'Carros', 'CH-7-2023-030', 'TC700', 'Bahco', 'Taller Móvil', 'operativa', '2023-04-15', 385000, 0, None, None, None, 'Con traba ruedas', 2, 2),
            
            # Herramientas múltiples unidades
            ('HERR-031', 'Martillo Bola 500g', 'Herramientas Manuales', 'Martillos', 'MB-500-031', 'H500B', 'Stanley', 'Pañol Principal', 'operativa', '2022-01-10', 8990, 0, None, None, None, 'Mango fibra de vidrio', 10, 10),
            ('HERR-032', 'Destornillador Plano 6mm', 'Herramientas Manuales', 'Destornilladores', 'DP-6-032', 'SD600', 'Wiha', 'Pañol Principal', 'operativa', '2022-01-10', 4500, 0, None, None, None, 'Mango ergonómico', 15, 15),
            ('HERR-033', 'Destornillador Phillips #2', 'Herramientas Manuales', 'Destornilladores', 'DPH-2-033', 'PH200', 'Wiha', 'Pañol Principal', 'operativa', '2022-01-10', 4500, 0, None, None, None, 'Mango ergonómico', 15, 15),
            ('HERR-034', 'Alicate Universal 8"', 'Herramientas Manuales', 'Alicates', 'AU-8-034', 'PLU8', 'Knipex', 'Pañol Principal', 'operativa', '2022-02-15', 25900, 0, None, None, None, 'Mandíbulas templadas', 8, 8),
            ('HERR-035', 'Alicate Corte Diagonal 6"', 'Herramientas Manuales', 'Alicates', 'ACD-6-035', 'CUT6', 'Knipex', 'Pañol Principal', 'operativa', '2022-02-15', 28500, 0, None, None, None, 'Corte fino', 8, 8),
            ('HERR-036', 'Linterna LED Recargable', 'Equipos Iluminación', 'Linternas', 'LL-2023-036', 'FL800', 'Fenix', 'Pañol Principal', 'operativa', '2023-01-20', 35000, 0, None, None, None, '800 lúmenes', 12, 12),
            ('HERR-037', 'Casco Seguridad Blanco', 'EPP', 'Cascos', 'CS-B-037', 'HH100W', '3M', 'Bodega EPP', 'operativa', '2023-03-01', 8900, 0, None, None, None, 'Certificado', 20, 20),
            ('HERR-038', 'Guantes Mecánico L', 'EPP', 'Guantes', 'GM-L-038', 'MG100L', 'Mechanix', 'Bodega EPP', 'operativa', '2023-03-01', 12900, 0, None, None, None, 'Talla L', 25, 25),
            ('HERR-039', 'Candado Seguridad 40mm', 'Seguridad', 'Candados', 'CS-40-039', 'PL40', 'Master Lock', 'Pañol Principal', 'operativa', '2022-11-10', 15900, 0, None, None, None, 'Con 2 llaves', 10, 10),
            ('HERR-040', 'Cinta Métrica 5m', 'Instrumentos Medición', 'Cintas', 'CM-5-040', 'TM500', 'Stanley', 'Pañol Principal', 'operativa', '2022-06-15', 7900, 0, None, None, None, 'Carcasa ABS', 10, 10),
            
            # Más herramientas especializadas
            ('HERR-041', 'Detector Fugas Ultrasónico', 'Instrumentos Medición', 'Detectores', 'DU-2022-041', 'UL101', 'UE Systems', 'Pañol Instrumentos', 'operativa', '2022-09-05', 1250000, 1, 365, '2025-09-05', 'CERT-2025-003', 'Para aire comprimido', 1, 1),
            ('HERR-042', 'Analizador Vibraciones', 'Instrumentos Medición', 'Analizadores', 'AV-2021-042', 'VIB300', 'SKF', 'Pañol Instrumentos', 'operativa', '2021-10-20', 2850000, 1, 365, '2024-10-20', 'CERT-2024-003', 'Calibración vencida', 1, 1),
            ('HERR-043', 'Medidor Espesor Ultrasónico', 'Instrumentos Medición', 'Medidores', 'MEU-2022-043', 'UT300', 'GE', 'Pañol Instrumentos', 'operativa', '2022-11-12', 985000, 1, 365, '2025-11-12', None, 'Para metales', 1, 1),
            ('HERR-044', 'Cámara Termográfica', 'Instrumentos Medición', 'Cámaras', 'CT-2023-044', 'Ti450', 'Fluke', 'Pañol Instrumentos', 'operativa', '2023-06-08', 3500000, 1, 730, '2025-06-08', None, 'Alta resolución', 1, 1),
            ('HERR-045', 'Balanza Precision 5kg', 'Instrumentos Medición', 'Balanzas', 'BP-5-2022-045', 'AX5000', 'Ohaus', 'Laboratorio', 'operativa', '2022-07-18', 450000, 1, 365, '2025-07-18', 'CERT-2025-004', 'Precisión 0.1g', 1, 1),
            ('HERR-046', 'Durómetro Portátil', 'Instrumentos Medición', 'Durómetros', 'DP-2021-046', 'DUR200', 'Innovatest', 'Laboratorio', 'operativa', '2021-05-25', 785000, 1, 365, '2024-05-25', 'CERT-2024-004', 'Escala Rockwell', 1, 1),
            ('HERR-047', 'Luxómetro Digital', 'Instrumentos Medición', 'Luxómetros', 'LD-2022-047', 'LX1330B', 'Lutron', 'Pañol Instrumentos', 'operativa', '2022-08-30', 185000, 1, 730, '2024-08-30', 'CERT-2024-005', 'Calibración vencida', 1, 1),
            ('HERR-048', 'Tacómetro Láser', 'Instrumentos Medición', 'Tacómetros', 'TL-2023-048', 'DT2234C', 'CEM', 'Pañol Instrumentos', 'operativa', '2023-02-14', 95000, 1, 730, '2025-02-14', None, 'Sin contacto', 1, 1),
            ('HERR-049', 'Pinza Amperimétrica', 'Instrumentos Medición', 'Pinzas', 'PA-2022-049', '376FC', 'Fluke', 'Pañol Eléctrico', 'operativa', '2022-12-05', 485000, 1, 365, '2025-12-05', None, 'True RMS', 1, 1),
            ('HERR-050', 'Medidor Aislación 1000V', 'Instrumentos Medición', 'Megóhmetros', 'MA-2023-050', '1587FC', 'Fluke', 'Pañol Eléctrico', 'operativa', '2023-03-20', 1450000, 1, 365, '2026-03-20', None, 'Bluetooth integrado', 1, 1),
        ]
        
        cursor.executemany('''
            INSERT INTO herramientas (sku, nombre, categoria_nombre, subcategoria_nombre, numero_serie, modelo, 
                                     fabricante, ubicacion_nombre, condicion, fecha_adquisicion, precio_unitario,
                                     requiere_calibracion, frecuencia_calibracion_dias, ultima_calibracion, 
                                     certificado_calibracion, observaciones, cantidad_total, cantidad_disponible)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', herramientas_demo)
        
        print(f"  ✓ {len(herramientas_demo)} herramientas insertadas")
        
        # 3. Movimientos históricos (30) - algunos cerrados, algunos activos
        hoy = datetime.now()
        movimientos_demo = []
        
        # Movimientos cerrados (devueltos)
        for i in range(1, 21):
            fecha_salida = (hoy - timedelta(days=30+i*2)).strftime('%Y-%m-%d')
            fecha_retorno = (hoy - timedelta(days=25+i*2)).strftime('%Y-%m-%d')
            herr_id = i
            emp_id = (i % 10) + 1
            estado_ret = 'operativa' if i % 5 != 0 else 'defectuosa'
            obs_ret = None if estado_ret == 'operativa' else f'Devuelta con desgaste, revisar estado'
            
            movimientos_demo.append((
                herr_id, emp_id, f'Empleado {emp_id}', fecha_salida, fecha_retorno, 1,
                'operativa', estado_ret, None, obs_ret, None, None, 'system'
            ))
        
        # Movimientos activos (prestados actualmente)
        for i in range(1, 11):
            fecha_salida = (hoy - timedelta(days=3+i)).strftime('%Y-%m-%d')
            herr_id = 10 + i
            emp_id = i
            
            movimientos_demo.append((
                herr_id, emp_id, f'Empleado {emp_id}', fecha_salida, None, 1,
                'operativa', None, f'Para trabajo en terreno', None, None, None, 'system'
            ))
        
        cursor.executemany('''
            INSERT INTO herramientas_movimientos (herramienta_id, empleado_id, empleado_nombre, fecha_salida, 
                                                 fecha_retorno, cantidad, estado_salida, estado_retorno,
                                                 observaciones_salida, observaciones_retorno, orden_trabajo_id, 
                                                 foto_path, usuario_registro)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', movimientos_demo)
        
        # Actualizar cantidad_disponible para herramientas prestadas
        cursor.execute('''
            UPDATE herramientas 
            SET cantidad_disponible = cantidad_total - (
                SELECT COUNT(*) FROM herramientas_movimientos
                WHERE herramienta_id = herramientas.id AND fecha_retorno IS NULL
            )
        ''')
        
        print(f"  ✓ {len(movimientos_demo)} movimientos insertados (10 activos)")
        
        # 4. Historial de mantenimientos (40)
        mantenimientos_demo = []
        
        # Mantenimientos completados
        for i in range(1, 31):
            fecha_mant = (hoy - timedelta(days=60+i*5)).strftime('%Y-%m-%d')
            herr_id = (i % 25) + 1
            tipo = ['preventivo', 'correctivo', 'calibracion'][i % 3]
            desc = f'Mantenimiento {tipo} - revisión completa'
            costo = [50000, 80000, 120000][i % 3]
            prox_fecha = None
            if tipo in ['preventivo', 'calibracion']:
                prox_fecha = (hoy + timedelta(days=180)).strftime('%Y-%m-%d')
            
            mantenimientos_demo.append((
                herr_id, fecha_mant, tipo, desc, f'Técnico {(i % 5) + 1}',
                'Proveedor Mantención SA' if i % 3 == 0 else None,
                costo, prox_fecha, None, f'Trabajo realizado OK', 'system'
            ))
        
        # Mantenimientos recientes que generan alertas (próximas fechas vencidas)
        for i in range(1, 11):
            fecha_mant = (hoy - timedelta(days=400)).strftime('%Y-%m-%d')
            herr_id = 15 + i
            tipo = 'preventivo' if i % 2 == 0 else 'calibracion'
            desc = f'Mantenimiento {tipo} programado'
            prox_fecha = (hoy - timedelta(days=30)).strftime('%Y-%m-%d')  # Vencido hace 30 días
            
            mantenimientos_demo.append((
                herr_id, fecha_mant, tipo, desc, 'Técnico Mantención',
                None, 75000, prox_fecha, None, 'Requiere nuevo mantenimiento', 'system'
            ))
        
        cursor.executemany('''
            INSERT INTO herramientas_mantenimiento (herramienta_id, fecha_mantenimiento, tipo, descripcion,
                                                    responsable_nombre, proveedor_nombre, costo, proxima_fecha,
                                                    certificado_path, observaciones, usuario_registro)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', mantenimientos_demo)
        
        print(f"  ✓ {len(mantenimientos_demo)} mantenimientos insertados")
        
        # 5. Planes de mantenimiento preventivo (15)
        planes_demo = [
            (3, 365, 'calibracion', 'Calibración anual multímetro digital', 45000, 1),
            (4, 365, 'calibracion', 'Calibración anual torquímetro', 85000, 1),
            (10, 365, 'calibracion', 'Calibración calibre digital', 65000, 1),
            (15, 365, 'calibracion', 'Calibración nivel láser', 125000, 1),
            (16, 180, 'preventivo', 'Cambio aceite y filtros compresor', 95000, 1),
            (17, 90, 'preventivo', 'Inspección talha eléctrica', 45000, 1),
            (18, 180, 'preventivo', 'Revisión válvulas oxicorte', 35000, 1),
            (25, 365, 'calibracion', 'Calibración llave torque digital', 95000, 1),
            (41, 365, 'calibracion', 'Calibración detector fugas', 285000, 1),
            (42, 365, 'calibracion', 'Calibración analizador vibraciones', 450000, 1),
            (43, 365, 'calibracion', 'Calibración medidor espesor', 185000, 1),
            (44, 730, 'calibracion', 'Calibración cámara termográfica (bianual)', 650000, 1),
            (45, 365, 'calibracion', 'Calibración balanza precisión', 95000, 1),
            (49, 365, 'calibracion', 'Calibración pinza amperimétrica', 125000, 1),
            (50, 365, 'calibracion', 'Calibración medidor aislación', 285000, 1),
        ]
        
        cursor.executemany('''
            INSERT INTO herramientas_planes_mantenimiento (herramienta_id, frecuencia_dias, tipo_mantenimiento,
                                                           descripcion, costo_estimado, activo)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', planes_demo)
        
        print(f"  ✓ {len(planes_demo)} planes de mantenimiento insertados")
        
        conn.commit()
        print("\n✓ Datos de demostración insertados correctamente")
        return True
        
    except Exception as e:
        print(f"\n✗ Error al insertar datos demo: {e}")
        conn.rollback()
        return False


def verificar_tablas(conn):
    """
    Verifica que las tablas se hayan creado correctamente
    """
    cursor = conn.cursor()
    
    try:
        tablas = [
            'empleados',
            'herramientas',
            'herramientas_movimientos',
            'herramientas_mantenimiento',
            'herramientas_planes_mantenimiento'
        ]
        
        print("\n🔍 Verificando tablas creadas...")
        for tabla in tablas:
            cursor.execute(f"SELECT COUNT(*) FROM {tabla}")
            count = cursor.fetchone()[0]
            print(f"  ✓ {tabla}: {count} registros")
        
        return True
        
    except Exception as e:
        print(f"✗ Error al verificar tablas: {e}")
        return False


if __name__ == '__main__':
    print("=" * 60)
    print("    CREACIÓN DE TABLAS DEL SISTEMA DE PAÑOL")
    print("=" * 60)
    print(f"\nBase de datos: {DB_PATH}")
    print()
    
    if not os.path.exists(DB_PATH):
        print(f"✗ Error: La base de datos no existe en {DB_PATH}")
        print("  Ejecute primero la aplicación para crear la base de datos")
        sys.exit(1)
    
    conn = sqlite3.connect(str(DB_PATH))
    
    try:
        exito = True
        
        # Paso 1: Crear tablas
        if not crear_tablas(conn):
            exito = False
        
        # Paso 2: Crear índices
        if exito and not crear_indices(conn):
            exito = False
        
        # Paso 3: Insertar datos demo
        if exito:
            respuesta = input("\n¿Desea insertar datos de demostración? (S/n): ").strip().lower()
            if respuesta in ['s', 'si', 'sí', 'yes', 'y', '']:
                if not insertar_datos_demo(conn):
                    exito = False
        
        # Paso 4: Verificar
        if exito:
            verificar_tablas(conn)
        
        if exito:
            print("\n" + "=" * 60)
            print("✓ PROCESO COMPLETADO EXITOSAMENTE")
            print("=" * 60)
            print("\nEl sistema de pañol está listo para usar.")
            print("Puede acceder a través de la interfaz web.")
        else:
            print("\n" + "=" * 60)
            print("✗ PROCESO COMPLETADO CON ERRORES")
            print("=" * 60)
            sys.exit(1)
            
    except Exception as e:
        print(f"\n✗ Error general: {e}")
        sys.exit(1)
    finally:
        conn.close()
