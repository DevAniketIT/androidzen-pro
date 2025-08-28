/**
 * Main Application Controller
 * Handles navigation, settings, global UI interactions, and coordination between modules
 */
class MainController {
    constructor() {
        this.currentSection = 'dashboard';
        this.sidebarCollapsed = false;
        this.mobileMenuOpen = false;
        this.notificationPanelOpen = false;
        
        // Initialize when DOM is ready
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => this.initialize());
        } else {
            this.initialize();
        }
    }

    /**
     * Initialize the application
     */
    initialize() {
        this.setupNavigation();
        this.setupNotifications();
        this.setupSettings();
        this.setupMobileHandling();
        this.setupKeyboardShortcuts();
        this.loadUserPreferences();
        this.requestNotificationPermission();
        
        // Apply saved theme
        if (window.Dashboard && window.Dashboard.settings) {
            window.Dashboard.applyTheme(window.Dashboard.settings.theme);
        }

        // Start demo mode for charts if enabled
        if (window.Charts && window.Dashboard?.settings?.demoMode) {
            window.Charts.startDemoMode();
        }

        console.log('AndroidZen Pro Dashboard initialized');
    }

    /**
     * Setup navigation between sections
     */
    setupNavigation() {
        // Sidebar menu items
        const menuItems = document.querySelectorAll('.menu-item a');
        menuItems.forEach(item => {
            item.addEventListener('click', (e) => {
                e.preventDefault();
                const section = item.getAttribute('data-section');
                if (section) {
                    this.navigateToSection(section);
                }
            });
        });

        // Sidebar toggle
        const sidebarToggle = document.getElementById('sidebarToggle');
        if (sidebarToggle) {
            sidebarToggle.addEventListener('click', () => this.toggleSidebar());
        }

        // Mobile menu toggle
        const mobileMenuToggle = document.getElementById('mobileMenuToggle');
        if (mobileMenuToggle) {
            mobileMenuToggle.addEventListener('click', () => this.toggleMobileMenu());
        }

        // Close mobile menu when clicking outside
        document.addEventListener('click', (e) => {
            const sidebar = document.getElementById('sidebar');
            const mobileToggle = document.getElementById('mobileMenuToggle');
            
            if (this.mobileMenuOpen && sidebar && !sidebar.contains(e.target) && 
                e.target !== mobileToggle && !mobileToggle?.contains(e.target)) {
                this.closeMobileMenu();
            }
        });
    }

    /**
     * Navigate to a specific section
     */
    navigateToSection(sectionName) {
        // Update active menu item
        document.querySelectorAll('.menu-item').forEach(item => {
            item.classList.remove('active');
        });
        
        const activeMenuItem = document.querySelector(`[data-section="${sectionName}"]`)?.parentNode;
        if (activeMenuItem) {
            activeMenuItem.classList.add('active');
        }

        // Hide all sections
        document.querySelectorAll('.content-section').forEach(section => {
            section.classList.remove('active');
        });

        // Show target section
        const targetSection = document.getElementById(sectionName);
        if (targetSection) {
            targetSection.classList.add('active');
            this.currentSection = sectionName;
            
            // Update page title
            this.updatePageTitle(sectionName);
            
            // Close mobile menu if open
            if (this.mobileMenuOpen) {
                this.closeMobileMenu();
            }
            
            // Trigger section-specific initialization
            this.onSectionChange(sectionName);
        }
    }

    /**
     * Update page title based on current section
     */
    updatePageTitle(section) {
        const titles = {
            dashboard: 'Dashboard',
            devices: 'Device Management',
            security: 'Security Center',
            performance: 'Performance Analytics',
            network: 'Network Management',
            settings: 'Settings & Configuration'
        };

        const pageTitle = document.getElementById('pageTitle');
        if (pageTitle) {
            pageTitle.textContent = titles[section] || 'AndroidZen Pro';
        }

        // Update document title
        document.title = `${titles[section] || 'AndroidZen Pro'} - AndroidZen Pro`;
    }

    /**
     * Handle section change events
     */
    onSectionChange(section) {
        switch (section) {
            case 'dashboard':
                // Refresh dashboard data
                if (window.Dashboard) {
                    window.Dashboard.updateUI();
                }
                break;
                
            case 'devices':
                // Refresh devices table
                if (window.Dashboard) {
                    window.Dashboard.populateDevicesTable();
                }
                break;
                
            case 'settings':
                // Load current settings into form
                this.loadSettingsForm();
                break;
        }
    }

    /**
     * Setup notification handling
     */
    setupNotifications() {
        // Notification button
        const notificationBtn = document.getElementById('notificationBtn');
        if (notificationBtn) {
            notificationBtn.addEventListener('click', () => this.toggleNotificationPanel());
        }

        // Close notification panel
        const closeNotifications = document.getElementById('closeNotifications');
        if (closeNotifications) {
            closeNotifications.addEventListener('click', () => this.closeNotificationPanel());
        }

        // Close notification panel when clicking outside
        document.addEventListener('click', (e) => {
            const panel = document.getElementById('notificationPanel');
            const button = document.getElementById('notificationBtn');
            
            if (this.notificationPanelOpen && panel && !panel.contains(e.target) && 
                e.target !== button && !button?.contains(e.target)) {
                this.closeNotificationPanel();
            }
        });
    }

    /**
     * Setup settings handling
     */
    setupSettings() {
        // Settings tabs
        const tabBtns = document.querySelectorAll('.tab-btn');
        tabBtns.forEach(btn => {
            btn.addEventListener('click', () => {
                const tabName = btn.getAttribute('data-tab');
                this.switchSettingsTab(tabName);
            });
        });

        // Save settings button
        const saveSettingsBtn = document.getElementById('saveSettingsBtn');
        if (saveSettingsBtn) {
            saveSettingsBtn.addEventListener('click', () => this.saveSettings());
        }

        // Reset settings button
        const resetSettingsBtn = document.getElementById('resetSettingsBtn');
        if (resetSettingsBtn) {
            resetSettingsBtn.addEventListener('click', () => this.resetSettings());
        }

        // Export data button
        const exportDataBtn = document.getElementById('exportDataBtn');
        if (exportDataBtn) {
            exportDataBtn.addEventListener('click', () => this.exportData());
        }

        // Theme change handler
        const themeSelect = document.getElementById('theme');
        if (themeSelect) {
            themeSelect.addEventListener('change', (e) => {
                if (window.Dashboard) {
                    window.Dashboard.applyTheme(e.target.value);
                }
            });
        }
    }

    /**
     * Setup mobile-specific handling
     */
    setupMobileHandling() {
        // Handle orientation changes
        window.addEventListener('orientationchange', () => {
            setTimeout(() => {
                if (window.Charts) {
                    window.Charts.resizeCharts();
                }
            }, 100);
        });

        // Handle viewport changes
        window.addEventListener('resize', () => {
            this.handleViewportChange();
        });
    }

    /**
     * Setup keyboard shortcuts
     */
    setupKeyboardShortcuts() {
        document.addEventListener('keydown', (e) => {
            // Ctrl/Cmd + K for search
            if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
                e.preventDefault();
                // TODO: Open search modal
                console.log('Search shortcut triggered');
            }

            // Escape to close panels
            if (e.key === 'Escape') {
                if (this.notificationPanelOpen) {
                    this.closeNotificationPanel();
                } else if (this.mobileMenuOpen) {
                    this.closeMobileMenu();
                }
            }

            // Navigation shortcuts (1-6)
            if (e.key >= '1' && e.key <= '6' && (e.ctrlKey || e.metaKey)) {
                e.preventDefault();
                const sections = ['dashboard', 'devices', 'security', 'performance', 'network', 'settings'];
                const sectionIndex = parseInt(e.key) - 1;
                if (sections[sectionIndex]) {
                    this.navigateToSection(sections[sectionIndex]);
                }
            }
        });
    }

    /**
     * Toggle sidebar collapse
     */
    toggleSidebar() {
        const sidebar = document.getElementById('sidebar');
        const mainContent = document.getElementById('mainContent');
        
        if (sidebar && mainContent) {
            this.sidebarCollapsed = !this.sidebarCollapsed;
            
            if (this.sidebarCollapsed) {
                sidebar.classList.add('collapsed');
                mainContent.classList.add('sidebar-collapsed');
            } else {
                sidebar.classList.remove('collapsed');
                mainContent.classList.remove('sidebar-collapsed');
            }
            
            // Save preference
            localStorage.setItem('sidebarCollapsed', this.sidebarCollapsed.toString());
            
            // Resize charts after animation
            setTimeout(() => {
                if (window.Charts) {
                    window.Charts.resizeCharts();
                }
            }, 300);
        }
    }

    /**
     * Toggle mobile menu
     */
    toggleMobileMenu() {
        if (this.mobileMenuOpen) {
            this.closeMobileMenu();
        } else {
            this.openMobileMenu();
        }
    }

    /**
     * Open mobile menu
     */
    openMobileMenu() {
        const sidebar = document.getElementById('sidebar');
        const overlay = document.getElementById('modalOverlay');
        
        if (sidebar) {
            sidebar.classList.add('mobile-open');
            this.mobileMenuOpen = true;
            
            if (overlay) {
                overlay.classList.add('active');
            }
            
            // Prevent body scrolling
            document.body.style.overflow = 'hidden';
        }
    }

    /**
     * Close mobile menu
     */
    closeMobileMenu() {
        const sidebar = document.getElementById('sidebar');
        const overlay = document.getElementById('modalOverlay');
        
        if (sidebar) {
            sidebar.classList.remove('mobile-open');
            this.mobileMenuOpen = false;
            
            if (overlay) {
                overlay.classList.remove('active');
            }
            
            // Restore body scrolling
            document.body.style.overflow = '';
        }
    }

    /**
     * Toggle notification panel
     */
    toggleNotificationPanel() {
        if (this.notificationPanelOpen) {
            this.closeNotificationPanel();
        } else {
            this.openNotificationPanel();
        }
    }

    /**
     * Open notification panel
     */
    openNotificationPanel() {
        const panel = document.getElementById('notificationPanel');
        const overlay = document.getElementById('modalOverlay');
        
        if (panel) {
            panel.classList.add('active');
            this.notificationPanelOpen = true;
            
            if (overlay) {
                overlay.classList.add('active');
            }
            
            // Update notification list
            if (window.Dashboard) {
                window.Dashboard.updateNotificationPanel();
            }
            
            // Mark notifications as read after viewing
            setTimeout(() => {
                if (window.Dashboard) {
                    window.Dashboard.notifications.forEach(n => n.read = true);
                    window.Dashboard.updateNotificationBadge();
                }
            }, 1000);
        }
    }

    /**
     * Close notification panel
     */
    closeNotificationPanel() {
        const panel = document.getElementById('notificationPanel');
        const overlay = document.getElementById('modalOverlay');
        
        if (panel) {
            panel.classList.remove('active');
            this.notificationPanelOpen = false;
            
            if (overlay && !this.mobileMenuOpen) {
                overlay.classList.remove('active');
            }
        }
    }

    /**
     * Switch settings tabs
     */
    switchSettingsTab(tabName) {
        // Update tab buttons
        document.querySelectorAll('.tab-btn').forEach(btn => {
            btn.classList.remove('active');
        });
        
        const activeTabBtn = document.querySelector(`[data-tab="${tabName}"]`);
        if (activeTabBtn) {
            activeTabBtn.classList.add('active');
        }

        // Update tab content
        document.querySelectorAll('.tab-content').forEach(content => {
            content.classList.remove('active');
        });
        
        const activeTabContent = document.getElementById(tabName);
        if (activeTabContent) {
            activeTabContent.classList.add('active');
        }
    }

    /**
     * Load current settings into form
     */
    loadSettingsForm() {
        if (!window.Dashboard?.settings) return;
        
        const settings = window.Dashboard.settings;
        
        // General settings
        const refreshInterval = document.getElementById('refreshInterval');
        if (refreshInterval) refreshInterval.value = settings.refreshInterval;
        
        const theme = document.getElementById('theme');
        if (theme) theme.value = settings.theme;
        
        const language = document.getElementById('language');
        if (language) language.value = settings.language;
        
        // Notification settings
        const enableNotifications = document.getElementById('enableNotifications');
        if (enableNotifications) enableNotifications.checked = settings.enableNotifications;
        
        const securityAlerts = document.getElementById('securityAlerts');
        if (securityAlerts) securityAlerts.checked = settings.securityAlerts;
        
        const deviceAlerts = document.getElementById('deviceAlerts');
        if (deviceAlerts) deviceAlerts.checked = settings.deviceAlerts;
        
        const performanceAlerts = document.getElementById('performanceAlerts');
        if (performanceAlerts) performanceAlerts.checked = settings.performanceAlerts;
        
        // Security settings
        const sessionTimeout = document.getElementById('sessionTimeout');
        if (sessionTimeout) sessionTimeout.value = settings.sessionTimeout || 30;
        
        const twoFactorAuth = document.getElementById('twoFactorAuth');
        if (twoFactorAuth) twoFactorAuth.checked = settings.twoFactorAuth || false;
        
        const loginNotifications = document.getElementById('loginNotifications');
        if (loginNotifications) loginNotifications.checked = settings.loginNotifications !== false;
        
        // Advanced settings
        const apiEndpoint = document.getElementById('apiEndpoint');
        if (apiEndpoint) apiEndpoint.value = settings.apiEndpoint || 'http://localhost:8000/api';
        
        const wsEndpoint = document.getElementById('wsEndpoint');
        if (wsEndpoint) wsEndpoint.value = settings.wsEndpoint || 'ws://localhost:8000/ws';
        
        const maxDevices = document.getElementById('maxDevices');
        if (maxDevices) maxDevices.value = settings.maxDevices || 10;
        
        const debugMode = document.getElementById('debugMode');
        if (debugMode) debugMode.checked = settings.debugMode || false;
    }

    /**
     * Save settings
     */
    saveSettings() {
        const newSettings = {};
        
        // General settings
        const refreshInterval = document.getElementById('refreshInterval');
        if (refreshInterval) newSettings.refreshInterval = parseInt(refreshInterval.value);
        
        const theme = document.getElementById('theme');
        if (theme) newSettings.theme = theme.value;
        
        const language = document.getElementById('language');
        if (language) newSettings.language = language.value;
        
        // Notification settings
        const enableNotifications = document.getElementById('enableNotifications');
        if (enableNotifications) newSettings.enableNotifications = enableNotifications.checked;
        
        const securityAlerts = document.getElementById('securityAlerts');
        if (securityAlerts) newSettings.securityAlerts = securityAlerts.checked;
        
        const deviceAlerts = document.getElementById('deviceAlerts');
        if (deviceAlerts) newSettings.deviceAlerts = deviceAlerts.checked;
        
        const performanceAlerts = document.getElementById('performanceAlerts');
        if (performanceAlerts) newSettings.performanceAlerts = performanceAlerts.checked;
        
        // Security settings
        const sessionTimeout = document.getElementById('sessionTimeout');
        if (sessionTimeout) newSettings.sessionTimeout = parseInt(sessionTimeout.value);
        
        const twoFactorAuth = document.getElementById('twoFactorAuth');
        if (twoFactorAuth) newSettings.twoFactorAuth = twoFactorAuth.checked;
        
        const loginNotifications = document.getElementById('loginNotifications');
        if (loginNotifications) newSettings.loginNotifications = loginNotifications.checked;
        
        // Advanced settings
        const apiEndpoint = document.getElementById('apiEndpoint');
        if (apiEndpoint) newSettings.apiEndpoint = apiEndpoint.value;
        
        const wsEndpoint = document.getElementById('wsEndpoint');
        if (wsEndpoint) newSettings.wsEndpoint = wsEndpoint.value;
        
        const maxDevices = document.getElementById('maxDevices');
        if (maxDevices) newSettings.maxDevices = parseInt(maxDevices.value);
        
        const debugMode = document.getElementById('debugMode');
        if (debugMode) newSettings.debugMode = debugMode.checked;
        
        // Save settings
        if (window.Dashboard) {
            window.Dashboard.saveSettings(newSettings);
        }
        
        // Update WebSocket connection if endpoint changed
        if (newSettings.wsEndpoint && window.wsClient) {
            window.wsClient.url = newSettings.wsEndpoint;
            // Reconnect with new URL
            window.wsClient.close();
            setTimeout(() => window.wsClient.connect(), 1000);
        }
        
        // Show success message
        if (window.Dashboard) {
            window.Dashboard.showToast('Settings saved successfully', 'success');
        }
    }

    /**
     * Reset settings to default
     */
    resetSettings() {
        if (confirm('Are you sure you want to reset all settings to default values?')) {
            localStorage.removeItem('androidzen-settings');
            location.reload(); // Reload to apply default settings
        }
    }

    /**
     * Export all data
     */
    exportData() {
        if (window.Dashboard) {
            window.Dashboard.generateReport();
        }
    }

    /**
     * Load user preferences
     */
    loadUserPreferences() {
        // Load sidebar state
        const sidebarCollapsed = localStorage.getItem('sidebarCollapsed');
        if (sidebarCollapsed === 'true') {
            this.toggleSidebar();
        }
    }

    /**
     * Request notification permission
     */
    requestNotificationPermission() {
        if ('Notification' in window && Notification.permission === 'default') {
            Notification.requestPermission().then((permission) => {
                console.log('Notification permission:', permission);
            });
        }
    }

    /**
     * Handle viewport changes
     */
    handleViewportChange() {
        const width = window.innerWidth;
        
        // Auto-close mobile menu on desktop
        if (width > 768 && this.mobileMenuOpen) {
            this.closeMobileMenu();
        }
        
        // Resize charts
        if (window.Charts) {
            setTimeout(() => {
                window.Charts.resizeCharts();
            }, 100);
        }
    }

    /**
     * Show error message
     */
    showError(message, details = '') {
        console.error(message, details);
        if (window.Dashboard) {
            window.Dashboard.showToast(message, 'danger', 5000);
        }
    }

    /**
     * Show success message
     */
    showSuccess(message) {
        console.log(message);
        if (window.Dashboard) {
            window.Dashboard.showToast(message, 'success');
        }
    }
}

// Initialize main controller
const app = new MainController();

// Export for global access
window.app = app;

// Service Worker registration for PWA support
if ('serviceWorker' in navigator) {
    window.addEventListener('load', () => {
        navigator.serviceWorker.register('/sw.js')
            .then((registration) => {
                console.log('SW registered: ', registration);
            })
            .catch((registrationError) => {
                console.log('SW registration failed: ', registrationError);
            });
    });
}

// Handle online/offline status
window.addEventListener('online', () => {
    app.showSuccess('Connection restored');
    if (window.wsClient) {
        window.wsClient.connect();
    }
});

window.addEventListener('offline', () => {
    app.showError('Connection lost');
});
