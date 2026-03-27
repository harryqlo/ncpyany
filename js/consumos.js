let consumoUsersCache = [];
let consumoRowsCache = new Map();
let currentConsumoEditKey = null;
let consumoDocumentGroups = [];
let consumoDocumentCache = new Map();
let currentConsumoDocumentKey = null;
let currentConsumoDocumentRef = null;
let isEditingConsumoDocument = false;


function getConsumoRowKey(row) {
  return row.source === 'acumulado'
    ? `acumulado:${encodeURIComponent(row.sku || '')}`
    : `movimiento:${row.rowid}`;
}


function getConsumoEndpoint(row) {
  return row.source === 'acumulado'
    ? `/api/consumos/historico/${encodeURIComponent(row.sku || '')}`
    : `/api/consumos/${row.rowid}`;
}


function normalizeConsumoRow(row) {
  return {
    source: row.source || (row.rowid != null ? 'movimiento' : 'acumulado'),
    rowid: row.rowid != null ? row.rowid : (row.rid != null ? row.rid : null),
    documento_ref: row.documento_ref || null,
    sku: row.sku || '',
    descripcion: row.descripcion || row.nombre || '',
    fecha: row.fecha || null,
    solicitante: row.solicitante || row.ref1 || '',
    cantidad: row.cantidad != null ? row.cantidad : (row.cant != null ? row.cant : 0),
    precio: row.precio || 0,
    total: row.total || 0,
    ot_id: row.ot_id || row.ot || row.ref2 || '',
    obs: row.obs || '',
    stock_en_consumo: row.stock_en_consumo != null ? row.stock_en_consumo : (row.stock_post != null ? row.stock_post : null)
  };
}


function cacheConsumoRow(row) {
  const normalized = normalizeConsumoRow(row);
  const rowKey = getConsumoRowKey(normalized);
  consumoRowsCache.set(rowKey, normalized);
  return rowKey;
}

function getConsumoDocumentDisplayLabel(group) {
  if (group.source === 'acumulado') return 'Histórico acumulado';
  if (group.documento_ref) return group.documento_ref;
  return group.items.length > 1 ? `Documento legacy (${group.items.length} líneas)` : `Registro ${group.items[0]?.rowid || '-'}`;
}

function getConsumoSummaryMeta(group) {
  const firstItem = group.items && group.items.length ? group.items[0] : null;
  if (group.source === 'acumulado') {
    return {
      documentMain: firstItem?.sku ? `Histórico SKU: ${firstItem.sku}` : 'Histórico acumulado',
      documentSub: firstItem?.descripcion || 'Consumo acumulado sin detalle por documento',
      requesterMain: firstItem?.descripcion || 'Ítem histórico',
      requesterSub: firstItem?.stock_en_consumo != null ? `Stock actual: ${fm(firstItem.stock_en_consumo)}` : 'Stock actual: -',
      otDisplay: firstItem?.ot_id || '-'
    };
  }

  return {
    documentMain: getConsumoDocumentDisplayLabel(group),
    documentSub: group.obs ? `Obs: ${group.obs}` : '',
    requesterMain: group.solicitante || '-',
    requesterSub: group.obs ? '' : 'Sin observaciones',
    otDisplay: group.ot_id || '-'
  };
}

function getConsumoDocumentKey(group) {
  if (group.source === 'acumulado') return `hist:${group.items[0]?.sku || 'na'}`;
  if (group.documento_ref) return `doc:${group.documento_ref}`;
  return `legacy:${group.items[0]?.rowid || Date.now()}`;
}

function buildLegacyConsumoSignature(row) {
  return [row.fecha || '', row.solicitante || '', row.ot_id || '', row.obs || '']
    .map((value) => String(value).trim().toLowerCase())
    .join('||');
}

function createConsumoDocumentGroup(row, opts = {}) {
  const group = {
    key: '',
    source: row.source,
    documento_ref: row.documento_ref || null,
    fecha: row.fecha || null,
    solicitante: row.solicitante || '',
    ot_id: row.ot_id || '',
    obs: row.obs || '',
    items: [],
    total_cantidad: 0,
    total_monto: 0,
    legacy_signature: opts.legacySignature || null
  };
  group.key = getConsumoDocumentKey(group);
  return group;
}

