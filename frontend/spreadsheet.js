/**
 * Equities AI - Spreadsheet Engine
 * Handles the Excel-like grid interface for displaying equity data
 */

class SpreadsheetEngine {
    constructor(containerId = 'spreadsheet') {
        this.container = document.getElementById(containerId);
        this.rows = 30;
        this.cols = 11;
        this.cells = {};
        this.selectedCell = null;
        this.currentView = 'dashboard';
        this.data = {
            agents: {},
            portfolio: null,
            positions: [],
            signals: [],
            performance: null,
            settings: {}
        };
        this.columnHeaders = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K'];
        this.numberFormat = 'currency';
        this.decimals = 2;
        this.autoRefresh = true;
        this.refreshInterval = null;
    }

    // Initialize the spreadsheet grid
    init() {
        this.render();
        this.attachEvents();
        this.setupFormulas();
    }

    // Render the grid
    render() {
        this.container.innerHTML = '';

        // Create spacer cell (top-left corner)
        const spacer = document.createElement('div');
        spacer.className = 'cells__spacer';
        this.container.appendChild(spacer);

        // Create column headers
        for (let col = 0; col < this.cols; col++) {
            const header = document.createElement('div');
            header.className = 'cells__alphabet';
            header.textContent = this.columnHeaders[col];
            this.container.appendChild(header);
        }

        // Create row numbers and cells
        for (let row = 1; row <= this.rows; row++) {
            // Row number
            const rowNum = document.createElement('div');
            rowNum.className = 'cells__number';
            rowNum.textContent = row;
            this.container.appendChild(rowNum);

            // Cells for this row
            for (let col = 0; col < this.cols; col++) {
                const cellId = `${this.columnHeaders[col]}${row}`;
                const cell = document.createElement('input');
                cell.type = 'text';
                cell.className = 'cells__input';
                cell.id = cellId;
                cell.dataset.row = row;
                cell.dataset.col = col;
                cell.readOnly = true; // Data is from API, not user-editable

                this.cells[cellId] = cell;
                this.container.appendChild(cell);
            }
        }

        // Adjust grid for the actual number of rows
        this.container.style.gridTemplateRows = `repeat(${this.rows + 1}, 25px)`;
    }

    // Attach event listeners
    attachEvents() {
        // Cell selection
        this.container.addEventListener('click', (e) => {
            if (e.target.classList.contains('cells__input')) {
                this.selectCell(e.target);
            }
        });

        // Double-click to view details
        this.container.addEventListener('dblclick', (e) => {
            if (e.target.classList.contains('cells__input') && e.target.classList.contains('cell-clickable')) {
                const row = parseInt(e.target.dataset.row);
                this.showCellDetails(e.target, row);
            }
        });
    }

    // Select a cell
    selectCell(cell) {
        if (this.selectedCell) {
            this.selectedCell.classList.remove('cell-selected');
        }
        cell.classList.add('cell-selected');
        this.selectedCell = cell;

        // Update formula bar
        const formulaDisplay = document.getElementById('formula-display');
        if (formulaDisplay) {
            formulaDisplay.textContent = cell.value || '';
        }

        // Update cell info in status bar
        const cellInfo = document.getElementById('cell-info');
        if (cellInfo) {
            cellInfo.textContent = `Cell ${cell.id}`;
        }
    }

    // Set cell value with formatting
    setCell(cellId, value, options = {}) {
        const cell = this.cells[cellId];
        if (!cell) return;

        // Clear existing classes
        cell.className = 'cells__input';

        // Apply value
        if (value === null || value === undefined) {
            cell.value = '';
        } else if (typeof value === 'number') {
            cell.value = this.formatNumber(value);
        } else {
            cell.value = String(value);
        }

        // Apply styling
        if (options.type) {
            cell.classList.add(`cell-${options.type}`);
        }
        if (options.clickable) {
            cell.classList.add('cell-clickable');
        }
        if (options.className) {
            cell.classList.add(options.className);
        }

        // Store raw value for calculations
        cell.dataset.rawValue = value;
        cell.dataset.type = options.type || 'text';
    }

    // Format numbers based on current format
    formatNumber(value) {
        if (isNaN(value)) return value;

        switch (this.numberFormat) {
            case 'currency':
                return new Intl.NumberFormat('en-US', {
                    style: 'currency',
                    currency: 'USD',
                    minimumFractionDigits: this.decimals,
                    maximumFractionDigits: this.decimals
                }).format(value);

            case 'percent':
                return new Intl.NumberFormat('en-US', {
                    style: 'percent',
                    minimumFractionDigits: this.decimals,
                    maximumFractionDigits: this.decimals
                }).format(value / 100);

            case 'number':
                return new Intl.NumberFormat('en-US', {
                    minimumFractionDigits: this.decimals,
                    maximumFractionDigits: this.decimals
                }).format(value);

            default:
                return String(value);
        }
    }

    // Clear all cells
    clear() {
        Object.values(this.cells).forEach(cell => {
            cell.value = '';
            cell.className = 'cells__input';
            cell.dataset.rawValue = '';
            cell.dataset.type = '';
        });
    }

