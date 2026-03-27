"""
Validadores de entrada - North Chrome v2
Valida y sanitiza todos los inputs del sistema
"""

import re
from typing import Any, Dict, Tuple
from config import VALIDATION


class ValidationError(Exception):
    """Excepción personalizada para errores de validación"""
    def __init__(self, message: str, field: str = None):
        self.message = message
        self.field = field
        super().__init__(self.message)


# ═══════════════════════════════════════════════════════════════
# VALIDADORES INDIVIDUALES
# ═══════════════════════════════════════════════════════════════

def validate_sku(sku: str) -> str:
    """
    Valida y normaliza SKU.
    
    Args:
        sku: Código SKU a validar
        
    Returns:
        str: SKU normalizado (mayúsculas)
        
    Raises:
        ValidationError: Si el SKU es inválido
        
    Examples:
        >>> validate_sku("abc-001")
        'ABC-001'
        
        >>> validate_sku("invalid@sku")
        ValidationError: SKU solo puede contener letras, números y guiones
    """
    if not sku or not isinstance(sku, str):
        raise ValidationError("SKU es requerido y debe ser texto", "sku")
    
    sku = sku.strip().upper()
    
    config = VALIDATION['sku']
    
    # Verificar longitud
    if len(sku) < config['min_length']:
        raise ValidationError(
            f"SKU mínimo {config['min_length']} caracteres",
            "sku"
        )
    
    if len(sku) > config['max_length']:
        raise ValidationError(
            f"SKU máximo {config['max_length']} caracteres",
            "sku"
        )
    
    # Verificar patrón
    if not re.match(config['pattern'], sku):
        raise ValidationError(
            "SKU solo puede contener letras, números y guiones",
            "sku"
        )
    
    return sku


def validate_nombre(nombre: str) -> str:
    """Valida nombre de producto"""
    if not nombre or not isinstance(nombre, str):
        raise ValidationError("Nombre es requerido y debe ser texto", "nombre")
    
    nombre = nombre.strip()
    
    config = VALIDATION['nombre']
    
    if len(nombre) < config['min_length']:
        raise ValidationError(
            f"Nombre mínimo {config['min_length']} caracteres",
            "nombre"
        )
    
    if len(nombre) > config['max_length']:
        raise ValidationError(
            f"Nombre máximo {config['max_length']} caracteres",
            "nombre"
        )
    
    return nombre


def validate_cantidad(cantidad: Any) -> float:
    """
    Valida cantidad numérica (stock)
    
    Args:
        cantidad: Valor a validar
        
    Returns:
        float: Cantidad validada
        
    Raises:
        ValidationError: Si la cantidad es inválida
    """
    try:
        qty = float(cantidad)
    except (ValueError, TypeError):
        raise ValidationError(
            "Cantidad debe ser número válido",
            "cantidad"
        )
    
    config = VALIDATION['stock']
    
    if qty < config['min_value']:
        raise ValidationError(
            f"Cantidad mínima: {config['min_value']}",
            "cantidad"
        )
    
    if qty > config['max_value']:
        raise ValidationError(
            f"Cantidad máxima: {config['max_value']}",
            "cantidad"
        )
    
    return qty


def validate_precio(precio: Any) -> float:
    """Valida precio unitario"""
    try:
        pr = float(precio)
    except (ValueError, TypeError):
        raise ValidationError(
            "Precio debe ser número válido",
            "precio"
        )
    
    config = VALIDATION['precio']
    
    if pr < config['min_value']:
        raise ValidationError(
            f"Precio mínimo: {config['min_value']}",
            "precio"
        )
    
    if pr > config['max_value']:
        raise ValidationError(
            f"Precio máximo: {config['max_value']}",
            "precio"
        )
    
    return pr


def validate_string(value: Any, max_length: int = 200, field_name: str = "Campo") -> str:
    """Valida cadena de texto genérica"""
    if not isinstance(value, str):
        value = str(value) if value is not None else ""
    
    value = value.strip()
    
    if len(value) > max_length:
        raise ValidationError(
            f"{field_name} máximo {max_length} caracteres",
            field_name.lower()
        )
    
    return value


# ═══════════════════════════════════════════════════════════════
# VALIDADORES COMPLEJOS
# ═══════════════════════════════════════════════════════════════

