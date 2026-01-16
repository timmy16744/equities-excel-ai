/**
 * Equities AI - Excel Interface
 * Main Application Controller
 */

class EquitiesExcelApp {
    constructor() {
        this.spreadsheet = new SpreadsheetEngine();
        this.isAnalyzing = false;
        this.refreshTimer = null;
        this.refreshInterval = 30000; // 30 seconds
        this.charts = {};
    }

    // Initialize the application
    async init() {
        console.log('Initializing Equities AI Excel...');

        // Initialize spreadsheet
        this.spreadsheet.init();

        // Setup event listeners
        this.setupEventListeners();

        // Connect WebSocket
        this.setupWebSocket();

        // Load initial data
        await this.loadInitialData();

        // Start auto-refresh
        this.startAutoRefresh();

        // Set default view
        this.switchView('dashboard');

        console.log('Equities AI Excel initialized');
    }

    // Setup all event listeners
    setupEventListeners() {
        // Menu bar navigation
        document.querySelectorAll('.menu-bar div[data-view]').forEach(item => {
            item.addEventListener('click', () => {
                this.switchView(item.dataset.view);
            });
        });

        // Sheet tabs
        document.querySelectorAll('.sheet-tab').forEach(tab => {
            tab.addEventListener('click', () => {
                const sheet = tab.dataset.sheet;
                this.switchSheet(sheet);
            });
        });

        // Action buttons
        document.getElementById('btn-analyze')?.addEventListener('click', () => this.triggerAnalysis());
        document.getElementById('btn-refresh')?.addEventListener('click', () => this.refreshData());
        document.getElementById('btn-export')?.addEventListener('click', () => this.exportReport());

        // Filter controls
        document.getElementById('agent-filter')?.addEventListener('change', (e) => this.filterByAgent(e.target.value));
        document.getElementById('timeframe-filter')?.addEventListener('change', (e) => this.filterByTimeframe(e.target.value));

        // Outlook filter buttons
        document.getElementById('btn-bullish')?.addEventListener('click', () => this.filterByOutlook('bullish'));
        document.getElementById('btn-neutral')?.addEventListener('click', () => this.filterByOutlook('neutral'));
        document.getElementById('btn-bearish')?.addEventListener('click', () => this.filterByOutlook('bearish'));

        // Display options
        document.getElementById('btn-grid-lines')?.addEventListener('click', () => this.toggleGridLines());
        document.getElementById('btn-theme')?.addEventListener('click', () => this.toggleTheme());
        document.getElementById('btn-wrap')?.addEventListener('click', () => this.toggleAutoRefresh());
        document.getElementById('btn-merge')?.addEventListener('click', () => this.consolidateView());

        // Sort buttons
        document.getElementById('btn-sort-asc')?.addEventListener('click', () => this.sortData('asc'));
        document.getElementById('btn-sort-desc')?.addEventListener('click', () => this.sortData('desc'));
        document.getElementById('btn-sort-default')?.addEventListener('click', () => this.sortData('default'));

        // Zoom controls
        document.getElementById('btn-zoom-in')?.addEventListener('click', () => this.adjustZoom(1));
        document.getElementById('btn-zoom-out')?.addEventListener('click', () => this.adjustZoom(-1));

        // Number format
        document.getElementById('number-format')?.addEventListener('change', (e) => {
            this.spreadsheet.setNumberFormat(e.target.value);
        });

        document.getElementById('btn-decimal-inc')?.addEventListener('click', () => this.spreadsheet.adjustDecimals(1));
        document.getElementById('btn-decimal-dec')?.addEventListener('click', () => this.spreadsheet.adjustDecimals(-1));

        // View buttons
        document.getElementById('btn-conditional')?.addEventListener('click', () => this.switchView('risk'));
        document.getElementById('btn-format-table')?.addEventListener('click', () => this.switchView('portfolio'));
        document.getElementById('btn-cell-style')?.addEventListener('click', () => this.switchView('agents'));

        // Position management
        document.getElementById('btn-add-position')?.addEventListener('click', () => this.showAddPositionModal());
        document.getElementById('btn-remove-position')?.addEventListener('click', () => this.showRemovePositionModal());
        document.getElementById('btn-edit-position')?.addEventListener('click', () => this.showEditPositionModal());

        // Modal controls
        document.getElementById('modal-close')?.addEventListener('click', () => this.hideModal());
        document.getElementById('modal-cancel')?.addEventListener('click', () => this.hideModal());

        // Keyboard shortcuts
        document.addEventListener('keydown', (e) => this.handleKeyboard(e));
    }

