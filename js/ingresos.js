// Función de búsqueda que resetea la página a 1
function searchIG() {
  igS.p = 1;
  lIG();
}

const igExpandedGroups = new Set();
let igRenderedGroups = [];
const IG_MAX_OPEN_DETAILS = 2;
const igExpandedOrder = [];
let ingresoPdfPreviewItems = [];
let ingresoProviderHints = [];
const IVA_RATE = 0.19;
let isEditingIngresoDocument = false;
let currentIngresoDocumentKey = null;

function _safeText(v) {
  return h(v == null ? '' : String(v));
}

function calcIvaFromNet(net) {
  const value = Number(net || 0);
  return r2(value * IVA_RATE);
}

function calcTotalWithIva(net) {
  const value = Number(net || 0);
  return r2(value + calcIvaFromNet(value));
}

function calcIngresoItemNet(item) {
  const qty = Number(item?.cantidad || 0);
  const price = Number(item?.precio || 0);
  const discount = Number(item?.descuento_pct || 0);
  const net = qty * price * (1 - discount / 100);
  return r2(net);
}

function _normalizeDocValue(v) {
  return (v || '').toString().trim();
}

function _resolveIngresoDocumento(row) {
  const factura = _normalizeDocValue(row.factura);
  const guia = _normalizeDocValue(row.guia);
  const oc = _normalizeDocValue(row.oc);
  if (factura) return { tipo: 'Factura', valor: factura };
  if (guia) return { tipo: 'Guía', valor: guia };
  if (oc) return { tipo: 'OC', valor: oc };
  return { tipo: 'Sin documento', valor: 'Sin documento' };
}

function _groupIngresosByDocumento(items) {
  const groupsMap = new Map();

  items.forEach((row) => {
    const proveedor = (row.proveedor || '').toString().trim() || 'Sin proveedor';
    const doc = _resolveIngresoDocumento(row);
    const groupKey = `${proveedor.toLowerCase()}__${doc.tipo.toLowerCase()}__${doc.valor.toLowerCase()}`;

    if (!groupsMap.has(groupKey)) {
      groupsMap.set(groupKey, {
        key: groupKey,
        proveedor,
        documento_tipo: doc.tipo,
        documento_valor: doc.valor,
        transportista: (row.transportista || '').toString().trim(),
        transportista_doc: (row.transportista_doc || '').toString().trim(),
        fecha: row.fecha || '-',
        items: [],
        total_cantidad: 0,
        total_monto: 0
      });
    }

    const group = groupsMap.get(groupKey);
    group.items.push(row);
    group.total_cantidad += Number(row.cantidad || 0);
    group.total_monto += Number(row.total || 0);
  });

  return Array.from(groupsMap.values());
}

function getIngresoGroupByIndex(index) {
  return igRenderedGroups[index] || null;
}

function buildIngresoGroupActionBox(index) {
  return `<div class="action-box"><button class="bi" onclick="toggleIGGroup(${index})" title="Ver documento">👁</button><button class="bi" onclick="editIngresoDocumento(${index})" title="Editar documento" style="color:var(--ac)">✎</button><button class="bi" onclick="deleteIngresoDocumento(${index})" title="Eliminar documento" style="color:var(--no)">✕</button></div>`;
}

function toggleIGGroup(index) {
  const g = igRenderedGroups[index];
  if (!g) return;

  if (igExpandedGroups.has(g.key)) {
    igExpandedGroups.delete(g.key);
    const orderIndex = igExpandedOrder.indexOf(g.key);
    if (orderIndex >= 0) igExpandedOrder.splice(orderIndex, 1);
  } else {
    if (igExpandedOrder.length >= IG_MAX_OPEN_DETAILS) {
      const oldestKey = igExpandedOrder.shift();
      if (oldestKey) igExpandedGroups.delete(oldestKey);
    }
    igExpandedGroups.add(g.key);
    igExpandedOrder.push(g.key);
  }

  renderIGGroupedRows();
}

function syncIGExpandedGroups() {
  const validKeys = new Set(igRenderedGroups.map((group) => group.key));

  Array.from(igExpandedGroups).forEach((groupKey) => {
    if (!validKeys.has(groupKey)) igExpandedGroups.delete(groupKey);
  });

  for (let index = igExpandedOrder.length - 1; index >= 0; index -= 1) {
    if (!validKeys.has(igExpandedOrder[index])) igExpandedOrder.splice(index, 1);
  }
}

