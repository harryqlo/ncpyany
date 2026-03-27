/**
 * Sistema de Configuración Avanzada - North Chrome v2
 * Gestiona todas las preferencias de UI del usuario
 * Almacenamiento: localStorage + servidor
 */

const SettingsManager = {
  // Configuración por defecto
  defaults: {
    fontSize: 'normal', // small, normal, large, xlarge
    fontFamily: 'system', // system, serif, mono
    density: 'normal', // compact, normal, spacious
    colorScheme: 'auto', // auto, dark, light
    accentColor: 'orange', // orange, blue, purple, green
    lineHeight: '1.5',
    animationsEnabled: true,
    compactMode: false,
    sidebarCollapsed: false,
    autoRefresh: true,
    autoRefreshInterval: 60000, // 60 segundos
    dateFormat: 'yyyy-mm-dd',
    numberFormat: 'es-CL',
    language: 'es',
    notifications: true,
    theme: 'professional', // professional, minimal, compact
  },

  // Mapa de escalas de fuente
  fontSizeScales: {
    small: {
      base: '12px',
      sm: '10px',
      md: '13px',
      lg: '18px',
      xl: '24px',
      title: '16px',
      label: '10px',
    },
    normal: {
      base: '14px',
      sm: '11px',
      md: '14px',
      lg: '20px',
      xl: '28px',
      title: '18px',
      label: '11px',
    },
    large: {
      base: '16px',
      sm: '12px',
      md: '16px',
      lg: '24px',
      xl: '32px',
      title: '22px',
      label: '12px',
    },
    xlarge: {
      base: '18px',
      sm: '13px',
      md: '18px',
      lg: '28px',
      xl: '36px',
      title: '26px',
      label: '13px',
    },
  },

  // Configuración guardada
  settings: {},

  /**
   * Inicializa el gestor de configuraciones
   */
  init() {
    this.loadSettings();
    this.applySavedSettings();
    this.setupEventListeners();
    console.log('✓ SettingsManager initialized', this.settings);
  },

  /**
   * Carga configuraciones de localStorage
   */
  loadSettings() {
    try {
      const saved = localStorage.getItem('nc_settings');
      this.settings = saved ? JSON.parse(saved) : {};
      // Fusionar con valores por defecto
      this.settings = { ...this.defaults, ...this.settings };
    } catch (e) {
      console.error('Error loading settings:', e);
      this.settings = { ...this.defaults };
    }
  },

  /**
   * Guarda configuraciones en localStorage
   */
  saveSettings() {
    try {
      localStorage.setItem('nc_settings', JSON.stringify(this.settings));
      this.sendToServer();
    } catch (e) {
      console.error('Error saving settings:', e);
    }
  },

  /**
   * Aplica todas las configuraciones guardadas
   */
  applySavedSettings() {
    this.applyFontSize(this.settings.fontSize);
    this.applyFontFamily(this.settings.fontFamily);
    this.applyDensity(this.settings.density);
    this.applyColorScheme(this.settings.colorScheme);
    this.applyAccentColor(this.settings.accentColor);
    this.applyTheme(this.settings.theme);
    this.applyLineHeight(this.settings.lineHeight);
    this.applyAnimationsEnabled(this.settings.animationsEnabled);
    this.applyCompactMode(this.settings.compactMode);
    if (typeof applyStoredSidebarState === 'function') {
      applyStoredSidebarState();
    }
  },

  /**
   * Aplica tamaño de fuente global
   */
  applyFontSize(size) {
    this.settings.fontSize = size;
    const scale = this.fontSizeScales[size] || this.fontSizeScales.normal;
    const css = `
      :root {
        --font-size-base: ${scale.base};
        --font-size-sm: ${scale.sm};
        --font-size-md: ${scale.md};
        --font-size-lg: ${scale.lg};
        --font-size-xl: ${scale.xl};
        --font-size-title: ${scale.title};
        --font-size-label: ${scale.label};
      }
      
      body {
        font-size: ${scale.base};
      }
      
      .topbar-t {
        font-size: var(--font-size-md) !important;
      }
      
      .s-logo {
        font-size: ${scale.md} !important;
      }
      
      .pt {
        font-size: var(--font-size-title) !important;
      }
      
      .pd {
        font-size: var(--font-size-sm) !important;
      }
      
      .btn {
        font-size: var(--font-size-sm) !important;
      }
      
      th, td {
        font-size: var(--font-size-sm) !important;
      }
      
      .ni {
        font-size: var(--font-size-sm) !important;
      }
      
      .fl {
        font-size: var(--font-size-label) !important;
      }
      
      .fi, .fs, .ft {
        font-size: var(--font-size-sm) !important;
      }
      
      input.t-search {
        font-size: var(--font-size-sm) !important;
      }
      
      .sv {
        font-size: var(--font-size-lg) !important;
      }
      
      .sl {
        font-size: var(--font-size-label) !important;
      }
      
      .badge {
        font-size: var(--font-size-label) !important;
      }
      
      .mt {
        font-size: var(--font-size-md) !important;
      }
      
      .empty-t {
        font-size: var(--font-size-md) !important;
      }
      
      .sec {
        font-size: var(--font-size-sm) !important;
      }
    `;

    this.injectCSS('nc-font-size', css);
    this.saveSettings();
  },

  /**
   * Aplica familia de fuente
   */
  applyFontFamily(family) {
    this.settings.fontFamily = family;
    const families = {
      system: "'IBM Plex Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
      serif: "'IBM Plex Serif', Georgia, serif",
      mono: "'IBM Plex Mono', 'Courier New', monospace",
    };
    const monoFamily = "'IBM Plex Mono', monospace";

    const css = `
      body, input, select, textarea, button {
        font-family: ${families[family] || families.system} !important;
      }
      
      .m {
        font-family: ${monoFamily} !important;
      }
    `;

    this.injectCSS('nc-font-family', css);
    this.saveSettings();
  },

  /**
   * Aplica densidad de contenido
   */
  applyDensity(density) {
    this.settings.density = density;
    const densities = {
      compact: {
        padding: '6px 10px',
        rowHeight: '28px',
        cardPadding: '10px',
        gap: '6px',
      },
      normal: {
        padding: '8px 12px',
        rowHeight: '36px',
        cardPadding: '16px',
        gap: '12px',
      },
      spacious: {
        padding: '12px 16px',
        rowHeight: '44px',
        cardPadding: '20px',
        gap: '16px',
      },
    };

    const d = densities[density] || densities.normal;
    const css = `
      .ni {
        padding: ${d.padding} !important;
      }
      
      td {
        padding: ${d.padding} !important;
      }
      
      th {
        padding: ${d.padding} !important;
      }
      
      .card {
        padding: ${d.cardPadding} !important;
      }
      
      .mbd {
        padding: ${d.cardPadding} !important;
      }
      
      .g4, .g2 {
        gap: ${d.gap} !important;
      }
      
      tr {
        height: ${d.rowHeight};
      }
      
      .btn {
        padding: ${d.padding} !important;
      }
    `;

    this.injectCSS('nc-density', css);
    this.saveSettings();
  },

  /**
   * Aplica esquema de color (refactorizado para usar ThemeManager)
   * Delega la lógica de tema a themeManager
   */
  applyColorScheme(scheme) {
    this.settings.colorScheme = scheme;
    
    // Validar tema
    if (!['dark', 'light', 'auto'].includes(scheme)) {
      console.error(`Invalid color scheme: ${scheme}`);
      scheme = 'auto';
      this.settings.colorScheme = scheme;
    }
    
    // Usar ThemeManager si está disponible
    if (typeof themeManager !== 'undefined') {
      themeManager.setTheme(scheme, false); // No guardar aquí, lo hace saveSettings()
    } else {
      // Fallback si themeManager no está disponible
      const resolved = scheme === 'auto' 
        ? (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light')
        : scheme;
      document.documentElement.setAttribute('data-theme', resolved);
    }
    
    // Guardar configuración
    this.saveSettings();
  },

  /**
   * Aplica color de acento
   */
  applyAccentColor(color) {
    this.settings.accentColor = color;
    const colors = {
      orange: '#f97316',
      blue: '#3b82f6',
      purple: '#a855f7',
      green: '#22c55e',
      red: '#ef4444',
      pink: '#ec4899',
    };

    const accent = colors[color] || colors.orange;
    const css = `
      :root {
        --ac: ${accent} !important;
        --acd: ${accent}1f !important;
      }
    `;

    this.injectCSS('nc-accent', css);
    this.saveSettings();
  },

  /**
   * Aplica tema profesional
   */
  applyTheme(theme) {
    this.settings.theme = theme;
    const css = theme === 'compact'
      ? `
        .topbar {
          height: 40px !important;
        }
        .ni {
          padding: 6px 8px !important;
        }
        .s-nav {
          padding: 4px 4px !important;
        }
      `
      : theme === 'minimal'
        ? `
        .sidebar {
          background: var(--bg0) !important;
        }
        .bd {
          display: none !important;
        }
      `
        : `
        /* Professional theme - default */
      `;

    this.injectCSS('nc-theme', css);
    this.saveSettings();
  },

  applyLineHeight(lineHeight) {
    const allowed = ['1.3', '1.5', '1.7'];
    const safeLineHeight = allowed.includes(String(lineHeight)) ? String(lineHeight) : '1.5';
    this.settings.lineHeight = safeLineHeight;

    const css = `
      body {
        line-height: ${safeLineHeight};
      }

      td, th, .btn, .ni, .sni, .fl, .fi, .fs, .ft, .pd, .sl {
        line-height: ${safeLineHeight};
      }
    `;

    this.injectCSS('nc-line-height', css);
    this.saveSettings();
  },

  applyAnimationsEnabled(enabled) {
    this.settings.animationsEnabled = !!enabled;

    const css = this.settings.animationsEnabled
      ? ''
      : `
        *, *::before, *::after {
          animation: none !important;
          transition: none !important;
          scroll-behavior: auto !important;
        }
      `;

    this.injectCSS('nc-animations', css);
    this.saveSettings();
  },

  applyCompactMode(enabled) {
    this.settings.compactMode = !!enabled;

    const css = this.settings.compactMode
      ? `
        .topbar { height: 44px !important; }
        .content { padding: 14px !important; }
        .th { padding: 8px 12px !important; }
        .card, .mbd { padding: 12px !important; }
        .btn { padding: 5px 9px !important; }
        td, th { padding-top: 6px !important; padding-bottom: 6px !important; }
      `
      : '';

    this.injectCSS('nc-compact-mode', css);
    this.saveSettings();
  },

  /**
   * Inyecta CSS dinámicamente
   */
  injectCSS(id, css) {
    let style = document.getElementById(id);
    if (!style) {
      style = document.createElement('style');
      style.id = id;
      document.head.appendChild(style);
    }
    style.textContent = css;
  },

  /**
   * Configura event listeners para cambios
   */
  setupEventListeners() {
    // Monitorear cambios en preferencias del sistema
    const darkModeQuery = window.matchMedia('(prefers-color-scheme: dark)');
    darkModeQuery.addEventListener('change', (e) => {
      if (this.settings.colorScheme === 'auto') {
        // Si está en modo automático, cambiar según la preferencia del SO
        const newTheme = e.matches ? 'dark' : 'light';
        document.documentElement.setAttribute('data-theme', newTheme);
      }
    });
    
    // Log para debugging
    console.log('✓ Event listeners configurados para tema:', this.settings.colorScheme);
  },

  /**
   * Sincroniza con servidor con manejo de errores mejorado
   */
  async sendToServer() {
    try {
      const response = await fetch('/api/user/settings', {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          'X-Requested-With': 'XMLHttpRequest'
        },
        body: JSON.stringify(this.settings),
      });
      
      if (!response.ok) {
        throw new Error(`Error ${response.status}: ${response.statusText}`);
      }
      
      console.log('✓ Configuraciones sincronizadas con servidor');
      return true;
    } catch (e) {
      // Sin mostrar error al usuario, solo log en consola para debugging
      console.warn('⚠ No se pudo sincronizar con servidor (offline):', e.message);
      return false;
    }
  },

  /**
   * Abre modal de configuraciones
   */
  openSettings() {
    const html = `
      <div class="settings-overlay" id="settings-overlay" onclick="if(event.target.id==='settings-overlay')SettingsManager.closeSettings()">
        <div class="settings-modal">
          <div class="settings-panel">
            <div class="settings-header">
              <h2>⚙️ Configuración Avanzada</h2>
              <button class="close-btn" onclick="SettingsManager.closeSettings()">✕</button>
            </div>
            
            <div class="settings-body">
              <!-- TAMAÑO DE FUENTE -->
              <div class="settings-group">
                <label class="settings-label">📝 Tamaño de Letra</label>
                <div class="settings-options">
                  ${this._createOption('fontSize', 'small', '↓ Pequeño', '14px')}
                  ${this._createOption('fontSize', 'normal', '→ Normal', '16px')}
                  ${this._createOption('fontSize', 'large', '↑ Grande', '18px')}
                  ${this._createOption('fontSize', 'xlarge', '⇧ Extra Grande', '20px')}
                </div>
              </div>

              <!-- TEMA -->
              <div class="settings-group">
                <label class="settings-label">🎨 Esquema de Colores</label>
                <div class="settings-options">
                  ${this._createOption('colorScheme', 'auto', '🔄 Automático', '')}
                  ${this._createOption('colorScheme', 'dark', '🌙 Oscuro', '')}
                  ${this._createOption('colorScheme', 'light', '☀️ Claro', '')}
                </div>
              </div>

              <!-- COLOR DE ACENTO -->
              <div class="settings-group">
                <label class="settings-label">✨ Color de Acento</label>
                <div class="settings-options">
                  ${this._createOption('accentColor', 'orange', '🟠 Naranja (Defecto)', '')}
                  ${this._createOption('accentColor', 'blue', '🔵 Azul', '')}
                  ${this._createOption('accentColor', 'purple', '🟣 Púrpura', '')}
                  ${this._createOption('accentColor', 'green', '🟢 Verde', '')}
                </div>
              </div>

              <!-- DENSIDAD -->
              <div class="settings-group">
                <label class="settings-label">📊 Densidad de Contenido</label>
                <div class="settings-options">
                  ${this._createOption('density', 'compact', '◾ Compacta', '')}
                  ${this._createOption('density', 'normal', '◽ Normal', '')}
                  ${this._createOption('density', 'spacious', '⬜ Espaciosa', '')}
                </div>
              </div>

              <!-- TEMA DE INTERFAZ -->
              <div class="settings-group">
                <label class="settings-label">🧩 Estilo de Interfaz</label>
                <div class="settings-options">
                  ${this._createOption('theme', 'professional', '💼 Profesional', '')}
                  ${this._createOption('theme', 'minimal', '🧼 Minimal', '')}
                  ${this._createOption('theme', 'compact', '📦 Compacto', '')}
                </div>
              </div>

              <!-- INTERLINEADO -->
              <div class="settings-group">
                <label class="settings-label">📏 Interlineado</label>
                <div class="settings-options">
                  ${this._createOption('lineHeight', '1.3', 'Bajo', '')}
                  ${this._createOption('lineHeight', '1.5', 'Normal', '')}
                  ${this._createOption('lineHeight', '1.7', 'Amplio', '')}
                </div>
              </div>

              <!-- FAMILIA DE FUENTE -->
              <div class="settings-group">
                <label class="settings-label">🔤 Familia de Fuente</label>
                <div class="settings-options">
                  ${this._createOption('fontFamily', 'system', '◀ Sistema', '')}
                  ${this._createOption('fontFamily', 'serif', '📖 Serif', '')}
                  ${this._createOption('fontFamily', 'mono', '⟡ Monoespaciada', '')}
                </div>
              </div>

              <!-- OPCIONES -->
              <div class="settings-group">
                <label class="settings-label">⚡ Opciones</label>
                <div class="settings-toggles">
                  <label class="toggle-label">
                    <input type="checkbox" id="anim-toggle" ${this.settings.animationsEnabled ? 'checked' : ''} 
                      onchange="SettingsManager.setSetting('animationsEnabled', this.checked)">
                    <span>Animaciones</span>
                  </label>
                  <label class="toggle-label">
                    <input type="checkbox" id="notif-toggle" ${this.settings.notifications ? 'checked' : ''} 
                      onchange="SettingsManager.setSetting('notifications', this.checked)">
                    <span>Notificaciones</span>
                  </label>
                  <label class="toggle-label">
                    <input type="checkbox" id="refresh-toggle" ${this.settings.autoRefresh ? 'checked' : ''} 
                      onchange="SettingsManager.setSetting('autoRefresh', this.checked)">
                    <span>Auto-actualizar</span>
                  </label>
                  <label class="toggle-label">
                    <input type="checkbox" id="compact-toggle" ${this.settings.compactMode ? 'checked' : ''} 
                      onchange="SettingsManager.setSetting('compactMode', this.checked)">
                    <span>Modo compacto global</span>
                  </label>
                </div>
              </div>

              <!-- INFORMACIÓN -->
              <div class="settings-info">
                <small>💾 Los cambios se guardan automáticamente</small>
              </div>
            </div>

            <div class="settings-footer">
              <button class="btn bs" onclick="SettingsManager.resetSettings()">↻ Restablecer Predeterminados</button>
              <button class="btn bp" onclick="SettingsManager.closeSettings()">✓ Listo</button>
            </div>
          </div>
        </div>
      </div>
    `;

    const container = document.createElement('div');
    container.id = 'settings-container';
    container.innerHTML = html;
    document.body.appendChild(container);
  },

  /**
   * Crea opción de botón
   */
  _createOption(setting, value, label, detail) {
    const isActive = this.settings[setting] === value;
    return `
      <button class="settings-option ${isActive ? 'active' : ''}" 
        data-setting="${setting}" 
        data-value="${value}"
        onclick="SettingsManager.setSetting('${setting}', '${value}')">
        <div class="option-label">${label}</div>
        ${detail ? `<div class="option-detail">${detail}</div>` : ''}
      </button>
    `;
  },

  /**
   * Establece una configuración
   */
  setSetting(key, value) {
    this.settings[key] = value;

    // Aplicar según el tipo
    if (key === 'fontSize') this.applyFontSize(value);
    else if (key === 'fontFamily') this.applyFontFamily(value);
    else if (key === 'density') this.applyDensity(value);
    else if (key === 'colorScheme') this.applyColorScheme(value);
    else if (key === 'accentColor') this.applyAccentColor(value);
    else if (key === 'theme') this.applyTheme(value);
    else if (key === 'lineHeight') this.applyLineHeight(value);
    else if (key === 'animationsEnabled') this.applyAnimationsEnabled(value);
    else if (key === 'compactMode') this.applyCompactMode(value);
    else this.saveSettings();

    // Actualizar UI - buscar SOLO botones del mismo setting
    document.querySelectorAll(`.settings-option[data-setting="${key}"]`).forEach((btn) => {
      btn.classList.remove('active');
    });
    document.querySelector(`.settings-option[data-setting="${key}"][data-value="${value}"]`)?.classList.add('active');
  },

  /**
   * Cierra el modal de configuraciones
   */
  closeSettings() {
    const container = document.getElementById('settings-container');
    if (container) container.remove();
  },

  /**
   * Reinicia a valores por defecto
   */
  resetSettings() {
    if (!confirm('¿Restaurar todos los ajustes a valores predeterminados?')) return;
    this.settings = { ...this.defaults };
    this.applySavedSettings();
    this.closeSettings();
  },
};

// Inicializar cuando el DOM está listo
document.addEventListener('DOMContentLoaded', () => {
  SettingsManager.init();
});
