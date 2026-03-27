"""
Seguridad y control de acceso (RBAC) para North Chrome.

Incluye:
- Usuarios del sistema (separados de empleados operativos)
- Roles base (admin, bodeguero, panolero, bodeguero_panolero, consulta)
- Etiquetas de permisos asignables por administrador
- Tokens Bearer persistidos en BD
"""

from __future__ import annotations

import hashlib
import secrets
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set

from werkzeug.security import check_password_hash, generate_password_hash

from app.db import get_db
from config import (
    ALLOW_INSECURE_DEFAULT_USERS,
    AUTH_TOKEN_TTL_HOURS,
    BOOTSTRAP_ADMIN_PASSWORD,
    BOOTSTRAP_ADMIN_USERNAME,
    BOOTSTRAP_CNC_PASSWORD,
    FLASK_ENV,
    IS_PRODUCTION,
    PASSWORD_MIN_LENGTH,
    PASSWORD_REQUIRE_DIGIT,
    PASSWORD_REQUIRE_LOWER,
    PASSWORD_REQUIRE_UPPER,
)


PERMISSIONS_CATALOG = [
    ('dashboard.view', 'Ver dashboard', 'dashboard'),
    ('items.view', 'Ver inventario', 'bodega'),
    ('items.manage', 'Gestionar inventario', 'bodega'),
    ('ingresos.view', 'Ver ingresos', 'bodega'),
    ('ingresos.manage', 'Gestionar ingresos', 'bodega'),
    ('consumos.view', 'Ver consumos', 'bodega'),
    ('consumos.manage', 'Gestionar consumos', 'bodega'),
    ('componentes.view', 'Ver componentes', 'bodega'),
    ('componentes.manage', 'Gestionar componentes', 'bodega'),
    ('ordenes.view', 'Ver órdenes', 'bodega'),
    ('ordenes.manage', 'Gestionar órdenes', 'bodega'),
    ('sellos.view', 'Ver sellos', 'bodega'),
    ('sellos.manage', 'Gestionar sellos', 'bodega'),
    ('herramientas.view', 'Ver herramientas', 'panol'),
    ('herramientas.manage', 'Gestionar herramientas', 'panol'),
    ('paniol.checkout', 'Registrar préstamos', 'panol'),
    ('paniol.checkin', 'Registrar devoluciones', 'panol'),
    ('mantenimiento.view', 'Ver mantenimiento', 'panol'),
    ('mantenimiento.manage', 'Gestionar mantenimiento', 'panol'),
    ('auditorias.view', 'Ver auditorías', 'auditoria'),
    ('auditorias.manage', 'Gestionar auditorías', 'auditoria'),
    ('empleados.view', 'Ver empleados', 'general'),
    ('empleados.manage', 'Gestionar empleados', 'general'),
    ('exports.view', 'Exportar reportes', 'general'),
    ('settings.own', 'Gestionar configuración personal', 'general'),
    ('users.manage', 'Gestionar usuarios y permisos', 'seguridad'),
]


