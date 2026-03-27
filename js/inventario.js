// Función de búsqueda que resetea la página a 1
function searchI() {
  iS.p = 1;
  lI();
}

function toggleActionMenu(elementId) {
  const menu = $(elementId);
  if (!menu) return;
  
  // Cerrar otros menús abiertos
  document.querySelectorAll('.inv-action-menu').forEach(m => {
    if (m.id !== elementId) m.style.display = 'none';
  });
  
  // Toggle actual
  menu.style.display = menu.style.display === 'none' ? 'block' : 'none';
}

// Cerrar menus al hacer click fuera
document.addEventListener('click', function(e) {
  if (!e.target.closest('.inv-action-menu') && !e.target.closest('[title="Opciones"]')) {
    document.querySelectorAll('.inv-action-menu').forEach(m => m.style.display = 'none');
  }
});

async function lI() {
  const p = new URLSearchParams({
    page: iS.p,
    per_page: 50,
    search: $('inv-s').value.trim(),
    categoria: $('inv-cat').value,
    estado: $('inv-est').value,
    sort: iS.s,
    dir: iS.d
  });
  const d = await api('/api/items?' + p);
  if (!d) return;

  const cs = $('inv-cat');
  if (d.categorias.length > 0 && cs.options.length <= 1) {
    d.categorias.forEach((c) => {
      const o = document.createElement('option');
      o.value = c;
      o.textContent = c;
      cs.appendChild(o);
    });
  }

  $('cl').innerHTML = d.categorias.map((c) => `<option value="${c}">`).join('');
  $('inv-c').textContent = fm(d.total) + ' productos';
  $('inv-b').innerHTML = d.items.length === 0
    ? '<tr><td colspan="10"><div class="empty"><div class="empty-i">📦</div><div class="empty-t">Sin resultados</div></div></td></tr>'
    : d.items.map((p) => {
      let st, sc, pc;
      if (p.stock <= 0) {
        st = 'Sin Stock'; sc = 'b-no'; pc = 0;
      } else if (p.stock <= 10) {
        st = 'Critico'; sc = 'b-no'; pc = Math.max(5, p.stock * 3);
      } else if (p.stock <= 50) {
        st = 'Bajo'; sc = 'b-wa'; pc = Math.min(60, p.stock);
      } else {
        st = 'Normal'; sc = 'b-ok'; pc = Math.min(100, p.stock / 5);
      }
      const cl = pc < 20 ? 'var(--no)' : pc < 50 ? 'var(--wa)' : 'var(--ok)';
      const dropId = `act-${p.sku.replace(/[^a-zA-Z0-9]/g, '_')}`;
      return `<tr><td class="m" style="font-size:10px">${p.sku}</td><td style="font-weight:500;max-width:380px;white-space:normal;word-wrap:break-word">${p.nombre || '-'}</td><td><span class="badge b-in">${p.categoria || '-'}</span></td><td class="m" style="font-weight:700">${fm(p.stock)}</td><td style="color:var(--t3);font-size:10px">${p.unidad || '-'}</td><td><div class="sbar"><div class="sfill" style="width:${pc}%;background:${cl}"></div></div><span class="badge ${sc}" style="margin-top:2px">${st}</span></td><td class="m">${fp(p.precio)}</td><td style="font-size:9px;color:var(--t3);max-width:70px;overflow:hidden;text-overflow:ellipsis">${p.proveedor || '-'}</td><td style="font-size:9px;color:var(--t3);max-width:50px;overflow:hidden;text-overflow:ellipsis">${p.ubicacion || '-'}</td><td><div style="position:relative"><button class="bi" title="Opciones" onclick="toggleActionMenu('${dropId}')">⋮</button><div id="${dropId}" class="inv-action-menu" style="display:none;position:absolute;top:24px;right:0;background:var(--bg2);border:1px solid var(--bd);border-radius:6px;z-index:1000;min-width:140px;box-shadow:0 4px 8px rgba(0,0,0,0.15)"><div style="padding:6px 0"><button class="inv-action-item" onclick="openFicha('${p.sku}');toggleActionMenu('${dropId}')">◉ Ficha</button><button class="inv-action-item" onclick="openKardex('${p.sku}','${(p.nombre || '').replace(/'/g, "\\'")}');toggleActionMenu('${dropId}')">K Kardex</button><button class="inv-action-item" onclick="editItem('${p.sku}');toggleActionMenu('${dropId}')">✎ Editar</button><button class="inv-action-item" style="color:var(--no)" onclick="delItem('${p.sku}');toggleActionMenu('${dropId}')">✕ Eliminar</button></div></div></div></td></tr>`;
    }).join('');

  rP('inv-p', d, iS, lI);
}

