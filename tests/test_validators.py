"""
Tests para el módulo de validadores
"""
import pytest
import sys
from pathlib import Path

# Agregar el directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent.parent))

from validators import (
    validate_sku,
    validate_nombre,
    validate_cantidad,
    validate_precio,
    validate_string,
    validate_search_query,
    ValidationError
)

# ═══════════════════════════════════════════════════════════════
# Tests para validate_sku
# ═══════════════════════════════════════════════════════════════

def test_validate_sku_valid():
    """Test SKU válido"""
    result = validate_sku('PROD-001')
    assert result == 'PROD-001'
    print("✅ test_validate_sku_valid PASSED")

def test_validate_sku_with_numbers():
    """Test SKU con números"""
    result = validate_sku('SK123')
    assert result == 'SK123'
    print("✅ test_validate_sku_with_numbers PASSED")

def test_validate_sku_with_hyphen():
    """Test SKU con guiones"""
    result = validate_sku('PROD-ABC-123')
    assert result == 'PROD-ABC-123'
    print("✅ test_validate_sku_with_hyphen PASSED")

def test_validate_sku_invalid_spaces():
    """Test SKU con espacios (inválido)"""
    with pytest.raises(ValidationError):
        validate_sku('PROD 001')
    print("✅ test_validate_sku_invalid_spaces PASSED")

def test_validate_sku_too_short():
    """Test SKU vacío"""
    with pytest.raises(ValidationError):
        validate_sku('')
    print("✅ test_validate_sku_too_short PASSED")

def test_validate_sku_too_long():
    """Test SKU demasiado largo"""
    with pytest.raises(ValidationError):
        validate_sku('A' * 21)  # Máximo es 20
    print("✅ test_validate_sku_too_long PASSED")

def test_validate_sku_special_chars():
    """Test SKU con caracteres especiales (inválido)"""
    with pytest.raises(ValidationError):
        validate_sku('PROD@001')
    print("✅ test_validate_sku_special_chars PASSED")

# ═══════════════════════════════════════════════════════════════
# Tests para validate_nombre
# ═══════════════════════════════════════════════════════════════

def test_validate_nombre_valid():
    """Test nombre válido"""
    result = validate_nombre('Producto Normal')
    assert result == 'Producto Normal'
    print("✅ test_validate_nombre_valid PASSED")

def test_validate_nombre_empty():
    """Test nombre vacío"""
    with pytest.raises(ValidationError):
        validate_nombre('')
    print("✅ test_validate_nombre_empty PASSED")

def test_validate_nombre_too_long():
    """Test nombre demasiado largo"""
    with pytest.raises(ValidationError):
        validate_nombre('A' * 201)  # Máximo 200
    print("✅ test_validate_nombre_too_long PASSED")

# ═══════════════════════════════════════════════════════════════
# Tests para validate_cantidad
# ═══════════════════════════════════════════════════════════════

def test_validate_cantidad_valid():
    """Test cantidad válida"""
    result = validate_cantidad(100)
    assert result == 100
    print("✅ test_validate_cantidad_valid PASSED")

def test_validate_cantidad_zero():
    """Test cantidad cero"""
    result = validate_cantidad(0)
    assert result == 0
    print("✅ test_validate_cantidad_zero PASSED")

def test_validate_cantidad_negative():
    """Test cantidad negativa (inválida)"""
    with pytest.raises(ValidationError):
        validate_cantidad(-5)
    print("✅ test_validate_cantidad_negative PASSED")

def test_validate_cantidad_too_high():
    """Test cantidad muy alta"""
    # Máximo es 999999
    with pytest.raises(ValidationError):
        validate_cantidad(1000000)
    print("✅ test_validate_cantidad_too_high PASSED")

def test_validate_cantidad_string():
    """Test cantidad como string convertible"""
    result = validate_cantidad('50')
    assert result == 50
    print("✅ test_validate_cantidad_string PASSED")

# ═══════════════════════════════════════════════════════════════
# Tests para validate_precio
# ═══════════════════════════════════════════════════════════════

def test_validate_precio_valid():
    """Test precio válido"""
    result = validate_precio(99.99)
    assert result == 99.99
    print("✅ test_validate_precio_valid PASSED")

def test_validate_precio_integer():
    """Test precio entero"""
    result = validate_precio(100)
    assert result == 100.0
    print("✅ test_validate_precio_integer PASSED")

def test_validate_precio_string():
    """Test precio como string convertible"""
    result = validate_precio('50.00')
    assert result == 50.0
    print("✅ test_validate_precio_string PASSED")

def test_validate_precio_negative():
    """Test precio negativo (inválido)"""
    with pytest.raises(ValidationError):
        validate_precio(-10)
    print("✅ test_validate_precio_negative PASSED")

def test_validate_precio_too_high():
    """Test precio muy alto"""
    # Máximo es 999999.99
    with pytest.raises(ValidationError):
        validate_precio(1000000)
    print("✅ test_validate_precio_too_high PASSED")

def test_validate_precio_invalid_string():
    """Test precio string inválido"""
    with pytest.raises(ValidationError):
        validate_precio('abc')
    print("✅ test_validate_precio_invalid_string PASSED")

# ═══════════════════════════════════════════════════════════════
# Tests para validate_string
# ═══════════════════════════════════════════════════════════════

def test_validate_string_valid():
    """Test string válido"""
    result = validate_string('Texto normal', 100)
    assert result == 'Texto normal'
    print("✅ test_validate_string_valid PASSED")

def test_validate_string_too_long():
    """Test string demasiado largo"""
    with pytest.raises(ValidationError):
        validate_string('A' * 101, 100)
    print("✅ test_validate_string_too_long PASSED")

def test_validate_string_empty():
    """Test string vacío"""
    result = validate_string('', 100)
    assert result == ''
    print("✅ test_validate_string_empty PASSED")

# ═══════════════════════════════════════════════════════════════
# Tests para validate_search_query
# ═══════════════════════════════════════════════════════════════

def test_validate_search_query_valid():
    """Test búsqueda válida"""
    result = validate_search_query('PROD-001')
    assert len(result) > 0
    print("✅ test_validate_search_query_valid PASSED")

def test_validate_search_query_with_spaces():
    """Test búsqueda con espacios"""
    result = validate_search_query('Producto Test')
    assert len(result) > 0
    print("✅ test_validate_search_query_with_spaces PASSED")

def test_validate_search_query_injection_attempt():
    """Test búsqueda intenta inyección SQL"""
    result = validate_search_query("'; DROP TABLE items; --")
    # Debe retornar algo (puede contener DROP pero es sanitizado en BD via parametrization)
    assert isinstance(result, str)
    print("✅ test_validate_search_query_injection_attempt PASSED")

def test_validate_search_query_empty():
    """Test búsqueda vacía"""
    # validate_search_query retorna string, no lanza excepción
    result = validate_search_query('')
    assert isinstance(result, str)
    print("✅ test_validate_search_query_empty PASSED")

# ═══════════════════════════════════════════════════════════════
# Tests generales
# ═══════════════════════════════════════════════════════════════

def test_validation_error_exists():
    """Verificar que ValidationError existe"""
    try:
        raise ValidationError("Test error", "field_name")
    except ValidationError as e:
        assert e.message == "Test error"
        assert e.field == "field_name"
    print("✅ test_validation_error_exists PASSED")
