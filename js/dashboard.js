// dashboard.js - logic for loading and rendering dashboard data

// make alias so old callers (core.js) still work
const lD = loadDashboard;

// global helper to expand arbitrary content
function expandWidget(title, htmlContent) {
  $('md-title').textContent = title;
  $('md-body').innerHTML = htmlContent;
  oM('m-dash');
}

// chart expansion helper
function expandChart(chart, title) {
  if (!chart) return;
  const img = new Image();
  img.src = chart.toBase64Image();
  expandWidget(title, `<div style="text-align:center"><img src="${img.src}" style="max-width:100%;"/></div>`);
}

async function loadDashboard() {
  // collect filters
  const params = new URLSearchParams();
  const keyMap = { 'dash-from': 'from', 'dash-to': 'to', 'dash-cat': 'category' };
  Object.keys(keyMap).forEach(id => {
    const el = $(id);
    if (el && el.value) params.append(keyMap[id], el.value);
  });

  const d = await api('/api/dashboard' + (params.toString() ? '?' + params.toString() : ''));
  if (!d) return;

  const acumuladoInfo = d.total_consumos_acumulados > 0 && !params.get('from') && !params.get('to')
    ? `<div class="card" style="padding:8px 12px;font-size:11px;color:var(--t2)">Consumo acumulado incorporado en metricas y graficos: <span class="m" style="color:var(--no)">${fm(d.total_consumos_acumulados)}</span></div>`
    : '';

  // warning about invalid rows
  if (d.invalid_items && d.invalid_items > 0) {
    $('d-warning').innerHTML = `<div class="card" style="background:var(--no)20;color:var(--no);padding:8px;display:flex;justify-content:space-between;align-items:center"><span>Productos sin SKU: ${d.invalid_items}</span><button class="btn bs no" onclick="cleanInvalid()">Limpiar</button></div>${acumuladoInfo}`;
  } else {
    $('d-warning').innerHTML = acumuladoInfo;
  }


  const cr = d.criticos + d.items_sin_stock;
  const bg = $('badge-c');
  if (bg) {
    if (cr > 0) {
      bg.style.display = 'inline';
      bg.textContent = cr;
    } else {
      bg.style.display = 'none';
    }
  }

  // populate category filter dropdown once
  if ($('dash-cat') && !$('dash-cat').dataset.populated) {
    const opts = d.categorias.map(c => `<option value="${h(c.nombre)}">${h(c.nombre)}</option>`).join('');
    $('dash-cat').innerHTML = '<option value="">Todas categorías</option>' + opts;
    $('dash-cat').dataset.populated = '1';
  }

  // top 10 items
  // stats cards with expand button
  $('d-stats').innerHTML = [
    { i: '📦', c: 'var(--ac)', l: 'Total Productos', v: fm(d.total_items) },
    { i: '✅', c: 'var(--ok)', l: 'Con Stock', v: fm(d.items_con_stock) },
    { i: '💰', c: 'var(--in)', l: 'Valor Inventario', v: fp(d.valor_total) },
    { i: '⚠️', c: 'var(--no)', l: 'Criticos', v: d.criticos + d.items_sin_stock }
  ].map(s => `
      <div class="card dash-card">
        <span class="expand" onclick="expandWidget('${h(s.l)}','<div style=&quot;font-size:24px;&quot;>${s.v}</div>');event.stopPropagation()">🔍</span>
        <div class="si" style="background:${s.c}22;color:${s.c}">${s.i}</div>
        <div class="sv">${s.v}</div>
        <div class="sl">${s.l}</div>
      </div>
    `).join('');

  // previously top_consumo rendered
  $('d-top').innerHTML = d.top_consumo.map(r => `<tr><td class="m" style="font-size:10px">${r.sku}</td><td>${h(r.nombre)||'-'}</td><td class="m" style="font-weight:600">${fm(r.total)}</td></tr>`).join('')
    || '<tr><td colspan="3" style="text-align:center;padding:20px;color:var(--t3)">Sin datos</td></tr>';

  // simple bar distribution (backup)
  const mx = Math.max(1, ...d.categorias.map(c => c.cantidad));
  const cols = ['var(--ac)', 'var(--ok)', 'var(--in)', 'var(--wa)', 'var(--no)', '#a855f7', '#ec4899', '#14b8a6'];
  $('d-chart').innerHTML = '<div class="ct">Distribucion</div>' + d.categorias.slice(0, 12).map((c, i) => `<div class="cbar" style="height:${Math.max(5, (c.cantidad / mx) * 130)}px;background:${cols[i % cols.length]}" title="${c.nombre}: ${c.cantidad}"></div>`).join('');

  // render Chart.js charts
  if (typeof renderCategoryChart === 'function') {
    renderCategoryChart(d.categorias);
  }
  if (typeof renderSeriesChart === 'function') {
    renderSeriesChart(d.series_ingresos || [], d.series_consumos || []);
  }

  // critical stock table
  $('d-crit').innerHTML = d.criticos_detail.length === 0
    ? '<tr><td colspan="5"><div class="empty"><div class="empty-t">Sin alertas</div></div></td></tr>'
    : d.criticos_detail.map(p => `<tr><td class="m" style="font-size:10px">${p.sku}</td><td style="font-weight:500">${h(p.nombre)}</td><td class="m" style="font-weight:700;color:var(--no)">${p.stock}</td><td><span class="badge b-in">${h(p.categoria)||'-'}</span></td><td><button class="btn bsm bg" onclick="openNewIng('${p.sku}')">+ Reponer</button></td></tr>`).join('');

  // restore charts visibility from localStorage
  restoreChartsState();
}

// perform cleanup of invalid items via API
async function cleanInvalid() {
  if (!confirm('Eliminar todos los productos sin SKU?')) return;
  const r = await api('/api/items/clean', { method: 'POST' });
  if (r && r.ok) {
    toast(`Eliminados ${r.deleted||0} registros`);
    loadDashboard();
  } else if (r) {
    toast(r.msg,'err');
  }
}

// toggle charts visibility and save preference
function toggleChartsView() {
  const container = $('charts-container');
  const btn = $('toggle-charts');
  if (!container || !btn) return;
  
  const isHidden = container.style.display === 'none';
  container.style.display = isHidden ? 'block' : 'none';
  btn.textContent = isHidden ? '⬆ Comprimir' : '⬇ Expandir';
  localStorage.setItem('dashboard-charts-expanded', isHidden);
}

// restore charts visibility from localStorage on dashboard load
function restoreChartsState() {
  const expanded = localStorage.getItem('dashboard-charts-expanded') === 'true';
  if (expanded) {
    const container = $('charts-container');
    const btn = $('toggle-charts');
    if (container) container.style.display = 'block';
    if (btn) btn.textContent = '⬆ Comprimir';
  }
}
