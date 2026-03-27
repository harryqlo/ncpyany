// ======================================
// PAÑOL - Sistema de Control de Herramientas
// Version 2 - Refactorizado y Profesional
// ======================================

// Estados de paginación
let empS = { p: 1 };
let herrS = { p: 1 };
let checkoutItems = [];
let chartTopEmpleados, chartTopHerramientas, chartCostosMant;
let mantenimientoRecepcionSeleccionada = null;
let envioMantenimientoSeleccionado = null;
let mantenimientoRecepcionIds = new Set();
let paniolRequestedTab = null;

// estado simplificado para las nuevas pestañas "entrega" y "devolucion"
const SimpleState = {
  entrega: { usuario: null, herramientas: [] },
  devolucion: { usuario: null, prestamos: [] }
};

// las vistas que maneja el módulo
const PANIOL_VIEWS = ['dashboard', 'entrega', 'devolucion', 'inventario', 'historial', 'mantenimiento'];

function isPaniolPageActive() {
  const page = document.getElementById('p-paniol');
  return !!(page && page.classList.contains('on') && !document.hidden);
}

function isPaniolPanelActive(tab) {
  const panel = document.getElementById('paniol-panel-' + tab);
  return !!(panel && panel.classList.contains('on'));
}

const _paniolRenderJobs = new Map();

function renderTableInChunks(tbodyId, rows, renderRow, options = {}) {
  const body = document.getElementById(tbodyId);
  if (!body) return;

  const emptyHtml = options.emptyHtml || '<tr><td colspan="1" style="text-align:center;padding:16px;color:var(--t3)">Sin datos</td></tr>';
  const batchSize = options.batchSize || 25;
  const nextJobId = (_paniolRenderJobs.get(tbodyId) || 0) + 1;
  _paniolRenderJobs.set(tbodyId, nextJobId);

  if (!rows || rows.length === 0) {
    body.innerHTML = emptyHtml;
    return;
  }

  body.innerHTML = '';
  let currentIndex = 0;

  const renderBatch = () => {
    if (_paniolRenderJobs.get(tbodyId) !== nextJobId) return;

    const endIndex = Math.min(currentIndex + batchSize, rows.length);
    const htmlChunk = rows.slice(currentIndex, endIndex).map(renderRow).join('');
    body.insertAdjacentHTML('beforeend', htmlChunk);
    currentIndex = endIndex;

    if (currentIndex < rows.length) {
      setTimeout(renderBatch, 0);
    }
  };

  renderBatch();
}

// ======================================
// NOTIFICACIONES PROFESIONALES - PAÑOL
// ======================================

/**
 * Mostrar notificación de feedback profesional en pañol
 * @param {string} message - Mensaje a mostrar
 * @param {string} type - Tipo: 'ok'|'err'|'warn'|'info'
 * @param {number} duration - Duración en ms (def: 3000)
 */
function showPaniolFeedback(message, type = 'info', duration = 3000) {
  const container = document.getElementById('paniol-feedback-container');
  if (!container) return;
  
  const feedback = document.createElement('div');
  feedback.className = `paniol-feedback feedback-${type}`;
  feedback.style.cssText = `
    padding: 14px 16px;
    margin-bottom: 12px;
    border-radius: 6px;
    font-size: 13px;
    line-height: 1.5;
    border-left: 4px solid;
    display: flex;
    align-items: flex-start;
    gap: 10px;
    animation: slideInDown 0.3s ease-out;
  `;
  
  // Estilos por tipo
  if (type === 'ok') {
    feedback.style.backgroundColor = 'var(--okd)';
    feedback.style.borderColor = 'var(--ok)';
    feedback.style.color = 'var(--ok)';
  } else if (type === 'err') {
    feedback.style.backgroundColor = 'var(--nod)';
    feedback.style.borderColor = 'var(--no)';
    feedback.style.color = 'var(--no)';
  } else if (type === 'warn') {
    feedback.style.backgroundColor = 'var(--wad)';
    feedback.style.borderColor = 'var(--wa)';
    feedback.style.color = 'var(--wa)';
  } else {
    // info
    feedback.style.backgroundColor = 'var(--acd)';
    feedback.style.borderColor = 'var(--ac)';
    feedback.style.color = 'var(--ac)';
  }
  
  // Contenido con saltos de línea
  const lines = message.split('\n');
  feedback.innerHTML = lines.map(line => `<div>${line}</div>`).join('');
  
  container.insertBefore(feedback, container.firstChild);
  
  // Auto-remover después de duration
  setTimeout(() => {
    feedback.style.animation = 'slideOutUp 0.3s ease-out forwards';
    setTimeout(() => feedback.remove(), 300);
  }, duration);
}

// ======================================
// DASHBOARD PAÑOL
// ======================================

async function loadPaniolDashboard() {
  await loadPaniolKPIs();
  // Solo cambiar a dashboard si no hay un tab específico ya solicitado
  if (!paniolRequestedTab || paniolRequestedTab === 'dashboard') {
    switchPaniolTab('dashboard');
  }
}

function setPaniolRoute(tab) {
  paniolRequestedTab = PANIOL_VIEWS.includes(tab) ? tab : 'dashboard';
  switchPaniolTab(paniolRequestedTab);
}

async function loadPaniolKPIs() {
  const d = await api('/api/herramientas/stats');
  if (!d) return;

  const setIfExists = (id, val) => {
    const el = document.getElementById(id);
    if (el) el.textContent = val;
  };

  // Actualizar KPIs en Dashboard
  setIfExists('kpi-total', d.total_herramientas || 0);
  setIfExists('kpi-prestadas', d.prestamos_activos || 0);
  setIfExists('kpi-mantenimiento', d.en_mantenimiento || 0);
  setIfExists('kpi-defectuosas', d.defectuosas || 0);
  
  // KPIs adicionales para versiones anteriores; quedan comentados
  // setIfExists('kpi-total-meson', d.total_herramientas || 0);
  // setIfExists('kpi-prestadas-meson', d.prestamos_activos || 0);
  // setIfExists('kpi-mantenimiento-meson', d.en_mantenimiento || 0);
  // setIfExists('kpi-defectuosas-meson', d.defectuosas || 0);
  
  setIfExists('kpi-mant-vencidos', d.mantenimientos_vencidos || 0);
  setIfExists('kpi-calib-vencidas', d.calibraciones_vencidas || 0);
}

function switchPaniolTab(tab) {
  const safeTab = PANIOL_VIEWS.includes(tab) ? tab : 'dashboard';
  paniolRequestedTab = safeTab;

  // actualizar fecha de devolucion por default cuando exista
  if (typeof PaniolState !== 'undefined' && PaniolState && PaniolState.devolución) {
    PaniolState.devolución.fecha = new Date().toISOString().split('T')[0];
  }
  
  // mostrar el panel correspondiente
  document.querySelectorAll('#p-paniol .paniol-panel').forEach(p => p.classList.remove('on'));
  const panel = document.getElementById('paniol-panel-' + safeTab);
  if (panel) panel.classList.add('on');

  const dashboardShell = document.getElementById('paniol-dashboard-shell');
  if (dashboardShell) {
    dashboardShell.style.display = safeTab === 'dashboard' ? '' : 'none';
  }

  if (typeof syncPaniolSidebarTab === 'function') {
    syncPaniolSidebarTab(safeTab);
  }
  
  // cargar datos según tab simplificado
  try {
    switch(safeTab) {
      case 'entrega': loadEntregaTab(); break;
      case 'devolucion': loadDevolucionTab(); break;
      case 'inventario': loadInventarioTab(); break;
      case 'historial': loadHistorialTab(); break;
      case 'mantenimiento': loadMantenimientoTab(); break;
      case 'dashboard': /* ya cargado en setPaniolRoute */ break;
    }
  } catch (err) {
    console.error('Error cargando pestaña de pañol:', safeTab, err);
    if (typeof showPaniolFeedback === 'function') {
      showPaniolFeedback(`❌ Error cargando pestaña ${safeTab}. Revise consola para detalle.`, 'err', 5000);
    }
  }
}

