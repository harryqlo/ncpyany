# 📋 PLAN ACCIÓN - SEMANA 2
**Docstrings + Testing Framework**

---

## 🎯 OBJETIVOS SEMANA 2

```
Meta Principal: API completamente documentada + Framework de testing
Tiempo estimado: 8-10 horas
Riesgo: MÍNIMO (solo documentación y tests, sin cambios funcionales)
Salida: 15 endpoints documentados + 10+ tests funcionando
```

---

## 📝 TAREA 1: API DOCSTRINGS (3-4 HORAS)

### Qué hay que hacer:
Agregar docstrings profesionales a TODOS los 15 endpoints en `servidor.py`

### Endpoints a documentar:

1. **GET `/api/dashboard`** - Dashboard principal
2. **GET `/api/items`** - Listar productos
3. **GET `/api/items/<int:item_id>`** - Detalle producto
4. **POST `/api/items`** - Crear producto
5. **PUT `/api/items/<int:item_id>`** - Actualizar producto
6. **DELETE `/api/items/<int:item_id>`** - Eliminar producto
7. **GET `/api/items/search`** - Buscar productos
8. **GET `/api/items/<int:item_id>/ficha`** - Ficha técnica
9. **GET `/api/items/<int:item_id>/kardex`** - Historial movimientos
10. **GET `/api/ingresos`** - Listar ingresos
11. **POST `/api/ingresos`** - Crear ingreso
12. **POST `/api/batch/ingresos`** - Batch ingresos
13. **GET `/api/consumos`** - Listar consumos
14. **POST `/api/consumos`** - Crear consumo
15. **POST `/api/batch/consumos`** - Batch consumos
16. **GET `/api/ordenes`** - Listar órdenes de trabajo
17. **POST `/api/ordenes`** - Crear orden

### Formato de docstring (PARA CADA ENDPOINT):

```python
@app.route('/api/endpoint', methods=['GET', 'POST'])
def endpoint_function():
    """
    [DESCRIPCIÓN CORTA]
    
    Método HTTP: GET/POST/PUT/DELETE
    Ruta: /api/endpoint
    
    Parámetros:
    - param1 (type): Descripción
    - param2 (type): Descripción [OPCIONAL]
    
    Query strings:
    - search (str): Términos búsqueda [OPCIONAL]
    - page (int): Número página, default=1 [OPCIONAL]
    
    Body JSON (si aplica):
    {
        "field1": "tipo",
        "field2": "tipo"
    }
    
    Respuesta exitosa (200/201):
    {
        "status": "success",
        "data": {...},
        "message": "Descripción"
    }
    
    Errores posibles:
    - 400: Validación falló - {error: "mensaje"}
    - 401: No autorizado
    - 404: Recurso no encontrado
    - 500: Error servidor
    
    Ejemplos:
    curl -X GET "http://localhost:5000/api/endpoint"
    curl -X POST "http://localhost:5000/api/endpoint" \\
         -H "Content-Type: application/json" \\
         -d '{"field": "value"}'
    
    Notas:
    - Este endpoint es crítico para...
    - Cuidado con...
    """
    # Código actual sin cambios
    pass
```

### Acciones concretas:

1. Abrir `servidor.py`
2. Ir a CADA @app.route()
3. Agregar docstring usando template arriba
4. Guardar cambios
5. Probar: `python servidor.py` (debe iniciar sin errores)

### Verificación:
```bash
# Comando para verificar docstrings:
python -c "from servidor import app; print([f.__doc__ for f in app.view_functions.values()])"

# Todo docstring debe tener:
✅ Descripción clara
✅ Método HTTP
✅ Ruta exacta
✅ Parámetros esperados
✅ Formato respuesta
✅ Códigos error
✅ Ejemplo curl
```

---

## 🧪 TAREA 2: TESTING FRAMEWORK (2-3 HORAS)

### Paso 1: Instalar pytest

```bash
pip install pytest pytest-flask pytest-cov
pip freeze > requirements.txt  # Actualizar requirements.txt
```

### Paso 2: Crear estructura tests

```
north_chrome/
├── tests/                          ← NEW folder
│   ├── __init__.py                 ← NEW (vacío)
│   ├── conftest.py                 ← NEW (configuración pytest)
│   ├── test_items.py               ← NEW (tests para items)
│   ├── test_ingresos.py            ← NEW (tests para ingresos)
│   ├── test_consumos.py            ← NEW (tests para consumos)
│   └── test_validators.py          ← NEW (tests para validadores)
```

### Paso 3: Crear `tests/conftest.py`

