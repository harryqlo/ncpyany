"""
Configuración centralizada de Logging - North Chrome v2
Logging para app general y auditoría
"""

import logging
import logging.handlers
import json
import hashlib
from pathlib import Path
from datetime import datetime, timezone
from config import (
    LOG_LEVEL,
    LOG_FORMAT,
    LOG_FILE,
    AUDIT_LOG_FILE,
    AUDIT_IMMUTABLE_LOG_FILE,
    ALERTS_LOG_FILE,
    LOG_MAX_SIZE,
    LOG_BACKUP_COUNT,
)

# ═══════════════════════════════════════════════════════════════
# NIVELES DE LOG
# ═══════════════════════════════════════════════════════════════

LOG_LEVELS = {
    'DEBUG': logging.DEBUG,
    'INFO': logging.INFO,
    'WARNING': logging.WARNING,
    'ERROR': logging.ERROR,
    'CRITICAL': logging.CRITICAL,
}


# ═══════════════════════════════════════════════════════════════
# SETUP LOGGING
# ═══════════════════════════════════════════════════════════════

def setup_logging():
    """
    Configura logging centralizado para toda la aplicación
    
    Returns:
        tuple: (logger_general, logger_auditoria)
    """
    
    # Logger raíz
    root_logger = logging.getLogger()
    root_logger.setLevel(LOG_LEVELS.get(LOG_LEVEL, logging.INFO))
    
    # Formateador
    formatter = logging.Formatter(LOG_FORMAT)
    
    # ───────────────────────────────────────────────────────────
    # HANDLER: ARCHIVO DE APLICACIÓN
    # ───────────────────────────────────────────────────────────
    
    file_handler = logging.handlers.RotatingFileHandler(
        LOG_FILE,
        maxBytes=LOG_MAX_SIZE,  # 10 MB
        backupCount=LOG_BACKUP_COUNT,  # 10 archivos
    )
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)
    
    # ───────────────────────────────────────────────────────────
    # HANDLER: CONSOLA
    # ───────────────────────────────────────────────────────────
    
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.INFO)  # Solo INFO+ en consola
    root_logger.addHandler(console_handler)
    
    # ───────────────────────────────────────────────────────────
    # LOGGER ESPECÍFICO: AUDITORÍA
    # ───────────────────────────────────────────────────────────
    
    audit_logger = logging.getLogger('audit')
    audit_logger.setLevel(logging.INFO)
    audit_logger.propagate = False  # No duplicar en root logger
    
    # Handler para auditoría
    audit_handler = logging.handlers.RotatingFileHandler(
        AUDIT_LOG_FILE,
        maxBytes=LOG_MAX_SIZE,
        backupCount=LOG_BACKUP_COUNT,
    )
    audit_handler.setFormatter(formatter)
    audit_logger.addHandler(audit_handler)
    
    return root_logger, audit_logger


# ═══════════════════════════════════════════════════════════════
# LOGGERS GLOBALES
# ═══════════════════════════════════════════════════════════════

logger, audit_logger = setup_logging()


