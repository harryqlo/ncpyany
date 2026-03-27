let sellosRowsCache = new Map();
let sellosBocinasCache = [];
let selectedSelloBocina = null;
let sellosInitDone = false;

const SELLOS_MATERIAL_CATALOG = {
  'BOCINA': {
    fullName: 'Buje / Casquillo',
    description: 'Componente tipo bushing. Suele referirse al material en tubo usado para fabricar estas piezas (bronce, resina fenólica o plásticos como POM).'
  },
  'FPM': {
    fullName: 'Caucho Fluorado (FKM / Viton®)',
    description: 'Elastómero de alto rendimiento con excelente resistencia a altas temperaturas, aceites, combustibles y químicos agresivos.'
  },
  'H-NBR': {
    fullName: 'Caucho Nitrilo Butadieno Hidrogenado',
    description: 'Versión mejorada del NBR estándar. Resiste mejor temperatura, ozono y degradación química.'
  },
  'HPU': {
    fullName: 'Poliuretano Resistente a la Hidrólisis',
    description: 'PU modificado para que agua/humedad no lo degrade. Muy usado en hidráulica por resistencia al desgaste y abrasión.'
  },
  'NBR': {
    fullName: 'Caucho Nitrilo Butadieno (Nitrilo)',
    description: 'Material estándar y económico para sellos de uso general. Excelente resistencia a aceites minerales y grasas convencionales.'
  },
  'H-NBR 90 BLACK': {
    fullName: 'HNBR - Dureza 90 Shore A (Negro)',
    description: 'Mismo H-NBR con dureza alta (90) para soportar mayores presiones sin deformarse.'
  },
  'POM': {
    fullName: 'Polioximetileno (Acetal o Delrin®)',
    description: 'Plástico de ingeniería duro y mecanizable. Se usa en anillos guía, antiextrusión y piezas estructurales como bocinas.'
  },
  'PTFE D46': {
    fullName: 'Politetrafluoroetileno (Teflón®) con carga',
    description: 'PTFE mezclado con aditivos para mejorar resistencia al desgaste y reducir deformación bajo presión.'
  },
  'PTFE I': {
    fullName: 'PTFE Grado I (Virgen)',
    description: 'Teflón puro con muy baja fricción y resistencia química total; es más blando que versiones con carga.'
  },
  'PTFE II': {
    fullName: 'PTFE Grado II (Con carga)',
    description: 'Teflón modificado con cargas para mejorar propiedades mecánicas frente al grado virgen.'
  },
  'PTFE REIN': {
    fullName: 'PTFE Puro ("Rein" = puro en alemán)',
    description: 'Teflón 100% virgen sin aditivos. Se usa cuando se requiere máxima resistencia química o grado alimentario.'
  }
};

function updateSelloMaterialHelp() {
  const material = ($('si-material')?.value || '').trim().toUpperCase();
  const info = SELLOS_MATERIAL_CATALOG[material];
  const isOtro = material === 'OTRO (NUEVO)';

  if ($('si-material-otro-wrap')) {
    $('si-material-otro-wrap').style.display = isOtro ? 'block' : 'none';
  }

  if ($('si-material-fullname')) {
    if (isOtro) {
      $('si-material-fullname').textContent = 'Material nuevo: ingreso manual';
    } else {
      $('si-material-fullname').textContent = info
        ? `${material}: ${info.fullName}`
        : 'Seleccione un material para ver su nombre completo.';
    }
  }
  if ($('si-material-desc')) {
    if (isOtro) {
      $('si-material-desc').textContent = 'Escribe el nombre del nuevo material y quedará registrado en el ingreso.';
    } else {
      $('si-material-desc').textContent = info
        ? info.description
        : 'Aquí aparecerá para qué sirve y cuándo usarlo.';
    }
  }
}

function selectSelloMaterial(material) {
  if (!$('si-material')) return;
  $('si-material').value = (material || '').toUpperCase();
  updateSelloMaterialHelp();
}