function appendConsumoDocumentItem(group, row) {
  group.items.push(row);
  group.total_cantidad += Number(row.cantidad || 0);
  group.total_monto += Number(row.total || 0);
  if (!group.fecha && row.fecha) group.fecha = row.fecha;
}

function groupConsumosByDocumento(items) {
  const groups = [];
  const byDocRef = new Map();
  let lastLegacyGroup = null;

  items.forEach((raw) => {
    const rowKey = cacheConsumoRow(raw);
    const row = consumoRowsCache.get(rowKey);
    if (!row) return;

    if (row.source === 'acumulado') {
      const group = createConsumoDocumentGroup(row);
      appendConsumoDocumentItem(group, row);
      groups.push(group);
      lastLegacyGroup = null;
      return;
    }

    const docRef = (row.documento_ref || '').trim();
    if (docRef) {
      let group = byDocRef.get(docRef);
      if (!group) {
        group = createConsumoDocumentGroup(row);
        groups.push(group);
        byDocRef.set(docRef, group);
      }
      appendConsumoDocumentItem(group, row);
      lastLegacyGroup = null;
      return;
    }

    const legacySignature = buildLegacyConsumoSignature(row);
    if (!lastLegacyGroup || lastLegacyGroup.legacy_signature !== legacySignature) {
      lastLegacyGroup = createConsumoDocumentGroup(row, { legacySignature });
      groups.push(lastLegacyGroup);
    }
    appendConsumoDocumentItem(lastLegacyGroup, row);
  });

  consumoDocumentCache = new Map(groups.map((group) => [group.key, group]));
  return groups;
}

function toggleConsumoDocument(index) {
  const group = consumoDocumentGroups[index];
  if (!group) return;
  const detailKey = `co-doc-detail-${index}`;
  const isOpen = document.getElementById(detailKey);
  if (isOpen) {
    isOpen.remove();
    return;
  }

  const summaryRow = document.getElementById(`co-doc-row-${index}`);
  if (!summaryRow) return;
  const detailRow = document.createElement('tr');
  detailRow.id = detailKey;
  detailRow.className = 'ingresos-doc-detail-host';
  detailRow.innerHTML = `<td colspan="7" style="padding:0 0 12px 0"><div style="padding:10px 10px 0 10px"><table class="consumos-doc-detail-table"><thead><tr><th>SKU</th><th>Producto</th><th style="text-align:right">Cant.</th><th style="text-align:right">Precio</th><th style="text-align:right">Total</th><th style="text-align:right">Stock Rest.</th></tr></thead><tbody>${group.items.map((item) => `<tr><td class="m" style="font-size:11px">${h(item.sku || '-')}</td><td style="max-width:260px;overflow:hidden;text-overflow:ellipsis;font-size:11px" title="${h(item.descripcion || '')}">${h(item.descripcion || '-')}</td><td class="m" style="text-align:right;font-weight:600;color:var(--no);font-size:11px">-${fm(item.cantidad || 0)}</td><td class="m" style="text-align:right;font-size:11px">${fp(item.precio || 0)}</td><td class="m" style="text-align:right;font-weight:700;font-size:11px">${fp(item.total || 0)}</td><td class="m" style="text-align:right;font-size:11px">${item.stock_en_consumo != null ? fm(item.stock_en_consumo) : '-'}</td></tr>`).join('')}</tbody></table></div></td>`;
  summaryRow.insertAdjacentElement('afterend', detailRow);
}

