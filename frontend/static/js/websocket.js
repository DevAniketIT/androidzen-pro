/**
 * WebSocket Client for Real-time Updates
 * Handles connection, message routing, and automatic reconnection with improved state management
 */
class WebSocketClient {
    constructor(url = 'ws://localhost:8000/ws', options = {}) {
        this.url = url;
        this.options = {
            maxReconnectAttempts: 10,
            reconnectDelay: 1000,
            heartbeatInterval: 30000, // 30 seconds
            enableHeartbeat: true,
            autoConnect: true,
            messageQueueEnabled: true,
            ...options
        };
        
        this.ws = null;
        this.reconnectAttempts = 0;
        this.isConnecting = false;
        this.isConnected = false;
        this.messageHandlers = new Map();
        this.connectionStatusCallbacks = [];
        this.messageQueue = [];
        this.subscriptions = new Set();
        this.heartbeatTimer = null;
        this.clientId = null;
        this.userId = null;
        
        // Bind methods
        this.connect = this.connect.bind(this);
        this.onMessage = this.onMessage.bind(this);
        this.onOpen = this.onOpen.bind(this);
        this.onClose = this.onClose.bind(this);
        this.onError = this.onError.bind(this);
        this.sendHeartbeat = this.sendHeartbeat.bind(this);
        
        // Initialize default message handlers
        this.initializeDefaultHandlers();
        
        // Auto-connect if enabled
        if (this.options.autoConnect) {
            this.connect();
        }
    }

    /**
     * Initialize default message handlers
     */
    initializeDefaultHandlers() {
        // Register handlers for new message types
        this.registerHandler('live_metrics', this.handleLiveMetrics.bind(this));
        this.registerHandler('notification', this.handleNotification.bind(this));
        this.registerHandler('device_action', this.handleDeviceAction.bind(this));
        this.registerHandler('system_message', this.handleSystemMessage.bind(this));
        this.registerHandler('performance_data', this.handlePerformanceData.bind(this));
        this.registerHandler('heartbeat', this.handleHeartbeat.bind(this));
    }

    /**
     * Establish WebSocket connection
     */
    connect() {
        if (this.isConnecting || (this.ws && this.ws.readyState === WebSocket.OPEN)) {
            return Promise.resolve();
        }

        return new Promise((resolve, reject) => {
            this.isConnecting = true;
            this.updateConnectionStatus('connecting', 'Connecting...');

            try {
                // Add auth token if available
                let wsUrl = this.url;
                const token = this.getAuthToken();
                if (token) {
                    wsUrl += `?token=${encodeURIComponent(token)}`;
                }
                
                this.ws = new WebSocket(wsUrl);
                this.ws.onopen = (event) => {
                    this.onOpen(event);
                    resolve();
                };
                this.ws.onmessage = this.onMessage;
                this.ws.onclose = this.onClose;
                this.ws.onerror = (error) => {
                    this.onError(error);
                    reject(error);
                };
            } catch (error) {
                console.error('WebSocket connection error:', error);
                this.isConnecting = false;
                reject(error);
                this.handleReconnect();
            }
        });
    }

    /**
     * Handle connection open
     */
    onOpen(event) {
        console.log('WebSocket connected');
        this.isConnecting = false;
        this.isConnected = true;
        this.reconnectAttempts = 0;
        this.updateConnectionStatus('connected', 'Connected');
        
        // Generate client ID if not set
        if (!this.clientId) {
            this.clientId = this.generateClientId();
        }
        
        // Process queued messages
        this.processMessageQueue();
        
        // Re-subscribe to topics
        this.resubscribeToTopics();
        
        // Start heartbeat if enabled
        if (this.options.enableHeartbeat) {
            this.startHeartbeat();
        }
        
        // Trigger connection established event
        this.emit('connected', { clientId: this.clientId });
    }

    /**
     * Handle incoming messages
     */
    onMessage(event) {
        try {
            const message = JSON.parse(event.data);
            const { type, data, timestamp } = message;
            
            // Log message for debugging
            if (type !== 'heartbeat') {
                console.debug('WebSocket message received:', type, data);
            }
            
            this.routeMessage({ type, payload: data, timestamp });
        } catch (error) {
            console.error('Error parsing WebSocket message:', error);
        }
    }

    /**
     * Handle connection close
     */
    onClose(event) {
        console.log('WebSocket disconnected:', event.code, event.reason);
        this.isConnecting = false;
        this.isConnected = false;
        this.updateConnectionStatus('disconnected', 'Disconnected');
        
        // Stop heartbeat
        this.stopHeartbeat();
        
        // Emit disconnected event
        this.emit('disconnected', { code: event.code, reason: event.reason });
        
        // Attempt reconnection unless it was a clean close
        if (event.code !== 1000 && this.reconnectAttempts < this.options.maxReconnectAttempts) {
            this.handleReconnect();
        } else if (event.code !== 1000) {
            this.updateConnectionStatus('failed', 'Connection Failed - Max retries exceeded');
        }
    }