/*
// ======================================
// TAB - MESÓN (Préstamos Activos)   <--- código legado, ocultado
// ======================================

async function loadMesonTab() {
  const prestamos = await PaniolAPI.getPrestamosActivos();
  const search = (document.getElementById('paniol-meson-search')?.value || '').trim().toLowerCase();
  
  const rows = prestamos.filter(p => {
    if (!search) return true;
    return `${p.herramienta_nombre} ${p.herramienta_sku} ${p.empleado_nombre}`.toLowerCase().includes(search);
  });
  
  PaniolUI.renderPrestamos(rows, 'paniol-prestamos-body');
  
  // Cargar devoluciones recientes
  const historial = await PaniolAPI.getHistorial(1, 5);
  const devols = (historial && historial.movimientos)
    ? historial.movimientos.filter(m => m.fecha_retorno).slice(0, 5)
    : [];
  
  const lastReturnsEl = document.getElementById('paniol-last-returns');
  if (lastReturnsEl) {
    lastReturnsEl.innerHTML = devols.length === 0
      ? 'Sin devoluciones recientes.'
      : devols.map(m => `<div style="padding:6px 0;border-bottom:1px solid var(--bd)"><strong>${m.herramienta_nombre}</strong><div class="m" style="font-size:10px;color:var(--t3)">${m.empleado_nombre} · ${m.fecha_retorno}</div></div>`).join('');
  }
}

// ======================================
// TAB - DEVOLUCIONES
// ======================================

async function loadDevolucionesTab() {
  const prestamos = await PaniolAPI.getPrestamosActivos();
  const search = (document.getElementById('paniol-devol-search')?.value || '').trim().toLowerCase();
  
  const fechaEl = document.getElementById('paniol-devol-fecha');
  if (fechaEl && !fechaEl.value) {
    fechaEl.value = new Date().toISOString().split('T')[0];
  }
  
  const rows = prestamos.filter(p => {
    if (!search) return true;
    return `${p.empleado_nombre} ${p.herramienta_nombre} ${p.herramienta_sku}`.toLowerCase().includes(search);
  });
  
  PaniolUI.renderDevolucionesLista(rows, 'paniol-devol-list');
}

/* legacy helper - ya no se utiliza en la interfaz simplificada
function selectPaniolDevolucion(movId) {
  const prestamo = PaniolState.prestamosCache.find(p => p.id === movId);
  if (!prestamo) return;
  
  PaniolState.devolución.seleccionada = prestamo;
  PaniolUI.renderDevolucionDetalle(prestamo);
  const btn = document.getElementById('paniol-devol-confirm');
  if (btn) btn.textContent = 'Confirmar (1)';
  
  // Re-render lista
  loadDevolucionesTab();
}

async function confirmDevolucionSeleccionada() {
  if (!PaniolState.devolución.seleccionada) {
    return toast('Selecciona un préstamo', 'err');
  }

  const p = PaniolState.devolución.seleccionada;
  const cantidadInput = document.getElementById('paniol-devol-cantidad');
  const cantidad = cantidadInput ? parseInt(cantidadInput.value, 10) : null;

  const result = await PaniolAPI.checkin(
    p.id,
    document.getElementById('paniol-devol-estado')?.value || 'operativa',
    document.getElementById('paniol-devol-obs')?.value || '',
    {
      cantidad: cantidad,
      fecha: document.getElementById('paniol-devol-fecha')?.value
    }
  );

  if (result && result.ok) {
    toast(result.msg || 'Devolución registrada');
    PaniolState.reset();
    document.getElementById('paniol-devol-obs').value = '';
    document.getElementById('paniol-devol-confirm').textContent = 'Confirmar (0)';
    document.getElementById('paniol-devol-selected').innerHTML = 'Selecciona un préstamo.';
    await Promise.all([
      loadPaniolKPIs(),
      loadDevolucionesTab(),
      loadMesonTab()
    ]);
  } else if (result) {
    toast(result.msg || 'Error', 'err');
  }
}
*/


// --------------------------------------
// FLUJOS SIMPLIFICADOS DE ENTREGA/DEVOLUCIÓN
// --------------------------------------

// nota: algunos helpers como lEmpleados se reutilizan más abajo

async function loadEntregaTab() {
  // cargar usuarios para dropdown y lista de herramientas
  await Promise.all([loadUsersForContext('entrega'), searchEntregaHerramientas()]);
  renderEntregaCarrito();
  const dateEl = document.getElementById('entrega-date');
  if (dateEl && !dateEl.value) dateEl.value = new Date().toISOString().split('T')[0];
  updateEntregaSummaryState();
}

function onEntregaToolSearchInput() {
  dbSearch('paniol-entrega-tools', searchEntregaHerramientas, 320);
}


function selectEntregaUsuario(id,nombre,numero) {
  SimpleState.entrega.usuario = { id, nombre, numero };
  SimpleState.entrega.herramientas = [];
  renderEntregaCarrito();
  searchEntregaHerramientas();
  updateEntregaSummaryState();
}


function selectDevolucionUsuario(id,nombre,numero) {
  SimpleState.devolucion.usuario = { id, nombre, numero };
  SimpleState.devolucion.prestamos = [];
  renderDevolucionCarrito();
  searchDevolucionHerramientas();
  updateDevolucionSummaryState();
}

