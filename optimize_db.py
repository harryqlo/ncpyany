"""
Script para optimizar la base de datos North Chrome
Ejecutar una sola vez para agregar índices
"""

import sqlite3
from pathlib import Path
from config import DB_PATH
from logger_config import logger


def create_indexes():
    """
    Crea índices en las tablas principales para mejorar performance
    """
    
    indexes = [
        # Items table
        "CREATE INDEX IF NOT EXISTS idx_items_sku ON items(sku)",
        "CREATE INDEX IF NOT EXISTS idx_items_categoria ON items(categoria_nombre)",
        "CREATE INDEX IF NOT EXISTS idx_items_stock ON items(stock_actual)",
        
        # Movimientos Ingreso
        "CREATE INDEX IF NOT EXISTS idx_ingreso_sku ON movimientos_ingreso(item_sku)",
        "CREATE INDEX IF NOT EXISTS idx_ingreso_fecha ON movimientos_ingreso(fecha_orden)",
        "CREATE INDEX IF NOT EXISTS idx_ingreso_proveedor ON movimientos_ingreso(proveedor_nombre)",
        
        # Movimientos Consumo
        "CREATE INDEX IF NOT EXISTS idx_consumo_sku ON movimientos_consumo(item_sku)",
        "CREATE INDEX IF NOT EXISTS idx_consumo_fecha ON movimientos_consumo(fecha_consumo)",
        "CREATE INDEX IF NOT EXISTS idx_consumo_solicitante ON movimientos_consumo(solicitante_nombre)",
        
        # Ordenes Trabajo
        "CREATE INDEX IF NOT EXISTS idx_ot_estado ON ordenes_trabajo(estado_ingreso)",
        "CREATE INDEX IF NOT EXISTS idx_ot_cliente ON ordenes_trabajo(cliente_nombre)",
    ]
    
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    
    created = 0
    already_exist = 0
    
    print("\n" + "="*60)
    print("OPTIMIZANDO BASE DE DATOS - CREANDO ÍNDICES")
    print("="*60 + "\n")
    
    for index_sql in indexes:
        try:
            cursor.execute(index_sql)
            created += 1
            print(f"✓ {index_sql.split('ON')[1].strip()}")
        except sqlite3.OperationalError as e:
            if "already exists" in str(e):
                already_exist += 1
            else:
                print(f"✗ Error: {e}")
                if logger:
                    logger.error(f"Error creando índice: {e}")
    
    conn.commit()
    conn.close()
    
    print("\n" + "-"*60)
    print(f"Índices creados: {created}")
    print(f"Ya existían: {already_exist}")
    print("="*60 + "\n")
    
    if logger:
        logger.info(f"Optimización BD completada: {created} índices nuevos")


def optimize_database():
    """
    Ejecuta VACUUM y ANALYZE para optimizar la BD
    """
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    
    print("\nEjecutando VACUUM (defragmentación)...")
    cursor.execute("VACUUM")
    
    print("Ejecutando ANALYZE (estadísticas)...")
    cursor.execute("ANALYZE")
    
    conn.commit()
    conn.close()
    
    print("✓ BD optimizada\n")
    
    if logger:
        logger.info("Base de datos optimizada (VACUUM + ANALYZE)")


if __name__ == '__main__':
    try:
        print("\n🔧 HERRAMIENTA DE OPTIMIZACIÓN - NORTH CHROME\n")
        
        # Crear índices
        create_indexes()
        
        # Optimizar
        optimize_database()
        
        print("✓ BD lista para producción")
        print("  - Índices creados para búsquedas rápidas")
        print("  - Defragmentación completada")
        print("  - Estadísticas actualizadas\n")
        
    except Exception as e:
        print(f"\n✗ Error durante optimización: {e}\n")
        if logger:
            logger.error(f"Error en optimización BD: {e}", exc_info=True)
