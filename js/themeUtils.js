/**
 * ThemeManager Utilities - North Chrome v2
 * Gestión centralizada de temas con sincronización automática
 * 
 * Responsabilidades:
 * - Sincronizar data-theme con localStorage
 * - Manejar preferencias del sistema operativo
 * - Aplicar transiciones suaves de tema
 * - Validar integridad del tema
 */

class ThemeManager {
  constructor() {
    this.STORAGE_KEY = 'nc_settings';
    this.THEME_ATTR = 'data-theme';
    this.VALID_THEMES = ['dark', 'light', 'auto'];
    this.TRANSITION_DELAY = 150; // ms para transiciones suaves
  }

  /**
   * Inicializa el gestor de temas
   */
  init() {
    this.applyStoredTheme();
    this.observeSystemPreference();
    console.log('✓ ThemeManager initialized');
  }

  /**
   * Obtiene el tema actual desde el elemento HTML
   */
  getCurrentTheme() {
    return document.documentElement.getAttribute(this.THEME_ATTR) || 'auto';
  }

  /**
   * Obtiene la preferencia guardada en localStorage
   */
  getStoredPreference() {
    try {
      const saved = localStorage.getItem(this.STORAGE_KEY);
      if (!saved) return null;
      const settings = JSON.parse(saved);
      return settings.colorScheme || 'auto';
    } catch (e) {
      console.warn('Error reading stored theme preference:', e);
      return null;
    }
  }

  /**
   * Resuelve 'auto' a 'dark' o 'light' basado en preferencia del SO
   */
  resolveAutoTheme() {
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    return prefersDark ? 'dark' : 'light';
  }

  /**
   * Aplica el tema almacenado al cargar la página
   */
  applyStoredTheme() {
    const preference = this.getStoredPreference();
    const themeToApply = preference || 'auto';
    
    const resolvedTheme = themeToApply === 'auto' 
      ? this.resolveAutoTheme() 
      : themeToApply;
    
    // Validar tema
    if (!this.VALID_THEMES.includes(resolvedTheme)) {
      console.warn(`Invalid theme: ${resolvedTheme}, falling back to dark`);
      document.documentElement.setAttribute(this.THEME_ATTR, 'dark');
    } else {
      document.documentElement.setAttribute(this.THEME_ATTR, resolvedTheme);
    }
  }

  /**
   * Observa cambios en la preferencia del sistema
   */
  observeSystemPreference() {
    const darkModeQuery = window.matchMedia('(prefers-color-scheme: dark)');
    
    darkModeQuery.addEventListener('change', (e) => {
      const stored = this.getStoredPreference();
      
      // Solo cambiar si está en modo automático
      if (stored === 'auto' || !stored) {
        const newTheme = e.matches ? 'dark' : 'light';
        this.setTheme(newTheme, false); // No guardar en localStorage, solo aplicar
      }
    });
  }

  /**
   * Establece un tema particular (de forma segura)
   * @param {string} theme - 'dark', 'light', o 'auto'
   * @param {boolean} save - Si guardar en localStorage
   */
  setTheme(theme, save = true) {
    if (!this.VALID_THEMES.includes(theme)) {
      console.error(`Invalid theme: ${theme}. Valid themes: ${this.VALID_THEMES.join(', ')}`);
      return false;
    }

    // Resolver 'auto'
    const resolvedTheme = theme === 'auto' ? this.resolveAutoTheme() : theme;

    // Aplicar transición suave
    this.applyThemeWithTransition(resolvedTheme);

    // Guardar si es necesario
    if (save) {
      this.saveThemePreference(theme);
    }

    return true;
  }

  /**
   * Aplica tema con transición suave (sin parpadeo)
   */
  applyThemeWithTransition(resolvedTheme) {
    // Esperar a que se renderice el siguiente frame
    requestAnimationFrame(() => {
      document.documentElement.setAttribute(this.THEME_ATTR, resolvedTheme);
    });
  }

  /**
   * Guarda la preferencia en localStorage
   */
  saveThemePreference(theme) {
    try {
      const saved = localStorage.getItem(this.STORAGE_KEY);
      const settings = saved ? JSON.parse(saved) : {};
      settings.colorScheme = theme;
      localStorage.setItem(this.STORAGE_KEY, JSON.stringify(settings));
      console.log(`✓ Theme preference saved: ${theme}`);
    } catch (e) {
      console.error('Error saving theme preference:', e);
    }
  }

  /**
   * Obtiene información de contraste para debugging
   */
  getThemeInfo() {
    const current = this.getCurrentTheme();
    const stored = this.getStoredPreference();
    const resolved = this.resolveAutoTheme();
    
    return {
      current,
      stored,
      resolved,
      isAuto: stored === 'auto' || !stored,
      systemPrefersDark: resolved === 'dark'
    };
  }

  /**
   * Limpia el tema (resetea a auto)
   */
  resetTheme() {
    this.setTheme('auto', true);
  }
}

// Instancia global
const themeManager = new ThemeManager();

// Inicializar automáticamente si el DOM está listo
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => {
    themeManager.init();
  });
} else {
  themeManager.init();
}