function renderCOGroupedRows() {
  const body = $('co-b');
  if (!body) return;

  if (!consumoDocumentGroups.length) {
    body.innerHTML = '<tr><td colspan="7"><div class="empty"><div class="empty-t">Sin consumos</div></div></td></tr>';
    return;
  }

  body.innerHTML = consumoDocumentGroups.map((group, index) => {
    const meta = getConsumoSummaryMeta(group);
    const actions = group.source === 'acumulado'
      ? `<div class="action-box"><button class="bi" onclick="toggleConsumoDocument(${index})" title="Ver detalle">👁</button><button class="bi" onclick="editConsumoDocumento('${group.key}')" title="Editar registro" style="color:var(--ac)">✎</button><button class="bi" onclick="deleteConsumoDocumento('${group.key}')" title="Eliminar registro" style="color:var(--no)">✕</button></div>`
      : `<div class="action-box"><button class="bi" onclick="toggleConsumoDocument(${index})" title="Ver documento">👁</button><button class="bi" onclick="editConsumoDocumento('${group.key}')" title="Editar documento" style="color:var(--ac)">✎</button><button class="bi" onclick="deleteConsumoDocumento('${group.key}')" title="Eliminar documento" style="color:var(--no)">✕</button></div>`;
    return `<tr class="ingresos-doc-summary-row" id="co-doc-row-${index}"><td class="m" style="font-size:11px">${h(group.fecha || '-')}</td><td><div class="co-cell-main"><b>${group.source === 'acumulado' ? 'Tipo' : 'Documento'}:</b> ${h(meta.documentMain)}</div>${meta.documentSub ? `<div class="co-cell-sub">${h(meta.documentSub)}</div>` : ''}</td><td><div class="co-cell-main">${h(meta.requesterMain)}</div>${meta.requesterSub ? `<div class="co-cell-sub">${h(meta.requesterSub)}</div>` : ''}</td><td class="m" style="color:var(--t3);font-size:11px">${h(meta.otDisplay)}</td><td class="m" style="text-align:right;font-size:11px">${fm(group.items.length)}</td><td class="m" style="text-align:right;font-weight:700;color:var(--no);font-size:11px">-${fm(group.total_cantidad)}</td><td style="text-align:center">${actions}</td></tr>`;
  }).join('');
}

function renderCOFlatRows(items) {
  const body = $('co-b');
  if (!body) return;

  if (!items.length) {
    body.innerHTML = '<tr><td colspan="9"><div class="empty"><div class="empty-t">Sin consumos</div></div></td></tr>';
    return;
  }

  body.innerHTML = items.map((raw) => {
    const rowKey = cacheConsumoRow(raw);
    const row = consumoRowsCache.get(rowKey);
    if (!row) return '';

    const fecha = row.fecha || '-';
    const solicitante = row.solicitante || (row.source === 'acumulado' ? 'Histórico' : '-');
    const consumo = fm(row.cantidad || 0);
    const precio = fp(row.precio || 0);
    const ot = row.ot_id || '-';
    const obs = row.obs || (row.source === 'acumulado' ? 'Histórico acumulado' : '-');

    return `<tr>
      <td class="m" style="font-size:11px;font-weight:600">${h(row.sku || '-')}</td>
      <td class="co-desc-cell" title="${h(row.descripcion || '')}">${h(row.descripcion || '-')}</td>
      <td class="m" style="font-size:11px">${h(fecha)}</td>
      <td style="font-size:11px">${h(solicitante)}</td>
      <td class="m" style="text-align:right;font-size:11px;color:var(--no);font-weight:700">${consumo}</td>
      <td class="m" style="text-align:right;font-size:11px">${precio}</td>
      <td class="m" style="font-size:11px">${h(ot)}</td>
      <td style="max-width:220px;overflow:hidden;text-overflow:ellipsis;font-size:11px" title="${h(obs)}">${h(obs)}</td>
      <td style="text-align:center"><div class="action-box"><button class="bi" onclick="editConsumo('${rowKey}')" title="Editar" style="color:var(--ac)">✎</button><button class="bi" onclick="deleteConsumo('${rowKey}')" title="Eliminar" style="color:var(--no)">✕</button></div></td>
    </tr>`;
  }).join('');
}