    // Setup custom formulas for equities data
    setupFormulas() {
        // These would be evaluated when cells reference formulas
        this.formulas = {
            'AGENT_CONSENSUS': (agents, field) => this.calculateConsensus(agents, field),
            'AGENT_OUTLOOK': (agentId) => this.data.agents[agentId]?.outlook || 'N/A',
            'AGENT_CONFIDENCE': (agentId) => this.data.agents[agentId]?.confidence || 0,
            'PORTFOLIO_VALUE': () => this.data.portfolio?.total_value || 0,
            'PORTFOLIO_PNL': () => this.data.portfolio?.pnl || 0,
            'RISK_SCORE': () => this.data.portfolio?.risk_score || 0
        };
    }

    // Calculate consensus from agent data
    calculateConsensus(agents, field) {
        const values = Object.values(this.data.agents)
            .filter(a => a && a[field])
            .map(a => a[field]);

        if (values.length === 0) return 'N/A';

        if (field === 'outlook') {
            const counts = { bullish: 0, bearish: 0, neutral: 0 };
            values.forEach(v => counts[v.toLowerCase()]++);
            const max = Math.max(...Object.values(counts));
            return Object.keys(counts).find(k => counts[k] === max);
        }

        if (field === 'confidence') {
            return values.reduce((a, b) => a + b, 0) / values.length;
        }

        return values[0];
    }

    // Render Dashboard view
    renderDashboard() {
        this.clear();
        this.currentView = 'dashboard';

        // Title row
        this.setCell('A1', 'EQUITIES AI DASHBOARD', { type: 'header' });
        this.setCell('F1', new Date().toLocaleString(), { type: 'label' });

        // Market Overview section
        this.setCell('A3', 'MARKET OVERVIEW', { type: 'header' });
        this.setCell('A4', 'Market Status:', { type: 'label' });
        this.setCell('B4', this.data.marketRegime || 'Loading...', { type: 'neutral' });
        this.setCell('C4', 'Consensus:', { type: 'label' });
        this.setCell('D4', this.calculateConsensus('all', 'outlook'), {
            type: this.getOutlookType(this.calculateConsensus('all', 'outlook'))
        });
        this.setCell('E4', 'Confidence:', { type: 'label' });
        this.setCell('F4', `${Math.round(this.calculateConsensus('all', 'confidence') || 0)}%`, { type: 'neutral' });

        // Agent Status section
        this.setCell('A6', 'AGENT STATUS', { type: 'header' });
        this.setCell('A7', 'Agent', { type: 'header' });
        this.setCell('B7', 'Outlook', { type: 'header' });
        this.setCell('C7', 'Confidence', { type: 'header' });
        this.setCell('D7', 'Status', { type: 'header' });
        this.setCell('E7', 'Last Update', { type: 'header' });

        const agentIds = [
            'macro', 'geopolitical', 'commodities', 'sentiment',
            'fundamentals', 'technical', 'alternative', 'cross_asset',
            'event', 'risk', 'aggregation', 'learning'
        ];

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

        agentIds.forEach((agentId, index) => {
            const row = 8 + index;
            const agent = this.data.agents[agentId];

            this.setCell(`A${row}`, agentNames[agentId], { type: 'label', clickable: true });
            this.setCell(`B${row}`, agent?.outlook || '--', {
                type: this.getOutlookType(agent?.outlook),
                clickable: true
            });
            this.setCell(`C${row}`, agent?.confidence ? `${agent.confidence}%` : '--', { type: 'neutral' });
            this.setCell(`D${row}`, agent?.status || 'Idle', {
                type: agent?.status === 'running' ? 'warning' : 'neutral'
            });
            this.setCell(`E${row}`, agent?.updated_at ? this.formatTime(agent.updated_at) : '--', { type: 'neutral' });
        });

        // Aggregated Insight section
        this.setCell('G6', 'AGGREGATED INSIGHT', { type: 'header' });
        const insight = this.data.insight;
        this.setCell('G7', 'Overall Outlook:', { type: 'label' });
        this.setCell('H7', insight?.overall_outlook || '--', {
            type: this.getOutlookType(insight?.overall_outlook)
        });
        this.setCell('G8', 'Confidence:', { type: 'label' });
        this.setCell('H8', insight?.confidence ? `${insight.confidence}%` : '--', { type: 'neutral' });
        this.setCell('G9', 'Risk Level:', { type: 'label' });
        this.setCell('H9', insight?.risk_level || '--', {
            type: insight?.risk_level === 'high' ? 'bearish' : insight?.risk_level === 'low' ? 'bullish' : 'neutral'
        });
        this.setCell('G10', 'Vetoed:', { type: 'label' });
        this.setCell('H10', insight?.vetoed ? 'YES' : 'NO', {
            type: insight?.vetoed ? 'bearish' : 'bullish'
        });

        // Quick Stats section
        this.setCell('G12', 'QUICK STATS', { type: 'header' });
        const perf = this.data.performance;
        this.setCell('G13', 'Avg Accuracy:', { type: 'label' });
        this.setCell('H13', perf?.avg_accuracy ? `${perf.avg_accuracy}%` : '--', { type: 'neutral' });
        this.setCell('G14', 'Total Predictions:', { type: 'label' });
        this.setCell('H14', perf?.total_predictions || '--', { type: 'neutral' });
        this.setCell('G15', 'Best Agent:', { type: 'label' });
        this.setCell('H15', perf?.best_agent || '--', { type: 'bullish' });

        // Update formula bar
        const formulaDisplay = document.getElementById('formula-display');
        if (formulaDisplay) {
            formulaDisplay.textContent = '=AGENT_CONSENSUS("ALL", "OUTLOOK")';
        }
    }

