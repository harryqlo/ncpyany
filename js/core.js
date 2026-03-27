const A = '';
const AUTH_TOKEN_KEY = 'nc_auth_token';
const AUTH_USER_KEY = 'nc_auth_user';
const AUDITORIAS_ENABLED = true;
let iS = { p: 1, s: 'nombre', d: 'asc' }, igS = { p: 1 }, coS = { p: 1 }, seS = { p: 1 }, otS = { p: 1 }, kxS = { p: 1, sku: '' };
let niItems = [], ncItems = [], isEditingIng = false, isViewingIng = false;

function $(id) { return document.getElementById(id); }

function getAuthToken() {
  return localStorage.getItem(AUTH_TOKEN_KEY) || '';
}

function getAuthUser() {
  try {
    return JSON.parse(localStorage.getItem(AUTH_USER_KEY) || 'null');
  } catch (_) {
    return null;
  }
}

function setAuthSession(token, user) {
  if (token) localStorage.setItem(AUTH_TOKEN_KEY, token);
  if (user) localStorage.setItem(AUTH_USER_KEY, JSON.stringify(user));
  window.currentAuthUser = user || null;
}

function clearAuthSession() {
  localStorage.removeItem(AUTH_TOKEN_KEY);
  localStorage.removeItem(AUTH_USER_KEY);
  window.currentAuthUser = null;
}

async function loginWithCredentials(username, password) {
  const response = await fetch(A + '/api/auth/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password })
  });
  const data = await response.json();
  if (!response.ok || !data?.ok || !data?.token) return null;
  setAuthSession(data.token, data.user || null);
  return data;
}

async function ensureAuthSession() {
  const existing = getAuthToken();
  if (existing) return existing;

  if (typeof requestInteractiveLogin === 'function') {
    return await requestInteractiveLogin();
  }

  toast('Abre el inicio de sesión para continuar', 'warn');
  return '';
}

// Debounce genérico para búsquedas en vivo
const _dbTimers = {};
const _apiInFlightGetControllers = new Map();
function dbSearch(key, fn, delay) {
  clearTimeout(_dbTimers[key]);
  _dbTimers[key] = setTimeout(fn, delay || 350);
}

function clearSectionFilters(fieldIds, refreshFn) {
  if (!Array.isArray(fieldIds)) return;

  fieldIds.forEach((id) => {
    const el = $(id);
    if (!el) return;

    if (el.tagName === 'SELECT') {
      el.selectedIndex = 0;
      return;
    }

    if (el.type === 'checkbox' || el.type === 'radio') {
      el.checked = false;
      return;
    }

    el.value = '';
  });

  if (typeof refreshFn === 'function') {
    refreshFn();
  }
}

function getUiSettings() {
  try {
    return JSON.parse(localStorage.getItem('nc_settings') || '{}');
  } catch (e) {
    return {};
  }
}

function saveSidebarPreference(collapsed) {
  const settings = getUiSettings();
  settings.sidebarCollapsed = collapsed;
  try {
    localStorage.setItem('nc_settings', JSON.stringify(settings));
  } catch (e) {
    console.warn('No se pudo guardar el estado del sidebar', e);
  }
}

function applyStoredSidebarState() {
  if (window.innerWidth < 768) return;
  const sidebar = $('sidebar');
  const main = $('main-container');
  const btn = $('toggle-btn');
  if (!sidebar || !main || !btn) return;

  const settings = getUiSettings();
  const collapsed = !!settings.sidebarCollapsed;
  sidebar.classList.toggle('collapsed', collapsed);
  main.classList.toggle('sidebar-collapsed', collapsed);
  btn.classList.toggle('menu-hidden', collapsed);
  sidebar.style.pointerEvents = collapsed ? 'none' : '';
  btn.innerHTML = collapsed ? '<span>☰</span>' : '<span>✕</span>';
}

let lastViewportMode = window.innerWidth >= 768 ? 'desktop' : 'mobile';
let resizeRafId = null;

