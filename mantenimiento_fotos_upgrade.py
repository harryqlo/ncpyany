"""
Script para extender el sistema de mantenimiento con fotografía profesional.
Agrega tablas de fotos comprimidas, índices y campos adicionales.
Ejecutar: python mantenimiento_fotos_upgrade.py
"""
import sqlite3
import os
import sys

# Agregar el directorio raíz al path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

try:
    from config import DB_PATH
except ImportError:
    SYSTEM_DIR = os.path.join(BASE_DIR, 'system')
    DB_PATH = os.path.join(SYSTEM_DIR, 'system.db')


def extender_tablas_mantenimiento(conn):
    """Agrega campos a tabla existente y crea nuevas tablas para fotos"""
    cursor = conn.cursor()
    
    try:
        # 1. Verificar si la tabla herramientas_mantenimiento_fotos ya existe
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='herramientas_mantenimiento_fotos'"
        )
        if cursor.fetchone():
            print("⚠ Tabla herramientas_mantenimiento_fotos ya existe")
        else:
            # Crear tabla para fotos comprimidas (evidencia fotográfica)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS herramientas_mantenimiento_fotos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    mantenimiento_id INTEGER NOT NULL,
                    herramienta_id INTEGER NOT NULL,
                    
                    -- Información de la foto
                    nombre_original TEXT,
                    tipo_foto TEXT CHECK(tipo_foto IN ('antes', 'durante', 'despues', 'documentacion')),
                    descripcion TEXT,
                    
                    -- Datos de la imagen comprimida
                    foto_blob BLOB NOT NULL,
                    tamaño_kb REAL DEFAULT 0,
                    ancho INTEGER,
                    alto INTEGER,
                    formato TEXT DEFAULT 'webp',
                    
                    -- Metadatos
                    usuario_uploaded TEXT,
                    fecha_uploaded TEXT DEFAULT (datetime('now')),
                    
                    FOREIGN KEY (mantenimiento_id) REFERENCES herramientas_mantenimiento(id) ON DELETE CASCADE,
                    FOREIGN KEY (herramienta_id) REFERENCES herramientas(id) ON DELETE CASCADE
                )
            ''')
            print("✓ Tabla herramientas_mantenimiento_fotos creada")
        
        # 2. Crear tabla para documentos/certificados (PDF, etc)
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='herramientas_mantenimiento_documentos'"
        )
        if cursor.fetchone():
            print("⚠ Tabla herramientas_mantenimiento_documentos ya existe")
        else:
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS herramientas_mantenimiento_documentos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    mantenimiento_id INTEGER NOT NULL,
                    herramienta_id INTEGER NOT NULL,
                    
                    -- Información del documento
                    nombre TEXT NOT NULL,
                    tipo_documento TEXT CHECK(tipo_documento IN ('certificado', 'orden_trabajo', 'cotizacion', 'reporte', 'otro')),
                    descripcion TEXT,
                    
                    -- Datos del archivo
                    archivo_blob BLOB NOT NULL,
                    tamaño_kb REAL DEFAULT 0,
                    formato TEXT DEFAULT 'pdf',
                    
                    -- Metadatos
                    usuario_uploaded TEXT,
                    fecha_uploaded TEXT DEFAULT (datetime('now')),
                    
                    FOREIGN KEY (mantenimiento_id) REFERENCES herramientas_mantenimiento(id) ON DELETE CASCADE,
                    FOREIGN KEY (herramienta_id) REFERENCES herramientas(id) ON DELETE CASCADE
                )
            ''')
            print("✓ Tabla herramientas_mantenimiento_documentos creada")
        
        # 3. Extender tabla principal con nuevos campos (si no existen ya)
        cursor.execute("PRAGMA table_info(herramientas_mantenimiento)")
        columnas = [col[1] for col in cursor.fetchall()]
        
        # Campos que podría necesitar agregar
        campos_nuevos = {
            'presupuesto': "REAL DEFAULT 0.0",
            'costo_final': "REAL DEFAULT 0.0",
            'tiempo_estimado_horas': "REAL DEFAULT 0.0",
            'tiempo_real_horas': "REAL DEFAULT 0.0",
            'estado_mant': "TEXT DEFAULT 'programado' CHECK(estado_mant IN ('programado', 'en_proceso', 'completado', 'cancelado'))",
            'tecnico_nombre': "TEXT",
            'taller_nombre': "TEXT",
            'numero_orden_trabajo': "TEXT",
            'nota_interna': "TEXT",
            'cantidad_fotos': "INTEGER DEFAULT 0",
            'cantidad_documentos': "INTEGER DEFAULT 0"
        }
        
        for campo, tipo in campos_nuevos.items():
            if campo not in columnas:
                try:
                    cursor.execute(f"ALTER TABLE herramientas_mantenimiento ADD COLUMN {campo} {tipo}")
                    print(f"  + Campo agregado: {campo}")
                except sqlite3.OperationalError:
                    pass  # Campo ya existe o hay conflicto
        
        conn.commit()
        return True
    
    except Exception as e:
        print(f"✗ Error extendiendo tablas: {e}")
        conn.rollback()
        return False


def crear_indices_fotos(conn):
    """Crea índices para optimizar consultas de fotos"""
    cursor = conn.cursor()
    
    try:
        # Índices para fotos
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_mant_fotos_herr ON herramientas_mantenimiento_fotos(herramienta_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_mant_fotos_mant ON herramientas_mantenimiento_fotos(mantenimiento_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_mant_fotos_tipo ON herramientas_mantenimiento_fotos(tipo_foto)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_mant_fotos_fecha ON herramientas_mantenimiento_fotos(fecha_uploaded)')
        
        # Índices para documentos
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_mant_docs_herr ON herramientas_mantenimiento_documentos(herramienta_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_mant_docs_mant ON herramientas_mantenimiento_documentos(mantenimiento_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_mant_docs_tipo ON herramientas_mantenimiento_documentos(tipo_documento)')
        
        conn.commit()
        print("✓ Índices para fotos y documentos creados")
        return True
    
    except Exception as e:
        print(f"✗ Error creando índices: {e}")
        conn.rollback()
        return False


if __name__ == '__main__':
    print("=" * 70)
    print("    EXTENSIÓN DE SISTEMA DE MANTENIMIENTO - FOTOGRAFÍA PROFESIONAL")
    print("=" * 70)
    print(f"\nBase de datos: {DB_PATH}\n")
    
    if not os.path.exists(DB_PATH):
        print(f"✗ Error: La base de datos no existe en {DB_PATH}")
        sys.exit(1)
    
    conn = sqlite3.connect(str(DB_PATH))
    
    try:
        exito = True
        
        # Paso 1: Extender tablas
        if not extender_tablas_mantenimiento(conn):
            exito = False
        
        # Paso 2: Crear índices
        if exito and not crear_indices_fotos(conn):
            exito = False
        
        if exito:
            print("\n✓ Extensión completada exitosamente")
            print("\nNuevas tablas:")
            print("  - herramientas_mantenimiento_fotos (para evidencia fotográfica comprimida)")
            print("  - herramientas_mantenimiento_documentos (para certificados, órdenes, etc)")
            print("\nCampos agregados a herramientas_mantenimiento:")
            print("  - presupuesto, costo_final, tiempo estimado/real")
            print("  - estado_mant, técnico, taller, número de orden")
            print("  - contadores de fotos y documentos")
        else:
            print("\n✗ Error durante la extensión")
            sys.exit(1)
    
    finally:
        conn.close()
