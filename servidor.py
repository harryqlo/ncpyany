"""
Módulo de compatibilidad antiguo para tests y scripts.
Se mantiene como "fachada" para que las pruebas heredadas que importan
`servidor.app` y `servidor.get_db` sigan funcionando.

Originalmente el servidor se definía en este archivo, pero la lógica
se redistribuyó en `app/__init__.py` y `app/db.py`. Aquí simplemente
reexportamos los símbolos necesarios.
"""

from app import create_app
from app.db import get_db

# Crear instancia global de la aplicación (como en versiones previas)
app = create_app()

# Para que las pruebas puedan cambiar la configuración de la app antes
# de la creación de contextos, también exportamos una función auxiliar:

def create_test_app(**kwargs):
    """Crea una nueva instancia de Flask para pruebas con opciones.
    Esto imita el comportamiento que podían esperar los tests anteriores.
    """
    app = create_app()
    for k, v in kwargs.items():
        app.config[k] = v
    return app

# alias para compatibilidad, aunque get_db ya está importado arriba


# Decimos a flake8/linters que no se quejen por nombres no usados
__all__ = ["create_app", "create_test_app", "app", "get_db"]