async function searchEntregaHerramientas() {
  if (!isPaniolPageActive() || !isPaniolPanelActive('entrega')) return;
  const body = document.getElementById('entrega-tool-results');
  if (!body) return;
  const userSelect = document.getElementById('entrega-user-select');

  // Si el select tiene valor pero el estado aún no se sincronizó, sincronizarlo.
  if (!SimpleState.entrega.usuario && userSelect && userSelect.value) {
    selectEntregaUsuarioFromDropdown(userSelect.value);
  }
  
  // Validar que se haya seleccionado usuario PRIMERO
  if (!SimpleState.entrega.usuario) {
    body.innerHTML = '<tr><td colspan="5" style="text-align:center;color:var(--wa);padding:24px;font-weight:600">⚠️ Seleccione un usuario primero para buscar herramientas.</td></tr>';
    return;
  }
  
  const q = document.getElementById('entrega-tool-search').value.trim();
  const resp = await api('/api/herramientas?per_page=50&page=1&search=' + encodeURIComponent(q));
  const list = (resp && resp.herramientas) ? resp.herramientas : [];
  const cartIds = new Set(SimpleState.entrega.herramientas.map(h=>String(h.id)));
  const available = list.filter(h => !cartIds.has(String(h.id)));
  body.innerHTML = available.length === 0
    ? '<tr><td colspan="5" style="text-align:center;color:var(--t3);padding:24px">No hay herramientas disponibles.</td></tr>'
    : available.map(h => {
      const entregable = h.condicion === 'operativa' && (h.cantidad_disponible || 0) > 0;
      const rowStyle = entregable ? '' : 'opacity:0.5;color:var(--t3);cursor:not-allowed';
      const reason = h.condicion !== 'operativa' ? `No operativa (${h.condicion})` : (h.cantidad_disponible <= 0 ? 'Sin disponibilidad' : '');
      const safeName = (h.nombre || '').replace(/"/g, '&quot;');
      const safeReason = (reason || '').replace(/"/g, '&quot;');
      return `<tr data-id="${h.id}" data-nombre="${safeName}" data-entregable="${entregable}" data-reason="${safeReason}" style="${rowStyle}">
        <td>${h.sku}</td><td>${h.nombre}</td><td><span class="badge-condicion ${h.condicion}">${h.condicion}</span></td><td>${h.cantidad_disponible||0}</td><td style="text-align:center;font-size:12px;color:var(--ac)">${entregable ? '✓' : '✕'}</td>
      </tr>`;
    }).join('');

  body.querySelectorAll('tr[data-id]').forEach(tr => {
    tr.addEventListener('click', () => {
      if (tr.dataset.entregable === 'true') {
        addEntregaHerramienta(tr.dataset.id, tr.dataset.nombre || '');
      } else {
        showBlockReason(tr);
      }
    });
  });
}

function addEntregaHerramienta(id, nombre) {
  // Prevenir stackeo: no permitir duplicados de la misma herramienta
  if (SimpleState.entrega.herramientas.find(h=>String(h.id)===String(id))) {
    showPaniolFeedback('⚠️ Estado: Esta herramienta ya está en el carrito', 'warn');
    return;
  }
  
  SimpleState.entrega.herramientas.push({id, nombre, observacion:''});
  showPaniolFeedback(`✓ ${nombre} agregada al carrito`, 'ok');
  renderEntregaCarrito();
  searchEntregaHerramientas();
}

function showBlockReason(element) {
  const reason = element.dataset.reason || 'No disponible';
  const name = element.dataset.nombre || 'Herramienta';
  const icon = '🚫';
  showPaniolFeedback(`${icon} ${name}: ${reason}`, 'err');
}

function renderEntregaCarrito() {
  const body = document.getElementById('entrega-cart-body');
  if (!body) return;
  if (SimpleState.entrega.herramientas.length === 0) {
    body.innerHTML = '<tr><td colspan="4" style="text-align:center;color:var(--t3)">No hay herramientas agregadas.</td></tr>';
  } else {
    body.innerHTML = SimpleState.entrega.herramientas.map(h =>
      `<tr>
        <td>${h.id}</td>
        <td>${h.nombre}</td>
        <td><input class="flt" placeholder="Observacion por herramienta" value="${(h.observacion || '').replace(/"/g, '&quot;')}" oninput="updateEntregaItemObs(${h.id}, this.value)"></td>
        <td><button onclick="removeEntregaHerramienta(${h.id})">✕</button></td>
      </tr>`
    ).join('');
  }
  updateEntregaSummaryState();
}

function removeEntregaHerramienta(id) {
  SimpleState.entrega.herramientas = SimpleState.entrega.herramientas.filter(h => String(h.id) !== String(id));
  renderEntregaCarrito();
  searchEntregaHerramientas();
}

function updateEntregaItemObs(id, obs) {
  const item = SimpleState.entrega.herramientas.find(h => String(h.id) === String(id));
  if (item) item.observacion = obs;
}

function updateEntregaSummaryState() {
  const count = SimpleState.entrega.herramientas.length;
  const badge = document.getElementById('entrega-count-badge');
  const note = document.getElementById('entrega-summary-note');
  const confirmBtn = document.getElementById('entrega-confirm-btn');
  const userName = SimpleState.entrega.usuario?.nombre || 'sin responsable';

  if (badge) {
    badge.textContent = `${count} ${count === 1 ? 'item' : 'items'}`;
  }

  if (note) {
    note.textContent = count === 0
      ? 'Seleccione al menos una herramienta para proceder con el registro.'
      : `Responsable: ${userName}. Listo para confirmar la salida.`;
  }

  if (confirmBtn) {
    confirmBtn.disabled = !(SimpleState.entrega.usuario && count > 0);
  }
}

async function confirmEntrega() {
  // Validaciones profesionales pre-submit
  if (!SimpleState.entrega.usuario) {
    showPaniolFeedback('❌ Debe seleccionar un usuario para proceder', 'err');
    return;
  }
  
  if (SimpleState.entrega.herramientas.length === 0) {
    showPaniolFeedback('❌ Agregue al menos una herramienta al carrito', 'err');
    return;
  }
  
  const fecha = document.getElementById('entrega-date')?.value;
  if (!fecha) {
    showPaniolFeedback('❌ Debe establecer una fecha de entrega', 'err');
    return;
  }
  
  // Mostrar indicador de procesamiento
  const btn = document.getElementById('entrega-confirm-btn');
  if (btn) btn.disabled = true;
  
  showPaniolFeedback('⏳ Procesando entrega...', 'info');
  
  const resp = await api('/api/herramientas/checkout', {
    method:'POST',
    headers:{'Content-Type':'application/json'},
    body: JSON.stringify({
      empleado_id: SimpleState.entrega.usuario.id,
      herramientas: SimpleState.entrega.herramientas.map(h => ({
        herramienta_id: parseInt(h.id, 10),
        cantidad: 1,
        observaciones: h.observacion || ''
      })),
      fecha_salida: fecha
    })
  });
  
  if (resp && resp.ok) {
    showPaniolFeedback(`✓ Entrega registrada exitosamente - ${SimpleState.entrega.herramientas.length} herramienta(s)`, 'ok');
    SimpleState.entrega.usuario = null;
    SimpleState.entrega.herramientas = [];
    const sel = document.getElementById('entrega-user-select');
    if (sel) sel.value = '';
    await Promise.all([loadPaniolKPIs(), loadEntregaTab()]);
  } else if (resp?.errores && resp.errores.length > 0) {
    // Mostrar errores específicos de validación del backend
    const errorList = resp.errores.map((e, i) => `${i+1}. ${e}`).join('\n');
    showPaniolFeedback(`⚠️ Errores en validación:\n${errorList}`, 'err', 5000);
    if (btn) btn.disabled = false;
  } else if (resp) {
    showPaniolFeedback(`❌ ${resp.msg || 'Error desconocido'}`, 'err');
    if (btn) btn.disabled = false;
  }
  
  if (btn) btn.disabled = false;
}

async function loadDevolucionTab() {
  if (!isPaniolPageActive() || !isPaniolPanelActive('devolucion')) return;
  await Promise.all([loadUsersForContext('devolucion'), searchDevolucionHerramientas()]);
  renderDevolucionCarrito();
  const dateEl = document.getElementById('devolucion-date');
  if (dateEl && !dateEl.value) dateEl.value = new Date().toISOString().split('T')[0];
  updateDevolucionSummaryState();
}

function onDevolucionToolSearchInput() {
  dbSearch('paniol-devol-tools', searchDevolucionHerramientas, 320);
}

async function loadUsuariosUnifiedTab() {
  await lEmpleados('usuarios');
}

function searchPaniolUsers() {
  empS.p = 1;
  lEmpleados('usuarios');
}


async function searchDevolucionHerramientas() {
  if (!isPaniolPageActive() || !isPaniolPanelActive('devolucion')) return;
  const selectedUser = SimpleState.devolucion.usuario;
  const q = document.getElementById('devol-tool-search').value.trim().toLowerCase();
  const body = document.getElementById('devol-tool-results');
  if (!body) return;
  if (!selectedUser) {
    body.innerHTML = '<tr><td colspan="3" style="text-align:center;color:var(--t3);padding:24px">Seleccione un usuario para ver sus herramientas a cargo.</td></tr>';
    return;
  }

  const prestamos = await PaniolAPI.getPrestamosActivos();
  const userLoans = prestamos.filter(p =>
    String(p.empleado_id || '') === String(selectedUser.id || '') ||
    (selectedUser.nombre && String(p.empleado_nombre || '') === String(selectedUser.nombre))
  );

  const list = userLoans.filter(p => `${p.herramienta_nombre} ${p.herramienta_sku}`.toLowerCase().includes(q));
  const cartIds = new Set(SimpleState.devolucion.prestamos.map(h=>String(h.id)));
  const available = list.filter(p => !cartIds.has(String(p.id)));
  body.innerHTML = available.length === 0
    ? '<tr><td colspan="3" style="text-align:center;color:var(--t3);padding:24px">No hay prestamos disponibles para este usuario.</td></tr>'
    : available.map(p => {
      return `<tr data-id="${p.id}" data-nombre="${p.herramienta_nombre.replace(/'/g,"\\'")}">
        <td>${p.herramienta_sku}</td><td>${p.herramienta_nombre}</td><td>${p.empleado_nombre}</td>
      </tr>`;
    }).join('');
  body.querySelectorAll('tr').forEach(tr => {
    tr.addEventListener('click', () => {
      if (!tr.dataset.id) return;
      addDevolucionHerramienta(tr.dataset.id, tr.dataset.nombre);
    });
  });
}

function addDevolucionHerramienta(id,nombre) {
  if (!SimpleState.devolucion.prestamos.find(h=>String(h.id)===String(id))) {
    SimpleState.devolucion.prestamos.push({id,nombre,observacion:''});
  }
  renderDevolucionCarrito();
  searchDevolucionHerramientas();
}

function renderDevolucionCarrito() {
  const body = document.getElementById('devol-cart-body');
  if (!body) return;
  if (SimpleState.devolucion.prestamos.length === 0) {
    body.innerHTML = '<tr><td colspan="3" style="text-align:center;color:var(--t3)">No hay préstamos seleccionados.</td></tr>';
  } else {
    body.innerHTML = SimpleState.devolucion.prestamos.map(h =>
      `<tr><td>${h.id}</td><td>${h.nombre}</td><td><button onclick="removeDevolucionHerramienta(${h.id})">✕</button></td></tr>`
    ).join('');
  }
  updateDevolucionSummaryState();
}

function removeDevolucionHerramienta(id) {
  SimpleState.devolucion.prestamos = SimpleState.devolucion.prestamos.filter(h => String(h.id) !== String(id));
  renderDevolucionCarrito();
  searchDevolucionHerramientas();
}

function updateDevolucionSummaryState() {
  const count = SimpleState.devolucion.prestamos.length;
  const badge = document.getElementById('devol-count-badge');
  const note = document.getElementById('devol-summary-note');
  const confirmBtn = document.getElementById('devol-confirm-btn');
  const userName = SimpleState.devolucion.usuario?.nombre || 'sin responsable';

  if (badge) {
    badge.textContent = `${count} ${count === 1 ? 'item' : 'items'}`;
  }
  if (note) {
    note.textContent = count === 0
      ? 'Seleccione al menos una herramienta para registrar la devolucion.'
      : `Responsable: ${userName}. Puede dejar observacion por cada herramienta.`;
  }
  if (confirmBtn) {
    confirmBtn.disabled = !(SimpleState.devolucion.usuario && count > 0);
  }
}

async function confirmDevolucion() {
  // Validaciones profesionales
  if (!SimpleState.devolucion.usuario) {
    showPaniolFeedback('❌ Debe seleccionar un usuario para proceder', 'err');
    return;
  }
  
  if (SimpleState.devolucion.prestamos.length === 0) {
    showPaniolFeedback('❌ Agregue al menos un préstamo al carrito', 'err');
    return;
  }
  
  const fecha = document.getElementById('devolucion-date')?.value;
  if (!fecha) {
    showPaniolFeedback('❌ Debe establecer una fecha de devolución', 'err');
    return;
  }
  
  const btn = document.getElementById('devol-confirm-btn');
  if (btn) btn.disabled = true;
  
  showPaniolFeedback('⏳ Procesando devolución...', 'info');
  
  const obsGeneral = document.getElementById('devolucion-obs')?.value || '';
  const r = await api('/api/herramientas/checkin', {
    method:'POST',
    headers:{'Content-Type':'application/json'},
    body: JSON.stringify({
      devoluciones: SimpleState.devolucion.prestamos.map(p => ({
        movimiento_id: p.id,
        estado_retorno: 'operativa',
        observaciones_retorno: (p.observacion || obsGeneral || '').trim(),
        fecha_retorno: fecha
      }))
    })
  });
  
  if (r && r.ok) {
    showPaniolFeedback(`✓ Devolución registrada exitosamente - ${SimpleState.devolucion.prestamos.length} herramienta(s)`, 'ok');
    SimpleState.devolucion.usuario = null;
    SimpleState.devolucion.prestamos = [];
    const sel = document.getElementById('devolucion-user-select');
    if (sel) sel.value = '';
    await Promise.all([loadPaniolKPIs(), loadDevolucionTab()]);
  } else if (r) {
    showPaniolFeedback(`❌ ${r.msg || 'Error desconocido'}`, 'err');
    if (btn) btn.disabled = false;
  }
  
  if (btn) btn.disabled = false;
}

// ======================================
// TAB - INVENTARIO
// ======================================

async function loadInventarioTab() {
  if (!isPaniolPageActive() || !isPaniolPanelActive('inventario')) return;
  const search = (document.getElementById('paniol-inv-search')?.value || '').trim();
  const d = await api('/api/herramientas?per_page=100&page=1&search=' + encodeURIComponent(search));
  const rows = (d && d.herramientas) ? d.herramientas : [];

  const container = document.getElementById('paniol-inv-body');
  if (!container) return;

  renderTableInChunks('paniol-inv-body', rows, (h) => {
    let cls, label;
    if (h.condicion === 'mantenimiento') { cls = 'mantenimiento'; label = 'MANTENCIÓN'; }
    else if (h.condicion === 'defectuosa')  { cls = 'defectuosa';   label = 'DAÑADA'; }
    else if (h.condicion === 'baja')        { cls = 'baja';         label = 'BAJA'; }
    else if ((h.cantidad_disponible || 0) > 0) { cls = 'operativa'; label = 'DISPONIBLE'; }
    else                                    { cls = 'en-uso';       label = 'EN USO'; }
    const safeNombre = (h.nombre || '')
      .replace(/'/g, "\\'")
      .replace(/"/g, '&quot;');
    const safeSku = (h.sku || '').replace(/"/g, '&quot;');
    return `<tr>
      <td class="m" style="font-weight:700;font-size:11px;color:var(--ac)">${h.sku}</td>
      <td style="font-weight:600">${h.nombre}</td>
      <td>${h.categoria || '-'}</td>
      <td><span class="badge-condicion ${cls}">${label}</span></td>
      <td style="text-align:center;font-weight:600">${h.cantidad_disponible ?? 0}<span style="color:var(--t3);font-weight:400">/${h.cantidad_total ?? 1}</span></td>
      <td>
        <div style="display:flex;gap:3px">
          <button class="bi" onclick="viewKardexHerramienta(${h.id},'${safeNombre}','${safeSku}')" title="Ver Kardex">👁</button>
          <button class="bi bi-ok" onclick="openMantenimiento(${h.id},'${safeNombre}','${safeSku}')" title="Registrar mantenimiento">🔧</button>
          <button class="bi bi-ac" onclick="editHerramienta(${h.id})" title="Editar">✎</button>
          <button class="bi bi-no" onclick="deleteHerramienta(${h.id})" title="Eliminar">✕</button>
        </div>
      </td>
    </tr>`;
  }, {
    batchSize: 30,
    emptyHtml: '<tr><td colspan="6" style="text-align:center;padding:24px;color:var(--t3)">Sin herramientas registradas.</td></tr>'
  });
}

// ======================================
// TAB - HISTORIAL
// ======================================

async function loadHistorialTab() {
  if (!isPaniolPageActive() || !isPaniolPanelActive('historial')) return;
  const d = await PaniolAPI.getHistorial(1, 100);
  const rows = (d && d.movimientos) ? d.movimientos : [];

  renderTableInChunks('paniol-hist-body', rows, (m) => `
      <tr>
        <td><div style="font-weight:600">${m.herramienta_nombre}</div><div class="m" style="font-size:10px;color:var(--t3)">${m.herramienta_sku || '-'}</div></td>
        <td>${m.empleado_nombre || '-'}</td>
        <td>${m.fecha_salida || '-'}</td>
        <td>${m.fecha_retorno || '-'}</td>
        <td><span class="badge-condicion ${m.fecha_retorno ? 'operativa' : 'mantenimiento'}">${m.fecha_retorno ? 'CERRADO' : 'ACTIVO'}</span></td>
      </tr>
    `, {
    batchSize: 35,
    emptyHtml: '<tr><td colspan="5" style="text-align:center;padding:24px;color:var(--t3)">Sin historial.</td></tr>'
  });
}

// ======================================
// TAB - MOVIMIENTOS / DEVOLUCIONES (antes "Usuarios")
// ======================================

async function loadMovimientosTab() {
  // Actualmente reutilizamos la pantalla de devoluciones, pero centralizamos
  // el concepto aquí. Guardamos el último préstamo seleccionado en el nuevo
  // campo de estado por si hay que añadir comportamiento adicional.
  await loadDevolucionesTab();
  PaniolState.movimientos.seleccionada = PaniolState.devolución.seleccionada;
}

// mantenemos la función anterior por compatibilidad interna aunque ya no se expone
async function loadUsuariosCargoTab() {
  const search = (document.getElementById('paniol-user-search')?.value || '').trim();
  const data = await PaniolAPI.getPrestamosPorUsuario(search);
  const usuarios = (data && data.usuarios) ? data.usuarios : [];

  PaniolUI.renderUsuariosCargoLista(usuarios, 'paniol-user-list');

  const currentKey = PaniolState.usuariosCargo.seleccionada?.key;
  let selected = null;

  if (currentKey) {
    selected = usuarios.find(u => PaniolUI._usuarioKey(u) === currentKey) || null;
  }

  if (!selected && usuarios.length > 0) {
    selected = usuarios[0];
  }

  PaniolState.usuariosCargo.seleccionada = selected
    ? { key: PaniolUI._usuarioKey(selected) }
    : null;

  PaniolUI.renderUsuarioCargoDetalle(selected, 'paniol-user-summary', 'paniol-user-tools-body');
}

function selectPaniolUsuarioCargo(usuarioKey) {
  PaniolState.usuariosCargo.seleccionada = { key: usuarioKey };
  loadUsuariosCargoTab();
}

async function openDevolucionDesdeUsuario(movimientoId) {
  const prestamos = await PaniolAPI.getPrestamosActivos();
  const prestamo = prestamos.find(item => item.id === movimientoId || item.movimiento_id === movimientoId);
  if (!prestamo) return toast('No se encontró el préstamo activo', 'err');

  PaniolState.devolución.seleccionada = prestamo;
  PaniolUI.renderDevolucionDetalle(prestamo);
  const btn = document.getElementById('paniol-devol-confirm');
  if (btn) btn.textContent = 'Confirmar (1)';

  switchPaniolTab('devolucion');
}

// ======================================
// TAB - MANTENIMIENTO (simplificado)
// reemplazo del flujo anterior comentado por nuevo modo tabla
// ======================================

async function loadMantenimientoTab() {
  if (!isPaniolPageActive() || !isPaniolPanelActive('mantenimiento')) return;
  const search = (document.getElementById('paniol-mant-search')?.value || '').trim().toLowerCase();
  const d = await api('/api/herramientas?per_page=100&page=1&search=' + encodeURIComponent(search));
  const rows = (d && d.herramientas) ? d.herramientas : [];
  const body = document.getElementById('paniol-mant-list');
  const confirmBtn = document.getElementById('paniol-mant-confirm');
  if (!body) return;

  const currentIds = new Set(rows.map((h) => h.id));
  mantenimientoRecepcionIds = new Set(
    [...mantenimientoRecepcionIds].filter((id) => currentIds.has(id))
  );

  renderTableInChunks('paniol-mant-list', rows, (h) => {
    const estado = h.condicion || 'operativa';
    const canReceive = estado === 'mantenimiento';
    const isChecked = canReceive && mantenimientoRecepcionIds.has(h.id);
    const editIcon = IconUtils.createSvgIcon('edit', { 
      size: 'sm', 
      className: 'icon-action edit',
      ariaHidden: true
    });
    return `<tr>
      <td><span class="mant-sku">${h.sku}</span></td>
      <td>${h.nombre}</td>
      <td><select class="mant-estado-sel" onchange="changeEstadoMant(${h.id},this.value)">${estadoOptions(estado)}</select></td>
      <td style="text-align:center">
        <div style="display:flex;align-items:center;justify-content:center;gap:8px">
          <label style="display:inline-flex;align-items:center;gap:4px;cursor:${canReceive ? 'pointer' : 'not-allowed'};opacity:${canReceive ? '1' : '.45'}" title="Seleccionar para recibir y habilitar">
            <input type="checkbox" ${isChecked ? 'checked' : ''} ${canReceive ? '' : 'disabled'} onchange="toggleMantenimientoRecepcion(${h.id}, this.checked)">
            <span style="font-size:10px;color:var(--t3)">Recibir</span>
          </label>
          <button class="btn-mant-info" title="Registrar información" onclick="openMantInfo(${h.id},'${(h.nombre || '').replace(/'/g,"\\'").replace(/"/g, '&quot;')}')">
            ${editIcon}
          </button>
        </div>
      </td>
         <td style="text-align:center;font-size:11px">
           <div style="display:flex;gap:4px;justify-content:center">
             <button class="btn bsm bp" onclick="abrirFormularioMantenimiento(${h.id},'${(h.nombre || '').replace(/'/g,"\\'").replace(/"/g,'&quot;')}')" title="Formulario profesional">📋</button>
             <button class="btn bsm bg" onclick="mostrarHistorialMantenimiento(${h.id},'${(h.nombre || '').replace(/'/g,"\\'").replace(/"/g,'&quot;')}')" title="Ver historial">📜</button>
           </div>
         </td>
    </tr>`;
  }, {
    batchSize: 30,
    emptyHtml: '<tr><td colspan="5" style="text-align:center;color:var(--t3);padding:24px">Sin herramientas</td></tr>'
  });

  if (confirmBtn) confirmBtn.disabled = rows.length === 0 || mantenimientoRecepcionIds.size === 0;
}

function onMantenimientoSearchInput() {
  dbSearch('paniol-mantenimiento', loadMantenimientoTab, 350);
}

function toggleMantenimientoRecepcion(id, checked) {
  if (checked) mantenimientoRecepcionIds.add(id);
  else mantenimientoRecepcionIds.delete(id);

  const confirmBtn = document.getElementById('paniol-mant-confirm');
  if (confirmBtn) confirmBtn.disabled = mantenimientoRecepcionIds.size === 0;
}

function estadoOptions(current) {
  const estados = ['operativa','mantenimiento','defectuosa','baja','buena','malo','regular','reparacion'];
  return estados.map(e => `<option value="${e}" ${e===current?'selected':''}>${e}</option>`).join('');
}

async function changeEstadoMant(id, estado) {
  const r = await api(`/api/herramientas/${id}`, {
    method:'PUT',
    headers:{'Content-Type':'application/json'},
    body: JSON.stringify({ condicion: estado })
  });
  if (r && r.ok) {
    if (estado !== 'mantenimiento') {
      mantenimientoRecepcionIds.delete(id);
    }
    toast('Estado actualizado');
    await refreshPaniolHerramientasViews();
  } else if (r) {
    toast(r.msg||'Error','err');
  }
}

function openMantInfo(id, nombre) {
  document.getElementById('mant-info-id').value = id;
  document.getElementById('mant-info-nombre').textContent = nombre;
  document.getElementById('mant-info-text').value = '';
  oM('m-mant-info');
  setTimeout(() => document.getElementById('mant-info-text').focus(), 150);
}

async function saveMantInfo() {
  const id = document.getElementById('mant-info-id').value;
  const info = document.getElementById('mant-info-text').value.trim();
  if (!info) { toast('Ingresa información', 'err'); return; }
  const r = await api(`/api/herramientas/${id}/mantenimiento-info`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ info })
  });
  if (!r || !r.ok) {
    toast((r && r.msg) || 'No se pudo guardar la información', 'err');
    return;
  }
  cM('m-mant-info');
  toast('Información registrada');
  await refreshPaniolHerramientasViews();
}

async function confirmMantenimientoRecepcion() {
  const ids = [...mantenimientoRecepcionIds];
  if (!ids.length) {
    toast('Selecciona al menos una herramienta en mantención', 'err');
    return;
  }

  const btn = document.getElementById('paniol-mant-confirm');
  if (btn) btn.disabled = true;

  let okCount = 0;
  let errCount = 0;

  for (const id of ids) {
    const r = await api(`/api/herramientas/${id}/recibir-mantenimiento`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ responsable_nombre: 'Pañol' })
    });
    if (r && r.ok) okCount += 1;
    else errCount += 1;
  }

  mantenimientoRecepcionIds.clear();
  await refreshPaniolHerramientasViews();

  if (okCount > 0 && errCount === 0) {
    toast(`Se habilitaron ${okCount} herramienta(s)`);
  } else if (okCount > 0 && errCount > 0) {
    toast(`Habilitadas ${okCount}, con ${errCount} error(es)`, 'warn');
  } else {
    toast('No se pudo habilitar ninguna herramienta', 'err');
  }
}