    // Setup WebSocket connection
    setupWebSocket() {
        ws.connect('updates');
        ws.connect('settings');

        // Handle real-time updates
        ws.on('agent_update', (data) => {
            this.handleAgentUpdate(data);
        });

        ws.on('insight_update', (data) => {
            this.handleInsightUpdate(data);
        });

        ws.on('order_executed', (data) => {
            this.handleOrderExecuted(data);
        });

        ws.on('settings_changed', (data) => {
            this.handleSettingsChanged(data);
        });

        ws.on('workflow_status', (data) => {
            this.updateWorkflowStatus(data);
        });

        ws.on('risk_alert', (data) => {
            this.handleRiskAlert(data);
        });

        ws.on('connected', () => {
            this.showToast('Connected to server', 'success');
        });

        ws.on('disconnected', () => {
            this.showToast('Disconnected from server', 'error');
        });
    }

    // Load initial data from API
    async loadInitialData() {
        this.updateWorkflowStatus({ status: 'Loading...' });

        try {
            // Check backend health
            const isHealthy = await api.healthCheck();
            if (!isHealthy) {
                this.showToast('Backend server not available', 'warning');
                this.loadDemoData();
                return;
            }

            // Load all data in parallel
            const [agents, insight, portfolio, positions, signals, settings, performance, weights, risk, orders] = await Promise.all([
                api.getAllAgentsStatus(),
                api.getLatestInsight(),
                api.getPortfolio(),
                api.getPositions(),
                api.getTradeSignals(),
                api.getSettings(),
                api.getPerformanceMetrics(),
                api.getAgentWeights(),
                api.getRiskMetrics(),
                api.getExecutionOrders()
            ]);

            // Update spreadsheet data
            this.spreadsheet.updateData({
                agents: agents || {},
                insight: insight,
                portfolio: portfolio,
                positions: positions || [],
                signals: signals || [],
                settings: settings || {},
                performance: performance,
                weights: weights || {},
                risk: risk,
                executionOrders: orders || []
            });

            this.updateWorkflowStatus({ status: 'Ready' });
            this.showToast('Data loaded successfully', 'success');

        } catch (error) {
            console.error('Failed to load data:', error);
            this.showToast('Failed to load data, using demo mode', 'warning');
            this.loadDemoData();
        }
    }

