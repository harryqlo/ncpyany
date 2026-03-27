// Estado de paginación para componentes
let compS = { p: 1 };
let currentCompId = null;
let compMateriales = [];

// Función de búsqueda que resetea la página a 1
function searchComp() {
  compS.p = 1;
  lComp();
}

// Cargar componentes
async function lComp() {
  const p = new URLSearchParams({ page: compS.p, per_page: 50, search: $('comp-s').value.trim() });
  const d = await api('/api/componentes?' + p);
  if (!d) return;
  $('comp-b').innerHTML = d.items.length === 0
    ? '<tr><td colspan="5"><div class="empty"><div class="empty-t">Sin componentes</div></div></td></tr>'
    : d.items.map((r) => `<tr>
        <td class="m" style="font-weight:700;font-size:13px;color:var(--ac)">${r.id}</td>
        <td style="font-weight:600;font-size:13px">${r.nombre}</td>
        <td class="m" style="color:var(--t3);font-size:10px">${r.codigo || '-'}</td>
        <td style="max-width:220px;overflow:hidden;text-overflow:ellipsis;font-size:11px;color:var(--t2)">${r.descripcion || '-'}</td>
        <td>
          <div style="display:flex;gap:3px">
            <button class="bi" onclick="viewCompMat(${r.id},'${r.nombre.replace(/'/g, "\\'")}','${r.codigo || ''}')" title="Ver materiales" style="color:var(--ac);font-size:15px">📋</button>
            <button class="bi" onclick="viewStockAnalysis(${r.id},'${r.nombre.replace(/'/g, "\\'")}')" title="Análisis de stock" style="color:var(--ok)">📊</button>
            <button class="bi" onclick="editComp(${r.id})" title="Editar" style="color:var(--ac)">✎</button>
            <button class="bi" onclick="deleteComp(${r.id})" title="Eliminar" style="color:var(--no)">✕</button>
          </div>
        </td>
      </tr>`).join('');
  rP('comp-p', d, compS, lComp);
}

// Abrir modal para nuevo componente
function openNewComp() {
  currentCompId = null;
  $('comp-modal-title').textContent = 'Nuevo Componente';
  $('comp-nom').value = '';
  $('comp-cod').value = '';
  $('comp-desc').value = '';
  oM('m-comp');
}

// Editar componente
async function editComp(id) {
  currentCompId = id;
  $('comp-modal-title').textContent = 'Editar Componente';
  
  const p = new URLSearchParams({ page: compS.p, per_page: 50, search: $('comp-s').value.trim() });
  const d = await api('/api/componentes?' + p);
  if (!d) return;
  
  const comp = d.items.find(item => item.id === id);
  if (!comp) return toast('Componente no encontrado', 'err');
  
  $('comp-nom').value = comp.nombre || '';
  $('comp-cod').value = comp.codigo || '';
  $('comp-desc').value = comp.descripcion || '';
  
  oM('m-comp');
}

// Eliminar componente
async function deleteComp(id) {
  if (!confirm('¿Eliminar componente? Se eliminarán también sus materiales asociados.')) return;
  
  const r = await api('/api/componentes/' + id, { method: 'DELETE' });
  
  if (r && r.ok) {
    toast(r.msg);
    lComp();
  } else if (r) {
    toast(r.msg, 'err');
  }
}

// Guardar componente
async function saveComp() {
  const nombre = $('comp-nom').value.trim();
  if (!nombre) return toast('Nombre obligatorio', 'err');
  
  const data = {
    nombre: nombre,
    codigo: $('comp-cod').value.trim(),
    descripcion: $('comp-desc').value.trim()
  };
  
  const url = currentCompId ? '/api/componentes/' + currentCompId : '/api/componentes';
  const method = currentCompId ? 'PUT' : 'POST';
  
  const r = await api(url, {
    method: method,
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data)
  });
  
  if (r && r.ok) {
    toast(r.msg);
    cM('m-comp');
    lComp();
  } else if (r) {
    toast(r.msg, 'err');
  }
}

// Ver materiales de un componente
async function viewCompMat(id, nombre, codigo) {
  currentCompId = id;
  $('cm-title').textContent = 'Materiales de: ' + nombre;
  $('cm-comp-id').textContent = id;
  $('cm-comp-nombre').textContent = nombre + (codigo ? ' [' + codigo + ']' : '');
  
  await loadCompMat(id);
  oM('m-comp-mat');
}

// Cargar materiales del componente
async function loadCompMat(id) {
  const d = await api('/api/componentes/' + id + '/materiales');
  if (!d) return;
  
  compMateriales = d.materiales;
  renderCompMat();
}

