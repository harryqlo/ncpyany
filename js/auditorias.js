/**
 * js/auditorias.js — Módulo de Auditorías de Inventario
 * North Chrome v2
 *
 * Gestiona tres tipos de auditoría con rotación:
 *   - Rotativa (4 ciclos semanales)
 *   - Semanal completa
 *   - Mensual completa
 */
'use strict';

/* global showToast, toast, $ */

const Auditorias = (() => {
    const API = '/api/auditorias';
    let _inicializado = false;
    let _sesionActivaId = null;
    let _sesionActivaItems = [];
    let _paginaSesiones  = 1;
    let _paginaABC       = 1;
    let _filtroTipo      = '';
    let _filtroEstado    = '';

    // ─────────────────────────────────────────────────────────────────────
    // UTILIDADES
    // ─────────────────────────────────────────────────────────────────────

    function _notify(msg, tipo = 'info') {
        if (typeof showToast === 'function') {
            showToast(msg, tipo);
        } else if (typeof toast === 'function') {
            const map = { success: 'ok', error: 'err', warn: 'warn', info: 'ok' };
            toast(msg, map[tipo] || 'ok');
        } else {
            console.log(`[Auditorias][${tipo}] ${msg}`);
        }
    }

    function _abrirModal(id) {
        const modal = document.getElementById(id);
        if (!modal) return;
        modal.classList.add('on');
    }

    function _cerrarModal(id) {
        const modal = document.getElementById(id);
        if (!modal) return;
        modal.classList.remove('on');
    }

    function _fmt(v, decimals = 2) {
        if (v === null || v === undefined) return '—';
        return Number(v).toFixed(decimals);
    }

    function _escapeCsv(v) {
        const raw = v === null || v === undefined ? '' : String(v);
        if (raw.includes('"') || raw.includes(';') || raw.includes(',') || raw.includes('\n')) {
            return `"${raw.replace(/"/g, '""')}"`;
        }
        return raw;
    }

    function _normalizarHeader(v) {
        return (v || '')
            .toString()
            .trim()
            .toLowerCase()
            .normalize('NFD')
            .replace(/[\u0300-\u036f]/g, '')
            .replace(/\s+/g, '_');
    }

    function _parseCsvLine(line, sep) {
        const out = [];
        let cur = '';
        let inQuotes = false;
        for (let i = 0; i < line.length; i++) {
            const ch = line[i];
            if (ch === '"') {
                if (inQuotes && line[i + 1] === '"') {
                    cur += '"';
                    i++;
                } else {
                    inQuotes = !inQuotes;
                }
                continue;
            }
            if (ch === sep && !inQuotes) {
                out.push(cur.trim());
                cur = '';
                continue;
            }
            cur += ch;
        }
        out.push(cur.trim());
        return out;
    }

    function _defaultAuditorName() {
        const auth = window.currentAuthUser || null;
        return auth?.display_name || auth?.username || 'Bodeguero';
    }

    async function _solicitarNombreAuditor(tipo) {
        if (typeof showTextPromptModal !== 'function') {
            return _defaultAuditorName();
        }
        return await showTextPromptModal({
            title: 'Iniciar auditoría',
            message: `Ingresa el nombre del responsable para la sesión ${tipo}.`,
            label: 'Auditor responsable',
            placeholder: 'Ej: Juan Pérez',
            defaultValue: _defaultAuditorName(),
            confirmText: 'Iniciar sesión',
            cancelText: 'Cancelar',
            required: true,
        });
    }

    function _badgeTipo(tipo) {
        const colores = {
            rotativo: { bg: 'var(--ac)', fg: 'var(--on-ac)' },
            semanal:  { bg: 'var(--ok)', fg: 'var(--on-ok)' },
            mensual:  { bg: 'var(--in)', fg: '#fff' },
            spot:     { bg: 'var(--wa)', fg: 'var(--on-wa)' },
        };
        const c = colores[tipo] || { bg: 'var(--bg4)', fg: 'var(--t1)' };
        return `<span class="badge" style="background:${c.bg};color:${c.fg};padding:2px 7px;border-radius:4px;font-size:10px;font-weight:600">${tipo}</span>`;
    }

    function _badgeEstado(estado) {
        const colores = {
            pendiente:   'var(--t3)',
            en_progreso: 'var(--wa)',
            completada:  'var(--ok)',
            cancelada:   'var(--no)',
        };
        return `<span style="color:${colores[estado] || 'var(--t2)'};font-weight:600;font-size:11px">${estado}</span>`;
    }

    function _badgeABC(clase) {
        const colores = {
            A: { bg: 'var(--no)', fg: 'var(--on-no)' },
            B: { bg: 'var(--wa)', fg: 'var(--on-wa)' },
            C: { bg: 'var(--bg4)', fg: 'var(--t1)' },
        };
        const c = colores[clase] || { bg: 'var(--bg4)', fg: 'var(--t1)' };
        return `<span class="badge" style="background:${c.bg};color:${c.fg};padding:1px 6px;border-radius:3px;font-size:10px;font-weight:700">${clase}</span>`;
    }

    function _progBar(contados, total) {
        const pct = total > 0 ? Math.round(contados / total * 100) : 0;
        const color = pct >= 100 ? '#27ae60' : pct >= 50 ? '#e67e22' : '#e74c3c';
        return `<div style="display:flex;align-items:center;gap:6px">
            <div style="flex:1;background:var(--bg3);border-radius:4px;height:6px;overflow:hidden">
              <div style="width:${pct}%;height:6px;background:${color};border-radius:4px;transition:width .3s"></div>
            </div>
            <span style="font-size:10px;color:var(--t3);white-space:nowrap">${contados}/${total}</span>
        </div>`;
    }

    // ─────────────────────────────────────────────────────────────────────
    // INIT
    // ─────────────────────────────────────────────────────────────────────

    async function init() {
        _initFiltros();
        await Promise.all([
            cargarEstadisticas(),
            cargarSesiones(1),
            cargarPlanes(),
            cargarTablaABC(1),
        ]);
        _inicializado = true;
    }

    function ensureInit() {
        if (_inicializado) return Promise.resolve();
        return init();
    }

    function _initFiltros() {
        const selTipo   = document.getElementById('aud-filtro-tipo');
        const selEstado = document.getElementById('aud-filtro-estado');
        if (selTipo)   selTipo.onchange   = () => { _filtroTipo   = selTipo.value;   cargarSesiones(1); };
        if (selEstado) selEstado.onchange = () => { _filtroEstado = selEstado.value; cargarSesiones(1); };
    }

    // ─────────────────────────────────────────────────────────────────────
    // ESTADÍSTICAS
    // ─────────────────────────────────────────────────────────────────────

    async function cargarEstadisticas() {
        const r = await api(API + '/estadisticas').catch(() => null);
        if (!r || !r.ok) {
            const el = document.getElementById('aud-stats');
            if (el) {
                const msg = r?.msg || 'No fue posible cargar Auditorías en este momento.';
                el.innerHTML = `<div class="empty-state">${msg}</div>`;
            }
            return;
        }

        _setTxt('aud-stat-sesiones',   r.total_sesiones);
        _setTxt('aud-stat-completadas', r.completadas);
        _setTxt('aud-stat-pendientes',  r.pendientes);
        _setTxt('aud-stat-ajustes',     r.total_ajustes);
        _setTxt('aud-stat-vencidos',    r.items_pendientes_conteo);
        _setTxt('aud-abc-A', (r.clasificacion_abc || {}).A || 0);
        _setTxt('aud-abc-B', (r.clasificacion_abc || {}).B || 0);
        _setTxt('aud-abc-C', (r.clasificacion_abc || {}).C || 0);

        // Próximas auditorías
        const elProx = document.getElementById('aud-proximas-tbody');
        if (elProx && r.proximas_auditorias) {
            elProx.innerHTML = r.proximas_auditorias.map(p => `
                <tr>
                  <td>${p.nombre}</td>
                  <td>${_badgeTipo(p.tipo)}</td>
                  <td>${p.tipo === 'rotativo' ? `Ciclo ${p.ciclo_actual}/${p.total_ciclos}` : '—'}</td>
                  <td style="font-family:monospace">${p.fecha_proxima || '—'}</td>
                  <td>
                    <button class="btn bsm bg" onclick="Auditorias.iniciarDesdePanel('${p.tipo}')">▶ Iniciar</button>
                  </td>
                </tr>`).join('') || '<tr><td colspan="5" class="empty-label">Sin planes activos</td></tr>';
        }

        // Historial mensual
        const elHist = document.getElementById('aud-historial-tbody');
        if (elHist && r.historial_mensual) {
            elHist.innerHTML = r.historial_mensual.map(h => `
                <tr>
                  <td style="font-family:monospace">${h.mes}</td>
                  <td>${h.sesiones}</td>
                  <td>${h.diferencias || 0}</td>
                  <td>${h.ajustes || 0}</td>
                </tr>`).join('') || '<tr><td colspan="4" class="empty-label">Sin historial</td></tr>';
        }
    }

    function _setTxt(id, val) {
        const el = document.getElementById(id);
        if (el) el.textContent = val;
    }

    // ─────────────────────────────────────────────────────────────────────
    // PLANES
    // ─────────────────────────────────────────────────────────────────────

    async function cargarPlanes() {
        const r = await api(API + '/planes').catch(() => null);
        if (!r || !r.ok) return;
        const tbody = document.getElementById('aud-planes-tbody');
        if (!tbody) return;
        tbody.innerHTML = r.items.map(p => `
            <tr>
              <td>${p.nombre}</td>
              <td>${_badgeTipo(p.tipo)}</td>
              <td>${p.tipo === 'rotativo' ? `${p.ciclo_actual}/${p.total_ciclos}` : '—'}</td>
              <td style="font-family:monospace">${p.fecha_proxima || '—'}</td>
              <td>${p.filtro_categoria || 'Todos'}</td>
              <td>${p.filtro_clase ? _badgeABC(p.filtro_clase) : 'A+B+C'}</td>
              <td>
                <label class="toggle-sw">
                  <input type="checkbox" ${p.activo ? 'checked' : ''}
                    onchange="Auditorias.togglePlan(${p.id}, this.checked)">
                  <span class="slider"></span>
                </label>
              </td>
              <td>
                <button class="btn bsm bg" onclick="Auditorias.iniciarSesionDesdePlan(${p.id},'${p.tipo}')">▶ Iniciar</button>
              </td>
            </tr>`).join('') || '<tr><td colspan="8" class="empty-label">Sin planes</td></tr>';
    }

    async function togglePlan(planId, activo) {
        const r = await api(API + '/planes/' + planId, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ activo: activo ? 1 : 0 }),
        });
        if (!r.ok) _notify(r.msg, 'error');
    }

    async function crearPlan(data) {
        const r = await api(API + '/planes', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data),
        });
        if (r.ok) {
            _notify('Plan creado correctamente', 'success');
            cargarPlanes();
            cargarEstadisticas();
        } else {
            _notify(r.msg || 'Error al crear plan', 'error');
        }
        return r;
    }

    // ─────────────────────────────────────────────────────────────────────
    // SESIONES — LISTADO
    // ─────────────────────────────────────────────────────────────────────

    async function cargarSesiones(page = 1) {
        _paginaSesiones = page;
        const params = new URLSearchParams({ page, per_page: 15 });
        if (_filtroTipo)   params.set('tipo',   _filtroTipo);
        if (_filtroEstado) params.set('estado', _filtroEstado);

        const r = await api(API + '/sesiones?' + params).catch(() => null);
        if (!r || !r.ok) return;

        const tbody = document.getElementById('aud-sesiones-tbody');
        if (!tbody) return;

        tbody.innerHTML = r.items.map(s => {
            const pct = s.total_items > 0 ? Math.round(s.items_contados / s.total_items * 100) : 0;
            const btns = [];
            if (s.estado !== 'completada' && s.estado !== 'cancelada') {
                btns.push(`<button class="btn bsm bp" onclick="Auditorias.abrirConteo(${s.id})">📋 Contar</button>`);
            }
            if (s.estado === 'en_progreso') {
                btns.push(`<button class="btn bsm bg" onclick="Auditorias.aplicarAjustes(${s.id})">✅ Ajustar</button>`);
                btns.push(`<button class="btn bsm bd" onclick="Auditorias.cancelarSesion(${s.id})">✕</button>`);
            }
            if (s.estado === 'completada') {
                btns.push(`<button class="btn bsm bg" onclick="Auditorias.descargarReporte(${s.id})" title="Descargar reporte completo">📥 Reporte</button>`);
            }
            return `<tr>
              <td style="font-family:monospace;font-size:11px">#${s.id}</td>
              <td>${_badgeTipo(s.tipo)}</td>
              <td>${_badgeEstado(s.estado)}</td>
              <td style="font-size:11px">${s.semana_iso || s.mes_periodo || '—'}</td>
              <td>${s.ciclo_numero ? `Ciclo ${s.ciclo_numero}` : '—'}</td>
              <td>${_progBar(s.items_contados, s.total_items)}</td>
              <td style="text-align:right;color:${s.items_con_diferencia > 0 ? '#e74c3c' : 'var(--t3)'}">${s.items_con_diferencia || 0}</td>
              <td style="font-size:10px;color:var(--t3)">${s.auditado_por || '—'}</td>
              <td><div style="display:flex;gap:4px">${btns.join('')}</div></td>
            </tr>`;
        }).join('') || '<tr><td colspan="9" class="empty-label">Sin sesiones registradas</td></tr>';

        // Paginación
        _renderPaginacion('aud-sesiones-pag', r.total_pages, page, cargarSesiones);
    }

    function _renderPaginacion(containerId, totalPages, currentPage, fn) {
        const el = document.getElementById(containerId);
        if (!el) return;
        if (totalPages <= 1) { el.innerHTML = ''; return; }
        let html = '<div class="pag">';
        if (currentPage > 1) html += `<button class="pag-btn" onclick="Auditorias._go('${containerId}',${currentPage - 1})">‹</button>`;
        for (let i = 1; i <= totalPages; i++) {
            html += `<button class="pag-btn ${i === currentPage ? 'on' : ''}" onclick="Auditorias._go('${containerId}',${i})">${i}</button>`;
        }
        if (currentPage < totalPages) html += `<button class="pag-btn" onclick="Auditorias._go('${containerId}',${currentPage + 1})">›</button>`;
        html += '</div>';
        el.innerHTML = html;
        el._fn = fn;
    }

    function _go(containerId, page) {
        const el = document.getElementById(containerId);
        if (el && el._fn) el._fn(page);
    }

    // ─────────────────────────────────────────────────────────────────────
    // CREAR SESIÓN
    // ─────────────────────────────────────────────────────────────────────

    async function iniciarSesionDesdePlan(planId, tipo) {
        const auditado_por = await _solicitarNombreAuditor(tipo);
        if (!auditado_por) return;
        _notify('Creando sesión...', 'info');
        const r = await api(API + '/sesiones', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ tipo, plan_id: planId, auditado_por }),
        });

        if (r.ok) {
            _notify(`Sesión #${r.sesion_id} creada — ${r.total_items} ítems a contar`, 'success');
            await Promise.all([cargarSesiones(1), cargarEstadisticas(), cargarPlanes()]);
            abrirConteo(r.sesion_id);
        } else {
            _notify(r.msg || 'Error al crear sesión', 'error');
        }
    }

    async function iniciarDesdePanel(tipo) {
        // Busca el plan activo del tipo indicado para iniciar
        const r = await api(API + '/planes');
        if (!r.ok) return;
        const plan = r.items.find(p => p.tipo === tipo && p.activo);
        if (!plan) {
            _notify(`No hay plan activo para tipo "${tipo}"`, 'error');
            return;
        }
        await iniciarSesionDesdePlan(plan.id, tipo);
    }

    async function crearSesionSpot() {
        const auditado_por = await _solicitarNombreAuditor('spot');
        if (!auditado_por) return;
        const categoria = document.getElementById('aud-spot-categoria') && document.getElementById('aud-spot-categoria').value || '';
        const clase     = document.getElementById('aud-spot-clase')     && document.getElementById('aud-spot-clase').value || '';
        _notify('Creando sesión spot...', 'info');
        const r = await api(API + '/sesiones', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                tipo: 'spot',
                auditado_por,
                filtro_categoria: categoria || null,
                filtro_clase: clase || null,
            }),
        });

        if (r.ok) {
            _notify(`Sesión spot #${r.sesion_id} — ${r.total_items} ítems`, 'success');
            await Promise.all([cargarSesiones(1), cargarEstadisticas()]);
            abrirConteo(r.sesion_id);
        } else {
            _notify(r.msg || 'Error', 'error');
        }
    }

    // ─────────────────────────────────────────────────────────────────────
    // MODAL DE CONTEO
    // ─────────────────────────────────────────────────────────────────────

    async function abrirConteo(sesionId) {
        _sesionActivaId = sesionId;
        const r = await api(API + '/sesiones/' + sesionId);
        if (!r.ok) { _notify('Error cargando sesión', 'error'); return; }
        _sesionActivaItems = Array.isArray(r.items) ? r.items : [];

        const modal = document.getElementById('modal-aud-conteo');
        if (!modal) return;

        // Header
        const s = r.sesion;
        document.getElementById('maud-titulo').textContent =
            `Sesión #${s.id} — ${s.tipo} ${s.semana_iso || s.mes_periodo || ''} ${s.ciclo_numero ? '· Ciclo ' + s.ciclo_numero : ''}`;
        document.getElementById('maud-prog').textContent =
            `${s.items_contados}/${s.total_items} contados · ${s.items_con_diferencia || 0} diferencias`;

        // Body tabla
        const tbody = document.getElementById('maud-conteo-tbody');
        if (tbody) {
            tbody.innerHTML = r.items.map(it => {
                const difHtml = it.diferencia !== null && it.diferencia !== undefined
                    ? `<span style="color:${it.diferencia < 0 ? '#e74c3c' : it.diferencia > 0 ? '#e67e22' : '#27ae60'};font-weight:600">
                         ${it.diferencia > 0 ? '+' : ''}${_fmt(it.diferencia)}
                       </span>`
                    : '—';
                return `<tr id="aud-fila-${it.item_sku}">
                  <td>${_badgeABC(it.clase_abc)}</td>
                  <td style="font-family:monospace;font-size:11px">${it.item_sku}</td>
                  <td style="font-size:12px">${it.item_nombre || '—'}</td>
                  <td style="text-align:right;font-weight:600">${_fmt(it.stock_sistema)}</td>
                  <td>
                    <input type="number" min="0" step="0.01"
                      class="fi" style="width:80px;text-align:right"
                      value="${it.stock_contado !== null && it.stock_contado !== undefined ? it.stock_contado : ''}"
                      placeholder="..."
                      ${it.ajustado ? 'disabled title="Ya ajustado"' : ''}
                      data-sku="${it.item_sku}"
                      onchange="Auditorias._onConteoChange('${it.item_sku}', this.value)" />
                  </td>
                  <td id="aud-dif-${it.item_sku}" style="text-align:right">${difHtml}</td>
                  <td style="text-align:center;color:#27ae60">${it.ajustado ? '✓' : ''}</td>
                </tr>`;
            }).join('') || '<tr><td colspan="7" class="empty-label">Sin ítems</td></tr>';
        }

        _abrirModal('modal-aud-conteo');
    }

    async function _onConteoChange(sku, valor) {
        if (_sesionActivaId === null) return;
        const r = await api(API + '/sesiones/' + _sesionActivaId + '/conteo', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                sku,
                stock_contado: parseFloat(valor),
                contado_por: 'usuario',
            }),
        });

        if (r.ok) {
            const cel = document.getElementById(`aud-dif-${sku}`);
            if (cel) {
                const d = r.diferencia;
                cel.innerHTML = `<span style="color:${d < 0 ? '#e74c3c' : d > 0 ? '#e67e22' : '#27ae60'};font-weight:600">${d > 0 ? '+' : ''}${_fmt(d)}</span>`;
            }
            // Actualizar header de progreso
            const rSes = await api(API + '/sesiones/' + _sesionActivaId);
            if (rSes.ok) {
                const s = rSes.sesion;
                const el = document.getElementById('maud-prog');
                if (el) el.textContent = `${s.items_contados}/${s.total_items} contados · ${s.items_con_diferencia || 0} diferencias`;
            }
        } else {
            _notify(r.msg, 'error');
        }
    }

    function cerrarConteo() {
        _cerrarModal('modal-aud-conteo');
        _sesionActivaId = null;
        _sesionActivaItems = [];
        const f = document.getElementById('maud-file-csv');
        if (f) f.value = '';
        cargarSesiones(_paginaSesiones);
        cargarEstadisticas();
    }

    // ─────────────────────────────────────────────────────────────────────
    // CARGA/DESCARGA CSV DE CONTEO
    // ─────────────────────────────────────────────────────────────────────

    function descargarPlantillaSesionActiva() {
        if (_sesionActivaId === null) {
            _notify('Abre una sesión para exportar la plantilla', 'warn');
            return;
        }
        if (!_sesionActivaItems.length) {
            _notify('La sesión no tiene ítems para exportar', 'warn');
            return;
        }

        const encabezado = ['sku', 'nombre', 'stock_sistema', 'stock_contado', 'contado_por', 'observaciones'];
        const lineas = [encabezado.join(';')];
        for (const it of _sesionActivaItems) {
            const fila = [
                it.item_sku,
                it.item_nombre || '',
                Number(it.stock_sistema || 0).toFixed(2),
                it.stock_contado ?? '',
                it.contado_por || '',
                it.observaciones || ''
            ];
            lineas.push(fila.map(_escapeCsv).join(';'));
        }

        const csv = '\ufeff' + lineas.join('\n');
        const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `auditoria_sesion_${_sesionActivaId}_plantilla.csv`;
        document.body.appendChild(a);
        a.click();
        a.remove();
        URL.revokeObjectURL(url);
        _notify('Plantilla CSV descargada', 'success');
    }

    function abrirCargaConteoSesionActiva() {
        if (_sesionActivaId === null) {
            _notify('Abre una sesión para importar conteo', 'warn');
            return;
        }
        const f = document.getElementById('maud-file-csv');
        if (!f) {
            _notify('No se encontró el selector de archivo', 'error');
            return;
        }
        f.value = '';
        f.click();
    }

    async function cargarConteoDesdeArchivo(event) {
        const file = event?.target?.files?.[0];
        if (!file) return;
        if (_sesionActivaId === null) {
            _notify('No hay sesión activa para importar', 'warn');
            return;
        }

        const text = await file.text();
        const rowsRaw = text.split(/\r?\n/).filter(r => r.trim());
        if (rowsRaw.length < 2) {
            _notify('El archivo no contiene datos', 'error');
            return;
        }

        const sep = (rowsRaw[0].split(';').length >= rowsRaw[0].split(',').length) ? ';' : ',';
        const headers = _parseCsvLine(rowsRaw[0], sep).map(_normalizarHeader);
        const skuIdx = headers.indexOf('sku');
        const contadoIdx = headers.indexOf('stock_contado');
        const contadoPorIdx = headers.indexOf('contado_por');
        const obsIdx = headers.indexOf('observaciones');

        if (skuIdx < 0 || contadoIdx < 0) {
            _notify('CSV inválido: requiere columnas sku y stock_contado', 'error');
            return;
        }

        const validSkus = new Set(_sesionActivaItems.map(it => String(it.item_sku)));
        const items = [];
        const errores = [];

        for (let i = 1; i < rowsRaw.length; i++) {
            const cols = _parseCsvLine(rowsRaw[i], sep);
            const sku = (cols[skuIdx] || '').trim();
            const contadoRaw = (cols[contadoIdx] || '').trim().replace(',', '.');
            if (!sku && !contadoRaw) continue;
            if (!sku) {
                errores.push(`Fila ${i + 1}: SKU vacío`);
                continue;
            }
            if (!validSkus.has(sku)) {
                errores.push(`Fila ${i + 1}: SKU ${sku} no pertenece a la sesión`);
                continue;
            }
            const contado = Number(contadoRaw);
            if (!Number.isFinite(contado) || contado < 0) {
                errores.push(`Fila ${i + 1}: stock_contado inválido para SKU ${sku}`);
                continue;
            }

            items.push({
                sku,
                stock_contado: contado,
                contado_por: (cols[contadoPorIdx] || '').trim() || 'usuario',
                observaciones: (cols[obsIdx] || '').trim()
            });
        }

        if (!items.length) {
            _notify(`No se importaron filas válidas. ${errores.slice(0, 2).join(' | ')}`, 'error');
            return;
        }

        _notify(`Subiendo ${items.length} conteos...`, 'info');
        const r = await api(API + '/sesiones/' + _sesionActivaId + '/conteo-lote', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ items })
        });

        if (!r || !r.ok) {
            _notify(r?.msg || 'Error al subir conteo masivo', 'error');
            return;
        }

        const analisis = r.analisis || {};
        const resumen = `Procesados: ${r.procesados || 0} · Avance: ${analisis.avance_pct || 0}% · Diferencias: ${analisis.items_con_diferencia || 0}`;
        if ((r.errores || []).length || errores.length) {
            _notify(`${resumen} · Errores: ${(r.errores || []).length + errores.length}`, 'warn');
        } else {
            _notify(resumen, 'success');
        }

        await Promise.all([
            abrirConteo(_sesionActivaId),
            cargarSesiones(_paginaSesiones),
            cargarEstadisticas()
        ]);
    }

    // ─────────────────────────────────────────────────────────────────────
    // APLICAR AJUSTES
    // ─────────────────────────────────────────────────────────────────────

    async function aplicarAjustes(sesionId) {
        const ok = typeof showConfirmModal === 'function'
            ? await showConfirmModal({
                title: 'Aplicar ajustes de auditoría',
                message: `Se actualizará el stock físico con todas las diferencias pendientes de la sesión #${sesionId}.`,
                confirmText: 'Aplicar ajustes',
                cancelText: 'Cancelar',
                variant: 'danger',
            })
            : true;
        if (!ok) return;

        _notify('Aplicando ajustes...', 'info');
        const r = await api(API + '/sesiones/' + sesionId + '/aplicar-ajustes', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ aplicado_por: 'usuario' }),
        });

        if (r.ok) {
            _notify(`✅ ${r.ajustados} ajuste(s) aplicados al inventario`, 'success');
            await Promise.all([cargarSesiones(_paginaSesiones), cargarEstadisticas()]);
            if (_sesionActivaId === sesionId) cerrarConteo();
        } else {
            _notify(r.msg || 'Error al aplicar ajustes', 'error');
        }
    }

    function aplicarAjustesSesionActiva() {
        if (_sesionActivaId === null) {
            _notify('No hay una sesión activa abierta para ajustar', 'warn');
            return;
        }
        return aplicarAjustes(_sesionActivaId);
    }

    async function cancelarSesion(sesionId) {
        const ok = typeof showConfirmModal === 'function'
            ? await showConfirmModal({
                title: 'Cancelar sesión',
                message: `La sesión #${sesionId} quedará cancelada y no podrá seguir contándose.`,
                confirmText: 'Cancelar sesión',
                cancelText: 'Volver',
                variant: 'danger',
            })
            : true;
        if (!ok) return;
        const r = await api(API + '/sesiones/' + sesionId + '/estado', {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ estado: 'cancelada' }),
        });
        if (r.ok) {
            _notify('Sesión cancelada', 'info');
            cargarSesiones(_paginaSesiones);
        } else {
            _notify(r.msg, 'error');
        }
    }

    // ─────────────────────────────────────────────────────────────────────
    // CLASIFICACIÓN ABC
    // ─────────────────────────────────────────────────────────────────────

    async function cargarTablaABC(page = 1) {
        _paginaABC = page;
        const clase  = document.getElementById('aud-abc-filtro-clase')  && document.getElementById('aud-abc-filtro-clase').value  || '';
        const buscar = document.getElementById('aud-abc-filtro-buscar') && document.getElementById('aud-abc-filtro-buscar').value || '';
        const params = new URLSearchParams({ page, per_page: 25 });
        if (clase)  params.set('clase', clase);
        if (buscar) params.set('search', buscar);

        const r = await api(API + '/clasificacion-abc?' + params).catch(() => null);
        if (!r || !r.ok) return;

        const tbody = document.getElementById('aud-abc-tbody');
        if (!tbody) return;

        tbody.innerHTML = r.items.map(it => `
            <tr>
              <td style="font-family:monospace;font-size:11px">${it.item_sku}</td>
              <td style="font-size:12px">${it.nombre || '—'}</td>
              <td>${_badgeABC(it.clase)}</td>
              <td style="text-align:right">$${_fmt(it.valor_anual)}</td>
              <td style="text-align:right">${_fmt(it.pct_acumulado)}%</td>
              <td style="text-align:right">${it.frecuencia_conteo_dias}d</td>
              <td style="font-size:10px;color:var(--t3)">${it.ultimo_conteo || 'nunca'}</td>
              <td style="font-family:monospace;font-size:10px;color:${it.vencido ? '#e74c3c' : 'var(--t3)'}">
                ${it.proximo_conteo || '—'} ${it.vencido ? '⚠️' : ''}
              </td>
              <td style="text-align:right">${_fmt(it.stock_actual, 0)}</td>
            </tr>`).join('') || '<tr><td colspan="9" class="empty-label">Sin clasificación ABC todavía. Usa Recalcular ABC para generarla.</td></tr>';

        _renderPaginacion('aud-abc-pag', r.total_pages, page, cargarTablaABC);
    }

    async function recalcularABC() {
        const ok = typeof showConfirmModal === 'function'
            ? await showConfirmModal({
                title: 'Recalcular clasificación ABC',
                message: 'Se volverá a calcular la prioridad ABC de todo el inventario usando el historial de consumo.',
                confirmText: 'Recalcular',
                cancelText: 'Cancelar',
            })
            : true;
        if (!ok) return;
        _notify('Recalculando...', 'info');
        const r = await api(API + '/recalcular-abc', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({}),
        });

        if (r.ok) {
            const res = r.resultado;
            _notify(`ABC actualizado — A:${res.A} B:${res.B} C:${res.C}`, 'success');
            await Promise.all([cargarTablaABC(1), cargarEstadisticas()]);
        } else {
            _notify(r.msg || 'Error al recalcular', 'error');
        }
    }

    // ─────────────────────────────────────────────────────────────────────
    // MODAL NUEVO PLAN
    // ─────────────────────────────────────────────────────────────────────

    function abrirModalNuevoPlan() {
        _abrirModal('modal-aud-nuevo-plan');
    }

    function cerrarModalNuevoPlan() {
        _cerrarModal('modal-aud-nuevo-plan');
    }

    async function guardarNuevoPlan() {
        const nombre = (document.getElementById('np-nombre') && document.getElementById('np-nombre').value || '').trim();
        const tipo   = document.getElementById('np-tipo')    && document.getElementById('np-tipo').value    || 'semanal';
        const ciclos = parseInt(document.getElementById('np-ciclos') && document.getElementById('np-ciclos').value || '4');
        const fecha  = document.getElementById('np-fecha')   && document.getElementById('np-fecha').value   || null;
        const cat    = document.getElementById('np-cat')     && document.getElementById('np-cat').value     || null;
        const clase  = document.getElementById('np-clase')   && document.getElementById('np-clase').value   || null;

        if (!nombre) { _notify('El nombre es requerido', 'error'); return; }

        await crearPlan({
            nombre, tipo,
            total_ciclos: tipo === 'rotativo' ? ciclos : 1,
            filtro_categoria: cat || null,
            filtro_clase: clase || null,
            fecha_proxima: fecha || null,
            creado_por: 'usuario',
        });
        cerrarModalNuevoPlan();
    }

    // ─────────────────────────────────────────────────────────────────────
    // DESCARGAR REPORTE
    // ─────────────────────────────────────────────────────────────────────

    function descargarReporte(sesionId) {
        _notify('Abriendo reporte...', 'info');
        const reportUrl = API + '/sesiones/' + sesionId + '/reporte-html';
        window.open(reportUrl, '_blank');
    }

    // ─────────────────────────────────────────────────────────────────────
    // API PÚBLICA
    // ─────────────────────────────────────────────────────────────────────

    return {
        init,
        ensureInit,
        cargarEstadisticas,
        cargarSesiones,
        cargarPlanes,
        togglePlan,
        iniciarSesionDesdePlan,
        iniciarDesdePanel,
        crearSesionSpot,
        abrirConteo,
        cerrarConteo,
        _onConteoChange,
        aplicarAjustes,
        cancelarSesion,
        cargarTablaABC,
        recalcularABC,
        abrirModalNuevoPlan,
        cerrarModalNuevoPlan,
        guardarNuevoPlan,
        aplicarAjustesSesionActiva,
        descargarPlantillaSesionActiva,
        abrirCargaConteoSesionActiva,
        cargarConteoDesdeArchivo,
        _go,
        descargarReporte,
    };
})();

    window.Auditorias = Auditorias;