    // Render Agents Detail view
    renderAgentsView() {
        this.clear();
        this.currentView = 'agents';

        this.setCell('A1', 'AGENT DETAILS', { type: 'header' });

        // Headers
        this.setCell('A3', 'Agent', { type: 'header' });
        this.setCell('B3', 'Phase', { type: 'header' });
        this.setCell('C3', 'Outlook', { type: 'header' });
        this.setCell('D3', 'Confidence', { type: 'header' });
        this.setCell('E3', 'Timeframe', { type: 'header' });
        this.setCell('F3', 'Key Factor', { type: 'header' });
        this.setCell('G3', 'Uncertainty', { type: 'header' });
        this.setCell('H3', 'Weight', { type: 'header' });
        this.setCell('I3', 'Accuracy', { type: 'header' });
        this.setCell('J3', 'Status', { type: 'header' });
        this.setCell('K3', 'Updated', { type: 'header' });

        const agents = [
            { id: 'macro', name: 'Macro Economics', phase: 'Data Gathering' },
            { id: 'geopolitical', name: 'Geopolitical', phase: 'Data Gathering' },
            { id: 'commodities', name: 'Commodities', phase: 'Data Gathering' },
            { id: 'sentiment', name: 'Sentiment', phase: 'Analysis' },
            { id: 'fundamentals', name: 'Fundamentals', phase: 'Analysis' },
            { id: 'technical', name: 'Technical', phase: 'Analysis' },
            { id: 'alternative', name: 'Alternative Data', phase: 'Alpha Discovery' },
            { id: 'cross_asset', name: 'Cross-Asset', phase: 'Alpha Discovery' },
            { id: 'event', name: 'Event-Driven', phase: 'Alpha Discovery' },
            { id: 'risk', name: 'Risk', phase: 'Risk Management' },
            { id: 'aggregation', name: 'Aggregation', phase: 'Synthesis' },
            { id: 'learning', name: 'Learning', phase: 'Learning' }
        ];

        agents.forEach((agent, index) => {
            const row = 4 + index;
            const data = this.data.agents[agent.id];
            const weight = this.data.weights?.[agent.id];
            const perf = this.data.agentPerformance?.[agent.id];

            this.setCell(`A${row}`, agent.name, { type: 'label', clickable: true });
            this.setCell(`B${row}`, agent.phase, { type: 'neutral' });
            this.setCell(`C${row}`, data?.outlook || '--', {
                type: this.getOutlookType(data?.outlook)
            });
            this.setCell(`D${row}`, data?.confidence ? `${data.confidence}%` : '--', { type: 'neutral' });
            this.setCell(`E${row}`, data?.timeframe || '--', { type: 'neutral' });
            this.setCell(`F${row}`, data?.key_factors?.[0] || '--', { type: 'neutral' });
            this.setCell(`G${row}`, data?.uncertainties?.[0] || '--', { type: 'neutral' });
            this.setCell(`H${row}`, weight ? `${(weight * 100).toFixed(1)}%` : '--', { type: 'neutral' });
            this.setCell(`I${row}`, perf?.accuracy ? `${perf.accuracy}%` : '--', {
                type: perf?.accuracy >= 60 ? 'bullish' : perf?.accuracy >= 40 ? 'neutral' : 'bearish'
            });
            this.setCell(`J${row}`, data?.status || 'Idle', {
                type: data?.status === 'running' ? 'warning' : 'neutral'
            });
            this.setCell(`K${row}`, data?.updated_at ? this.formatTime(data.updated_at) : '--', { type: 'neutral' });
        });

        // Summary row
        const summaryRow = 17;
        this.setCell(`A${summaryRow}`, 'SUMMARY', { type: 'header' });
        this.setCell(`C${summaryRow}`, this.calculateConsensus('all', 'outlook'), {
            type: this.getOutlookType(this.calculateConsensus('all', 'outlook'))
        });
        this.setCell(`D${summaryRow}`, `${Math.round(this.calculateConsensus('all', 'confidence') || 0)}%`, { type: 'neutral' });
    }