function applyResponsiveSidebarLayout(force = false) {
  const currentMode = window.innerWidth >= 768 ? 'desktop' : 'mobile';
  if (!force && currentMode === lastViewportMode) return;

  const sidebar = $('sidebar');
  const overlay = $('sidebar-overlay');
  if (!sidebar) {
    lastViewportMode = currentMode;
    return;
  }

  if (currentMode === 'desktop') {
    sidebar.classList.remove('open');
    if (overlay) overlay.classList.remove('active');
    applyStoredSidebarState();
  } else {
    sidebar.classList.remove('collapsed');
    sidebar.style.pointerEvents = '';
    const main = $('main-container');
    if (main) main.classList.remove('sidebar-collapsed');
  }

  lastViewportMode = currentMode;
}

function refreshSidebarTitles() {
  document.querySelectorAll('.ni, .sni').forEach((node) => {
    const text = node.textContent.replace(/▾|▸/g, '').trim();
    if (text) node.title = text;
  });
}

function enhanceAccessibility() {
  document.querySelectorAll('.ni, .sni').forEach((node) => {
    const text = (node.textContent || '').replace(/▾|▸/g, '').trim();
    if (!node.getAttribute('role')) node.setAttribute('role', 'button');
    if (!node.getAttribute('aria-label') && text) node.setAttribute('aria-label', text);
    if (!node.hasAttribute('tabindex')) node.setAttribute('tabindex', '0');
  });

  document.querySelectorAll('button, .btn, .bi, .mx, .toggle-sidebar, .s-btn').forEach((node) => {
    const text = (node.textContent || '').replace(/[\n\r\t]+/g, ' ').trim();
    const title = (node.getAttribute('title') || '').trim();
    if (!node.getAttribute('aria-label')) {
      if (text) node.setAttribute('aria-label', text);
      else if (title) node.setAttribute('aria-label', title);
    }
  });
}

function loadAuditoriasPage(page) {
  if (!AUDITORIAS_ENABLED) return;
  if (typeof Auditorias === 'undefined') return;
  if (typeof Auditorias.ensureInit === 'function') Auditorias.ensureInit();

  if (page === 'auditorias') {
    Auditorias.cargarEstadisticas();
    Auditorias.cargarPlanes();
    Auditorias.cargarSesiones(1);
    return;
  }
  if (page === 'auditorias-sesiones') {
    Auditorias.cargarSesiones(1);
    return;
  }
  if (page === 'auditorias-abc') {
    Auditorias.cargarTablaABC(1);
    return;
  }
  if (page === 'auditorias-planes') {
    Auditorias.cargarPlanes();
  }
}

async function api(u, o) {
  const opts = o ? { ...o } : {};
  opts.headers = { ...(opts.headers || {}) };
  const method = (opts.method || 'GET').toUpperCase();
  const isAbortableGet = method === 'GET' && !opts.body;
  const requestKey = isAbortableGet ? `${method}:${u}` : '';
  let requestController = null;

  if (isAbortableGet) {
    const previousController = _apiInFlightGetControllers.get(requestKey);
    if (previousController) previousController.abort();

    requestController = new AbortController();
    _apiInFlightGetControllers.set(requestKey, requestController);
    opts.signal = requestController.signal;
  }

  if (!u.startsWith('/api/auth/login') && !u.startsWith('/api/auth/bootstrap') && !u.startsWith('/api/auth/setup-status')) {
    const token = await ensureAuthSession();
    if (!token) return null;
    opts.headers.Authorization = 'Bearer ' + token;
  }

  try {
    let r = await fetch(A + u, opts);

    if (r.status === 401 && !u.startsWith('/api/auth/login')) {
      clearAuthSession();
      const refreshedToken = await ensureAuthSession();
      if (!refreshedToken) return { ok: false, msg: 'No autenticado' };
      opts.headers.Authorization = 'Bearer ' + refreshedToken;
      r = await fetch(A + u, opts);
    }

    const parseResponse = async (response) => {
      const contentType = (response.headers.get('content-type') || '').toLowerCase();
      if (contentType.includes('application/json')) {
        try {
          return await response.json();
        } catch (_) {
          return { ok: false, msg: `Respuesta JSON inválida (${response.status})` };
        }
      }

      let text = '';
      try {
        text = (await response.text() || '').trim();
      } catch (_) {
        text = '';
      }

      const shortText = text ? text.slice(0, 180) : '';
      return {
        ok: false,
        msg: shortText ? `Respuesta no JSON (${response.status}): ${shortText}` : `Respuesta no JSON (${response.status})`
      };
    };

    const parsed = await parseResponse(r);

    if (r.status === 403) {
      toast((parsed && parsed.msg) || 'Permiso denegado', 'err');
      return parsed;
    }

    return parsed;
  } catch (e) {
    if (e && e.name === 'AbortError') return null;
    toast('Error de conexion', 'err');
    return null;
  } finally {
    if (isAbortableGet && requestController) {
      const activeController = _apiInFlightGetControllers.get(requestKey);
      if (activeController === requestController) {
        _apiInFlightGetControllers.delete(requestKey);
      }
    }
  }
}

