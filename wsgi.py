"""
Entrypoint WSGI para despliegue (PythonAnywhere u otros hosts WSGI).
"""

import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

os.environ.setdefault('FLASK_ENV', 'production')

from app import create_app

application = create_app()
