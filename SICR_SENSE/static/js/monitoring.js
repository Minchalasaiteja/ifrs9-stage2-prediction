// SICRSense Monitoring Dashboard JavaScript
class MonitoringDashboard {
    constructor() {
        this.ws = null;
        this.charts = {};
        this.currentSection = 'overview';
        this.autoRefreshInterval = null;
        this.metricsHistory = {
            predictions: [],
            latencies: [],
            connections: []
        };
        this.init();
    }
    
    init() {
        this.setupWebSocket();
        this.setupNavigation();
        this.initializeCharts();
        this.fetchInitialData();
        this.startAutoRefresh();
        this.setupEventListeners();
    }
    
    setupWebSocket() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const token = localStorage.getItem('access_token');
        const wsUrl = `${protocol}//${window.location.host}/ws${token ? `?token=${token}` : ''}`;
        
        this.ws = new WebSocket(wsUrl);
        
        this.ws.onopen = () => {
            console.log('Monitoring WebSocket connected');
            this.updateConnectionStatus(true);
            this.ws.send(JSON.stringify({ type: 'subscribe_metrics' }));
            this.ws.send(JSON.stringify({ type: 'subscribe_predictions' }));
            this.ws.send(JSON.stringify({ type: 'request_metrics' }));
        };
        