function _extractDownloadFilename(contentDisposition, fallbackName) {
  if (!contentDisposition) return fallbackName;
  const utf8Match = /filename\*=UTF-8''([^;]+)/i.exec(contentDisposition);
  if (utf8Match && utf8Match[1]) {
    try {
      return decodeURIComponent(utf8Match[1].trim());
    } catch (_) {
      return utf8Match[1].trim();
    }
  }

  const plainMatch = /filename="?([^";]+)"?/i.exec(contentDisposition);
  if (plainMatch && plainMatch[1]) return plainMatch[1].trim();
  return fallbackName;
}

async function downloadFileAuth(u, fallbackFileName = 'descarga.bin') {
  const opts = { method: 'GET', headers: {} };

  if (!u.startsWith('/api/auth/login') && !u.startsWith('/api/auth/bootstrap') && !u.startsWith('/api/auth/setup-status')) {
    const token = await ensureAuthSession();
    if (!token) return false;
    opts.headers.Authorization = 'Bearer ' + token;
  }

  try {
    let r = await fetch(A + u, opts);

    if (r.status === 401 && !u.startsWith('/api/auth/login')) {
      clearAuthSession();
      const refreshedToken = await ensureAuthSession();
      if (!refreshedToken) {
        toast('No autenticado', 'err');
        return false;
      }
      opts.headers.Authorization = 'Bearer ' + refreshedToken;
      r = await fetch(A + u, opts);
    }

    if (!r.ok) {
      let errMsg = `No se pudo descargar (${r.status})`;
      try {
        const contentType = (r.headers.get('content-type') || '').toLowerCase();
        if (contentType.includes('application/json')) {
          const body = await r.json();
          if (body && body.msg) errMsg = body.msg;
        }
      } catch (_) {
      }
      toast(errMsg, 'err');
      return false;
    }

    const blob = await r.blob();
    const fileName = _extractDownloadFilename(r.headers.get('content-disposition'), fallbackFileName);
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = fileName;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
    return true;
  } catch (_) {
    toast('Error de conexion', 'err');
    return false;
  }
}

function toast(m, t = 'ok') {
  const e = document.createElement('div');
  e.className = 'toast t-' + t;
  e.textContent = m;
  $('tc').appendChild(e);
  setTimeout(() => {
    e.style.opacity = '0';
    e.style.transition = 'opacity .3s';
    setTimeout(() => e.remove(), 300);
  }, 3500);
}

function oM(id) { $(id).classList.add('on'); }
function cM(id) { $(id).classList.remove('on'); }
function fm(n) { return n != null ? Number(n).toLocaleString('es-CL') : '-'; }
function fp(n) { return '$ ' + fm(Math.round(n || 0)); }
function r2(n) { return Math.round(n * 100) / 100; }

let confirmModalResolver = null;
let promptModalResolver = null;

function _focusLater(id) {
  setTimeout(() => $(id)?.focus(), 30);
}

function closeConfirmModal(result = false) {
  cM('m-confirm');
  const resolver = confirmModalResolver;
  confirmModalResolver = null;
  if (resolver) resolver(Boolean(result));
}