    /**
     * Handle connection error
     */
    onError(error) {
        console.error('WebSocket error:', error);
        this.updateConnectionStatus('error', 'Connection Error');
    }

    /**
     * Route incoming messages to appropriate handlers
     */
    routeMessage(data) {
        const { type, payload } = data;
        
        // Handle system messages
        switch (type) {
            case 'ping':
                this.send({ type: 'pong', timestamp: Date.now() });
                return;
                
            case 'device_update':
                this.handleDeviceUpdate(payload);
                break;
                
            case 'security_alert':
                this.handleSecurityAlert(payload);
                break;
                
            case 'performance_data':
                this.handlePerformanceData(payload);
                break;
                
            case 'storage_update':
                this.handleStorageUpdate(payload);
                break;
                
            case 'network_status':
                this.handleNetworkStatus(payload);
                break;
                
            case 'notification':
                this.handleNotification(payload);
                break;
        }
        
        // Call registered handlers
        if (this.messageHandlers.has(type)) {
            this.messageHandlers.get(type).forEach(handler => {
                try {
                    handler(payload);
                } catch (error) {
                    console.error(`Error in message handler for ${type}:`, error);
                }
            });
        }
    }

    /**
     * Handle device updates
     */
    handleDeviceUpdate(payload) {
        if (window.Dashboard) {
            window.Dashboard.updateDeviceStatus(payload);
        }
    }

    /**
     * Handle security alerts
     */
    handleSecurityAlert(payload) {
        if (window.Dashboard) {
            window.Dashboard.addSecurityAlert(payload);
        }
        
        // Show browser notification if enabled
        if (Notification.permission === 'granted') {
            new Notification('Security Alert', {
                body: payload.message,
                icon: '/static/images/security-icon.png'
            });
        }
    }

    /**
     * Handle performance data updates
     */
    handlePerformanceData(payload) {
        if (window.Charts) {
            window.Charts.updatePerformanceChart(payload);
        }
    }

    /**
     * Handle storage updates
     */
    handleStorageUpdate(payload) {
        if (window.Charts) {
            window.Charts.updateStorageChart(payload);
        }
    }

    /**
     * Handle network status updates
     */
    handleNetworkStatus(payload) {
        if (window.Dashboard) {
            window.Dashboard.updateNetworkStatus(payload);
        }
        
        if (window.Charts) {
            window.Charts.updateNetworkChart(payload);
        }
    }

    /**
     * Handle notifications
     */
    handleNotification(payload) {
        if (window.Dashboard) {
            window.Dashboard.addNotification(payload);
        }
    }

    /**
     * Register message handler by type
     */
    on(type, handler) {
        if (!this.messageHandlers.has(type)) {
            this.messageHandlers.set(type, []);
        }
        this.messageHandlers.get(type).push(handler);
    }

    /**
     * Unregister message handler
     */
    off(type, handler) {
        if (this.messageHandlers.has(type)) {
            const handlers = this.messageHandlers.get(type);
            const index = handlers.indexOf(handler);
            if (index > -1) {
                handlers.splice(index, 1);
            }
        }
    }

    /**
     * Handle reconnection logic
     */
    handleReconnect() {
        if (this.reconnectAttempts >= this.options.maxReconnectAttempts) {
            console.error('Max reconnection attempts reached');
            this.updateConnectionStatus('failed', 'Connection Failed');
            return;
        }

        this.reconnectAttempts++;
        const delay = this.options.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1);
        
        console.log(`Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts}/${this.options.maxReconnectAttempts})`);
        this.updateConnectionStatus('reconnecting', `Reconnecting... (${this.reconnectAttempts}/${this.options.maxReconnectAttempts})`);
        
