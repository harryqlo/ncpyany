async function openKardex(sku, nombre) {
  kxS.sku = sku;
  kxS.p = 1;
  $('kx-t').textContent = 'Kardex: ' + sku;
  $('kx-sub').textContent = nombre || '';
  await loadKardex();
  oM('m-kardex');
}

let kardexItemsCache = [];

async function loadKardex() {
  const d = await api(`/api/items/${encodeURIComponent(kxS.sku)}/kardex?page=${kxS.p}&per_page=100`);
  if (!d) return;
  kardexItemsCache = d.items || [];
  $('kx-b').innerHTML = d.items.length === 0
    ? '<tr><td colspan="8"><div class="empty"><div class="empty-t">Sin movimientos</div></div></td></tr>'
    : d.items.map((m, index) => {
      const isI = m.tipo === 'INGRESO';
      const action = !isI ? `<button class="btn bsm bs" onclick="editKardexConsumo(${index})">Editar</button>` : '';
      return `<tr><td class="m" style="font-size:10px">${m.fecha || 'Saldo inicial'}</td><td><span class="badge ${isI ? 'b-ok' : 'b-no'}">${m.tipo}</span></td><td class="m" style="text-align:right;color:var(--ok)">${isI ? '+' + fm(m.cant) : ''}</td><td class="m" style="text-align:right;color:var(--no)">${!isI ? '-' + fm(m.cant) : ''}</td><td class="m" style="text-align:right;font-weight:700">${fm(m.saldo)}</td><td style="font-size:10px">${m.ref1 || ''} ${m.ref2 ? '(' + m.ref2 + ')' : ''} ${m.ref3 || ''}</td><td style="font-size:10px;color:var(--t3);max-width:150px;overflow:hidden;text-overflow:ellipsis">${m.obs || ''}</td><td style="text-align:right">${action}</td></tr>`;
    }).join('');
  rP('kx-p', d, kxS, loadKardex);
}


function editKardexConsumo(index) {
  const row = kardexItemsCache[index];
  if (!row || row.tipo !== 'CONSUMO') return toast('Consumo no encontrado', 'err');
  if (typeof openConsumoEditorForRow !== 'function') return toast('Editor no disponible', 'err');
  openConsumoEditorForRow({ ...row, descripcion: $('kx-sub')?.textContent || '' });
}