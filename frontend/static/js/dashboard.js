/**
 * Dashboard Management Module
 * Handles dashboard widgets, data updates, and user interactions
 */
class DashboardManager {
    constructor() {
        this.devices = new Map();
        this.notifications = [];
        this.securityAlerts = [];
        this.networkStatus = {
            wifi: { status: 'connected', details: 'Signal: Strong' },
            ethernet: { status: 'disconnected', details: 'Cable unplugged' },
            server: { status: 'connected', details: 'Latency: 25ms' }
        };
        this.settings = this.loadSettings();
        this.refreshInterval = null;

        // Initialize when DOM is ready
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => this.initialize());
        } else {
            this.initialize();
        }
    }

    /**
     * Initialize dashboard
     */
    initialize() {
        this.initializePagination();
        this.setupEventListeners();
        this.setupRefreshInterval();
        this.setupWebSocketSubscriptions();
        this.loadInitialData();
        this.updateUI();
        
        // Start demo mode if enabled
        if (this.settings.demoMode) {
            this.startDemoMode();
        }
    }

    /**
     * Setup event listeners
     */
    setupEventListeners() {
        // Quick action buttons
        const scanBtn = document.getElementById('scanDevicesBtn');
        const refreshBtn = document.getElementById('refreshDataBtn');
        const securityBtn = document.getElementById('securityScanBtn');
        const reportBtn = document.getElementById('generateReportBtn');

        if (scanBtn) scanBtn.addEventListener('click', () => this.scanDevices());
        if (refreshBtn) refreshBtn.addEventListener('click', () => this.refreshData());
        if (securityBtn) securityBtn.addEventListener('click', () => this.performSecurityScan());
        if (reportBtn) reportBtn.addEventListener('click', () => this.generateReport());

        // Performance controls
        const metricSelect = document.getElementById('performanceMetric');
        const timeframeSelect = document.getElementById('performanceTimeframe');

        if (metricSelect) {
            metricSelect.addEventListener('change', (e) => {
                if (window.Charts) {
                    window.Charts.changePerformanceMetric(e.target.value);
                }
            });
        }

        if (timeframeSelect) {
            timeframeSelect.addEventListener('change', (e) => {
                if (window.Charts) {
                    window.Charts.changePerformanceTimeframe(e.target.value);
                }
            });
        }

        // Device management buttons
        const addDeviceBtn = document.getElementById('addDeviceBtn');
        const refreshDevicesBtn = document.getElementById('refreshDevicesBtn');
        if (addDeviceBtn) addDeviceBtn.addEventListener('click', () => this.showAddDeviceModal());
        if (refreshDevicesBtn) refreshDevicesBtn.addEventListener('click', () => this.refreshDevices());
        
        // Device search and filter
        const deviceSearch = document.getElementById('deviceSearch');
        const deviceFilter = document.getElementById('deviceFilter');
        if (deviceSearch) deviceSearch.addEventListener('input', (e) => this.filterDevices(e.target.value, deviceFilter?.value));
        if (deviceFilter) deviceFilter.addEventListener('change', (e) => this.filterDevices(deviceSearch?.value, e.target.value));
        
        // Bulk actions
        const selectAllDevices = document.getElementById('selectAllDevices');
        if (selectAllDevices) selectAllDevices.addEventListener('change', (e) => this.toggleSelectAllDevices(e.target.checked));
        
        const bulkConnectBtn = document.getElementById('bulkConnectBtn');
        const bulkDisconnectBtn = document.getElementById('bulkDisconnectBtn');
        const bulkRemoveBtn = document.getElementById('bulkRemoveBtn');
        if (bulkConnectBtn) bulkConnectBtn.addEventListener('click', () => this.bulkConnectDevices());
        if (bulkDisconnectBtn) bulkDisconnectBtn.addEventListener('click', () => this.bulkDisconnectDevices());
        if (bulkRemoveBtn) bulkRemoveBtn.addEventListener('click', () => this.bulkRemoveDevices());
        
        // Pagination
        const prevPageBtn = document.getElementById('prevPageBtn');
        const nextPageBtn = document.getElementById('nextPageBtn');
        if (prevPageBtn) prevPageBtn.addEventListener('click', () => this.prevPage());
        if (nextPageBtn) nextPageBtn.addEventListener('click', () => this.nextPage());
        
        // Modal event listeners
        this.setupModalEventListeners();
    }

    /**
     * Setup auto-refresh interval
     */
    setupRefreshInterval() {
        const interval = this.settings.refreshInterval * 1000;
        
        if (this.refreshInterval) {
            clearInterval(this.refreshInterval);
        }
        
        this.refreshInterval = setInterval(() => {
            this.refreshData();
        }, interval);
    }

    /**
     * Setup WebSocket subscriptions
     */
    setupWebSocketSubscriptions() {
        // Wait for WebSocket client to be available
        const setupSubscriptions = () => {
            if (window.wsClient && window.wsClient.isConnected) {
                // Subscribe to relevant topics
                window.wsClient.subscribe('device_status');
                window.wsClient.subscribe('notifications');
                window.wsClient.subscribe('security');
                window.wsClient.subscribe('performance');
                
                // Register additional handlers
                window.wsClient.on('live_metrics', this.handleLiveMetrics.bind(this));
                window.wsClient.on('device_action', this.updateDeviceAction.bind(this));
                window.wsClient.on('system_message', this.addSystemMessage.bind(this));
                
                console.log('Dashboard WebSocket subscriptions initialized');
            } else {
                // Retry after a short delay
                setTimeout(setupSubscriptions, 1000);
            }
        };
        
        setupSubscriptions();
    }

    /**
     * Load initial demo data
     */
    loadInitialData() {
        // Only load sample devices if in demo mode
        if (this.settings.demoMode) {
            // Add sample devices
            this.devices.set('device1', {
                id: 'device1',
                name: 'Samsung Galaxy S21',
                model: 'SM-G991B',
                status: 'online',
                lastSeen: new Date(),
                osVersion: 'Android 13',
                batteryLevel: 85,
                storageUsed: 45
            });
    
            this.devices.set('device2', {
                id: 'device2',
                name: 'Google Pixel 6',
                model: 'GP6',
                status: 'offline',
                lastSeen: new Date(Date.now() - 300000), // 5 minutes ago
                osVersion: 'Android 13',
                batteryLevel: 92,
                storageUsed: 32
            });
    
            this.devices.set('device3', {
                id: 'device3',
                name: 'OnePlus 9 Pro',
                model: 'LE2123',
                status: 'online',
                lastSeen: new Date(),
                osVersion: 'Android 12',
                batteryLevel: 67,
                storageUsed: 78
            });
        }

        // Add sample security alerts
        this.securityAlerts = [
            {
                id: 'alert1',
                type: 'warning',
                title: 'Suspicious App Detected',
                message: 'Unknown app requesting sensitive permissions on Galaxy S21',
                timestamp: new Date(Date.now() - 600000),
                device: 'device1'
            },
            {
                id: 'alert2',
                type: 'info',
                title: 'Security Scan Complete',
                message: 'No threats found on Pixel 6',
                timestamp: new Date(Date.now() - 1800000),
                device: 'device2'
            }
        ];

        // Add sample notifications
        this.notifications = [
            {
                id: 'notif1',
                type: 'success',
                title: 'Device Connected',
                message: 'OnePlus 9 Pro is now connected',
                timestamp: new Date(Date.now() - 120000),
                read: false
            },
            {
                id: 'notif2',
                type: 'warning',
                title: 'Low Battery',
                message: 'Galaxy S21 battery is below 20%',
                timestamp: new Date(Date.now() - 900000),
                read: true
            }
        ];
    }

    /**
     * Update UI with current data
     */
    updateUI() {
        this.updateDeviceStats();
        this.updateDeviceList();
        this.updateSecurityAlerts();
        this.updateNetworkStatus();
        this.updateNotificationBadge();
        this.populateDevicesTable();
    }

    /**
     * Update device statistics
     */
    updateDeviceStats() {
        const totalDevices = this.devices.size;
        const connectedDevices = Array.from(this.devices.values())
            .filter(device => device.status === 'online').length;
        const offlineDevices = totalDevices - connectedDevices;

        const totalEl = document.getElementById('totalDevices');
        const connectedEl = document.getElementById('connectedDevices');
        const offlineEl = document.getElementById('offlineDevices');

        if (totalEl) totalEl.textContent = totalDevices;
        if (connectedEl) connectedEl.textContent = connectedDevices;
        if (offlineEl) offlineEl.textContent = offlineDevices;
    }

    /**
     * Update device list in the widget
     */
    updateDeviceList() {
        const container = document.getElementById('deviceList');
        if (!container) return;

        const devices = Array.from(this.devices.values()).slice(0, 4); // Show first 4
        
        container.innerHTML = devices.map(device => `
            <div class="device-item">
                <div class="device-info">
                    <div class="device-icon">
                        <i class="fas fa-mobile-alt"></i>
                    </div>
                    <div>
                        <div class="device-name">${device.name}</div>
                        <div class="device-model">${device.model}</div>
                    </div>
                </div>
                <div class="device-status ${device.status}">${device.status}</div>
            </div>
        `).join('');
    }

    /**
     * Update security alerts display
     */
    updateSecurityAlerts() {
        const criticalCount = this.securityAlerts.filter(alert => alert.type === 'critical').length;
        const warningCount = this.securityAlerts.filter(alert => alert.type === 'warning').length;
        const infoCount = this.securityAlerts.filter(alert => alert.type === 'info').length;

        const criticalEl = document.getElementById('criticalAlerts');
        const warningEl = document.getElementById('warningAlerts');
        const infoEl = document.getElementById('infoAlerts');

        if (criticalEl) {
            criticalEl.textContent = criticalCount;
            criticalEl.setAttribute('data-label', 'Critical');
        }
        if (warningEl) {
            warningEl.textContent = warningCount;
            warningEl.setAttribute('data-label', 'Warning');
        }
        if (infoEl) {
            infoEl.textContent = infoCount;
            infoEl.setAttribute('data-label', 'Info');
        }

        // Update alert list
        const alertList = document.getElementById('alertList');
        if (alertList) {
            const recentAlerts = this.securityAlerts.slice(0, 3);
            alertList.innerHTML = recentAlerts.map(alert => `
                <div class="alert-item">
                    <div class="alert-icon ${alert.type}">
                        <i class="fas ${this.getAlertIcon(alert.type)}"></i>
                    </div>
                    <div class="alert-content">
                        <div class="alert-title">${alert.title}</div>
                        <div class="alert-message">${alert.message}</div>
                        <div class="alert-time">${this.formatTimeAgo(alert.timestamp)}</div>
                    </div>
                </div>
            `).join('');
        }
    }

    /**
     * Update network status indicators
     */
    updateNetworkStatus() {
        Object.keys(this.networkStatus).forEach(type => {
            const statusEl = document.getElementById(`${type}Status`);
            const detailsEl = document.getElementById(`${type}Details`);
            const status = this.networkStatus[type];

            if (statusEl) {
                statusEl.textContent = this.capitalizeFirst(status.status);
                statusEl.className = `network-status ${status.status}`;
            }
            if (detailsEl) {
                detailsEl.textContent = status.details;
            }
        });
    }

    /**
     * Update notification badge
     */
    updateNotificationBadge() {
        const badge = document.getElementById('notificationBadge');
        if (!badge) return;

        const unreadCount = this.notifications.filter(n => !n.read).length;
        badge.textContent = unreadCount;
        badge.style.display = unreadCount > 0 ? 'block' : 'none';
    }

    /**
     * Populate devices table
     */
    populateDevicesTable() {
        const devices = Array.from(this.devices.values());
        this.renderDevicesTable(devices);
        this.updateDeviceCounts(devices);
    }

    /**
     * Handle device updates from WebSocket
     */
    updateDeviceStatus(deviceData) {
        if (this.devices.has(deviceData.id)) {
            this.devices.set(deviceData.id, { ...this.devices.get(deviceData.id), ...deviceData });
        } else {
            this.devices.set(deviceData.id, deviceData);
        }
        
        this.updateUI();
    }

    /**
     * Add security alert
     */
    addSecurityAlert(alertData) {
        this.securityAlerts.unshift(alertData);
        
        // Keep only last 50 alerts
        if (this.securityAlerts.length > 50) {
            this.securityAlerts = this.securityAlerts.slice(0, 50);
        }
        
        this.updateSecurityAlerts();
        
        // Add as notification too
        this.addNotification({
            id: 'notif_' + alertData.id,
            type: alertData.type,
            title: alertData.title,
            message: alertData.message,
            timestamp: new Date(),
            read: false
        });
    }

    /**
     * Add notification
     */
    addNotification(notification) {
        this.notifications.unshift(notification);
        
        // Keep only last 50 notifications
        if (this.notifications.length > 50) {
            this.notifications = this.notifications.slice(0, 50);
        }
        
        this.updateNotificationBadge();
        
        // Update notification panel if open
        this.updateNotificationPanel();
    }

    /**
     * Update network status
     */
    updateNetworkStatus(statusData) {
        this.networkStatus = { ...this.networkStatus, ...statusData };
        this.updateNetworkStatus();
    }

    /**
     * Quick action methods
     */
    scanDevices() {
        console.log('Scanning for devices...');
        this.showLoading('scanDevicesBtn');
        
        if (window.wsClient) {
            window.wsClient.scanDevices();
        }
        
        // Simulate scan completion
        setTimeout(() => {
            this.hideLoading('scanDevicesBtn');
            this.showToast('Device scan initiated', 'success');
        }, 2000);
    }

    refreshData() {
        console.log('Refreshing data...');
        this.showLoading('refreshDataBtn');
        
        if (window.wsClient) {
            window.wsClient.refreshData();
        }
        
        // Simulate refresh
        setTimeout(() => {
            this.hideLoading('refreshDataBtn');
            this.updateUI();
            this.showToast('Data refreshed successfully', 'success');
        }, 1000);
    }

    performSecurityScan() {
        console.log('Performing security scan...');
        this.showLoading('securityScanBtn');
        
        if (window.wsClient) {
            window.wsClient.performSecurityScan();
        }
        
        // Simulate scan
        setTimeout(() => {
            this.hideLoading('securityScanBtn');
            this.showToast('Security scan completed', 'success');
        }, 3000);
    }

    generateReport() {
        console.log('Generating report...');
        this.showLoading('generateReportBtn');
        
        // Simulate report generation
        setTimeout(() => {
            this.hideLoading('generateReportBtn');
            this.downloadReport();
            this.showToast('Report generated successfully', 'success');
        }, 2000);
    }

    /**
     * Device management methods
     */
    viewDevice(deviceId) {
        const device = this.devices.get(deviceId);
        if (device) {
            console.log('Viewing device:', device);
            this.showDeviceDetails(device);
        }
    }

    editDevice(deviceId) {
        const device = this.devices.get(deviceId);
        if (device) {
            console.log('Editing device:', device);
            this.showEditDeviceModal(device);
        }
    }

    /**
     * Show device details modal
     */
    showDeviceDetails(device) {
        const modal = document.getElementById('deviceDetailsModal');
        if (!modal) return;

        // Populate device details
        const detailsContainer = modal.querySelector('.device-details-content');
        if (detailsContainer) {
            detailsContainer.innerHTML = `
                <div class="device-header">
                    <h3><i class="fas fa-mobile-alt"></i> ${device.name}</h3>
                    <span class="device-status ${device.status}">${device.status}</span>
                </div>
                <div class="device-info-grid">
                    <div class="info-item">
                        <label>Device ID:</label>
                        <span>${device.id}</span>
                    </div>
                    <div class="info-item">
                        <label>Model:</label>
                        <span>${device.model}</span>
                    </div>
                    <div class="info-item">
                        <label>OS Version:</label>
                        <span>${device.osVersion}</span>
                    </div>
                    <div class="info-item">
                        <label>IP Address:</label>
                        <span>${device.ipAddress || 'N/A'}</span>
                    </div>
                    <div class="info-item">
                        <label>Battery Level:</label>
                        <div class="battery-indicator">
                            <div class="battery-bar">
                                <div class="battery-fill" style="width: ${device.battery}%"></div>
                            </div>
                            <span>${device.battery}%</span>
                        </div>
                    </div>
                    <div class="info-item">
                        <label>Storage Used:</label>
                        <div class="storage-indicator">
                            <div class="storage-bar">
                                <div class="storage-fill" style="width: ${device.storage}%"></div>
                            </div>
                            <span>${device.storage}% used</span>
                        </div>
                    </div>
                    <div class="info-item">
                        <label>Last Seen:</label>
                        <span>${this.formatTimeAgo(device.lastSeen)}</span>
                    </div>
                    <div class="info-item">
                        <label>Connection Type:</label>
                        <span>${device.connectionType || 'ADB'}</span>
                    </div>
                </div>
                <div class="device-actions">
                    <button class="btn btn-primary" onclick="Dashboard.toggleDeviceConnection('${device.id}')">
                        <i class="fas ${device.status === 'online' ? 'fa-plug' : 'fa-play'}"></i>
                        ${device.status === 'online' ? 'Disconnect' : 'Connect'}
                    </button>
                    <button class="btn btn-secondary" onclick="Dashboard.editDevice('${device.id}')">
                        <i class="fas fa-edit"></i> Edit
                    </button>
                </div>
            `;
        }

        this.showModal('deviceDetailsModal');
    }

    /**
     * Show edit device modal
     */
    showEditDeviceModal(device) {
        const modal = document.getElementById('editDeviceModal');
        if (!modal) {
            // Create edit device modal if it doesn't exist
            this.createEditDeviceModal();
        }

        // Populate form with device data
        const form = document.getElementById('editDeviceForm');
        if (form) {
            form.elements.deviceName.value = device.name;
            form.elements.deviceModel.value = device.model;
            form.elements.ipAddress.value = device.ipAddress || '';
            form.elements.connectionType.value = device.connectionType || 'adb';
            form.dataset.deviceId = device.id;
        }

        this.showModal('editDeviceModal');
    }

    /**
     * Create edit device modal dynamically
     */
    createEditDeviceModal() {
        const modalHTML = `
            <div id="editDeviceModal" class="modal">
                <div class="modal-content">
                    <div class="modal-header">
                        <h3>Edit Device</h3>
                        <button class="modal-close" id="closeEditDeviceModal">
                            <i class="fas fa-times"></i>
                        </button>
                    </div>
                    <form id="editDeviceForm">
                        <div class="form-group">
                            <label for="deviceName">Device Name</label>
                            <input type="text" id="deviceName" name="deviceName" required>
                        </div>
                        <div class="form-group">
                            <label for="deviceModel">Model</label>
                            <input type="text" id="deviceModel" name="deviceModel">
                        </div>
                        <div class="form-group">
                            <label for="ipAddress">IP Address</label>
                            <input type="text" id="ipAddress" name="ipAddress" pattern="^(?:[0-9]{1,3}\.){3}[0-9]{1,3}$">
                        </div>
                        <div class="form-group">
                            <label for="connectionType">Connection Type</label>
                            <select id="connectionType" name="connectionType">
                                <option value="adb">ADB</option>
                                <option value="wifi">WiFi</option>
                                <option value="usb">USB</option>
                                <option value="emulator">Emulator</option>
                            </select>
                        </div>
                        <div class="form-actions">
                            <button type="button" class="btn btn-secondary" id="cancelEditDevice">Cancel</button>
                            <button type="submit" class="btn btn-primary">Update Device</button>
                        </div>
                    </form>
                </div>
            </div>
        `;
        
        document.body.insertAdjacentHTML('beforeend', modalHTML);
        
        // Setup event listeners
        const closeBtn = document.getElementById('closeEditDeviceModal');
        const cancelBtn = document.getElementById('cancelEditDevice');
        const form = document.getElementById('editDeviceForm');
        
        if (closeBtn) closeBtn.addEventListener('click', () => this.hideModal('editDeviceModal'));
        if (cancelBtn) cancelBtn.addEventListener('click', () => this.hideModal('editDeviceModal'));
        if (form) form.addEventListener('submit', (e) => this.handleEditDevice(e));
    }

    /**
     * Handle edit device form submission
     */
    handleEditDevice(e) {
        e.preventDefault();
        
        const form = e.target;
        const deviceId = form.dataset.deviceId;
        const device = this.devices.get(deviceId);
        
        if (!device) {
            this.showToast('Device not found', 'error');
            return;
        }

        // Update device with form data
        const formData = new FormData(form);
        device.name = formData.get('deviceName');
        device.model = formData.get('deviceModel');
        device.ipAddress = formData.get('ipAddress');
        device.connectionType = formData.get('connectionType');

        // In production mode, make API call
        if (!this.settings.demoMode) {
            this.updateDeviceViaAPI(deviceId, {
                name: device.name,
                model: device.model,
                ipAddress: device.ipAddress,
                connectionType: device.connectionType
            });
        }

        this.updateUI();
        this.hideModal('editDeviceModal');
        this.showToast('Device updated successfully', 'success');
    }

    removeDevice(deviceId) {
        if (confirm('Are you sure you want to remove this device?')) {
            this.devices.delete(deviceId);
            this.updateUI();
            this.showToast('Device removed successfully', 'success');
        }
    }

    /**
     * Setup modal event listeners
     */
    setupModalEventListeners() {
        // Add device modal
        const addDeviceModal = document.getElementById('addDeviceModal');
        const closeAddDeviceModal = document.getElementById('closeAddDeviceModal');
        const cancelAddDevice = document.getElementById('cancelAddDevice');
        const addDeviceForm = document.getElementById('addDeviceForm');
        
        if (closeAddDeviceModal) closeAddDeviceModal.addEventListener('click', () => this.hideModal('addDeviceModal'));
        if (cancelAddDevice) cancelAddDevice.addEventListener('click', () => this.hideModal('addDeviceModal'));
        if (addDeviceForm) addDeviceForm.addEventListener('submit', (e) => this.handleAddDevice(e));
        
        // Device details modal
        const closeDeviceDetailsModal = document.getElementById('closeDeviceDetailsModal');
        if (closeDeviceDetailsModal) closeDeviceDetailsModal.addEventListener('click', () => this.hideModal('deviceDetailsModal'));
        
        // Security modal
        const closeSecurityModal = document.getElementById('closeSecurityModal');
        if (closeSecurityModal) closeSecurityModal.addEventListener('click', () => this.hideModal('securityModal'));
        
        // Confirmation modal
        const confirmationCancel = document.getElementById('confirmationCancel');
        const confirmationConfirm = document.getElementById('confirmationConfirm');
        if (confirmationCancel) confirmationCancel.addEventListener('click', () => this.hideModal('confirmationModal'));
        if (confirmationConfirm) confirmationConfirm.addEventListener('click', () => this.handleConfirmation());
        
        // Modal overlay click to close
        const modalOverlay = document.getElementById('modalOverlay');
        if (modalOverlay) modalOverlay.addEventListener('click', () => this.closeAllModals());
    }
    
    /**
     * Device management modal functions
     */
    showAddDeviceModal() {
        this.showModal('addDeviceModal');
        document.getElementById('addDeviceForm').reset();
    }
    
    showModal(modalId) {
        const modal = document.getElementById(modalId);
        const overlay = document.getElementById('modalOverlay');
        
        if (modal && overlay) {
            overlay.style.display = 'block';
            modal.style.display = 'block';
            modal.classList.add('active');
            
            // Add animation
            setTimeout(() => {
                modal.style.opacity = '1';
                modal.style.transform = 'translateY(0)';
            }, 10);
        }
    }
    
    hideModal(modalId) {
        const modal = document.getElementById(modalId);
        const overlay = document.getElementById('modalOverlay');
        
        if (modal) {
            modal.style.opacity = '0';
            modal.style.transform = 'translateY(-20px)';
            
            setTimeout(() => {
                modal.style.display = 'none';
                modal.classList.remove('active');
                if (overlay) overlay.style.display = 'none';
            }, 300);
        }
    }
    
    closeAllModals() {
        const modals = document.querySelectorAll('.modal');
        const overlay = document.getElementById('modalOverlay');
        
        modals.forEach(modal => {
            if (modal.classList.contains('active')) {
                this.hideModal(modal.id);
            }
        });
        
        if (overlay) overlay.style.display = 'none';
    }
    
    /**
     * Handle add device form submission
     */
    async handleAddDevice(event) {
        event.preventDefault();
        
        const formData = new FormData(event.target);
        const deviceData = {
            device_id: formData.get('deviceId'),
            device_name: formData.get('deviceName'),
            model: formData.get('deviceModel'),
            manufacturer: formData.get('deviceManufacturer'),
            android_version: formData.get('androidVersion'),
            connection_type: formData.get('connectionType'),
            ip_address: formData.get('ipAddress'),
            port: formData.get('port') ? parseInt(formData.get('port')) : null
        };
        
        try {
            if (this.settings.demoMode) {
                // Add device to demo data
                const newDevice = {
                    id: deviceData.device_id,
                    name: deviceData.device_name,
                    model: deviceData.model || 'Unknown',
                    manufacturer: deviceData.manufacturer || 'Unknown',
                    status: 'online',
                    lastSeen: new Date(),
                    osVersion: deviceData.android_version || 'Android 13',
                    batteryLevel: Math.floor(Math.random() * 100),
                    storageUsed: Math.floor(Math.random() * 100)
                };
                
                this.devices.set(deviceData.device_id, newDevice);
                this.updateUI();
                this.hideModal('addDeviceModal');
                this.showToast('Device added successfully (demo)', 'success');
                
            } else {
                // Make API call to backend
                const response = await fetch(`${this.settings.apiEndpoint}/devices`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(deviceData)
                });
                
                if (response.ok) {
                    const result = await response.json();
                    this.devices.set(result.device_id, result);
                    this.updateUI();
                    this.hideModal('addDeviceModal');
                    this.showToast('Device added successfully', 'success');
                } else {
                    const error = await response.json();
                    this.showToast(`Error adding device: ${error.detail}`, 'error');
                }
            }
            
        } catch (error) {
            console.error('Error adding device:', error);
            this.showToast('Failed to add device. Please try again.', 'error');
        }
    }
    
    /**
     * Enhanced device management methods
     */
    async refreshDevices() {
        this.showLoading('refreshDevicesBtn');
        
        try {
            if (this.settings.demoMode) {
                // Simulate refresh in demo mode
                await new Promise(resolve => setTimeout(resolve, 1000));
                this.updateUI();
                this.showToast('Devices refreshed (demo)', 'success');
            } else {
                // Make API call to fetch devices
                const response = await fetch(`${this.settings.apiEndpoint}/devices`);
                if (response.ok) {
                    const devices = await response.json();
                    this.devices.clear();
                    devices.forEach(device => {
                        this.devices.set(device.device_id, device);
                    });
                    this.updateUI();
                    this.showToast('Devices refreshed successfully', 'success');
                } else {
                    throw new Error('Failed to fetch devices');
                }
            }
        } catch (error) {
            console.error('Error refreshing devices:', error);
            this.showToast('Failed to refresh devices', 'error');
        } finally {
            this.hideLoading('refreshDevicesBtn');
        }
    }
    
    /**
     * Device filtering and search
     */
    filterDevices(searchTerm = '', filterType = 'all') {
        const tbody = document.getElementById('devicesTableBody');
        if (!tbody) return;
        
        let filteredDevices = Array.from(this.devices.values());
        
        // Apply search filter
        if (searchTerm) {
            filteredDevices = filteredDevices.filter(device => 
                device.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
                device.model.toLowerCase().includes(searchTerm.toLowerCase()) ||
                device.osVersion.toLowerCase().includes(searchTerm.toLowerCase())
            );
        }
        
        // Apply status filter
        if (filterType !== 'all') {
            filteredDevices = filteredDevices.filter(device => {
                switch (filterType) {
                    case 'online':
                        return device.status === 'online';
                    case 'offline':
                        return device.status === 'offline';
                    case 'android':
                        return device.osVersion.toLowerCase().includes('android');
                    default:
                        return true;
                }
            });
        }
        
        // Update table with filtered results
        this.renderDevicesTable(filteredDevices);
        this.updateDeviceCounts(filteredDevices);
    }
    
    renderDevicesTable(devices) {
        const tbody = document.getElementById('devicesTableBody');
        if (!tbody) return;
        
        tbody.innerHTML = devices.map(device => `
            <tr data-device-id="${device.id}">
                <td>
                    <input type="checkbox" class="device-checkbox" value="${device.id}">
                </td>
                <td>
                    <div class="device-cell">
                        <i class="fas fa-mobile-alt"></i>
                        ${device.name}
                    </div>
                </td>
                <td>
                    <span class="status-badge ${device.status}">
                        <i class="fas fa-circle"></i>
                        ${this.capitalizeFirst(device.status)}
                    </span>
                </td>
                <td>${device.model}</td>
                <td>${device.osVersion}</td>
                <td>
                    <div class="battery-indicator">
                        <div class="battery-level" style="width: ${device.batteryLevel || 0}%"></div>
                        <span>${device.batteryLevel || 0}%</span>
                    </div>
                </td>
                <td>
                    <div class="storage-indicator">
                        <div class="storage-level" style="width: ${device.storageUsed || 0}%"></div>
                        <span>${device.storageUsed || 0}%</span>
                    </div>
                </td>
                <td><span class="time-ago">${this.formatTimeAgo(device.lastSeen)}</span></td>
                <td>
                    <div class="action-buttons">
                        <button class="btn secondary xs" onclick="window.Dashboard.viewDevice('${device.id}')"
                                title="View Details">
                            <i class="fas fa-eye"></i>
                        </button>
                        <button class="btn warning xs" onclick="window.Dashboard.editDevice('${device.id}')"
                                title="Edit Device">
                            <i class="fas fa-edit"></i>
                        </button>
                        <button class="btn ${device.status === 'online' ? 'success' : 'info'} xs" 
                                onclick="window.Dashboard.toggleDeviceConnection('${device.id}')"
                                title="${device.status === 'online' ? 'Disconnect' : 'Connect'}">
                            <i class="fas fa-${device.status === 'online' ? 'unlink' : 'plug'}"></i>
                        </button>
                        <button class="btn danger xs" onclick="window.Dashboard.removeDevice('${device.id}')"
                                title="Remove Device">
                            <i class="fas fa-trash"></i>
                        </button>
                    </div>
                </td>
            </tr>
        `).join('');
        
        // Add event listeners for checkboxes
        const checkboxes = tbody.querySelectorAll('.device-checkbox');
        checkboxes.forEach(checkbox => {
            checkbox.addEventListener('change', () => this.updateBulkActions());
        });
    }
    
    updateDeviceCounts(devices) {
        const totalCount = devices.length;
        const onlineCount = devices.filter(d => d.status === 'online').length;
        const offlineCount = devices.filter(d => d.status === 'offline').length;
        const issuesCount = devices.filter(d => d.batteryLevel < 20 || d.storageUsed > 90).length;
        
        const totalEl = document.getElementById('totalDevicesCount');
        const onlineEl = document.getElementById('onlineDevicesCount');
        const offlineEl = document.getElementById('offlineDevicesCount');
        const issuesEl = document.getElementById('issuesDevicesCount');
        
        if (totalEl) totalEl.textContent = totalCount;
        if (onlineEl) onlineEl.textContent = onlineCount;
        if (offlineEl) offlineEl.textContent = offlineCount;
        if (issuesEl) issuesEl.textContent = issuesCount;
    }
    
    /**
     * Bulk actions
     */
    toggleSelectAllDevices(checked) {
        const checkboxes = document.querySelectorAll('.device-checkbox');
        checkboxes.forEach(checkbox => {
            checkbox.checked = checked;
        });
        this.updateBulkActions();
    }
    
    updateBulkActions() {
        const checkboxes = document.querySelectorAll('.device-checkbox:checked');
        const bulkActions = document.getElementById('bulkActions');
        const selectedCount = document.getElementById('selectedCount');
        
        if (checkboxes.length > 0) {
            if (bulkActions) bulkActions.style.display = 'block';
            if (selectedCount) selectedCount.textContent = checkboxes.length;
        } else {
            if (bulkActions) bulkActions.style.display = 'none';
        }
    }
    
    getSelectedDevices() {
        const checkboxes = document.querySelectorAll('.device-checkbox:checked');
        return Array.from(checkboxes).map(cb => cb.value);
    }
    
    bulkConnectDevices() {
        const selectedDevices = this.getSelectedDevices();
        if (selectedDevices.length === 0) return;
        
        this.showConfirmation(
            'Bulk Connect Devices',
            `Are you sure you want to connect ${selectedDevices.length} selected device(s)?`,
            () => {
                selectedDevices.forEach(deviceId => {
                    this.connectDevice(deviceId);
                });
                this.showToast(`${selectedDevices.length} devices connected`, 'success');
            }
        );
    }
    
    bulkDisconnectDevices() {
        const selectedDevices = this.getSelectedDevices();
        if (selectedDevices.length === 0) return;
        
        this.showConfirmation(
            'Bulk Disconnect Devices',
            `Are you sure you want to disconnect ${selectedDevices.length} selected device(s)?`,
            () => {
                selectedDevices.forEach(deviceId => {
                    this.disconnectDevice(deviceId);
                });
                this.showToast(`${selectedDevices.length} devices disconnected`, 'success');
            }
        );
    }
    
    bulkRemoveDevices() {
        const selectedDevices = this.getSelectedDevices();
        if (selectedDevices.length === 0) return;
        
        this.showConfirmation(
            'Bulk Remove Devices',
            `Are you sure you want to remove ${selectedDevices.length} selected device(s)? This action cannot be undone.`,
            () => {
                selectedDevices.forEach(deviceId => {
                    this.devices.delete(deviceId);
                });
                this.updateUI();
                this.showToast(`${selectedDevices.length} devices removed`, 'success');
            }
        );
    }
    
    /**
     * Device actions
     */
    toggleDeviceConnection(deviceId) {
        const device = this.devices.get(deviceId);
        if (!device) return;
        
        if (device.status === 'online') {
            this.disconnectDevice(deviceId);
        } else {
            this.connectDevice(deviceId);
        }
    }
    
    connectDevice(deviceId) {
        const device = this.devices.get(deviceId);
        if (device) {
            device.status = 'online';
            device.lastSeen = new Date();
            this.updateUI();
            
            // In production, make API call
            if (!this.settings.demoMode) {
                this.connectDeviceViaAPI(deviceId);
            }
        }
    }
    
    disconnectDevice(deviceId) {
        const device = this.devices.get(deviceId);
        if (device) {
            device.status = 'offline';
            this.updateUI();
            
            // In production, make API call
            if (!this.settings.demoMode) {
                this.disconnectDeviceViaAPI(deviceId);
            }
        }
    }

    /**
     * Connect device via API
     */
    async connectDeviceViaAPI(deviceId) {
        try {
            const response = await fetch(`${this.settings.apiEndpoint}/devices/${deviceId}/connect`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': this.getAuthHeader()
                }
            });

            if (response.ok) {
                const result = await response.json();
                this.showToast(`Device ${deviceId} connected successfully`, 'success');
                
                // Update device status from response
                if (result.status) {
                    const device = this.devices.get(deviceId);
                    if (device) {
                        device.status = result.status;
                        device.lastSeen = new Date(result.last_seen || Date.now());
                        this.updateUI();
                    }
                }
            } else {
                const error = await response.json();
                throw new Error(error.detail || 'Failed to connect device');
            }
        } catch (error) {
            console.error('Error connecting device:', error);
            this.showToast(`Failed to connect device: ${error.message}`, 'error');
            
            // Revert status change on error
            const device = this.devices.get(deviceId);
            if (device) {
                device.status = 'offline';
                this.updateUI();
            }
        }
    }

    /**
     * Disconnect device via API
     */
    async disconnectDeviceViaAPI(deviceId) {
        try {
            const response = await fetch(`${this.settings.apiEndpoint}/devices/${deviceId}/disconnect`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': this.getAuthHeader()
                }
            });

            if (response.ok) {
                const result = await response.json();
                this.showToast(`Device ${deviceId} disconnected successfully`, 'success');
                
                // Update device status from response
                if (result.status) {
                    const device = this.devices.get(deviceId);
                    if (device) {
                        device.status = result.status;
                        this.updateUI();
                    }
                }
            } else {
                const error = await response.json();
                throw new Error(error.detail || 'Failed to disconnect device');
            }
        } catch (error) {
            console.error('Error disconnecting device:', error);
            this.showToast(`Failed to disconnect device: ${error.message}`, 'error');
            
            // Revert status change on error
            const device = this.devices.get(deviceId);
            if (device) {
                device.status = 'online';
                this.updateUI();
            }
        }
    }

    /**
     * Update device via API
     */
    async updateDeviceViaAPI(deviceId, deviceData) {
        try {
            const response = await fetch(`${this.settings.apiEndpoint}/devices/${deviceId}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': this.getAuthHeader()
                },
                body: JSON.stringify(deviceData)
            });

            if (response.ok) {
                const result = await response.json();
                console.log('Device updated via API:', result);
            } else {
                const error = await response.json();
                throw new Error(error.detail || 'Failed to update device');
            }
        } catch (error) {
            console.error('Error updating device via API:', error);
            this.showToast(`Failed to update device: ${error.message}`, 'error');
        }
    }

    /**
     * Get authorization header for API requests
     */
    getAuthHeader() {
        const token = this.getAuthToken();
        return token ? `Bearer ${token}` : null;
    }

    /**
     * Get authentication token from storage
     */
    getAuthToken() {
        return localStorage.getItem('auth_token') || sessionStorage.getItem('auth_token');
    }
    
    /**
     * Confirmation dialog
     */
    showConfirmation(title, message, onConfirm) {
        const titleEl = document.getElementById('confirmationTitle');
        const messageEl = document.getElementById('confirmationMessage');
        
        if (titleEl) titleEl.textContent = title;
        if (messageEl) messageEl.textContent = message;
        
        this.pendingConfirmation = onConfirm;
        this.showModal('confirmationModal');
    }
    
    handleConfirmation() {
        if (this.pendingConfirmation) {
            this.pendingConfirmation();
            this.pendingConfirmation = null;
        }
        this.hideModal('confirmationModal');
    }
    
    /**
     * Pagination
     */
    prevPage() {
        if (this.currentPage > 1) {
            this.currentPage--;
            this.updateDevicesPage();
        }
    }
    
    nextPage() {
        const totalPages = Math.ceil(this.totalDevices / this.pageSize);
        if (this.currentPage < totalPages) {
            this.currentPage++;
            this.updateDevicesPage();
        }
    }

    /**
     * Initialize pagination properties
     */
    initializePagination() {
        this.currentPage = 1;
        this.pageSize = 10;
        this.totalDevices = 0;
    }

    /**
     * Update devices page with pagination
     */
    updateDevicesPage() {
        const devices = Array.from(this.devices.values());
        this.totalDevices = devices.length;
        
        // Apply current filters
        let filteredDevices = this.applyCurrentFilters(devices);
        this.totalDevices = filteredDevices.length;
        
        // Apply pagination
        const startIndex = (this.currentPage - 1) * this.pageSize;
        const endIndex = startIndex + this.pageSize;
        const paginatedDevices = filteredDevices.slice(startIndex, endIndex);
        
        // Render paginated devices
        this.renderDevicesTable(paginatedDevices);
        this.updatePaginationUI();
    }

    /**
     * Apply current search and filter criteria
     */
    applyCurrentFilters(devices) {
        let filtered = devices;
        
        // Apply search filter
        const searchTerm = document.getElementById('deviceSearch')?.value || '';
        if (searchTerm) {
            filtered = filtered.filter(device => 
                device.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
                device.model.toLowerCase().includes(searchTerm.toLowerCase()) ||
                device.osVersion.toLowerCase().includes(searchTerm.toLowerCase())
            );
        }
        
        // Apply status filter
        const filterType = document.getElementById('deviceFilter')?.value || 'all';
        if (filterType !== 'all') {
            filtered = filtered.filter(device => {
                switch (filterType) {
                    case 'online':
                        return device.status === 'online';
                    case 'offline':
                        return device.status === 'offline';
                    case 'android':
                        return device.osVersion.toLowerCase().includes('android');
                    default:
                        return true;
                }
            });
        }
        
        return filtered;
    }

    /**
     * Update pagination UI elements
     */
    updatePaginationUI() {
        const totalPages = Math.ceil(this.totalDevices / this.pageSize);
        
        // Update pagination info
        const paginationInfo = document.getElementById('paginationInfo');
        if (paginationInfo) {
            const startItem = this.totalDevices === 0 ? 0 : (this.currentPage - 1) * this.pageSize + 1;
            const endItem = Math.min(this.currentPage * this.pageSize, this.totalDevices);
            paginationInfo.textContent = `Showing ${startItem}-${endItem} of ${this.totalDevices} devices`;
        }
        
        // Update page indicator
        const pageIndicator = document.getElementById('currentPageIndicator');
        if (pageIndicator) {
            pageIndicator.textContent = `Page ${this.currentPage} of ${Math.max(1, totalPages)}`;
        }
        
        // Update pagination buttons
        const prevBtn = document.getElementById('prevPageBtn');
        const nextBtn = document.getElementById('nextPageBtn');
        
        if (prevBtn) {
            prevBtn.disabled = this.currentPage <= 1;
        }
        if (nextBtn) {
            nextBtn.disabled = this.currentPage >= totalPages || totalPages <= 1;
        }
    }

    /**
     * Utility methods
     */
    showLoading(buttonId) {
        const button = document.getElementById(buttonId);
        if (button) {
            button.disabled = true;
            const originalText = button.innerHTML;
            button.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Loading...';
            button.dataset.originalText = originalText;
        }
    }

    hideLoading(buttonId) {
        const button = document.getElementById(buttonId);
        if (button && button.dataset.originalText) {
            button.disabled = false;
            button.innerHTML = button.dataset.originalText;
            delete button.dataset.originalText;
        }
    }

    showToast(message, type = 'info', duration = 3000) {
        const toast = document.createElement('div');
        toast.className = `notification ${type}`;
        toast.innerHTML = `
            <div class="notification-icon">
                <i class="fas ${this.getAlertIcon(type)}"></i>
            </div>
            <div class="notification-content">
                <div class="notification-message">${message}</div>
            </div>
        `;
        
        document.body.appendChild(toast);
        
        // Position toast
        toast.style.position = 'fixed';
        toast.style.top = '20px';
        toast.style.right = '20px';
        toast.style.zIndex = '10000';
        toast.style.minWidth = '300px';
        
        // Auto remove
        setTimeout(() => {
            toast.remove();
        }, duration);
    }

    getAlertIcon(type) {
        switch (type) {
            case 'critical':
            case 'danger':
                return 'fa-exclamation-triangle';
            case 'warning':
                return 'fa-exclamation-circle';
            case 'success':
                return 'fa-check-circle';
            case 'info':
            default:
                return 'fa-info-circle';
        }
    }

    formatTimeAgo(timestamp) {
        const now = new Date();
        const diff = now - new Date(timestamp);
        const minutes = Math.floor(diff / 60000);
        const hours = Math.floor(minutes / 60);
        const days = Math.floor(hours / 24);

        if (days > 0) return `${days}d ago`;
        if (hours > 0) return `${hours}h ago`;
        if (minutes > 0) return `${minutes}m ago`;
        return 'Just now';
    }

    capitalizeFirst(str) {
        return str.charAt(0).toUpperCase() + str.slice(1);
    }

    downloadReport() {
        const data = {
            timestamp: new Date().toISOString(),
            devices: Array.from(this.devices.values()),
            securityAlerts: this.securityAlerts,
            networkStatus: this.networkStatus
        };
        
        const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `androidzen-report-${new Date().toISOString().split('T')[0]}.json`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    }

    /**
     * Settings management
     */
    loadSettings() {
        const defaultSettings = {
            refreshInterval: 30,
            theme: 'auto',
            language: 'en',
            enableNotifications: true,
            securityAlerts: true,
            deviceAlerts: true,
            performanceAlerts: false,
            demoMode: false
        };

        try {
            const saved = localStorage.getItem('androidzen-settings');
            return saved ? { ...defaultSettings, ...JSON.parse(saved) } : defaultSettings;
        } catch (error) {
            console.error('Error loading settings:', error);
            return defaultSettings;
        }
    }

    saveSettings(newSettings) {
        this.settings = { ...this.settings, ...newSettings };
        localStorage.setItem('androidzen-settings', JSON.stringify(this.settings));
        
        // Apply settings
        if (newSettings.refreshInterval) {
            this.setupRefreshInterval();
        }
        
        if (newSettings.theme) {
            this.applyTheme(newSettings.theme);
        }
    }

    applyTheme(theme) {
        const body = document.body;
        
        if (theme === 'dark') {
            body.setAttribute('data-theme', 'dark');
        } else if (theme === 'light') {
            body.removeAttribute('data-theme');
        } else {
            // Auto theme based on system preference
            if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
                body.setAttribute('data-theme', 'dark');
            } else {
                body.removeAttribute('data-theme');
            }
        }
        
        // Update charts theme
        if (window.Charts) {
            const isDark = body.getAttribute('data-theme') === 'dark';
            window.Charts.updateTheme(isDark);
        }
    }

    /**
     * Start demo mode with mock data updates
     */
    startDemoMode() {
        // Clear any existing demo intervals first
        this.stopDemoMode();
        
        console.log('Starting Dashboard demo mode with controlled updates');
        this.showToast('Demo Mode Enabled - Using mock data', 'info', 3000);
        
        // Add logout button to header
        const userInfo = document.querySelector('.header-user');
        if (userInfo && !userInfo.querySelector('.exit-demo-btn')) {
            const logoutBtn = document.createElement('button');
            logoutBtn.className = 'btn danger sm exit-demo-btn';
            logoutBtn.innerHTML = 'Exit Demo';
            logoutBtn.style.marginLeft = '10px';
            logoutBtn.onclick = () => {
                this.stopDemoMode();
                this.settings.demoMode = false;
                this.saveSettings({ demoMode: false });
                this.showToast('Demo Mode Disabled', 'success');
                setTimeout(() => window.location.reload(), 1000);
            };
            userInfo.appendChild(logoutBtn);
        }
        
        // Initialize demo intervals array
        this.demoIntervals = this.demoIntervals || [];
        
        // Update device statuses every 15 seconds (less frequent)
        this.demoIntervals.push(setInterval(() => {
            if (this.devices && this.devices.size > 0) {
                this.devices.forEach((device, id) => {
                    if (Math.random() < 0.05) { // 5% chance to change status (reduced)
                        const newStatus = device.status === 'online' ? 'offline' : 'online';
                        device.status = newStatus;
                        device.lastSeen = new Date();
                        this.updateDeviceStatus(device);
                    }
                });
            }
        }, 15000));

        // Add random security alerts every 30 seconds (much less frequent)
        this.demoIntervals.push(setInterval(() => {
            if (Math.random() < 0.2 && this.devices && this.devices.size > 0) { // 20% chance every interval
                const devices = Array.from(this.devices.keys());
                if (devices.length > 0) {
                    const randomDevice = devices[Math.floor(Math.random() * devices.length)];
                    const alertTypes = ['warning', 'info'];
                    const alertType = alertTypes[Math.floor(Math.random() * alertTypes.length)];
                    
                    this.addSecurityAlert({
                        id: 'alert_' + Date.now(),
                        type: alertType,
                        title: 'Demo Security Alert',
                        message: `Sample ${alertType} alert for demonstration`,
                        timestamp: new Date(),
                        device: randomDevice
                    });
                }
            }
        }, 30000));
    }
    
    /**
     * Stop demo mode and clear all intervals
     */
    stopDemoMode() {
        if (this.demoIntervals) {
            console.log('Stopping demo mode, clearing intervals');
            this.demoIntervals.forEach(interval => {
                if (interval) clearInterval(interval);
            });
            this.demoIntervals = [];
        }
        
        // Remove exit demo button
        const exitBtn = document.querySelector('.exit-demo-btn');
        if (exitBtn) {
            exitBtn.remove();
        }
        
        // Stop charts demo mode if it exists
        if (window.Charts && window.Charts.stopDemoMode) {
            window.Charts.stopDemoMode();
        }
    }

    /**
     * Update notification panel
     */
    updateNotificationPanel() {
        const notificationList = document.getElementById('notificationList');
        if (!notificationList) return;
        
        notificationList.innerHTML = this.notifications.map(notification => `
            <div class="notification ${notification.type} ${notification.read ? 'read' : ''}">
                <div class="notification-icon">
                    <i class="fas ${this.getAlertIcon(notification.type)}"></i>
                </div>
                <div class="notification-content">
                    <div class="notification-title">${notification.title}</div>
                    <div class="notification-message">${notification.message}</div>
                    <div class="notification-time">${this.formatTimeAgo(notification.timestamp)}</div>
                </div>
            </div>
        `).join('');
    }

    /**
     * Handle live metrics from WebSocket
     */
    handleLiveMetrics(payload) {
        const { device_id, metrics } = payload;
        console.log('Live metrics received:', device_id, metrics);
        
        // Update device if it exists
        if (this.devices.has(device_id)) {
            const device = this.devices.get(device_id);
            
            // Update device metrics
            if (metrics.battery_level !== undefined) device.batteryLevel = metrics.battery_level;
            if (metrics.cpu_usage !== undefined) device.cpuUsage = metrics.cpu_usage;
            if (metrics.memory_usage !== undefined) device.memoryUsage = metrics.memory_usage;
            if (metrics.storage_usage !== undefined) device.storageUsed = metrics.storage_usage;
            
            device.lastSeen = new Date();
            
            this.updateUI();
        }
    }

    /**
     * Update device action status
     */
    updateDeviceAction(payload) {
        const { device_id, action_type, status, result } = payload;
        console.log('Device action update:', payload);
        
        // Show toast notification for completed actions
        if (status === 'completed') {
            this.showToast(`${action_type} completed for device ${device_id}`, 'success');
        } else if (status === 'failed') {
            this.showToast(`${action_type} failed for device ${device_id}`, 'error');
        }
    }

    /**
     * Add system message
     */
    addSystemMessage(payload) {
        console.log('System message:', payload.message);
        
        // Add as notification
        this.addNotification({
            id: 'system_' + Date.now(),
            type: 'info',
            title: 'System Message',
            message: payload.message,
            timestamp: new Date(),
            read: false
        });
    }
}

// Export for global use
window.Dashboard = new DashboardManager();