function setConsumoModalMode() {
  const title = $('m-con-title');
  const subtitle = $('m-con-subtitle');
  const saveBtn = $('m-con-save-btn');
  if (!title || !subtitle || !saveBtn) return;

  if (isEditingConsumoDocument) {
    title.textContent = 'Editar Documento de Consumo';
    subtitle.textContent = 'Ajusta encabezado e insumos del retiro completo en una sola operación.';
    saveBtn.textContent = '✓ Guardar Documento';
  } else {
    title.textContent = '📤 Retiro de Materiales';
    subtitle.textContent = 'Registra múltiples productos para un solicitante u OT';
    saveBtn.textContent = '✓ Registrar Consumo';
  }
}

function resetConsumoDocumentState() {
  currentConsumoDocumentKey = null;
  currentConsumoDocumentRef = null;
  isEditingConsumoDocument = false;
  setConsumoModalMode();
}

async function resolveConsumoDraftItems(items) {
  return Promise.all(items.map(async (item) => {
    let stock = null;
    let unidad = item.unidad || '';
    try {
      const matches = await api('/api/items/search?q=' + encodeURIComponent(item.sku || ''));
      if (Array.isArray(matches)) {
        const exact = matches.find((candidate) => candidate.sku === item.sku) || matches[0];
        if (exact) {
          stock = Number(exact.stock || 0);
          unidad = exact.unidad || unidad;
        }
      }
    } catch (error) {
      stock = null;
    }
    return {
      rowid: item.rowid || null,
      sku: item.sku,
      nombre: item.descripcion || item.nombre || '',
      unidad,
      stock,
      cantidad: Number(item.cantidad || 0),
      baseCantidad: Number(item.cantidad || 0),
      source: item.source || 'movimiento'
    };
  }));
}

function setNCQuantity(index, value) {
  const item = ncItems[index];
  if (!item) return;
  const parsed = parseFloat(value);
  item.cantidad = parsed > 0 ? parsed : 0;
  uNCT();
}

async function editConsumoDocumento(docKey) {
  const group = consumoDocumentCache.get(docKey);
  if (!group) return toast('Documento no encontrado', 'err');

  if (group.source === 'acumulado' && group.items.length === 1) {
    return editConsumo(getConsumoRowKey(group.items[0]));
  }

  await ensureConsumoUsersLoaded();
  populateConsumoUserOptions(consumoUsersCache);

  isEditingConsumoDocument = true;
  currentConsumoDocumentKey = group.key;
  currentConsumoDocumentRef = group.documento_ref || null;
  setConsumoModalMode();

  $('nc-fecha').value = group.fecha || new Date().toISOString().split('T')[0];
  $('nc-sol-filter').value = '';
  $('nc-sol').value = group.solicitante || '';
  $('nc-ot').value = group.ot_id || '';
  $('nc-obs').value = group.obs || '';
  $('nc-asku').value = '';
  $('nc-add-v').value = '';
  $('nc-add-n').value = '';
  $('nc-add-u').value = '';
  $('nc-add-st').value = '';
  $('nc-aq').value = '1';
  $('nc-info').textContent = '';

  const matchingUser = consumoUsersCache.find((user) => (user.nombre || user.name || '') === (group.solicitante || ''));
  $('nc-sol-select').value = matchingUser ? String(matchingUser.id) : '';

  ncItems = await resolveConsumoDraftItems(group.items);
  rNC();
  oM('m-con');
}

async function deleteConsumoDocumento(docKey) {
  const group = consumoDocumentCache.get(docKey);
  if (!group) return toast('Documento no encontrado', 'err');

  if (group.source === 'acumulado' && group.items.length === 1) {
    return deleteConsumo(getConsumoRowKey(group.items[0]));
  }

  if (!confirm(`¿Eliminar este documento de consumo? Se restaurarán ${group.items.length} insumo(s) al stock.`)) return;

  const rowids = group.items.map((item) => item.rowid).filter((rowid) => rowid != null);
  const r = await api('/api/consumos/documento', {
    method: 'DELETE',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ rowids })
  });

  if (r && r.ok) {
    toast(r.msg);
    if (currentConsumoDocumentKey === docKey) closeCon(true);
    lCO();
    if (typeof lD !== 'undefined') lD();
  } else if (r) {
    toast(r.msg, 'err');
  }
}

