/**
 * Icon Utilities - North Chrome v2
 * Sistema centralizado para gestión de iconos SVG
 * 
 * Funcionalidades:
 * - Rendereo consistente de SVGs
 * - Aplicación de clases de accesibilidad
 * - Fallback a Unicode si es necesario
 * - Factory functions para crear iconos
 */

const IconUtils = {
  /**
   * Definición de iconos SVG - ViewBox estándar 24×24
   * Todos los iconos usan el mismo estándar para escalabilidad
   */
  icons: {

    // ── NAVEGACIÓN ────────────────────────────────────────────────
    dashboard: {
      name: 'Dashboard',
      svg: '<path d="M12 7.01L12.01 6.99889"/><path d="M16 9.01L16.01 8.99889"/><path d="M8 9.01L8.01 8.99889"/><path d="M18 13.01L18.01 12.9989"/><path d="M6 13.01L6.01 12.9989"/><path d="M17 17.01L17.01 16.9989"/><path d="M7 17.01L7.01 16.9989"/><path d="M12 17L13 11"/><path d="M8.5 20.001H4C2.74418 18.3295 2 16.2516 2 14C2 8.47715 6.47715 4 12 4C17.5228 4 22 8.47715 22 14C22 16.2516 21.2558 18.3295 20 20.001L15.5 20"/><path d="M12 23C13.6569 23 15 21.6569 15 20C15 18.3431 13.6569 17 12 17C10.3431 17 9 18.3431 9 20C9 21.6569 10.3431 23 12 23Z"/>'
    },
    inventario: {
      name: 'Inventario',
      svg: '<path d="M3 21v-13l9 -4l9 4v13"/><path d="M13 13h4v8h-10v-6h6"/><path d="M13 21v-9a1 1 0 0 0 -1 -1h-2a1 1 0 0 0 -1 1v3"/>'
    },
    componentes: {
      name: 'Componentes',
      viewBox: '0 0 256 256',
      fill: true,
      svg: '<path d="M205.66,50.32a8,8,0,0,1,0,11.32l-56,56a8,8,0,0,1-11.32-11.31l56-56A8,8,0,0,1,205.66,50.32ZM248,58.41a50.13,50.13,0,0,1-14.77,35.66L180,147.3A15.86,15.86,0,0,1,168.69,152H152v16.83a16,16,0,0,1-3.25,9.66,8.08,8.08,0,0,1-.72.83l-8,8a16,16,0,0,1-22.62,0L98.7,168.6l-77,77.06a8,8,0,0,1-11.32-11.32l77.05-77.05-18.7-18.71a16,16,0,0,1,0-22.63l8-8a8,8,0,0,1,.82-.72A16.14,16.14,0,0,1,87.17,104H104V87.3A15.92,15.92,0,0,1,108.68,76l53.24-53.23A50.43,50.43,0,0,1,248,58.41Zm-16,0a34.43,34.43,0,0,0-58.77-24.35L120,87.3V104a16,16,0,0,1-16,16H87.28L80,127.27,128.72,176l7.28-7.28V152a16,16,0,0,1,16-16h16.69l53.23-53.24A34.21,34.21,0,0,0,232,58.41Z"/>'
    },
    ingresos: {
      name: 'Ingresos',
      svg: '<path d="M4 18v3h16v-14l-8 -4l-8 4v3"/><path d="M4 14h9"/><path d="M10 11l3 3l-3 3"/>'
    },
    consumos: {
      name: 'Consumos',
      svg: '<path d="M4 19v2h16v-14l-8 -4l-8 4v2"/><path d="M13 14h-9"/><path d="M7 11l-3 3l3 3"/>'
    },
    ordenes: {
      name: 'Órdenes de Trabajo',
      svg: '<path d="M3 21h18"/><path d="M5 21v-12l5 4v-4l5 4h4"/><path d="M19 21v-8l-1.436 -9.574a.5 .5 0 0 0 -.495 -.426h-1.145a.5 .5 0 0 0 -.494 .418l-1.43 8.582"/><path d="M9 17h1"/><path d="M14 17h1"/>'
    },
    usuarios: {
      name: 'Usuarios',
      viewBox: '0 0 256 256',
      fill: true,
      svg: '<path d="M117.25,157.92a60,60,0,1,0-66.5,0A95.83,95.83,0,0,0,3.53,195.63a8,8,0,1,0,13.4,8.74,80,80,0,0,1,134.14,0,8,8,0,0,0,13.4-8.74A95.83,95.83,0,0,0,117.25,157.92ZM40,108a44,44,0,1,1,44,44A44.05,44.05,0,0,1,40,108Zm210.14,98.7a8,8,0,0,1-11.07-2.33A79.83,79.83,0,0,0,172,168a8,8,0,0,1,0-16,44,44,0,1,0-16.34-84.87,8,8,0,1,1-5.94-14.85,60,60,0,0,1,55.53,105.64,95.83,95.83,0,0,1,47.22,37.71A8,8,0,0,1,250.14,206.7Z"/>'
    },
    auditorias: {
      name: 'Auditorías',
      svg: '<path d="M13 15.5v-6.5a1 1 0 0 1 1 -1h6a1 1 0 0 1 1 1v4"/><path d="M18 8v-3a1 1 0 0 0 -1 -1h-13a1 1 0 0 0 -1 1v12a1 1 0 0 0 1 1h7"/><path d="M16 9h2"/><path d="M15 19l2 2l4 -4"/>'
    },
    paniol: {
      name: 'Dashboard Pañol',
      viewBox: '0 0 256 256',
      fill: true,
      svg: '<path d="M224,64H176V56a24,24,0,0,0-24-24H104A24,24,0,0,0,80,56v8H32A16,16,0,0,0,16,80V192a16,16,0,0,0,16,16H224a16,16,0,0,0,16-16V80A16,16,0,0,0,224,64ZM96,56a8,8,0,0,1,8-8h48a8,8,0,0,1,8,8v8H96ZM224,80v32H192v-8a8,8,0,0,0-16,0v8H80v-8a8,8,0,0,0-16,0v8H32V80Zm0,112H32V128H64v8a8,8,0,0,0,16,0v-8h96v8a8,8,0,0,0,16,0v-8h32v64Z"/>'
    },
    chevronDown: {
      name: 'Chevron Abajo',
      svg: '<path d="M7 7l5 5l5 -5"/><path d="M7 13l5 5l5 -5"/>'
    },
    chevronRight: {
      name: 'Chevron Derecha',
      svg: '<path d="M7 7l5 5l-5 5"/><path d="M13 7l5 5l-5 5"/>'
    },

    // ── ACCIONES PRINCIPALES ─────────────────────────────────────
    plus: {
      name: 'Agregar',
      svg: '<path d="M9 5h-2a2 2 0 0 0 -2 2v12a2 2 0 0 0 2 2h10a2 2 0 0 0 2 -2v-12a2 2 0 0 0 -2 -2h-2"/><path d="M9 5a2 2 0 0 1 2 -2h2a2 2 0 0 1 2 2a2 2 0 0 1 -2 2h-2a2 2 0 0 1 -2 -2"/><path d="M10 14h4"/><path d="M12 12v4"/>'
    },
    cancel: {
      name: 'Cancelar',
      svg: '<path d="M3 12a9 9 0 1 0 18 0a9 9 0 1 0 -18 0"/><path d="M18.364 5.636l-12.728 12.728"/>'
    },
    x: {
      name: 'Cerrar',
      svg: '<path d="M18 6l-12 12"/><path d="M6 6l12 12"/>'
    },
    check: {
      name: 'Confirmar',
      svg: '<path d="M7 12l5 5l10 -10"/><path d="M2 12l5 5m5 -5l5 -5"/>'
    },
    download: {
      name: 'Descargar',
      svg: '<path d="M19 18a3.5 3.5 0 0 0 0 -7h-1a5 4.5 0 0 0 -11 -2a4.6 4.4 0 0 0 -2.1 8.4"/><path d="M12 13l0 9"/><path d="M9 19l3 3l3 -3"/>'
    },
    edit: {
      name: 'Editar',
      fill: true,
      svg: '<path d="M8 7a1 1 0 0 1 -1 1h-1a1 1 0 0 0 -1 1v9a1 1 0 0 0 1 1h9a1 1 0 0 0 1 -1v-1a1 1 0 0 1 2 0v1a3 3 0 0 1 -3 3h-9a3 3 0 0 1 -3 -3v-9a3 3 0 0 1 3 -3h1a1 1 0 0 1 1 1"/><path d="M14.596 5.011l4.392 4.392l-6.28 6.303a1 1 0 0 1 -.708 .294h-3a1 1 0 0 1 -1 -1v-3a1 1 0 0 1 .294 -.708zm6.496 -2.103a3.097 3.097 0 0 1 .165 4.203l-.164 .18l-.693 .694l-4.387 -4.387l.695 -.69a3.1 3.1 0 0 1 4.384 0"/>'
    },
    exportCsv: {
      name: 'Exportar CSV',
      svg: '<path d="M14 3v4a1 1 0 0 0 1 1h4"/><path d="M17 21h-10a2 2 0 0 1 -2 -2v-14a2 2 0 0 1 2 -2h7l5 5v11a2 2 0 0 1 -2 2"/><path d="M9 15h6"/><path d="M12.5 17.5l2.5 -2.5l-2.5 -2.5"/>'
    },
    filter: {
      name: 'Filtrar',
      svg: '<path d="M4 4h16v2.172a2 2 0 0 1 -.586 1.414l-4.414 4.414v7l-6 2v-8.5l-4.48 -4.928a2 2 0 0 1 -.52 -1.345v-2.227"/>'
    },
    refresh: {
      name: 'Actualizar',
      svg: '<path d="M20 11a8.1 8.1 0 0 0 -15.5 -2m-.5 -4v4h4"/><path d="M4 13a8.1 8.1 0 0 0 15.5 2m.5 4v-4h-4"/>'
    },
    save: {
      name: 'Guardar',
      svg: '<path d="M6 4h10l4 4v10a2 2 0 0 1 -2 2h-12a2 2 0 0 1 -2 -2v-12a2 2 0 0 1 2 -2"/><path d="M10 14a2 2 0 1 0 4 0a2 2 0 1 0 -4 0"/><path d="M14 4l0 4l-6 0l0 -4"/>'
    },
    search: {
      name: 'Buscar',
      svg: '<path d="M3 10a7 7 0 1 0 14 0a7 7 0 1 0 -14 0"/><path d="M21 21l-6 -6"/>'
    },
    settings: {
      name: 'Configuración',
      svg: '<path d="M10.325 4.317c.426 -1.756 2.924 -1.756 3.35 0a1.724 1.724 0 0 0 2.573 1.066c1.543 -.94 3.31 .826 2.37 2.37a1.724 1.724 0 0 0 1.065 2.572c1.756 .426 1.756 2.924 0 3.35a1.724 1.724 0 0 0 -1.066 2.573c.94 1.543 -.826 3.31 -2.37 2.37a1.724 1.724 0 0 0 -2.572 1.065c-.426 1.756 -2.924 1.756 -3.35 0a1.724 1.724 0 0 0 -2.573 -1.066c-1.543 .94 -3.31 -.826 -2.37 -2.37a1.724 1.724 0 0 0 -1.065 -2.572c-1.756 -.426 -1.756 -2.924 0 -3.35a1.724 1.724 0 0 0 1.066 -2.573c-.94 -1.543 .826 -3.31 2.37 -2.37c1 .608 2.296 .07 2.572 -1.065"/><path d="M9 12a3 3 0 1 0 6 0a3 3 0 0 0 -6 0"/>'
    },
    sort: {
      name: 'Ordenar',
      svg: '<path d="M4 6l9 0"/><path d="M4 12l7 0"/><path d="M4 18l7 0"/><path d="M15 15l3 3l3 -3"/><path d="M18 6l0 12"/>'
    },
    delete: {
      name: 'Eliminar',
      svg: '<path d="M4 7l16 0"/><path d="M10 11l0 6"/><path d="M14 11l0 6"/><path d="M5 7l1 12a2 2 0 0 0 2 2h8a2 2 0 0 0 2 -2l1 -12"/><path d="M9 7v-3a1 1 0 0 1 1 -1h4a1 1 0 0 1 1 1v3"/>'
    },
    upload: {
      name: 'Subir',
      svg: '<path d="M7 18a4.6 4.4 0 0 1 0 -9a5 4.5 0 0 1 11 2h1a3.5 3.5 0 0 1 0 7h-1"/><path d="M9 15l3 -3l3 3"/><path d="M12 12l0 9"/>'
    },
    eye: {
      name: 'Ver',
      svg: '<path d="M10 12a2 2 0 1 0 4 0a2 2 0 0 0 -4 0"/><path d="M21 12c-2.4 4 -5.4 6 -9 6c-3.6 0 -6.6 -2 -9 -6c2.4 -4 5.4 -6 9 -6c3.6 0 6.6 2 9 6"/>'
    },
    menu: {
      name: 'Menú',
      svg: '<path d="M3 6l18 0"/><path d="M3 12l18 0"/><path d="M3 18l18 0"/>'
    },

    // ── ESTADO Y FEEDBACK ────────────────────────────────────────
    statusAvailable: {
      name: 'Disponible',
      svg: '<path d="M3 13a2 2 0 0 1 2 -2h10a2 2 0 0 1 2 2v6a2 2 0 0 1 -2 2h-10a2 2 0 0 1 -2 -2l0 -6"/><path d="M9 16a1 1 0 1 0 2 0a1 1 0 0 0 -2 0"/><path d="M13 11v-4a4 4 0 1 1 8 0v4"/>'
    },
    statusCheckCircle: {
      name: 'Check Círculo',
      svg: '<path d="M3 12a9 9 0 1 0 18 0a9 9 0 1 0 -18 0"/><path d="M9 12l2 2l4 -4"/>'
    },
    statusDamaged: {
      name: 'Dañado',
      svg: '<path d="M8 17a2 2 0 1 0 4 0a2 2 0 1 0 -4 0"/><path d="M7 6l4 5h1a2 2 0 0 1 2 2v4h-2m-4 0h-5m0 -6h8m-6 0v-5m2 0h-4"/><path d="M14 8v-2"/><path d="M19 12h2"/><path d="M17.5 15.5l1.5 1.5"/><path d="M17.5 8.5l1.5 -1.5"/>'
    },
    statusDecommissioned: {
      name: 'De Baja',
      svg: '<path d="M11 7h8a1 1 0 0 1 1 1v7c0 .27 -.107 .516 -.282 .696"/><path d="M16 16h-11a1 1 0 0 1 -1 -1v-7a1 1 0 0 1 1 -1h2"/><path d="M7 16v4"/><path d="M7.5 16l4.244 -4.244"/><path d="M13.745 9.755l2.755 -2.755"/><path d="M13.5 16l1.249 -1.249"/><path d="M16.741 12.759l3.259 -3.259"/><path d="M4 13.5l4.752 -4.752"/><path d="M17 17v3"/><path d="M5 20h4"/><path d="M15 20h4"/><path d="M17 7v-2"/><path d="M3 3l18 18"/>'
    },
    statusError: {
      name: 'Error',
      svg: '<path d="M4 8v-2a2 2 0 0 1 2 -2h2"/><path d="M4 16v2a2 2 0 0 0 2 2h2"/><path d="M16 4h2a2 2 0 0 1 2 2v2"/><path d="M16 20h2a2 2 0 0 0 2 -2v-2"/><path d="M9 10h.01"/><path d="M15 10h.01"/><path d="M9.5 15.05a3.5 3.5 0 0 1 5 0"/>'
    },
    statusWarningTriangle: {
      name: 'Alerta Triángulo',
      svg: '<path d="M12 9v4"/><path d="M10.363 3.591l-8.106 13.534a1.914 1.914 0 0 0 1.636 2.871h16.214a1.914 1.914 0 0 0 1.636 -2.87l-8.106 -13.536a1.914 1.914 0 0 0 -3.274 0"/><path d="M12 16h.01"/>'
    },
    statusInProgress: {
      name: 'En Progreso',
      svg: '<path d="M10 20.777a8.942 8.942 0 0 1 -2.48 -.969"/><path d="M14 3.223a9.003 9.003 0 0 1 0 17.554"/><path d="M4.579 17.093a8.961 8.961 0 0 1 -1.227 -2.592"/><path d="M3.124 10.5c.16 -.95 .468 -1.85 .9 -2.675l.169 -.305"/><path d="M6.907 4.579a8.954 8.954 0 0 1 3.093 -1.356"/>'
    },
    statusInUse: {
      name: 'En Uso',
      svg: '<path d="M16 12l4 -4a2.828 2.828 0 1 0 -4 -4l-4 4m-2 2l-7 7v4h4l7 -7"/><path d="M14.5 5.5l4 4"/><path d="M12 8l-5 -5m-2 2l-2 2l5 5"/><path d="M7 8l-1.5 1.5"/><path d="M16 12l5 5m-2 2l-2 2l-5 -5"/><path d="M16 17l-1.5 1.5"/><path d="M3 3l18 18"/>'
    },
    statusInfo: {
      name: 'Información',
      svg: '<path d="M3 12a9 9 0 1 0 18 0a9 9 0 0 0 -18 0"/><path d="M12 9h.01"/><path d="M11 12h1v4h1"/>'
    },
    statusPending: {
      name: 'Pendiente',
      svg: '<path d="M3 12a9 9 0 1 0 18 0a9 9 0 0 0 -18 0"/><path d="M12 7v5l3 3"/>'
    },
    statusSuccess: {
      name: 'Éxito',
      svg: '<path d="M10 20.777a8.942 8.942 0 0 1 -2.48 -.969"/><path d="M14 3.223a9.003 9.003 0 0 1 0 17.554"/><path d="M4.579 17.093a8.961 8.961 0 0 1 -1.227 -2.592"/><path d="M3.124 10.5c.16 -.95 .468 -1.85 .9 -2.675l.169 -.305"/><path d="M6.907 4.579a8.954 8.954 0 0 1 3.093 -1.356"/><path d="M9 12l2 2l4 -4"/>'
    },
    statusUnavailable: {
      name: 'No Disponible',
      svg: '<path d="M5 13a2 2 0 0 1 2 -2h10a2 2 0 0 1 2 2v6a2 2 0 0 1 -2 2h-10a2 2 0 0 1 -2 -2v-6"/><path d="M11 16a1 1 0 1 0 2 0a1 1 0 0 0 -2 0"/><path d="M8 11v-4a4 4 0 1 1 8 0v4"/>'
    },
    statusWarning: {
      name: 'Advertencia',
      fill: true,
      svg: '<path d="M12 1.67c.955 0 1.845 .467 2.39 1.247l.105 .16l8.114 13.548a2.914 2.914 0 0 1 -2.307 4.363l-.195 .008h-16.225a2.914 2.914 0 0 1 -2.582 -4.2l.099 -.185l8.11 -13.538a2.914 2.914 0 0 1 2.491 -1.403zm.01 13.33l-.127 .007a1 1 0 0 0 0 1.986l.117 .007l.127 -.007a1 1 0 0 0 0 -1.986l-.117 -.007zm-.01 -7a1 1 0 0 0 -.993 .883l-.007 .117v4l.007 .117a1 1 0 0 0 1.986 0l.007 -.117v-4l-.007 -.117a1 1 0 0 0 -.993 -.883z"/>'
    },
    statusXCircle: {
      name: 'X Círculo',
      svg: '<path d="M3 12a9 9 0 1 0 18 0a9 9 0 1 0 -18 0"/><path d="M10 10l4 4m0 -4l-4 4"/>'
    },

    // ── PAÑOL / PRÉSTAMOS ────────────────────────────────────────
    activeLoan: {
      name: 'Préstamo Activo',
      svg: '<path d="M13 9l7.383 7.418c.823 .82 .823 2.148 0 2.967a2.11 2.11 0 0 1 -2.976 0l-7.407 -7.385"/><path d="M6.66 15.66l-3.32 -3.32a1.25 1.25 0 0 1 .42 -2.044l3.24 -1.296l6 -6l3 3l-6 6l-1.296 3.24a1.25 1.25 0 0 1 -2.044 .42"/>'
    },
    alertWarning: {
      name: 'Alerta',
      fill: true,
      svg: '<path d="M12 1.67c.955 0 1.845 .467 2.39 1.247l.105 .16l8.114 13.548a2.914 2.914 0 0 1 -2.307 4.363l-.195 .008h-16.225a2.914 2.914 0 0 1 -2.582 -4.2l.099 -.185l8.11 -13.538a2.914 2.914 0 0 1 2.491 -1.403zm.01 13.33l-.127 .007a1 1 0 0 0 0 1.986l.117 .007l.127 -.007a1 1 0 0 0 0 -1.986l-.117 -.007zm-.01 -7a1 1 0 0 0 -.993 .883l-.007 .117v4l.007 .117a1 1 0 0 0 1.986 0l.007 -.117v-4l-.007 -.117a1 1 0 0 0 -.993 -.883z"/>'
    },
    blocked: {
      name: 'Bloqueado',
      svg: '<path d="M3 12a9 9 0 1 0 18 0a9 9 0 1 0 -18 0"/><path d="M5.7 5.7l12.6 12.6"/>'
    },
    calendar: {
      name: 'Calendario',
      svg: '<path d="M4 7a2 2 0 0 1 2 -2h12a2 2 0 0 1 2 2v12a2 2 0 0 1 -2 2h-12a2 2 0 0 1 -2 -2v-12"/><path d="M16 3v4"/><path d="M8 3v4"/><path d="M4 11h16"/><path d="M11 15h1"/><path d="M12 15v3"/>'
    },
    clipboard: {
      name: 'Registro',
      svg: '<path d="M9 5h-2a2 2 0 0 0 -2 2v12a2 2 0 0 0 2 2h10a2 2 0 0 0 2 -2v-12a2 2 0 0 0 -2 -2h-2"/><path d="M9 5a2 2 0 0 1 2 -2h2a2 2 0 0 1 2 2a2 2 0 0 1 -2 2h-2a2 2 0 0 1 -2 -2"/>'
    },
    employee: {
      name: 'Empleado',
      svg: '<path d="M8 7a4 4 0 1 0 8 0a4 4 0 0 0 -8 0"/><path d="M6 21v-2a4 4 0 0 1 4 -4h4a4 4 0 0 1 4 4v2"/>'
    },
    handOver: {
      name: 'Entrega',
      svg: '<path d="M3 17a2 2 0 1 0 4 0a2 2 0 1 0 -4 0"/><path d="M12 17a2 2 0 1 0 4 0a2 2 0 1 0 -4 0"/><path d="M7 17l5 0"/><path d="M3 17v-6h13v6"/><path d="M5 11v-4h4"/><path d="M9 11v-6h4l3 6"/><path d="M22 15h-3v-10"/><path d="M16 13l3 0"/>'
    },
    loanHistory: {
      name: 'Historial',
      svg: '<path d="M12 8l0 4l2 2"/><path d="M3.05 11a9 9 0 1 1 .5 4m-.5 5v-5h5"/>'
    },
    maintenancePlan: {
      name: 'Plan de Mantenimiento',
      svg: '<path d="M8 9h8"/><path d="M8 13h6"/><path d="M12.031 18.581l-4.031 2.419v-3h-2a3 3 0 0 1 -3 -3v-8a3 3 0 0 1 3 -3h12a3 3 0 0 1 3 3v5"/><path d="M17.001 19a2 2 0 1 0 4 0a2 2 0 1 0 -4 0"/><path d="M19.001 15.5v1.5"/><path d="M19.001 21v1.5"/><path d="M22.032 17.25l-1.299 .75"/><path d="M17.27 20l-1.3 .75"/><path d="M15.97 17.25l1.3 .75"/><path d="M20.733 20l1.3 .75"/>'
    },
    maintenance: {
      name: 'Mantenimiento',
      svg: '<path d="M5 20a2 2 0 1 0 4 0a2 2 0 0 0 -4 0"/><path d="M15 20a2 2 0 1 0 4 0a2 2 0 0 0 -4 0"/><path d="M5 20h-2v-6l2 -5h9l4 5h1a2 2 0 0 1 2 2v4h-2m-4 0h-6m-6 -6h15m-6 0v-5"/><path d="M3 6l9 -4l9 4"/>'
    },
    return: {
      name: 'Devolución',
      svg: '<path d="M5 17a2 2 0 1 0 4 0a2 2 0 1 0 -4 0"/><path d="M15 17a2 2 0 1 0 4 0a2 2 0 1 0 -4 0"/><path d="M5 17h-2v-11a1 1 0 0 1 1 -1h9v6h-5l2 2m0 -4l-2 2"/><path d="M9 17l6 0"/><path d="M13 6h5l3 5v6h-2"/>'
    },
    toolInventory: {
      name: 'Inventario de Herramientas',
      svg: '<path d="M3 21v-13l9 -4l9 4v13"/><path d="M13 13h4v8h-10v-6h6"/><path d="M13 21v-9a1 1 0 0 0 -1 -1h-2a1 1 0 0 0 -1 1v3"/>'
    },
    tools: {
      name: 'Herramientas',
      svg: '<path d="M7 10h3v-3l-3.5 -3.5a6 6 0 0 1 8 8l6 6a2 2 0 0 1 -3 3l-6 -6a6 6 0 0 1 -8 -8l3.5 3.5"/>'
    },

    // ── DATOS Y ANALÍTICA ────────────────────────────────────────
    activityTimeline: {
      name: 'Línea de Tiempo',
      svg: '<path d="M10 20a2 2 0 1 0 4 0a2 2 0 1 0 -4 0"/><path d="M10 20h-6"/><path d="M14 20h6"/><path d="M12 15l-2 -2h-3a1 1 0 0 1 -1 -1v-8a1 1 0 0 1 1 -1h10a1 1 0 0 1 1 1v8a1 1 0 0 1 -1 1h-3l-2 2"/><path d="M9 6h6"/><path d="M9 9h3"/>'
    },
    barChart: {
      name: 'Gráfico de Barras',
      svg: '<path d="M3 13a1 1 0 0 1 1 -1h4a1 1 0 0 1 1 1v6a1 1 0 0 1 -1 1h-4a1 1 0 0 1 -1 -1l0 -6"/><path d="M9 9a1 1 0 0 1 1 -1h4a1 1 0 0 1 1 1v10a1 1 0 0 1 -1 1h-4a1 1 0 0 1 -1 -1l0 -10"/><path d="M15 5a1 1 0 0 1 1 -1h4a1 1 0 0 1 1 1v14a1 1 0 0 1 -1 1h-4a1 1 0 0 1 -1 -1l0 -14"/><path d="M4 20h14"/>'
    },
    lineChart: {
      name: 'Gráfico de Líneas',
      svg: '<path d="M18 21v-14"/><path d="M9 15l3 -3l3 3"/><path d="M15 10l3 -3l3 3"/><path d="M3 21l18 0"/><path d="M12 21l0 -9"/><path d="M3 6l3 -3l3 3"/><path d="M6 21v-18"/>'
    },
    pieChart: {
      name: 'Gráfico Circular',
      svg: '<path d="M10 3.2a9 9 0 1 0 10.8 10.8a1 1 0 0 0 -1 -1h-3.8a4.1 4.1 0 1 1 -5 -5v-4a.9 .9 0 0 0 -1 -.8"/><path d="M15 3.5a9 9 0 0 1 5.5 5.5h-4.5a9 9 0 0 0 -1 -1v-4.5"/>'
    },
    report: {
      name: 'Reporte',
      svg: '<path d="M9 5h-2a2 2 0 0 0 -2 2v12a2 2 0 0 0 2 2h10a2 2 0 0 0 2 -2v-12a2 2 0 0 0 -2 -2h-2"/><path d="M9 5a2 2 0 0 1 2 -2h2a2 2 0 0 1 2 2a2 2 0 0 1 -2 2h-2a2 2 0 0 1 -2 -2"/><path d="M9 17v-5"/><path d="M12 17v-1"/><path d="M15 17v-3"/>'
    },
    table: {
      name: 'Tabla',
      svg: '<path d="M3 5a2 2 0 0 1 2 -2h14a2 2 0 0 1 2 2v14a2 2 0 0 1 -2 2h-14a2 2 0 0 1 -2 -2v-14"/><path d="M3 10h18"/><path d="M10 3v18"/>'
    },
    trendDown: {
      name: 'Tendencia Baja',
      svg: '<path d="M3 7l6 6l4 -4l8 8"/><path d="M21 10l0 7l-7 0"/>'
    },
    trendUp: {
      name: 'Tendencia Alta',
      svg: '<path d="M3 17l6 -6l4 4l8 -8"/><path d="M14 7l7 0l0 7"/>'
    }

  },

  /**
   * Crear elemento SVG con atributos completos
   * @param {string} iconName - Nombre del icono
   * @param {Object} options - Opciones de rendereo
   * @returns {string} HTML del icono SVG
   */
  createSvgIcon(iconName, options = {}) {
    const icon = this.icons[iconName];
    if (!icon) {
      console.warn(`Icon not found: ${iconName}`);
      return '';
    }

    const {
      size = 'md',
      color = undefined,
      className = '',
      title = icon.name,
      ariaHidden = true,
      ariaLabel = undefined
    } = options;

    const fill = icon.fill ? 'currentColor' : 'none';
    const stroke = icon.fill ? 'none' : 'currentColor';
    const viewBox = icon.viewBox || '0 0 24 24';

    const classes = [
      'icon',
      `icon-${size}`,
      icon.fill ? '' : 'icon-stroke',
      color ? `icon-${color}` : '',
      className
    ].filter(Boolean).join(' ');

    const ariaAttrs = ariaHidden 
      ? 'aria-hidden="true"'
      : `aria-label="${ariaLabel || title}"`;

    return `
<svg class="${classes}" viewBox="${viewBox}" fill="${fill}" stroke="${stroke}" 
     stroke-width="2" stroke-linecap="round" stroke-linejoin="round" ${ariaAttrs}>
  <title>${title}</title>
  ${icon.svg}
</svg>`.trim();
  },

  /**
   * Crear elemento de icono con accesibilidad
   * @param {string} iconName
   * @param {string} label - Etiqueta accesible
   * @param {Object} options
   * @returns {string} HTML
   */
  createAccessibleIcon(iconName, label, options = {}) {
    const svg = this.createSvgIcon(iconName, {
      ...options,
      ariaHidden: true
    });

    return `
<span class="icon-with-label">
  ${svg}
  <span class="sr-only">${label}</span>
</span>`.trim();
  },

  /**
   * Crear contenedor de icono de estado
   * @param {string} status - 'operativa', 'mantenimiento', 'defectuosa', 'baja'
   * @param {string} label
   * @returns {string} HTML
   */
  createStatusIcon(status, label) {
    return `<span class="icon-status ${status}" role="img" aria-label="${label}"></span>`;
  },

  /**
   * Crear caja de KPI
   * @param {string} type - 'primary', 'warning', 'danger', 'neutral'
   * @param {string} content - Contenido (unicode o número)
   * @param {string} label
   * @returns {string} HTML
   */
  createKpiBox(type = 'primary', content = '□', label = '') {
    const ariaLabel = label || `KPI ${type}`;
    return `
<div class="icon-kpi ${type}" role="img" aria-label="${ariaLabel}">
  <span class="icon-unicode">${content}</span>
</div>`.trim();
  },

  /**
   * Crear botón de acción con icono
   * @param {string} iconName
   * @param {string} text
   * @param {Object} options
   * @returns {string} HTML
   */
  createIconButton(iconName, text, options = {}) {
    const {
      className = '',
      onClick = '',
      title = '',
      disabled = false
    } = options;

    const svg = this.createSvgIcon(iconName, { size: 'sm', className: 'icon-action' });
    const disabledAttr = disabled ? 'disabled' : '';
    const onClickAttr = onClick ? `onclick="${onClick}"` : '';

    return `
<button class="btn ${className}" ${onClickAttr} ${disabledAttr} title="${title}">
  ${svg}
  <span>${text}</span>
</button>`.trim();
  },

  /**
   * Reemplazar todos los iconos SVG inline en un elemento
   * Útil para inicialización dinámica
   * @param {Element} container
   */
  renderAllIcons(container = document.body) {
    const placeholders = container.querySelectorAll('[data-icon]');
    placeholders.forEach(el => {
      const iconName = el.dataset.icon;
      const options = {
        size: el.dataset.iconSize || 'md',
        color: el.dataset.iconColor || undefined,
        className: el.className
      };
      el.innerHTML = this.createSvgIcon(iconName, options);
    });
  },

  /**
   * Obtener información de un icono
   * @param {string} iconName
   * @returns {Object|null}
   */
  getIcon(iconName) {
    return this.icons[iconName] || null;
  },

  /**
   * Listar todos los iconos disponibles
   * @returns {Array}
   */
  listAllIcons() {
    return Object.keys(this.icons).map(name => ({
      name,
      label: this.icons[name].name
    }));
  },

  /**
   * Validar si un icono existe
   * @param {string} iconName
   * @returns {boolean}
   */
  hasIcon(iconName) {
    return iconName in this.icons;
  }
};

// Log de inicialización
console.log('✓ IconUtils initialized with', Object.keys(IconUtils.icons).length, 'icons');
