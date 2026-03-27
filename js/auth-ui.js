let authLoginResolver = null;
let authRolesCache = [];
let authPermissionsCache = [];
let authUsersCache = [];
let currentPermEditor = null;

const PAGE_PERMISSION_MAP = {
  dashboard: 'dashboard.view',
  inventario: 'items.view',
  componentes: 'componentes.view',
  ingresos: 'ingresos.view',
  'nuevo-ingreso': 'ingresos.view',
  consumos: 'consumos.view',
  sellos: 'sellos.view',
  ordenes: 'ordenes.view',
  usuarios: 'empleados.view',
  paniol: 'herramientas.view',
  auditorias: 'auditorias.view',
  'auditorias-sesiones': 'auditorias.view',
  'auditorias-abc': 'auditorias.view',
  'auditorias-planes': 'auditorias.view'
};

const PAGE_PRIORITY = [
  'dashboard',
  'inventario',
  'ingresos',
  'consumos',
  'sellos',
  'ordenes',
  'componentes',
  'usuarios',
  'paniol',
  'auditorias'
];

const PERMISSION_CATEGORY_LABELS = {
  dashboard: 'Dashboard',
  bodega: 'Bodega',
  panol: 'Pañol',
  auditoria: 'Auditoría',
  general: 'General',
  seguridad: 'Seguridad'
};

function setAuthLockState(locked) {
  document.body.classList.toggle('auth-locked', !!locked);
  const screen = $('auth-lock-screen');
  if (screen) screen.style.display = locked ? 'flex' : 'none';
}

function authGetCurrentUser() {
  const user = getAuthUser();
  return user || null;
}

function authHasPermission(code) {
  const user = authGetCurrentUser();
  if (!user) return false;
  const permissions = Array.isArray(user.permissions) ? user.permissions : [];
  if (permissions.includes('*')) return true;
  return permissions.includes(code);
}

function authCanAccessPage(page) {
  if (!page) return false;
  const needed = PAGE_PERMISSION_MAP[page];
  if (!needed) return true;
  return authHasPermission(needed);
}

function getPreferredHomePage() {
  for (const page of PAGE_PRIORITY) {
    if (authCanAccessPage(page)) return page;
  }
  return 'sellos';
}

function updateAuthTopbarUI() {
  const user = authGetCurrentUser();
  const chip = $('auth-user-chip');
  const loginBtn = $('auth-login-btn');
  const logoutBtn = $('auth-logout-btn');

  if (!chip || !loginBtn || !logoutBtn) return;

  if (user) {
    const role = user.role || 'usuario';
    const label = user.display_name || user.username || 'Usuario';
    chip.textContent = `${label} (${role})`;
    loginBtn.style.display = 'none';
    logoutBtn.style.display = '';
  } else {
    chip.textContent = 'Sin sesión';
    loginBtn.style.display = '';
    logoutBtn.style.display = 'none';
  }
}

function toggleNodeByPermission(node, permissionCode) {
  if (!node) return;
  const allowed = authHasPermission(permissionCode);
  node.style.display = allowed ? '' : 'none';
}

function applyFrontendAccessByPermissions() {
  Object.entries(PAGE_PERMISSION_MAP).forEach(([page, permission]) => {
    const navNode = document.querySelector(`.ni[data-p="${page}"]`);
    const subNode = document.querySelector(`.sni[data-p="${page}"]`);
    const pageNode = document.getElementById(`p-${page}`);
    const allowed = authHasPermission(permission);

    if (navNode) navNode.style.display = allowed ? '' : 'none';
    if (subNode) subNode.style.display = allowed ? '' : 'none';
    if (pageNode) pageNode.style.display = allowed ? '' : 'none';
  });

  const canExport = authHasPermission('exports.view');
  document.querySelectorAll('.s-backup .s-btn').forEach((btn) => {
    btn.style.display = canExport ? '' : 'none';
  });

  const globalSearch = $('gsearch');
  if (globalSearch) {
    globalSearch.style.display = authHasPermission('items.view') ? '' : 'none';
  }
}

function openLoginModal() {
  if ($('login-msg')) $('login-msg').textContent = 'Usuarios iniciales: admin/admin · operador_cnc_sellos/cnc123';
  if ($('login-username')) $('login-username').value = '';
  if ($('login-password')) $('login-password').value = '';
  setAuthLockState(true);
  setTimeout(() => $('login-username')?.focus(), 30);
}