async function ensureConsumoUsersLoaded() {
  if (consumoUsersCache.length > 0) return;

  const d = await api('/api/empleados?per_page=200&page=1&search=');
  if (d && Array.isArray(d.empleados)) {
    consumoUsersCache = d.empleados;
  }
}

function getConsumoUserLabel(user) {
  const numero = user.numero_identificacion || user.numero_empleado || '';
  const nombre = user.nombre || user.name || '';
  return `${numero ? `${numero} - ` : ''}${nombre}`.trim();
}

function populateConsumoUserOptions(users) {
  const select = $('nc-sol-select');
  if (!select) return;

  const current = select.value || '';
  select.innerHTML = '<option value="">-- Seleccione un usuario --</option>' +
    users.map((u) => `<option value="${u.id}">${getConsumoUserLabel(u)}</option>`).join('');

  if (current && users.some((u) => String(u.id) === String(current))) {
    select.value = current;
  }
}

function filterConsumoUserOptions() {
  const filter = ($('nc-sol-filter')?.value || '').trim().toLowerCase();
  if (!filter) {
    populateConsumoUserOptions(consumoUsersCache);
    return;
  }

  const filtered = consumoUsersCache.filter((u) => {
    const txt = getConsumoUserLabel(u).toLowerCase();
    return txt.includes(filter);
  });
  populateConsumoUserOptions(filtered);
}

function selectConsumoUser(userId) {
  if (!userId) {
    $('nc-sol').value = '';
    return;
  }

  const user = consumoUsersCache.find((u) => String(u.id) === String(userId));
  $('nc-sol').value = user ? (user.nombre || user.name || '') : '';
}

// Función de búsqueda que resetea la página a 1
function searchCO() {
  coS.p = 1;
  lCO();
}

async function downloadConsumosHistoricosFormatoExcel() {
  const ok = await downloadFileAuth('/api/export/consumos/historicos/formato.xlsx', 'formato_ot_consumos_historicos.xlsx');
  if (ok) {
    toast('Formato Excel descargado');
  }
}

async function lCO() {
  const p = new URLSearchParams({ page: coS.p, per_page: 50, search: $('co-s').value.trim() });
  const d = await api('/api/consumos?' + p);
  if (!d) return;

  consumoRowsCache = new Map();
  consumoDocumentGroups = [];
  consumoDocumentCache = new Map();
  renderCOFlatRows(d.items || []);
  rP('co-p', d, coS, lCO);
}

function editConsumo(rowKey) {
  const row = consumoRowsCache.get(rowKey);
  if (!row) return toast('Consumo no encontrado', 'err');

  currentConsumoEditKey = rowKey;
  $('ce-key').value = rowKey;
  $('ce-source').value = row.source || 'movimiento';
  $('ce-sku').value = row.sku || '';
  $('ce-desc').textContent = row.descripcion || '-';
  $('ce-stock').textContent = row.stock_en_consumo != null ? fm(row.stock_en_consumo) : '-';
  $('ce-fecha').value = row.fecha || new Date().toISOString().split('T')[0];
  $('ce-sol').value = row.solicitante || '';
  $('ce-ot').value = row.ot_id || '';
  $('ce-cantidad').value = row.cantidad != null ? row.cantidad : '';
  $('ce-obs').value = row.obs || '';
  $('ce-source-note').textContent = row.source === 'acumulado'
    ? 'Este registro seguirá siendo histórico. Solo se actualizará OT / referencia de cargo.'
    : 'La actualizacion ajustara el stock automaticamente.';
  oM('m-con-edit');
}


function openConsumoEditorForRow(row) {
  const rowKey = cacheConsumoRow(row);
  editConsumo(rowKey);
}

function closeConsumoEdit() {
  currentConsumoEditKey = null;
  $('ce-key').value = '';
  $('ce-source').value = '';
  $('ce-sku').value = '';
  $('ce-desc').textContent = '-';
  $('ce-stock').textContent = '-';
  $('ce-fecha').value = '';
  $('ce-sol').value = '';
  $('ce-ot').value = '';
  $('ce-cantidad').value = '';
  $('ce-obs').value = '';
  $('ce-source-note').textContent = '';
  cM('m-con-edit');
}


