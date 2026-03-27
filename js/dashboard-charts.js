// helpers for dashboard charts using Chart.js

let __categoryChart = null;
let __seriesChart = null;

/**
 * draws or updates the category distribution bar chart
 * data: [{nombre, cantidad}, ...]
 */
function renderCategoryChart(data) {
    const ctx = document.getElementById('d-cat-chart').getContext('2d');
    const labels = data.map(d => d.nombre);
    const values = data.map(d => d.cantidad);
    const colors = [
        'var(--ac)', 'var(--ok)', 'var(--in)', 'var(--wa)', 'var(--no)',
        '#a855f7', '#ec4899', '#14b8a6', '#facc15', '#3b82f6'
    ];
    const bg = labels.map((_,i)=>colors[i%colors.length]);
    const config = {
        type: 'bar',
        data: {
            labels,
            datasets: [{
                label: 'Productos por categoría',
                data: values,
                backgroundColor: bg,
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: { display: false },
                tooltip: { mode: 'index', intersect: false }
            },
            onClick: (evt,item) => {
                if (item.length>0) {
                    const idx = item[0].index;
                    const cat = labels[idx];
                    // when clicking on bar, apply filter
                    document.getElementById('dash-cat').value = cat;
                    loadDashboard();
                }
            }
        }
    };
    if (__categoryChart) {
        __categoryChart.data = config.data;
        __categoryChart.update();
    } else {
        __categoryChart = new Chart(ctx, config);
    }
}

/**
 * draws or updates ingresos vs consumos line chart
 * ingresos/consumos arrays have {period, total}
 */
function renderSeriesChart(ingresos, consumos) {
    const ctx = document.getElementById('d-series-chart').getContext('2d');
    // compute union of periods
    const periods = Array.from(new Set([...ingresos.map(i=>i.period), ...consumos.map(c=>c.period)])).sort((left, right) => {
        const leftMonthly = /^\d{4}-\d{2}$/.test(left || '');
        const rightMonthly = /^\d{4}-\d{2}$/.test(right || '');
        if (leftMonthly && rightMonthly) return left.localeCompare(right);
        if (leftMonthly) return -1;
        if (rightMonthly) return 1;
        return String(left || '').localeCompare(String(right || ''));
    });
    const ingMap = Object.fromEntries(ingresos.map(i=>[i.period,i.total]));
    const conMap = Object.fromEntries(consumos.map(c=>[c.period,c.total]));
    const ingValues = periods.map(p=>ingMap[p]||0);
    const conValues = periods.map(p=>conMap[p]||0);
    const config = {
        type: 'line',
        data: {
            labels: periods,
            datasets: [
                {
                    label: 'Ingresos',
                    data: ingValues,
                    borderColor: 'var(--ok)',
                    backgroundColor: 'var(--ok)33',
                    fill: true
                },
                {
                    label: 'Consumos',
                    data: conValues,
                    borderColor: 'var(--no)',
                    backgroundColor: 'var(--no)33',
                    fill: true
                }
            ]
        },
        options: {
            responsive: true,
            plugins: { tooltip: { mode: 'index', intersect: false } }
        }
    };
    if (__seriesChart) {
        __seriesChart.data = config.data;
        __seriesChart.update();
    } else {
        __seriesChart = new Chart(ctx, config);
    }
}

// global accessors used by expandChart
window.getCategoryChart = () => __categoryChart;
window.getSeriesChart = () => __seriesChart;
