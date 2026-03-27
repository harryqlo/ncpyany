
import sqlite3
import os
from datetime import datetime, timedelta

# Importar configuración y logger
try:
    from config import DB_PATH
    from logger_config import logger
except ImportError:
    # Fallback si no están disponibles
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    SYSTEM_DIR = os.path.join(BASE_DIR, 'system')
    DB_PATH = os.path.join(SYSTEM_DIR, 'system.db')
    logger = None

# CONSTANTES DE CONFIGURACIÓN
EXCEL_DATE_EPOCH = datetime(1899, 12, 30)
ISO_DATE_FORMAT = '%Y-%m-%d'

def get_db(module='general'):
    """
    Obtiene conexión a base de datos SQLite según el módulo.
    
    Módulos disponibles:
    - 'bodega': Gestión de componentes/materiales
    - 'paniol': Control de herramientas y préstamos
    - 'general': Órdenes, ingresos, consumos, config (default)

    Args:
        module (str): Módulo solicitado ('bodega', 'paniol', 'general')

    Returns:
        sqlite3.Connection: Conexión a BD del módulo
    """
    try:
        from config import DATABASES
        db_config = DATABASES.get(module, DATABASES.get('general'))
        db_path = db_config['path']
    except (ImportError, KeyError):
        # Fallback si no está disponible
        db_path = DB_PATH
    
    try:
        from flask import current_app
        # En tests, permitir override de la BD
        db_path = current_app.config.get('DATABASE', db_path)
    except RuntimeError:
        # Sin contexto Flask, usar config
        pass

    conn = sqlite3.connect(str(db_path), timeout=15.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=15000")
    return conn


def excel_to_date(serial):
    """
    Convierte número serial de Excel a fecha ISO (YYYY-MM-DD)
    
    Args:
        serial: Número serial de Excel o string de fecha
        
    Returns:
        str: Fecha en formato YYYY-MM-DD, None si es inválido
    """
    if serial is None:
        return None
    
    # Si ya es string, intentar primero ISO y luego serial numérico
    if isinstance(serial, str):
        serial_clean = serial.strip()
        if not serial_clean:
            return None
        try:
            datetime.strptime(serial_clean[:10], ISO_DATE_FORMAT)
            return serial_clean[:10]
        except ValueError:
            try:
                serial_float = float(serial_clean)
                if serial_float < 1:
                    return None
                excel_date = EXCEL_DATE_EPOCH + timedelta(days=serial_float)
                return excel_date.strftime(ISO_DATE_FORMAT)
            except (ValueError, TypeError):
                if logger:
                    logger.warning(f"Fecha inválida (string): {serial}")
                return None
    
    # Convertir desde serial de Excel
    try:
        serial_float = float(serial)
        if serial_float < 1:
            return None
        
        excel_date = EXCEL_DATE_EPOCH + timedelta(days=serial_float)
        return excel_date.strftime(ISO_DATE_FORMAT)
    except (ValueError, TypeError) as e:
        if logger:
            logger.warning(f"Error convirtiendo Excel date {serial}: {e}")
        return None


def date_to_excel(date_string):
    """
    Convierte fecha ISO a número serial de Excel
    
    Args:
        date_string: Fecha en formato YYYY-MM-DD
        
    Returns:
        int: Número serial de Excel, None si es inválido
    """
    if not date_string:
        return None
    
    try:
        date_obj = datetime.strptime(date_string[:10], ISO_DATE_FORMAT)
        delta = date_obj - EXCEL_DATE_EPOCH
        return delta.days
    except (ValueError, TypeError) as e:
        if logger:
            logger.warning(f"Error convirtiendo a Excel date {date_string}: {e}")
        return None


def parse_price(val):
    """
    Convierte valor a float seguro
    
    Args:
        val: Valor a convertir
        
    Returns:
        float: Valor numérico, 0.0 si no puede convertir
    """
    if val is None:
        return 0.0
    if isinstance(val, (int, float)):
        return float(val)
    try:
        return float(str(val).replace('$', '').replace(',', '').strip())
    except (ValueError, TypeError):
        return 0.0