async function saveConsumoEdit() {
  const rowKey = $('ce-key').value || currentConsumoEditKey;
  const row = consumoRowsCache.get(rowKey);
  if (!row) return toast('Consumo no encontrado', 'err');
  if (!$('ce-fecha').value) return toast('Fecha requerida', 'err');

  const cantidad = parseFloat($('ce-cantidad').value);
  if (!cantidad || cantidad <= 0) return toast('Cantidad invalida', 'err');

  const r = await api(getConsumoEndpoint(row), {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      fecha: $('ce-fecha').value,
      solicitante: $('ce-sol').value.trim(),
      ot_id: $('ce-ot').value.trim(),
      cantidad: cantidad,
      observaciones: $('ce-obs').value.trim()
    })
  });

  if (r && r.ok) {
    toast(r.msg);
    closeConsumoEdit();
    lCO();
    if (typeof lD !== 'undefined') lD();
    if (typeof refreshOpenConsumoContexts === 'function') refreshOpenConsumoContexts(row.sku);
  } else if (r) {
    toast(r.msg, 'err');
  }
}


async function deleteConsumo(rowKey) {
  const row = consumoRowsCache.get(rowKey);
  if (!row) return toast('Consumo no encontrado', 'err');
  if (!confirm('¿Eliminar este consumo? El stock será restaurado.')) return;

  const r = await api(getConsumoEndpoint(row), {
    method: 'DELETE'
  });

  if (r && r.ok) {
    toast(r.msg);
    if (currentConsumoEditKey === rowKey) closeConsumoEdit();
    lCO();
    if (typeof lD !== 'undefined') lD();
    if (typeof refreshOpenConsumoContexts === 'function') refreshOpenConsumoContexts(row.sku);
  } else if (r) {
    toast(r.msg, 'err');
  }
}


window.openConsumoEditorForRow = openConsumoEditorForRow;

async function openNewCon() {
  resetConsumoDocumentState();
  ncItems = [];
  $('nc-fecha').value = new Date().toISOString().split('T')[0];
  $('nc-sol').value = '';
  $('nc-sol-filter').value = '';
  $('nc-sol-select').value = '';
  $('nc-ot').value = '';
  $('nc-obs').value = '';
  $('nc-asku').value = '';
  $('nc-add-v').value = '';
  $('nc-add-n').value = '';
  $('nc-add-u').value = '';
  $('nc-add-st').value = '';
  $('nc-aq').value = '1';
  $('nc-info').textContent = '';

  await ensureConsumoUsersLoaded();
  populateConsumoUserOptions(consumoUsersCache);

  rNC();
  setConsumoModalMode();
  oM('m-con');
}

function closeCon(force = false) {
  if (!force && ncItems.length > 0 && !confirm('Salir?')) return;
  cM('m-con');
  resetConsumoDocumentState();
}

function addNC() {
  const sk = $('nc-add-v').value.trim();
  const nm = $('nc-add-n').value;
  const un = $('nc-add-u').value;
  const stk = parseFloat($('nc-add-st').value) || 0;
  const q = parseFloat($('nc-aq').value) || 0;
  if (!sk) return toast('Selecciona producto', 'err');
  if (q <= 0) return toast('Cantidad > 0', 'err');
  const existing = ncItems.find((item) => item.sku === sk);
  const maxDisponible = stk + Number(existing?.baseCantidad || 0);
  if (!existing && q > stk) return toast(`Stock insuficiente (${stk})`, 'err');
  if (existing) {
    const nuevaCantidad = Number(existing.cantidad || 0) + q;
    if (nuevaCantidad > maxDisponible) return toast(`Stock insuficiente (${maxDisponible})`, 'err');
    existing.cantidad = nuevaCantidad;
    existing.stock = stk;
  } else {
    ncItems.push({ sku: sk, nombre: nm, unidad: un, stock: stk, cantidad: q, baseCantidad: 0, rowid: null, source: 'movimiento' });
  }
  $('nc-asku').value = '';
  $('nc-add-v').value = '';
  $('nc-add-n').value = '';
  $('nc-add-u').value = '';
  $('nc-add-st').value = '';
  $('nc-aq').value = '1';
  $('nc-info').textContent = '';
  $('nc-asku').focus();
  rNC();
  toast(sk + ' agregado');
}