function renderIGGroupedRows() {
  const body = $('ig-b');
  if (!body) return;

  if (!igRenderedGroups.length) {
    body.innerHTML = '<tr><td colspan="7"><div class="empty"><div class="empty-t">Sin ingresos</div></div></td></tr>';
    return;
  }

  body.innerHTML = igRenderedGroups.map((g, index) => {
    const expanded = igExpandedGroups.has(g.key);
    const detailRows = g.items.map((item) => `
      ${(() => {
        const itemNet = Number(item.total ?? calcIngresoItemNet(item));
        const itemIva = calcIvaFromNet(itemNet);
        const itemTotalIva = calcTotalWithIva(itemNet);
        return `<tr>
        <td class="m" style="font-size:10px">${_safeText(item.fecha || '-')}</td>
        <td class="m" style="font-size:10px">${_safeText(item.sku)}</td>
        <td style="max-width:220px;overflow:hidden;text-overflow:ellipsis" title="${_safeText(item.descripcion || '')}">${_safeText(item.descripcion) || '-'}</td>
        <td class="m" style="text-align:right;font-weight:600;color:var(--ok)">+${fm(item.cantidad || 0)}</td>
        <td class="m" style="text-align:right">${fp(item.precio || 0)}</td>
        <td class="m" style="text-align:right;font-weight:600">${fp(itemNet)}<div class="ing-iva-inline">IVA: ${fp(itemIva)} · c/IVA: ${fp(itemTotalIva)}</div></td>
        <td class="m" style="text-align:center;color:var(--t3);font-size:10px">—</td>
      </tr>`;
      })()}
      `).join('');

    return `
      <tr class="ingresos-doc-summary-row${expanded ? ' is-open' : ''}">
        <td class="m" style="font-size:10px">${_safeText(g.fecha)}</td>
        <td style="font-size:10px"><b>${_safeText(g.documento_tipo)}:</b> ${_safeText(g.documento_valor)}${g.transportista ? `<div class="co-cell-sub">Transportista: ${_safeText(g.transportista)}</div>` : ''}${g.transportista_doc ? `<div class="co-cell-sub">Doc. transp.: ${_safeText(g.transportista_doc)}</div>` : ''}</td>
        <td style="font-size:10px">${_safeText(g.proveedor)}</td>
        <td class="m" style="text-align:right">${fm(g.items.length)}</td>
        <td class="m" style="text-align:right;font-weight:600;color:var(--ok)">+${fm(g.total_cantidad)}</td>
        <td class="m" style="text-align:right;font-weight:700">${fp(g.total_monto)}</td>
        <td style="text-align:center">${buildIngresoGroupActionBox(index)}</td>
      </tr>
      ${expanded ? `<tr class="ingresos-doc-detail-host is-open"><td colspan="7" style="padding:0 0 12px 0"><div class="ingresos-doc-detail-shell"><table class="ingresos-doc-detail-table"><thead><tr><th>Fecha</th><th>SKU</th><th>Producto</th><th>Cant.</th><th>Precio</th><th>Total</th><th>Acciones</th></tr></thead><tbody>${detailRows}</tbody></table></div></td></tr>` : ''}
    `;
  }).join('');
}

async function lIG() {
  const params = { page: igS.p, per_page: 50, search: $('ig-s').value.trim(), from: $('ig-f').value, to: $('ig-t').value };
  const p = new URLSearchParams(params);
  const d = await api('/api/ingresos?' + p);
  if (!d) return;
  const ingresosPage = $('p-ingresos');
  if (document.hidden || !ingresosPage || !ingresosPage.classList.contains('on')) return;
  // update summary if provided
  if (d.sum_qty !== undefined && d.sum_total !== undefined) {
    const el = $('ig-summary');
    if (el) {
      const neto = Number(d.sum_total || 0);
      const iva = calcIvaFromNet(neto);
      const totalConIva = calcTotalWithIva(neto);
      el.textContent = `Totales ➤ Cantidad: ${fm(d.sum_qty)}  |  Neto: ${fp(neto)}  |  IVA 19%: ${fp(iva)}  |  Total c/IVA: ${fp(totalConIva)}`;
    }
  } else {
    const el = $('ig-summary');
    if (el) el.textContent = '';
  }
  igRenderedGroups = _groupIngresosByDocumento(d.items || []);
  syncIGExpandedGroups();
  renderIGGroupedRows();
  rP('ig-p', d, igS, lIG);
}

