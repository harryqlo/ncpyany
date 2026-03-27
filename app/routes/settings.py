
from flask import Blueprint, jsonify, request, g
from user_settings import UserSettingsManager

bp = Blueprint('settings', __name__, url_prefix='/api/user/settings')


def _current_user_key():
    current_user = getattr(g, 'current_user', None)
    if not current_user:
        return 'default'
    return current_user.get('username') or str(current_user.get('id') or 'default')

@bp.route('', methods=['GET'], strict_slashes=False)
def api_get_settings():
    """Obtiene configuraciones del usuario"""
    if not UserSettingsManager:
        return jsonify({'ok': False, 'msg': 'No disponible'}), 500
    settings = UserSettingsManager.get_settings(_current_user_key())
    return jsonify({'ok': True, 'settings': settings})

@bp.route('', methods=['POST'], strict_slashes=False)
def api_save_settings():
    """Guarda configuraciones del usuario"""
    if not UserSettingsManager:
        return jsonify({'ok': False, 'msg': 'No disponible'}), 500
    
    try:
        data = request.get_json() or {}
        result = UserSettingsManager.save_settings(_current_user_key(), data)
        return jsonify(result), 200 if result['ok'] else 400
    except Exception as e:
        return jsonify({'ok': False, 'msg': str(e)}), 500

@bp.route('/reset', methods=['POST'])
def api_reset_settings():
    """Reinicia configuraciones a valores por defecto"""
    if not UserSettingsManager:
        return jsonify({'ok': False, 'msg': 'No disponible'}), 500
    
    result = UserSettingsManager.reset_settings(_current_user_key())
    return jsonify(result), 200 if result['ok'] else 400
