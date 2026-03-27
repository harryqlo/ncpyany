"""
Configuración centralizada de North Chrome v2
Centraliza todas las constantes y ajustes del sistema
"""

import os
from pathlib import Path
from datetime import timedelta

# ═══════════════════════════════════════════════════════════════
# RUTAS
# ═══════════════════════════════════════════════════════════════

BASE_DIR = Path(__file__).parent.absolute()
SYSTEM_DIR = BASE_DIR / 'system'
BACKUP_DIR = SYSTEM_DIR / 'backups'
LOGS_DIR = BASE_DIR / 'logs'

# Crear carpetas si no existen
LOGS_DIR.mkdir(exist_ok=True)
BACKUP_DIR.mkdir(exist_ok=True)

# ═══════════════════════════════════════════════════════════════
# BASE DE DATOS - MÓDULOS SEPARADOS
# ═══════════════════════════════════════════════════════════════

# Ruta legacy principal (actual instalación productiva)
DB_LEGACY = SYSTEM_DIR / 'system.db'

# Rutas por módulo (pueden separarse por variables de entorno cuando exista migración)
DB_BODEGA = Path(os.getenv('DB_BODEGA_PATH', str(DB_LEGACY)))
DB_PANIOL = Path(os.getenv('DB_PANIOL_PATH', str(DB_LEGACY)))
DB_GENERAL = Path(os.getenv('DB_GENERAL_PATH', str(DB_LEGACY)))
DB_PATH = DB_LEGACY  # compatibilidad con scripts y rutas legacy

# Configuración por módulo
DATABASES = {
    'bodega': {
        'path': str(DB_BODEGA),
        'timeout': 30,
        'check_same_thread': False,
        'journal_mode': 'WAL',
    },
    'paniol': {
        'path': str(DB_PANIOL),
        'timeout': 30,
        'check_same_thread': False,
        'journal_mode': 'WAL',
    },
    'general': {
        'path': str(DB_GENERAL),
        'timeout': 30,
        'check_same_thread': False,
        'journal_mode': 'WAL',
    }
}

# Configuración genérica (compatibilidad legacy)
# Copia defensiva para evitar mutaciones globales desde clases de entorno.
DATABASE = dict(DATABASES['general'])

# ═══════════════════════════════════════════════════════════════
# CONFIGURACIÓN DE HERRAMIENTAS
# ═══════════════════════════════════════════════════════════════

HERRAMIENTAS_PREFIX_DEFAULT = 'NC'  # North Chrome - prefijo automático
HERRAMIENTAS_SKU_SEPARATOR = '-'    # Separador para SKU (NC-001, NC-002, etc)

# ═══════════════════════════════════════════════════════════════
# FLASK CONFIGURATION
# ═══════════════════════════════════════════════════════════════

FLASK_ENV = os.getenv('FLASK_ENV', 'development')
DEBUG = FLASK_ENV == 'development'
SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
IS_PRODUCTION = FLASK_ENV.lower() == 'production'