async function refreshPaniolHerramientasViews() {
  const tasks = [];
  if (!document.hidden) tasks.push(loadPaniolKPIs());

  if (isPaniolPanelActive('inventario')) tasks.push(loadInventarioTab());
  if (isPaniolPanelActive('mantenimiento')) tasks.push(loadMantenimientoTab());
  if (isPaniolPanelActive('entrega')) tasks.push(searchEntregaHerramientas());
  if (isPaniolPanelActive('devolucion')) tasks.push(searchDevolucionHerramientas());

  await Promise.all(tasks);
}

async function refreshActivePaniolPanel() {
  if (!isPaniolPageActive()) return;

  if (isPaniolPanelActive('mantenimiento')) return loadMantenimientoTab();
  if (isPaniolPanelActive('inventario')) return loadInventarioTab();
  if (isPaniolPanelActive('historial')) return loadHistorialTab();
  if (isPaniolPanelActive('entrega')) return searchEntregaHerramientas();
  if (isPaniolPanelActive('devolucion')) return searchDevolucionHerramientas();

  return loadPaniolKPIs();
}

document.addEventListener('visibilitychange', () => {
  if (!document.hidden) {
    refreshActivePaniolPanel();
  }
});

/* legacy maintainence functions commented out for simplificación
async function loadMantenimientoTab() {
  ...old implementation...
}
function selectMantenimientoEnvio(id, nombre, sku) { ... }
async function confirmMantenimientoEnvio() { ... }
function selectMantenimientoRecepcion(id, nombre, sku) { ... }
async function confirmMantenimientoRecepcion() { ... }
*/