function rmNC(i) { ncItems.splice(i, 1); rNC(); }

function rNC() {
  const tb = $('nc-body');
  if (!ncItems.length) {
    tb.innerHTML = '<tr><td colspan="6" style="text-align:center;padding:24px;color:var(--t3);font-size:11px">Agrega productos arriba</td></tr>';
  } else {
    tb.innerHTML = ncItems.map((it, i) => {
      const maxQty = it.stock != null ? Number(it.stock || 0) + Number(it.baseCantidad || 0) : null;
      const stockLabel = maxQty != null ? fm(maxQty) : '-';
      const maxAttr = maxQty != null ? ` max="${maxQty}"` : '';
      return `<tr><td class="m" style="font-size:10px;color:var(--t3)">${i + 1}</td><td class="m" style="font-size:10px;font-weight:600">${it.sku}</td><td style="font-size:10px;max-width:180px;overflow:hidden;text-overflow:ellipsis">${it.nombre} <span style="color:var(--t3)">${it.unidad}</span></td><td class="m" style="text-align:right;color:var(--t3)">${stockLabel}</td><td style="text-align:right"><input type="number" class="fi" style="width:70px;text-align:right;padding:3px 6px;font-size:10px" value="${it.cantidad}" min=".01"${maxAttr} step=".01" onchange="setNCQuantity(${i}, this.value)"></td><td><button class="bi" onclick="rmNC(${i})" style="color:var(--no);width:24px;height:24px;font-size:12px">✕</button></td></tr>`;
    }).join('');
  }
  uNCT();
}

function uNCT() {
  $('nc-ti').textContent = ncItems.length;
  $('nc-tu').textContent = fm(ncItems.reduce((s, i) => s + i.cantidad, 0));
  $('nc-cnt').textContent = ncItems.length + ' producto' + (ncItems.length !== 1 ? 's' : '');
}

async function saveCB() {
  if (!ncItems.length) return toast('Agrega productos', 'err');
  if (!$('nc-fecha').value) return toast('Fecha requerida', 'err');
  if (!$('nc-sol').value.trim() && $('nc-sol-select')?.value) {
    selectConsumoUser($('nc-sol-select').value);
  }
  if (!$('nc-sol').value.trim()) return toast('Solicitante requerido', 'err');

  const payload = {
    fecha: $('nc-fecha').value,
    solicitante: $('nc-sol').value.trim(),
    ot_id: $('nc-ot').value.trim(),
    observaciones: $('nc-obs').value.trim(),
    items: ncItems.map((i) => ({ rowid: i.rowid || null, sku: i.sku, cantidad: i.cantidad }))
  };

  if (isEditingConsumoDocument) {
    payload.documento_ref = currentConsumoDocumentRef;
    const editResponse = await api('/api/consumos/documento', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });

    if (editResponse && editResponse.ok) {
      toast(editResponse.msg);
      ncItems = [];
      closeCon(true);
      if ($('co-s')) $('co-s').value = '';
      coS.p = 1;
      lCO();
      if (typeof lD !== 'undefined') lD();
    } else if (editResponse) {
      toast(editResponse.msg, 'err');
    }
    return;
  }

  const r = await api('/api/consumos/batch', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  });

  if (r && r.ok) {
    toast(r.msg);
    ncItems = [];
    closeCon(true);
    if ($('co-s')) $('co-s').value = '';
    coS.p = 1;
    lCO();
    lD();
  } else if (r) {
    toast(r.msg, 'err');
  }
}

window.editConsumoDocumento = editConsumoDocumento;
window.deleteConsumoDocumento = deleteConsumoDocumento;
window.toggleConsumoDocument = toggleConsumoDocument;
window.setNCQuantity = setNCQuantity;
window.downloadConsumosHistoricosFormatoExcel = downloadConsumosHistoricosFormatoExcel;