def validate_item_data(data: Dict) -> Dict:
    """
    Valida todos los datos de un producto
    
    Args:
        data: Diccionario con datos del producto
        
    Returns:
        dict: Datos validados y normalizados
        
    Raises:
        ValidationError: Si hay errores en validación
    """
    validated = {}
    
    # SKU (requerido)
    try:
        validated['sku'] = validate_sku(data.get('sku', ''))
    except ValidationError as e:
        raise e
    
    # Nombre (requerido)
    try:
        validated['nombre'] = validate_nombre(data.get('nombre', ''))
    except ValidationError as e:
        raise e
    
    # Stock (opcional, default 0)
    try:
        validated['stock'] = validate_cantidad(data.get('stock', 0))
    except ValidationError:
        validated['stock'] = 0.0
    
    # Precio (opcional, default 0)
    try:
        validated['precio'] = validate_precio(data.get('precio', 0))
    except ValidationError:
        validated['precio'] = 0.0
    
    # Campos opcionales
    validated['unidad'] = validate_string(data.get('unidad', ''), 50, 'Unidad')
    validated['ubicacion'] = validate_string(data.get('ubicacion', ''), 50, 'Ubicación')
    validated['categoria'] = validate_string(data.get('categoria', ''), 50, 'Categoría')
    validated['proveedor'] = validate_string(data.get('proveedor', ''), 100, 'Proveedor')
    
    return validated


def validate_ingreso_data(data: Dict) -> Dict:
    """Valida datos de un ingreso"""
    validated = {}
    
    # SKU (requerido)
    validated['sku'] = validate_sku(data.get('sku', ''))
    
    # Cantidad (requerido)
    validated['cantidad'] = validate_cantidad(data.get('cantidad'))
    
    # Precio (opcional)
    try:
        validated['precio'] = validate_precio(data.get('precio', 0))
    except ValidationError:
        validated['precio'] = 0.0
    
    # Campos opcionales
    validated['proveedor'] = validate_string(data.get('proveedor', ''), 100, 'Proveedor')
    validated['factura'] = validate_string(data.get('factura', ''), 50, 'Factura')
    validated['guia'] = validate_string(data.get('guia', ''), 50, 'Guía')
    validated['oc'] = validate_string(data.get('oc', ''), 50, 'OC')
    validated['observaciones'] = validate_string(data.get('observaciones', ''), 500, 'Observaciones')
    
    return validated


def validate_consumo_data(data: Dict) -> Dict:
    """Valida datos de un consumo"""
    validated = {}
    
    # SKU (requerido)
    validated['sku'] = validate_sku(data.get('sku', ''))
    
    # Cantidad (requerido)
    validated['cantidad'] = validate_cantidad(data.get('cantidad'))
    
    # Solicitante (opcional)
    validated['solicitante'] = validate_string(data.get('solicitante', ''), 100, 'Solicitante')
    
    # OT (opcional)
    validated['ot_id'] = validate_string(data.get('ot_id', ''), 50, 'OT')
    
    # Observaciones
    validated['observaciones'] = validate_string(data.get('observaciones', ''), 500, 'Observaciones')
    
    return validated


# ═══════════════════════════════════════════════════════════════
# VALIDADORES DE BÚSQUEDA Y FILTROS
# ═══════════════════════════════════════════════════════════════

def validate_search_query(query: str, max_length: int = 100) -> str:
    """Valida y sanitiza consulta de búsqueda"""
    if not isinstance(query, str):
        return ""
    
    query = query.strip()
    
    if len(query) > max_length:
        query = query[:max_length]
    
    # Remover caracteres peligrosos
    query = re.sub(r'[;\'"]', '', query)
    
    return query


def validate_pagination(page: Any, per_page: Any, max_per_page: int = 200) -> Tuple[int, int]:
    """
    Valida parámetros de paginación
    
    Returns:
        tuple: (page, per_page) validados
    """
    try:
        page = int(page)
        per_page = int(per_page)
    except (ValueError, TypeError):
        page = 1
        per_page = 50
    
    # Validar rangos
    if page < 1:
        page = 1
    
    if per_page < 1:
        per_page = 50
    
    if per_page > max_per_page:
        per_page = max_per_page
    
    return page, per_page


# ═══════════════════════════════════════════════════════════════
# VALIDADORES MÓDULO PAÑOL
# ═══════════════════════════════════════════════════════════════