    // Load demo data when backend is unavailable
    loadDemoData() {
        const demoAgents = {
            macro: { outlook: 'Bullish', confidence: 72, status: 'idle', updated_at: new Date().toISOString(), timeframe: '1 week', key_factors: ['Fed policy dovish'], uncertainties: ['Inflation data'] },
            geopolitical: { outlook: 'Neutral', confidence: 58, status: 'idle', updated_at: new Date().toISOString(), timeframe: '1 month', key_factors: ['Trade tensions stable'], uncertainties: ['Election risk'] },
            commodities: { outlook: 'Bearish', confidence: 65, status: 'idle', updated_at: new Date().toISOString(), timeframe: '2 weeks', key_factors: ['Oil supply increase'], uncertainties: ['OPEC decisions'] },
            sentiment: { outlook: 'Bullish', confidence: 78, status: 'idle', updated_at: new Date().toISOString(), timeframe: '1 week', key_factors: ['Positive earnings sentiment'], uncertainties: ['Retail participation'] },
            fundamentals: { outlook: 'Bullish', confidence: 70, status: 'idle', updated_at: new Date().toISOString(), timeframe: '3 months', key_factors: ['Strong earnings growth'], uncertainties: ['Valuation stretched'] },
            technical: { outlook: 'Bullish', confidence: 82, status: 'idle', updated_at: new Date().toISOString(), timeframe: '1 week', key_factors: ['Breakout confirmed'], uncertainties: ['Overbought RSI'] },
            alternative: { outlook: 'Neutral', confidence: 55, status: 'idle', updated_at: new Date().toISOString(), timeframe: '2 weeks', key_factors: ['Mixed signals'], uncertainties: ['Data quality'] },
            cross_asset: { outlook: 'Bullish', confidence: 68, status: 'idle', updated_at: new Date().toISOString(), timeframe: '1 month', key_factors: ['Risk-on rotation'], uncertainties: ['Bond yields'] },
            event: { outlook: 'Neutral', confidence: 60, status: 'idle', updated_at: new Date().toISOString(), timeframe: '1 week', key_factors: ['FOMC meeting ahead'], uncertainties: ['CPI release'] },
            risk: { outlook: 'Neutral', confidence: 75, status: 'idle', updated_at: new Date().toISOString(), timeframe: '1 week', key_factors: ['Risk within limits'], uncertainties: ['Tail risk events'] },
            aggregation: { outlook: 'Bullish', confidence: 71, status: 'idle', updated_at: new Date().toISOString(), timeframe: '1 week', key_factors: ['Consensus bullish'], uncertainties: ['Agent disagreement'] },
            learning: { outlook: 'Neutral', confidence: 65, status: 'idle', updated_at: new Date().toISOString(), timeframe: 'Ongoing', key_factors: ['Weights updated'], uncertainties: ['Small sample size'] }
        };

        const demoInsight = {
            overall_outlook: 'Bullish',
            confidence: 71,
            risk_level: 'moderate',
            vetoed: false,
            final_recommendations: ['Maintain equity exposure', 'Hedge tail risk'],
            conflicts: ['Commodities vs Technical on energy sector']
        };

        const demoPortfolio = {
            total_value: 1250000,
            invested: 1050000,
            cash: 200000,
            pnl: 75000,
            pnl_percent: 6.38,
            sharpe_ratio: 1.45
        };

        const demoPositions = [
            { symbol: 'AAPL', name: 'Apple Inc.', sector: 'Technology', shares: 500, avg_cost: 175.50, current_price: 182.30, weight: 8.5 },
            { symbol: 'MSFT', name: 'Microsoft Corp.', sector: 'Technology', shares: 300, avg_cost: 380.00, current_price: 395.20, weight: 11.2 },
            { symbol: 'GOOGL', name: 'Alphabet Inc.', sector: 'Technology', shares: 200, avg_cost: 140.00, current_price: 152.50, weight: 2.9 },
            { symbol: 'AMZN', name: 'Amazon.com Inc.', sector: 'Consumer', shares: 150, avg_cost: 175.00, current_price: 185.40, weight: 2.6 },
            { symbol: 'NVDA', name: 'NVIDIA Corp.', sector: 'Technology', shares: 100, avg_cost: 450.00, current_price: 520.00, weight: 4.9 },
            { symbol: 'JPM', name: 'JPMorgan Chase', sector: 'Financial', shares: 400, avg_cost: 185.00, current_price: 192.50, weight: 7.3 },
            { symbol: 'V', name: 'Visa Inc.', sector: 'Financial', shares: 250, avg_cost: 275.00, current_price: 285.00, weight: 6.7 },
            { symbol: 'UNH', name: 'UnitedHealth', sector: 'Healthcare', shares: 100, avg_cost: 520.00, current_price: 545.00, weight: 5.2 }
        ];

        const demoSignals = [
            { symbol: 'AAPL', action: 'hold', strength: 'moderate', confidence: 72, target_price: 195.00, stop_loss: 170.00, take_profit: 210.00, source_agent: 'aggregation', status: 'active', created_at: new Date().toISOString() },
            { symbol: 'TSLA', action: 'buy', strength: 'strong', confidence: 78, target_price: 280.00, stop_loss: 220.00, take_profit: 320.00, source_agent: 'technical', status: 'pending', created_at: new Date().toISOString() },
            { symbol: 'XOM', action: 'sell', strength: 'moderate', confidence: 65, target_price: 95.00, stop_loss: 115.00, take_profit: null, source_agent: 'commodities', status: 'active', created_at: new Date().toISOString() }
        ];

        const demoWeights = {
            macro: 0.12, geopolitical: 0.08, commodities: 0.08, sentiment: 0.10,
            fundamentals: 0.15, technical: 0.12, alternative: 0.08, cross_asset: 0.10,
            event: 0.07, risk: 0.10, aggregation: 0, learning: 0
        };

        const demoRisk = {
            portfolio_risk: 45,
            max_drawdown: 8.5,
            leverage: 1.0,
            concentration: 35,
            var_95: '$25,000',
            beta: 1.12,
            vetoed: false,
            veto_reason: null
        };

        const demoPerformance = {
            overall_accuracy: 67,
            total_predictions: 450,
            correct_predictions: 302,
            best_agent: 'Technical',
            by_agent: {
                macro: { total: 45, correct: 28, accuracy: 62, brier_score: 0.18, trend: 'up' },
                geopolitical: { total: 38, correct: 22, accuracy: 58, brier_score: 0.22, trend: 'stable' },
                commodities: { total: 42, correct: 27, accuracy: 64, brier_score: 0.19, trend: 'up' },
                sentiment: { total: 50, correct: 35, accuracy: 70, brier_score: 0.15, trend: 'up' },
                fundamentals: { total: 40, correct: 28, accuracy: 70, brier_score: 0.16, trend: 'stable' },
                technical: { total: 55, correct: 42, accuracy: 76, brier_score: 0.12, trend: 'up' },
                alternative: { total: 35, correct: 19, accuracy: 54, brier_score: 0.24, trend: 'down' },
                cross_asset: { total: 48, correct: 31, accuracy: 65, brier_score: 0.18, trend: 'stable' },
                event: { total: 30, correct: 18, accuracy: 60, brier_score: 0.21, trend: 'stable' },
                risk: { total: 40, correct: 32, accuracy: 80, brier_score: 0.10, trend: 'up' }
            }
        };

        const demoSettings = {
            api_config: {
                anthropic_api_key: { value: '********', is_sensitive: true, type: 'string', description: 'Claude API key' },
                alpha_vantage_api_key: { value: '********', is_sensitive: true, type: 'string', description: 'Market data API' }
            },
            agent_config: {
                macro_enabled: { value: true, is_sensitive: false, type: 'boolean', description: 'Enable macro agent' },
                technical_model: { value: 'claude-sonnet-4-20250514', is_sensitive: false, type: 'string', description: 'Model for technical agent' }
            },
            risk_management: {
                max_drawdown: { value: 15, is_sensitive: false, type: 'float', description: 'Maximum drawdown %' },
                max_position_size: { value: 10, is_sensitive: false, type: 'float', description: 'Max position size %' }
            },
            ui_preferences: {
                theme: { value: 'light', is_sensitive: false, type: 'string', description: 'UI theme' },
                refresh_interval: { value: 30, is_sensitive: false, type: 'integer', description: 'Auto-refresh seconds' }
            }
        };

        this.spreadsheet.updateData({
            agents: demoAgents,
            insight: demoInsight,
            portfolio: demoPortfolio,
            positions: demoPositions,
            signals: demoSignals,
            settings: demoSettings,
            performance: demoPerformance,
            weights: demoWeights,
            risk: demoRisk,
            executionOrders: [],
            riskAlerts: [],
            marketRegime: 'Bull Market'
        });

        this.updateWorkflowStatus({ status: 'Demo Mode' });
    }