    // Render Portfolio view
    renderPortfolioView() {
        this.clear();
        this.currentView = 'portfolio';

        const portfolio = this.data.portfolio || {};
        const positions = this.data.positions || [];

        // Portfolio Overview
        this.setCell('A1', 'PORTFOLIO OVERVIEW', { type: 'header' });

        this.setCell('A3', 'Total Value:', { type: 'label' });
        this.setCell('B3', portfolio.total_value || 0, { type: 'value' });
        this.setCell('C3', 'Invested:', { type: 'label' });
        this.setCell('D3', portfolio.invested || 0, { type: 'value' });
        this.setCell('E3', 'Cash:', { type: 'label' });
        this.setCell('F3', portfolio.cash || 0, { type: 'value' });

        this.setCell('A4', 'P&L:', { type: 'label' });
        this.setCell('B4', portfolio.pnl || 0, {
            type: (portfolio.pnl || 0) >= 0 ? 'bullish' : 'bearish'
        });
        this.setCell('C4', 'P&L %:', { type: 'label' });
        this.setCell('D4', portfolio.pnl_percent ? `${portfolio.pnl_percent}%` : '--', {
            type: (portfolio.pnl_percent || 0) >= 0 ? 'bullish' : 'bearish'
        });
        this.setCell('E4', 'Sharpe Ratio:', { type: 'label' });
        this.setCell('F4', portfolio.sharpe_ratio?.toFixed(2) || '--', { type: 'neutral' });

        // Risk Metrics
        this.setCell('H1', 'RISK METRICS', { type: 'header' });
        const risk = this.data.risk || {};

        this.setCell('H3', 'Max Drawdown:', { type: 'label' });
        this.setCell('I3', risk.max_drawdown ? `${risk.max_drawdown}%` : '--', {
            type: (risk.max_drawdown || 0) > 10 ? 'bearish' : 'neutral'
        });
        this.setCell('H4', 'Leverage:', { type: 'label' });
        this.setCell('I4', risk.leverage ? `${risk.leverage}x` : '--', { type: 'neutral' });
        this.setCell('H5', 'Concentration:', { type: 'label' });
        this.setCell('I5', risk.concentration ? `${risk.concentration}%` : '--', { type: 'neutral' });
        this.setCell('H6', 'VaR (95%):', { type: 'label' });
        this.setCell('I6', risk.var_95 || '--', { type: 'neutral' });

        // Positions Table
        this.setCell('A7', 'POSITIONS', { type: 'header' });

        this.setCell('A8', 'Symbol', { type: 'header' });
        this.setCell('B8', 'Name', { type: 'header' });
        this.setCell('C8', 'Sector', { type: 'header' });
        this.setCell('D8', 'Shares', { type: 'header' });
        this.setCell('E8', 'Avg Cost', { type: 'header' });
        this.setCell('F8', 'Current', { type: 'header' });
        this.setCell('G8', 'Value', { type: 'header' });
        this.setCell('H8', 'Weight', { type: 'header' });
        this.setCell('I8', 'P&L', { type: 'header' });
        this.setCell('J8', 'Change %', { type: 'header' });

        positions.forEach((pos, index) => {
            const row = 9 + index;
            const pnl = (pos.current_price - pos.avg_cost) * pos.shares;
            const pnlPercent = ((pos.current_price - pos.avg_cost) / pos.avg_cost * 100).toFixed(2);

            this.setCell(`A${row}`, pos.symbol, { type: 'label', clickable: true });
            this.setCell(`B${row}`, pos.name || '--', { type: 'neutral' });
            this.setCell(`C${row}`, pos.sector || '--', { type: 'neutral' });
            this.setCell(`D${row}`, pos.shares, { type: 'value' });
            this.setCell(`E${row}`, pos.avg_cost, { type: 'value' });
            this.setCell(`F${row}`, pos.current_price, { type: 'value' });
            this.setCell(`G${row}`, pos.value || pos.current_price * pos.shares, { type: 'value' });
            this.setCell(`H${row}`, pos.weight ? `${pos.weight}%` : '--', { type: 'neutral' });
            this.setCell(`I${row}`, pnl, { type: pnl >= 0 ? 'bullish' : 'bearish' });
            this.setCell(`J${row}`, `${pnlPercent}%`, { type: pnl >= 0 ? 'bullish' : 'bearish' });
        });

        if (positions.length === 0) {
            this.setCell('A9', 'No positions', { type: 'neutral' });
        }
    }

