
import os
import shutil
from datetime import datetime
from app import create_app
from app.db import get_db

# Importar configuración
try:
    from config import DB_PATH, BASE_DIR, SYSTEM_DIR, BACKUP_DIR
except ImportError:
    # Fallback si no están disponibles
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    SYSTEM_DIR = os.path.join(BASE_DIR, 'system')
    DB_PATH = os.path.join(SYSTEM_DIR, 'system.db')
    BACKUP_DIR = os.path.join(SYSTEM_DIR, 'backups')

def auto_backup():
    """
    Realiza una copia de seguridad automática de la base de datos.
    """
    os.makedirs(BACKUP_DIR, exist_ok=True)
    bp = os.path.join(BACKUP_DIR, f'system_{datetime.now().strftime("%Y-%m-%d")}.db')
    if not os.path.exists(bp):
        shutil.copy2(DB_PATH, bp)
        print(f"[Backup] Respaldo: {bp}")
        # Limpia respaldos antiguos, manteniendo los 10 más recientes
        bks = sorted([f for f in os.listdir(BACKUP_DIR) if f.endswith('.db')])
        while len(bks) > 10:
            os.remove(os.path.join(BACKUP_DIR, bks.pop(0)))
    else:
        print(f"[Backup] Respaldo de hoy ya existe.")

def check_database():
    """
    Verifica la existencia y el estado de la base de datos.
    """
    os.makedirs(SYSTEM_DIR, exist_ok=True)
    if not os.path.exists(DB_PATH):
        print(f"[WARN] Buscando system.db en ubicaciones comunes...")
        found = None
        search_paths = [
            BASE_DIR,
            os.path.dirname(BASE_DIR),
            os.path.expanduser(r'~\Downloads'),
            os.path.expanduser(r'~\Desktop'),
            os.path.expanduser(r'~\Documents')
        ]
        for d in search_paths:
            if found: break
            # Busca en la carpeta y subcarpetas de primer nivel
            try:
                for entry in os.scandir(d):
                    c2 = os.path.join(d, entry.name)
                    if entry.is_file() and entry.name == 'system.db':
                        found = c2
                        break
                    elif entry.is_dir():
                        c3 = os.path.join(c2, 'system.db')
                        if os.path.exists(c3):
                            found = c3
                            break
            except (FileNotFoundError, PermissionError):
                continue
        
        if found:
            shutil.copy2(found, DB_PATH)
            print(f"   [OK] Base de datos encontrada y copiada desde: {found}")
        else:
            print(f"   [ERROR] No se encontro 'system.db'. Copialo manualmente en: {SYSTEM_DIR}")
            input("\n   Presiona Enter para salir...")
            exit(1)

    try:
        cn = get_db()
        ni = cn.execute('SELECT COUNT(*) FROM items').fetchone()[0]
        cn.close()
        print(f"[OK] Conexion a BD exitosa. {ni} productos encontrados.")
    except Exception as e:
        print(f"   [ERROR] Error al conectar con la base de datos: {e}")
        input("\n   Presiona Enter para salir...")
        exit(1)


def get_server_config():
    """
    Configuración de servidor con valores estables por defecto.
    Permite override por variables de entorno.
    """
    host = os.getenv('NC_HOST', '127.0.0.1').strip() or '127.0.0.1'

    try:
        port = int(os.getenv('NC_PORT', '5000'))
    except ValueError:
        port = 5000

    debug_raw = os.getenv('NC_DEBUG', '0').strip().lower()
    debug = debug_raw in ('1', 'true', 'yes', 'on')

    return host, port, debug

if __name__ == '__main__':
    check_database()
    auto_backup()
    
    app = create_app()
    host, port, debug = get_server_config()
    
    print(f"""
{'='*50}
  North Chrome v2 - Modular
  BD: {DB_PATH}
  Backups: {BACKUP_DIR}
  URL: http://{host}:{port}
{'='*50}
""")

    try:
        app.run(host=host, port=port, debug=debug, use_reloader=False)
    except OSError as e:
        print(f"[ERROR] No se pudo iniciar el servidor en {host}:{port} -> {e}")
        print("[SUGERENCIA] Cambia el puerto con NC_PORT, por ejemplo: set NC_PORT=5001")
        input("\nPresiona Enter para salir...")