function exportIG() {
  // navigate to export URL including current filters
  const params = new URLSearchParams({ search: $('ig-s').value.trim(), from: $('ig-f').value, to: $('ig-t').value });
  location.href = '/api/export/ingresos?' + params.toString();
}


function _setIngReadOnly(flag) {
  ['ni-fecha', 'ni-prov', 'ni-fact', 'ni-guia', 'ni-oc', 'ni-trans', 'ni-trans-doc', 'ni-obs'].forEach((id) => {
    const el = $(id);
    if (!el) return;
    if (flag) el.setAttribute('readonly', 'readonly');
    else el.removeAttribute('readonly');
  });
  $('ni-add-section').style.display = flag ? 'none' : '';
}

function _setIngFooter(content) {
  const footer = $('m-ing-actions');
  if (footer) footer.innerHTML = content;
}

function _ingDefaultFooter() {
  return '<div class="ing-footer-stats"><div><div class="ing-stat-label">Items</div><div class="ing-stat-value" id="ni-ti">0</div></div><div><div class="ing-stat-label">Unidades</div><div class="ing-stat-value" id="ni-tu">0</div></div><div><div class="ing-stat-label">Neto</div><div class="ing-stat-value ing-stat-value--total" id="ni-tt">$ 0</div></div><div><div class="ing-stat-label">IVA 19%</div><div class="ing-stat-value" id="ni-iva">$ 0</div></div><div><div class="ing-stat-label">Total c/IVA</div><div class="ing-stat-value" id="ni-tt-iva">$ 0</div></div></div><div class="ing-footer-btns"><button class="btn bs" onclick="closeIng()">Cancelar</button><button class="btn bg" onclick="saveIB()">✓ Registrar Ingreso</button></div>';
}

function renderIngresoProviderDatalist(items) {
  const dl = $('pvl');
  if (!dl) return;
  dl.innerHTML = (items || []).map((it) => {
    const label = `${it.nombre}${it.usos ? ` (${it.usos})` : ''}`;
    return `<option value="${h(it.nombre)}" label="${h(label)}"></option>`;
  }).join('');
}

async function loadIngresoProviderHints(query) {
  const q = (query || '').trim();
  const d = await api('/api/ingresos/proveedores?q=' + encodeURIComponent(q));
  if (!d || !d.ok) return;
  ingresoProviderHints = d.items || [];
  renderIngresoProviderDatalist(ingresoProviderHints);
}

function onIngresoProviderInput() {
  const value = $('ni-prov')?.value || '';
  loadIngresoProviderHints(value);
}

let _ingProviderInitDone = false;
function initIngresoProviderAutocomplete() {
  const input = $('ni-prov');
  if (!input || _ingProviderInitDone) return;
  input.addEventListener('input', onIngresoProviderInput);
  input.addEventListener('focus', onIngresoProviderInput);
  _ingProviderInitDone = true;
}

function _n(value, fallback = 0) {
  const parsed = parseFloat(value);
  return Number.isFinite(parsed) ? parsed : fallback;
}

function triggerIngresoPdfPicker() {
  const input = $('ni-pdf-file');
  if (!input) return;
  input.click();
}

