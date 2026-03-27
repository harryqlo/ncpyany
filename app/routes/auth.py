"""
Rutas de autenticación y administración de usuarios del sistema.
"""

from datetime import datetime, timedelta

from flask import Blueprint, jsonify, request, g

from config import LOGIN_LOCKOUT_MINUTES, LOGIN_MAX_ATTEMPTS

from app.security import (
    authenticate_user,
    create_system_user,
    extract_bearer_token,
    get_user_from_token,
    init_security_schema,
    issue_token,
    list_permissions,
    list_roles,
    list_system_users,
    revoke_token,
    set_user_permission_overrides,
    update_system_user,
)


bp = Blueprint('auth', __name__, url_prefix='/api/auth')

_LOGIN_ATTEMPTS = {}


def _login_key(username: str) -> str:
    ip = (request.headers.get('X-Forwarded-For', '') or request.remote_addr or '').split(',')[0].strip()
    return f"{username.lower()}|{ip}"


def _is_login_locked(username: str):
    key = _login_key(username)
    now = datetime.utcnow()
    state = _LOGIN_ATTEMPTS.get(key)
    if not state:
        return False, 0

    lock_until = state.get('lock_until')
    if lock_until and now < lock_until:
        remaining = int((lock_until - now).total_seconds())
        return True, max(remaining, 1)

    if lock_until and now >= lock_until:
        _LOGIN_ATTEMPTS.pop(key, None)
        return False, 0

    return False, 0


def _register_login_failure(username: str):
    key = _login_key(username)
    now = datetime.utcnow()
    state = _LOGIN_ATTEMPTS.get(key, {'count': 0, 'lock_until': None})
    state['count'] += 1

    if state['count'] >= LOGIN_MAX_ATTEMPTS:
        state['lock_until'] = now + timedelta(minutes=LOGIN_LOCKOUT_MINUTES)

    _LOGIN_ATTEMPTS[key] = state


def _clear_login_failures(username: str):
    _LOGIN_ATTEMPTS.pop(_login_key(username), None)


@bp.route('/setup-status', strict_slashes=False)
def api_auth_setup_status():
    init_security_schema()
    return jsonify({'ok': True, 'seeded': True})


@bp.route('/bootstrap', strict_slashes=False)
def api_auth_bootstrap():
    init_security_schema()
    payload = {
        'ok': True,
        'roles': list_roles(),
        'permissions': list_permissions(),
    }
    current_user = getattr(g, 'current_user', None)
    if current_user:
        payload['current_user'] = current_user
    return jsonify(payload)


@bp.route('/login', methods=['POST'], strict_slashes=False)
def api_auth_login():
    init_security_schema()
    data = request.get_json() or {}
    username = (data.get('username') or '').strip()
    password = data.get('password') or ''

    if not username or not password:
        return jsonify({'ok': False, 'msg': 'Username y password requeridos'}), 400

    locked, remaining_seconds = _is_login_locked(username)
    if locked:
        return jsonify({'ok': False, 'msg': f'Temporalmente bloqueado. Intenta nuevamente en {remaining_seconds}s'}), 429

    user = authenticate_user(username, password)
    if not user:
        _register_login_failure(username)
        return jsonify({'ok': False, 'msg': 'Credenciales inválidas'}), 401

    _clear_login_failures(username)

    token_data = issue_token(user['id'])
    full_user = get_user_from_token(token_data['token']) or user

    return jsonify({
        'ok': True,
        'token': token_data['token'],
        'expires_at': token_data['expires_at'],
        'user': full_user,
    })


@bp.route('/logout', methods=['POST'], strict_slashes=False)
def api_auth_logout():
    token = extract_bearer_token(request.headers.get('Authorization', ''))
    if token:
        revoke_token(token)
    return jsonify({'ok': True, 'msg': 'Sesión cerrada'})


@bp.route('/me', strict_slashes=False)
def api_auth_me():
    current_user = getattr(g, 'current_user', None)
    if not current_user:
        return jsonify({'ok': False, 'msg': 'No autenticado'}), 401
    return jsonify({'ok': True, 'user': current_user})


@bp.route('/permissions', strict_slashes=False)
def api_auth_permissions():
    return jsonify({'ok': True, 'permissions': list_permissions()})


@bp.route('/roles', strict_slashes=False)
def api_auth_roles():
    return jsonify({'ok': True, 'roles': list_roles()})


@bp.route('/users', strict_slashes=False)
def api_auth_users():
    return jsonify({'ok': True, 'users': list_system_users()})


@bp.route('/users', methods=['POST'], strict_slashes=False)
def api_auth_create_user():
    data = request.get_json() or {}
    result = create_system_user(
        username=(data.get('username') or '').strip(),
        password=data.get('password') or '',
        role=(data.get('role') or 'consulta').strip(),
        display_name=(data.get('display_name') or '').strip(),
    )
    status = 200 if result.get('ok') else 400
    return jsonify(result), status


@bp.route('/users/<int:user_id>', methods=['PUT'], strict_slashes=False)
def api_auth_update_user(user_id):
    data = request.get_json() or {}
    result = update_system_user(
        user_id=user_id,
        role=data.get('role'),
        display_name=data.get('display_name'),
        is_active=data.get('is_active'),
        password=data.get('password'),
    )
    status = 200 if result.get('ok') else 400
    return jsonify(result), status


@bp.route('/users/<int:user_id>/permissions', methods=['PUT'], strict_slashes=False)
def api_auth_update_user_permissions(user_id):
    data = request.get_json() or {}
    grants = data.get('grants') or []
    revokes = data.get('revokes') or []
    result = set_user_permission_overrides(user_id, grants, revokes)
    status = 200 if result.get('ok') else 400
    return jsonify(result), status