// Renderizar materiales (formato Excel mejorado)
function renderCompMat() {
  const tb = $('cm-body');
  const totalItems = $('cm-total-items');
  
  if (!compMateriales.length) {
    tb.innerHTML = '<tr><td colspan="4" style="text-align:center;padding:24px;color:var(--t3);font-size:11px">Sin materiales. Agrega arriba.</td></tr>';
    totalItems.textContent = '0';
  } else {
    tb.innerHTML = compMateriales.map((m, i) => {
      const itemNum = i + 1;
      const descripcion = `${m.nombre || 'Sin nombre'} [SKU: ${m.sku}] (${m.unidad || 'Unidad'})`;
      const qty = fm(m.cantidad);
      
      return `<tr>
        <td style="text-align:center;font-weight:700;font-size:13px;color:var(--ac)">${itemNum}</td>
        <td style="font-size:12px;padding:10px 12px">
          <div style="font-weight:600;color:var(--t1)">${m.nombre || 'Sin nombre'}</div>
          <div style="font-size:10px;color:var(--t3);margin-top:2px">SKU: ${m.sku} • Stock: ${fm(m.stock)} ${m.unidad || 'Unidad'}</div>
        </td>
        <td style="text-align:center;font-weight:700;font-size:14px;color:var(--ok)">${qty}</td>
        <td style="text-align:center">
          <button class="bi" onclick="removeCompMat('${m.sku}')" title="Eliminar" style="color:var(--no)">✕</button>
        </td>
      </tr>`;
    }).join('');
    totalItems.textContent = compMateriales.length;
  }
}

// Función de impresión de materiales
function printCompMateriales() {
  if (!compMateriales.length) {
    return toast('No hay materiales para imprimir', 'err');
  }
  
  const compNombre = $('cm-comp-nombre').textContent;
  const compId = $('cm-comp-id').textContent;
  const fecha = new Date().toLocaleDateString('es-CL');
  
  // Crear contenido para imprimir
  let printContent = `
    <!DOCTYPE html>
    <html>
    <head>
      <meta charset="UTF-8">
      <title>Lista de Materiales - ${compNombre}</title>
      <style>
        @page { 
          size: A4; 
          margin: 15mm; 
        }
        * { 
          margin: 0; 
          padding: 0; 
          box-sizing: border-box; 
        }
        body { 
          font-family: Arial, sans-serif; 
          font-size: 11pt;
          color: #000;
          background: #fff;
        }
        .header {
          text-align: center;
          margin-bottom: 20px;
          padding-bottom: 15px;
          border-bottom: 3px solid #0533d1;
        }
        .header h1 {
          font-size: 20pt;
          font-weight: 700;
          color: #0533d1;
          margin-bottom: 5px;
        }
        .header .meta {
          font-size: 9pt;
          color: #666;
          margin-top: 5px;
        }
        table {
          width: 100%;
          border-collapse: collapse;
          margin-top: 10px;
        }
        thead {
          background: #f5f5f5;
        }
        th {
          padding: 12px 8px;
          text-align: left;
          font-weight: 700;
          font-size: 10pt;
          text-transform: uppercase;
          border: 2px solid #333;
          background: #e8e8e8;
        }
        th.center {
          text-align: center;
        }
        td {
          padding: 10px 8px;
          border: 1px solid #999;
          font-size: 10pt;
        }
        td.item-num {
          text-align: center;
          font-weight: 700;
          font-size: 12pt;
          width: 60px;
        }
        td.qty {
          text-align: center;
          font-weight: 700;
          font-size: 11pt;
          width: 80px;
        }
        td.descripcion {
          padding-left: 12px;
        }
        .desc-main {
          font-weight: 600;
          margin-bottom: 3px;
        }
        .desc-detail {
          font-size: 8pt;
          color: #555;
        }
        .footer {
          margin-top: 30px;
          padding-top: 15px;
          border-top: 1px solid #ccc;
          font-size: 8pt;
          color: #666;
          text-align: center;
        }
        .checkbox {
          display: inline-block;
          width: 15px;
          height: 15px;
          border: 2px solid #333;
          margin-right: 5px;
          vertical-align: middle;
        }
        tr:nth-child(even) {
          background: #fafafa;
        }
        @media print {
          body { 
            margin: 0;
            -webkit-print-color-adjust: exact;
            print-color-adjust: exact;
          }
        }
      </style>
    </head>
    <body>
      <div class="header">
        <h1>${compNombre}</h1>
        <div class="meta">ID: ${compId} • Fecha: ${fecha} • Total Items: ${compMateriales.length}</div>
      </div>
      <table>
        <thead>
          <tr>
            <th class="center">ITEM#</th>
            <th>DESCRIPCIÓN</th>
            <th class="center">QTY</th>
            <th class="center" style="width:50px">✓</th>
          </tr>
        </thead>
        <tbody>
  `;
  
  compMateriales.forEach((m, i) => {
    printContent += `
      <tr>
        <td class="item-num">${i + 1}</td>
        <td class="descripcion">
          <div class="desc-main">${m.nombre || 'Sin nombre'}</div>
          <div class="desc-detail">SKU: ${m.sku} • Stock disponible: ${fm(m.stock)} ${m.unidad || 'Unidad'}</div>
        </td>
        <td class="qty">${fm(m.cantidad)}</td>
        <td style="text-align:center"><span class="checkbox"></span></td>
      </tr>
    `;
  });
  
  printContent += `
        </tbody>
      </table>
      <div class="footer">
        North Chrome - Gestión de Bodega v2 • Impreso: ${new Date().toLocaleString('es-CL')}
      </div>
    </body>
    </html>
  `;
  
  // Abrir ventana de impresión
  const printWindow = window.open('', '_blank');
  printWindow.document.write(printContent);
  printWindow.document.close();
  printWindow.focus();
  
  // Imprimir después de cargar
  setTimeout(() => {
    printWindow.print();
  }, 250);
}