function closeLoginModal() {
  setAuthLockState(false);
}

async function submitLoginModal() {
  const username = ($('login-username')?.value || '').trim();
  const password = ($('login-password')?.value || '');

  if (!username || !password) {
    if ($('login-msg')) $('login-msg').textContent = 'Usuario y contraseña requeridos';
    return;
  }

  const login = await loginWithCredentials(username, password);
  if (!login?.token) {
    if ($('login-msg')) $('login-msg').textContent = 'Credenciales inválidas';
    return;
  }

  updateAuthTopbarUI();
  closeLoginModal();

  if (typeof authSyncMe === 'function') {
    await authSyncMe();
  }

  if (authLoginResolver) {
    const resolve = authLoginResolver;
    authLoginResolver = null;
    resolve(login.token);
  }

  if (typeof go === 'function') {
    go(getPreferredHomePage());
  }

  toast('Sesión iniciada', 'ok');
}

async function requestInteractiveLogin() {
  return await new Promise((resolve) => {
    authLoginResolver = resolve;
    openLoginModal();
  });
}

async function logoutSession() {
  const token = getAuthToken();
  if (token) {
    try {
      await fetch('/api/auth/logout', {
        method: 'POST',
        headers: {
          Authorization: 'Bearer ' + token
        }
      });
    } catch (_) {
      // no-op
    }
  }

  clearAuthSession();
  setAuthLockState(true);
  updateAuthTopbarUI();
  if (typeof go === 'function') go('dashboard');
  toast('Sesión cerrada', 'ok');
  openLoginModal();
}

async function authSyncMe() {
  const token = getAuthToken();
  if (!token) {
    setAuthLockState(true);
    updateAuthTopbarUI();
    return;
  }

  try {
    const response = await fetch('/api/auth/me', {
      headers: {
        Authorization: 'Bearer ' + token
      }
    });
    if (!response.ok) {
      clearAuthSession();
      setAuthLockState(true);
      updateAuthTopbarUI();
      return;
    }

    const data = await response.json();
    if (data?.ok && data.user) {
      setAuthSession(token, data.user);
    }
  } catch (_) {
    // no-op
  }

  updateAuthTopbarUI();
  applyFrontendAccessByPermissions();
  setAuthLockState(!authGetCurrentUser());
}

function renderSystemUsersRows(users) {
  const body = $('sys-users-body');
  if (!body) return;

  if (!users.length) {
    body.innerHTML = '<tr><td colspan="6" style="text-align:center;padding:24px;color:var(--t3)">Sin usuarios del sistema</td></tr>';
    return;
  }

  body.innerHTML = users.map((user) => {
    const activeBadge = `<span class="badge-condicion ${user.is_active ? 'operativa' : 'defectuosa'}">${user.is_active ? 'Activo' : 'Inactivo'}</span>`;
    const lastLogin = user.last_login_at || '-';
    return `<tr>
      <td class="m" style="font-weight:700;color:var(--ac)">${h(user.username)}</td>
      <td>${h(user.display_name || user.username)}</td>
      <td>${h(prettyRoleCode(user.role || '-'))}</td>
      <td>${activeBadge}</td>
      <td class="m" style="font-size:11px">${h(lastLogin)}</td>
      <td>
        <div style="display:flex;gap:4px;justify-content:center">
          <button class="bi bi-ac" title="Editar" onclick="editSystemUser(${user.id})">✎</button>
          <button class="bi" title="Permisos" onclick="openSystemPermissions(${user.id})" style="color:var(--ok)">🔐</button>
        </div>
      </td>
    </tr>`;
  }).join('');
}

function rolePermissionsSet(roleCode) {
  const role = authRolesCache.find((r) => r.code === roleCode);
  const list = role?.permissions || [];
  return new Set(list);
}

function effectivePermissionsForUser(user) {
  const base = rolePermissionsSet(user.role);
  if (base.has('*')) {
    return new Set(authPermissionsCache.map((p) => p.code));
  }

  const effective = new Set(base);
  const overrides = Array.isArray(user.permission_overrides) ? user.permission_overrides : [];
  overrides.forEach((override) => {
    if (override.granted) effective.add(override.code);
    else effective.delete(override.code);
  });
  return effective;
}