    // Refresh data from API
    async refreshData() {
        try {
            await this.loadInitialData();
        } catch (error) {
            console.error('Refresh failed:', error);
            this.showToast('Failed to refresh data', 'error');
        }
    }

    // Trigger full analysis
    async triggerAnalysis() {
        if (this.isAnalyzing) {
            this.showToast('Analysis already in progress', 'warning');
            return;
        }

        this.isAnalyzing = true;
        this.updateWorkflowStatus({ status: 'Analyzing...' });

        try {
            const result = await api.triggerAnalysis();
            this.showToast('Analysis started', 'success');

            // The WebSocket will provide updates as agents complete
        } catch (error) {
            console.error('Analysis failed:', error);
            this.showToast('Failed to start analysis', 'error');
            this.updateWorkflowStatus({ status: 'Error' });
        } finally {
            this.isAnalyzing = false;
        }
    }

    // Export report
    exportReport() {
        const csv = this.spreadsheet.exportToCSV();
        const blob = new Blob([csv], { type: 'text/csv' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `equities-ai-${this.spreadsheet.currentView}-${new Date().toISOString().split('T')[0]}.csv`;
        a.click();
        URL.revokeObjectURL(url);
        this.showToast('Report exported', 'success');
    }

    // Switch view
    switchView(view) {
        this.spreadsheet.switchView(view);

        // Update menu bar
        document.querySelectorAll('.menu-bar div[data-view]').forEach(item => {
            item.classList.remove('active');
            if (item.dataset.view === view) {
                item.classList.add('active');
            }
        });
    }

    // Switch sheet tab
    switchSheet(sheet) {
        document.querySelectorAll('.sheet-tab').forEach(tab => {
            tab.classList.remove('active');
            if (tab.dataset.sheet === sheet) {
                tab.classList.add('active');
            }
        });

        // Map sheet to view
        const viewMap = {
            'main': 'dashboard',
            'agents': 'agents',
            'positions': 'portfolio',
            'history': 'performance',
            'config': 'settings'
        };

        this.switchView(viewMap[sheet] || 'dashboard');
    }

    // Handle agent update from WebSocket
    handleAgentUpdate(data) {
        const { agent_id, output } = data;
        if (this.spreadsheet.data.agents) {
            this.spreadsheet.data.agents[agent_id] = {
                ...this.spreadsheet.data.agents[agent_id],
                ...output,
                updated_at: new Date().toISOString()
            };
            this.spreadsheet.refreshView();
        }
        this.showToast(`${agent_id} agent updated`, 'info');
    }

    // Handle insight update from WebSocket
    handleInsightUpdate(data) {
        this.spreadsheet.data.insight = data;
        this.spreadsheet.refreshView();
        this.showToast('Aggregated insight updated', 'info');
    }

    // Handle order executed from WebSocket
    handleOrderExecuted(data) {
        this.showToast(`Order executed: ${data.symbol} ${data.action}`, 'success');
        this.refreshData();
    }

    // Handle settings changed from WebSocket
    handleSettingsChanged(data) {
        const { category, key, value } = data;
        if (this.spreadsheet.data.settings[category]) {
            this.spreadsheet.data.settings[category][key] = {
                ...this.spreadsheet.data.settings[category][key],
                value
            };
        }
        if (this.spreadsheet.currentView === 'settings') {
            this.spreadsheet.refreshView();
        }
    }

    // Handle risk alert from WebSocket
    handleRiskAlert(data) {
        this.spreadsheet.data.riskAlerts = this.spreadsheet.data.riskAlerts || [];
        this.spreadsheet.data.riskAlerts.unshift(data);
        this.showToast(`Risk Alert: ${data.message}`, 'warning');

        if (this.spreadsheet.currentView === 'risk') {
            this.spreadsheet.refreshView();
        }
    }

    // Update workflow status
    updateWorkflowStatus(data) {
        const statusEl = document.getElementById('workflow-status');
        if (statusEl) {
            statusEl.textContent = `Workflow: ${data.status}`;
        }
    }

    // Filter by agent
    filterByAgent(agentId) {
        // Filter implementation
        console.log('Filter by agent:', agentId);
    }

    // Filter by timeframe
    filterByTimeframe(timeframe) {
        // Filter implementation
        console.log('Filter by timeframe:', timeframe);
    }

    // Filter by outlook
    filterByOutlook(outlook) {
        // Highlight cells with matching outlook
        Object.values(this.spreadsheet.cells).forEach(cell => {
            if (cell.dataset.type === outlook) {
                cell.style.outline = '2px solid var(--green)';
            } else {
                cell.style.outline = '';
            }
        });
    }

    // Toggle grid lines
    toggleGridLines() {
        const cells = document.querySelector('.cells');
        cells.style.gridGap = cells.style.gridGap === '0px' ? '1px' : '0px';
    }

    // Toggle theme
    toggleTheme() {
        document.body.classList.toggle('dark-theme');
    }

    // Toggle auto-refresh
    toggleAutoRefresh() {
        const enabled = this.spreadsheet.toggleAutoRefresh();
        if (enabled) {
            this.startAutoRefresh();
            this.showToast('Auto-refresh enabled', 'info');
        } else {
            this.stopAutoRefresh();
            this.showToast('Auto-refresh disabled', 'info');
        }
    }

    // Start auto-refresh
    startAutoRefresh() {
        if (this.refreshTimer) return;
        this.refreshTimer = setInterval(() => {
            if (this.spreadsheet.autoRefresh) {
                this.refreshData();
            }
        }, this.refreshInterval);
    }

    // Stop auto-refresh
    stopAutoRefresh() {
        if (this.refreshTimer) {
            clearInterval(this.refreshTimer);
            this.refreshTimer = null;
        }
    }

    // Consolidate view
    consolidateView() {
        // Merge related data into a summary view
        this.switchView('dashboard');
    }

    // Sort data
    sortData(direction) {
        // Sort implementation based on current view
        console.log('Sort:', direction);
    }

    // Adjust zoom
    adjustZoom(delta) {
        const cells = document.querySelector('.cells');
        const currentSize = parseFloat(getComputedStyle(cells).fontSize) || 14;
        const newSize = Math.max(10, Math.min(20, currentSize + delta));
        cells.style.fontSize = `${newSize}px`;
    }

    // Show agent details modal
    showAgentDetails(agentId) {
        const agent = this.spreadsheet.data.agents[agentId];
        if (!agent) return;

        const agentNames = {
            'macro': 'Macro Economics',
            'geopolitical': 'Geopolitical',
            'commodities': 'Commodities',
            'sentiment': 'Sentiment',
            'fundamentals': 'Fundamentals',
            'technical': 'Technical',
            'alternative': 'Alternative Data',
            'cross_asset': 'Cross-Asset',
            'event': 'Event-Driven',
            'risk': 'Risk',
            'aggregation': 'Aggregation',
            'learning': 'Learning'
        };

        const modalTitle = document.getElementById('modal-title');
        const modalBody = document.getElementById('modal-body');

        modalTitle.textContent = `${agentNames[agentId]} Agent Details`;
        modalBody.innerHTML = `
            <div class="agent-details">
                <div class="form-group">
                    <label>Outlook</label>
                    <div class="agent-badge ${agent.outlook?.toLowerCase()}">${agent.outlook || 'N/A'}</div>
                </div>
                <div class="form-group">
                    <label>Confidence</label>
                    <div class="confidence-meter">
                        <div class="confidence-bar">
                            <div class="confidence-fill" style="width: ${agent.confidence || 0}%"></div>
                        </div>
                        <span>${agent.confidence || 0}%</span>
                    </div>
                </div>
                <div class="form-group">
                    <label>Timeframe</label>
                    <div>${agent.timeframe || 'N/A'}</div>
                </div>
                <div class="form-group">
                    <label>Key Factors</label>
                    <ul>
                        ${(agent.key_factors || []).map(f => `<li>${f}</li>`).join('') || '<li>None</li>'}
                    </ul>
                </div>
                <div class="form-group">
                    <label>Uncertainties</label>
                    <ul>
                        ${(agent.uncertainties || []).map(u => `<li>${u}</li>`).join('') || '<li>None</li>'}
                    </ul>
                </div>
                <div class="form-group">
                    <label>Reasoning</label>
                    <p>${agent.reasoning || 'No reasoning available'}</p>
                </div>
                <div class="form-group">
                    <label>Last Updated</label>
                    <div>${agent.updated_at ? new Date(agent.updated_at).toLocaleString() : 'N/A'}</div>
                </div>
            </div>
        `;

        this.showModal();
    }

    // Show add position modal
    showAddPositionModal() {
        const modalTitle = document.getElementById('modal-title');
        const modalBody = document.getElementById('modal-body');
        const modalConfirm = document.getElementById('modal-confirm');

        modalTitle.textContent = 'Add New Position';
        modalBody.innerHTML = `
            <form id="add-position-form">
                <div class="form-group">
                    <label>Symbol</label>
                    <input type="text" id="position-symbol" placeholder="e.g., AAPL" required>
                </div>
                <div class="form-group">
                    <label>Shares</label>
                    <input type="number" id="position-shares" placeholder="100" required>
                </div>
                <div class="form-group">
                    <label>Average Cost</label>
                    <input type="number" id="position-cost" step="0.01" placeholder="150.00" required>
                </div>
                <div class="form-group">
                    <label>Sector</label>
                    <select id="position-sector">
                        <option value="Technology">Technology</option>
                        <option value="Financial">Financial</option>
                        <option value="Healthcare">Healthcare</option>
                        <option value="Consumer">Consumer</option>
                        <option value="Industrial">Industrial</option>
                        <option value="Energy">Energy</option>
                        <option value="Other">Other</option>
                    </select>
                </div>
            </form>
        `;

        modalConfirm.onclick = async () => {
            const symbol = document.getElementById('position-symbol').value;
            const shares = parseInt(document.getElementById('position-shares').value);
            const avg_cost = parseFloat(document.getElementById('position-cost').value);
            const sector = document.getElementById('position-sector').value;

            try {
                await api.addPosition({ symbol, shares, avg_cost, sector });
                this.showToast('Position added', 'success');
                this.hideModal();
                this.refreshData();
            } catch (error) {
                this.showToast('Failed to add position', 'error');
            }
        };

        this.showModal();
    }

    // Show remove position modal
    showRemovePositionModal() {
        const positions = this.spreadsheet.data.positions || [];
        const modalTitle = document.getElementById('modal-title');
        const modalBody = document.getElementById('modal-body');
        const modalConfirm = document.getElementById('modal-confirm');

        modalTitle.textContent = 'Remove Position';
        modalBody.innerHTML = `
            <form id="remove-position-form">
                <div class="form-group">
                    <label>Select Position</label>
                    <select id="position-to-remove">
                        ${positions.map(p => `<option value="${p.id || p.symbol}">${p.symbol} - ${p.shares} shares</option>`).join('')}
                    </select>
                </div>
                <p style="color: var(--bearish)">Warning: This action cannot be undone.</p>
            </form>
        `;

        modalConfirm.onclick = async () => {
            const positionId = document.getElementById('position-to-remove').value;
            try {
                await api.removePosition(positionId);
                this.showToast('Position removed', 'success');
                this.hideModal();
                this.refreshData();
            } catch (error) {
                this.showToast('Failed to remove position', 'error');
            }
        };

        this.showModal();
    }

    // Show edit position modal
    showEditPositionModal() {
        const positions = this.spreadsheet.data.positions || [];
        const modalTitle = document.getElementById('modal-title');
        const modalBody = document.getElementById('modal-body');
        const modalConfirm = document.getElementById('modal-confirm');

        modalTitle.textContent = 'Edit Position';
        modalBody.innerHTML = `
            <form id="edit-position-form">
                <div class="form-group">
                    <label>Select Position</label>
                    <select id="position-to-edit" onchange="window.app.populateEditForm()">
                        ${positions.map(p => `<option value="${p.id || p.symbol}" data-shares="${p.shares}" data-cost="${p.avg_cost}" data-sector="${p.sector}">${p.symbol}</option>`).join('')}
                    </select>
                </div>
                <div class="form-group">
                    <label>New Shares</label>
                    <input type="number" id="edit-shares" placeholder="100">
                </div>
                <div class="form-group">
                    <label>New Average Cost</label>
                    <input type="number" id="edit-cost" step="0.01" placeholder="150.00">
                </div>
            </form>
        `;

        modalConfirm.onclick = async () => {
            const positionId = document.getElementById('position-to-edit').value;
            const shares = parseInt(document.getElementById('edit-shares').value);
            const avg_cost = parseFloat(document.getElementById('edit-cost').value);

            try {
                await api.updatePosition(positionId, { shares, avg_cost });
                this.showToast('Position updated', 'success');
                this.hideModal();
                this.refreshData();
            } catch (error) {
                this.showToast('Failed to update position', 'error');
            }
        };

        this.showModal();
        this.populateEditForm();
    }

    // Populate edit form with selected position data
    populateEditForm() {
        const select = document.getElementById('position-to-edit');
        const option = select.options[select.selectedIndex];
        document.getElementById('edit-shares').value = option.dataset.shares || '';
        document.getElementById('edit-cost').value = option.dataset.cost || '';
    }

    // Show modal
    showModal() {
        document.getElementById('modal').classList.remove('hidden');
    }

    // Hide modal
    hideModal() {
        document.getElementById('modal').classList.add('hidden');
    }

    // Show toast notification
    showToast(message, type = 'info') {
        const container = document.getElementById('toast-container');
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        toast.textContent = message;
        container.appendChild(toast);

        setTimeout(() => {
            toast.style.opacity = '0';
            setTimeout(() => toast.remove(), 300);
        }, 3000);
    }

    // Handle keyboard shortcuts
    handleKeyboard(e) {
        // Ctrl+R: Refresh
        if (e.ctrlKey && e.key === 'r') {
            e.preventDefault();
            this.refreshData();
        }

        // Ctrl+E: Export
        if (e.ctrlKey && e.key === 'e') {
            e.preventDefault();
            this.exportReport();
        }

        // Ctrl+A: Analyze
        if (e.ctrlKey && e.key === 'a' && !e.target.closest('input, textarea')) {
            e.preventDefault();
            this.triggerAnalysis();
        }

        // Escape: Close modal
        if (e.key === 'Escape') {
            this.hideModal();
        }

        // Number keys for view switching
        if (!e.ctrlKey && !e.altKey && !e.target.closest('input, textarea, select')) {
            const views = ['dashboard', 'agents', 'portfolio', 'performance', 'signals', 'risk', 'execution', 'settings', 'help'];
            const num = parseInt(e.key);
            if (num >= 1 && num <= 9 && views[num - 1]) {
                this.switchView(views[num - 1]);
            }
        }
    }
}

// Global app instance
let app;

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    app = new EquitiesExcelApp();
    window.app = app;
    app.init();
});