def validate_empleado_data(data: Dict) -> Dict:
    """
    Valida datos de un empleado
    
    Args:
        data: Diccionario con datos del empleado
        
    Returns:
        dict: Datos validados y normalizados
        
    Raises:
        ValidationError: Si hay errores en validación
    """
    validated = {}
    
    # Número de identificación (requerido)
    numero_id = data.get('numero_identificacion', '').strip()
    if not numero_id:
        raise ValidationError("Número de identificación requerido", "numero_identificacion")
    
    if len(numero_id) > 50:
        raise ValidationError("Número de identificación máximo 50 caracteres", "numero_identificacion")
    
    validated['numero_identificacion'] = numero_id.upper()
    
    # Nombre (requerido)
    nombre = data.get('nombre', '').strip()
    if not nombre:
        raise ValidationError("Nombre requerido", "nombre")
    
    if len(nombre) < 3:
        raise ValidationError("Nombre mínimo 3 caracteres", "nombre")
    
    if len(nombre) > 200:
        raise ValidationError("Nombre máximo 200 caracteres", "nombre")
    
    validated['nombre'] = nombre
    
    # Campos opcionales
    validated['departamento'] = validate_string(data.get('departamento', ''), 100, 'Departamento')
    validated['puesto'] = validate_string(data.get('puesto', ''), 100, 'Puesto')
    validated['telefono'] = validate_string(data.get('telefono', ''), 50, 'Teléfono')
    validated['email'] = validate_string(data.get('email', ''), 200, 'Email')
    validated['observaciones'] = validate_string(data.get('observaciones', ''), 500, 'Observaciones')
    
    # Estado
    estado = data.get('estado', 'activo').strip().lower()
    if estado not in ['activo', 'inactivo']:
        estado = 'activo'
    validated['estado'] = estado
    
    return validated


def validate_herramienta_data(data: Dict) -> Dict:
    """
    Valida datos de una herramienta
    
    Args:
        data: Diccionario con datos de la herramienta
        
    Returns:
        dict: Datos validados y normalizados
        
    Raises:
        ValidationError: Si hay errores en validación
    """
    validated = {}
    
    # SKU (requerido)
    validated['sku'] = validate_sku(data.get('sku', ''))
    
    # Nombre (requerido)
    validated['nombre'] = validate_nombre(data.get('nombre', ''))
    
    # Condición
    condicion = data.get('condicion', 'operativa').strip().lower()
    if condicion not in ['operativa', 'mantenimiento', 'defectuosa', 'baja']:
        condicion = 'operativa'
    validated['condicion'] = condicion
    
    # Precio
    try:
        validated['precio_unitario'] = validate_precio(data.get('precio_unitario', 0))
    except ValidationError:
        validated['precio_unitario'] = 0.0
    
    # Cantidad
    try:
        cantidad_total = int(data.get('cantidad_total', 1))
        if cantidad_total < 1:
            cantidad_total = 1
        validated['cantidad_total'] = cantidad_total
    except (ValueError, TypeError):
        validated['cantidad_total'] = 1
    
    try:
        cantidad_disponible = int(data.get('cantidad_disponible', validated['cantidad_total']))
        if cantidad_disponible < 0:
            cantidad_disponible = 0
        if cantidad_disponible > validated['cantidad_total']:
            cantidad_disponible = validated['cantidad_total']
        validated['cantidad_disponible'] = cantidad_disponible
    except (ValueError, TypeError):
        validated['cantidad_disponible'] = validated['cantidad_total']
    
    # Calibración
    validated['requiere_calibracion'] = bool(data.get('requiere_calibracion'))
    
    if validated['requiere_calibracion']:
        try:
            frecuencia = int(data.get('frecuencia_calibracion_dias', 365))
            if frecuencia < 1:
                frecuencia = 365
            validated['frecuencia_calibracion_dias'] = frecuencia
        except (ValueError, TypeError):
            validated['frecuencia_calibracion_dias'] = 365
    else:
        validated['frecuencia_calibracion_dias'] = None
    
    # Campos opcionales
    validated['categoria'] = validate_string(data.get('categoria', ''), 100, 'Categoría')
    validated['subcategoria'] = validate_string(data.get('subcategoria', ''), 100, 'Subcategoría')
    validated['numero_serie'] = validate_string(data.get('numero_serie', ''), 100, 'Número de serie')
    validated['modelo'] = validate_string(data.get('modelo', ''), 100, 'Modelo')
    validated['fabricante'] = validate_string(data.get('fabricante', ''), 100, 'Fabricante')
    validated['ubicacion'] = validate_string(data.get('ubicacion', ''), 100, 'Ubicación')
    validated['observaciones'] = validate_string(data.get('observaciones', ''), 500, 'Observaciones')
    
    return validated