function groupPermissionsByCategory() {
  const groups = {};
  authPermissionsCache.forEach((permission) => {
    const category = permission.category || 'general';
    if (!groups[category]) groups[category] = [];
    groups[category].push(permission);
  });
  return groups;
}

function prettyRoleCode(roleCode) {
  const role = authRolesCache.find((entry) => entry.code === roleCode);
  if (role?.label) return role.label;
  return String(roleCode || '')
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (match) => match.toUpperCase());
}

function prettyPermissionCode(code) {
  return String(code || '')
    .replace(/^paniol\./, 'pañol.')
    .replace(/^panol\./, 'pañol.');
}

function prettyCategory(category) {
  return PERMISSION_CATEGORY_LABELS[category] || String(category || 'General').toUpperCase();
}

function openNewSystemUser() {
  $('msu-title').textContent = 'Nuevo Usuario del Sistema';
  $('msu-id').value = '';
  $('msu-username').value = '';
  $('msu-display').value = '';
  $('msu-password').value = '';
  $('msu-active').value = '1';
  $('msu-username').readOnly = false;
  populateRoleSelect('msu-role', 'consulta');
  oM('m-system-user');
}

function editSystemUser(userId) {
  const user = authUsersCache.find((u) => Number(u.id) === Number(userId));
  if (!user) {
    toast('Usuario no encontrado', 'err');
    return;
  }

  $('msu-title').textContent = 'Editar Usuario del Sistema';
  $('msu-id').value = String(user.id);
  $('msu-username').value = user.username || '';
  $('msu-display').value = user.display_name || user.username || '';
  $('msu-password').value = '';
  $('msu-active').value = user.is_active ? '1' : '0';
  $('msu-username').readOnly = true;
  populateRoleSelect('msu-role', user.role || 'consulta');
  oM('m-system-user');
}

function populateRoleSelect(selectId, selectedCode) {
  const select = $(selectId);
  if (!select) return;

  select.innerHTML = authRolesCache
    .map((role) => `<option value="${h(role.code)}" ${role.code === selectedCode ? 'selected' : ''}>${h(role.label || role.code)}</option>`)
    .join('');
}

async function saveSystemUser() {
  const id = ($('msu-id').value || '').trim();
  const username = ($('msu-username').value || '').trim();
  const displayName = ($('msu-display').value || '').trim();
  const role = ($('msu-role').value || 'consulta').trim();
  const isActive = $('msu-active').value === '1';
  const password = $('msu-password').value || '';

  if (!username) return toast('Username requerido', 'err');
  if (!id && !password) return toast('Password requerida al crear', 'err');

  const payload = {
    username,
    display_name: displayName,
    role,
    is_active: isActive,
  };
  if (password) payload.password = password;

  const url = id ? `/api/auth/users/${id}` : '/api/auth/users';
  const method = id ? 'PUT' : 'POST';

  const response = await api(url, {
    method,
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  });

  if (response?.ok) {
    toast(response.msg || 'Usuario guardado');
    cM('m-system-user');
    await loadSystemUsersAdminPanel();
  } else if (response) {
    toast(response.msg || 'No se pudo guardar', 'err');
  }
}

function openSystemPermissions(userId) {
  const user = authUsersCache.find((u) => Number(u.id) === Number(userId));
  if (!user) {
    toast('Usuario no encontrado', 'err');
    return;
  }

  if (user.role === 'admin') {
    toast('Administrador ya tiene todos los permisos (*)', 'info');
    return;
  }

  const base = rolePermissionsSet(user.role);
  const effective = effectivePermissionsForUser(user);
  const overrides = new Map((user.permission_overrides || []).map((o) => [o.code, !!o.granted]));

  currentPermEditor = { user, base, effective, overrides };

  $('msp-sub').textContent = `${user.username} · Rol ${prettyRoleCode(user.role)}`;
  $('msp-help').textContent = 'Marca para permitir. Desmarca para denegar incluso si viene por rol.';

  const grouped = groupPermissionsByCategory();
  const categories = Object.keys(grouped).sort();

  $('msp-list').innerHTML = categories.map((category) => {
    const permissions = grouped[category];
    const rows = permissions.map((permission) => {
      const checked = effective.has(permission.code) ? 'checked' : '';
      const inherited = base.has(permission.code) && !overrides.has(permission.code);
      const tag = inherited
        ? '<span style="font-size:10px;color:var(--t3);font-weight:600">Rol base</span>'
        : '<span style="font-size:10px;color:var(--ac);font-weight:600">Override</span>';
      return `<label style="display:flex;align-items:center;justify-content:space-between;gap:10px;padding:9px 0;border-bottom:1px solid var(--bd)">
        <span><b style="font-size:13px">${h(permission.label || '')}</b></span>
        <span style="display:flex;align-items:center;gap:8px">${tag}<input type="checkbox" data-perm="${h(permission.code)}" ${checked}></span>
      </label>`;
    }).join('');

    return `<div style="margin-bottom:12px;border:1px solid var(--bd);border-radius:8px;padding:12px;background:var(--bg2)"><div style="font-size:11px;color:var(--t2);text-transform:uppercase;font-weight:700;margin-bottom:8px;letter-spacing:.5px">${h(prettyCategory(category))}</div>${rows}</div>`;
  }).join('');

  oM('m-system-perms');
}

