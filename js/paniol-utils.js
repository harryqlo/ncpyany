/**
 * Utilidades para el sistema de Pañol
 * Centraliza funciones comunes, rendering y estado
 */

// =========================================================================
// ESTADO GLOBAL CENTRALIZADO
// =========================================================================

const PaniolState = {
  // Paginación
  empleados: { page: 1 },
  herramientas: { page: 1 },
  usuariosCargo: { seleccionada: null },  // legacy, seguirá existiendo por compatibilidad
  movimientos: { seleccionada: null },  // nuevo campo para agrupar devoluciones/usuarios
  
  // Selecciones actuales
  devolución: {
    seleccionada: null,
    fecha: null,
    estado: 'operativa',
    observaciones: ''
  },
  
  // Cachés
  prestamosCache: [],
  
  // Reset
  reset() {
    this.devolución = {
      seleccionada: null,
      fecha: null,
      estado: 'operativa',
      observaciones: ''
    };
    this.movimientos.seleccionada = null;
    this.usuariosCargo.seleccionada = null;
  }
};

// =========================================================================
// HELPERS DE DOM Y UI
// =========================================================================

const PaniolUI = {
  /**
   * Obtiene elemento por ID
   */
  get(id) {
    return document.getElementById(id);
  },
  
  /**
   * Renderiza tabla de préstamos activos
   */
  renderPrestamos(prestamos, containerid = 'paniol-prestamos-body') {
    const container = this.get(containerid);
    if (!container) return;
    
    if (!prestamos || prestamos.length === 0) {
      container.innerHTML = '<tr><td colspan="4" style="text-align:center;padding:24px;color:var(--t3)">Sin préstamos activos.</td></tr>';
      return;
    }
    
    container.innerHTML = prestamos.map(p => `
      <tr>
        <td><div style="font-weight:600">${p.herramienta_nombre}</div><div class="m" style="font-size:10px;color:var(--t3)">${p.herramienta_sku || '-'}</div></td>
        <td>${p.empleado_nombre || '-'}</td>
        <td>${p.fecha_salida ||'-'}</td>
        <td><button class="btn bs bsm" onclick="openCheckin(${p.id},'${this.escape(p.herramienta_nombre)}','${this.escape(p.empleado_nombre)}',${p.cantidad || 1})">Devolver</button></td>
      </tr>
    `).join('');
  },
  
  /**
   * Renderiza tabla de herramientas
   */
  renderHerramientas(herramientas, containerId = 'herr-b') {
    const container = this.get(containerId);
    if (!container) return;

    if (!herramientas || herramientas.length === 0) {
      container.innerHTML = '<tr><td colspan="8"><div class="empty"><div class="empty-t">Sin herramientas</div></div></td></tr>';
      return;
    }

    container.innerHTML = herramientas.map(h => {
      const disponible = h.cantidad_disponible !== undefined ? (h.cantidad_disponible || 0) : 0;
      return `
        <tr>
          <td class="m" style="font-weight:700;font-size:11px;color:var(--ac)">${h.sku}</td>
          <td style="font-weight:600">${h.nombre}</td>
          <td>${h.categoria || '-'}</td>
          <td style="text-align:right">${h.cantidad_total || 0}</td>
          <td style="text-align:right;font-weight:700;color:${disponible > 0 ? 'var(--ok)' : 'var(--no)'}">${disponible}</td>
          <td><span class="badge-condicion ${h.condicion}">${(h.condicion || 'operativa').toUpperCase()}</span></td>
          <td style="font-size:10px;color:var(--t3)">${h.proxima_calibracion ? 'Próx: ' + h.proxima_calibracion : '-'}</td>
          <td>
            <div style="display:flex;gap:3px;flex-wrap:wrap">
              <button class="bi" onclick="viewKardexHerramienta(${h.id},'${this.escape(h.nombre)}','${h.sku}')" title="Kardex" style="color:var(--ac)">📊</button>
              <button class="bi" onclick="openMantenimiento(${h.id},'${this.escape(h.nombre)}','${h.sku}')" title="Mantenimiento" style="color:var(--ok)">🔧</button>
              <button class="bi" onclick="editHerramienta(${h.id})" title="Editar" style="color:var(--ac)">✎</button>
              <button class="bi" onclick="deleteHerramienta(${h.id})" title="Eliminar" style="color:var(--no)">✕</button>
            </div>
          </td>
        </tr>
      `;
    }).join('');
  },
  
  /**
   * Renderiza lista de devoluciones disponibles
   */
  renderDevolucionesLista(prestamos, containerId = 'paniol-devol-list') {
    const container = this.get(containerId);
    if (!container) return;
    
    if (!prestamos || prestamos.length === 0) {
      container.innerHTML = '<div style="padding:16px;color:var(--t3)">No hay préstamos para devolver.</div>';
      return;
    }
    
    const selected = PaniolState.devolución.seleccionada;
    container.innerHTML = prestamos.map(p => `
      <div class="paniol-loan-item ${selected && selected.id === p.id ? 'on' : ''}" onclick="selectPaniolDevolucion(${p.id})">
        <div style="font-weight:700">${p.herramienta_nombre}</div>
        <div style="font-size:11px;color:var(--t3)">${p.herramienta_sku} · ${p.empleado_nombre}</div>
        <div class="m" style="font-size:10px;margin-top:4px;color:var(--t3)">Salida: ${p.fecha_salida}</div>
      </div>
    `).join('');
  },
  
  /**
   * Renderiza detalle de devolución seleccionada
   */
  renderDevolucionDetalle(prestamo) {
    const container = this.get('paniol-devol-selected');
    if (!container) return;
    
    if (!prestamo) {
      container.innerHTML = 'Selecciona un préstamo para devolver.';
      return;
    }

    // permitimos devolver menos de la cantidad total
    const maxCant = prestamo.cantidad || 1;
    container.innerHTML = `
      <div style="font-weight:700">${prestamo.herramienta_nombre}</div>
      <div style="font-size:11px;color:var(--t3)">${prestamo.herramienta_sku || '-'} · ${prestamo.empleado_nombre || '-'}</div>
      <div class="m" style="margin-top:8px;font-size:10px;color:var(--t3)">
        Cantidad original: ${maxCant}
      </div>
      <div class="m" style="margin-top:4px;font-size:10px;color:var(--t3)">
        <label style="font-size:10px;color:var(--t3);">Devolver:</label>
        <input type="number" id="paniol-devol-cantidad" min="1" max="${maxCant}" value="${maxCant}" style="width:40px;margin-left:4px">
      </div>
      <div class="m" style="font-size:10px;color:var(--t3)">Fecha salida: ${prestamo.fecha_salida || '-'}</div>
    `;
  },

  renderUsuariosCargoLista(usuarios, containerId = 'paniol-user-list') {
    const container = this.get(containerId);
    if (!container) return;

    if (!usuarios || usuarios.length === 0) {
      container.innerHTML = '<div style="padding:16px;color:var(--t3)">Sin usuarios con herramientas a cargo.</div>';
      return;
    }

    const selected = PaniolState.usuariosCargo.seleccionada;
    container.innerHTML = usuarios.map(u => {
      const active = selected && selected.key === this._usuarioKey(u);
      return `
        <div class="paniol-loan-item ${active ? 'on' : ''}" onclick="selectPaniolUsuarioCargo('${this.escape(this._usuarioKey(u))}')">
          <div style="display:flex;justify-content:space-between;gap:8px;align-items:flex-start">
            <div>
              <div style="font-weight:700">${u.empleado_nombre || 'Sin nombre'}</div>
              <div style="font-size:11px;color:var(--t3)">${u.numero_identificacion || 'Sin identificación'}${u.departamento ? ' · ' + u.departamento : ''}</div>
            </div>
            <span class="badge-condicion operativa">${u.total_prestamos}</span>
          </div>
          <div class="m" style="font-size:10px;margin-top:6px;color:var(--t3)">Cant. total: ${u.cantidad_total || 0} · Desde: ${u.desde || '-'}</div>
        </div>
      `;
    }).join('');
  },

  renderUsuarioCargoDetalle(usuario, summaryId = 'paniol-user-summary', bodyId = 'paniol-user-tools-body') {
    const summary = this.get(summaryId);
    const body = this.get(bodyId);
    const title = this.get('paniol-user-title');
    if (!summary || !body || !title) return;

    if (!usuario) {
      title.textContent = 'Herramientas a Cargo';
      summary.innerHTML = '<div style="color:var(--t3)">Selecciona un usuario para ver sus herramientas.</div>';
      body.innerHTML = '<tr><td colspan="5" style="text-align:center;padding:24px;color:var(--t3)">Sin selección.</td></tr>';
      return;
    }

    title.textContent = usuario.empleado_nombre || 'Herramientas a Cargo';
    summary.innerHTML = `
      <div class="paniol-user-summary-grid">
        <div><div class="m" style="font-size:10px;color:var(--t3)">Identificación</div><div style="font-weight:700">${usuario.numero_identificacion || '-'}</div></div>
        <div><div class="m" style="font-size:10px;color:var(--t3)">Departamento</div><div style="font-weight:700">${usuario.departamento || '-'}</div></div>
        <div><div class="m" style="font-size:10px;color:var(--t3)">Herramientas</div><div style="font-weight:700">${usuario.total_prestamos || 0}</div></div>
        <div><div class="m" style="font-size:10px;color:var(--t3)">Cant. total</div><div style="font-weight:700">${usuario.cantidad_total || 0}</div></div>
      </div>
    `;

    body.innerHTML = (usuario.herramientas || []).map(item => `
      <tr>
        <td class="m" style="font-size:11px;color:var(--ac);font-weight:700">${item.herramienta_sku}</td>
        <td style="font-weight:600">${item.herramienta_nombre}</td>
        <td>${item.fecha_salida || '-'}</td>
        <td style="text-align:right">${item.cantidad || 1}</td>
        <td><button class="btn bs bsm" onclick="openDevolucionDesdeUsuario(${item.movimiento_id})">Devolver</button></td>
      </tr>
    `).join('');
  },

  _usuarioKey(usuario) {
    return usuario.empleado_id != null ? `id:${usuario.empleado_id}` : `nombre:${usuario.empleado_nombre || ''}`;
  },
  
  /**
   * Renderiza tabla de historial
   */
  renderHistorial(movimientos, containerId = 'paniol-hist-body') {
    const container = this.get(containerId);
    if (!container) return;
    
    if (!movimientos || movimientos.length === 0) {
      container.innerHTML = '<tr><td colspan="5" style="text-align:center;padding:24px;color:var(--t3)">Sin historial.</td></tr>';
      return;
    }
    
    container.innerHTML = movimientos.map(m => `
      <tr>
        <td><div style="font-weight:600">${m.herramienta_nombre}</div><div class="m" style="font-size:10px;color:var(--t3)">${m.herramienta_sku || '-'}</div></td>
        <td>${m.empleado_nombre || '-'}</td>
        <td>${m.fecha_salida || '-'}</td>
        <td>${m.fecha_retorno || '-'}</td>
        <td><span class="badge-condicion ${m.fecha_retorno ? 'operativa' : 'mantenimiento'}">${m.fecha_retorno ? 'CERRADO' : 'ACTIVO'}</span></td>
      </tr>
    `).join('');
  },
  
  /**
   * Escapa caracteres especiales en strings
   */
  escape(str) {
    return (str || '').replace(/'/g, "\\'").replace(/"/g, '\\"');
  },
  
  /**
   * Muestra/oculta loading
   */
  setLoading(containerId, show = true) {
    const el = this.get(containerId);
    if (el) {
      el.style.opacity = show ? '0.6' : '1';
      el.style.pointerEvents = show ? 'none' : 'auto';
    }
  }
};