ROLE_TEMPLATES = {
    'admin': {
        'label': 'Administrador',
        'permissions': {'*'}
    },
    'bodeguero': {
        'label': 'Bodeguero',
        'permissions': {
            'dashboard.view',
            'items.view', 'items.manage',
            'ingresos.view', 'ingresos.manage',
            'consumos.view', 'consumos.manage',
            'componentes.view', 'componentes.manage',
            'ordenes.view', 'ordenes.manage',
            'sellos.view', 'sellos.manage',
            'auditorias.view', 'auditorias.manage',
            'empleados.view',
            'exports.view',
            'settings.own',
        }
    },
    'panolero': {
        'label': 'Pañolero',
        'permissions': {
            'dashboard.view',
            'herramientas.view', 'herramientas.manage',
            'paniol.checkout', 'paniol.checkin',
            'mantenimiento.view', 'mantenimiento.manage',
            'consumos.view',
            'auditorias.view',
            'empleados.view',
            'settings.own',
        }
    },
    'bodeguero_panolero': {
        'label': 'Bodeguero/Pañolero',
        'permissions': {
            'dashboard.view',
            'items.view', 'items.manage',
            'ingresos.view', 'ingresos.manage',
            'consumos.view', 'consumos.manage',
            'componentes.view', 'componentes.manage',
            'ordenes.view', 'ordenes.manage',
            'sellos.view', 'sellos.manage',
            'herramientas.view', 'herramientas.manage',
            'paniol.checkout', 'paniol.checkin',
            'mantenimiento.view', 'mantenimiento.manage',
            'auditorias.view', 'auditorias.manage',
            'empleados.view',
            'exports.view',
            'settings.own',
        }
    },
    'consulta': {
        'label': 'Consulta',
        'permissions': {
            'dashboard.view',
            'items.view',
            'ingresos.view',
            'consumos.view',
            'componentes.view',
            'ordenes.view',
            'sellos.view',
            'herramientas.view',
            'mantenimiento.view',
            'auditorias.view',
            'empleados.view',
            'exports.view',
            'settings.own',
        }
    },
    'operador_cnc_sellos': {
        'label': 'Operador CNC Sellos',
        'permissions': {
            'sellos.view',
            'sellos.manage',
            'settings.own',
        }
    },
}


def _normalize_text(value: str) -> str:
    return ''.join(ch.lower() for ch in (value or '').strip() if ch.isalnum())


def resolve_role_code(role_value: Optional[str]) -> Optional[str]:
    if role_value is None:
        return None

    raw = str(role_value).strip()
    if not raw:
        return None

    if raw in ROLE_TEMPLATES:
        return raw

    normalized_raw = _normalize_text(raw)

    for code, meta in ROLE_TEMPLATES.items():
        if normalized_raw == _normalize_text(code):
            return code
        label = meta.get('label') or ''
        if normalized_raw == _normalize_text(label):
            return code

    return None


def _utcnow_iso() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat()


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode('utf-8')).hexdigest()


def _validate_password_strength(password: str) -> Optional[str]:
    if not password or len(password) < PASSWORD_MIN_LENGTH:
        return f'Password debe tener al menos {PASSWORD_MIN_LENGTH} caracteres'

    if PASSWORD_REQUIRE_UPPER and not re.search(r'[A-Z]', password):
        return 'Password debe incluir al menos una mayúscula'
    if PASSWORD_REQUIRE_LOWER and not re.search(r'[a-z]', password):
        return 'Password debe incluir al menos una minúscula'
    if PASSWORD_REQUIRE_DIGIT and not re.search(r'\d', password):
        return 'Password debe incluir al menos un número'

    return None


def _seed_default_users(conn) -> None:
    admin_row = conn.execute(
        'SELECT id FROM system_users WHERE username = ?',
        [BOOTSTRAP_ADMIN_USERNAME]
    ).fetchone()

    if admin_row:
        return

    if BOOTSTRAP_ADMIN_PASSWORD:
        conn.execute(
            '''INSERT INTO system_users (username, password_hash, role_code, display_name, is_active, updated_at)
               VALUES (?, ?, ?, ?, 1, ?)''',
            [
                BOOTSTRAP_ADMIN_USERNAME,
                generate_password_hash(BOOTSTRAP_ADMIN_PASSWORD),
                'admin',
                'Administrador',
                _utcnow_iso()
            ]
        )

        if BOOTSTRAP_CNC_PASSWORD:
            cnc_row = conn.execute(
                'SELECT id FROM system_users WHERE username = ?',
                ['operador_cnc_sellos']
            ).fetchone()
            if not cnc_row:
                conn.execute(
                    '''INSERT INTO system_users (username, password_hash, role_code, display_name, is_active, updated_at)
                       VALUES (?, ?, ?, ?, 1, ?)''',
                    [
                        'operador_cnc_sellos',
                        generate_password_hash(BOOTSTRAP_CNC_PASSWORD),
                        'operador_cnc_sellos',
                        'Operador CNC Sellos',
                        _utcnow_iso()
                    ]
                )
        return

    if not IS_PRODUCTION or ALLOW_INSECURE_DEFAULT_USERS:
        conn.execute(
            '''INSERT INTO system_users (username, password_hash, role_code, display_name, is_active, updated_at)
               VALUES (?, ?, ?, ?, 1, ?)''',
            ['admin', generate_password_hash('admin'), 'admin', 'Administrador', _utcnow_iso()]
        )

        cnc_row = conn.execute(
            'SELECT id FROM system_users WHERE username = ?',
            ['operador_cnc_sellos']
        ).fetchone()
        if not cnc_row:
            conn.execute(
                '''INSERT INTO system_users (username, password_hash, role_code, display_name, is_active, updated_at)
                   VALUES (?, ?, ?, ?, 1, ?)''',
                [
                    'operador_cnc_sellos',
                    generate_password_hash('cnc123'),
                    'operador_cnc_sellos',
                    'Operador CNC Sellos',
                    _utcnow_iso()
                ]
            )