def _get_int_env(name, default):
    try:
        return int(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default


AUTH_TOKEN_TTL_HOURS = _get_int_env('AUTH_TOKEN_TTL_HOURS', 8 if IS_PRODUCTION else 12)
PASSWORD_MIN_LENGTH = _get_int_env('PASSWORD_MIN_LENGTH', 10 if IS_PRODUCTION else 3)
PASSWORD_REQUIRE_UPPER = os.getenv('PASSWORD_REQUIRE_UPPER', '1' if IS_PRODUCTION else '0').strip().lower() in ('1', 'true', 'yes', 'on')
PASSWORD_REQUIRE_LOWER = os.getenv('PASSWORD_REQUIRE_LOWER', '1' if IS_PRODUCTION else '0').strip().lower() in ('1', 'true', 'yes', 'on')
PASSWORD_REQUIRE_DIGIT = os.getenv('PASSWORD_REQUIRE_DIGIT', '1' if IS_PRODUCTION else '0').strip().lower() in ('1', 'true', 'yes', 'on')

# En producción, por seguridad no se deben crear usuarios por defecto inseguros.
ALLOW_INSECURE_DEFAULT_USERS = os.getenv('ALLOW_INSECURE_DEFAULT_USERS', '0').strip().lower() in ('1', 'true', 'yes', 'on')
BOOTSTRAP_ADMIN_USERNAME = os.getenv('BOOTSTRAP_ADMIN_USERNAME', 'admin').strip() or 'admin'
BOOTSTRAP_ADMIN_PASSWORD = os.getenv('BOOTSTRAP_ADMIN_PASSWORD', '').strip()
BOOTSTRAP_CNC_PASSWORD = os.getenv('BOOTSTRAP_CNC_PASSWORD', '').strip()

# Endurecimiento de login
LOGIN_MAX_ATTEMPTS = _get_int_env('LOGIN_MAX_ATTEMPTS', 5)
LOGIN_LOCKOUT_MINUTES = _get_int_env('LOGIN_LOCKOUT_MINUTES', 15)

# Sesión
PERMANENT_SESSION_LIFETIME = timedelta(hours=8)
SESSION_REFRESH_EACH_REQUEST = True

# CORS
CORS_ALLOWED_ORIGINS = (
    os.getenv('ALLOWED_ORIGINS', 'http://localhost:5000').split(',')
)

# ═══════════════════════════════════════════════════════════════
# LOGGING
# ═══════════════════════════════════════════════════════════════

LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
LOG_FILE = LOGS_DIR / 'app.log'
AUDIT_LOG_FILE = LOGS_DIR / 'audit.log'
AUDIT_IMMUTABLE_LOG_FILE = LOGS_DIR / 'audit_immutable.log'
ALERTS_LOG_FILE = LOGS_DIR / 'alerts.log'

# Configuración de rotación de logs
LOG_MAX_SIZE = 10 * 1024 * 1024  # 10 MB
LOG_BACKUP_COUNT = 10

# ═══════════════════════════════════════════════════════════════
# API CONFIGURATION
# ═══════════════════════════════════════════════════════════════

API_CONFIG = {
    'items_per_page': 50,
    'max_items_per_page': 200,
    'search_limit': 20,
    'timeout_seconds': 30,
}

# JSON
JSON_SORT_KEYS = False
MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB max upload

# ═══════════════════════════════════════════════════════════════
# VALIDACIÓN DE DATOS
# ═══════════════════════════════════════════════════════════════

VALIDATION = {
    'sku': {
        'min_length': 1,
        'max_length': 20,
        'pattern': r'^[A-Z0-9-]+$',  # Alfanumérico + guiones
    },
    'nombre': {
        'min_length': 1,
        'max_length': 200,
    },
    'stock': {
        'min_value': 0,
        'max_value': 999999,
    },
    'precio': {
        'min_value': 0.0,
        'max_value': 999999.99,
    },
}

# ═══════════════════════════════════════════════════════════════
# ALERTAS Y UMBRALES
# ═══════════════════════════════════════════════════════════════

ALERTS = {
    'stock_critico': 5,  # Stock crítico si <= 5
    'stock_bajo': 50,    # Stock bajo si <= 50
    'prestamo_vencido_dias': 30,
    'email_on_alert': False,  # Para implementar luego
    'email_recipients': [],
}

OPERATIONS_JOBS = {
    'daily_time': '07:30',
    'weekly_restore_day': 'SUN',
    'weekly_restore_time': '08:00',
}

# ═══════════════════════════════════════════════════════════════
# BACKUP
# ═══════════════════════════════════════════════════════════════

BACKUP_CONFIG = {
    'retention_days': 30,
    'auto_backup_enabled': True,
    'schedule': 'daily',  # daily, weekly
}

# ═══════════════════════════════════════════════════════════════
# DATES Y CONVERSIÓN
# ═══════════════════════════════════════════════════════════════

EXCEL_DATE_EPOCH = None  # Se calcula en logger
ISO_DATE_FORMAT = '%Y-%m-%d'
EXCEL_DATE_FORMAT = 'MM/DD/YYYY'

# ═══════════════════════════════════════════════════════════════
# CONFIGURACIONES DE UI / PREFERENCIAS
# ═══════════════════════════════════════════════════════════════

UI_DEFAULTS = {
    'fontSize': 'normal',
    'fontFamily': 'system',
    'density': 'normal',
    'colorScheme': 'auto',
    'accentColor': 'orange',
    'lineHeight': '1.5',
    'compactMode': False,
    'theme': 'professional',
    'animationsEnabled': True,
    'notifications': True,
    'autoRefresh': True,
    'autoRefreshInterval': 60000,
}

FONT_SIZES = {
    'small': {'base': '12px', 'md': '13px', 'lg': '18px', 'title': '16px'},
    'normal': {'base': '14px', 'md': '14px', 'lg': '20px', 'title': '18px'},
    'large': {'base': '16px', 'md': '16px', 'lg': '24px', 'title': '22px'},
    'xlarge': {'base': '18px', 'md': '18px', 'lg': '28px', 'title': '26px'},
}

# ═══════════════════════════════════════════════════════════════
# CONFIGURACIONES POR AMBIENTE
# ═══════════════════════════════════════════════════════════════

class DevelopmentConfig:
    """Configuración para desarrollo"""
    DEBUG = True
    TESTING = False
    LOG_LEVEL = 'DEBUG'

class ProductionConfig:
    """Configuración para producción"""
    DEBUG = False
    TESTING = False
    LOG_LEVEL = 'WARNING'
    PERMANENT_SESSION_LIFETIME = timedelta(hours=4)

class TestingConfig:
    """Configuración para tests"""
    TESTING = True
    DATABASE_PATH = ':memory:'
    LOG_LEVEL = 'CRITICAL'

# ═══════════════════════════════════════════════════════════════
# FACTORY DE CONFIGURACIÓN
# ═══════════════════════════════════════════════════════════════

def get_config(env=None):
    """Retorna la configuración apropiada según el ambiente"""
    if env is None:
        env = FLASK_ENV
    
    configs = {
        'development': DevelopmentConfig,
        'production': ProductionConfig,
        'testing': TestingConfig,
    }
    
    return configs.get(env, DevelopmentConfig)


def print_config_summary():
    """Imprime resumen de configuración actual"""
    print("\n" + "="*60)
    print("CONFIGURACIÓN NORTH CHROME - RESUMEN")
    print("="*60)
    print(f"Ambiente: {FLASK_ENV}")
    print(f"Base de datos: {DB_PATH}")
    print(f"Logs: {LOG_FILE}")
    print(f"API items por página: {API_CONFIG['items_per_page']}")
    print(f"Stock crítico: {ALERTS['stock_critico']} unidades")
    print(f"Stock bajo: {ALERTS['stock_bajo']} unidades")
    print(f"Retención backups: {BACKUP_CONFIG['retention_days']} días")
    print("="*60 + "\n")


if __name__ == '__main__':
    print_config_summary()