    // Render Performance view
    renderPerformanceView() {
        this.clear();
        this.currentView = 'performance';

        this.setCell('A1', 'PERFORMANCE METRICS', { type: 'header' });

        const perf = this.data.performance || {};

        // Summary Stats
        this.setCell('A3', 'Overall Accuracy:', { type: 'label' });
        this.setCell('B3', perf.overall_accuracy ? `${perf.overall_accuracy}%` : '--', { type: 'neutral' });
        this.setCell('C3', 'Total Predictions:', { type: 'label' });
        this.setCell('D3', perf.total_predictions || '--', { type: 'neutral' });
        this.setCell('E3', 'Correct:', { type: 'label' });
        this.setCell('F3', perf.correct_predictions || '--', { type: 'bullish' });
        this.setCell('G3', 'Best Agent:', { type: 'label' });
        this.setCell('H3', perf.best_agent || '--', { type: 'bullish' });

        // Agent Performance Table
        this.setCell('A5', 'AGENT PERFORMANCE', { type: 'header' });

        this.setCell('A6', 'Agent', { type: 'header' });
        this.setCell('B6', 'Predictions', { type: 'header' });
        this.setCell('C6', 'Correct', { type: 'header' });
        this.setCell('D6', 'Accuracy', { type: 'header' });
        this.setCell('E6', 'Brier Score', { type: 'header' });
        this.setCell('F6', 'Calibration', { type: 'header' });
        this.setCell('G6', 'Weight', { type: 'header' });
        this.setCell('H6', 'Trend', { type: 'header' });

        const agentPerf = perf.by_agent || {};
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

        Object.keys(agentNames).forEach((agentId, index) => {
            const row = 7 + index;
            const data = agentPerf[agentId] || {};
            const weight = this.data.weights?.[agentId];

            this.setCell(`A${row}`, agentNames[agentId], { type: 'label' });
            this.setCell(`B${row}`, data.total || '--', { type: 'neutral' });
            this.setCell(`C${row}`, data.correct || '--', { type: 'bullish' });
            this.setCell(`D${row}`, data.accuracy ? `${data.accuracy}%` : '--', {
                type: (data.accuracy || 0) >= 60 ? 'bullish' : (data.accuracy || 0) >= 40 ? 'neutral' : 'bearish'
            });
            this.setCell(`E${row}`, data.brier_score?.toFixed(3) || '--', { type: 'neutral' });
            this.setCell(`F${row}`, data.calibration?.toFixed(3) || '--', { type: 'neutral' });
            this.setCell(`G${row}`, weight ? `${(weight * 100).toFixed(1)}%` : '--', { type: 'neutral' });
            this.setCell(`H${row}`, data.trend || '--', {
                type: data.trend === 'up' ? 'bullish' : data.trend === 'down' ? 'bearish' : 'neutral'
            });
        });
    }

    // Render Signals view
    renderSignalsView() {
        this.clear();
        this.currentView = 'signals';

        this.setCell('A1', 'TRADE SIGNALS', { type: 'header' });

        this.setCell('A3', 'Symbol', { type: 'header' });
        this.setCell('B3', 'Action', { type: 'header' });
        this.setCell('C3', 'Strength', { type: 'header' });
        this.setCell('D3', 'Confidence', { type: 'header' });
        this.setCell('E3', 'Target', { type: 'header' });
        this.setCell('F3', 'Stop Loss', { type: 'header' });
        this.setCell('G3', 'Take Profit', { type: 'header' });
        this.setCell('H3', 'Source', { type: 'header' });
        this.setCell('I3', 'Status', { type: 'header' });
        this.setCell('J3', 'Generated', { type: 'header' });

        const signals = this.data.signals || [];

        signals.forEach((signal, index) => {
            const row = 4 + index;

            this.setCell(`A${row}`, signal.symbol, { type: 'label', clickable: true });
            this.setCell(`B${row}`, signal.action, {
                type: signal.action === 'buy' ? 'bullish' : signal.action === 'sell' ? 'bearish' : 'neutral'
            });
            this.setCell(`C${row}`, signal.strength || '--', { type: 'neutral' });
            this.setCell(`D${row}`, signal.confidence ? `${signal.confidence}%` : '--', { type: 'neutral' });
            this.setCell(`E${row}`, signal.target_price, { type: 'value' });
            this.setCell(`F${row}`, signal.stop_loss, { type: 'value' });
            this.setCell(`G${row}`, signal.take_profit, { type: 'value' });
            this.setCell(`H${row}`, signal.source_agent || '--', { type: 'neutral' });
            this.setCell(`I${row}`, signal.status || 'pending', {
                type: signal.status === 'executed' ? 'bullish' : signal.status === 'rejected' ? 'bearish' : 'warning'
            });
            this.setCell(`J${row}`, signal.created_at ? this.formatTime(signal.created_at) : '--', { type: 'neutral' });
        });

        if (signals.length === 0) {
            this.setCell('A4', 'No active signals', { type: 'neutral' });
        }
    }

    // Render Settings view
    renderSettingsView() {
        this.clear();
        this.currentView = 'settings';

        this.setCell('A1', 'SETTINGS', { type: 'header' });

        const categories = ['api_config', 'agent_config', 'risk_management', 'scheduling', 'performance', 'ui_preferences', 'system'];
        const categoryNames = {
            'api_config': 'API Configuration',
            'agent_config': 'Agent Configuration',
            'risk_management': 'Risk Management',
            'scheduling': 'Scheduling',
            'performance': 'Performance',
            'ui_preferences': 'UI Preferences',
            'system': 'System'
        };

        let currentRow = 3;

        categories.forEach(category => {
            const settings = this.data.settings[category] || {};

            this.setCell(`A${currentRow}`, categoryNames[category], { type: 'header' });
            currentRow++;

            this.setCell(`A${currentRow}`, 'Key', { type: 'header' });
            this.setCell(`B${currentRow}`, 'Value', { type: 'header' });
            this.setCell(`C${currentRow}`, 'Type', { type: 'header' });
            this.setCell(`D${currentRow}`, 'Description', { type: 'header' });
            currentRow++;

            Object.entries(settings).forEach(([key, setting]) => {
                if (currentRow > this.rows) return;

                const displayValue = setting.is_sensitive ? '********' :
                    (setting.value !== null && setting.value !== undefined ? String(setting.value) : '--');

                this.setCell(`A${currentRow}`, key, { type: 'label' });
                this.setCell(`B${currentRow}`, displayValue, { type: 'neutral', clickable: !setting.is_sensitive });
                this.setCell(`C${currentRow}`, setting.value_type || setting.type || 'string', { type: 'neutral' });
                this.setCell(`D${currentRow}`, setting.description || '--', { type: 'neutral' });
                currentRow++;
            });

            currentRow++; // Extra space between categories
        });
    }