function sI(k) {
  if (iS.s === k) iS.d = iS.d === 'asc' ? 'desc' : 'asc';
  else { iS.s = k; iS.d = 'asc'; }
  iS.p = 1;
  lI();
}

async function openNewItem(fromIngreso) {
  $('mi-t').textContent = 'Nuevo Producto';
  $('mi-esku').value = '';
  $('mi-sku').value = '';
  $('mi-nom').value = '';
  $('mi-cat').value = '';
  $('mi-stk').value = '0';
  $('mi-pre').value = '0';
  $('mi-stk-min').value = '0';
  $('mi-stk-max').value = '0';
  $('mi-ubi').value = '';
  $('mi-prv').value = '';
  $('mi-sku').removeAttribute('readonly');
  // hide delete button when creating new item
  const delBtn = $('mi-del'); if (delBtn) delBtn.style.display = 'none';
  try {
    const res = await api('/api/items/suggest-sku?prefix=NCI&_=' + Date.now());
    if (res && res.ok && res.sku) $('mi-sku').value = res.sku;
  } catch (e) {}
  window._fromIngreso = !!fromIngreso;
  window._returnToIngresoModal = !!fromIngreso && !!($('m-ing') && $('m-ing').classList.contains('on'));
  if (window._returnToIngresoModal) cM('m-ing');
  oM('m-item');
}

function closeItemModal() {
  cM('m-item');
  if (window._returnToIngresoModal && $('m-ing')) {
    oM('m-ing');
  }
  window._returnToIngresoModal = false;
}

async function editItem(sku) {
  const d = await api('/api/items?search=' + encodeURIComponent(sku) + '&per_page=1');
  if (!d || !d.items.length) return;
  const p = d.items[0];
  $('mi-t').textContent = 'Editar: ' + p.sku;
  $('mi-esku').value = p.sku;
  $('mi-sku').value = p.sku;
  $('mi-sku').setAttribute('readonly', true);
  $('mi-nom').value = p.nombre || '';
  $('mi-cat').value = p.categoria || '';
  $('mi-uni').value = p.unidad || 'Unidad';
  $('mi-stk').value = p.stock;
  $('mi-stk').setAttribute('readonly', true);
  $('mi-stk').title = 'El stock se corrige desde Auditorías';
  $('mi-pre').value = p.precio;
  $('mi-stk-min').value = p.stock_min || '0';
  $('mi-stk-max').value = p.stock_max || '0';
  $('mi-ubi').value = p.ubicacion || '';
  $('mi-prv').value = p.proveedor || '';
  // show delete button when editing
  const delBtn = $('mi-del'); if (delBtn) delBtn.style.display = 'inline-block';
  window._editingSku = p.sku;
  oM('m-item');
}

async function saveItem() {
  const es = $('mi-esku').value;
  const d = {
    sku: $('mi-sku').value.trim(),
    nombre: $('mi-nom').value.trim(),
    categoria: $('mi-cat').value.trim(),
    unidad: $('mi-uni').value,
    stock: parseFloat($('mi-stk').value) || 0,
    precio: parseFloat($('mi-pre').value) || 0,
    stock_min: parseFloat($('mi-stk-min').value) || 0,
    stock_max: parseFloat($('mi-stk-max').value) || 0,
    ubicacion: $('mi-ubi').value.trim(),
    proveedor: $('mi-prv').value.trim()
  };

  if (es) delete d.stock;
  if (!d.sku || !d.nombre) return toast('SKU y Nombre obligatorios', 'err');

  let r;
  if (es) r = await api('/api/items/' + encodeURIComponent(es), { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(d) });
  else r = await api('/api/items', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(d) });

  if (r && r.ok) {
    toast(r.msg);
    cM('m-item');
    lI();
    if (window._fromIngreso) {
      window._fromIngreso = false;
      if ($('ni-asku')) {
        $('ni-asku').value = d.sku + ' - ' + d.nombre;
        $('ni-add-v').value = d.sku;
        $('ni-add-n').value = d.nombre;
        $('ni-add-u').value = d.unidad || '';
        $('ni-info').innerHTML = '<span style="color:var(--in)">Nuevo insumo creado</span>';
      }
    }
    if (window._returnToIngresoModal && $('m-ing')) oM('m-ing');
    window._returnToIngresoModal = false;
  } else if (r) {
    if (r.suggested_sku && $('mi-sku')) {
      $('mi-sku').value = r.suggested_sku;
      $('mi-sku').focus();
      $('mi-sku').select();
    }
    toast(r.msg, 'err');
  }
}