function _renderIngresoPdfPreview() {
  const container = $('ni-pdf-review');
  const body = $('ni-pdf-body');
  const stats = $('ni-pdf-stats');

  if (!container || !body || !stats) return;
  if (!ingresoPdfPreviewItems.length) {
    container.style.display = 'none';
    body.innerHTML = '';
    stats.textContent = '';
    return;
  }

  container.style.display = '';
  const matched = ingresoPdfPreviewItems.filter((row) => !!row.matched).length;
  stats.textContent = `Líneas: ${ingresoPdfPreviewItems.length} · Match catálogo: ${matched}`;

  body.innerHTML = ingresoPdfPreviewItems.map((row, index) => {
    const warn = (row.warnings || []).join(' · ');
    return `<tr>
      <td><input type="text" class="fi" style="width:100px" value="${h(row.sku || '')}" onchange="updateIngresoPdfRow(${index},'sku',this.value)"></td>
      <td title="${h(warn || row.raw || '')}"><input type="text" class="fi" style="width:100%" value="${h(row.item_nombre || row.descripcion || '')}" onchange="updateIngresoPdfRow(${index},'item_nombre',this.value)"></td>
      <td><input type="number" class="fi" style="width:80px;text-align:right" min="0.01" step="0.01" value="${_n(row.cantidad, 1)}" onchange="updateIngresoPdfRow(${index},'cantidad',this.value)"></td>
      <td><input type="number" class="fi" style="width:90px;text-align:right" min="0" step="0.01" value="${_n(row.precio, 0)}" onchange="updateIngresoPdfRow(${index},'precio',this.value)"></td>
      <td><input type="number" class="fi" style="width:70px;text-align:right" min="0" max="100" step="0.1" value="${_n(row.descuento_pct, 0)}" onchange="updateIngresoPdfRow(${index},'descuento_pct',this.value)"></td>
      <td class="m" style="font-size:10px;text-align:center">${Math.round(_n(row.confidence, 0) * 100)}%</td>
      <td><button class="bi" style="color:var(--no)" title="Quitar" onclick="removeIngresoPdfRow(${index})">✕</button></td>
    </tr>`;
  }).join('');
}

function updateIngresoPdfRow(index, field, value) {
  const row = ingresoPdfPreviewItems[index];
  if (!row) return;
  if (field === 'cantidad' || field === 'precio' || field === 'descuento_pct') {
    row[field] = _n(value, field === 'cantidad' ? 1 : 0);
  } else {
    row[field] = (value || '').trim();
  }
  _renderIngresoPdfPreview();
}

function removeIngresoPdfRow(index) {
  ingresoPdfPreviewItems.splice(index, 1);
  _renderIngresoPdfPreview();
}

function clearIngresoPdfPreview() {
  ingresoPdfPreviewItems = [];
  const fileInput = $('ni-pdf-file');
  const meta = $('ni-pdf-meta');
  if (fileInput) fileInput.value = '';
  if (meta) meta.textContent = 'Sin archivo cargado';
  _renderIngresoPdfPreview();
}

async function handleIngresoPdfSelected(event) {
  const input = event?.target;
  const file = input?.files?.[0];
  if (!file) return;
  if (!/\.pdf$/i.test(file.name || '')) {
    toast('Solo se permite PDF', 'err');
    clearIngresoPdfPreview();
    return;
  }

  const meta = $('ni-pdf-meta');
  if (meta) meta.textContent = `Analizando: ${file.name}`;

  const fd = new FormData();
  fd.append('pdf', file);

  const r = await api('/api/ingresos/preview-pdf', { method: 'POST', body: fd });
  if (!r) {
    if (meta) meta.textContent = 'Sin respuesta del servidor';
    toast('No hubo respuesta del servidor. Verifica que el backend esté activo y actualizado.', 'err');
    return;
  }

  if (!r.ok) {
    if (meta) meta.textContent = 'Error al analizar PDF';
    toast(r.msg || 'Error al analizar PDF. Revisa formato o estado del servidor.', 'err');
    return;
  }

  const preview = r.preview || {};
  const doc = preview.documento || {};
  const items = preview.items || [];

  if (doc.fecha && !$('ni-fecha').value) $('ni-fecha').value = doc.fecha;
  if (doc.proveedor && !$('ni-prov').value.trim()) $('ni-prov').value = doc.proveedor;
  if (doc.factura && !$('ni-fact').value.trim()) $('ni-fact').value = doc.factura;
  if (doc.guia && !$('ni-guia').value.trim()) $('ni-guia').value = doc.guia;
  if (doc.oc && !$('ni-oc').value.trim()) $('ni-oc').value = doc.oc;
  if (doc.transportista && !$('ni-trans').value.trim()) $('ni-trans').value = doc.transportista;
  if (doc.transportista_doc && !$('ni-trans-doc').value.trim()) $('ni-trans-doc').value = doc.transportista_doc;
  if (doc.observaciones && !$('ni-obs').value.trim()) $('ni-obs').value = doc.observaciones;

  ingresoPdfPreviewItems = items.map((it) => ({
    sku: (it.sku || '').trim(),
    item_nombre: (it.item_nombre || it.descripcion || '').trim(),
    item_unidad: (it.item_unidad || '').trim(),
    cantidad: _n(it.cantidad, 1),
    precio: _n(it.precio, 0),
    descuento_pct: _n(it.descuento_pct, 0),
    matched: !!it.matched,
    confidence: _n(it.confidence, 0),
    raw: it.raw || '',
    warnings: it.warnings || []
  })).filter((it) => it.cantidad > 0);

  _renderIngresoPdfPreview();
  const conf = Math.round(_n(doc.confidence, 0) * 100);
  if (meta) meta.textContent = `${file.name} · Confianza documento: ${conf}% · Líneas sugeridas: ${ingresoPdfPreviewItems.length}`;
  toast('PDF analizado. Revisa y aplica las líneas.', 'ok');
}