def _read_last_hash(file_path: Path) -> str:
    """Lee el hash de la última línea de la bitácora inmutable."""
    if not file_path.exists():
        return 'GENESIS'

    try:
        last_line = ''
        with file_path.open('r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    last_line = line.strip()

        if not last_line:
            return 'GENESIS'

        payload = json.loads(last_line)
        return payload.get('hash', 'GENESIS')
    except Exception:
        return 'GENESIS'


def log_immutable_event(event_type: str, payload: dict, actor: str = 'system'):
    """
    Registra un evento en una bitácora inmutable encadenada por hash.

    Esto no reemplaza la auditoría tradicional, la refuerza con encadenamiento.
    """
    immutable_path = Path(AUDIT_IMMUTABLE_LOG_FILE)
    immutable_path.parent.mkdir(parents=True, exist_ok=True)

    prev_hash = _read_last_hash(immutable_path)
    event = {
        'ts': datetime.now(timezone.utc).isoformat(),
        'event_type': event_type,
        'actor': actor,
        'payload': payload,
        'prev_hash': prev_hash,
    }
    serialized = json.dumps(event, ensure_ascii=True, sort_keys=True)
    event_hash = hashlib.sha256(serialized.encode('utf-8')).hexdigest()
    event['hash'] = event_hash

    with immutable_path.open('a', encoding='utf-8') as f:
        f.write(json.dumps(event, ensure_ascii=True, sort_keys=True) + '\n')


def log_alert(alert_type: str, severity: str, details: str):
    """Registra alertas operativas en logger y archivo dedicado."""
    level = severity.upper()
    msg = f"[{alert_type}] severity={level} details={details}"
    if level in ('CRITICAL', 'HIGH'):
        logger.error(msg)
    elif level == 'MEDIUM':
        logger.warning(msg)
    else:
        logger.info(msg)

    alerts_path = Path(ALERTS_LOG_FILE)
    alerts_path.parent.mkdir(parents=True, exist_ok=True)
    line = f"{datetime.now().isoformat()}|{alert_type}|{level}|{details}\n"
    with alerts_path.open('a', encoding='utf-8') as f:
        f.write(line)


# ═══════════════════════════════════════════════════════════════
# FUNCIONES DE LOGGING ESPECIALIZADAS
# ═══════════════════════════════════════════════════════════════

def log_operation(operation: str, resource: str, details: str, 
                 user: str = "system", success: bool = True, 
                 ip: str = None):
    """
    Registra una operación en el log de auditoría
    
    Args:
        operation: CREATE, READ, UPDATE, DELETE
        resource: items, ingresos, consumos, ordenes
        details: Descripción de qué cambió
        user: Usuario que ejecutó la operación
        success: Si fue exitosa
        ip: IP del cliente
    """
    status = "SUCCESS" if success else "FAILED"
    audit_logger.info(
        f"[{status}] user={user} op={operation} resource={resource} "
        f"details={details} ip={ip}"
    )

    log_immutable_event(
        event_type=f"{operation}_{resource}".upper(),
        payload={
            'status': status,
            'resource': resource,
            'details': details,
            'ip': ip,
        },
        actor=user,
    )


def log_error_detailed(error: Exception, context: str = "", 
                       user: str = "system"):
    """
    Registra un error con contexto detallado
    
    Args:
        error: La excepción
        context: Contexto donde ocurrió
        user: Usuario asociado
    """
    logger.error(
        f"Error en {context}: {str(error)}",
        exc_info=True,
        extra={'user': user}
    )


def log_performance(operation: str, duration_ms: float, 
                   resource_count: int = 0):
    """
    Registra métricas de performance
    
    Args:
        operation: Nombre de la operación
        duration_ms: Tiempo en milisegundos
        resource_count: Cantidad de recursos procesados
    """
    if duration_ms > 1000:  # Log si toma más de 1 segundo
        logger.warning(
            f"Operación lenta: {operation} ({duration_ms:.1f}ms, "
            f"{resource_count} recursos)"
        )


def log_security_event(event_type: str, details: str, 
                       user: str = "unknown", ip: str = None):
    """
    Registra evento de seguridad
    
    Args:
        event_type: LOGIN_FAILED, UNAUTHORIZED_ACCESS, etc
        details: Descripción del evento
        user: Usuario invol ucrado
        ip: IP de origen
    """
    audit_logger.warning(
        f"[SECURITY] {event_type}: user={user} ip={ip} details={details}"
    )


# ═══════════════════════════════════════════════════════════════
# CONFIGURACIÓN DE LOGGERS ESPECÍFICOS
# ═══════════════════════════════════════════════════════════════

def get_logger(name: str) -> logging.Logger:
    """
    Obtiene un logger específico para un módulo
    
    Args:
        name: Nombre del módulo (__name__)
        
    Returns:
        Logger configurado
    """
    return logging.getLogger(name)


# Loggers para módulos específicos
logger_auth = get_logger('auth')
logger_inventory = get_logger('inventory')
logger_ingresos = get_logger('ingresos')
logger_consumos = get_logger('consumos')
logger_ordenes = get_logger('ordenes')


if __name__ == '__main__':
    # Test logging
    print("Testando sistema de logging...\n")
    
    logger.info("Mensaje INFO - Aplicación")
    logger.warning("Mensaje WARNING - Aplicación")
    
    audit_logger.info("[SUCCESS] user=admin op=CREATE resource=items details=Producto ABC-001 creado")
    
    log_operation(
        operation="CREATE",
        resource="items",
        details="SKU ABC-001 - Producto Test",
        user="admin",
        success=True
    )
    
    log_security_event(
        event_type="UNAUTHORIZED_ACCESS",
        details="Intento de acceso sin autenticación",
        user="unknown",
        ip="192.168.1.100"
    )
    
    print("✓ Logging configurado correctamente")
    print(f"✓ Archivo de logs: {LOG_FILE}")
    print(f"✓ Archivo de auditoría: {AUDIT_LOG_FILE}")