async function delItem(sku) {
  if (!sku || sku.toLowerCase()==='null' || sku.toLowerCase()==='none') {
    toast('SKU inválido', 'err');
    return;
  }
  if (!confirm('Eliminar ' + sku + '?')) return;
  const r = await api('/api/items/' + encodeURIComponent(sku), { method: 'DELETE' });
  if (r && r.ok) {
    toast('Eliminado');
    lI();
  } else if (r) {
    toast(r.msg, 'err');
  }
}

let currentFichaSku = null;
let fichaConsumosCache = [];

function buildFichaPriceSparkline(ingresos) {
  // Mantener datos completos: fecha + precio, ordenados de antiguo a reciente
  const datosValidos = (ingresos || [])
    .slice()
    .reverse()
    .map((row) => ({
      fecha: row.fecha || '?',
      precio: Number(row.precio || 0)
    }))
    .filter((d) => Number.isFinite(d.precio));

  if (datosValidos.length < 2) {
    return '<div class="ficha-empty mb16">Sin datos suficientes para tendencia de precios</div>';
  }

  const serie = datosValidos.map(d => d.precio);
  const width = 260;
  const height = 56;
  const pad = 6;
  const min = Math.min(...serie);
  const max = Math.max(...serie);
  const range = max - min || 1;

  // ID único para este gráfico
  const chartId = 'sparkline-' + Math.random().toString(36).substr(2, 9);

  // Puntos del gráfico con coordenadas
  const pointsData = serie.map((value, index) => {
    const x = pad + (index * (width - pad * 2)) / Math.max(1, serie.length - 1);
    const y = height - pad - ((value - min) / range) * (height - pad * 2);
    return { x: parseFloat(x.toFixed(1)), y: parseFloat(y.toFixed(1)), value, index };
  });

  const pointsPath = pointsData.map(p => `${p.x},${p.y}`).join(' ');

  // Comparar precio más reciente vs más antiguo para mostrar TENDENCIA GENERAL
  const priceRecent = serie[serie.length - 1];
  const priceOldest = serie[0];
  const delta = priceRecent - priceOldest;
  const trendColor = delta > 0 ? 'var(--no)' : delta < 0 ? 'var(--ok)' : 'var(--t2)';
  const trendSign = delta > 0 ? '+' : '';
  const trendLabel = delta > 0 ? 'Alza' : delta < 0 ? 'Baja' : 'Estable';

  // Generar circulos para cada punto con tooltip
  const circles = pointsData.map((p, idx) => {
    const fecha = datosValidos[idx].fecha;
    const titulo = `${fecha}: ${fp(p.value)}`;
    return `<circle cx="${p.x}" cy="${p.y}" r="3" fill="var(--ac)" opacity="0.6" style="cursor:pointer;transition:all 0.2s" onmouseover="this.setAttribute('r','5');this.setAttribute('opacity','1');document.getElementById('${chartId}-tt').innerHTML='${titulo}';document.getElementById('${chartId}-tt').style.display='block'" onmouseout="this.setAttribute('r','3');this.setAttribute('opacity','0.6');document.getElementById('${chartId}-tt').style.display='none'"></circle>`;
  }).join('');

  return `
    <div class="mb16" style="border:1px solid var(--bd);border-radius:8px;padding:10px;background:var(--bg2)">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px">
        <div style="font-size:11px;color:var(--t2)">Tendencia precio (últimos ingresos)</div>
        <div style="font-size:10px;color:${trendColor};font-weight:600">${trendLabel}: ${trendSign}${fp(delta)}</div>
      </div>
      <div style="position:relative;margin-bottom:4px">
        <svg width="100%" viewBox="0 0 ${width} ${height}" preserveAspectRatio="none" style="height:56px;display:block">
          <polyline points="${pointsPath}" fill="none" stroke="var(--ac)" stroke-width="2" stroke-linejoin="round" stroke-linecap="round"></polyline>
          ${circles}
        </svg>
        <div id="${chartId}-tt" style="display:none;position:absolute;bottom:60px;left:50%;transform:translateX(-50%);background:var(--bd);color:var(--t1);padding:4px 8px;border-radius:4px;font-size:10px;white-space:nowrap;z-index:10;box-shadow:0 2px 8px rgba(0,0,0,0.2)"></div>
      </div>
      <div style="display:flex;justify-content:space-between;font-size:10px;color:var(--t3)">
        <span>Mín: ${fp(min)}</span>
        <span style="font-size:9px;color:var(--t4)">Pasa el mouse sobre los puntos</span>
        <span>Máx: ${fp(max)}</span>
      </div>
    </div>`;
}

