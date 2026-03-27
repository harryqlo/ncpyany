/**
 * Generador de Reportes de Mantenimiento
 * Crea reportes HTML exportables con gráficos y análisis
 */

const MantReportes = {
  /**
   * Genera reporte visual de costos por herramienta
   */
  async generarReporteCostosHTML(desde, hasta) {
    const respuesta = await apiMantReporteCostos(desde, hasta);
    if (!respuesta?.ok) {
      toast('Error generando reporte', 'err');
      return;
    }

    const stats = respuesta;
    const hoy = new Date().toLocaleDateString('es-ES');

    const html = `
      <!DOCTYPE html>
      <html lang="es">
      <head>
        <meta charset="UTF-8">
        <title>Reporte de Costos de Mantenimiento</title>
        <style>
          body { font-family: Arial, sans-serif; margin: 20px; color: #333; }
          .header { text-align: center; margin-bottom: 30px; border-bottom: 3px solid #0066cc; padding-bottom: 20px; }
          .header h1 { margin: 0; color: #0066cc; }
          .header .subtitle { color: #666; margin: 10px 0 0 0; font-size: 14px; }
          .period-info { background: #f5f5f5; padding: 15px; border-radius: 8px; margin-bottom: 20px; }
          .period-info p { margin: 5px 0; }
          .stats-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 15px; margin-bottom: 30px; }
          .stat-box { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 8px; text-align: center; }
          .stat-label { font-size: 12px; opacity: 0.9; }
          .stat-value { font-size: 28px; font-weight: bold; margin: 10px 0; }
          table { width: 100%; border-collapse: collapse; margin-top: 20px; }
          th { background: #0066cc; color: white; padding: 12px; text-align: left; font-weight: bold; }
          td { padding: 12px; border-bottom: 1px solid #ddd; }
          tr:nth-child(even) { background: #f9f9f9; }
          .footer { margin-top: 40px; padding-top: 20px; border-top: 1px solid #ddd; font-size: 12px; color: #666; text-align: center; }
          .currency { color: #00aa00; font-weight: bold; }
          @media print { body { margin: 0; } .no-print { display: none; } }
        </style>
      </head>
      <body>
        <div class="header">
          <h1>📊 REPORTE DE MANTENIMIENTO</h1>
          <p class="subtitle">Costos y Análisis de Herramientas</p>
        </div>

        <div class="period-info">
          <p><strong>Período:</strong> ${desde} al ${hasta}</p>
          <p><strong>Generado:</strong> ${hoy}</p>
          <p><strong>Registros de Mantenimiento:</strong> ${stats.cantidad_registros}</p>
        </div>

        <div class="stats-grid">
          <div class="stat-box" style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);">
            <div class="stat-label">Costo Total</div>
            <div class="stat-value">$${(stats.costo_total || 0).toLocaleString()}</div>
          </div>
          <div class="stat-box" style="background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);">
            <div class="stat-label">Promedio por Mantenimiento</div>
            <div class="stat-value">$${stats.cantidad_registros > 0 ? ((stats.costo_total || 0) / stats.cantidad_registros).toLocaleString() : '0'}</div>
          </div>
          <div class="stat-box" style="background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);">
            <div class="stat-label">Registros</div>
            <div class="stat-value">${stats.cantidad_registros}</div>
          </div>
          <div class="stat-box" style="background: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%);">
            <div class="stat-label">Herramientas Atendidas</div>
            <div class="stat-value">${[...new Set(stats.reporte.map(r => r.sku))].length}</div>
          </div>
        </div>

        <table>
          <thead>
            <tr>
              <th>SKU</th>
              <th>Herramienta</th>
              <th>Tipo</th>
              <th>Cantidad de Mant.</th>
              <th>Costo Total</th>
              <th>Promedio por Mant.</th>
              <th>Horas Totales</th>
            </tr>
          </thead>
          <tbody>
            ${stats.reporte.map(r => `
              <tr>
                <td><strong>${r.sku}</strong></td>
                <td>${r.herramienta}</td>
                <td>${r.tipo}</td>
                <td>${r.cantidad}</td>
                <td class="currency">$${(r.costo_total || 0).toLocaleString()}</td>
                <td>$${(r.costo_promedio || 0).toLocaleString()}</td>
                <td>${(r.horas || 0).toFixed(1)}h</td>
              </tr>
            `).join('')}
          </tbody>
        </table>

        <div class="footer no-print">
          <button onclick="window.print()" style="padding:8px 16px;background:#0066cc;color:white;border:none;border-radius:4px;cursor:pointer;font-size:14px">🖨 Imprimir</button>
          <button onclick="descargarReporteCSV()" style="padding:8px 16px;background:#00aa00;color:white;border:none;border-radius:4px;cursor:pointer;margin-left:10px;font-size:14px">📥 Descargar CSV</button>
        </div>

        <div class="footer">
          <p>Reporte generado automáticamente por North Chrome v2 - Sistema de Gestión de Bodega</p>
          <p>Generado: ${new Date().toLocaleString('es-ES')}</p>
        </div>
      </body>
      </html>
    `;

    // Abrir en nueva ventana
    const ventana = window.open('', 'Reporte Mantenimiento');
    ventana.document.open();
    ventana.document.write(html);
    ventana.document.close();
  },

  /**
   * Genera reporte de herramientas en mantenimiento
   */
  async generarReporteHerramientasEnMant() {
    const respuesta = await api('/api/herramientas?condicion=mantenimiento&per_page=100');
    if (!respuesta?.ok) {
      toast('Error cargando datos', 'err');
      return;
    }

    const herramientas = respuesta.herramientas || [];
    const hoy = new Date().toLocaleDateString('es-ES');

    const html = `
      <!DOCTYPE html>
      <html lang="es">
      <head>
        <meta charset="UTF-8">
        <title>Herramientas en Mantenimiento</title>
        <style>
          body { font-family: Arial, sans-serif; margin: 20px; color: #333; }
          .header { text-align: center; margin-bottom: 30px; border-bottom: 3px solid #ff6600; padding-bottom: 20px; }
          .header h1 { margin: 0; color: #ff6600; }
          .alert-box { background: #fffacd; padding: 15px; border-left: 4px solid #ff6600; margin-bottom: 20px; border-radius: 4px; }
          table { width: 100%; border-collapse: collapse; margin-top: 20px; }
          th { background: #ff6600; color: white; padding: 12px; text-align: left; font-weight: bold; }
          td { padding: 12px; border-bottom: 1px solid #ddd; }
          tr:nth-child(even) { background: #f9f9f9; }
          .sku { color: #0066cc; font-weight: bold; }
          .footer { margin-top: 40px; padding-top: 20px; border-top: 1px solid #ddd; font-size: 12px; color: #666; text-align: center; }
          @media print { body { margin: 0; } }
        </style>
      </head>
      <body>
        <div class="header">
          <h1>🔧 HERRAMIENTAS EN MANTENIMIENTO</h1>
          <p>Estado actual de herramientas que requieren atención</p>
        </div>

        <div class="alert-box">
          <strong>⚠️ Total de herramientas en mantenimiento:</strong> ${herramientas.length}
          <br><strong>Generado:</strong> ${hoy}
        </div>

        <table>
          <thead>
            <tr>
              <th>SKU</th>
              <th>Nombre</th>
              <th>Categoría</th>
              <th>Ubicación</th>
              <th>Estado</th>
              <th>Observaciones</th>
            </tr>
          </thead>
          <tbody>
            ${herramientas.map(h => `
              <tr>
                <td class="sku">${h.sku}</td>
                <td>${h.nombre}</td>
                <td>${h.categoria || '-'}</td>
                <td>${h.ubicacion || '-'}</td>
                <td><strong>${h.condicion}</strong></td>
                <td>${h.observaciones || '-'}</td>
              </tr>
            `).join('')}
          </tbody>
        </table>

        <div class="footer">
          <button onclick="window.print()" style="padding:8px 16px;background:#ff6600;color:#1f130c;border:none;border-radius:4px;cursor:pointer">🖨 Imprimir</button>
          <p>Reporte generado automáticamente por North Chrome v2</p>
          <p>${new Date().toLocaleString('es-ES')}</p>
        </div>
      </body>
      </html>
    `;

    const ventana = window.open('', 'Herramientas en Mantenimiento');
    ventana.document.open();
    ventana.document.write(html);
    ventana.document.close();
  },

  /**
   * Genera reporte de alertas de calibración
   */
  async generarReporteAlertasCalibración() {
    const respuesta = await apiMantAlertas(365);
    if (!respuesta?.ok) {
      toast('Error cargando alertas', 'err');
      return;
    }

    const alertas = respuesta.alertas || [];
    const hoy = new Date().toLocaleDateString('es-ES');

    const criticas = alertas.filter(a => a.urgencia === 'crítica').length;
    const proximas = alertas.filter(a => a.urgencia === 'próxima').length;

    const html = `
      <!DOCTYPE html>
      <html lang="es">
      <head>
        <meta charset="UTF-8">
        <title>Alertas de Calibración</title>
        <style>
          body { font-family: Arial, sans-serif; margin: 20px; color: #333; }
          .header { text-align: center; margin-bottom: 30px; border-bottom: 3px solid #d9534f; padding-bottom: 20px; }
          .header h1 { margin: 0; color: #d9534f; }
          .stats { display: grid; grid-template-columns: 1fr 1fr; gap: 15px; margin-bottom: 30px; }
          .stat-alert { padding: 15px; border-radius: 4px; }
          .stat-critica { background: rgba(217, 83, 79, 0.1); border-left: 4px solid #d9534f; }
          .stat-proxima { background: rgba(240, 173, 78, 0.1); border-left: 4px solid #f0ad4e; }
          table { width: 100%; border-collapse: collapse; }
          th { background: #d9534f; color: white; padding: 12px; text-align: left; }
          td { padding: 12px; border-bottom: 1px solid #ddd; }
          tr:nth-child(even) { background: #f9f9f9; }
          .critica { color: #d9534f; font-weight: bold; }
          .proxima { color: #f0ad4e; font-weight: bold; }
          .footer { margin-top: 40px; padding-top: 20px; border-top: 1px solid #ddd; font-size: 12px; color: #666; text-align: center; }
        </style>
      </head>
      <body>
        <div class="header">
          <h1>⚠️ ALERTAS DE CALIBRACIÓN</h1>
          <p>Estado de herramientas que requieren calibración</p>
        </div>

        <div class="stats">
          <div class="stat-alert stat-critica">
            <div style="font-size:14px;font-weight:bold">🚨 CRÍTICAS (Vencidas)</div>
            <div style="font-size:32px;font-weight:bold;color:#d9534f;margin-top:10px">${criticas}</div>
          </div>
          <div class="stat-alert stat-proxima">
            <div style="font-size:14px;font-weight:bold">📋 PRÓXIMAS A VENCER</div>
            <div style="font-size:32px;font-weight:bold;color:#f0ad4e;margin-top:10px">${proximas}</div>
          </div>
        </div>

        <table>
          <thead>
            <tr>
              <th>SKU</th>
              <th>Nombre</th>
              <th>Última Calibración</th>
              <th>Frecuencia</th>
              <th>Estado</th>
              <th>Urgencia</th>
            </tr>
          </thead>
          <tbody>
            ${alertas.map(a => `
              <tr>
                <td><strong>${a.sku}</strong></td>
                <td>${a.nombre}</td>
                <td>${a.ultima_calibracion || 'Nunca'}</td>
                <td>${a.frecuencia_dias} días</td>
                <td>${a.estado}</td>
                <td class="${a.urgencia === 'crítica' ? 'critica' : 'proxima'}">${a.urgencia.toUpperCase()}</td>
              </tr>
            `).join('')}
          </tbody>
        </table>

        <div class="footer">
          <button onclick="window.print()" style="padding:8px 16px;background:#d9534f;color:white;border:none;border-radius:4px;cursor:pointer">🖨 Imprimir</button>
          <p>Reporte de alertas generado automáticamente por North Chrome v2</p>
          <p>${new Date().toLocaleString('es-ES')}</p>
        </div>
      </body>
      </html>
    `;

    const ventana = window.open('', 'Alertas Calibración');
    ventana.document.open();
    ventana.document.write(html);
    ventana.document.close();
  }
};

// Exportar funciones globales
if (typeof window !== 'undefined') {
  window.MantReportes = MantReportes;
}