    // Render Risk view
    renderRiskView() {
        this.clear();
        this.currentView = 'risk';

        this.setCell('A1', 'RISK MANAGEMENT', { type: 'header' });

        const risk = this.data.risk || {};
        const alerts = this.data.riskAlerts || [];

        // Risk Metrics
        this.setCell('A3', 'RISK METRICS', { type: 'header' });

        this.setCell('A4', 'Portfolio Risk Score:', { type: 'label' });
        this.setCell('B4', risk.portfolio_risk ? `${risk.portfolio_risk}%` : '--', {
            type: (risk.portfolio_risk || 0) > 70 ? 'bearish' : (risk.portfolio_risk || 0) > 40 ? 'warning' : 'bullish'
        });

        this.setCell('A5', 'Max Drawdown:', { type: 'label' });
        this.setCell('B5', risk.max_drawdown ? `${risk.max_drawdown}%` : '--', {
            type: (risk.max_drawdown || 0) > 15 ? 'bearish' : 'neutral'
        });

        this.setCell('A6', 'Current Leverage:', { type: 'label' });
        this.setCell('B6', risk.leverage ? `${risk.leverage}x` : '--', { type: 'neutral' });

        this.setCell('A7', 'Position Concentration:', { type: 'label' });
        this.setCell('B7', risk.concentration ? `${risk.concentration}%` : '--', { type: 'neutral' });

        this.setCell('A8', 'Value at Risk (95%):', { type: 'label' });
        this.setCell('B8', risk.var_95 || '--', { type: 'neutral' });

        this.setCell('A9', 'Beta:', { type: 'label' });
        this.setCell('B9', risk.beta?.toFixed(2) || '--', { type: 'neutral' });

        // Risk Veto Status
        this.setCell('D3', 'VETO STATUS', { type: 'header' });
        this.setCell('D4', 'Vetoed:', { type: 'label' });
        this.setCell('E4', risk.vetoed ? 'YES' : 'NO', {
            type: risk.vetoed ? 'bearish' : 'bullish'
        });
        this.setCell('D5', 'Veto Reason:', { type: 'label' });
        this.setCell('E5', risk.veto_reason || 'None', { type: 'neutral' });

        // Risk Alerts
        this.setCell('A11', 'RISK ALERTS', { type: 'header' });

        this.setCell('A12', 'Type', { type: 'header' });
        this.setCell('B12', 'Message', { type: 'header' });
        this.setCell('C12', 'Severity', { type: 'header' });
        this.setCell('D12', 'Time', { type: 'header' });

        alerts.forEach((alert, index) => {
            const row = 13 + index;
            if (row > this.rows) return;

            this.setCell(`A${row}`, alert.type, { type: 'label' });
            this.setCell(`B${row}`, alert.message, { type: 'neutral' });
            this.setCell(`C${row}`, alert.severity, {
                type: alert.severity === 'high' ? 'bearish' : alert.severity === 'medium' ? 'warning' : 'neutral'
            });
            this.setCell(`D${row}`, alert.created_at ? this.formatTime(alert.created_at) : '--', { type: 'neutral' });
        });

        if (alerts.length === 0) {
            this.setCell('A13', 'No active alerts', { type: 'bullish' });
        }
    }

    // Render Execution view
    renderExecutionView() {
        this.clear();
        this.currentView = 'execution';

        this.setCell('A1', 'EXECUTION ORDERS', { type: 'header' });

        this.setCell('A3', 'Order ID', { type: 'header' });
        this.setCell('B3', 'Symbol', { type: 'header' });
        this.setCell('C3', 'Action', { type: 'header' });
        this.setCell('D3', 'Quantity', { type: 'header' });
        this.setCell('E3', 'Price', { type: 'header' });
        this.setCell('F3', 'Kelly Size', { type: 'header' });
        this.setCell('G3', 'Status', { type: 'header' });
        this.setCell('H3', 'Approved By', { type: 'header' });
        this.setCell('I3', 'Created', { type: 'header' });

        const orders = this.data.executionOrders || [];

        orders.forEach((order, index) => {
            const row = 4 + index;
            if (row > this.rows) return;

            this.setCell(`A${row}`, order.id?.slice(0, 8) || '--', { type: 'label', clickable: true });
            this.setCell(`B${row}`, order.symbol, { type: 'label' });
            this.setCell(`C${row}`, order.action, {
                type: order.action === 'buy' ? 'bullish' : 'bearish'
            });
            this.setCell(`D${row}`, order.quantity, { type: 'value' });
            this.setCell(`E${row}`, order.price, { type: 'value' });
            this.setCell(`F${row}`, order.kelly_size ? `${order.kelly_size}%` : '--', { type: 'neutral' });
            this.setCell(`G${row}`, order.status, {
                type: order.status === 'executed' ? 'bullish' :
                    order.status === 'pending' ? 'warning' :
                    order.status === 'rejected' ? 'bearish' : 'neutral'
            });
            this.setCell(`H${row}`, order.approved_by || '--', { type: 'neutral' });
            this.setCell(`I${row}`, order.created_at ? this.formatTime(order.created_at) : '--', { type: 'neutral' });
        });

        if (orders.length === 0) {
            this.setCell('A4', 'No execution orders', { type: 'neutral' });
        }
    }