function applyIngresoPdfPreview() {
  if (!ingresoPdfPreviewItems.length) {
    return toast('No hay líneas para aplicar', 'err');
  }

  const validItems = ingresoPdfPreviewItems
    .filter((row) => row.sku && _n(row.cantidad, 0) > 0)
    .map((row) => {
      const qty = _n(row.cantidad, 0);
      const price = _n(row.precio, 0);
      const discount = Math.max(0, Math.min(100, _n(row.descuento_pct, 0)));
      return {
        sku: row.sku,
        nombre: row.item_nombre || row.sku,
        unidad: row.item_unidad || '',
        cantidad: qty,
        precio: price,
        descuento_pct: discount,
        subtotal: r2(qty * price * (1 - discount / 100))
      };
    });

  if (!validItems.length) {
    return toast('Corrige SKU y cantidad antes de aplicar', 'err');
  }

  niItems = [...niItems, ...validItems];
  clearIngresoPdfPreview();
  rNI();
  toast(`${validItems.length} línea(s) agregada(s) desde PDF`);
}

function openNewIng(sku) {
  initIngresoProviderAutocomplete();
  loadIngresoProviderHints('');
  isEditingIng = false;
  isViewingIng = false;
  niItems = [];
  $('ni-fecha').value = new Date().toISOString().split('T')[0];
  $('ni-prov').value = '';
  $('ni-fact').value = '';
  $('ni-guia').value = '';
  $('ni-oc').value = '';
  $('ni-trans').value = '';
  $('ni-trans-doc').value = '';
  $('ni-obs').value = '';
  $('ni-asku').value = sku || '';
  $('ni-add-v').value = sku || '';
  $('ni-add-n').value = '';
  $('ni-add-u').value = '';
  $('ni-aq').value = '1';
  $('ni-ap').value = '0';
  $('ni-ad').value = '0';
  $('ni-info').textContent = '';
  clearIngresoPdfPreview();
  _setIngReadOnly(false);
  _setIngFooter(_ingDefaultFooter());
  rNI();
  oM('m-ing');
  if (sku) $('ni-aq').focus();
}

async function editIG(id) {
  initIngresoProviderAutocomplete();
  loadIngresoProviderHints('');
  if (!id) return toast('ID invalido', 'err');
  const d = await api('/api/ingresos/' + id);
  if (!d || !d.ok) return toast('No encontrado', 'err');
  const ing = d.data;
  isEditingIng = true;
  isViewingIng = false;
  niItems = ing.items || [];
  $('ni-fecha').value = ing.fecha || '';
  $('ni-prov').value = ing.proveedor || '';
  $('ni-fact').value = ing.factura || '';
  $('ni-guia').value = ing.guia || '';
  $('ni-oc').value = ing.oc || '';
  $('ni-trans').value = ing.transportista || '';
  $('ni-trans-doc').value = ing.transportista_doc || '';
  $('ni-obs').value = ing.observaciones || '';
  $('ni-asku').value = '';
  $('ni-add-v').value = '';
  $('ni-add-n').value = '';
  $('ni-add-u').value = '';
  $('ni-aq').value = '1';
  $('ni-ap').value = '0';
  $('ni-ad').value = '0';
  $('ni-info').textContent = '';
  clearIngresoPdfPreview();
  _setIngReadOnly(false);
  rNI();
  oM('m-ing');
  _setIngFooter(`<div class="ing-footer-stats"><div><div class="ing-stat-label">Items</div><div class="ing-stat-value" id="ni-ti">0</div></div><div><div class="ing-stat-label">Unidades</div><div class="ing-stat-value" id="ni-tu">0</div></div><div><div class="ing-stat-label">Neto</div><div class="ing-stat-value ing-stat-value--total" id="ni-tt">$ 0</div></div><div><div class="ing-stat-label">IVA 19%</div><div class="ing-stat-value" id="ni-iva">$ 0</div></div><div><div class="ing-stat-label">Total c/IVA</div><div class="ing-stat-value" id="ni-tt-iva">$ 0</div></div></div><div class="ing-footer-btns"><button class="btn bs" onclick="closeIng()">Cancelar</button><button class="btn bg" onclick="saveIB(${id})">✓ Actualizar Ingreso</button></div>`);
  uNIT();
}

