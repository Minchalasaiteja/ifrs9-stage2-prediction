/**
 * SICRSense Theme Manager
 * Manages dark/light theme switching with localStorage persistence
 * Can be used across all pages to ensure consistent theming
 */

class ThemeManager {
    constructor(options = {}) {
        this.storageKey = options.storageKey || 'sicrsense-theme';
        this.toggleSelector = options.toggleSelector || '#themeToggle';
        this.iconSelector = options.iconSelector || '#themeIcon';
        this.isDark = true;
        this.initialized = false;
        
        // Initialize on DOM ready
        this.init();
    }

    /**
     * Initialize theme manager
     */
    init() {
        if (this.initialized) return;
        
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => this._setupTheme());
        } else {
            this._setupTheme();
        }
        
        this.initialized = true;
    }

    /**
     * Internal setup function
     */
    _setupTheme() {
        // Load saved theme preference
        this.loadThemePreference();
        
        // Setup toggle button if it exists
        const toggleBtn = document.querySelector(this.toggleSelector);
        if (toggleBtn) {
            toggleBtn.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                this.toggle();
            });
        }
    }

    /**
     * Load theme preference from localStorage
     */
    loadThemePreference() {
        try {
            // Prefer the configured storage key, but fall back to legacy 'theme'
            const saved = localStorage.getItem(this.storageKey) || localStorage.getItem('theme');
            if (saved === 'light') {
                this.setTheme(false);
            } else if (saved === 'dark') {
                this.setTheme(true);
            } else {
                // Default to dark if not set
                this.setTheme(true);
            }
        } catch (e) {
            console.warn('Failed to load theme preference:', e);
            this.setTheme(true);
        }
    }

    /**
     * Set theme
     * @param {boolean} dark - True for dark mode, false for light mode
     */
    setTheme(dark) {
        if (dark) {
            document.body.classList.remove('light');
            this._updateIcon('moon');
        } else {
            document.body.classList.add('light');
            this._updateIcon('sun');
        }
        
        // Save preference
        try {
            localStorage.setItem(this.storageKey, dark ? 'dark' : 'light');
        } catch (e) {
            console.warn('Failed to save theme preference:', e);
        }
        
        this.isDark = dark;
        
        // Dispatch custom event
        window.dispatchEvent(new CustomEvent('themechange', {
            detail: { isDark: dark, theme: dark ? 'dark' : 'light' }
        }));
    }

    /**
     * Toggle theme
     */
    toggle() {
        this.setTheme(!this.isDark);
    }

    /**
     * Update theme icon
     * @param {string} iconName - 'moon' or 'sun'
     */
    _updateIcon(iconName) {
        const iconEl = document.querySelector(this.iconSelector);
        if (iconEl) {
            iconEl.className = `fas fa-${iconName}`;
        }
    }

    /**
     * Get current theme
     * @returns {string} 'dark' or 'light'
     */
    getTheme() {
        return this.isDark ? 'dark' : 'light';
    }

    /**
     * Check if dark mode is active
     * @returns {boolean}
     */
    isDarkMode() {
        return this.isDark;
    }
}

// Auto-initialize if script is loaded in a page
// This will automatically setup theme management on any page that includes this script
document.addEventListener('DOMContentLoaded', () => {
    // Only auto-initialize if there's a theme toggle button on the page
    if (document.querySelector('#themeToggle') && !window.themeManager) {
        window.themeManager = new ThemeManager();
    }
});

// Also support manual initialization for pages that need custom options
window.initializeTheme = (options) => {
    window.themeManager = new ThemeManager(options);
    return window.themeManager;
};