```python
"""
Configuración para pytest - Fixtures compartidas
"""
import pytest
import os
import tempfile
from servidor import app, get_db
from config import get_config

@pytest.fixture
def client():
    """Crea cliente de prueba"""
    # Usar BD temporal para tests
    db_fd, db_path = tempfile.mkstemp()
    app.config['DATABASE'] = db_path
    app.config['TESTING'] = True
    
    with app.test_client() as client:
        # Crear tablas
        with app.app_context():
            init_db()
        yield client
    
    # Limpiar
    os.close(db_fd)
    os.unlink(db_path)

@pytest.fixture
def runner(app):
    """Para correr comandos CLI"""
    return app.test_cli_runner()

def init_db():
    """Inicializar BD temporal"""
    db = get_db()
    # Crear tablas (mismo schema que production)
    db.executescript("""
        CREATE TABLE items (
            c1 INTEGER PRIMARY KEY,
            sku TEXT UNIQUE,
            nombre TEXT,
            categoria TEXT,
            stock INTEGER,
            precio REAL
        );
        
        CREATE TABLE movimientos_ingreso (
            c1 INTEGER PRIMARY KEY,
            sku TEXT,
            cantidad INTEGER,
            proveedor TEXT,
            fecha TEXT
        );
        
        CREATE TABLE movimientos_consumo (
            c1 INTEGER PRIMARY KEY,
            sku TEXT,
            cantidad INTEGER,
            solicitante TEXT,
            fecha TEXT
        );
        
        CREATE TABLE ordenes_trabajo (
            c1 INTEGER PRIMARY KEY,
            numero TEXT,
            cliente TEXT,
            estado TEXT,
            fecha TEXT
        );
    """)
    db.commit()
```

### Paso 4: Crear `tests/test_items.py`

```python
"""
Tests para endpoints de items
"""
import json

def test_dashboard(client):
    """Test endpoint dashboard"""
    response = client.get('/api/dashboard')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert 'status' in data
    assert data['status'] == 'success'

def test_list_items_empty(client):
    """Test listar items cuando no hay"""
    response = client.get('/api/items')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert len(data['data']) == 0

def test_create_item(client):
    """Test crear nuevo item"""
    payload = {
        'sku': 'TEST-001',
        'nombre': 'Producto Test',
        'categoria': 'Test',
        'stock': 10,
        'precio': 100.50
    }
    response = client.post('/api/items', 
                          json=payload,
                          content_type='application/json')
    assert response.status_code == 201 or 200
    data = json.loads(response.data)
    assert data['status'] == 'success'

def test_create_item_invalid_sku(client):
    """Test crear item con SKU inválido"""
    payload = {
        'sku': 'invalid sku with spaces',  # ❌ Inválido
        'nombre': 'Test',
        'categoria': 'Test',
        'stock': 10,
        'precio': 100.50
    }
    response = client.post('/api/items', 
                          json=payload,
                          content_type='application/json')
    assert response.status_code == 400  # Debe rechazar

def test_search_items(client):
    """Test buscar items"""
    # Primero crear uno
    client.post('/api/items',
                json={'sku': 'SRCH-001', 'nombre': 'Searchable', 'categoria': 'Test', 'stock': 5, 'precio': 50},
                content_type='application/json')
    
    # Luego buscar
    response = client.get('/api/items/search?q=Searchable')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert len(data['data']) > 0
```

### Paso 5: Crear `tests/test_validators.py`

```python
"""
Tests para módulo validators
"""
from validators import (
    validate_sku, 
    validate_nombre, 
    validate_cantidad,
    validate_precio,
    ValidationError
)
import pytest

def test_validate_sku_valid():
    """Test SKU válido"""
    result = validate_sku('TEST-001')
    assert result == 'TEST-001'

def test_validate_sku_invalid_spaces():
    """Test SKU con espacios (inválido)"""
    with pytest.raises(ValidationError):
        validate_sku('TEST 001')

def test_validate_sku_too_long():
    """Test SKU demasiado largo"""
    with pytest.raises(ValidationError):
        validate_sku('A' * 21)  # Máximo 20 caracteres

def test_validate_nombre_valid():
    """Test nombre válido"""
    result = validate_nombre('Producto normal')
    assert result == 'Producto normal'

def test_validate_cantidad_valid():
    """Test cantidad válida"""
    result = validate_cantidad(100)
    assert result == 100

def test_validate_cantidad_negative():
    """Test cantidad negativa (inválida)"""
    with pytest.raises(ValidationError):
        validate_cantidad(-5)

def test_validate_precio_valid():
    """Test precio válido"""
    result = validate_precio(99.99)
    assert result == 99.99

def test_validate_precio_string():
    """Test precio como string (convertible)"""
    result = validate_precio('50.00')
    assert result == 50.00
```

### Paso 6: Ejecutar tests

```bash
# Ejecutar todos los tests
pytest tests/ -v

# Ejecutar con cobertura
pytest tests/ -v --cov=./ --cov-report=html

# Ejecutar un archivo específico
pytest tests/test_validators.py -v

# Ejecutar un test específico
pytest tests/test_validators.py::test_validate_sku_valid -v
```