        setTimeout(() => {
            this.connect();
        }, delay);
    }

    /**
     * Update connection status UI
     */
    updateConnectionStatus(status, message) {
        const indicator = document.getElementById('statusIndicator');
        const text = document.getElementById('statusText');
        
        if (indicator && text) {
            indicator.className = `status-indicator ${status}`;
            text.textContent = message;
        }
        
        // Call registered callbacks
        this.connectionStatusCallbacks.forEach(callback => {
            try {
                callback(status, message);
            } catch (error) {
                console.error('Error in connection status callback:', error);
            }
        });
    }

    /**
     * Register connection status callback
     */
    onConnectionStatusChange(callback) {
        this.connectionStatusCallbacks.push(callback);
    }

    /**
     * Generate unique client ID
     */
    generateClientId() {
        return 'client_' + Math.random().toString(36).substr(2, 9) + '_' + Date.now();
    }

    /**
     * Request device scan
     */
    scanDevices() {
        this.send({
            type: 'scan_devices',
            timestamp: Date.now()
        });
    }

    /**
     * Request data refresh
     */
    refreshData() {
        this.send({
            type: 'refresh_data',
            timestamp: Date.now()
        });
    }

    /**
     * Request security scan
     */
    performSecurityScan() {
        this.send({
            type: 'security_scan',
            timestamp: Date.now()
        });
    }

    /**
     * Update settings
     */
    updateSettings(settings) {
        this.send({
            type: 'update_settings',
            payload: settings,
            timestamp: Date.now()
        });
    }

    /**
     * Subscribe to specific device updates
     */
    subscribeToDevice(deviceId) {
        this.send({
            type: 'subscribe_device',
            payload: { deviceId },
            timestamp: Date.now()
        });
    }

    /**
     * Unsubscribe from device updates
     */
    unsubscribeFromDevice(deviceId) {
        this.send({
            type: 'unsubscribe_device',
            payload: { deviceId },
            timestamp: Date.now()
        });
    }

    /**
     * Close connection
     */
    close() {
        if (this.ws) {
            this.ws.close(1000, 'Client closing connection');
        }
    }

    /**
     * Get connection state
     */
    getConnectionState() {
        if (!this.ws) return 'CLOSED';
        
        switch (this.ws.readyState) {
            case WebSocket.CONNECTING:
                return 'CONNECTING';
            case WebSocket.OPEN:
                return 'OPEN';
            case WebSocket.CLOSING:
                return 'CLOSING';
            case WebSocket.CLOSED:
                return 'CLOSED';
            default:
                return 'UNKNOWN';
        }
    }

    /**
     * Get authentication token from localStorage
     */
    getAuthToken() {
        return localStorage.getItem('authToken') || sessionStorage.getItem('authToken');
    }

    /**
     * Process queued messages when connection is restored
     */
    processMessageQueue() {
        if (this.options.messageQueueEnabled && this.messageQueue.length > 0) {
            console.log(`Processing ${this.messageQueue.length} queued messages`);
            const queue = [...this.messageQueue];
            this.messageQueue = [];
            
            queue.forEach(message => {
                this.send(message);
            });
        }
    }

    /**
     * Re-subscribe to all topics after reconnection
     */
    resubscribeToTopics() {
        this.subscriptions.forEach(topic => {
            this.subscribe(topic);
        });
    }

    /**
     * Subscribe to a topic
     */
    subscribe(topic) {
        this.subscriptions.add(topic);
        this.send({
            type: 'subscription',
            data: { topic }
        });
    }

    /**
     * Unsubscribe from a topic
     */
    unsubscribe(topic) {
        this.subscriptions.delete(topic);
        this.send({
            type: 'unsubscription',
            data: { topic }
        });
    }

    /**
     * Start heartbeat timer
     */
    startHeartbeat() {
        this.stopHeartbeat(); // Clear any existing timer
        this.heartbeatTimer = setInterval(this.sendHeartbeat, this.options.heartbeatInterval);
    }

    /**
     * Stop heartbeat timer
     */
    stopHeartbeat() {
        if (this.heartbeatTimer) {
            clearInterval(this.heartbeatTimer);
            this.heartbeatTimer = null;
        }
    }

    /**
     * Send heartbeat message
     */
    sendHeartbeat() {
        if (this.isConnected) {
            this.send({
                type: 'heartbeat',
                data: { timestamp: Date.now() }
            });
        }
    }

    /**
     * Handle heartbeat response
     */
    handleHeartbeat(payload) {
        console.debug('Heartbeat response received:', payload);
    }

    /**
     * Handle live metrics updates
     */
    handleLiveMetrics(payload) {
        if (window.Charts) {
            window.Charts.updateLiveMetrics(payload);
        }
        console.debug('Live metrics received:', payload);
    }

    /**
     * Handle device action status updates
     */
    handleDeviceAction(payload) {
        if (window.Dashboard) {
            window.Dashboard.updateDeviceAction(payload);
        }
        console.debug('Device action update:', payload);
    }

    /**
     * Handle system messages
     */
    handleSystemMessage(payload) {
        console.info('System message:', payload.message);
        if (window.Dashboard) {
            window.Dashboard.addSystemMessage(payload);
        }
    }

    /**
     * Register a message handler
     */
    registerHandler(type, handler) {
        if (!this.messageHandlers.has(type)) {
            this.messageHandlers.set(type, []);
        }
        this.messageHandlers.get(type).push(handler);
    }

    /**
     * Emit event to all listeners
     */
    emit(event, data) {
        if (this.messageHandlers.has(event)) {
            this.messageHandlers.get(event).forEach(handler => {
                try {
                    handler(data);
                } catch (error) {
                    console.error(`Error in event handler for ${event}:`, error);
                }
            });
        }
    }

    /**
     * Enhanced send method with queueing support
     */
    send(data) {
        if (this.isConnected && this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify(data));
        } else if (this.options.messageQueueEnabled) {
            console.warn('WebSocket not connected, message queued:', data);
            this.messageQueue.push(data);
        } else {
            console.warn('WebSocket not connected, message dropped:', data);
        }
    }
}

// Export for global use
window.WebSocketClient = WebSocketClient;

// Auto-initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    // Get WebSocket URL from settings or use default
    const wsUrl = localStorage.getItem('wsEndpoint') || 'ws://localhost:8000/ws';
    window.wsClient = new WebSocketClient(wsUrl);
});