function resolveSelloIngresoMaterial() {
  const selectedMaterial = ($('si-material')?.value || '').trim().toUpperCase();
  if (selectedMaterial === 'OTRO (NUEVO)') {
    return ($('si-material-otro')?.value || '').trim().toUpperCase();
  }
  return selectedMaterial;
}

function openNuevoInsumoDesdeSellos() {
  if (typeof openNewItem === 'function') {
    openNewItem(true);
  } else {
    toast('No se pudo abrir creación de insumo', 'err');
  }
}

function toggleSellosGuide() {
  const wrap = $('se-guide-wrap');
  const button = $('se-guide-toggle-btn');
  if (!wrap || !button) return;
  const isHidden = wrap.style.display === 'none' || !wrap.style.display;
  wrap.style.display = isHidden ? 'block' : 'none';
  button.textContent = isHidden ? 'Ocultar guía rápida' : 'Ver guía rápida';
}

function initSellosSection() {
  if (sellosInitDone) return;
  sellosInitDone = true;

  if ($('se-fecha')) $('se-fecha').value = new Date().toISOString().split('T')[0];
  if ($('se-cantidad')) $('se-cantidad').addEventListener('input', updateSelloCalc);
  if ($('se-largo')) $('se-largo').addEventListener('input', updateSelloCalc);

  updateSelloCalc();
  searchSellosBocinas();
}

function updateSelloCalc() {
  const cantidad = parseFloat(($('se-cantidad')?.value || '0')) || 0;
  const largo = parseFloat(($('se-largo')?.value || '0')) || 0;
  const consumo = cantidad * largo;
  if ($('se-calc')) $('se-calc').textContent = `Consumo estimado: ${fm(consumo)} mm`;
}

function searchSE() {
  seS.p = 1;
  lSE();
}

function renderSellosBocinaList(items) {
  const host = $('se-bocina-list');
  if (!host) return;

  if (!items.length) {
    host.innerHTML = '<div class="empty" style="padding:18px"><div class="empty-t">Sin bocinas</div><div class="empty-d">Ajusta búsqueda o importa CSV.</div></div>';
    return;
  }

  host.innerHTML = items.map((item) => {
    const selected = selectedSelloBocina && selectedSelloBocina.codigo_interno === item.codigo_interno;
    return `<button type="button" class="sellos-bocina-item ${selected ? 'is-selected' : ''}" onclick="pickSelloBocinaByCode('${h(item.codigo_interno || '')}')"><div class="title">${h(item.codigo_interno || '-')} · ${h(item.sku || '-')}</div><div class="meta">${h(item.material_sello || '-')} · ${h(item.medida || '-')} · Disponible: ${fm(item.stock || 0)} mm</div></button>`;
  }).join('');
}

function pickSelloBocinaByCode(code) {
  const item = sellosBocinasCache.find((entry) => (entry.codigo_interno || '') === code);
  if (!item) return;
  pickSelloBocina(item);
}

function pickSelloBocina(item) {
  selectedSelloBocina = item || null;
  if ($('se-bocina-sku')) $('se-bocina-sku').value = item?.sku || '';
  if ($('se-bocina-codigo')) $('se-bocina-codigo').value = item?.codigo_interno || '';

  if ($('se-selected-box')) {
    if (!item) {
      $('se-selected-box').textContent = 'Selecciona una bocina en la lista izquierda.';
    } else {
      $('se-selected-box').innerHTML = `<div style="font-size:15px;font-weight:700">${h(item.codigo_interno || '-')} · ${h(item.sku || '-')}</div><div style="margin-top:5px">${h(item.nombre || '')}</div><div style="margin-top:6px;color:var(--t1)">Material: ${h(item.material_sello || '-')} · Medida: ${h(item.medida || '-')} · Largo nominal: ${fm(item.largo_referencia_mm || 0)} mm</div>`;
    }
  }

  if ($('se-stock-info')) {
    if (item) {
      const extraCantidad = item.cantidad_bocinas != null ? ` · Bocinas: ${fm(item.cantidad_bocinas)}` : '';
      $('se-stock-info').textContent = `Stock disponible: ${fm(item.stock || 0)} mm · Interno: ${item.codigo_interno || '-'} · Material: ${item.material_sello || '-'}${extraCantidad}`;
      if (item.largo_referencia_mm && $('se-largo')) $('se-largo').value = item.largo_referencia_mm;
    } else {
      $('se-stock-info').textContent = 'Selecciona una bocina para ver stock disponible.';
    }
  }

  renderSellosBocinaList(sellosBocinasCache);
  updateSelloCalc();
}

