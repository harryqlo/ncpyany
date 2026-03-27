#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de Verificación de Instalación
North Chrome v2 - Sistema de Configuraciones Avanzadas

Ejecutar: python verificar_instalacion.py
"""

import os
import sys
from pathlib import Path

# Colores para terminal
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

def print_header():
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.RESET}")
    print(f"{Colors.BOLD}🔍 VERIFICACIÓN DE INSTALACIÓN{Colors.RESET}")
    print(f"{Colors.BOLD}North Chrome v2 - Configuraciones Avanzadas{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.RESET}\n")

def check_file(path, description):
    """Verifica si un archivo existe"""
    if os.path.exists(path):
        size = os.path.getsize(path)
        status = f"{Colors.GREEN}✅ EXISTE{Colors.RESET}"
        print(f"{status} | {description}")
        print(f"     └─ Tamaño: {size:,} bytes")
        return True
    else:
        status = f"{Colors.RED}❌ NO EXISTE{Colors.RESET}"
        print(f"{status} | {description}")
        return False

def check_directory(path, description):
    """Verifica si un directorio existe"""
    if os.path.isdir(path):
        status = f"{Colors.GREEN}✅ EXISTE{Colors.RESET}"
        print(f"{status} | {description}")
        return True
    else:
        status = f"{Colors.RED}❌ NO EXISTE{Colors.RESET}"
        print(f"{status} | {description}")
        return False

def verify_imports():
    """Verifica que los módulos Python se cargan correctamente"""
    print(f"\n{Colors.BOLD}2️⃣  VERIFICACIÓN DE MÓDULOS PYTHON{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'-'*60}{Colors.RESET}\n")
    
    modules = [
        ('flask', 'Flask'),
        ('flask_cors', 'Flask-CORS'),
        ('sqlite3', 'SQLite3'),
    ]
    
    all_ok = True
    for module, name in modules:
        try:
            __import__(module)
            print(f"{Colors.GREEN}✅{Colors.RESET} {name} importado correctamente")
        except ImportError:
            print(f"{Colors.RED}❌{Colors.RESET} {name} NO está instalado")
            all_ok = False
    
    return all_ok

def main():
    print_header()
    
    base_path = Path(__file__).parent.absolute()
    os.chdir(base_path)
    
    # 1. Verificar archivos principales
    print(f"{Colors.BOLD}1️⃣  VERIFICACIÓN DE ARCHIVOS{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'-'*60}{Colors.RESET}\n")
    
    files_to_check = [
        ("settings.js", "Frontend - Gestor de configuraciones"),
        ("settings-styles.css", "Frontend - Estilos del panel"),
        ("user_settings.py", "Backend - Gestor servidor"),
        ("test_settings.py", "Testing - Suite de pruebas"),
        ("config.py", "Configuración (debe estar actualizado)"),
        ("servidor.py", "Servidor Flask (debe estar actualizado)"),
        ("index.html", "Frontend principal (debe estar actualizado)"),
    ]
    
    files_ok = 0
    for filename, description in files_to_check:
        if check_file(os.path.join(base_path, filename), description):
            files_ok += 1
    
    # 2. Verificar módulos Python
    modules_ok = verify_imports()
    
    # 3. Verificar directorios
    print(f"\n{Colors.BOLD}3️⃣  VERIFICACIÓN DE DIRECTORIOS{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'-'*60}{Colors.RESET}\n")
    
    dirs_to_check = [
        ("system", "Base de datos SQLite"),
        ("logs", "Archivos de log"),
        ("system/backups", "Respaldos automáticos"),
    ]
    
    dirs_ok = 0
    for dirname, description in dirs_to_check:
        if check_directory(os.path.join(base_path, dirname), description):
            dirs_ok += 1
    
    # 4. Verificar base de datos
    print(f"\n{Colors.BOLD}4️⃣  VERIFICACIÓN DE BASE DE DATOS{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'-'*60}{Colors.RESET}\n")
    
    db_path = os.path.join(base_path, "system", "system.db")
    db_ok = False
    
    if os.path.exists(db_path):
        print(f"{Colors.GREEN}✅ Base de datos existente{Colors.RESET}")
        print(f"     └─ Ruta: {db_path}")
        
        # Verificar tabla de configuraciones
        try:
            import sqlite3
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='user_settings'")
            if cursor.fetchone():
                print(f"{Colors.GREEN}✅ Tabla 'user_settings' existe{Colors.RESET}")
                db_ok = True
            else:
                print(f"{Colors.YELLOW}⚠️  Tabla 'user_settings' no existe (se creará automáticamente){Colors.RESET}")
                db_ok = True  # Se creará al ejecutar
            conn.close()
        except Exception as e:
            print(f"{Colors.RED}❌ Error verificando BD: {e}{Colors.RESET}")
    else:
        print(f"{Colors.YELLOW}⚠️  Base de datos no existe (se creará automáticamente){Colors.RESET}")
        db_ok = True
    
    # 5. Verificar configuración en config.py
    print(f"\n{Colors.BOLD}5️⃣  VERIFICACIÓN DE CONFIGURACIÓN{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'-'*60}{Colors.RESET}\n")
    
    config_ok = False
    try:
        from config import UI_DEFAULTS, FONT_SIZES
        print(f"{Colors.GREEN}✅ UI_DEFAULTS encontrado{Colors.RESET}")
        print(f"     └─ Contiene {len(UI_DEFAULTS)} opciones")
        print(f"{Colors.GREEN}✅ FONT_SIZES encontrado{Colors.RESET}")
        print(f"     └─ Contiene {len(FONT_SIZES)} escalas")
        config_ok = True
    except ImportError as e:
        print(f"{Colors.RED}❌ Error importando configuración: {e}{Colors.RESET}")
    
    # 6. Resumen
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.RESET}")
    print(f"{Colors.BOLD}📊 RESUMEN{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.RESET}\n")
    
    total_files = len(files_to_check)
    total_dirs = len(dirs_to_check)
    
    print(f"Archivos:      {files_ok}/{total_files} ✓")
    print(f"Módulos:       {'OK' if modules_ok else 'CON ERRORES'} ✓" if modules_ok else "Módulos:       ❌ CON ERRORES")
    print(f"Directorios:   {dirs_ok}/{total_dirs} ✓")
    print(f"Base de datos: {'OK' if db_ok else '❌ ERROR'} ✓" if db_ok else ("Base de datos: ❌ ERROR"))
    print(f"Configuración: {'OK' if config_ok else '❌ ERROR'} ✓" if config_ok else ("Configuración: ❌ ERROR"))
    
    # Determine overall status
    all_ok = (files_ok == total_files) and modules_ok and (dirs_ok == total_dirs) and db_ok and config_ok
    
    if all_ok:
        print(f"\n{Colors.GREEN}{Colors.BOLD}✅ TODO ESTÁ CORRECTO - SISTEMA LISTO PARA USAR{Colors.RESET}")
        print(f"\n{Colors.BOLD}Próximos pasos:{Colors.RESET}")
        print(f"1. Ejecuta: {Colors.BOLD}python servidor.py{Colors.RESET}")
        print(f"2. Abre: {Colors.BOLD}http://localhost:5000{Colors.RESET}")
        print(f"3. Busca el botón: {Colors.BOLD}⚙️{Colors.RESET} (esquina superior derecha)")
        print(f"4. ¡Personaliza tu interfaz!\n")
        return 0
    else:
        print(f"\n{Colors.RED}{Colors.BOLD}❌ HAY PROBLEMAS - VER ARRIBA{Colors.RESET}\n")
        
        print(f"{Colors.YELLOW}Tips de Solución:{Colors.RESET}")
        if files_ok < total_files:
            print(f"• Archivos faltantes: Descarga e instala settings.js y settings-styles.css")
        if not modules_ok:
            print(f"• Módulos faltantes: pip install flask flask-cors")
        if dirs_ok < total_dirs:
            print(f"• Directorios: Se crearán automáticamente al ejecutar servidor.py")
        if not db_ok:
            print(f"• BD: Se creará automáticamente al ejecutar servidor.py")
        print()
        
        return 1

if __name__ == '__main__':
    try:
        exit_code = main()
        sys.exit(exit_code)
    except Exception as e:
        print(f"\n{Colors.RED}❌ Error inesperado: {e}{Colors.RESET}\n")
        sys.exit(1)