async function viewIG(id) {
  initIngresoProviderAutocomplete();
  loadIngresoProviderHints('');
  if (!id) return toast('ID invalido', 'err');
  const d = await api('/api/ingresos/' + id);
  if (!d || !d.ok) return toast('No encontrado', 'err');
  const ing = d.data;
  isViewingIng = true;
  isEditingIng = false;
  niItems = ing.items || [];
  $('ni-fecha').value = ing.fecha || '';
  $('ni-prov').value = ing.proveedor || '';
  $('ni-fact').value = ing.factura || '';
  $('ni-guia').value = ing.guia || '';
  $('ni-oc').value = ing.oc || '';
  $('ni-trans').value = ing.transportista || '';
  $('ni-trans-doc').value = ing.transportista_doc || '';
  $('ni-obs').value = ing.observaciones || '';
  $('ni-asku').value = '';
  $('ni-add-v').value = '';
  $('ni-add-n').value = '';
  $('ni-add-u').value = '';
  $('ni-aq').value = '1';
  $('ni-ap').value = '0';
  $('ni-ad').value = '0';
  $('ni-info').textContent = '';
  clearIngresoPdfPreview();
  _setIngReadOnly(true);
  rNI();
  oM('m-ing');
  _setIngFooter(`<div class="ing-footer-stats"><div><div class="ing-stat-label">Items</div><div class="ing-stat-value" id="ni-ti">0</div></div><div><div class="ing-stat-label">Unidades</div><div class="ing-stat-value" id="ni-tu">0</div></div><div><div class="ing-stat-label">Neto</div><div class="ing-stat-value ing-stat-value--total" id="ni-tt">$ 0</div></div><div><div class="ing-stat-label">IVA 19%</div><div class="ing-stat-value" id="ni-iva">$ 0</div></div><div><div class="ing-stat-label">Total c/IVA</div><div class="ing-stat-value" id="ni-tt-iva">$ 0</div></div></div><div class="ing-footer-btns"><button class="btn bs" onclick="closeIng()">Cerrar</button></div>`);
  uNIT();
}

async function delIG(id) {
  if (!id || !confirm('Eliminar este ingreso?')) return;
  const r = await api('/api/ingresos/' + id, { method: 'DELETE' });
  if (r && r.ok) {
    toast('Ingreso eliminado');
    lIG();
  } else if (r) {
    toast(r.msg, 'err');
  }
}

function closeIng() {
  if (!$('m-ing').classList.contains('on')) return;
  isEditingIng = false;
  isEditingIngresoDocument = false;
  currentIngresoDocumentKey = null;
  isViewingIng = false;
  niItems = [];
  clearIngresoPdfPreview();
  _setIngReadOnly(false);
  _setIngFooter(_ingDefaultFooter());
  cM('m-ing');
}

function addNI() {
  const sk = $('ni-add-v').value.trim();
  const nm = $('ni-add-n').value;
  const un = $('ni-add-u').value;
  const q = parseFloat($('ni-aq').value) || 0;
  const pr = parseFloat($('ni-ap').value) || 0;
  const dc = parseFloat($('ni-ad').value) || 0;
  if (!sk) return toast('Selecciona producto', 'err');
  if (q <= 0) return toast('Cantidad > 0', 'err');
  niItems.push({ sku: sk, nombre: nm, unidad: un, cantidad: q, precio: pr, descuento_pct: dc, subtotal: r2(q * pr * (1 - dc / 100)) });
  $('ni-asku').value = '';
  $('ni-add-v').value = '';
  $('ni-add-n').value = '';
  $('ni-add-u').value = '';
  $('ni-aq').value = '1';
  $('ni-ap').value = '0';
  $('ni-ad').value = '0';
  $('ni-info').textContent = '';
  $('ni-asku').focus();
  rNI();
  toast(sk + ' agregado');
}

function rmNI(i) { niItems.splice(i, 1); rNI(); }