async function saveSystemPermissions() {
  if (!currentPermEditor) return;

  const { user, base } = currentPermEditor;
  const checks = Array.from(document.querySelectorAll('#msp-list input[type="checkbox"][data-perm]'));

  const grants = [];
  const revokes = [];

  checks.forEach((check) => {
    const code = check.getAttribute('data-perm');
    if (!code) return;
    const wants = check.checked;
    const baseHas = base.has(code);

    if (wants && !baseHas) grants.push(code);
    if (!wants && baseHas) revokes.push(code);
    if (wants && baseHas) {
      // hereda permiso, limpiar posible revoke manual
    }
    if (!wants && !baseHas) {
      // no hereda permiso, limpiar posible grant manual
    }
  });

  const response = await api(`/api/auth/users/${user.id}/permissions`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ grants, revokes })
  });

  if (response?.ok) {
    toast(response.msg || 'Permisos guardados');
    cM('m-system-perms');
    currentPermEditor = null;
    await loadSystemUsersAdminPanel();
  } else if (response) {
    toast(response.msg || 'No se pudieron guardar permisos', 'err');
  }
}

async function loadSystemUsersAdminPanel() {
  const body = $('sys-users-body');
  const help = $('sys-users-help');
  const btn = $('btn-new-system-user');
  if (!body || !help || !btn) return;

  await authSyncMe();
  const isAdmin = authHasPermission('users.manage');

  if (!isAdmin) {
    btn.style.display = 'none';
    help.textContent = 'Solo Administrador puede gestionar usuarios del sistema y permisos.';
    body.innerHTML = '<tr><td colspan="6" style="text-align:center;padding:24px;color:var(--t3)">Acceso restringido</td></tr>';
    return;
  }

  btn.style.display = '';
  help.textContent = 'Admin puede crear cuentas, asignar roles y definir permisos por etiqueta.';

  const [rolesRes, permissionsRes, usersRes] = await Promise.all([
    api('/api/auth/roles'),
    api('/api/auth/permissions'),
    api('/api/auth/users')
  ]);

  if (!rolesRes?.ok || !permissionsRes?.ok || !usersRes?.ok) {
    body.innerHTML = '<tr><td colspan="6" style="text-align:center;padding:24px;color:var(--no)">No se pudo cargar la administración de usuarios</td></tr>';
    return;
  }

  authRolesCache = rolesRes.roles || [];
  authPermissionsCache = permissionsRes.permissions || [];
  authUsersCache = usersRes.users || [];

  renderSystemUsersRows(authUsersCache);
}

window.openLoginModal = openLoginModal;
window.submitLoginModal = submitLoginModal;
window.logoutSession = logoutSession;
window.requestInteractiveLogin = requestInteractiveLogin;
window.loadSystemUsersAdminPanel = loadSystemUsersAdminPanel;
window.openNewSystemUser = openNewSystemUser;
window.editSystemUser = editSystemUser;
window.saveSystemUser = saveSystemUser;
window.openSystemPermissions = openSystemPermissions;
window.saveSystemPermissions = saveSystemPermissions;
window.authCanAccessPage = authCanAccessPage;
window.getPreferredHomePage = getPreferredHomePage;

document.addEventListener('DOMContentLoaded', async () => {
  updateAuthTopbarUI();
  await authSyncMe();

  const loginPassword = $('login-password');
  if (loginPassword) {
    loginPassword.addEventListener('keydown', (event) => {
      if (event.key === 'Enter') submitLoginModal();
    });
  }
});