function showConfirmModal(options = {}) {
  const title = options.title || 'Confirmar acción';
  const message = options.message || '¿Deseas continuar?';
  const confirmText = options.confirmText || 'Aceptar';
  const cancelText = options.cancelText || 'Cancelar';
  const variant = options.variant === 'danger' ? 'danger' : 'primary';

  $('m-confirm-title').textContent = title;
  $('m-confirm-message').textContent = message;
  $('m-confirm-cancel').textContent = cancelText;
  $('m-confirm-ok').textContent = confirmText;
  $('m-confirm-ok').className = variant === 'danger' ? 'btn no' : 'btn bg';

  oM('m-confirm');
  _focusLater('m-confirm-ok');

  return new Promise((resolve) => {
    confirmModalResolver = resolve;
  });
}

function closeTextPromptModal(result = null) {
  cM('m-text-prompt');
  const resolver = promptModalResolver;
  promptModalResolver = null;
  if (resolver) resolver(result);
}

function acceptTextPromptModal() {
  const input = $('m-text-prompt-input');
  const value = (input?.value || '').trim();
  if ($('m-text-prompt-required')?.checked && !value) {
    input?.focus();
    input?.select();
    return;
  }
  closeTextPromptModal(value || null);
}

function showTextPromptModal(options = {}) {
  const title = options.title || 'Ingresa un valor';
  const message = options.message || '';
  const label = options.label || 'Valor';
  const placeholder = options.placeholder || '';
  const defaultValue = options.defaultValue || '';
  const confirmText = options.confirmText || 'Aceptar';
  const cancelText = options.cancelText || 'Cancelar';
  const required = options.required !== false;

  $('m-text-prompt-title').textContent = title;
  $('m-text-prompt-message').textContent = message;
  $('m-text-prompt-label').textContent = label;
  $('m-text-prompt-input').placeholder = placeholder;
  $('m-text-prompt-input').value = defaultValue;
  $('m-text-prompt-ok').textContent = confirmText;
  $('m-text-prompt-cancel').textContent = cancelText;
  $('m-text-prompt-required').checked = required;

  oM('m-text-prompt');
  _focusLater('m-text-prompt-input');
  $('m-text-prompt-input')?.select();

  return new Promise((resolve) => {
    promptModalResolver = resolve;
  });
}