// ======================================
// EMPLEADOS
// ======================================

async function searchEmpleados() {
  empS.p = 1;
  lEmpleados();
}

// context puede ser 'default'|'entrega'|'devolucion' para enrutar resultados
typeCtx = 'default';
async function lEmpleados(context = 'default') {
  const isEntrega = context === 'entrega';
  const isDevol = context === 'devolucion';
  const isUsuarios = context === 'usuarios';

  const searchEl = isEntrega
    ? 'entrega-user-search'
    : isDevol
      ? 'devol-user-search'
      : isUsuarios
        ? 'paniol-users-search'
        : 'emp-s';
  const deptEl = document.getElementById(isUsuarios ? 'paniol-users-dept' : 'emp-dept');
  const cargoEl = document.getElementById('emp-cargo');
  const search = document.getElementById(searchEl)?.value.trim() || '';
  const dept = deptEl?.value || '';
  const cargo = cargoEl?.value || '';
  
  const p = new URLSearchParams({ 
    page: empS.p, 
    per_page: 50, 
    search: search,
    departamento: dept,
    cargo: cargo
  });
  
  const d = await api('/api/empleados?' + p);
  if (!d) return;
  
  // Llenar filtros de departamento y cargo (se comparten)
  if (d.departamentos && deptEl) {
    const currentDept = deptEl.value;
    deptEl.innerHTML = '<option value="">Todos departamentos</option>' + 
      d.departamentos.map(dep => `<option value="${dep}" ${dep === currentDept ? 'selected' : ''}>${dep}</option>`).join('');
  }
  if (d.cargos && cargoEl) {
    const cargoSelect = $('emp-cargo');
    const currentCargo = cargoSelect.value;
    cargoSelect.innerHTML = '<option value="">Todos cargos</option>' + 
      d.cargos.map(c => `<option value="${c}" ${c === currentCargo ? 'selected' : ''}>${c}</option>`).join('');
  }
  
  const renderTarget = isEntrega
    ? 'entrega-user-list'
    : isDevol
      ? 'devol-user-list'
      : isUsuarios
        ? 'paniol-users-body'
        : 'emp-b';
  const bodyEl = document.getElementById(renderTarget);
  if (!bodyEl) return;

  if (d.empleados.length === 0) {
    const cols = isEntrega || isDevol ? 2 : isUsuarios ? 7 : 8;
    bodyEl.innerHTML = `<tr><td colspan="${cols}"><div class="empty"><div class="empty-t">Sin empleados</div></div></td></tr>`;
  } else if (isEntrega || isDevol) {
    // Filtrar solo usuarios ACTIVOS para entrega/devolución
    const empleadosValidos = d.empleados.filter(e => e.activo === true || e.activo === 1);
    if (empleadosValidos.length === 0) {
      bodyEl.innerHTML = `<tr><td colspan="2"><div class="empty"><div class="empty-t">Solo se muestran empleados activos</div></div></td></tr>`;
    } else {
      bodyEl.innerHTML = empleadosValidos.map(e => {
        const num = e.numero_identificacion || e.numero_empleado || e.employee_number || e.numero || '';
        const nom = e.nombre || e.name || e.nombre_empleado || '—';
        const sel = (isEntrega && SimpleState.entrega.usuario && String(SimpleState.entrega.usuario.id) === String(e.id))
                 || (isDevol && SimpleState.devolucion.usuario && String(SimpleState.devolucion.usuario.id) === String(e.id));
        return `<tr class="${sel?'selected':''}${isEntrega||isDevol?' clickable':''}" onclick="select${isEntrega? 'Entrega' : 'Devolucion'}Usuario(${e.id},'${nom.replace(/'/g,"\\'")}',${num})">
          <td class="m" style="font-weight:700;font-size:12px;color:var(--ac)">${num}</td>
          <td style="font-weight:600">${nom}</td>
        </tr>`;
      }).join('');
    }
  } else {
    bodyEl.innerHTML = d.empleados.map(e => {
      const num = e.numero_identificacion || e.numero_empleado || e.employee_number || e.numero || '';
      const nom = e.nombre || e.name || e.nombre_empleado || '—';
      const cargoTxt = e.puesto || e.cargo || '-';
      const deptTxt = e.departamento || '-';
      const emailTxt = e.email || '-';
      const estadoTxt = (e.estado || '').toString().toLowerCase();
      const activo = estadoTxt === 'activo' || estadoTxt === '1' || estadoTxt === 'true';
      const badge = `<span class="badge-condicion ${activo ? 'operativa' : 'defectuosa'}">${activo ? 'Activo' : 'Inactivo'}</span>`;
      return `<tr>
        <td class="m" style="font-weight:700;font-size:11px;color:var(--ac)">${num}</td>
        <td style="font-weight:600">${nom}</td>
        <td>${cargoTxt}</td>
        <td>${deptTxt}</td>
        <td>${emailTxt}</td>
        <td>${badge}</td>
        <td>
          <div style="display:flex;gap:3px">
            <button class="bi bi-ac" onclick="editEmpleado(${e.id})" title="Editar">✎</button>
            <button class="bi bi-no" onclick="deleteEmpleado(${e.id})" title="Eliminar">✕</button>
          </div>
        </td>
      </tr>`;
    }).join('');
  }

  rP(isUsuarios ? 'paniol-users-p' : 'emp-p', d, empS, () => lEmpleados(context));
}


// caching user list for dropdown filtering
let entregaUsersCache = [];
let devolucionUsersCache = [];