// =========================================================================
// HELPERS DE API
// =========================================================================

const PaniolAPI = {
  /**
   * Obtiene préstamos activos
   */
  async getPrestamosActivos() {
    const d = await api('/api/herramientas/prestamos-activos');
    PaniolState.prestamosCache = (d && d.prestamos) ? d.prestamos : [];
    return PaniolState.prestamosCache;
  },
  
  /**
   * Obtiene movimientos del historial
   */
  async getHistorial(page = 1, perPage = 50) {
    return await api(`/api/herramientas/historial-movimientos?page=${page}&per_page=${perPage}`);
  },

  async getPrestamosPorUsuario(search = '') {
    const params = new URLSearchParams();
    if (search) params.set('search', search);
    const suffix = params.toString() ? `?${params.toString()}` : '';
    return await api(`/api/herramientas/prestamos-por-usuario${suffix}`);
  },
  
  /**
   * Realiza checkin (devolución)
   */
  async checkin(movimentoId, estadoRetorno, observaciones, opts = {}) {
    // opts puede contener cantidad (cantidad_devuelta) y fecha (fecha_devolucion)
    const payload = {
      devoluciones: [{
        movimiento_id: movimentoId,
        estado_retorno: estadoRetorno,
        observaciones_retorno: observaciones
      }]
    };

    if (opts.cantidad != null) {
      payload.devoluciones[0].cantidad_devuelta = opts.cantidad;
    }
    if (opts.fecha) {
      payload.devoluciones[0].fecha_devolucion = opts.fecha;
    }

    return await api('/api/herramientas/checkin', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
  },
  
  /**
   * Obtiene estadísticas
   */
  async getStats() {
    return await api('/api/herramientas/stats');
  }
};