function h(t) {
  if (t == null) return '';
  return String(t)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

function toggleSidebar() {
  const sidebar = $('sidebar');
  const main = $('main-container');
  const btn = $('toggle-btn');
  const overlay = $('sidebar-overlay');
  
  // En móvil (< 768px), usar clase 'open' con overlay
  if (window.innerWidth < 768) {
    sidebar.classList.toggle('open');
    if (overlay) {
      if (sidebar.classList.contains('open')) {
        overlay.classList.add('active');
      } else {
        overlay.classList.remove('active');
      }
    }
  } else {
    // En desktop, ocultar/mostrar sidebar completamente
    sidebar.classList.toggle('collapsed');
    main.classList.toggle('sidebar-collapsed');
    btn.classList.toggle('menu-hidden');
    
    // NO activar overlay en desktop
    if (overlay) {
      overlay.classList.remove('active');
    }
    
    const isCollapsed = sidebar.classList.contains('collapsed');
    sidebar.style.pointerEvents = isCollapsed ? 'none' : '';
    btn.innerHTML = isCollapsed ? '<span>☰</span>' : '<span>✕</span>';
    saveSidebarPreference(isCollapsed);
  }
}

function toggleMobileSidebar() {
  // Alias para mantener compatibilidad
  toggleSidebar();
}

function toggleNavGroup(group) {
  const node = $('snav-' + group);
  const caret = $('caret-' + group);
  if (!node) return;
  node.classList.toggle('open');
  if (caret) caret.textContent = node.classList.contains('open') ? '▾' : '▸';
}

function openNavGroup(group) {
  const node = $('snav-' + group);
  const caret = $('caret-' + group);
  if (!node) return;
  node.classList.add('open');
  if (caret) caret.textContent = '▾';
}

function syncPaniolSidebarTab(tab) {
  document.querySelectorAll('.sni[data-p^="paniol-"]').forEach((n) => n.classList.remove('on'));
  const selected = tab === 'dashboard'
    ? null
    : document.querySelector(`.sni[data-p="paniol-${tab}"]`);
  if (selected) selected.classList.add('on');

  const parent = document.querySelector('.ni[data-group="paniol"]');
  if (parent) parent.classList.add('on');
  openNavGroup('paniol');

  if ($('p-paniol') && $('p-paniol').classList.contains('on')) {
    const t = {
      dashboard: 'Dashboard Pañol',
      entrega: 'Pañol - Entrega',
      devolucion: 'Pañol - Devolución',
      inventario: 'Pañol - Inventario',
      historial: 'Pañol - Historial',
      mantenimiento: 'Pañol - Mantenimiento'
    };
    $('topbar-t').textContent = t[tab] || 'Dashboard Pañol';
  }
}

async function goPaniol(tab = 'entrega') {
  const validTabs = ['dashboard', 'entrega', 'devolucion', 'inventario', 'historial', 'mantenimiento'];
  const safeTab = validTabs.includes(tab) ? tab : 'dashboard';

  // Primero navegar a Pañol
  const pPaniol = document.getElementById('p-paniol');
  if (!pPaniol || !pPaniol.classList.contains('on')) {
    go('paniol');
  }

  // Luego activar tab solicitada
  if (typeof setPaniolRoute === 'function') {
    setPaniolRoute(safeTab);
  } else if (typeof switchPaniolTab === 'function') {
    switchPaniolTab(safeTab);
  }
  syncPaniolSidebarTab(safeTab);
}

function go(p) {
  const legacyHerramientas = p === 'herramientas';
  const requestedPage = legacyHerramientas ? 'paniol' : p;

  if (!AUDITORIAS_ENABLED && requestedPage.startsWith('auditorias')) {
    toast('Módulo Auditorías desactivado temporalmente', 'info');
    go('dashboard');
    return;
  }

  const targetPage = requestedPage;

  if (typeof authCanAccessPage === 'function' && !authCanAccessPage(targetPage)) {
    const fallback = (typeof getPreferredHomePage === 'function')
      ? getPreferredHomePage()
      : 'dashboard';
    if (fallback !== targetPage) {
      toast('No tienes acceso a esta vista', 'err');
      return go(fallback);
    }
  }

  document.querySelectorAll('.pg').forEach((s) => s.classList.remove('on'));
  document.querySelectorAll('.ni').forEach((n) => n.classList.remove('on'));
  document.querySelectorAll('.sni').forEach((n) => n.classList.remove('on'));

  const section = $('p-' + targetPage);
  if (!section) return;
  section.classList.add('on');

  const topNav = document.querySelector(`.ni[data-p="${targetPage}"]`);
  if (topNav) topNav.classList.add('on');

  const subNav = document.querySelector(`.sni[data-p="${targetPage}"]`);
  if (subNav) {
    subNav.classList.add('on');
    const parentGroup = subNav.closest('.snav');
    if (parentGroup && parentGroup.id) {
      const group = parentGroup.id.replace('snav-', '');
      const parent = document.querySelector(`.ni[data-group="${group}"]`);
      if (parent) parent.classList.add('on');
      openNavGroup(group);
    }
  }

  const t = { 
    dashboard: 'Dashboard', 
    inventario: 'Inventario', 
    'nuevo-ingreso': 'Ingresos - Nuevo', 
    ingresos: 'Ingresos - Historial', 
    consumos: 'Consumos', 
    sellos: 'Sellos',
    ordenes: 'Ordenes de Trabajo', 
    usuarios: 'Usuarios',
    componentes: 'Componentes',
    paniol: 'Dashboard Pañol',
    auditorias: 'Auditorías - Dashboard',
    'auditorias-sesiones': 'Auditorías - Sesiones',
    'auditorias-abc': 'Auditorías - Clasificación ABC',
    'auditorias-planes': 'Auditorías - Planes'
  };
  $('topbar-t').textContent = legacyHerramientas
    ? 'Pañol - Inventario de Herramientas'
    : (t[targetPage] || targetPage);
  
  // Sincronizar quick nav con la página actual
  document.querySelectorAll('.qn-item').forEach((btn) => btn.classList.remove('active'));
  const quickNavBtn = document.querySelector(`.qn-item[data-page="${targetPage}"]`);
  if (quickNavBtn) quickNavBtn.classList.add('active');
  
  if (targetPage === 'dashboard') {
    if (typeof loadDashboard === 'function') loadDashboard();
    else if (typeof lD === 'function') lD(); // backwards compat
  }
  if (targetPage === 'inventario') lI();
  if (targetPage === 'nuevo-ingreso') {
    openNavGroup('ingresos');
  }
  if (targetPage === 'ingresos') { lIG(); openNavGroup('ingresos'); }
  if (targetPage === 'consumos') lCO();
  if (targetPage === 'sellos' && typeof lSE === 'function') lSE();
  if (targetPage === 'ordenes') lOT();
  if (targetPage === 'usuarios') {
    lEmpleados('usuarios');
    if (typeof loadSystemUsersAdminPanel === 'function') {
      loadSystemUsersAdminPanel();
    }
  }
  if (targetPage === 'componentes') lComp();
  if (targetPage === 'paniol') {
    openNavGroup('paniol');
    const paniolTab = legacyHerramientas ? 'inventario' : 'dashboard';
    // Garantiza que siempre haya una pestaña visible en Pañol
    if (typeof setPaniolRoute === 'function') {
      setPaniolRoute(paniolTab);
    } else if (typeof switchPaniolTab === 'function') {
      switchPaniolTab(paniolTab);
    }
    syncPaniolSidebarTab(paniolTab);
  }
  if (targetPage.startsWith('auditorias')) {
    openNavGroup('auditorias');
    loadAuditoriasPage(targetPage);
  }
  
  // Cerrar sidebar solo en móvil después de navegar
  const sidebar = $('sidebar');
  const overlay = $('sidebar-overlay');
  
  if (window.innerWidth < 768) {
    sidebar.classList.remove('open');
    if (overlay) {
      overlay.classList.remove('active');
    }
  }

  enhanceAccessibility();
}

function applyFeatureToggles() {
  if (AUDITORIAS_ENABLED) return;

  const audNav = $('ni-auditorias');
  const audSubNav = $('snav-auditorias');
  const controlLabel = $('nl-control');

  if (audNav) audNav.style.display = 'none';
  if (audSubNav) audSubNav.style.display = 'none';
  if (controlLabel) controlLabel.style.display = 'none';

  ['p-auditorias', 'p-auditorias-sesiones', 'p-auditorias-abc', 'p-auditorias-planes']
    .forEach((id) => {
      const node = $(id);
      if (node) node.style.display = 'none';
    });
}

window.addEventListener('resize', () => {
  if (resizeRafId !== null) cancelAnimationFrame(resizeRafId);
  resizeRafId = requestAnimationFrame(() => {
    resizeRafId = null;
    applyResponsiveSidebarLayout();
  });
});

refreshSidebarTitles();
applyResponsiveSidebarLayout(true);
applyFeatureToggles();
enhanceAccessibility();

document.addEventListener('keydown', (event) => {
  if (event.key !== 'Enter' && event.key !== ' ') return;
  const target = event.target;
  if (!target || !(target.classList?.contains('ni') || target.classList?.contains('sni'))) return;
  event.preventDefault();
  target.click();
});

let skT;
function skuS(inp, prefix) {
  clearTimeout(skT);
  const q = inp.value.trim();
  const dd = $(prefix + '-dd');
  if (q.length < 1) {
    dd.classList.remove('show');
    return;
  }
  skT = setTimeout(async () => {
    const its = await api('/api/items/search?q=' + encodeURIComponent(q));
    if (!its || !its.length) {
      dd.classList.remove('show');
      return;
    }
    dd.innerHTML = its.map((i) => {
      const sn = (i.nombre || '').replace(/'/g, "\\'").replace(/\"/g, '&quot;');
      const su = (i.unidad || '').replace(/'/g, "\\'");
      return `<div class="sku-o" onclick="skSel('${prefix}','${i.sku}','${sn}',${i.stock},'${su}')"><span><b>${i.sku}</b> - ${i.nombre || '?'}</span><span class="m" style="color:var(--t3)">${i.stock} ${i.unidad || ''}</span></div>`;
    }).join('');
    dd.classList.add('show');
  }, 200);
}

function skSel(pf, sku, nom, stk, uni) {
  const inp = pf === 'ni-add' ? $('ni-asku') : (pf === 'cm-add' ? $('cm-asku') : $('nc-asku'));
  inp.value = sku + ' - ' + nom;
  $(pf + '-v').value = sku;
  $(pf + '-n').value = nom;
  if (pf !== 'cm-add') $(pf + '-u').value = uni;
  $(pf + '-dd').classList.remove('show');
  if (pf === 'ni-add') {
    $('ni-info').innerHTML = `<span style="color:var(--in)">Stock actual: ${stk} ${uni}</span>`;
    $('ni-aq').focus();
  }
  if (pf === 'nc-add') {
    $(pf + '-st').value = stk;
    $('nc-info').innerHTML = `<span style="color:var(--in)">Stock disponible: ${stk} ${uni}</span>`;
    $('nc-aq').focus();
  }
  if (pf === 'cm-add') {
    $('cm-info').innerHTML = `<span style="color:var(--in)">${nom} (${uni})</span>`;
    $('cm-aq').focus();
  }
}

document.addEventListener('click', (e) => {
  if (!e.target.closest('.sku-w')) {
    document.querySelectorAll('.sku-dd').forEach((d) => d.classList.remove('show'));
  }
});

document.addEventListener('keydown', (e) => {
  if (e.key !== 'Escape') return;
  if ($('m-confirm') && $('m-confirm').classList.contains('on')) closeConfirmModal(false);
  else if ($('m-text-prompt') && $('m-text-prompt').classList.contains('on')) closeTextPromptModal(null);
  else if ($('m-ing') && $('m-ing').classList.contains('on') && typeof closeIng === 'function') closeIng();
  else if ($('m-con-edit') && $('m-con-edit').classList.contains('on') && typeof closeConsumoEdit === 'function') closeConsumoEdit();
  else if ($('m-con') && $('m-con').classList.contains('on') && typeof closeCon === 'function') closeCon();
  else if ($('m-item') && $('m-item').classList.contains('on') && typeof closeItemModal === 'function') closeItemModal();
  else if ($('m-item') && $('m-item').classList.contains('on')) cM('m-item');
  else if ($('m-ot') && $('m-ot').classList.contains('on')) cM('m-ot');
  else if ($('m-comp') && $('m-comp').classList.contains('on')) cM('m-comp');
  else if ($('m-comp-mat') && $('m-comp-mat').classList.contains('on')) cM('m-comp-mat');
  else if ($('m-stock-analysis') && $('m-stock-analysis').classList.contains('on')) cM('m-stock-analysis');
  else if ($('m-kardex') && $('m-kardex').classList.contains('on')) cM('m-kardex');
  else if ($('ficha-ov') && $('ficha-ov').classList.contains('on') && typeof closeFicha === 'function') closeFicha();
});

document.addEventListener('keydown', (e) => {
  if (e.key !== 'Enter') return;
  if ($('m-confirm') && $('m-confirm').classList.contains('on')) {
    if (document.activeElement?.id !== 'm-confirm-cancel') {
      e.preventDefault();
      closeConfirmModal(true);
    }
  }
  if ($('m-text-prompt') && $('m-text-prompt').classList.contains('on') && document.activeElement?.id === 'm-text-prompt-input') {
    e.preventDefault();
    acceptTextPromptModal();
  }
});