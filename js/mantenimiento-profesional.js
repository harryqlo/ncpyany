/**
 * Sistema Profesional de Mantenimiento de Herramientas
 * Formulario completo con carga de fotos comprimidas, seguimiento y reportes
 */

// ================ CONSTANTES Y CONFIGURACIÓN ================

const MANT_CONFIG = {
  tipos: ['preventivo', 'correctivo', 'calibracion'],
  tiposFoto: ['antes', 'durante', 'despues', 'documentacion'],
  maxFotosMB: 10,
  compresionCalidad: 85,
};

// ================ ESTADO GLOBAL ================

const MantState = {
  mantenimientoActual: null,
  fotosSeleccionadas: [],
  enviandoFotos: false,
  filtros: {
    tipo: null,
    fechaDesde: null,
    fechaHasta: null,
  }
};

// ================ API CALLS ================

async function apiMantRegistrarCompleto(herramientaId, datos) {
  /**
   * Registra un mantenimiento completo con todos los detalles
   */
  return await api(`/api/mantenimiento/registrar-completo/${herramientaId}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(datos)
  });
}

async function apiMantAgregarFoto(mantenimientoId, archivo, tipoFoto, descripcion = '') {
  /**
   * Carga una foto comprimida a un mantenimiento
   */
  const formData = new FormData();
  formData.append('foto', archivo);
  formData.append('tipo_foto', tipoFoto);
  formData.append('descripcion', descripcion);

  const response = await fetch(`/api/mantenimiento/agregar-foto/${mantenimientoId}`, {
    method: 'POST',
    body: formData
  });

  return await response.json();
}

async function apiMantListarFotos(mantenimientoId) {
  /**
   * Obtiene todas las fotos de un mantenimiento
   */
  return await api(`/api/mantenimiento/fotos/${mantenimientoId}`);
}

async function apiMantDetalle(mantenimientoId) {
  /**
   * Obtiene detalle completo de un mantenimiento
   */
  return await api(`/api/mantenimiento/detalle/${mantenimientoId}`);
}

async function apiMantHistorial(herramientaId, tipo = null, limit = 50) {
  /**
   * Obtiene historial de mantenimientos
   */
  let url = `/api/mantenimiento/historial/${herramientaId}?limit=${limit}`;
  if (tipo) url += `&tipo=${tipo}`;
  return await api(url);
}

async function apiMantAlertas(dias = 30) {
  /**
   * Obtiene alertas de calibración próximas a vencer
   */
  return await api(`/api/mantenimiento/alertas-vencimiento?dias=${dias}`);
}

async function apiMantReporteCostos(desde, hasta, tipo = null) {
  /**
   * Obtiene reporte de costos de mantenimiento
   */
  let url = `/api/mantenimiento/reporte-costos?desde=${desde}&hasta=${hasta}`;
  if (tipo) url += `&tipo=${tipo}`;
  return await api(url);
}

function escaparHtml(texto) {
  if (texto === null || texto === undefined) return '';
  return String(texto)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

function construirHtmlInformeMantenimiento(mantenimiento, fotos = []) {
  const fechaImpresion = new Date().toLocaleString('es-CL');
  const filasFotos = fotos.length > 0
    ? fotos.map((foto, idx) => `
      <tr>
        <td>${idx + 1}</td>
        <td>${escaparHtml(foto.tipo || '-')}</td>
        <td>${escaparHtml(foto.nombre || '-')}</td>
        <td>${escaparHtml(foto.descripcion || '-')}</td>
        <td>${foto.tamaño_kb ? `${foto.tamaño_kb} KB` : '-'}</td>
      </tr>
    `).join('')
    : '<tr><td colspan="5" style="text-align:center;color:#666">Sin evidencias fotográficas registradas</td></tr>';

  return `
    <!DOCTYPE html>
    <html lang="es">
    <head>
      <meta charset="UTF-8" />
      <title>Informe de Mantenimiento #${mantenimiento.id}</title>
      <style>
        body { font-family: Arial, sans-serif; margin: 24px; color: #222; }
        .header { border-bottom: 2px solid #111; padding-bottom: 10px; margin-bottom: 18px; }
        .header h1 { margin: 0; font-size: 20px; }
        .header p { margin: 4px 0 0 0; font-size: 12px; color: #555; }
        .section { margin-top: 16px; }
        .section h2 { font-size: 14px; margin: 0 0 8px 0; text-transform: uppercase; }
        .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 8px 16px; font-size: 12px; }
        .row { margin-bottom: 6px; }
        .label { color: #666; font-size: 11px; text-transform: uppercase; }
        .value { font-weight: 600; }
        table { width: 100%; border-collapse: collapse; font-size: 12px; }
        th, td { border: 1px solid #bbb; padding: 6px; text-align: left; }
        th { background: #efefef; }
        .signatures { margin-top: 36px; display: grid; grid-template-columns: 1fr 1fr; gap: 28px; }
        .sign-box { border-top: 1px solid #333; padding-top: 6px; font-size: 12px; text-align: center; }
        .print-actions { margin-top: 16px; }
        .print-actions button { padding: 8px 14px; border: none; background: #1f4bd6; color: #fff; border-radius: 4px; cursor: pointer; }
        @media print {
          .print-actions { display: none; }
          body { margin: 10mm; }
        }
      </style>
    </head>
    <body>
      <div class="header">
        <h1>Informe de Mantenimiento de Herramienta</h1>
        <p>Folio: #${mantenimiento.id} · Generado: ${fechaImpresion}</p>
      </div>

      <div class="section">
        <h2>Datos generales</h2>
        <div class="grid">
          <div class="row"><div class="label">Herramienta</div><div class="value">${escaparHtml(mantenimiento?.herramienta?.nombre || '-')}</div></div>
          <div class="row"><div class="label">SKU</div><div class="value">${escaparHtml(mantenimiento?.herramienta?.sku || '-')}</div></div>
          <div class="row"><div class="label">Tipo</div><div class="value">${escaparHtml(mantenimiento.tipo || '-')}</div></div>
          <div class="row"><div class="label">Fecha mantenimiento</div><div class="value">${escaparHtml(mantenimiento.fecha || '-')}</div></div>
          <div class="row"><div class="label">Responsable</div><div class="value">${escaparHtml(mantenimiento.responsable || '-')}</div></div>
          <div class="row"><div class="label">Técnico</div><div class="value">${escaparHtml(mantenimiento.tecnico || '-')}</div></div>
          <div class="row"><div class="label">Taller</div><div class="value">${escaparHtml(mantenimiento.taller || '-')}</div></div>
          <div class="row"><div class="label">Orden de trabajo</div><div class="value">${escaparHtml(mantenimiento.numero_orden || '-')}</div></div>
        </div>
      </div>

      <div class="section">
        <h2>Detalle técnico</h2>
        <div class="row"><div class="label">Descripción</div><div class="value">${escaparHtml(mantenimiento.descripcion || '-')}</div></div>
        <div class="row"><div class="label">Observaciones</div><div class="value">${escaparHtml(mantenimiento.observaciones || '-')}</div></div>
      </div>

      <div class="section">
        <h2>Costos y tiempos</h2>
        <div class="grid">
          <div class="row"><div class="label">Presupuesto</div><div class="value">$${Number(mantenimiento.presupuesto || 0).toLocaleString('es-CL')}</div></div>
          <div class="row"><div class="label">Costo final</div><div class="value">$${Number(mantenimiento.costo_final || 0).toLocaleString('es-CL')}</div></div>
          <div class="row"><div class="label">Tiempo estimado</div><div class="value">${Number(mantenimiento.tiempo_estimado || 0).toFixed(1)} h</div></div>
          <div class="row"><div class="label">Tiempo real</div><div class="value">${Number(mantenimiento.tiempo_real || 0).toFixed(1)} h</div></div>
        </div>
      </div>

      <div class="section">
        <h2>Evidencias fotográficas</h2>
        <table>
          <thead>
            <tr>
              <th>#</th>
              <th>Tipo</th>
              <th>Nombre archivo</th>
              <th>Descripción</th>
              <th>Tamaño</th>
            </tr>
          </thead>
          <tbody>${filasFotos}</tbody>
        </table>
      </div>

      <div class="signatures">
        <div class="sign-box">Firma Responsable de Mantenimiento</div>
        <div class="sign-box">Firma Recepción de Equipo</div>
      </div>

      <div class="print-actions">
        <button onclick="window.print()">Imprimir informe</button>
      </div>
    </body>
    </html>
  `;
}

async function imprimirInformeMantenimiento(mantenimientoId) {
  const detalle = await apiMantDetalle(mantenimientoId);
  if (!detalle?.ok || !detalle.mantenimiento) {
    toast('No se pudo obtener detalle para imprimir', 'err');
    return;
  }

  const respFotos = await apiMantListarFotos(mantenimientoId);
  const fotos = respFotos?.ok ? (respFotos.fotos || []) : [];

  const html = construirHtmlInformeMantenimiento(detalle.mantenimiento, fotos);
  const ventana = window.open('', `InformeMantenimiento_${mantenimientoId}`);
  if (!ventana) {
    toast('Bloqueador de ventanas: habilita pop-ups para imprimir', 'err');
    return;
  }
  ventana.document.open();
  ventana.document.write(html);
  ventana.document.close();
}

// ================ UI - FORMULARIO PROFESIONAL ================

function abrirFormularioMantenimiento(herramientaId, herramientaNombre) {
  /**
   * Abre el formulario profesional de registro de mantenimiento
   */
  MantState.mantenimientoActual = { herramientaId, herramientaNombre };
  MantState.fotosSeleccionadas = [];

  // Limpiar formulario
  document.getElementById('mant-form-herr-nombre').textContent = herramientaNombre;
  const mantFormId = document.getElementById('mant-form-id');
  if (mantFormId) mantFormId.value = '';
  document.getElementById('mant-form-tipo').value = 'preventivo';
  document.getElementById('mant-form-descripcion').value = '';
  document.getElementById('mant-form-fecha').value = new Date().toISOString().split('T')[0];
  document.getElementById('mant-form-responsable').value = '';
  document.getElementById('mant-form-tecnico').value = '';
  document.getElementById('mant-form-taller').value = '';
  document.getElementById('mant-form-orden-trabajo').value = '';
  document.getElementById('mant-form-presupuesto').value = '';
  document.getElementById('mant-form-costo-final').value = '';
  document.getElementById('mant-form-tiempo-est').value = '';
  document.getElementById('mant-form-tiempo-real').value = '';
  document.getElementById('mant-form-proveedor').value = '';
  document.getElementById('mant-form-proxima-fecha').value = '';
  document.getElementById('mant-form-observaciones').value = '';
  document.getElementById('mant-form-nota-interna').value = '';

  // Limpiar galería de fotos
  document.getElementById('mant-galeria-previsualizacion').innerHTML = '';
  document.getElementById('mant-contador-fotos').textContent = '0 fotos';
  actualizarGaleriaPreview();

  oM('m-mant-formulario');
}

function agregarFotoSeleccionada(event) {
  /**
   * Maneja la selección de archivos de foto
   */
  const files = event.target.files;
  if (!files.length) return;

  Array.from(files).forEach(file => {
    // Validar tamaño
    if (file.size > MANT_CONFIG.maxFotosMB * 1024 * 1024) {
      toast(`Archivo demasiado grande: ${(file.size / 1024 / 1024).toFixed(1)}MB`, 'err');
      return;
    }

    // Crear preview
    const reader = new FileReader();
    reader.onload = (e) => {
      const fotoObj = {
        id: Math.random(),
        archivo: file,
        preview: e.target.result,
        tipo: 'documentacion',
        descripcion: '',
        comprimida: false,
        tamaño_original: file.size
      };

      MantState.fotosSeleccionadas.push(fotoObj);
      actualizarGaleriaPreview();
    };
    reader.readAsDataURL(file);
  });
}

function actualizarGaleriaPreview() {
  /**
   * Actualiza la galería de previsualizaciones
   */
  const galeria = document.getElementById('mant-galeria-previsualizacion');
  const contador = document.getElementById('mant-contador-fotos');

  if (MantState.fotosSeleccionadas.length === 0) {
    galeria.innerHTML = '<div style="text-align:center;color:var(--t3);padding:20px">Clic para cargar fotos</div>';
    contador.textContent = '0 fotos';
    return;
  }

  galeria.innerHTML = MantState.fotosSeleccionadas.map((foto, idx) => `
    <div class="mant-foto-preview" style="position:relative;overflow:hidden;border-radius:8px;background:var(--bg2)">
      <img src="${foto.preview}" style="width:100%;height:100%;object-fit:cover" alt="Preview">
      <div style="position:absolute;top:0;right:0;background:rgba(0,0,0,0.7);padding:4px 8px;border-radius:0 8px 0 0">
        <small style="color:white;font-weight:600">${foto.tipo}</small>
      </div>
      <div style="position:absolute;bottom:0;left:0;right:0;background:linear-gradient(to top, rgba(0,0,0,0.8), transparent);padding:12px;color:white;font-size:11px">
        <input type="text" class="mant-foto-desc" placeholder="Descripción..." 
               value="${foto.descripcion}" 
               onchange="MantState.fotosSeleccionadas[${idx}].descripcion = this.value"
               style="width:100%;background:rgba(255,255,255,0.2);border:1px solid rgba(255,255,255,0.3);color:white;padding:4px;border-radius:4px;font-size:10px;margin-bottom:4px">
        <select class="mant-foto-tipo" onchange="MantState.fotosSeleccionadas[${idx}].tipo = this.value"
                style="width:100%;background:rgba(255,255,255,0.2);border:1px solid rgba(255,255,255,0.3);color:white;padding:4px;border-radius:4px;font-size:10px;margin-bottom:4px">
          ${MANT_CONFIG.tiposFoto.map(t => `<option value="${t}" ${t === foto.tipo ? 'selected' : ''}>${t}</option>`).join('')}
        </select>
        <div style="display:flex;gap:4px">
          <button class="btn-mini" onclick="MantState.fotosSeleccionadas.splice(${idx}, 1); actualizarGaleriaPreview()" 
                  style="flex:1;padding:4px;font-size:9px">🗑 Eliminar</button>
          <button class="btn-mini" style="flex:1;padding:4px;font-size:9px">
            ${foto.tamaño_original ? (foto.tamaño_original / 1024 / 1024).toFixed(1) + 'MB' : 'sin cargarse'}
          </button>
        </div>
      </div>
    </div>
  `).join('');

  galeria.style.display = 'grid';
  galeria.style.gridTemplateColumns = 'repeat(auto-fill, minmax(120px, 1fr))';
  galeria.style.gap = '8px';

  contador.textContent = `${MantState.fotosSeleccionadas.length} foto${MantState.fotosSeleccionadas.length !== 1 ? 's' : ''}`;
}

async function guardarMantenimientoCompleto(imprimirAlFinal = false) {
  /**
   * Guarda el mantenimiento con todas sus fotos
   */
  const herramientaId = MantState.mantenimientoActual.herramientaId;

  // Validar campos
  const tipo = document.getElementById('mant-form-tipo').value;
  const descripcion = document.getElementById('mant-form-descripcion').value?.trim();
  const fecha = document.getElementById('mant-form-fecha').value;
  const responsable = document.getElementById('mant-form-responsable').value?.trim();

  if (!descripcion || !fecha || !responsable) {
    toast('Completa campos requeridos: Descripción, Fecha y Responsable', 'err');
    return;
  }

  // Preparar datos
  const datosMantenimiento = {
    tipo,
    descripcion,
    fecha_mantenimiento: fecha,
    responsable_nombre: responsable,
    tecnico_nombre: document.getElementById('mant-form-tecnico').value || null,
    taller_nombre: document.getElementById('mant-form-taller').value || null,
    numero_orden_trabajo: document.getElementById('mant-form-orden-trabajo').value || null,
    presupuesto: parseFloat(document.getElementById('mant-form-presupuesto').value) || 0,
    costo_final: parseFloat(document.getElementById('mant-form-costo-final').value) || 0,
    tiempo_estimado_horas: parseFloat(document.getElementById('mant-form-tiempo-est').value) || 0,
    tiempo_real_horas: parseFloat(document.getElementById('mant-form-tiempo-real').value) || 0,
    proveedor_nombre: document.getElementById('mant-form-proveedor').value || null,
    proxima_fecha: document.getElementById('mant-form-proxima-fecha').value || null,
    observaciones: document.getElementById('mant-form-observaciones').value || null,
    nota_interna: document.getElementById('mant-form-nota-interna').value || null,
  };

  try {
    // 1. Registrar mantenimiento
    const respMant = await apiMantRegistrarCompleto(herramientaId, datosMantenimiento);
    if (!respMant || !respMant.ok) {
      toast(respMant?.msg || 'Error registrando mantenimiento', 'err');
      return;
    }

    const mantenimientoId = respMant.mantenimiento_id;
    toast(`✓ Mantenimiento #${mantenimientoId} registrado`);

    // 2. Cargar fotos
    if (MantState.fotosSeleccionadas.length > 0) {
      MantState.enviandoFotos = true;
      let fotosExitosas = 0;

      for (const foto of MantState.fotosSeleccionadas) {
        const respFoto = await apiMantAgregarFoto(
          mantenimientoId,
          foto.archivo,
          foto.tipo,
          foto.descripcion
        );

        if (respFoto?.ok) {
          fotosExitosas++;
        }
      }

      toast(`✓ ${fotosExitosas}/${MantState.fotosSeleccionadas.length} fotos guardadas (comprimidas)`);
      MantState.enviandoFotos = false;
    }

    // 3. Cerrar modal y refrescar
    cM('m-mant-formulario');
    await refreshPaniolHerramientasViews();

    if (imprimirAlFinal) {
      await imprimirInformeMantenimiento(mantenimientoId);
    } else {
      const deseaImprimir = window.confirm('¿Deseas imprimir el informe de este mantenimiento?');
      if (deseaImprimir) {
        await imprimirInformeMantenimiento(mantenimientoId);
      }
    }

  } catch (e) {
    console.error('Error guardando mantenimiento:', e);
    toast('Error en el proceso: ' + e.message, 'err');
  }
}

// ================ UI - HISTORIAL Y CONSULTAS ================

async function mostrarHistorialMantenimiento(herramientaId, herramientaNombre) {
  /**
   * Muestra el historial completo de mantenimientos
   */
  document.getElementById('mant-hist-herr-nombre').textContent = herramientaNombre;

  const respuesta = await apiMantHistorial(herramientaId);
  if (!respuesta?.ok) {
    toast('Error cargando historial', 'err');
    return;
  }

  const mantenimientos = respuesta.mantenimientos || [];
  const container = document.getElementById('mant-hist-lista');

  if (mantenimientos.length === 0) {
    container.innerHTML = '<div style="text-align:center;color:var(--t3);padding:20px">Sin registros de mantenimiento</div>';
    oM('m-mant-historial');
    return;
  }

  container.innerHTML = mantenimientos.map(m => `
    <div class="mant-hist-item" style="padding:12px;border-bottom:1px solid var(--bd);cursor:pointer" 
         onclick="mostrarDetalleMantenimiento(${m.id})">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px">
        <div style="font-weight:600;color:var(--ac)">#${m.id} • ${m.tipo}</div>
        <div style="font-size:11px;color:var(--t3)">${m.fecha}</div>
      </div>
      <div style="font-size:12px;margin-bottom:4px">${m.descripcion?.substring(0, 60)}...</div>
      <div style="display:flex;gap:12px;font-size:11px;color:var(--t3)">
        <span>💰 ${m.costo ? '$' + m.costo.toLocaleString() : 'Sin costo'}</span>
        <span>📷 ${m.cantidad_fotos || 0} fotos</span>
        <span>👤 ${m.responsable || 'N/A'}</span>
      </div>
    </div>
  `).join('');

  oM('m-mant-historial');
}

async function mostrarDetalleMantenimiento(mantenimientoId) {
  /**
   * Muestra el detalle completo de un mantenimiento con fotos
   */
  const respuesta = await apiMantDetalle(mantenimientoId);
  if (!respuesta?.ok) {
    toast('Error cargando detalle', 'err');
    return;
  }

  const m = respuesta.mantenimiento;
  const stats = respuesta.estadisticas;

  // Rellenar información
  document.getElementById('mant-det-titulo').innerHTML = `
    <div>
      <div style="font-weight:600;color:var(--ac)">#${m.id} • ${m.tipo.toUpperCase()}</div>
      <div style="font-size:12px;color:var(--t3)">${m.herramienta.nombre} (${m.herramienta.sku})</div>
    </div>
    <button class="btn bsm" onclick="imprimirInformeMantenimiento(${m.id})" style="margin-left:8px">Imprimir informe</button>
  `;

  const infoHtml = `
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;font-size:12px">
      <div>
        <label style="color:var(--t3)">Fecha</label>
        <div style="font-weight:600">${m.fecha}</div>
      </div>
      <div>
        <label style="color:var(--t3)">Responsable</label>
        <div style="font-weight:600">${m.responsable || '-'}</div>
      </div>
      <div>
        <label style="color:var(--t3)">Técnico</label>
        <div style="font-weight:600">${m.tecnico || '-'}</div>
      </div>
      <div>
        <label style="color:var(--t3)">Taller</label>
        <div style="font-weight:600">${m.taller || '-'}</div>
      </div>
      <div>
        <label style="color:var(--t3)">Orden Trabajo</label>
        <div style="font-weight:600">${m.numero_orden || '-'}</div>
      </div>
      <div>
        <label style="color:var(--t3)">Próximo Mantenimiento</label>
        <div style="font-weight:600">${m.proxima_fecha || '-'}</div>
      </div>
      <div style="grid-column:1/-1">
        <label style="color:var(--t3)">Descripción</label>
        <div style="font-weight:600;line-height:1.4">${m.descripcion}</div>
      </div>
      ${m.observaciones ? `<div style="grid-column:1/-1">
        <label style="color:var(--t3)">Observaciones</label>
        <div style="font-size:11px;line-height:1.4">${m.observaciones}</div>
      </div>` : ''}
    </div>

    <div style="border-top:1px solid var(--bd);margin-top:12px;padding-top:12px;display:grid;grid-template-columns:1fr 1fr;gap:12px;font-size:12px">
      <div>
        <label style="color:var(--t3)">Presupuesto</label>
        <div style="font-weight:600;color:var(--ok)">$${(m.presupuesto || 0).toLocaleString()}</div>
      </div>
      <div>
        <label style="color:var(--t3)">Costo Final</label>
        <div style="font-weight:600;color:${stats.costo_diferencia && stats.costo_diferencia > 0 ? 'var(--no)' : 'var(--ok)'}">${(m.costo_final || 0).toLocaleString()}</div>
      </div>
      <div>
        <label style="color:var(--t3)">Estimado (hrs)</label>
        <div style="font-weight:600">${(m.tiempo_estimado || 0).toFixed(1)}h</div>
      </div>
      <div>
        <label style="color:var(--t3)">Real (hrs)</label>
        <div style="font-weight:600">${(m.tiempo_real || 0).toFixed(1)}h</div>
      </div>
    </div>
  `;

  document.getElementById('mant-det-info').innerHTML = infoHtml;

  // Cargar fotos
  const respFotos = await apiMantListarFotos(mantenimientoId);
  const fotosHtml = respFotos?.ok && respFotos.fotos?.length > 0
    ? `<div style="display:grid;grid-template-columns:repeat(auto-fill, minmax(150px, 1fr));gap:8px;margin-top:12px">
         ${respFotos.fotos.map(f => `
           <div style="cursor:pointer;border-radius:8px;overflow:hidden;background:var(--bg2)" 
                onclick="abrirFotoCompleta('${f.url_completa}', '${f.nombre}')">
             <img src="data:image/webp;base64,${f.miniatura_b64}" style="width:100%;height:120px;object-fit:cover">
             <div style="padding:6px;font-size:9px;background:var(--bg1)">
               <div style="font-weight:600;color:var(--ac)">${f.tipo}</div>
               <div style="color:var(--t3)">${f.tamaño_kb}KB</div>
             </div>
           </div>
         `).join('')}
       </div>`
    : '<div style="color:var(--t3);font-size:12px;padding:12px;text-align:center">Sin fotos</div>';

  document.getElementById('mant-det-fotos').innerHTML = fotosHtml;

  oM('m-mant-detalle');
}

function abrirFotoCompleta(urlFoto, nombre) {
  /**
   * Abre una foto en tamaño completo
   */
  document.getElementById('mant-foto-completa-img').src = urlFoto;
  document.getElementById('mant-foto-completa-nombre').textContent = nombre;
  oM('m-mant-foto-completa');
}

// ================ ALERTAS Y REPORTES ================

async function mostrarAlertasCalibración() {
  /**
   * Muestra alertas de herramientas próximas a vencer calibración
   */
  const respuesta = await apiMantAlertas(30);
  if (!respuesta?.ok) {
    toast('Error cargando alertas', 'err');
    return;
  }

  const alertas = respuesta.alertas || [];

  if (alertas.length === 0) {
    toast('✓ Todas las calibraciones están al día', 'ok');
    return;
  }

  const html = `
    <div style="max-height:400px;overflow-y:auto">
      ${alertas.map(a => `
        <div style="padding:12px;border-bottom:1px solid var(--bd);background:${a.urgencia === 'crítica' ? 'rgba(255, 0, 0, 0.1)' : 'rgba(255, 150, 0, 0.1)'}">
          <div style="font-weight:600;color:${a.urgencia === 'crítica' ? 'var(--no)' : 'var(--wa)'}">${a.sku} • ${a.nombre}</div>
          <div style="font-size:11px;color:var(--t3);margin-top:4px">
            Última calibración: ${a.ultima_calibracion || 'Nunca'}
            ${a.dias_vencido ? `<br>Vencido: ${a.dias_vencido} días` : ''}
          </div>
        </div>
      `).join('')}
    </div>
  `;

  // Mostrar en modal
  const container = document.getElementById('mant-alertas-lista');
  if (container) {
    container.innerHTML = html;
    oM('m-mant-alertas');
  }
}

async function generarReporteCostos() {
  /**
   * Genera y muestra reporte de costos de mantenimiento
   */
  const hoy = new Date().toISOString().split('T')[0];
  const hace90dias = new Date(Date.now() - 90 * 24 * 60 * 60 * 1000).toISOString().split('T')[0];

  const respuesta = await apiMantReporteCostos(hace90dias, hoy);
  if (!respuesta?.ok) {
    toast('Error generando reporte', 'err');
    return;
  }

  const stats = respuesta;
  console.table(stats.reporte);
  toast(`Reporte: $${(stats.costo_total || 0).toLocaleString()} en ${stats.cantidad_registros} mantenimientos`);
}

// ================ EXPORTAR ================
if (typeof window !== 'undefined') {
  window.abrirFormularioMantenimiento = abrirFormularioMantenimiento;
  window.agregarFotoSeleccionada = agregarFotoSeleccionada;
  window.guardarMantenimientoCompleto = guardarMantenimientoCompleto;
  window.mostrarHistorialMantenimiento = mostrarHistorialMantenimiento;
  window.mostrarDetalleMantenimiento = mostrarDetalleMantenimiento;
  window.abrirFotoCompleta = abrirFotoCompleta;
  window.imprimirInformeMantenimiento = imprimirInformeMantenimiento;
  window.mostrarAlertasCalibración = mostrarAlertasCalibración;
  window.generarReporteCostos = generarReporteCostos;
}