function edNI(i, f, v) {
  const it = niItems[i];
  it[f] = parseFloat(v) || 0;
  it.subtotal = r2(it.cantidad * it.precio * (1 - it.descuento_pct / 100));
  uNIT();
}

function rNI() {
  const tb = $('ni-body');
  if (!niItems.length) {
    tb.innerHTML = '<tr><td colspan="8" style="text-align:center;padding:18px;color:var(--t3);font-size:10px">Agrega productos arriba</td></tr>';
  } else if (isViewingIng) {
    tb.innerHTML = niItems.map((it, i) => `<tr><td class="m" style="color:var(--t3);font-size:10px">${i + 1}</td><td class="m" style="font-weight:600;font-size:10px">${it.sku}</td><td style="max-width:180px;overflow:hidden;text-overflow:ellipsis;font-size:10px" title="${it.nombre}">${it.nombre} <span style="color:var(--t3)">${it.unidad}</span></td><td class="m" style="text-align:right;font-size:10px">${fm(it.cantidad)}</td><td class="m" style="text-align:right;font-size:10px">${fp(it.precio)}</td><td class="m" style="text-align:right;font-weight:600;color:var(--ok);font-size:10px">${fp(calcIngresoItemNet(it))}</td></tr>`).join('');
  } else {
    tb.innerHTML = niItems.map((it, i) => `<tr><td class="m" style="color:var(--t3);font-size:10px">${i + 1}</td><td class="m" style="font-weight:600;font-size:10px">${it.sku}</td><td style="max-width:180px;overflow:hidden;text-overflow:ellipsis;font-size:10px" title="${it.nombre}">${it.nombre} <span style="color:var(--t3)">${it.unidad}</span></td><td style="text-align:right"><input type="number" class="fi" style="width:62px;text-align:right;padding:3px 6px;font-size:10px" value="${it.cantidad}" min=".01" step=".01" onchange="edNI(${i},'cantidad',this.value);rNI()"></td><td style="text-align:right"><input type="number" class="fi" style="width:82px;text-align:right;padding:3px 6px;font-size:10px" value="${it.precio}" min="0" step=".01" onchange="edNI(${i},'precio',this.value);rNI()"></td><td style="text-align:right"><input type="number" class="fi" style="width:50px;text-align:right;padding:3px 6px;font-size:10px" value="${it.descuento_pct}" min="0" max="100" step=".1" onchange="edNI(${i},'descuento_pct',this.value);rNI()"></td><td class="m" style="text-align:right;font-weight:600;color:var(--ok);font-size:10px">${fp(calcIngresoItemNet(it))}</td><td><button class="bi" onclick="rmNI(${i})" style="color:var(--no);width:22px;height:22px;font-size:11px">✕</button></td></tr>`).join('');
  }
  uNIT();
}

function uNIT() {
  const ti = niItems.length;
  const tu = niItems.reduce((s, i) => s + i.cantidad, 0);
  const tt = niItems.reduce((s, i) => s + calcIngresoItemNet(i), 0);
  const iva = calcIvaFromNet(tt);
  const totalConIva = calcTotalWithIva(tt);
  if ($('ni-ti')) $('ni-ti').textContent = ti;
  if ($('ni-tu')) $('ni-tu').textContent = fm(tu);
  if ($('ni-tt')) $('ni-tt').textContent = fp(tt);
  if ($('ni-iva')) $('ni-iva').textContent = fp(iva);
  if ($('ni-tt-iva')) $('ni-tt-iva').textContent = fp(totalConIva);
  $('ni-cnt').textContent = ti + ' producto' + (ti !== 1 ? 's' : '');
}