async function loadUsersForContext(context) {
  const cache = context === 'entrega' ? entregaUsersCache : devolucionUsersCache;
  if (cache.length === 0) {
    const q = '';
    const d = await api('/api/empleados?per_page=100&page=1&search=' + encodeURIComponent(q));
    if (d && d.empleados) {
      // FILTRO: Solo usuarios ACTIVOS para entregar/devolver herramientas
      const activeUsers = d.empleados.filter(e => e.activo === true || e.activo === 1);
      cache.push(...activeUsers);
    }
  }
  populateUserDropdown(context, cache);
}

function populateUserDropdown(context, list) {
  const select = document.getElementById(`${context}-user-select`);
  if (!select) return;
  const current = context === 'entrega'
    ? (SimpleState.entrega.usuario?.id ? String(SimpleState.entrega.usuario.id) : select.value)
    : (SimpleState.devolucion.usuario?.id ? String(SimpleState.devolucion.usuario.id) : select.value);
  // Asegurar que solo mostramos usuarios ACTIVOS
  const activeUsers = (list || []).filter(u => u.activo === true || u.activo === 1);
  select.innerHTML = '<option value="">-- selecciona usuario --</option>' +
    activeUsers.map(u => `<option value="${u.id}">${u.numero_empleado || u.numero_identificacion || ''} - ${u.nombre || u.name || ''}</option>`).join('');
  if (current) select.value = current;
}

function filterUserOptions(context) {
  const filter = document.getElementById(`${context}-user-filter`).value.toLowerCase();
  const cache = context === 'entrega' ? entregaUsersCache : devolucionUsersCache;
  const filtered = cache
    .filter(u => u.activo === true || u.activo === 1) // Solo activos
    .filter(u => {
      const txt = `${u.numero_empleado||u.numero_identificacion||''} ${u.nombre||u.name||''}`.toLowerCase();
      return txt.includes(filter);
    });
  populateUserDropdown(context, filtered);
}

function selectEntregaUsuarioFromDropdown(val) {
  if (!val) {
    SimpleState.entrega.usuario = null;
    searchEntregaHerramientas();
    updateEntregaSummaryState();
    return;
  }
  const user = entregaUsersCache.find(u => String(u.id) === String(val));
  SimpleState.entrega.usuario = user ? { id: user.id, nombre: user.nombre || user.name } : { id: val };
  // limpiar carrito cuando cambiamos usuario
  SimpleState.entrega.herramientas = [];
  renderEntregaCarrito();
  searchEntregaHerramientas();
  updateEntregaSummaryState();
}

function selectDevolucionUsuarioFromDropdown(val) {
  if (!val) {
    SimpleState.devolucion.usuario = null;
    SimpleState.devolucion.prestamos = [];
    renderDevolucionCarrito();
    searchDevolucionHerramientas();
    updateDevolucionSummaryState();
    return;
  }
  const user = devolucionUsersCache.find(u => String(u.id) === String(val));
  SimpleState.devolucion.usuario = user ? { id: user.id, nombre: user.nombre || user.name } : { id: val };
  SimpleState.devolucion.prestamos = [];
  renderDevolucionCarrito();
  searchDevolucionHerramientas();
  updateDevolucionSummaryState();
}

function openNewEmpleado() {
  $('memp-t').textContent = 'Nuevo Empleado';
  $('memp-id').value = '';
  $('memp-num').value = '';
  $('memp-nom').value = '';
  $('memp-rut').value = '';
  $('memp-email').value = '';
  $('memp-cargo').value = '';
  $('memp-dept').value = '';
  $('memp-tel').value = '';
  $('memp-activo').value = '1';
  $('memp-del').style.display = 'none';
  $('memp-num').readOnly = false;
  
  // Sugerir próximo número
  api('/api/empleados/suggest-numero').then(d => {
    if (d && d.numero) $('memp-num').value = d.numero;
  });
  
  oM('m-empleado');
}

async function editEmpleado(id) {
  const d = await api('/api/empleados/' + id);
  if (!d || !d.empleado) return toast('Empleado no encontrado', 'err');
  
  const e = d.empleado;
  $('memp-t').textContent = 'Editar Empleado';
  $('memp-id').value = e.id;
  $('memp-num').value = e.numero_empleado;
  $('memp-nom').value = e.nombre;
  $('memp-rut').value = e.rut || '';
  $('memp-email').value = e.email || '';
  $('memp-cargo').value = e.cargo || '';
  $('memp-dept').value = e.departamento || '';
  $('memp-tel').value = e.telefono || '';
  $('memp-activo').value = e.activo ? '1' : '0';
  $('memp-del').style.display = 'inline-block';
  $('memp-num').readOnly = true;
  
  oM('m-empleado');
}

async function saveEmpleado() {
  const nombre = $('memp-nom').value.trim();
  const numero = $('memp-num').value.trim();
  
  if (!nombre || !numero) return toast('Nombre y número obligatorios', 'err');
  
  const data = {
    numero_empleado: numero,
    nombre: nombre,
    rut: $('memp-rut').value.trim(),
    email: $('memp-email').value.trim(),
    cargo: $('memp-cargo').value.trim(),
    departamento: $('memp-dept').value.trim(),
    telefono: $('memp-tel').value.trim(),
    activo: parseInt($('memp-activo').value)
  };
  
  const id = $('memp-id').value;
  const url = id ? `/api/empleados/${id}` : '/api/empleados';
  const method = id ? 'PUT' : 'POST';
  
  const r = await api(url, {
    method: method,
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data)
  });
  
  if (r && r.ok) {
    toast(r.msg);
    cM('m-empleado');
    entregaUsersCache = [];
    devolucionUsersCache = [];
    if (typeof consumoUsersCache !== 'undefined') consumoUsersCache = [];
    lEmpleados('usuarios');
  } else if (r) {
    toast(r.msg, 'err');
  }
}

async function deleteEmpleado(id) {
  if (!confirm('¿Eliminar empleado?')) return;
  
  const r = await api('/api/empleados/' + id, { method: 'DELETE' });
  
  if (r && r.ok) {
    toast(r.msg);
    entregaUsersCache = [];
    devolucionUsersCache = [];
    if (typeof consumoUsersCache !== 'undefined') consumoUsersCache = [];
    lEmpleados('usuarios');
  } else if (r) {
    toast(r.msg, 'err');
  }
}

// ======================================
// HERRAMIENTAS
// ======================================

async function searchHerramientas() {
  herrS.p = 1;
  lHerramientas();
}

async function lHerramientas() {
  // Compatibilidad: si la vista legacy fue removida, usa el inventario de Pañol.
  if (!$('herr-s') || !$('herr-estado') || !$('herr-cat') || !$('herr-b')) {
    if (typeof loadInventarioTab === 'function') {
      await loadInventarioTab();
    }
    return;
  }

  const search = $('herr-s').value.trim();
  const condicion = $('herr-estado').value;
  const categoria = $('herr-cat').value;
  
  const p = new URLSearchParams({ 
    page: herrS.p, 
    per_page: 50, 
    search: search,
    condicion: condicion,
    categoria: categoria
  });
  
  const d = await api('/api/herramientas?' + p);
  if (!d) return;
  
  // Llenar filtro de categorías
  if (d.categorias) {
    const catSelect = $('herr-cat');
    const currentCat = catSelect.value;
    catSelect.innerHTML = '<option value="">Todas categorías</option>' + 
      d.categorias.map(cat => `<option value="${cat}" ${cat === currentCat ? 'selected' : ''}>${cat}</option>`).join('');
  }
  
  $('herr-b').innerHTML = d.herramientas.length === 0
    ? '<tr><td colspan="8"><div class="empty"><div class="empty-t">Sin herramientas</div></div></td></tr>'
    : d.herramientas.map(h => {
      const total = h.cantidad_total || 0;
      const disponible = h.cantidad_disponible || 0;
      const badgeEstado = `<span class="badge-condicion ${h.condicion}">${h.condicion}</span>`;
      const calibInfo = h.requiere_calibracion 
        ? (h.proxima_calibracion ? `Próx: ${h.proxima_calibracion}` : 'Sin calibrar')
        : '-';
      
      return `<tr>
        <td class="m" style="font-weight:700;font-size:11px;color:var(--ac)">${h.sku}</td>
        <td style="font-weight:600">${h.nombre}</td>
        <td>${h.categoria || '-'}</td>
        <td style="text-align:right">${total}</td>
        <td style="text-align:right;font-weight:700;color:${disponible > 0 ? 'var(--ok)' : 'var(--no)'}">${disponible}</td>
        <td>${badgeEstado}</td>
        <td style="font-size:10px;color:var(--t3)">${calibInfo}</td>
        <td>
          <div style="display:flex;gap:3px;flex-wrap:wrap">
            <button class="bi bi-ac" onclick="viewKardexHerramienta(${h.id},'${(h.nombre || '').replace(/'/g, "\\'").replace(/"/g, '&quot;')}','${(h.sku || '').replace(/"/g, '&quot;')}')" title="Kardex">📊</button>
            <button class="bi bi-ok" onclick="openMantenimiento(${h.id},'${(h.nombre || '').replace(/'/g, "\\'").replace(/"/g, '&quot;')}','${(h.sku || '').replace(/"/g, '&quot;')}')" title="Mantenimiento">🔧</button>
            <button class="bi bi-ac" onclick="editHerramienta(${h.id})" title="Editar">✎</button>
            <button class="bi bi-no" onclick="deleteHerramienta(${h.id})" title="Eliminar">✕</button>
          </div>
        </td>
      </tr>`;
    }).join('');
  
  rP('herr-p', d, herrS, lHerramientas);
}