def init_security_schema() -> None:
    conn = get_db('general')
    try:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS system_users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                role_code TEXT NOT NULL DEFAULT 'consulta',
                display_name TEXT,
                is_active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT,
                last_login_at TEXT,
                login_count INTEGER NOT NULL DEFAULT 0
            )
        ''')

        conn.execute('''
            CREATE TABLE IF NOT EXISTS system_permissions (
                code TEXT PRIMARY KEY,
                label TEXT NOT NULL,
                category TEXT NOT NULL
            )
        ''')

        conn.execute('''
            CREATE TABLE IF NOT EXISTS system_roles (
                code TEXT PRIMARY KEY,
                label TEXT NOT NULL
            )
        ''')

        conn.execute('''
            CREATE TABLE IF NOT EXISTS system_role_permissions (
                role_code TEXT NOT NULL,
                permission_code TEXT NOT NULL,
                PRIMARY KEY (role_code, permission_code)
            )
        ''')

        conn.execute('''
            CREATE TABLE IF NOT EXISTS system_user_permissions (
                user_id INTEGER NOT NULL,
                permission_code TEXT NOT NULL,
                granted INTEGER NOT NULL DEFAULT 1,
                PRIMARY KEY (user_id, permission_code)
            )
        ''')

        conn.execute('''
            CREATE TABLE IF NOT EXISTS auth_tokens (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                token_hash TEXT UNIQUE NOT NULL,
                user_id INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                revoked INTEGER NOT NULL DEFAULT 0,
                revoked_at TEXT
            )
        ''')

        for code, label, category in PERMISSIONS_CATALOG:
            conn.execute(
                '''INSERT INTO system_permissions (code, label, category)
                   VALUES (?, ?, ?)
                   ON CONFLICT(code) DO UPDATE SET
                     label=excluded.label,
                     category=excluded.category''',
                [code, label, category]
            )

        for role_code, role_data in ROLE_TEMPLATES.items():
            conn.execute(
                'INSERT OR IGNORE INTO system_roles (code, label) VALUES (?, ?)',
                [role_code, role_data['label']]
            )

            if role_code == 'admin':
                conn.execute('DELETE FROM system_role_permissions WHERE role_code = ?', [role_code])
                conn.execute(
                    'INSERT OR IGNORE INTO system_role_permissions (role_code, permission_code) VALUES (?, ?)',
                    [role_code, '*']
                )
                continue

            conn.execute('DELETE FROM system_role_permissions WHERE role_code = ?', [role_code])
            for permission in role_data['permissions']:
                conn.execute(
                    'INSERT OR IGNORE INTO system_role_permissions (role_code, permission_code) VALUES (?, ?)',
                    [role_code, permission]
                )

        _seed_default_users(conn)

        conn.commit()
    finally:
        conn.close()


def authenticate_user(username: str, password: str) -> Optional[Dict]:
    conn = get_db('general')
    try:
        row = conn.execute(
            '''SELECT id, username, password_hash, role_code, display_name, is_active
               FROM system_users WHERE username = ?''',
            [username]
        ).fetchone()

        if not row:
            return None

        if not row[5]:
            return None

        if not check_password_hash(row[2], password):
            return None

        now = _utcnow_iso()
        conn.execute(
            '''UPDATE system_users
               SET last_login_at = ?, login_count = login_count + 1, updated_at = ?
               WHERE id = ?''',
            [now, now, row[0]]
        )
        conn.commit()

        return {
            'id': row[0],
            'username': row[1],
            'role': row[3],
            'display_name': row[4] or row[1],
            'is_active': bool(row[5]),
        }
    finally:
        conn.close()


def issue_token(user_id: int, hours: int = AUTH_TOKEN_TTL_HOURS) -> Dict:
    token = secrets.token_urlsafe(48)
    now = datetime.utcnow().replace(microsecond=0)
    expires = now + timedelta(hours=hours)

    conn = get_db('general')
    try:
        conn.execute(
            '''INSERT INTO auth_tokens (token_hash, user_id, created_at, expires_at, revoked)
               VALUES (?, ?, ?, ?, 0)''',
            [_token_hash(token), user_id, now.isoformat(), expires.isoformat()]
        )
        conn.commit()
    finally:
        conn.close()

    return {
        'token': token,
        'expires_at': expires.isoformat(),
    }


def revoke_token(token: str) -> None:
    conn = get_db('general')
    try:
        conn.execute(
            '''UPDATE auth_tokens
               SET revoked = 1, revoked_at = ?
               WHERE token_hash = ?''',
            [_utcnow_iso(), _token_hash(token)]
        )
        conn.commit()
    finally:
        conn.close()


def _fetch_user_by_id(user_id: int) -> Optional[Dict]:
    conn = get_db('general')
    try:
        row = conn.execute(
            '''SELECT id, username, role_code, display_name, is_active
               FROM system_users
               WHERE id = ?''',
            [user_id]
        ).fetchone()
        if not row:
            return None
        return {
            'id': row[0],
            'username': row[1],
            'role': row[2],
            'display_name': row[3] or row[1],
            'is_active': bool(row[4]),
        }
    finally:
        conn.close()


def _get_role_permissions(role_code: str) -> Set[str]:
    conn = get_db('general')
    try:
        rows = conn.execute(
            'SELECT permission_code FROM system_role_permissions WHERE role_code = ?',
            [role_code]
        ).fetchall()
        return {r[0] for r in rows}
    finally:
        conn.close()


def _get_user_overrides(user_id: int) -> Dict[str, bool]:
    conn = get_db('general')
    try:
        rows = conn.execute(
            'SELECT permission_code, granted FROM system_user_permissions WHERE user_id = ?',
            [user_id]
        ).fetchall()
        return {r[0]: bool(r[1]) for r in rows}
    finally:
        conn.close()


def resolve_permissions(user: Dict) -> Set[str]:
    role_permissions = _get_role_permissions(user['role'])
    if '*' in role_permissions:
        return {'*'}

    permissions = set(role_permissions)
    overrides = _get_user_overrides(user['id'])
    for code, granted in overrides.items():
        if granted:
            permissions.add(code)
        else:
            permissions.discard(code)
    return permissions


def get_user_from_token(token: str) -> Optional[Dict]:
    if not token:
        return None

    conn = get_db('general')
    try:
        row = conn.execute(
            '''SELECT user_id, expires_at, revoked
               FROM auth_tokens
               WHERE token_hash = ?''',
            [_token_hash(token)]
        ).fetchone()
    finally:
        conn.close()

    if not row:
        return None

    if row[2]:
        return None

    try:
        expires_at = datetime.fromisoformat(row[1])
    except Exception:
        return None

    if datetime.utcnow() > expires_at:
        return None

    user = _fetch_user_by_id(row[0])
    if not user or not user['is_active']:
        return None

    user['permissions'] = sorted(resolve_permissions(user))
    return user


def list_permissions() -> List[Dict]:
    conn = get_db('general')
    try:
        rows = conn.execute(
            'SELECT code, label, category FROM system_permissions ORDER BY category, code'
        ).fetchall()
        return [
            {'code': r[0], 'label': r[1], 'category': r[2]}
            for r in rows
        ]
    finally:
        conn.close()


def list_roles() -> List[Dict]:
    conn = get_db('general')
    try:
        rows = conn.execute(
            'SELECT code, label FROM system_roles ORDER BY code'
        ).fetchall()
        roles = []
        for row in rows:
            role_perms = conn.execute(
                'SELECT permission_code FROM system_role_permissions WHERE role_code = ? ORDER BY permission_code',
                [row[0]]
            ).fetchall()
            roles.append({
                'code': row[0],
                'label': row[1],
                'permissions': [r[0] for r in role_perms],
            })
        return roles
    finally:
        conn.close()


def list_system_users() -> List[Dict]:
    conn = get_db('general')
    try:
        rows = conn.execute(
            '''SELECT id, username, role_code, display_name, is_active, created_at, last_login_at, login_count
               FROM system_users
               ORDER BY username'''
        ).fetchall()

        users = []
        for row in rows:
            overrides = conn.execute(
                '''SELECT permission_code, granted
                   FROM system_user_permissions
                   WHERE user_id = ?
                   ORDER BY permission_code''',
                [row[0]]
            ).fetchall()
            users.append({
                'id': row[0],
                'username': row[1],
                'role': row[2],
                'display_name': row[3] or row[1],
                'is_active': bool(row[4]),
                'created_at': row[5],
                'last_login_at': row[6],
                'login_count': row[7],
                'permission_overrides': [
                    {'code': o[0], 'granted': bool(o[1])}
                    for o in overrides
                ],
            })
        return users
    finally:
        conn.close()


def create_system_user(username: str, password: str, role: str, display_name: str = '') -> Dict:
    role_code = resolve_role_code(role)
    if role_code not in ROLE_TEMPLATES:
        return {'ok': False, 'msg': 'Rol inválido'}
    if not username or len(username.strip()) < 3:
        return {'ok': False, 'msg': 'Username inválido'}
    password_error = _validate_password_strength(password)
    if password_error:
        return {'ok': False, 'msg': password_error}

    conn = get_db('general')
    try:
        exists = conn.execute(
            'SELECT 1 FROM system_users WHERE username = ?',
            [username.strip()]
        ).fetchone()
        if exists:
            return {'ok': False, 'msg': 'Username ya existe'}

        conn.execute(
            '''INSERT INTO system_users (username, password_hash, role_code, display_name, is_active, updated_at)
               VALUES (?, ?, ?, ?, 1, ?)''',
            [username.strip(), generate_password_hash(password), role_code, display_name.strip() or username.strip(), _utcnow_iso()]
        )
        conn.commit()
        return {'ok': True, 'msg': 'Usuario creado'}
    finally:
        conn.close()


def update_system_user(user_id: int, role: Optional[str] = None,
                       display_name: Optional[str] = None,
                       is_active: Optional[bool] = None,
                       password: Optional[str] = None) -> Dict:
    conn = get_db('general')
    try:
        row = conn.execute('SELECT id, username FROM system_users WHERE id = ?', [user_id]).fetchone()
        if not row:
            return {'ok': False, 'msg': 'Usuario no encontrado'}

        updates = []
        params = []

        if role is not None:
            role_code = resolve_role_code(role)
            if role_code not in ROLE_TEMPLATES:
                return {'ok': False, 'msg': 'Rol inválido'}
            updates.append('role_code = ?')
            params.append(role_code)

        if display_name is not None:
            updates.append('display_name = ?')
            params.append(display_name.strip() or row[1])

        if is_active is not None:
            updates.append('is_active = ?')
            params.append(1 if is_active else 0)

        if password:
            password_error = _validate_password_strength(password)
            if password_error:
                return {'ok': False, 'msg': password_error}
            updates.append('password_hash = ?')
            params.append(generate_password_hash(password))

        updates.append('updated_at = ?')
        params.append(_utcnow_iso())
        params.append(user_id)

        conn.execute(
            f"UPDATE system_users SET {', '.join(updates)} WHERE id = ?",
            params
        )
        conn.commit()
        return {'ok': True, 'msg': 'Usuario actualizado'}
    finally:
        conn.close()


def set_user_permission_overrides(user_id: int, grants: List[str], revokes: List[str]) -> Dict:
    conn = get_db('general')
    try:
        user_row = conn.execute('SELECT id FROM system_users WHERE id = ?', [user_id]).fetchone()
        if not user_row:
            return {'ok': False, 'msg': 'Usuario no encontrado'}

        valid_codes = {p[0] for p in PERMISSIONS_CATALOG}
        for code in grants + revokes:
            if code not in valid_codes:
                return {'ok': False, 'msg': f'Permiso inválido: {code}'}

        conn.execute('DELETE FROM system_user_permissions WHERE user_id = ?', [user_id])

        for code in grants:
            conn.execute(
                '''INSERT INTO system_user_permissions (user_id, permission_code, granted)
                   VALUES (?, ?, 1)
                   ON CONFLICT(user_id, permission_code)
                   DO UPDATE SET granted = 1''',
                [user_id, code]
            )

        for code in revokes:
            conn.execute(
                '''INSERT INTO system_user_permissions (user_id, permission_code, granted)
                   VALUES (?, ?, 0)
                   ON CONFLICT(user_id, permission_code)
                   DO UPDATE SET granted = 0''',
                [user_id, code]
            )

        conn.commit()
        return {'ok': True, 'msg': 'Permisos actualizados'}
    finally:
        conn.close()


def extract_bearer_token(auth_header: str) -> str:
    if not auth_header:
        return ''
    parts = auth_header.split(' ', 1)
    if len(parts) != 2:
        return ''
    if parts[0].lower() != 'bearer':
        return ''
    return parts[1].strip()


def required_permission_for_request(path: str, method: str) -> Optional[str]:
    # Público
    if path in ('/api/auth/login', '/api/auth/bootstrap', '/api/auth/setup-status'):
        return None

    if path.startswith('/api/auth/users') or path.startswith('/api/auth/permissions') or path.startswith('/api/auth/roles'):
        return 'users.manage'

    if path.startswith('/api/auth/me') or path.startswith('/api/auth/logout'):
        return ''  # requiere auth pero no permiso específico

    if path.startswith('/api/user/settings'):
        return 'settings.own'

    # Endpoints especiales Pañol
    if path.startswith('/api/herramientas/checkout'):
        return 'paniol.checkout'
    if path.startswith('/api/herramientas/checkin'):
        return 'paniol.checkin'

    route_map = [
        ('/api/dashboard', 'dashboard.view', 'dashboard.view'),
        ('/api/items', 'items.view', 'items.manage'),
        ('/api/ingresos', 'ingresos.view', 'ingresos.manage'),
        ('/api/consumos', 'consumos.view', 'consumos.manage'),
        ('/api/componentes', 'componentes.view', 'componentes.manage'),
        ('/api/ordenes', 'ordenes.view', 'ordenes.manage'),
        ('/api/sellos', 'sellos.view', 'sellos.manage'),
        ('/api/empleados', 'empleados.view', 'empleados.manage'),
        ('/api/herramientas', 'herramientas.view', 'herramientas.manage'),
        ('/api/mantenimiento', 'mantenimiento.view', 'mantenimiento.manage'),
        ('/api/auditorias', 'auditorias.view', 'auditorias.manage'),
        ('/api/exports', 'exports.view', 'exports.view'),
    ]

    for prefix, view_permission, manage_permission in route_map:
        if path.startswith(prefix):
            if method.upper() in ('GET', 'HEAD', 'OPTIONS'):
                return view_permission
            return manage_permission

    return ''