// Agregar material al componente
async function addCompMat() {
  const sku = $('cm-add-v').value.trim();
  const cantidad = parseFloat($('cm-aq').value) || 0;
  
  if (!sku) return toast('Selecciona un producto', 'err');
  if (cantidad <= 0) return toast('Cantidad debe ser > 0', 'err');
  
  const r = await api('/api/componentes/' + currentCompId + '/materiales', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ sku: sku, cantidad: cantidad })
  });
  
  if (r && r.ok) {
    toast(r.msg);
    $('cm-asku').value = '';
    $('cm-add-v').value = '';
    $('cm-add-n').value = '';
    $('cm-aq').value = '1';
    $('cm-info').textContent = '';
    await loadCompMat(currentCompId);
  } else if (r) {
    toast(r.msg, 'err');
  }
}

// Remover material del componente
async function removeCompMat(sku) {
  if (!confirm('¿Eliminar este material del componente?')) return;
  
  const r = await api('/api/componentes/' + currentCompId + '/materiales/' + sku, {
    method: 'DELETE'
  });
  
  if (r && r.ok) {
    toast(r.msg);
    await loadCompMat(currentCompId);
  } else if (r) {
    toast(r.msg, 'err');
  }
}

// Ver análisis de stock necesario
async function viewStockAnalysis(id, nombre) {
  $('sa-title').textContent = 'Análisis de Stock: ' + nombre;
  
  const d = await api('/api/componentes/' + id + '/stock-necesario');
  if (!d) return;
  
  const tb = $('sa-body');
  if (!d.materiales.length) {
    tb.innerHTML = '<tr><td colspan="6" style="text-align:center;padding:24px;color:var(--t3)">Este componente no tiene materiales definidos</td></tr>';
  } else {
    tb.innerHTML = d.materiales.map((m, i) => {
      const statusColor = m.suficiente ? 'var(--ok)' : 'var(--no)';
      const statusIcon = m.suficiente ? '✓' : '✗';
      const statusClass = m.suficiente ? 'icon-unicode-check' : 'icon-unicode-error';
      const statusText = m.suficiente ? 'OK' : 'Falta: ' + fm(m.faltante);
      return `<tr><td class="m" style="color:var(--t3)">${i + 1}</td><td class="m" style="font-weight:600">${m.sku}</td><td>${m.nombre || '-'}</td><td class="m">${fm(m.necesario)} ${m.unidad}</td><td class="m">${fm(m.disponible)}</td><td class="m"><span class="${statusClass}">${statusIcon}</span> ${statusText}</td></tr>`;
    }).join('');
  }
  
  const canProduceIcon = d.puede_producir ? '✓' : '✗';
  const canProduceClass = d.puede_producir ? 'icon-unicode-check' : 'icon-unicode-error';
  const canProduceText = d.puede_producir ? 'Puede producirse' : 'Stock insuficiente';
  $('sa-status').innerHTML = `<span class="${canProduceClass}" style="font-weight:700">${canProduceIcon} ${canProduceText}</span>`;
  
  oM('m-stock-analysis');
}