function openNewHerramienta() {
  $('mherr-t').textContent = 'Nueva Herramienta';
  $('mherr-id').value = '';
  $('mherr-sku').value = '';
  $('mherr-nom').value = '';
  $('mherr-cat').value = '';
  $('mherr-marca').value = '';
  $('mherr-modelo').value = '';
  $('mherr-serie').value = '';
  $('mherr-cant').value = '1';
  $('mherr-ubi').value = '';
  $('mherr-estado').value = 'operativa';
  $('mherr-valor').value = '0';
  $('mherr-req-calib').checked = false;
  $('mherr-frec-calib').value = '';
  $('mherr-ult-calib').value = '';
  $('mherr-desc').value = '';
  $('mherr-del').style.display = 'none';
  $('mherr-sku').readOnly = false;
  toggleCalibracionFields();
  
  // Sugerir próximo SKU
  api('/api/herramientas/suggest-sku').then(d => {
    if (d && d.sku) $('mherr-sku').value = d.sku;
  });
  
  oM('m-herramienta');
}

async function editHerramienta(id) {
  const d = await api('/api/herramientas/' + id);
  if (!d || !d.herramienta) return toast('Herramienta no encontrada', 'err');
  
  const h = d.herramienta;
  $('mherr-t').textContent = 'Editar Herramienta';
  $('mherr-id').value = h.id;
  $('mherr-sku').value = h.sku;
  $('mherr-nom').value = h.nombre;
  $('mherr-cat').value = h.categoria || '';
  $('mherr-marca').value = h.marca || '';
  $('mherr-modelo').value = h.modelo || '';
  $('mherr-serie').value = h.numero_serie || '';
  $('mherr-cant').value = h.cantidad_total || 1;
  $('mherr-ubi').value = h.ubicacion || '';
  $('mherr-estado').value = h.condicion || 'operativa';
  $('mherr-valor').value = h.precio_unitario || 0;
  $('mherr-req-calib').checked = h.requiere_calibracion;
  $('mherr-frec-calib').value = h.frecuencia_calibracion_dias || '';
  $('mherr-ult-calib').value = h.ultima_calibracion || '';
  $('mherr-desc').value = h.descripcion || '';
  $('mherr-del').style.display = 'inline-block';
  $('mherr-sku').readOnly = true;
  toggleCalibracionFields();
  
  oM('m-herramienta');
}

function toggleCalibracionFields() {
  const calibFields = $('calib-fields');
  calibFields.style.display = $('mherr-req-calib').checked ? 'block' : 'none';
}

async function saveHerramienta() {
  const nombre = $('mherr-nom').value.trim();
  const sku = $('mherr-sku').value.trim();
  
  if (!nombre || !sku) return toast('Nombre y SKU obligatorios', 'err');
  
  const data = {
    sku: sku,
    nombre: nombre,
    categoria: $('mherr-cat').value.trim(),
    fabricante: $('mherr-marca').value.trim(),
    modelo: $('mherr-modelo').value.trim(),
    numero_serie: $('mherr-serie').value.trim(),
    cantidad_total: parseInt($('mherr-cant').value),
    ubicacion: $('mherr-ubi').value.trim(),
    condicion: $('mherr-estado').value,
    precio_unitario: parseFloat($('mherr-valor').value) || 0,
    requiere_calibracion: $('mherr-req-calib').checked ? 1 : 0,
    frecuencia_calibracion_dias: $('mherr-req-calib').checked ? parseInt($('mherr-frec-calib').value) || null : null,
    ultima_calibracion: $('mherr-req-calib').checked ? $('mherr-ult-calib').value || null : null,
    descripcion: $('mherr-desc').value.trim()
  };
  
  const id = $('mherr-id').value;
  const url = id ? `/api/herramientas/${id}` : '/api/herramientas';
  const method = id ? 'PUT' : 'POST';
  
  const r = await api(url, {
    method: method,
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data)
  });
  
  if (r && r.ok) {
    toast(r.msg);
    cM('m-herramienta');
    await refreshPaniolHerramientasViews();
  } else if (r) {
    toast(r.msg, 'err');
  }
}

async function deleteHerramienta(id) {
  if (!confirm('¿Eliminar herramienta?')) return;
  
  const r = await api('/api/herramientas/' + id, { method: 'DELETE' });
  
  if (r && r.ok) {
    toast(r.msg);
    await refreshPaniolHerramientasViews();
  } else if (r) {
    toast(r.msg, 'err');
  }
}

// ======================================
// CHECKOUT (PRÉSTAMO)
// ======================================

function openCheckoutHerramientas() {
  checkoutItems = [];
  $('mco-fecha').value = new Date().toISOString().split('T')[0];
  $('mco-emp').value = '';
  $('mco-obs').value = '';
  $('mco-herr').value = '';
  $('mco-cant').value = '1';
  $('mco-herr-id').value = '';
  $('mco-info').textContent = '';
  updateCheckoutTable();
  
  // Cargar lista de empleados
  api('/api/empleados?per_page=500').then(d => {
    if (d && d.empleados) {
      const empList = $('emp-list');
      empList.innerHTML = d.empleados
        .filter(e => e.activo)
        .map(e => `<option value="${e.numero_empleado}">${e.numero_empleado} - ${e.nombre}</option>`)
        .join('');
    }
  });
  
  // Cargar lista de herramientas disponibles
  api('/api/herramientas?per_page=500&condicion=operativa').then(d => {
    if (d && d.herramientas) {
      const herrList = $('herr-disp-list');
      herrList.innerHTML = d.herramientas
        .filter(h => (h.cantidad_disponible || 0) > 0)
        .map(h => {
          const disp = h.cantidad_disponible || 0;
          return `<option value="${h.sku}" data-id="${h.id}" data-disp="${disp}">${h.sku} - ${h.nombre} (Disp: ${disp})</option>`;
        })
        .join('');
    }
  });
  
  oM('m-checkout');
}

function addCheckoutItem() {
  const herrInput = $('mco-herr').value.trim();
  const cant = parseInt($('mco-cant').value);
  
  if (!herrInput || !cant || cant < 1) {
    $('mco-info').textContent = 'Selecciona herramienta y cantidad válida';
    return;
  }
  
  // Buscar herramienta en la lista
  api('/api/herramientas/search?q=' + encodeURIComponent(herrInput)).then(d => {
    if (!d || !d.herramientas || d.herramientas.length === 0) {
      $('mco-info').textContent = 'Herramienta no encontrada';
      return;
    }
    
    const h = d.herramientas[0];
    const disponible = h.cantidad_disponible || 0;
    
    if (disponible < cant) {
      $('mco-info').textContent = `Solo hay ${disponible} disponibles`;
      return;
    }
    
    // Verificar si ya está en la lista
    if (checkoutItems.find(item => item.herramienta_id === h.id)) {
      $('mco-info').textContent = 'Herramienta ya agregada';
      return;
    }
    
    checkoutItems.push({
      herramienta_id: h.id,
      sku: h.sku,
      nombre: h.nombre,
      cantidad: cant,
      disponible: disponible
    });
    
    $('mco-herr').value = '';
    $('mco-cant').value = '1';
    $('mco-info').textContent = '';
    updateCheckoutTable();
  });
}

function removeCheckoutItem(index) {
  checkoutItems.splice(index, 1);
  updateCheckoutTable();
}

function updateCheckoutTable() {
  $('mco-cnt').textContent = `${checkoutItems.length} herramienta${checkoutItems.length !== 1 ? 's' : ''}`;
  $('mco-ti').textContent = checkoutItems.length;
  $('mco-tu').textContent = checkoutItems.reduce((sum, item) => sum + item.cantidad, 0);
  
  if (checkoutItems.length === 0) {
    $('mco-body').innerHTML = '<tr><td colspan="6" style="text-align:center;padding:24px;color:var(--t3);font-size:11px">Agrega herramientas arriba</td></tr>';
    return;
  }
  
  $('mco-body').innerHTML = checkoutItems.map((item, idx) => `<tr>
    <td>${idx + 1}</td>
    <td class="m" style="color:var(--t3);font-size:10px">${item.sku}</td>
    <td style="font-weight:600">${item.nombre}</td>
    <td style="text-align:right;color:var(--t3)">${item.disponible}</td>
    <td style="text-align:right;font-weight:700">${item.cantidad}</td>
    <td><button class="bi bi-no" onclick="removeCheckoutItem(${idx})">✕</button></td>
  </tr>`).join('');
}

async function saveCheckout() {
  const fecha = $('mco-fecha').value;
  const empleado = $('mco-emp').value.trim();
  const obs = $('mco-obs').value.trim();
  
  if (!fecha || !empleado) return toast('Fecha y empleado obligatorios', 'err');
  if (checkoutItems.length === 0) return toast('Agrega al menos una herramienta', 'err');
  
  const data = {
    fecha: fecha,
    empleado: empleado,
    observaciones: obs,
    herramientas: checkoutItems.map(item => ({
      herramienta_id: item.herramienta_id,
      cantidad: item.cantidad
    }))
  };
  
  const r = await api('/api/herramientas/checkout', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data)
  });
  
  if (r && r.ok) {
    toast(r.msg);
    closeMCheckout();
    if (window.location.hash === '#paniol' || window.location.hash === '') {
      loadPaniolDashboard();
    }
    if (window.location.hash === '#herramientas') {
      loadInventarioTab();
    }
  } else if (r) {
    toast(r.msg, 'err');
  }
}

