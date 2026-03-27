function rP(el, data, state, fn) {
  const { page: rawPg, total: t, per_page: pp, total_pages: rawTp } = data;
  const tp = Math.max(1, parseInt(rawTp || 1, 10));
  const pg = Math.min(tp, Math.max(1, parseInt(rawPg || 1, 10)));
  const maxVisible = 10;

  const s = t > 0 ? ((pg - 1) * pp + 1) : 0;
  const e = t > 0 ? Math.min(pg * pp, t) : 0;

  const blockStart = Math.floor((pg - 1) / maxVisible) * maxVisible + 1;
  const blockEnd = Math.min(tp, blockStart + maxVisible - 1);
  const pageButtons = [];
  for (let p = blockStart; p <= blockEnd; p++) {
    pageButtons.push(`<button class="pb ${p === pg ? 'on' : ''}" data-action="page" data-page="${p}">${p}</button>`);
  }

  const controlsHtml = `<div class="pi">${s}-${e} de ${fm(t)}</div><div class="pbs"><button class="pb" data-action="first" ${pg <= 1 ? 'disabled' : ''}>«</button><button class="pb" data-action="prev" ${pg <= 1 ? 'disabled' : ''}>‹</button>${pageButtons.join('')}<button class="pb" data-action="next" ${pg >= tp ? 'disabled' : ''}>›</button><button class="pb" data-action="last" ${pg >= tp ? 'disabled' : ''}>»</button></div>`;

  const bottom = $(el);
  if (!bottom) return;

  const topId = `${el}-top`;
  let top = $(topId);
  const host = bottom.parentElement;
  if (host && !top) {
    top = document.createElement('div');
    top.id = topId;
    top.className = 'pag pag-top';
    const tableWrap = host.querySelector('.ts');
    if (tableWrap) host.insertBefore(top, tableWrap);
    else host.insertBefore(top, bottom);
  }

  bottom.innerHTML = controlsHtml;
  if (top) top.innerHTML = controlsHtml;

  const goToPage = (nextPage) => {
    state.p = Math.min(tp, Math.max(1, nextPage));
    fn();
    const activeView = document.querySelector('.pg.on');
    if (activeView && typeof activeView.scrollIntoView === 'function') {
      activeView.scrollIntoView({ behavior: 'smooth', block: 'start' });
    } else {
      window.scrollTo({ top: 0, behavior: 'smooth' });
    }
  };

  [bottom, top].filter(Boolean).forEach((root) => {
    root.querySelectorAll('.pb[data-action]').forEach((btn) => {
      if (btn.disabled) return;
      btn.onclick = () => {
        const action = btn.dataset.action;
        if (action === 'first') goToPage(1);
        else if (action === 'prev') goToPage(pg - 1);
        else if (action === 'next') goToPage(pg + 1);
        else if (action === 'last') goToPage(tp);
        else if (action === 'page') goToPage(parseInt(btn.dataset.page || pg, 10));
      };
    });
  });
}