async function searchSellosBocinas() {
  const query = ($('se-browse')?.value || '').trim();
  const data = await api('/api/sellos/bocinas?q=' + encodeURIComponent(query));
  if (!Array.isArray(data)) return;
  sellosBocinasCache = data;

  if (selectedSelloBocina) {
    const found = data.find((item) => item.codigo_interno === selectedSelloBocina.codigo_interno);
    selectedSelloBocina = found || null;
  }

  renderSellosBocinaList(sellosBocinasCache);
}

async function lSE() {
  initSellosSection();
  const p = new URLSearchParams({
    page: seS.p,
    per_page: 50,
    search: ($('se-s')?.value || '').trim()
  });
  const d = await api('/api/sellos?' + p);
  if (!d) return;

  const body = $('se-b');
  if (!body) return;

  sellosRowsCache = new Map();

  if (!Array.isArray(d.items) || !d.items.length) {
    body.innerHTML = '<tr><td colspan="9"><div class="empty"><div class="empty-t">Sin registros de sellos</div></div></td></tr>';
  } else {
    body.innerHTML = d.items.map((row) => {
      sellosRowsCache.set(row.id, row);
      return `<tr>
        <td class="m" style="font-size:11px">${h(row.fecha || '-')}</td>
        <td><div class="m" style="font-size:11px;font-weight:600">${h(row.bocina_codigo_interno || '-')} · ${h(row.bocina_sku || '-')}</div><div style="font-size:11px;color:var(--t3)">${h(row.bocina_descripcion || '')}</div></td>
        <td class="m" style="font-size:11px">${h(row.ot_id || '-')}</td>
        <td class="m" style="text-align:right;font-weight:700">${fm(row.cantidad_sellos || 0)}</td>
        <td class="m" style="text-align:right">${fm(row.largo_sello_mm || 0)} mm</td>
        <td class="m" style="text-align:right;color:var(--no);font-weight:700">-${fm(row.consumo_mm || 0)}</td>
        <td class="m" style="text-align:right">${fm(row.stock_actual_bocina || 0)}</td>
        <td style="max-width:260px;overflow:hidden;text-overflow:ellipsis" title="${h(row.observaciones || '')}">${h(row.observaciones || '-')}</td>
        <td style="text-align:center"><button class="bi" onclick="deleteSello(${row.id})" title="Eliminar" style="color:var(--no)">✕</button></td>
      </tr>`;
    }).join('');
  }

  if ($('se-total-sellos')) $('se-total-sellos').textContent = fm(d.resumen?.total_sellos || 0);
  if ($('se-total-mm')) $('se-total-mm').textContent = fm(d.resumen?.total_mm_consumidos || 0);
  if ($('se-rend')) $('se-rend').textContent = fm(d.resumen?.sellos_por_1000mm || 0);

  rP('se-p', d, seS, lSE);
}

async function migrarCodigosSellos() {
  const r = await api('/api/sellos/migrar-codigos', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ force_all: false })
  });

  if (r && r.ok) {
    toast(r.msg || 'Migración completada');
    await searchSellosBocinas();
  } else if (r) {
    toast(r.msg || 'No se pudo migrar códigos', 'err');
  }
}

