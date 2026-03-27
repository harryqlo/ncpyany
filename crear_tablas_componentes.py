"""
Script para crear las tablas de componentes en la base de datos.
Ejecutar: python crear_tablas_componentes.py
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

def crear_tablas():
    """
    Crea las tablas necesarias para la funcionalidad de componentes
    """
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    
    try:
        # Tabla de componentes
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS componentes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT NOT NULL,
                codigo TEXT,
                descripcion TEXT,
                fecha_creacion INTEGER DEFAULT (cast(julianday('now') - 2440587.5 as integer) * 86400)
            )
        ''')
        
        # Tabla de materiales de componentes (relación muchos a muchos)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS componentes_materiales (
                componente_id INTEGER NOT NULL,
                item_sku TEXT NOT NULL,
                cantidad_necesaria REAL NOT NULL DEFAULT 1,
                PRIMARY KEY (componente_id, item_sku),
                FOREIGN KEY (componente_id) REFERENCES componentes(id) ON DELETE CASCADE,
                FOREIGN KEY (item_sku) REFERENCES items(sku) ON DELETE CASCADE
            )
        ''')
        
        # Crear índices para mejorar el rendimiento
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_comp_nombre ON componentes(nombre)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_comp_codigo ON componentes(codigo)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_comp_mat_comp ON componentes_materiales(componente_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_comp_mat_sku ON componentes_materiales(item_sku)')
        
        conn.commit()
        print("✓ Tablas de componentes creadas correctamente")
        print("  - componentes")
        print("  - componentes_materiales")
        
    except Exception as e:
        print(f"✗ Error al crear tablas: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()
    
    return True

if __name__ == '__main__':
    print("=== Creación de tablas de componentes ===")
    print(f"Base de datos: {DB_PATH}")
    print()
    
    if not os.path.exists(DB_PATH):
        print(f"✗ Error: La base de datos no existe en {DB_PATH}")
        sys.exit(1)
    
    if crear_tablas():
        print()
        print("✓ Proceso completado exitosamente")
    else:
        print()
        print("✗ Proceso completado con errores")
        sys.exit(1)