    // Helper: Get outlook type for styling
    getOutlookType(outlook) {
        if (!outlook) return 'neutral';
        const lower = outlook.toLowerCase();
        if (lower === 'bullish' || lower === 'buy') return 'bullish';
        if (lower === 'bearish' || lower === 'sell') return 'bearish';
        return 'neutral';
    }

    // Helper: Format time
    formatTime(timestamp) {
        if (!timestamp) return '--';
        const date = new Date(timestamp);
        return date.toLocaleTimeString('en-US', {
            hour: '2-digit',
            minute: '2-digit'
        });
    }

    // Show cell details in modal
    showCellDetails(cell, row) {
        const agentId = this.getAgentIdFromRow(row);
        if (agentId && this.data.agents[agentId]) {
            window.app?.showAgentDetails(agentId);
        }
    }

    // Get agent ID from row number
    getAgentIdFromRow(row) {
        const agentMap = {
            8: 'macro', 9: 'geopolitical', 10: 'commodities',
            11: 'sentiment', 12: 'fundamentals', 13: 'technical',
            14: 'alternative', 15: 'cross_asset', 16: 'event',
            17: 'risk', 18: 'aggregation', 19: 'learning'
        };
        return agentMap[row];
    }

    // Update data and re-render current view
    updateData(newData) {
        this.data = { ...this.data, ...newData };
        this.refreshView();
    }

    // Render Help view
    renderHelpView() {
        this.clear();
        this.currentView = 'help';

        this.setCell('A1', 'EQUITIES AI HELP', { type: 'header' });

        this.setCell('A3', 'KEYBOARD SHORTCUTS', { type: 'header' });
        this.setCell('A4', 'Ctrl+R', { type: 'label' });
        this.setCell('B4', 'Refresh data from server', { type: 'neutral' });
        this.setCell('A5', 'Ctrl+E', { type: 'label' });
        this.setCell('B5', 'Export current view to CSV', { type: 'neutral' });
        this.setCell('A6', 'Ctrl+A', { type: 'label' });
        this.setCell('B6', 'Trigger full analysis', { type: 'neutral' });
        this.setCell('A7', '1-9', { type: 'label' });
        this.setCell('B7', 'Switch between views', { type: 'neutral' });
        this.setCell('A8', 'Escape', { type: 'label' });
        this.setCell('B8', 'Close modal dialogs', { type: 'neutral' });

        this.setCell('A10', 'VIEWS', { type: 'header' });
        this.setCell('A11', '1. Dashboard', { type: 'label' });
        this.setCell('B11', 'Overview of all agents and market consensus', { type: 'neutral' });
        this.setCell('A12', '2. Agents', { type: 'label' });
        this.setCell('B12', 'Detailed view of all 12 AI agents', { type: 'neutral' });
        this.setCell('A13', '3. Portfolio', { type: 'label' });
        this.setCell('B13', 'Position tracking and P&L analysis', { type: 'neutral' });
        this.setCell('A14', '4. Performance', { type: 'label' });
        this.setCell('B14', 'Agent accuracy and calibration metrics', { type: 'neutral' });
        this.setCell('A15', '5. Signals', { type: 'label' });
        this.setCell('B15', 'Trade signals and recommendations', { type: 'neutral' });
        this.setCell('A16', '6. Risk', { type: 'label' });
        this.setCell('B16', 'Risk metrics, veto status, and alerts', { type: 'neutral' });
        this.setCell('A17', '7. Execution', { type: 'label' });
        this.setCell('B17', 'Execution orders and approval workflow', { type: 'neutral' });
        this.setCell('A18', '8. Settings', { type: 'label' });
        this.setCell('B18', 'Configuration and preferences', { type: 'neutral' });

        this.setCell('A20', 'AGENTS OVERVIEW', { type: 'header' });
        this.setCell('A21', 'Phase 1: Data', { type: 'label' });
        this.setCell('B21', 'Macro, Geopolitical, Commodities (parallel)', { type: 'neutral' });
        this.setCell('A22', 'Phase 2: Analysis', { type: 'label' });
        this.setCell('B22', 'Sentiment, Fundamentals, Technical (parallel)', { type: 'neutral' });
        this.setCell('A23', 'Phase 3: Alpha', { type: 'label' });
        this.setCell('B23', 'Alternative, Cross-Asset, Event (parallel)', { type: 'neutral' });
        this.setCell('A24', 'Phase 4: Risk', { type: 'label' });
        this.setCell('B24', 'Risk agent with veto power', { type: 'warning' });
        this.setCell('A25', 'Phase 5: Synthesis', { type: 'label' });
        this.setCell('B25', 'Aggregation engine combines all outputs', { type: 'neutral' });
        this.setCell('A26', 'Phase 6: Learn', { type: 'label' });
        this.setCell('B26', 'Learning agent updates weights', { type: 'neutral' });

        this.setCell('D10', 'CELL COLORS', { type: 'header' });
        this.setCell('D11', 'Green', { type: 'bullish' });
        this.setCell('E11', 'Bullish / Positive', { type: 'neutral' });
        this.setCell('D12', 'Red', { type: 'bearish' });
        this.setCell('E12', 'Bearish / Negative', { type: 'neutral' });
        this.setCell('D13', 'Gray', { type: 'neutral' });
        this.setCell('E13', 'Neutral / No Signal', { type: 'neutral' });
        this.setCell('D14', 'Yellow', { type: 'warning' });
        this.setCell('E14', 'Warning / Pending', { type: 'neutral' });

        this.setCell('D16', 'ABOUT', { type: 'header' });
        this.setCell('D17', 'Version:', { type: 'label' });
        this.setCell('E17', '1.0.0', { type: 'neutral' });
        this.setCell('D18', 'Backend:', { type: 'label' });
        this.setCell('E18', 'FastAPI + LangGraph', { type: 'neutral' });
        this.setCell('D19', 'AI Model:', { type: 'label' });
        this.setCell('E19', 'Claude Sonnet 4.5', { type: 'neutral' });
        this.setCell('D20', 'Data Sources:', { type: 'label' });
        this.setCell('E20', 'Alpha Vantage, FRED, News API', { type: 'neutral' });
    }