async function importCsvSellos() {
  const defaultPath = 'C:\\Users\\bodega.NORTHCHROME\\Desktop\\Libro1.csv';
  const csvPath = prompt('Ruta completa del CSV de bocinas:', defaultPath);
  if (!csvPath) return;

  const r = await api('/api/sellos/importar-csv', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ csv_path: csvPath })
  });

  if (r && r.ok) {
    toast(r.msg || 'CSV importado');
    await searchSellosBocinas();
    await lSE();
  } else if (r) {
    toast(r.msg || 'No se pudo importar CSV', 'err');
  }
}

function openSelloIngresoModal() {
  if ($('si-fecha')) $('si-fecha').value = new Date().toISOString().split('T')[0];
  if ($('si-doc')) $('si-doc').value = '';
  if ($('si-material')) $('si-material').value = '';
  if ($('si-material-otro')) $('si-material-otro').value = '';
  if ($('si-sku')) $('si-sku').value = '';
  if ($('si-mi')) $('si-mi').value = '';
  if ($('si-me')) $('si-me').value = '';
  if ($('si-largo')) $('si-largo').value = '150';
  if ($('si-cantidad')) $('si-cantidad').value = '1';
  if ($('si-obs')) $('si-obs').value = '';
  if ($('si-packing')) $('si-packing').value = '';
  if ($('si-info')) $('si-info').textContent = 'Se generará un código interno NCB único por cada unidad.';
  updateSelloMaterialHelp();
  oM('m-sellos-ingreso');
}

function closeSelloIngresoModal() {
  cM('m-sellos-ingreso');
}

async function saveSelloIngreso() {
  const fecha = ($('si-fecha')?.value || '').trim();
  const referencia = ($('si-doc')?.value || '').trim();
  const material = resolveSelloIngresoMaterial();
  const sku = ($('si-sku')?.value || '').trim();
  const mi = ($('si-mi')?.value || '').trim();
  const me = ($('si-me')?.value || '').trim();
  const largo = parseFloat(($('si-largo')?.value || '0')) || 0;
  const cantidad = parseInt(($('si-cantidad')?.value || '0'), 10) || 0;
  const obs = ($('si-obs')?.value || '').trim();

  if (!fecha) return toast('Fecha requerida', 'err');
  if (!material) return toast('Material requerido', 'err');
  if (!mi || !me) return toast('Medida interna y externa requeridas', 'err');
  if (largo <= 0) return toast('Largo nominal inválido', 'err');
  if (cantidad <= 0) return toast('Cantidad de bocinas inválida', 'err');

  const r = await api('/api/sellos/ingresos', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      fecha,
      referencia_doc: referencia,
      material_sello: material,
      sku_proveedor: sku,
      medida_interna: mi,
      medida_externa: me,
      largo_nominal_mm: largo,
      cantidad_bocinas: cantidad,
      observaciones: obs
    })
  });

  if (r && r.ok) {
    toast(r.msg || 'Llegada registrada');
    if ($('si-info')) {
      const preview = Array.isArray(r.codigos_generados) ? r.codigos_generados.slice(0, 5).join(', ') : '';
      $('si-info').textContent = preview ? `Códigos generados: ${preview}${r.codigos_generados.length > 5 ? ' ...' : ''}` : 'Ingreso guardado.';
    }
    await searchSellosBocinas();
    closeSelloIngresoModal();
  } else if (r) {
    toast(r.msg || 'No se pudo registrar llegada', 'err');
  }
}

async function saveSelloIngresoPackingList() {
  const fecha = ($('si-fecha')?.value || '').trim();
  const referencia = ($('si-doc')?.value || '').trim();
  const texto = ($('si-packing')?.value || '').trim();
  const obs = ($('si-obs')?.value || '').trim();

  if (!fecha) return toast('Fecha requerida', 'err');
  if (!texto) return toast('Pega el texto del packing list', 'err');

  const r = await api('/api/sellos/ingresos/packing-list', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      fecha,
      referencia_doc: referencia,
      texto,
      observaciones: obs
    })
  });

  if (r && r.ok) {
    toast(r.msg || 'Packing list cargado');
    if ($('si-info')) {
      $('si-info').textContent = `Líneas cargadas: ${r.lineas_cargadas || 0} · Bocinas creadas: ${r.bocinas_creadas || 0}${(r.lineas_omitidas || 0) > 0 ? ` · Omitidas: ${r.lineas_omitidas}` : ''}`;
    }
    await searchSellosBocinas();
    closeSelloIngresoModal();
  } else if (r) {
    toast(r.msg || 'No se pudo cargar packing list', 'err');
  }
}