async function openFicha(sku) {
  const d = await api('/api/items/' + encodeURIComponent(sku) + '/ficha');
  if (!d || !d.ok) return toast('No encontrado', 'err');
  const p = d.data;
  currentFichaSku = sku;
  fichaConsumosCache = p.ultimos_consumos || [];
  $('f-sku').textContent = p.sku;
  $('f-nombre').textContent = p.nombre || 'Sin nombre';
  $('f-cat').textContent = [p.categoria_nombre, p.subcategoria_nombre, p.unidad_medida_nombre].filter(Boolean).join(' · ');

  let html = `<div class="f-stat"><div class="f-stat-card"><div class="f-stat-v" style="color:var(--ac)">${fm(p.stock_actual || 0)}</div><div class="f-stat-l">Stock Actual</div></div><div class="f-stat-card"><div class="f-stat-v">${fp(p.precio_unitario_promedio)}</div><div class="f-stat-l">Precio Promedio</div></div><div class="f-stat-card"><div class="f-stat-v" style="color:var(--ok)">${fm(p.total_ingresado)}</div><div class="f-stat-l">Total Ingresado (${p.total_ingresos_count} mov.)</div></div><div class="f-stat-card"><div class="f-stat-v" style="color:var(--no)">${fm(p.total_consumido)}</div><div class="f-stat-l">Total Consumido (${p.total_consumos_count} reg.)</div></div></div>`;

  const vp = p.variacion_precio || {};
  let variacionDetail = '<strong>-</strong>';
  if (vp.tiene_variacion) {
    const deltaAbs = Number(vp.delta_abs || 0);
    const deltaPct = Number(vp.delta_pct || 0);
    const isUp = deltaAbs > 0;
    const isDown = deltaAbs < 0;
    const color = isUp ? 'var(--no)' : (isDown ? 'var(--ok)' : 'var(--t2)');
    const sign = deltaAbs > 0 ? '+' : '';
    const signPct = deltaPct > 0 ? '+' : '';
    variacionDetail = `<strong style="color:${color}">${sign}${fp(deltaAbs)} (${signPct}${deltaPct.toFixed(2)}%)</strong><div style="font-size:10px;color:var(--t3)">Actual: ${fp(vp.precio_actual || 0)} · Anterior: ${fp(vp.precio_anterior || 0)}</div>`;
  } else if (vp.precio_actual != null) {
    variacionDetail = `<strong>${fp(vp.precio_actual || 0)}</strong><div style="font-size:10px;color:var(--t3)">Sin precio anterior para comparar</div>`;
  }

  html += `<div class="ficha-meta mb16"><div><span class="ficha-meta-l">Último proveedor</span><strong>${p.proveedor_ultimo_nombre || p.proveedor_principal_nombre || '-'}</strong></div><div><span class="ficha-meta-l">Ubicación</span><strong>${p.ubicacion_nombre || '-'}</strong></div><div><span class="ficha-meta-l">Variación precio insumo</span>${variacionDetail}</div></div>`;

  html += buildFichaPriceSparkline(p.ultimos_ingresos || []);

  if ((p.proveedores_compra_count || 0) > 1) {
    html += '<div class="sec">Proveedores de Compra</div>';
    html += `<div class="ficha-list mb16">${(p.proveedores_compra || []).map((r) => `<div class="ficha-item"><div class="ficha-item-top"><strong>${r.proveedor || '-'}</strong><span class="badge b-in">${fm(r.compras || 0)} compra(s)</span></div><div class="ficha-item-meta"><span>Último precio: <b>${fp(r.precio_ultimo || 0)}</b></span><span>Última compra: <b>${r.fecha_ultima || '-'}</b></span></div></div>`).join('')}</div>`;
  }

  html += `<div style="margin-bottom:6px;display:flex;justify-content:space-between;align-items:center"><div class="sec" style="margin:0">Últimos Ingresos</div><button class="btn bsm bg" onclick="openNewIng('${p.sku}')">+ Reponer</button></div>`;

  const ingresosVista = (p.ultimos_ingresos || []).slice(0, 5);
  if (ingresosVista.length) {
    html += `<div class="ficha-list mb16">${ingresosVista.map((r) => `<div class="ficha-item"><div class="ficha-item-top"><strong>${r.fecha || '-'}</strong><span class="badge b-ok">+${fm(r.cantidad)}</span></div><div class="ficha-item-meta"><span>Precio: <b>${fp(r.precio)}</b></span><span>Proveedor: <b>${r.proveedor || '-'}</b></span><span>Doc: <b>${r.factura || r.guia || '-'}</b></span></div></div>`).join('')}</div>`;
  } else {
    html += '<div class="ficha-empty mb16">Sin ingresos</div>';
  }

  html += '<div class="sec">Últimos Consumos</div>';
  const consumosVista = (p.ultimos_consumos || []).slice(0, 5);
  if (consumosVista.length) {
    html += `<div class="ficha-list mb16">${consumosVista.map((r, index) => `<div class="ficha-item"><div class="ficha-item-top"><strong>${r.fecha || 'Saldo inicial'}</strong><span class="badge b-no">-${fm(r.cantidad)}</span></div><div class="ficha-item-meta"><span>Solicitante: <b>${r.solicitante || '-'}</b></span><span>OT: <b>${r.ot || '-'}</b></span></div><div style="margin-top:8px"><button class="btn bsm bs" onclick="editFichaConsumo(${index})">Editar</button></div></div>`).join('')}</div>`;
  } else {
    html += '<div class="ficha-empty mb16">Sin consumos</div>';
  }

  html += `<button class="btn bp" style="width:100%" onclick="closeFicha();openKardex('${p.sku}','${(p.nombre || '').replace(/'/g, "\\'")}')">Ver Kardex Completo -></button>`;
  $('f-body').innerHTML = html;
  $('ficha-ov').classList.add('on');
  $('ficha-panel').classList.add('open');
}

function closeFicha() {
  currentFichaSku = null;
  fichaConsumosCache = [];
  $('ficha-ov').classList.remove('on');
  $('ficha-panel').classList.remove('open');
}


function editFichaConsumo(index) {
  const row = fichaConsumosCache[index];
  if (!row) return toast('Consumo no encontrado', 'err');
  if (typeof openConsumoEditorForRow !== 'function') return toast('Editor no disponible', 'err');
  openConsumoEditorForRow({
    rowid: row.rowid,
    source: row.source,
    sku: row.sku || currentFichaSku,
    fecha: row.fecha,
    cantidad: row.cantidad,
    solicitante: row.solicitante,
    ot_id: row.ot,
    obs: row.obs,
    stock_post: row.stock_post,
    descripcion: $('f-nombre').textContent
  });
}


function refreshOpenConsumoContexts(sku) {
  if (currentFichaSku && currentFichaSku === sku && $('ficha-ov')?.classList.contains('on')) {
    openFicha(sku);
  }
  if (typeof kxS !== 'undefined' && kxS.sku === sku && $('m-kardex')?.classList.contains('on') && typeof loadKardex === 'function') {
    loadKardex();
  }
}


window.refreshOpenConsumoContexts = refreshOpenConsumoContexts;