// SICRSense Dashboard JavaScript
class DashboardManager {
    constructor() {
        this.ws = null;
        this.charts = {};
        this.metricsInterval = null;
        this.initialize();
    }
    
    initialize() {
        this.setupWebSocket();
        this.setupEventListeners();
        this.initializeCharts();
        this.fetchInitialData();
        this.loadRecentPredictions();
        this.startMetricsPolling();
    }
    
    setupWebSocket() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws`;
        const token = getAuthToken();
        
        this.ws = new WebSocket(`${wsUrl}?token=${token}`);
        
        this.ws.onopen = () => {
            console.log('WebSocket connected');
            this.updateConnectionStatus(true);
            this.ws.send(JSON.stringify({ type: 'subscribe_predictions' }));
            this.ws.send(JSON.stringify({ type: 'subscribe_metrics' }));
        };
        
        this.ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            this.handleWebSocketMessage(data);
        };
        
        this.ws.onclose = () => {
            console.log('WebSocket disconnected');
            this.updateConnectionStatus(false);
            setTimeout(() => this.setupWebSocket(), 3000);
        };
        
        this.ws.onerror = (error) => {
            console.error('WebSocket error:', error);
            this.updateConnectionStatus(false);
        };
    }
    
    handleWebSocketMessage(data) {
        switch(data.type) {
            case 'prediction_update':
                this.updatePredictionDisplay(data.data);
                break;
            case 'metrics_update':
                this.updateMetrics(data.data);
                break;
            case 'system_alert':
                this.showAlert(data);
                break;
        }
    }
    
    setupEventListeners() {
        // Form submission
        document.getElementById('inference-form')?.addEventListener('submit', (e) => {
            e.preventDefault();
            this.submitPrediction();
        });
        
        // Random data button
        document.getElementById('randomize-btn')?.addEventListener('click', () => {
            this.fillRandomData();
        });
        window.fillRandomData = () => this.fillRandomData();
        
        // Batch upload
        document.getElementById('batch-upload')?.addEventListener('change', (e) => {
            this.handleBatchUpload(e.target.files[0]);
        });
    }
    
    async submitPrediction() {
        const formData = this.getFormData();
        const token = getAuthToken();
        
        try {
            this.showResultState('loading');
            this.showLoading(true);
            console.log('[Dashboard] Submitting prediction:', formData);
            
            const response = await fetch('/api/v1/predict', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify(formData)
            });
            
            console.log('[Dashboard] Response status:', response.status);
            
            if (response.ok) {
                const result = await response.json();
                console.log('[Dashboard] API response:', result);
                
                // Try different response formats
                let prediction = result?.data?.predictions?.[0] || result?.data || result;
                
                if (!prediction || typeof prediction !== 'object') {
                    throw new Error('Invalid prediction response format');
                }
                
                console.log('[Dashboard] Extracted prediction:', prediction);
                this.updatePredictionDisplay(prediction);
                this.showResultState('result');
                this.showToast('Prediction completed successfully', 'success');
            } else {
                const errorText = await response.text();
                console.error('[Dashboard] API error response:', errorText);
                try {
                    const error = JSON.parse(errorText);
                    this.showToast(error.detail || 'Prediction failed', 'error');
                } catch {
                    this.showToast(`Prediction failed: ${response.status}`, 'error');
                }
                this.showResultState('waiting');
            }
        } catch (error) {
            console.error('[Dashboard] Prediction error:', error);
            this.showToast(`Error: ${error.message}`, 'error');
            this.showResultState('waiting');
        } finally {
            this.showLoading(false);
        }
    }
    
    getFormData() {
        return {
            loan_id: document.getElementById('loan_id')?.value || `LN-${Date.now()}`,
            loan_amount_gbp: parseFloat(document.getElementById('loan_amount_gbp')?.value || 250000),
            outstanding_balance_gbp: parseFloat(document.getElementById('outstanding_balance_gbp')?.value || 240000),
            original_loan_term_months: parseFloat(document.getElementById('original_loan_term_months')?.value || 360),
            remaining_term_months: parseFloat(document.getElementById('remaining_term_months')?.value || 340),
            interest_rate_pct: parseFloat(document.getElementById('interest_rate_pct')?.value || 5.2),
            vintage_year: parseFloat(document.getElementById('vintage_year')?.value || 2024),
            internal_credit_score: parseFloat(document.getElementById('internal_credit_score')?.value || 680),
            credit_score_change_last_quarter: parseFloat(document.getElementById('credit_score_change_last_quarter')?.value || -15),
            bureau_inquiries_last_6m: parseFloat(document.getElementById('bureau_inquiries_last_6m')?.value || 2),
            days_past_due_current: parseFloat(document.getElementById('days_past_due_current')?.value || 0),
            missed_payments_last_12m: parseFloat(document.getElementById('missed_payments_last_12m')?.value || 0),
            months_on_book: parseFloat(document.getElementById('months_on_book')?.value || 20),
            pd_12m_at_origination_pct: parseFloat(document.getElementById('pd_12m_at_origination_pct')?.value || 1.20),
            pd_12m_current_pct: parseFloat(document.getElementById('pd_12m_current_pct')?.value || 1.85),
            pd_relative_change_pct: parseFloat(document.getElementById('pd_relative_change_pct')?.value || 54.2)
        };
    }
    
    updatePredictionDisplay(prediction) {
        if (!prediction) {
            console.error('[Dashboard] No prediction data');
            return;
        }
        
        const probPercent = Math.round((prediction.migration_probability ?? 0) * 100);
        console.log('[Dashboard] Updating display with probability:', probPercent + '%');
        
        // Update probability ring
        const ring = document.getElementById('probability-ring');
        if (ring) {
            const circumference = 2 * Math.PI * 88;
            const offset = circumference - (probPercent / 100) * circumference;
            ring.style.strokeDasharray = `${circumference} ${circumference}`;
            ring.style.strokeDashoffset = offset;
        }
        
        // Update values with safe access
        this.animateValue('res-prob', probPercent + '%');
        
        const tierEl = document.getElementById('res-tier');
        if (tierEl) tierEl.textContent = prediction.risk_tier || 'Unknown';
        
        const actionEl = document.getElementById('res-action');
        if (actionEl) actionEl.textContent = prediction.recommended_action || 'N/A';
        
        // Update stage text
        const stageEl = document.getElementById('res-stage');
        if (stageEl) {
            if (prediction.predicted_migration === 1) {
                stageEl.textContent = 'Stage 2 (SICR)';
            } else {
                stageEl.textContent = 'Stage 1 (Performing)';
            }
        }

        const latencyElement = document.getElementById('res-latency');
        if (latencyElement) {
            latencyElement.textContent = `${prediction.processing_time_ms ?? prediction.latency ?? '--'}ms`;
        }
        
        // Add to history table
        this.addToHistoryTable(prediction);
        
        console.log('[Dashboard] Display updated successfully');
    }
    
    showResultState(state = 'result') {
        const states = ['state-waiting', 'state-loading', 'state-result'];
        states.forEach((id) => {
            const el = document.getElementById(id);
            if (!el) return;
            el.classList.toggle('hidden', id !== `state-${state}`);
        });
    }
    
    addToHistoryTable(prediction) {
        const tbody = document.getElementById('history-table-body');
        if (!tbody) {
            console.warn('[Dashboard] history-table-body element not found');
            return;
        }
        
        // Remove the "No predictions yet" message if present
        if (tbody.children.length === 1 && tbody.children[0].cells?.length === 1) {
            tbody.innerHTML = '';
        }
        
        const row = document.createElement('tr');
        row.className = 'border-b border-gray-700/50 hover:bg-white/5';
        
        const prob = (prediction.migration_probability ?? 0) * 100;
        const timestamp = prediction.timestamp ? new Date(prediction.timestamp).toLocaleString() : new Date().toLocaleString();
        
        row.innerHTML = `
            <td class="py-3 px-4 font-mono text-sm">${prediction.loan_id || 'N/A'}</td>
            <td class="py-3 px-4">
                <span class="px-2 py-1 rounded-full text-xs ${this.getRiskColor(prediction.risk_tier)}">
                    ${prediction.risk_tier || 'Unknown'}
                </span>
            </td>
            <td class="py-3 px-4 font-bold">${prob.toFixed(1)}%</td>
            <td class="py-3 px-4">${prediction.predicted_migration === 1 ? 'SICR' : 'Performing'}</td>
            <td class="py-3 px-4 text-gray-400">${prediction.processing_time_ms ?? '--'}ms</td>
            <td class="py-3 px-4 text-gray-500 text-sm">${timestamp}</td>
        `;
        
        tbody.insertBefore(row, tbody.firstChild);
        
        // Keep only last 50 rows
        while (tbody.children.length > 50) {
            tbody.removeChild(tbody.lastChild);
        }
    }
    
    getRiskColor(tier) {
        const colors = {
            'Very High': 'bg-red-400/10 text-red-400 border border-red-400/30',
            'High': 'bg-orange-400/10 text-orange-400 border border-orange-400/30',
            'Medium': 'bg-yellow-400/10 text-yellow-400 border border-yellow-400/30',
            'Low': 'bg-green-400/10 text-green-400 border border-green-400/30',
            'Very Low': 'bg-emerald-400/10 text-emerald-400 border border-emerald-400/30'
        };
        return colors[tier] || 'bg-gray-400/10 text-gray-400 border border-gray-400/30';
    }
    
    fillRandomData() {
        const isHighRisk = Math.random() > 0.5;
        
        const fields = {
            loan_id: `LN-${Math.random().toString(36).substr(2, 9).toUpperCase()}`,
            loan_amount_gbp: Math.floor(Math.random() * 400000 + 120000),
            outstanding_balance_gbp: Math.floor(Math.random() * 380000 + 60000),
            internal_credit_score: isHighRisk ? Math.floor(Math.random() * 200 + 400) : Math.floor(Math.random() * 200 + 700),
            credit_score_change_last_quarter: isHighRisk ? -Math.floor(Math.random() * 60 + 15) : Math.floor(Math.random() * 25),
            days_past_due_current: isHighRisk ? Math.floor(Math.random() * 55) : 0,
            missed_payments_last_12m: isHighRisk ? Math.floor(Math.random() * 5) : 0,
            pd_relative_change_pct: isHighRisk ? Math.floor(Math.random() * 100 + 50) : Math.floor(Math.random() * 50)
        };
        
        Object.entries(fields).forEach(([id, value]) => {
            const element = document.getElementById(id);
            if (element) element.value = value;
        });
        
        this.showToast('Randomized parameters successfully', 'info');
    }
    
    initializeCharts() {
        // Prediction history chart
        const ctx = document.getElementById('predictionsChart');
        if (ctx) {
            this.charts.predictions = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: [],
                    datasets: [{
                        label: 'Predictions',
                        data: [],
                        borderColor: '#00f0ff',
                        tension: 0.4,
                        fill: true,
                        backgroundColor: 'rgba(0, 240, 255, 0.1)'
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { legend: { display: false } },
                    scales: {
                        y: { beginAtZero: true }
                    }
                }
            });
        }
    }
    
    updateMetrics(metrics) {
        document.getElementById('total-predictions').textContent = metrics.total_predictions?.toLocaleString() || '0';
        document.getElementById('active-connections').textContent = metrics.active_connections || '0';
        document.getElementById('avg-latency').textContent = metrics.avg_latency_ms + 'ms';
    }
    
    updateConnectionStatus(connected) {
        const badge = document.getElementById('ws-status');
        if (badge) {
            badge.className = connected ? 
                'px-3 py-1 rounded-full text-xs bg-green-400/10 text-green-400 border border-green-400/30' :
                'px-3 py-1 rounded-full text-xs bg-red-400/10 text-red-400 border border-red-400/30';
            badge.innerHTML = connected ? 
                '<i class="fas fa-circle text-[6px] mr-1"></i> Connected' :
                '<i class="fas fa-circle text-[6px] mr-1"></i> Disconnected';
        }
    }
    
    animateValue(elementId, newValue) {
        const element = document.getElementById(elementId);
        if (!element) return;

        const duration = 1000;
        const startTime = performance.now();
        const startValue = parseFloat(element.textContent) || 0;
        const normalizedValue = typeof newValue === 'number'
            ? newValue
            : parseFloat(String(newValue).replace(/[^0-9.]/g, '')) || 0;
        const targetValue = normalizedValue;
        const suffix = typeof newValue === 'string'
            ? (newValue.includes('%') ? '%' : newValue.includes('ms') ? 'ms' : '')
            : '';

        function update(currentTime) {
            const elapsed = currentTime - startTime;
            const progress = Math.min(elapsed / duration, 1);
            const eased = 1 - Math.pow(1 - progress, 3);
            const current = startValue + (targetValue - startValue) * eased;

            element.textContent = suffix ? `${Math.round(current)}${suffix}` : Math.round(current).toLocaleString();

            if (progress < 1) {
                requestAnimationFrame(update);
            }
        }

        requestAnimationFrame(update);
    }
    
    showLoading(show) {
        const loader = document.getElementById('loading-overlay');
        if (loader) {
            loader.style.display = show ? 'flex' : 'none';
        }
    }
    
    showToast(message, type = 'info') {
        const container = document.getElementById('toast-container');
        if (!container) return;
        
        const toast = document.createElement('div');
        const colors = {
            success: 'border-green-400 bg-green-400/10',
            error: 'border-red-400 bg-red-400/10',
            info: 'border-cyan-400 bg-cyan-400/10',
            warning: 'border-yellow-400 bg-yellow-400/10'
        };
        
        toast.className = `p-4 rounded-xl border ${colors[type]} backdrop-blur-md transform translate-x-full transition-transform duration-300`;
        toast.innerHTML = `
            <div class="flex items-center gap-3">
                <i class="fas fa-${type === 'success' ? 'check-circle' : type === 'error' ? 'exclamation-circle' : 'info-circle'} text-${type === 'success' ? 'green' : type === 'error' ? 'red' : 'cyan'}-400"></i>
                <span>${message}</span>
            </div>
        `;
        
        container.appendChild(toast);
        
        setTimeout(() => toast.style.transform = 'translateX(0)', 100);
        setTimeout(() => {
            toast.style.transform = 'translateX(100%)';
            setTimeout(() => toast.remove(), 300);
        }, 3000);
    }
    
    showAlert(alert) {
        // Show system alert
        this.showToast(alert.message, alert.severity || 'warning');
    }
    
    async handleBatchUpload(file) {
        if (!file) return;
        
        try {
            const text = await file.text();
            const data = JSON.parse(text);
            
            const token = getAuthToken();
            const response = await fetch('/api/v1/predict/batch', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify(data)
            });
            
            if (response.ok) {
                const result = await response.json();
                this.showToast(`Batch processed: ${result.batch_size} predictions`, 'success');
            }
        } catch (error) {
            this.showToast('Failed to process batch file', 'error');
        }
    }
    
    async fetchInitialData() {
        try {
            const token = getAuthToken();
            const response = await fetch('/api/v1/stats', {
                headers: { 'Authorization': `Bearer ${token}` }
            });
            
            if (response.ok) {
                const data = await response.json();
                this.updateMetrics(data);
            }
        } catch (error) {
            console.error('Failed to fetch initial data:', error);
        }
    }

    async loadRecentPredictions(limit = 5) {
        const token = getAuthToken();
        const tbody = document.getElementById('history-table-body');
        if (!tbody) return;

        try {
            const response = await fetch(`/api/v1/predictions/history?limit=${limit}`, {
                headers: { 'Authorization': `Bearer ${token}` }
            });

            if (!response.ok) {
                return;
            }

            const result = await response.json();
            const predictions = result.predictions || [];

            if (!predictions.length) {
                tbody.innerHTML = '<tr><td colspan="6" class="text-center text-gray-500 py-6">No recent predictions available.</td></tr>';
                return;
            }

            tbody.innerHTML = predictions.map(prediction => {
                const prob = (prediction.migration_probability ?? 0) * 100;
                const stage = prediction.predicted_migration ? 'Stage 2' : 'Stage 1';
                const when = prediction.timestamp ? new Date(prediction.timestamp).toLocaleString() : '—';
                return `
                    <tr class="border-b border-gray-700/50 hover:bg-white/5">
                        <td class="py-3 px-4 font-mono text-sm">${prediction.loan_id || '—'}</td>
                        <td class="py-3 px-4">${prediction.risk_tier || 'Unknown'}</td>
                        <td class="py-3 px-4 font-bold">${prob.toFixed(1)}%</td>
                        <td class="py-3 px-4">${stage}</td>
                        <td class="py-3 px-4 text-gray-400">${prediction.processing_time_ms ?? '--'}ms</td>
                        <td class="py-3 px-4 text-gray-500 text-sm">${when}</td>
                    </tr>`;
            }).join('');
        } catch (error) {
            console.error('Failed to load recent predictions:', error);
        }
    }
    
    startMetricsPolling() {
        this.metricsInterval = setInterval(() => {
            this.fetchInitialData();
        }, 30000); // Poll every 30 seconds as backup
    }
}

// Initialize dashboard
document.addEventListener('DOMContentLoaded', () => {
    window.dashboard = new DashboardManager();
});