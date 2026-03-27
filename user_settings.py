"""
Gestor de Configuraciones del Usuario
North Chrome v2 - Funciones de Preferencias y Ajustes
"""

import sqlite3
import json
from datetime import datetime
from pathlib import Path

try:
    from config import DB_PATH, UI_DEFAULTS
except ImportError:
    DB_PATH = 'system/system.db'
    UI_DEFAULTS = {
        'fontSize': 'normal',
        'fontFamily': 'system',
        'density': 'normal',
        'colorScheme': 'auto',
        'accentColor': 'orange',
        'theme': 'professional',
    }


class UserSettingsManager:
    """Gestor centralizado de configuraciones de usuario"""

    @staticmethod
    def init_db():
        """Inicializa tabla de configuraciones si no existe"""
        try:
            conn = sqlite3.connect(str(DB_PATH))
            conn.execute('PRAGMA journal_mode=WAL')
            
            conn.execute('''
                CREATE TABLE IF NOT EXISTS user_settings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT DEFAULT 'default' UNIQUE,
                    settings TEXT NOT NULL DEFAULT '{}',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error initializing settings DB: {e}")
            return False

    @staticmethod
    def get_settings(user_id='default'):
        """
        Obtiene configuraciones guardadas del usuario
        
        Args:
            user_id: ID del usuario (por defecto 'default' para único usuario)
            
        Returns:
            dict: Configuraciones del usuario
        """
        try:
            conn = sqlite3.connect(str(DB_PATH))
            cursor = conn.cursor()
            
            cursor.execute(
                'SELECT settings FROM user_settings WHERE user_id = ?',
                (user_id,)
            )
            row = cursor.fetchone()
            conn.close()
            
            if row:
                settings = json.loads(row[0])
                # Fusionar con valores por defecto (por si hay nuevas opciones)
                return {**UI_DEFAULTS, **settings}
            else:
                # Crear entrada por defecto
                UserSettingsManager.save_settings(user_id, UI_DEFAULTS)
                return UI_DEFAULTS
                
        except Exception as e:
            print(f"Error getting settings: {e}")
            return UI_DEFAULTS

    @staticmethod
    def save_settings(user_id='default', settings=None):
        """
        Guarda configuraciones del usuario
        
        Args:
            user_id: ID del usuario
            settings: Dict con configuraciones
            
        Returns:
            dict: {'ok': bool, 'msg': str}
        """
        if settings is None:
            settings = {}

        try:
            # Validar configuraciones
            validated = UserSettingsManager._validate_settings(settings)
            
            conn = sqlite3.connect(str(DB_PATH))
            conn.execute('PRAGMA journal_mode=WAL')
            
            # Verificar si existe el usuario
            cursor = conn.cursor()
            cursor.execute('SELECT id FROM user_settings WHERE user_id = ?', (user_id,))
            exists = cursor.fetchone()
            
            if exists:
                # Actualizar
                conn.execute(
                    '''UPDATE user_settings 
                       SET settings = ?, updated_at = CURRENT_TIMESTAMP 
                       WHERE user_id = ?''',
                    (json.dumps(validated), user_id)
                )
            else:
                # Insertar
                conn.execute(
                    '''INSERT INTO user_settings (user_id, settings) 
                       VALUES (?, ?)''',
                    (user_id, json.dumps(validated))
                )
            
            conn.commit()
            conn.close()
            
            return {
                'ok': True,
                'msg': 'Configuración guardada correctamente',
                'settings': validated
            }
        except Exception as e:
            print(f"Error saving settings: {e}")
            return {
                'ok': False,
                'msg': f'Error al guardar configuración: {str(e)}'
            }

    @staticmethod
    def _validate_settings(settings):
        """
        Valida y sanitiza configuraciones
        
        Args:
            settings: Dict con configuraciones
            
        Returns:
            dict: Configuraciones validadas
        """
        validated = {}
        
        # Validaciones por campo
        valid_sizes = ['small', 'normal', 'large', 'xlarge']
        valid_families = ['system', 'serif', 'mono']
        valid_densities = ['compact', 'normal', 'spacious']
        valid_schemes = ['auto', 'dark', 'light']
        valid_accents = ['orange', 'blue', 'purple', 'green', 'red', 'pink']
        valid_themes = ['professional', 'minimal', 'compact']
        valid_line_heights = ['1.3', '1.5', '1.7']
        
        validated['fontSize'] = settings.get('fontSize', 'normal')
        if validated['fontSize'] not in valid_sizes:
            validated['fontSize'] = 'normal'
            
        validated['fontFamily'] = settings.get('fontFamily', 'system')
        if validated['fontFamily'] not in valid_families:
            validated['fontFamily'] = 'system'
            
        validated['density'] = settings.get('density', 'normal')
        if validated['density'] not in valid_densities:
            validated['density'] = 'normal'
            
        validated['colorScheme'] = settings.get('colorScheme', 'auto')
        if validated['colorScheme'] not in valid_schemes:
            validated['colorScheme'] = 'auto'
            
        validated['accentColor'] = settings.get('accentColor', 'orange')
        if validated['accentColor'] not in valid_accents:
            validated['accentColor'] = 'orange'
            
        validated['theme'] = settings.get('theme', 'professional')
        if validated['theme'] not in valid_themes:
            validated['theme'] = 'professional'

        validated['lineHeight'] = str(settings.get('lineHeight', '1.5'))
        if validated['lineHeight'] not in valid_line_heights:
            validated['lineHeight'] = '1.5'
        
        # Booleanos
        validated['animationsEnabled'] = bool(settings.get('animationsEnabled', True))
        validated['notifications'] = bool(settings.get('notifications', True))
        validated['autoRefresh'] = bool(settings.get('autoRefresh', True))
        validated['compactMode'] = bool(settings.get('compactMode', False))
        
        # Números
        refresh_interval = int(settings.get('autoRefreshInterval', 60000))
        validated['autoRefreshInterval'] = max(5000, min(300000, refresh_interval))
        
        return validated

    @staticmethod
    def reset_settings(user_id='default'):
        """
        Reinicia configuraciones a valores por defecto
        
        Args:
            user_id: ID del usuario
            
        Returns:
            dict: {'ok': bool, 'msg': str}
        """
        return UserSettingsManager.save_settings(user_id, UI_DEFAULTS.copy())

    @staticmethod
    def get_all_users_stats():
        """
        Obtiene estadísticas de configuraciones de todos los usuarios
        
        Returns:
            dict: Estadísticas
        """
        try:
            conn = sqlite3.connect(str(DB_PATH))
            cursor = conn.cursor()
            
            cursor.execute('SELECT COUNT(*) FROM user_settings')
            total_users = cursor.fetchone()[0]
            
            cursor.execute(
                '''SELECT settings FROM user_settings 
                   WHERE settings NOT NULL'''
            )
            
            theme_stats = {}
            size_stats = {}
            
            for row in cursor.fetchall():
                try:
                    settings = json.loads(row[0])
                    theme = settings.get('theme', 'professional')
                    size = settings.get('fontSize', 'normal')
                    
                    theme_stats[theme] = theme_stats.get(theme, 0) + 1
                    size_stats[size] = size_stats.get(size, 0) + 1
                except:
                    pass
            
            conn.close()
            
            return {
                'total_users': total_users,
                'theme_distribution': theme_stats,
                'fontSize_distribution': size_stats,
                'last_updated': datetime.now().isoformat()
            }
        except Exception as e:
            print(f"Error getting stats: {e}")
            return {}


# Inicializar tabla al importar
UserSettingsManager.init_db()
