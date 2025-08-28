/**
 * Charts Management Module
 * Handles all Chart.js visualizations and real-time updates
 */
class ChartsManager {
    constructor() {
        this.charts = {};
        this.colors = {
            primary: '#2563eb',
            secondary: '#64748b',
            success: '#10b981',
            warning: '#f59e0b',
            danger: '#ef4444',
            info: '#3b82f6'
        };
        
        // Initialize charts when DOM is ready
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => this.initialize());
        } else {
            this.initialize();
        }
    }

    /**
     * Initialize all charts
     */
    initialize() {
        this.initializeStorageChart();
        this.initializePerformanceChart();
        this.initializeNetworkChart();
    }

    /**
     * Initialize storage usage chart (doughnut)
     */
    initializeStorageChart() {
        const ctx = document.getElementById('storageChart');
        if (!ctx) return;

        this.charts.storage = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: ['Used', 'Free'],
                datasets: [{
                    data: [0, 100],
                    backgroundColor: [
                        this.colors.primary,
                        '#e2e8f0'
                    ],
                    borderWidth: 0,
                    cutout: '70%'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
                    },
                    tooltip: {
                        callbacks: {
                            label: (context) => {
                                const label = context.label;
                                const value = context.parsed;
                                return `${label}: ${value}%`;
                            }
                        }
                    }
                },
                animation: {
                    animateRotate: true,
                    animateScale: false
                }
            },
            plugins: [{
                id: 'centerText',
                beforeDraw: (chart) => {
                    const ctx = chart.ctx;
                    const width = chart.width;
                    const height = chart.height;
                    const fontSize = Math.min(width, height) / 10;
                    
                    ctx.restore();
                    ctx.font = `${fontSize}px sans-serif`;
                    ctx.textAlign = 'center';
                    ctx.textBaseline = 'middle';
                    ctx.fillStyle = '#1e293b';
                    
                    const used = chart.data.datasets[0].data[0];
                    const text = `${used}%`;
                    const centerX = width / 2;
                    const centerY = height / 2;
                    
                    ctx.fillText(text, centerX, centerY - 10);
                    ctx.font = `${fontSize * 0.4}px sans-serif`;
                    ctx.fillStyle = '#64748b';
                    ctx.fillText('Used', centerX, centerY + 15);
                    ctx.save();
                }
            }]
        });

        // Update with initial data
        this.updateStorageChart({
            used: 45,
            total: 128,
            free: 83
        });
    }

    /**
     * Initialize performance metrics chart (line)
     */
    initializePerformanceChart() {
        const ctx = document.getElementById('performanceChart');
        if (!ctx) return;

        const now = new Date();
        const timeLabels = [];
        const initialData = [];

        // Generate last 10 data points
        for (let i = 9; i >= 0; i--) {
            const time = new Date(now - i * 60000); // 1 minute intervals
            timeLabels.push(time.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }));
            initialData.push(Math.random() * 100);
        }

        this.charts.performance = new Chart(ctx, {
            type: 'line',
            data: {
                labels: timeLabels,
                datasets: [{
                    label: 'CPU Usage',
                    data: initialData,
                    borderColor: this.colors.primary,
                    backgroundColor: this.colors.primary + '20',
                    borderWidth: 2,
                    fill: true,
                    tension: 0.4,
                    pointRadius: 0,
                    pointHoverRadius: 4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: {
                    intersect: false,
                    mode: 'index'
                },
                scales: {
                    x: {
                        display: true,
                        grid: {
                            display: false
                        }
                    },
                    y: {
                        display: true,
                        min: 0,
                        max: 100,
                        ticks: {
                            callback: (value) => `${value}%`
                        },
                        grid: {
                            color: '#f1f5f9'
                        }
                    }
                },
                plugins: {
                    legend: {
                        display: false
                    },
                    tooltip: {
                        backgroundColor: '#1e293b',
                        titleColor: '#ffffff',
                        bodyColor: '#ffffff',
                        cornerRadius: 8
                    }
                },
                animation: {
                    duration: 300,
                    easing: 'easeInOutQuart'
                }
            }
        });
    }

    /**
     * Initialize network traffic chart (line)
     */
    initializeNetworkChart() {
        const ctx = document.getElementById('networkChart');
        if (!ctx) return;

        const now = new Date();
        const timeLabels = [];
        const uploadData = [];
        const downloadData = [];

        // Generate last 10 data points
        for (let i = 9; i >= 0; i--) {
            const time = new Date(now - i * 60000);
            timeLabels.push(time.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }));
            uploadData.push(Math.random() * 50);
            downloadData.push(Math.random() * 100);
        }

        this.charts.network = new Chart(ctx, {
            type: 'line',
            data: {
                labels: timeLabels,
                datasets: [
                    {
                        label: 'Download',
                        data: downloadData,
                        borderColor: this.colors.success,
                        backgroundColor: this.colors.success + '20',
                        borderWidth: 2,
                        fill: false,
                        tension: 0.4,
                        pointRadius: 0,
                        pointHoverRadius: 4
                    },
                    {
                        label: 'Upload',
                        data: uploadData,
                        borderColor: this.colors.info,
                        backgroundColor: this.colors.info + '20',
                        borderWidth: 2,
                        fill: false,
                        tension: 0.4,
                        pointRadius: 0,
                        pointHoverRadius: 4
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: {
                    intersect: false,
                    mode: 'index'
                },
                scales: {
                    x: {
                        display: true,
                        grid: {
                            display: false
                        }
                    },
                    y: {
                        display: true,
                        min: 0,
                        ticks: {
                            callback: (value) => `${value} MB/s`
                        },
                        grid: {
                            color: '#f1f5f9'
                        }
                    }
                },
                plugins: {
                    legend: {
                        display: true,
                        position: 'top',
                        labels: {
                            usePointStyle: true,
                            pointStyle: 'circle',
                            padding: 15,
                            font: {
                                size: 12
                            }
                        }
                    },
                    tooltip: {
                        backgroundColor: '#1e293b',
                        titleColor: '#ffffff',
                        bodyColor: '#ffffff',
                        cornerRadius: 8
                    }
                },
                animation: {
                    duration: 300,
                    easing: 'easeInOutQuart'
                }
            }
        });
    }

    /**
     * Update storage chart with new data
     */
    updateStorageChart(data) {
        if (!this.charts.storage) return;

        const usedPercentage = Math.round((data.used / data.total) * 100);
        const freePercentage = 100 - usedPercentage;

        this.charts.storage.data.datasets[0].data = [usedPercentage, freePercentage];
        this.charts.storage.update('active');

        // Update storage details
        this.updateStorageDetails(data);
    }

    /**
     * Update storage details section
     */
    updateStorageDetails(data) {
        const container = document.getElementById('storageDetails');
        if (!container) return;

        container.innerHTML = `
            <div class="storage-item">
                <span class="storage-label">Total Storage</span>
                <span class="storage-value">${data.total} GB</span>
            </div>
            <div class="storage-item">
                <span class="storage-label">Used Storage</span>
                <span class="storage-value">${data.used} GB</span>
            </div>
            <div class="storage-item">
                <span class="storage-label">Free Storage</span>
                <span class="storage-value">${data.free} GB</span>
            </div>
            <div class="storage-item">
                <span class="storage-label">Usage Percentage</span>
                <span class="storage-value">${Math.round((data.used / data.total) * 100)}%</span>
            </div>
        `;
    }

    /**
     * Update performance chart with new data
     */
    updatePerformanceChart(data) {
        if (!this.charts.performance) return;

        const chart = this.charts.performance;
        const now = new Date();
        const timeLabel = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

        // Add new data point
        chart.data.labels.push(timeLabel);
        chart.data.datasets[0].data.push(data.value);

        // Remove old data points (keep last 10)
        if (chart.data.labels.length > 10) {
            chart.data.labels.shift();
            chart.data.datasets[0].data.shift();
        }

        // Update chart label based on metric type
        let label = 'Value';
        let color = this.colors.primary;
        
        switch (data.type) {
            case 'cpu':
                label = 'CPU Usage';
                color = this.colors.primary;
                break;
            case 'memory':
                label = 'Memory Usage';
                color = this.colors.warning;
                break;
            case 'battery':
                label = 'Battery Level';
                color = this.colors.success;
                break;
            case 'temperature':
                label = 'Temperature';
                color = this.colors.danger;
                break;
        }

        chart.data.datasets[0].label = label;
        chart.data.datasets[0].borderColor = color;
        chart.data.datasets[0].backgroundColor = color + '20';

        chart.update('none');
    }

    /**
     * Update network chart with new data
     */
    updateNetworkChart(data) {
        if (!this.charts.network) return;

        const chart = this.charts.network;
        const now = new Date();
        const timeLabel = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

        // Add new data points
        chart.data.labels.push(timeLabel);
        chart.data.datasets[0].data.push(data.download);
        chart.data.datasets[1].data.push(data.upload);

        // Remove old data points (keep last 10)
        if (chart.data.labels.length > 10) {
            chart.data.labels.shift();
            chart.data.datasets[0].data.shift();
            chart.data.datasets[1].data.shift();
        }

        chart.update('none');
    }

    /**
     * Change performance metric type
     */
    changePerformanceMetric(type) {
        // This will be called when user changes the dropdown
        // The actual data update will come via WebSocket
        console.log(`Performance metric changed to: ${type}`);
        
        // Request new data from server
        if (window.wsClient) {
            window.wsClient.send({
                type: 'change_performance_metric',
                payload: { metric: type },
                timestamp: Date.now()
            });
        }
    }

    /**
     * Change performance timeframe
     */
    changePerformanceTimeframe(timeframe) {
        console.log(`Performance timeframe changed to: ${timeframe}`);
        
        // Request new data from server
        if (window.wsClient) {
            window.wsClient.send({
                type: 'change_performance_timeframe',
                payload: { timeframe: timeframe },
                timestamp: Date.now()
            });
        }
    }

    /**
     * Resize charts when container size changes
     */
    resizeCharts() {
        Object.values(this.charts).forEach(chart => {
            if (chart && typeof chart.resize === 'function') {
                chart.resize();
            }
        });
    }

    /**
     * Update chart theme colors
     */
    updateTheme(isDark = false) {
        const textColor = isDark ? '#f1f5f9' : '#1e293b';
        const gridColor = isDark ? '#334155' : '#f1f5f9';

        Object.values(this.charts).forEach(chart => {
            if (!chart) return;

            // Update scales
            if (chart.options.scales) {
                Object.values(chart.options.scales).forEach(scale => {
                    if (scale.ticks) {
                        scale.ticks.color = textColor;
                    }
                    if (scale.grid) {
                        scale.grid.color = gridColor;
                    }
                });
            }

            // Update legend
            if (chart.options.plugins?.legend?.labels) {
                chart.options.plugins.legend.labels.color = textColor;
            }

            chart.update('none');
        });
    }

    /**
     * Destroy all charts
     */
    destroy() {
        Object.values(this.charts).forEach(chart => {
            if (chart && typeof chart.destroy === 'function') {
                chart.destroy();
            }
        });
        this.charts = {};
    }

    /**
     * Generate mock performance data for demo
     */
    generateMockPerformanceData() {
        const types = ['cpu', 'memory', 'battery', 'temperature'];
        const type = types[Math.floor(Math.random() * types.length)];
        
        let value;
        switch (type) {
            case 'cpu':
                value = Math.random() * 100;
                break;
            case 'memory':
                value = Math.random() * 100;
                break;
            case 'battery':
                value = Math.max(20, Math.random() * 100);
                break;
            case 'temperature':
                value = 30 + Math.random() * 40;
                break;
        }

        return { type, value: Math.round(value) };
    }

    /**
     * Generate mock network data for demo
     */
    generateMockNetworkData() {
        return {
            download: Math.random() * 100,
            upload: Math.random() * 50
        };
    }

    /**
     * Start demo mode with mock data
     */
    startDemoMode() {
        // Clear any existing intervals first
        this.stopDemoMode();
        
        console.log('Starting Charts demo mode');
        
        // Update performance chart every 5 seconds (less frequent)
        this.demoIntervals = this.demoIntervals || [];
        
        this.demoIntervals.push(setInterval(() => {
            if (this.performanceChart) {
                this.updatePerformanceChart(this.generateMockPerformanceData());
            }
        }, 5000));

        // Update network chart every 7 seconds (less frequent)
        this.demoIntervals.push(setInterval(() => {
            if (this.networkChart) {
                this.updateNetworkChart(this.generateMockNetworkData());
            }
        }, 7000));

        // Update storage chart every 10 seconds (much less frequent)
        this.demoIntervals.push(setInterval(() => {
            if (this.storageChart) {
                this.updateStorageChart({
                    used: 40 + Math.random() * 20,
                    total: 128,
                    free: 88 - Math.random() * 20
                });
            }
        }, 10000));
    }
    
    /**
     * Stop demo mode and clear intervals
     */
    stopDemoMode() {
        if (this.demoIntervals) {
            this.demoIntervals.forEach(interval => clearInterval(interval));
            this.demoIntervals = [];
        }
    }
}

// Export for global use
window.Charts = new ChartsManager();

// Handle window resize
window.addEventListener('resize', () => {
    if (window.Charts) {
        window.Charts.resizeCharts();
    }
});
