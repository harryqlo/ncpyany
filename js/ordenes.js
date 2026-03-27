// Función de búsqueda que resetea la página a 1
function searchOT() {
  otS.p = 1;
  lOT();
}

async function lOT() {
  const p = new URLSearchParams({ page: otS.p, per_page: 50, search: $('ot-s').value.trim() });
  const d = await api('/api/ordenes?' + p);
  if (!d) return;
  $('ot-b').innerHTML = d.items.length === 0
    ? '<tr><td colspan="7"><div class="empty"><div class="empty-t">Sin ordenes</div></div></td></tr>'
    : d.items.map((r) => `<tr><td class="m" style="font-weight:600">${r.id}</td><td style="max-width:220px;overflow:hidden;text-overflow:ellipsis">${r.descripcion || '-'}</td><td>${r.cliente || '-'}</td><td style="font-size:10px;color:var(--t3)">${r.referencia || '-'}</td><td class="m" style="font-size:10px">${r.fecha || '-'}</td><td style="font-size:10px;max-width:180px;overflow:hidden;text-overflow:ellipsis">${r.materiales || '-'}</td><td><div style="display:flex;gap:3px"><button class="bi" onclick="editOT(${r.id})" title="Editar" style="color:var(--ac)">✎</button><button class="bi" onclick="deleteOT(${r.id})" title="Eliminar" style="color:var(--no)">✕</button></div></td></tr>`).join('');
  rP('ot-p', d, otS, lOT);
}

let currentOTId = null;

async function openNewOT() {
  currentOTId = null;
  $('ot-modal-title').textContent = 'Nueva OT';
  $('ot-num-display').style.display = 'block';
  $('ot-desc').value = '';
  $('ot-cli').value = '';
  $('ot-ref').value = '';
  $('ot-cod').value = '';
  $('ot-mat').value = '';
  
  // Obtener siguiente número de OT
  const sig = await api('/api/ordenes/siguiente');
  if (sig) {
    $('ot-num').textContent = sig.siguiente;
  }
  
  oM('m-ot');
}

async function editOT(id) {
  currentOTId = id;
  $('ot-modal-title').textContent = 'Editar OT';
  $('ot-num-display').style.display = 'none';
  
  // Buscar la OT en la lista actual
  const p = new URLSearchParams({ page: otS.p, per_page: 50, search: $('ot-s').value.trim() });
  const d = await api('/api/ordenes?' + p);
  if (!d) return;
  
  const ot = d.items.find(item => item.id === id);
  if (!ot) return toast('OT no encontrada', 'err');
  
  $('ot-desc').value = ot.descripcion || '';
  $('ot-cli').value = ot.cliente || '';
  $('ot-ref').value = ot.referencia || '';
  $('ot-cod').value = ot.codigo || '';
  $('ot-mat').value = ot.materiales || '';
  
  oM('m-ot');
}

async function deleteOT(id) {
  if (!confirm('¿Eliminar OT #' + id + '?')) return;
  
  const r = await api('/api/ordenes/' + id, {
    method: 'DELETE'
  });
  
  if (r && r.ok) {
    toast(r.msg);
    lOT();
  } else if (r) {
    toast(r.msg, 'err');
  }
}

async function saveOT() {
  const desc = $('ot-desc').value.trim();
  if (!desc) return toast('Descripcion obligatoria', 'err');
  
  const data = {
    descripcion: desc,
    cliente: $('ot-cli').value,
    referencia: $('ot-ref').value,
    codigo: $('ot-cod').value,
    materiales: $('ot-mat').value,
    fecha: new Date().toISOString().split('T')[0]
  };
  
  const url = currentOTId ? '/api/ordenes/' + currentOTId : '/api/ordenes';
  const method = currentOTId ? 'PUT' : 'POST';
  
  const r = await api(url, {
    method: method,
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data)
  });
  
  if (r && r.ok) {
    toast(r.msg);
    cM('m-ot');
    lOT();
  } else if (r) {
    toast(r.msg, 'err');
  }
}