    // Refresh current view
    refreshView() {
        switch (this.currentView) {
            case 'dashboard':
                this.renderDashboard();
                break;
            case 'agents':
                this.renderAgentsView();
                break;
            case 'portfolio':
                this.renderPortfolioView();
                break;
            case 'performance':
                this.renderPerformanceView();
                break;
            case 'signals':
                this.renderSignalsView();
                break;
            case 'settings':
                this.renderSettingsView();
                break;
            case 'risk':
                this.renderRiskView();
                break;
            case 'execution':
                this.renderExecutionView();
                break;
            case 'help':
                this.renderHelpView();
                break;
        }

        // Update last update time
        const lastUpdate = document.getElementById('last-update');
        if (lastUpdate) {
            lastUpdate.textContent = `Last update: ${new Date().toLocaleTimeString()}`;
        }
    }

    // Switch view
    switchView(view) {
        this.currentView = view;
        this.refreshView();

        // Update menu bar active state
        document.querySelectorAll('.menu-bar div').forEach(item => {
            item.classList.remove('active');
            if (item.dataset.view === view) {
                item.classList.add('active');
            }
        });

        // Update formula bar
        const formulaDisplay = document.getElementById('formula-display');
        if (formulaDisplay) {
            const formulas = {
                'dashboard': '=AGENT_CONSENSUS("ALL", "OUTLOOK")',
                'agents': '=AGENT_DETAILS()',
                'portfolio': '=PORTFOLIO_VALUE()',
                'performance': '=PERFORMANCE_SUMMARY()',
                'signals': '=TRADE_SIGNALS()',
                'settings': '=SETTINGS_LIST()',
                'risk': '=RISK_METRICS()',
                'execution': '=EXECUTION_ORDERS()',
                'help': '=HELP()'
            };
            formulaDisplay.textContent = formulas[view] || '';
        }
    }

    // Set number format
    setNumberFormat(format) {
        this.numberFormat = format;
        this.refreshView();
    }

    // Adjust decimals
    adjustDecimals(delta) {
        this.decimals = Math.max(0, Math.min(6, this.decimals + delta));
        this.refreshView();
    }

    // Toggle auto-refresh
    toggleAutoRefresh() {
        this.autoRefresh = !this.autoRefresh;
        return this.autoRefresh;
    }

    // Export current view as CSV
    exportToCSV() {
        let csv = '';

        for (let row = 1; row <= this.rows; row++) {
            const rowData = [];
            for (let col = 0; col < this.cols; col++) {
                const cellId = `${this.columnHeaders[col]}${row}`;
                const cell = this.cells[cellId];
                const value = cell?.value || '';
                // Escape quotes and wrap in quotes if contains comma
                const escaped = value.includes(',') || value.includes('"')
                    ? `"${value.replace(/"/g, '""')}"`
                    : value;
                rowData.push(escaped);
            }
            csv += rowData.join(',') + '\n';
        }

        return csv;
    }
}

// Export for module usage
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { SpreadsheetEngine };
}