### Verificación Final:

```bash
# Debe mostrar algo como:
tests/test_items.py::test_dashboard PASSED              [10%]
tests/test_items.py::test_list_items_empty PASSED       [20%]
tests/test_items.py::test_create_item PASSED            [30%]
tests/test_validators.py::test_validate_sku_valid PASSED [40%]
... más tests ...

====== 12 passed in 2.34s ======  ✅
```

---

## 📊 TAREA 3: COBERTURA DE CÓDIGO (1 HORA)

### Generar reporte de cobertura:

```bash
pytest tests/ --cov=./ --cov-report=html --cov-report=term
```

### Ver reporte:
```bash
# En Windows:
start htmlcov/index.html

# En Mac:
open htmlcov/index.html

# En Linux:
firefox htmlcov/index.html
```

### Meta:
- **Mínimo 50% code coverage** (aceptable)
- **Ideal 70%+** (muy bueno)
- No necesita 100% (tests pueden alcanzar ~70%)

---

## 🔄 ORDEN DE EJECUCIÓN

### Día 1 (Lunes):
```
1. Agregar docstrings a 5 endpoints (1 hora)
2. Verificar servidor sigue funcionando (15 min)
3. Instalar pytest (5 min)
```

### Día 2 (Martes):
```
1. Agregar docstrings a 10 endpoints más (2 horas)
2. Crear estructura tests/ (15 min)
3. Crear conftest.py (30 min)
```

### Día 3 (Miércoles):
```
1. Escribir test_items.py (1 hora)
2. Escribir test_validators.py (1 hora)
3. Ejecutar y debuggear tests (1 hora)
4. Generar reporte cobertura (15 min)
```

---

## ✅ CHECKLIST SEMANA 2

### Docstrings:
- [ ] 15 endpoints con docstrings
- [ ] Cada uno con: descripción, método, rutas, parámetros, respuesta, errores
- [ ] Ejemplos curl para cada uno
- [ ] Servidor corre sin errores

### Testing:
- [ ] pytest instalado
- [ ] Estructura tests/ creada
- [ ] conftest.py funcional
- [ ] test_items.py con 5+ tests
- [ ] test_validators.py con 8+ tests
- [ ] Todos los tests PASEN ✅

### Cobertura:
- [ ] Reporte de cobertura generado
- [ ] Mínimo 50% coverage alcanzado
- [ ] Mostrar reporte HTML

---

## 💡 TIPS & TRICKS

### Para docstrings rápido:
```python
# Template copiar/pegar:
"""
Description here
"""
```

Luego completar con información específica de cada endpoint.

### Para tests rápido:
1. Copiar test desde test_validators.py
2. Cambiar datos (sku, nombre, etc.)
3. Ejecutar: `pytest -v` para ver si pasa

### Debugging tests:
```bash
# Si falla, ver más detalles:
pytest tests/test_file.py::test_name -v -s

# Parar en error:
pytest --pdb tests/

# Ver qué sucede:
pytest --tb=short
```

---

## 🎯 RESULTADO ESPERADO FINAL

```
north_chrome/
├── servidor.py             ← 15 endpoints con docstrings
├── validators.py           ← Sin cambios
├── tests/                  ← NEW
│   ├── conftest.py
│   ├── test_items.py       ← 5+ tests
│   ├── test_validators.py  ← 8+ tests
│   └── __init__.py
│
├── .coverage               ← Reporte cobertura
├── htmlcov/                ← Reporte HTML
│   └── index.html          ← Abrir en navegador
│
└── requirements.txt        ← pytest agregado

pytest output:
✅ 13 tests passed
✅ 50%+ code coverage
✅ Todos los tests VERDES
```

---

## 📞 SOPORTE SEMANA 2

Si algo falla:

| Problema | Solución |
|----------|----------|
| `ModuleNotFoundError: No module named 'pytest'` | `pip install pytest pytest-flask pytest-cov` |
| Tests no encuentran `servidor.py` | Asegurar conftest.py en directorio `tests/` |
| `ConnectionError` en tests | Usar `tempfile` para BD temporal (ver conftest.py) |
| Docstring no aparece | Verificar indentación (debe estar dentro función) |

---

## 🚀 LISTO PARA EMPEZAR?

```
Si completaste TODO en este documento:
✅ TAREAS SEMANA 2 FINALIZADAS
   ↓
✅ LISTO PARA PHASE 1 (Autenticación JWT)
   ↓
🎉 ¡A por la siguiente semana!
```

---

**Tiempo total Semana 2: 8-10 horas**
**Esfuerzo: MODERADO (documentación + escritura de tests)**
**Riesgo: MÍNIMO (solo agrega, no modifica lógica)**
**Impacto: ALTO (completa calidad + documentación)**

¡Vamos! 🚀
