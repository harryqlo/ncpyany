#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test para verificar que el módulo de configuraciones funciona correctamente
North Chrome v2
"""

import sys
import json
from pathlib import Path

# Agregar ruta actual al path
sys.path.insert(0, str(Path(__file__).parent))

try:
    from user_settings import UserSettingsManager, UI_DEFAULTS
    print("✅ Módulo user_settings.py importado correctamente")
except ImportError as e:
    print(f"❌ Error importando user_settings: {e}")
    sys.exit(1)


def test_initialization():
    """Test 1: Inicialización de BD"""
    print("\n" + "="*50)
    print("TEST 1: Inicialización de Base de Datos")
    print("="*50)
    
    result = UserSettingsManager.init_db()
    if result:
        print("✅ Base de datos inicializada correctamente")
    else:
        print("❌ Error inicializando base de datos")
    
    return result


def test_get_default_settings():
    """Test 2: Obtener configuraciones por defecto"""
    print("\n" + "="*50)
    print("TEST 2: Obtener Configuraciones por Defecto")
    print("="*50)
    
    settings = UserSettingsManager.get_settings()
    print(f"Configuraciones obtenidas: {json.dumps(settings, indent=2)}")
    
    # Verificar que tienen todos los campos
    required_fields = ['fontSize', 'fontFamily', 'density', 'colorScheme', 'accentColor', 'theme']
    missing = [f for f in required_fields if f not in settings]
    
    if not missing:
        print("✅ Todas las configuraciones necesarias están presentes")
        return True
    else:
        print(f"❌ Faltan campos: {missing}")
        return False


def test_save_settings():
    """Test 3: Guardar configuraciones"""
    print("\n" + "="*50)
    print("TEST 3: Guardar Configuraciones")
    print("="*50)
    
    new_settings = {
        'fontSize': 'large',
        'colorScheme': 'light',
        'accentColor': 'blue',
        'density': 'spacious'
    }
    
    result = UserSettingsManager.save_settings('test_user', new_settings)
    print(f"Resultado: {json.dumps(result, indent=2)}")
    
    if result['ok']:
        print("✅ Configuraciones guardadas correctamente")
        return True
    else:
        print(f"❌ Error guardando: {result['msg']}")
        return False


def test_retrieve_saved():
    """Test 4: Recuperar configuraciones guardadas"""
    print("\n" + "="*50)
    print("TEST 4: Recuperar Configuraciones Guardadas")
    print("="*50)
    
    settings = UserSettingsManager.get_settings('test_user')
    print(f"Configuraciones recuperadas: {json.dumps(settings, indent=2)}")
    
    # Verificar que se guardaron los cambios
    if settings.get('fontSize') == 'large' and settings.get('colorScheme') == 'light':
        print("✅ Configuraciones recuperadas correctamente")
        return True
    else:
        print("❌ Las configuraciones no se recuperaron correctamente")
        return False


def test_validation():
    """Test 5: Validación de configuraciones inválidas"""
    print("\n" + "="*50)
    print("TEST 5: Validación de Configuraciones")
    print("="*50)
    
    invalid_settings = {
        'fontSize': 'huge',  # Inválido
        'colorScheme': 'neon',  # Inválido
        'accentColor': 'rainbow',  # Inválido
        'density': 'ultra'  # Inválido
    }
    
    result = UserSettingsManager.save_settings('validation_test', invalid_settings)
    saved = result.get('settings', {})
    
    print(f"Valores después de validación:")
    print(f"  fontSize: {saved.get('fontSize')} (esperado: 'normal')")
    print(f"  colorScheme: {saved.get('colorScheme')} (esperado: 'auto')")
    print(f"  accentColor: {saved.get('accentColor')} (esperado: 'orange')")
    print(f"  density: {saved.get('density')} (esperado: 'normal')")
    
    if (saved.get('fontSize') == 'normal' and 
        saved.get('colorScheme') == 'auto' and
        saved.get('accentColor') == 'orange' and
        saved.get('density') == 'normal'):
        print("✅ Validación funcionando correctamente")
        return True
    else:
        print("❌ Validación fallida")
        return False


def test_stats():
    """Test 6: Estadísticas"""
    print("\n" + "="*50)
    print("TEST 6: Estadísticas de Usuarios")
    print("="*50)
    
    stats = UserSettingsManager.get_all_users_stats()
    print(f"Estadísticas: {json.dumps(stats, indent=2)}")
    
    if stats and 'total_users' in stats:
        print(f"✅ Total de usuarios: {stats['total_users']}")
        return True
    else:
        print("❌ No se pudo obtener estadísticas")
        return False


def main():
    """Ejecuta todos los tests"""
    print("\n" + "="*50)
    print("🧪 TESTS DEL MÓDULO user_settings.py")
    print("="*50)
    
    tests = [
        ("Inicialización BD", test_initialization),
        ("Configuraciones por defecto", test_get_default_settings),
        ("Guardar configuraciones", test_save_settings),
        ("Recuperar guardadas", test_retrieve_saved),
        ("Validación", test_validation),
        ("Estadísticas", test_stats),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n❌ Error en {name}: {e}")
            import traceback
            traceback.print_exc()
            results.append((name, False))
    
    # Resumen
    print("\n" + "="*50)
    print("📊 RESUMEN DE TESTS")
    print("="*50)
    
    passed = sum(1 for _, r in results if r)
    total = len(results)
    
    for name, result in results:
        status = "✅ PASÓ" if result else "❌ FALLÓ"
        print(f"{status}: {name}")
    
    print(f"\nTotal: {passed}/{total} tests pasados")
    
    if passed == total:
        print("\n🎉 ¡TODOS LOS TESTS PASARON! 🎉")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) fallaron")
        return 1


if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code)