async function saveSelloProduccion() {
  const codigoInterno = ($('se-bocina-codigo')?.value || '').trim();
  const sku = ($('se-bocina-sku')?.value || '').trim();
  const fecha = ($('se-fecha')?.value || '').trim();
  const otId = ($('se-ot')?.value || '').trim();
  const cantidad = parseFloat(($('se-cantidad')?.value || '0')) || 0;
  const largo = parseFloat(($('se-largo')?.value || '0')) || 0;
  const obs = ($('se-obs')?.value || '').trim();

  if (!sku) return toast('Selecciona una bocina en la lista izquierda', 'err');
  if (!fecha) return toast('Fecha requerida', 'err');
  if (!otId) return toast('OT requerida para justificar consumo', 'err');
  if (cantidad <= 0) return toast('Cantidad de sellos inválida', 'err');
  if (largo <= 0) return toast('MM usados por sello inválido', 'err');

  const consumo = cantidad * largo;
  if (selectedSelloBocina && consumo > Number(selectedSelloBocina.stock || 0)) {
    return toast(`Stock insuficiente (${fm(selectedSelloBocina.stock || 0)} mm)`, 'err');
  }

  const r = await api('/api/sellos', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      bocina_codigo_interno: codigoInterno,
      bocina_sku: sku,
      fecha,
      ot_id: otId,
      cantidad_sellos: cantidad,
      largo_sello_mm: largo,
      observaciones: obs
    })
  });

  if (r && r.ok) {
    toast(r.msg || 'Registro creado');
    if ($('se-cantidad')) $('se-cantidad').value = '1';
    if ($('se-largo')) $('se-largo').value = '1';
    if ($('se-obs')) $('se-obs').value = '';
    if (selectedSelloBocina) {
      selectedSelloBocina.stock = Number(r.stock_bocina || 0);
    }
    updateSelloCalc();
    await searchSellosBocinas();
    seS.p = 1;
    await lSE();
  } else if (r) {
    toast(r.msg || 'No se pudo registrar', 'err');
  }
}

async function deleteSello(id) {
  if (!confirm('¿Eliminar este registro y restaurar stock de la bocina?')) return;
  const r = await api('/api/sellos/' + id, { method: 'DELETE' });
  if (r && r.ok) {
    toast(r.msg || 'Registro eliminado');
    await searchSellosBocinas();
    await lSE();
  } else if (r) {
    toast(r.msg || 'No se pudo eliminar', 'err');
  }
}

window.pickSelloBocinaByCode = pickSelloBocinaByCode;
window.searchSellosBocinas = searchSellosBocinas;
window.saveSelloProduccion = saveSelloProduccion;
window.searchSE = searchSE;
window.deleteSello = deleteSello;
window.lSE = lSE;
window.migrarCodigosSellos = migrarCodigosSellos;
window.importCsvSellos = importCsvSellos;
window.openSelloIngresoModal = openSelloIngresoModal;
window.closeSelloIngresoModal = closeSelloIngresoModal;
window.saveSelloIngreso = saveSelloIngreso;
window.saveSelloIngresoPackingList = saveSelloIngresoPackingList;
window.updateSelloMaterialHelp = updateSelloMaterialHelp;
window.selectSelloMaterial = selectSelloMaterial;
window.openNuevoInsumoDesdeSellos = openNuevoInsumoDesdeSellos;
window.toggleSellosGuide = toggleSellosGuide;