def validate_checkout_data(data: Dict) -> Dict:
    """
    Valida datos de un préstamo (checkout)
    
    Args:
        data: Diccionario con datos del préstamo
        
    Returns:
        dict: Datos validados
        
    Raises:
        ValidationError: Si hay errores en validación
    """
    validated = {}
    
    # Empleado (al menos ID o nombre)
    empleado_id = data.get('empleado_id')
    empleado_nombre = data.get('empleado_nombre', '').strip()
    
    if not empleado_id and not empleado_nombre:
        raise ValidationError("Debe especificar empleado (ID o nombre)", "empleado")
    
    if empleado_id:
        try:
            validated['empleado_id'] = int(empleado_id)
        except (ValueError, TypeError):
            raise ValidationError("ID de empleado inválido", "empleado_id")
    else:
        validated['empleado_id'] = None
    
    if empleado_nombre:
        if len(empleado_nombre) > 200:
            raise ValidationError("Nombre de empleado máximo 200 caracteres", "empleado_nombre")
        validated['empleado_nombre'] = empleado_nombre
    else:
        validated['empleado_nombre'] = None
    
    # Herramientas (requerido, array de objetos)
    herramientas = data.get('herramientas', [])
    if not isinstance(herramientas, list) or len(herramientas) == 0:
        raise ValidationError("Debe especificar al menos una herramienta", "herramientas")
    
    validated_herramientas = []
    for idx, item in enumerate(herramientas):
        if not isinstance(item, dict):
            raise ValidationError(f"Herramienta {idx + 1}: formato inválido", "herramientas")
        
        herr_id = item.get('herramienta_id')
        if not herr_id:
            raise ValidationError(f"Herramienta {idx + 1}: ID requerido", "herramientas")
        
        try:
            herr_id = int(herr_id)
        except (ValueError, TypeError):
            raise ValidationError(f"Herramienta {idx + 1}: ID inválido", "herramientas")
        
        cantidad = item.get('cantidad', 1)
        try:
            cantidad = int(cantidad)
            if cantidad < 1:
                cantidad = 1
        except (ValueError, TypeError):
            cantidad = 1
        
        observaciones = validate_string(item.get('observaciones', ''), 500, 'Observaciones')
        
        validated_herramientas.append({
            'herramienta_id': herr_id,
            'cantidad': cantidad,
            'observaciones': observaciones
        })
    
    validated['herramientas'] = validated_herramientas
    
    # Orden de trabajo (opcional)
    orden_trabajo_id = data.get('orden_trabajo_id')
    if orden_trabajo_id:
        try:
            validated['orden_trabajo_id'] = int(orden_trabajo_id)
        except (ValueError, TypeError):
            validated['orden_trabajo_id'] = None
    else:
        validated['orden_trabajo_id'] = None
    
    return validated


def validate_checkin_data(data: Dict) -> Dict:
    """
    Valida datos de una devolución (checkin)
    
    Args:
        data: Diccionario con datos de la devolución
        
    Returns:
        dict: Datos validados
        
    Raises:
        ValidationError: Si hay errores en validación
    """
    validated = {}
    
    # Devoluciones (requerido, array de objetos)
    devoluciones = data.get('devoluciones', [])
    if not isinstance(devoluciones, list) or len(devoluciones) == 0:
        raise ValidationError("Debe especificar al menos una devolución", "devoluciones")
    
    validated_devoluciones = []
    for idx, item in enumerate(devoluciones):
        if not isinstance(item, dict):
            raise ValidationError(f"Devolución {idx + 1}: formato inválido", "devoluciones")
        
        # ID de movimiento (requerido)
        mov_id = item.get('movimiento_id')
        if not mov_id:
            raise ValidationError(f"Devolución {idx + 1}: ID de movimiento requerido", "devoluciones")
        
        try:
            mov_id = int(mov_id)
        except (ValueError, TypeError):
            raise ValidationError(f"Devolución {idx + 1}: ID de movimiento inválido", "devoluciones")
        
        # Estado de retorno (requerido)
        estado_retorno = item.get('estado_retorno', '').strip().lower()
        if estado_retorno not in ['operativa', 'defectuosa', 'dañada']:
            estado_retorno = 'operativa'
        
        # Observaciones (requeridas si no es operativa)
        observaciones = validate_string(item.get('observaciones_retorno', ''), 500, 'Observaciones')
        
        if estado_retorno != 'operativa' and not observaciones:
            raise ValidationError(
                f"Devolución {idx + 1}: Observaciones requeridas para estado '{estado_retorno}'",
                "observaciones_retorno"
            )
        
        # Cantidad devuelta (opcional, si no se especifica se devuelve todo)
        cantidad_devuelta = item.get('cantidad_devuelta')
        if cantidad_devuelta is not None:
            try:
                cantidad_devuelta = int(cantidad_devuelta)
                if cantidad_devuelta < 1:
                    raise ValidationError(
                        f"Devolución {idx + 1}: Cantidad debe ser mayor a 0",
                        "cantidad_devuelta"
                    )
            except (ValueError, TypeError):
                cantidad_devuelta = None
        
        validated_devoluciones.append({
            'movimiento_id': mov_id,
            'estado_retorno': estado_retorno,
            'observaciones_retorno': observaciones,
            'cantidad_devuelta': cantidad_devuelta
        })
    
    validated['devoluciones'] = validated_devoluciones
    
    return validated