async function saveIB(editId) {
  if (!niItems.length) return toast('Agrega productos', 'err');
  if (!$('ni-fecha').value) return toast('Fecha requerida', 'err');
  if (!$('ni-prov').value.trim()) return toast('Proveedor requerido', 'err');

  const payload = {
    fecha: $('ni-fecha').value,
    proveedor: $('ni-prov').value.trim(),
    factura: $('ni-fact').value.trim(),
    guia: $('ni-guia').value.trim(),
    oc: $('ni-oc').value.trim(),
    transportista: $('ni-trans').value.trim(),
    transportista_doc: $('ni-trans-doc').value.trim(),
    observaciones: $('ni-obs').value.trim(),
    items: niItems.map((i) => ({ rowid: i.rowid || null, sku: i.sku, cantidad: i.cantidad, precio: i.precio, descuento_pct: i.descuento_pct, descripcion: i.nombre }))
  };

  let url = '/api/ingresos/batch';
  let method = 'POST';
  if (isEditingIngresoDocument) {
    url = '/api/ingresos/documento';
    method = 'PUT';
  } else if (editId) {
    url = `/api/ingresos/${editId}`;
    method = 'PUT';
  }

  const r = await api(url, { method: method, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
  if (r && r.ok) {
    toast(r.msg);
    niItems = [];
    isEditingIng = false;
    isEditingIngresoDocument = false;
    currentIngresoDocumentKey = null;
    cM('m-ing');
    lIG();
    lD();
  } else if (r) {
    toast(r.msg, 'err');
  }
}

function _mapIngresoRowToModalItem(row) {
  const qty = Number(row.cantidad || 0);
  const price = Number(row.precio || 0);
  const discount = Number(row.desc_pct || row.descuento_pct || 0);
  return {
    rowid: row.rowid || null,
    sku: row.sku || '',
    nombre: row.descripcion || row.sku || '',
    unidad: row.unidad || '',
    cantidad: qty,
    precio: price,
    descuento_pct: discount,
    subtotal: r2(qty * price * (1 - discount / 100))
  };
}

function editIngresoDocumento(index) {
  const group = getIngresoGroupByIndex(index);
  if (!group || !group.items || !group.items.length) return toast('Documento no encontrado', 'err');

  const first = group.items[0];
  isEditingIng = true;
  isViewingIng = false;
  isEditingIngresoDocument = true;
  currentIngresoDocumentKey = group.key;

  niItems = group.items.map(_mapIngresoRowToModalItem);

  $('ni-fecha').value = first.fecha || '';
  $('ni-prov').value = first.proveedor || group.proveedor || '';
  $('ni-fact').value = first.factura || '';
  $('ni-guia').value = first.guia || '';
  $('ni-oc').value = first.oc || '';
  $('ni-trans').value = first.transportista || '';
  $('ni-trans-doc').value = first.transportista_doc || '';
  $('ni-obs').value = first.obs || '';
  $('ni-asku').value = '';
  $('ni-add-v').value = '';
  $('ni-add-n').value = '';
  $('ni-add-u').value = '';
  $('ni-aq').value = '1';
  $('ni-ap').value = '0';
  $('ni-ad').value = '0';
  $('ni-info').textContent = '';

  clearIngresoPdfPreview();
  _setIngReadOnly(false);
  _setIngFooter('<div class="ing-footer-stats"><div><div class="ing-stat-label">Items</div><div class="ing-stat-value" id="ni-ti">0</div></div><div><div class="ing-stat-label">Unidades</div><div class="ing-stat-value" id="ni-tu">0</div></div><div><div class="ing-stat-label">Neto</div><div class="ing-stat-value ing-stat-value--total" id="ni-tt">$ 0</div></div><div><div class="ing-stat-label">IVA 19%</div><div class="ing-stat-value" id="ni-iva">$ 0</div></div><div><div class="ing-stat-label">Total c/IVA</div><div class="ing-stat-value" id="ni-tt-iva">$ 0</div></div></div><div class="ing-footer-btns"><button class="btn bs" onclick="closeIng()">Cancelar</button><button class="btn bg" onclick="saveIB()">✓ Guardar Documento</button></div>');
  rNI();
  oM('m-ing');
}

async function deleteIngresoDocumento(index) {
  const group = getIngresoGroupByIndex(index);
  if (!group || !group.items || !group.items.length) return toast('Documento no encontrado', 'err');

  const rowids = group.items.map((item) => item.rowid).filter((rowid) => rowid != null);
  if (!rowids.length) return toast('Documento sin filas válidas', 'err');
  if (!confirm(`Eliminar documento completo con ${rowids.length} insumo(s)?`)) return;

  const r = await api('/api/ingresos/documento', {
    method: 'DELETE',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ rowids })
  });

  if (r && r.ok) {
    toast(r.msg || 'Documento eliminado');
    lIG();
    lD();
  } else if (r) {
    toast(r.msg, 'err');
  }
}

window.editIngresoDocumento = editIngresoDocumento;
window.deleteIngresoDocumento = deleteIngresoDocumento;