        this.ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            this.handleMessage(data);
        };
        
        this.ws.onclose = () => {
            this.updateConnectionStatus(false);
            setTimeout(() => this.setupWebSocket(), 3000);
        };
    }
    
    handleMessage(data) {
        switch(data.type) {
            case 'metrics_update':
                this.updateRealTimeMetrics(data.data);
                break;
            case 'metrics_snapshot':
                this.updateAllMetrics(data.data);
                break;
            case 'system_alert':
                this.showAlert(data);
                break;
            case 'prediction_update':
                this.addLivePrediction(data.data);
                break;
        }
    }
    
    setupNavigation() {
        document.querySelectorAll('[data-section]').forEach(item => {
            item.addEventListener('click', (e) => {
                e.preventDefault();
                this.switchSection(item.dataset.section);
            });
        });
    }
    
    switchSection(section) {
        document.querySelectorAll('[id^="section-"]').forEach(s => {
            s.classList.add('hidden');
        });
        
        const target = document.getElementById(`section-${section}`);
        if (target) {
            target.classList.remove('hidden');
            gsap.from(target.children, {
                opacity: 0,
                y: 30,
                duration: 0.6,
                stagger: 0.1,
                ease: 'power2.out'
            });
        }
        
        document.querySelectorAll('[data-section]').forEach(item => {
            item.classList.remove('active');
        });
        document.querySelector(`[data-section="${section}"]`)?.classList.add('active');
        
        this.currentSection = section;
        this.loadSectionData(section);
    }
    
    initializeCharts() {
        // Prediction Rate Chart
        const prCtx = document.getElementById('predictionRateChart');
        if (prCtx) {
            this.charts.predictionRate = new Chart(prCtx, {
                type: 'line',
                data: {
                    labels: [],
                    datasets: [{
                        label: 'Predictions/min',
                        data: [],
                        borderColor: '#00f0ff',
                        backgroundColor: 'rgba(0, 240, 255, 0.1)',
                        borderWidth: 2,
                        fill: true,
                        tension: 0.4,
                        pointRadius: 0
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { legend: { display: false } },
                    scales: {
                        x: { 
                            grid: { color: 'rgba(255,255,255,0.05)' },
                            ticks: { color: '#a0a0b0', maxTicksLimit: 10 }
                        },
                        y: {
                            grid: { color: 'rgba(255,255,255,0.05)' },
                            ticks: { color: '#a0a0b0' },
                            beginAtZero: true
                        }
                    },
                    animation: { duration: 750, easing: 'easeInOutQuart' }
                }
            });
        }
        
        // Latency Distribution Chart
        const ldCtx = document.getElementById('latencyDistributionChart');
        if (ldCtx) {
            this.charts.latencyDist = new Chart(ldCtx, {
                type: 'bar',
                data: {
                    labels: ['<50ms', '50-100ms', '100-250ms', '250-500ms', '>500ms'],
                    datasets: [{
                        label: 'Requests',
                        data: [0, 0, 0, 0, 0],
                        backgroundColor: [
                            'rgba(16, 185, 129, 0.6)',
                            'rgba(0, 240, 255, 0.6)',
                            'rgba(245, 158, 11, 0.6)',
                            'rgba(249, 115, 22, 0.6)',
                            'rgba(239, 68, 68, 0.6)'
                        ],
                        borderWidth: 1,
                        borderRadius: 8
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { legend: { display: false } },
                    scales: {
                        y: {
                            grid: { color: 'rgba(255,255,255,0.05)' },
                            ticks: { color: '#a0a0b0' }
                        },
                        x: {
                            grid: { display: false },
                            ticks: { color: '#a0a0b0' }
                        }
                    }
                }
            });
        }
        
        // Risk Distribution Doughnut
        const rdCtx = document.getElementById('riskDistributionDoughnut');
        if (rdCtx) {
            this.charts.riskDist = new Chart(rdCtx, {
                type: 'doughnut',
                data: {
                    labels: ['Very Low', 'Low', 'Medium', 'High', 'Very High'],
                    datasets: [{
                        data: [30, 25, 20, 15, 10],
                        backgroundColor: ['#10b981', '#34d399', '#fbbf24', '#f97316', '#ef4444'],
                        borderWidth: 0
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            position: 'bottom',
                            labels: { color: '#a0a0b0', padding: 20 }
                        }
                    }
                }
            });
        }
        
        // Resource Timeline
        const rtCtx = document.getElementById('resourceTimeline');
        if (rtCtx) {
            this.charts.resources = new Chart(rtCtx, {
                type: 'line',
                data: {
                    labels: [],
                    datasets: [
                        {
                            label: 'CPU',
                            data: [],
                            borderColor: '#00f0ff',
                            tension: 0.4,
                            fill: false
                        },
                        {
                            label: 'Memory',
                            data: [],
                            borderColor: '#7c3aed',
                            tension: 0.4,
                            fill: false
                        }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        y: {
                            beginAtZero: true,
                            max: 100,
                            grid: { color: 'rgba(255,255,255,0.05)' }
                        },
                        x: {
                            grid: { color: 'rgba(255,255,255,0.05)' }
                        }
                    }
                }
            });
        }
    }
    
    updateRealTimeMetrics(data) {
        // Update counter animations
        if (data.total_predictions !== undefined && data.total_predictions > 0) {
            // We'll let the initial API fetch or the live prediction events increment this,
            // to avoid overriding it with the cache size.
        }
        this.animateValue('activeConnections', data.active_connections || 0);
        if (data.avg_latency_ms !== undefined) {
            this.animateValue('avgLatency', data.avg_latency_ms + 'ms');
        }
        
        // Update system metrics
        if (data.system_metrics) {
            document.getElementById('cpuValue').textContent = 
                Math.round(data.system_metrics.cpu?.percent || 0) + '%';
            document.getElementById('memoryValue').textContent = 
                Math.round(data.system_metrics.memory?.percent || 0) + '%';
            
            // Update resource timeline
            if (this.charts.resources) {
                const chart = this.charts.resources;
                chart.data.labels.push(new Date().toLocaleTimeString());
                chart.data.datasets[0].data.push(data.system_metrics.cpu?.percent || 0);
                chart.data.datasets[1].data.push(data.system_metrics.memory?.percent || 0);
                
                if (chart.data.labels.length > 20) {
                    chart.data.labels.shift();
                    chart.data.datasets[0].data.shift();
                    chart.data.datasets[1].data.shift();
                }
                chart.update('none');
            }
        }
    }
    
    updateAllMetrics(data) {
        if (!data) return;
        
        if (data.total_predictions !== undefined) {
            document.getElementById('totalPredictions').textContent = 
                data.total_predictions.toLocaleString();
        }
        
        if (data.active_connections !== undefined) {
            document.getElementById('activeConnections').textContent = 
                data.active_connections;
        }
        
        if (data.avg_latency_ms !== undefined) {
            document.getElementById('avgLatency').textContent = 
                data.avg_latency_ms + 'ms';
        } else if (data.latency?.average_ms !== undefined) {
            document.getElementById('avgLatency').textContent = 
                data.latency.average_ms + 'ms';
        }
    }
    
    addLivePrediction(prediction) {
        const container = document.getElementById('live-predictions');
        if (!container) return;
        
        const item = document.createElement('div');
        item.className = 'flex items-center justify-between p-3 rounded-xl bg-white/5 animate-slide-in';
        item.innerHTML = `
            <div class="flex items-center gap-3">
                <span class="w-2 h-2 rounded-full ${this.getRiskColor(prediction.risk_tier)}"></span>
                <span class="font-mono text-sm">${prediction.loan_id}</span>
            </div>
            <span class="text-sm font-bold">${(prediction.migration_probability * 100).toFixed(1)}%</span>
        `;
        
        container.insertBefore(item, container.firstChild);
        
        // Limit to 10 items
        while (container.children.length > 10) {
            container.removeChild(container.lastChild);
        }
        
        // Increment total predictions dynamically
        const totalElement = document.getElementById('totalPredictions');
        if (totalElement) {
            const currentTotal = parseInt(totalElement.textContent.replace(/,/g, '')) || 0;
            this.animateValue('totalPredictions', currentTotal + 1);
        }
        
        // Bump the prediction rate chart dynamically
        if (this.charts.predictionRate) {
            const chart = this.charts.predictionRate;
            if (chart.data.labels.length > 0) {
                const lastIdx = chart.data.datasets[0].data.length - 1;
                chart.data.datasets[0].data[lastIdx]++;
                chart.update('none');
            }
        }
        
        // Update latency distribution chart dynamically
        if (this.charts.latencyDist && prediction.processing_time_ms !== undefined) {
            const latency = prediction.processing_time_ms;
            let index = 4; // >500ms
            if (latency < 50) index = 0;
            else if (latency < 100) index = 1;
            else if (latency < 250) index = 2;
            else if (latency < 500) index = 3;
            
            this.charts.latencyDist.data.datasets[0].data[index]++;
            this.charts.latencyDist.update('none');
        }
        
        // Update Risk Distribution dynamically
        if (this.charts.riskDist && prediction.risk_tier) {
            const riskMap = {
                'Very Low': 0,
                'Low': 1,
                'Medium': 2,
                'High': 3,
                'Very High': 4
            };
            const idx = riskMap[prediction.risk_tier];
            if (idx !== undefined) {
                this.charts.riskDist.data.datasets[0].data[idx]++;
                this.charts.riskDist.update('none');
            }
        }
    }
    
    getRiskColor(tier) {
        const colors = {
            'Very High': 'bg-red-400',
            'High': 'bg-orange-400',
            'Medium': 'bg-yellow-400',
            'Low': 'bg-green-400',
            'Very Low': 'bg-emerald-400'
        };
        return colors[tier] || 'bg-gray-400';
    }
    
    animateValue(elementId, newValue) {
        const element = document.getElementById(elementId);
        if (!element) return;
        
        const startValue = parseInt(element.textContent) || 0;
        const targetValue = typeof newValue === 'string' ? 
            parseInt(newValue) : newValue;
        const duration = 800;
        const startTime = performance.now();
        
        const animate = (currentTime) => {
            const elapsed = currentTime - startTime;
            const progress = Math.min(elapsed / duration, 1);
            const eased = 1 - Math.pow(1 - progress, 3);
            const current = Math.round(startValue + (targetValue - startValue) * eased);
            
            element.textContent = typeof newValue === 'string' && newValue.includes('ms') ?
                current + 'ms' : current.toLocaleString();
            
            if (progress < 1) {
                requestAnimationFrame(animate);
            }
        };
        
        requestAnimationFrame(animate);
    }
    
    async fetchInitialData() {
        try {
            const token = localStorage.getItem('access_token');
            const response = await fetch('/api/v1/monitoring/overview', {
                headers: { 'Authorization': `Bearer ${token}` }
            });
            
            if (response.ok) {
                const data = await response.json();
                this.updateAllMetrics(data);
                
                // Update charts with historical data
                if (data.prediction_rates && this.charts.predictionRate) {
                    const chart = this.charts.predictionRate;
                    chart.data.labels = data.prediction_rates.map(r => 
                        new Date(r.timestamp).toLocaleTimeString()
                    );
                    chart.data.datasets[0].data = data.prediction_rates.map(r => r.count);
                    chart.update();
                }
                
                if (data.latency_distribution && this.charts.latencyDist) {
                    // Reset to 0
                    const newLatData = [0, 0, 0, 0, 0];
                    data.latency_distribution.forEach(d => {
                        const r = d.range;
                        if (r === '0') newLatData[0] += d.count;
                        else if (r === '50') newLatData[1] += d.count;
                        else if (r === '100') newLatData[2] += d.count;
                        else if (r === '250') newLatData[3] += d.count;
                        else newLatData[4] += d.count; // 500 or >1000
                    });
                    this.charts.latencyDist.data.datasets[0].data = newLatData;
                    this.charts.latencyDist.update();
                }
            }
        } catch (error) {
            console.error('Failed to fetch monitoring data:', error);
        }
    }
    
    async loadSectionData(section) {
        try {
            const token = localStorage.getItem('access_token');
            const response = await fetch(`/api/v1/monitoring/${section}`, {
                headers: { 'Authorization': `Bearer ${token}` }
            });
            
            if (response.ok) {
                const data = await response.json();
                
                switch(section) {
                    case 'performance':
                        document.getElementById('aucScore').textContent = data.auc_roc?.toFixed(2) || '--';
                        document.getElementById('f1Score').textContent = data.f1_score?.toFixed(2) || '--';
                        document.getElementById('precision').textContent = data.precision?.toFixed(2) || '--';
                        break;
                    case 'risk':
                        if (this.charts.riskDist && data.risk_distribution) {
                            const newRiskData = [0, 0, 0, 0, 0];
                            const riskMap = {
                                'Very Low': 0, 'Low': 1, 'Medium': 2, 'High': 3, 'Very High': 4
                            };
                            data.risk_distribution.forEach(d => {
                                const idx = riskMap[d.tier];
                                if (idx !== undefined) {
                                    newRiskData[idx] += d.count;
                                }
                            });
                            this.charts.riskDist.data.datasets[0].data = newRiskData;
                            this.charts.riskDist.update();
                        }
                        break;
                }
            }
        } catch (error) {
            console.error(`Failed to load ${section} data:`, error);
        }
    }
    
    startAutoRefresh() {
        this.autoRefreshInterval = setInterval(() => {
            this.fetchInitialData();
        }, 10000); // Refresh every 10 seconds
    }
    
    setupEventListeners() {
        document.getElementById('autoRefresh')?.addEventListener('change', (e) => {
            if (e.target.checked) {
                this.startAutoRefresh();
            } else {
                clearInterval(this.autoRefreshInterval);
            }
        });
        
        document.getElementById('timeRange')?.addEventListener('change', (e) => {
            this.fetchInitialData();
        });
    }
    
    updateConnectionStatus(connected) {
        const badge = document.getElementById('ws-status-badge');
        if (badge) {
            badge.className = connected ? 
                'px-3 py-1 rounded-full text-xs bg-green-400/10 text-green-400' :
                'px-3 py-1 rounded-full text-xs bg-red-400/10 text-red-400';
            badge.innerHTML = connected ? 
                '<i class="fas fa-circle text-[6px] mr-1"></i> Connected' :
                '<i class="fas fa-circle text-[6px] mr-1"></i> Disconnected';
        }
    }
    
    showAlert(alert) {
        const container = document.getElementById('alert-container');
        if (!container) return;
        
        const alertEl = document.createElement('div');
        alertEl.className = `p-4 rounded-xl border-l-4 ${
            alert.severity === 'critical' ? 'border-red-400 bg-red-400/10' :
            alert.severity === 'warning' ? 'border-yellow-400 bg-yellow-400/10' :
            'border-cyan-400 bg-cyan-400/10'
        } mb-4`;
        alertEl.innerHTML = `
            <div class="flex items-center justify-between">
                <div>
                    <p class="font-semibold">${alert.message}</p>
                    <p class="text-sm text-gray-400">${new Date(alert.timestamp).toLocaleString()}</p>
                </div>
                <button onclick="this.parentElement.parentElement.remove()" class="text-gray-500 hover:text-white">
                    <i class="fas fa-times"></i>
                </button>
            </div>
        `;
        
        container.insertBefore(alertEl, container.firstChild);
    }
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    window.monitoring = new MonitoringDashboard();
});