def validate_mantenimiento_data(data: Dict) -> Dict:
    """
    Valida datos de un mantenimiento
    
    Args:
        data: Diccionario con datos del mantenimiento
        
    Returns:
        dict: Datos validados
        
    Raises:
        ValidationError: Si hay errores en validación
    """
    validated = {}
    
    # Fecha de mantenimiento (requerida)
    fecha_mant = data.get('fecha_mantenimiento', '').strip()
    if not fecha_mant:
        raise ValidationError("Fecha de mantenimiento requerida", "fecha_mantenimiento")
    
    # Validar formato fecha (básico)
    if not re.match(r'^\d{4}-\d{2}-\d{2}$', fecha_mant):
        raise ValidationError("Fecha de mantenimiento formato inválido (YYYY-MM-DD)", "fecha_mantenimiento")
    
    validated['fecha_mantenimiento'] = fecha_mant
    
    # Tipo (requerido)
    tipo = data.get('tipo', '').strip().lower()
    if tipo not in ['preventivo', 'correctivo', 'calibracion']:
        raise ValidationError("Tipo de mantenimiento inválido", "tipo")
    
    validated['tipo'] = tipo
    
    # Descripción (requerida)
    descripcion = data.get('descripcion', '').strip()
    if not descripcion:
        raise ValidationError("Descripción requerida", "descripcion")
    
    if len(descripcion) > 500:
        raise ValidationError("Descripción máximo 500 caracteres", "descripcion")
    
    validated['descripcion'] = descripcion
    
    # Costo (opcional)
    try:
        costo = float(data.get('costo', 0))
        if costo < 0:
            costo = 0
        validated['costo'] = costo
    except (ValueError, TypeError):
        validated['costo'] = 0.0
    
    # Campos opcionales
    validated['responsable_nombre'] = validate_string(data.get('responsable_nombre', ''), 200, 'Responsable')
    validated['proveedor_nombre'] = validate_string(data.get('proveedor_nombre', ''), 200, 'Proveedor')
    validated['observaciones'] = validate_string(data.get('observaciones', ''), 500, 'Observaciones')
    validated['certificado_path'] = validate_string(data.get('certificado_path', ''), 500, 'Certificado')
    
    # Próxima fecha (opcional)
    proxima_fecha = data.get('proxima_fecha', '').strip()
    if proxima_fecha:
        if not re.match(r'^\d{4}-\d{2}-\d{2}$', proxima_fecha):
            proxima_fecha = None
    validated['proxima_fecha'] = proxima_fecha if proxima_fecha else None
    
    return validated


if __name__ == '__main__':

    # De prueba
    try:
        sku = validate_sku("ABC-001")
        print(f"✓ SKU válido: {sku}")
    except ValidationError as e:
        print(f"✗ Error: {e.message}")
    
    try:
        qty = validate_cantidad(10)
        print(f"✓ Cantidad válida: {qty}")
    except ValidationError as e:
        print(f"✗ Error: {e.message}")
    
    try:
        item = validate_item_data({
            'sku': 'test-001',
            'nombre': 'Producto Test',
            'stock': 100,
            'precio': 99.99
        })
        print(f"✓ Item válido: {item}")
    except ValidationError as e:
        print(f"✗ Error: {e.message}")