function closeMCheckout() {
  checkoutItems = [];
  cM('m-checkout');
}

// ======================================
// CHECKIN (DEVOLUCIÓN)
// ======================================

function openCheckin(movId, herrNombre, empNombre, cant) {
  $('mci-mov-id').value = movId;
  $('mci-herr').value = herrNombre;
  $('mci-emp').value = empNombre;
  $('mci-cant').value = cant;              // para mostrar cantidad prestada
  $('mci-cant').min = 1;
  $('mci-cant').max = cant;
  $('mci-cant').readOnly = false;          // permitir modificar en caso de devoluciones parciales
  $('mci-fecha').value = new Date().toISOString().split('T')[0];
  $('mci-estado').value = 'operativa';
  $('mci-obs').value = '';
  
  oM('m-checkin');
}

async function saveCheckin() {
  const movId = $('mci-mov-id').value;
  const fecha = $('mci-fecha').value;
  const estado = $('mci-estado').value;
  const obs = $('mci-obs').value.trim();
  const cantidad = parseInt($('mci-cant').value, 10);
  
  if (!fecha || !estado) return toast('Fecha y estado obligatorios', 'err');
  if (estado !== 'operativa' && !obs) return toast('Las observaciones son obligatorias si el estado no es operativa', 'err');
  if (isNaN(cantidad) || cantidad < 1) return toast('Cantidad devuelta inválida', 'err');
  
  const data = {
    movimiento_id: parseInt(movId),
    fecha_devolucion: fecha,
    estado_devolucion: estado,
    observaciones_devolucion: obs,
    cantidad_devuelta: cantidad
  };
  
  const r = await api('/api/herramientas/checkin', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data)
  });
  
  if (r && r.ok) {
    toast(r.msg);
    cM('m-checkin');
    if (window.location.hash === '#paniol' || window.location.hash === '') {
      loadPaniolDashboard();
    }
    if (window.location.hash === '#herramientas') {
      loadInventarioTab();
    }
  } else if (r) {
    toast(r.msg, 'err');
  }
}

// ======================================
// MANTENIMIENTO
// ======================================

function openMantenimiento(herrId, herrNombre, herrSku) {
  $('mmant-herr-id').value = herrId;
  $('mmant-herr').value = `${herrNombre} (${herrSku})`;
  $('mmant-tipo').value = 'preventivo';
  $('mmant-fecha').value = new Date().toISOString().split('T')[0];
  $('mmant-desc').value = '';
  $('mmant-costo').value = '0';
  $('mmant-realizado').value = '';
  $('mmant-obs').value = '';
  
  oM('m-mant');
}

async function saveMantenimiento() {
  const herrId = $('mmant-herr-id').value;
  const tipo = $('mmant-tipo').value;
  const fecha = $('mmant-fecha').value;
  const desc = $('mmant-desc').value.trim();
  const costo = parseFloat($('mmant-costo').value) || 0;
  const responsable = $('mmant-realizado').value.trim();
  const obs = $('mmant-obs').value.trim();
  
  if (!tipo || !fecha || !desc) return toast('Tipo, fecha y descripción obligatorios', 'err');
  
  const data = {
    herramienta_id: parseInt(herrId),
    tipo: tipo,
    fecha_mantenimiento: fecha,
    descripcion: desc,
    costo: costo,
    responsable_nombre: responsable,
    observaciones: obs
  };
  
  const r = await api(`/api/herramientas/${herrId}/mantenimiento`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data)
  });
  
  if (r && r.ok) {
    toast(r.msg);
    cM('m-mant');
    await refreshPaniolHerramientasViews();
  } else if (r) {
    toast(r.msg, 'err');
  }
}

// ======================================
// KARDEX HERRAMIENTA
// ======================================

async function viewKardexHerramienta(herrId, herrNombre, herrSku) {
  $('mkh-sub').textContent = `${herrNombre} (${herrSku})`;
  $('mkh-timeline').innerHTML = '<div style="text-align:center;padding:40px;color:var(--t3)">Cargando...</div>';
  
  oM('m-kardex-herr');
  
  const d = await api('/api/herramientas/' + herrId + '/kardex');
  if (!d || !d.movimientos) {
    $('mkh-timeline').innerHTML = '<div style="text-align:center;padding:40px;color:var(--t3)">Sin movimientos</div>';
    return;
  }
  
  $('mkh-timeline').innerHTML = d.movimientos.map(m => {
    const icon = m.tipo === 'prestamo' ? '📤' : '📥';
    const colorClass = m.tipo === 'prestamo' ? 'salida' : 'devolucion';
    const estadoBadge = m.estado_devolucion ? `<span class="badge-condicion ${m.estado_devolucion}">${m.estado_devolucion}</span>` : '';
    
    return `<div class="kardex-item ${colorClass}">
      <div class="kardex-icon icon-unicode">${icon}</div>
      <div class="kardex-content">
        <div class="kardex-header">
          <strong>${m.tipo === 'prestamo' ? 'Préstamo' : 'Devolución'}</strong>
          <span class="kardex-date">${m.fecha}</span>
        </div>
        <div class="kardex-details">
          <div>Empleado: <strong>${m.empleado}</strong></div>
          <div>Cantidad: <strong>${m.cantidad}</strong></div>
          ${m.observaciones ? `<div>Obs: ${m.observaciones}</div>` : ''}
          ${estadoBadge ? `<div>Estado: ${estadoBadge}</div>` : ''}
        </div>
      </div>
    </div>`;
  }).join('');
}

// ======================================
// PLANES DE MANTENIMIENTO
// ======================================

async function openPlanesMantenimiento() {
  // Cargar todas las herramientas
  api('/api/herramientas?per_page=500').then(d => {
    if (d && d.herramientas) {
      const herrList = $('herr-all-list');
      herrList.innerHTML = d.herramientas
        .map(h => `<option value="${h.sku}" data-id="${h.id}">${h.sku} - ${h.nombre}</option>`)
        .join('');
    }
  });
  
  loadPlanesMantenimiento();
  oM('m-planes-mant');
}

async function loadPlanesMantenimiento() {
  $('mpm-body').innerHTML = '<tr><td colspan="7" style="text-align:center;padding:24px;color:var(--t3)">Cargando...</td></tr>';
  
  const d = await api('/api/herramientas/planes-mantenimiento');
  if (!d || !d.planes) {
    $('mpm-body').innerHTML = '<tr><td colspan="7" style="text-align:center;padding:24px;color:var(--t3)">Sin planes</td></tr>';
    return;
  }
  
  $('mpm-body').innerHTML = d.planes.map(p => {
    const vencido = p.estado === 'vencido';
    const estadoBadge = `<span class="badge-condicion ${vencido ? 'defectuosa' : 'operativa'}">${p.estado}</span>`;
    
    return `<tr>
      <td style="font-weight:600">${p.herramienta_nombre}</td>
      <td>${p.tipo}</td>
      <td style="text-align:center">${p.frecuencia_dias} días</td>
      <td>${p.ultimo_mantenimiento || '-'}</td>
      <td>${p.proximo_mantenimiento || '-'}</td>
      <td>${estadoBadge}</td>
      <td>
        <button class="bi bi-no" onclick="deletePlan(${p.id})" title="Eliminar">✕</button>
      </td>
    </tr>`;
  }).join('');
}

async function createPlan() {
  const herrInput = $('mpm-herr').value.trim();
  const tipo = $('mpm-tipo').value;
  const frec = parseInt($('mpm-frec').value);
  
  if (!herrInput || !tipo || !frec || frec < 1) {
    return toast('Completa todos los campos', 'err');
  }
  
  // Buscar herramienta
  const searchResult = await api('/api/herramientas/search?q=' + encodeURIComponent(herrInput));
  if (!searchResult || !searchResult.herramientas || searchResult.herramientas.length === 0) {
    return toast('Herramienta no encontrada', 'err');
  }
  
  const herrId = searchResult.herramientas[0].id;
  
  const data = {
    herramienta_id: herrId,
    tipo: tipo,
    frecuencia_dias: frec
  };
  
  const r = await api('/api/herramientas/planes-mantenimiento', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data)
  });
  
  if (r && r.ok) {
    toast(r.msg);
    $('mpm-herr').value = '';
    $('mpm-frec').value = '30';
    loadPlanesMantenimiento();
  } else if (r) {
    toast(r.msg, 'err');
  }
}

async function deletePlan(id) {
  if (!confirm('¿Eliminar este plan de mantenimiento?')) return;
  
  const r = await api('/api/herramientas/planes-mantenimiento/' + id, { method: 'DELETE' });
  
  if (r && r.ok) {
    toast(r.msg);
    loadPlanesMantenimiento();
  } else if (r) {
    toast(r.msg, 'err');
  }
}

// Exponer acciones de Pañol usadas por onclick inline en index.html
Object.assign(window, {
  loadInventarioTab,
  loadMantenimientoTab,
  openNewHerramienta,
  editHerramienta,
  deleteHerramienta,
  viewKardexHerramienta,
  openMantenimiento,
  saveMantenimiento,
  changeEstadoMant,
  openMantInfo,
  saveMantInfo,
  toggleMantenimientoRecepcion,
  confirmMantenimientoRecepcion,
  openPlanesMantenimiento,
  loadPlanesMantenimiento,
  createPlan,
  deletePlan
});
