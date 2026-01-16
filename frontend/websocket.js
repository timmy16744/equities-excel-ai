/**
 * Equities AI - WebSocket Client
 * Handles real-time updates from the backend
 */

class EquitiesWebSocket {
    constructor(baseUrl = 'ws://localhost:8000') {
        this.baseUrl = baseUrl;
        this.connections = {};
        this.listeners = {};
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 10;
        this.reconnectDelay = 1000;
        this.pingInterval = 30000;
        this.pingTimers = {};
    }

    // Connect to a specific WebSocket channel
    connect(channel = 'updates') {
        if (this.connections[channel]?.readyState === WebSocket.OPEN) {
            console.log(`Already connected to ${channel}`);
            return;
        }

        const wsUrl = `${this.baseUrl}/ws/${channel}`;
        console.log(`Connecting to WebSocket: ${wsUrl}`);

        try {
            const ws = new WebSocket(wsUrl);

            ws.onopen = () => {
                console.log(`WebSocket connected: ${channel}`);
                this.reconnectAttempts = 0;
                this.updateStatus('connected');
                this.startPing(channel);
                this.emit('connected', { channel });
            };

            ws.onmessage = (event) => {
                try {
                    const message = JSON.parse(event.data);
                    this.handleMessage(channel, message);
                } catch (error) {
                    console.error('Failed to parse WebSocket message:', error);
                }
            };

            ws.onerror = (error) => {
                console.error(`WebSocket error on ${channel}:`, error);
                this.emit('error', { channel, error });
            };

            ws.onclose = (event) => {
                console.log(`WebSocket closed: ${channel}`, event.code, event.reason);
                this.stopPing(channel);
                this.updateStatus('disconnected');
                this.emit('disconnected', { channel, code: event.code, reason: event.reason });

                // Attempt reconnection
                if (event.code !== 1000) { // Not a normal close
                    this.attemptReconnect(channel);
                }
            };

            this.connections[channel] = ws;
        } catch (error) {
            console.error(`Failed to create WebSocket connection: ${error}`);
            this.updateStatus('disconnected');
        }
    }

    // Disconnect from a channel
    disconnect(channel = 'updates') {
        const ws = this.connections[channel];
        if (ws) {
            this.stopPing(channel);
            ws.close(1000, 'Client requested disconnect');
            delete this.connections[channel];
        }
    }

    // Disconnect all channels
    disconnectAll() {
        Object.keys(this.connections).forEach(channel => {
            this.disconnect(channel);
        });
    }

    // Attempt reconnection with exponential backoff
    attemptReconnect(channel) {
        if (this.reconnectAttempts >= this.maxReconnectAttempts) {
            console.error(`Max reconnect attempts reached for ${channel}`);
            this.emit('reconnect_failed', { channel });
            return;
        }

        this.reconnectAttempts++;
        const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1);

        console.log(`Reconnecting to ${channel} in ${delay}ms (attempt ${this.reconnectAttempts})`);
        this.updateStatus('connecting');

        setTimeout(() => {
            this.connect(channel);
        }, delay);
    }

    // Send a message to a channel
    send(channel, message) {
        const ws = this.connections[channel];
        if (ws?.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify(message));
        } else {
            console.warn(`Cannot send to ${channel}: not connected`);
        }
    }

    // Handle incoming messages
    handleMessage(channel, message) {
        const { type, data, timestamp } = message;

        // Emit typed events
        switch (type) {
            case 'agent_update':
                this.emit('agent_update', data);
                break;

            case 'insight_update':
                this.emit('insight_update', data);
                break;

            case 'order_executed':
                this.emit('order_executed', data);
                break;

            case 'settings_changed':
                this.emit('settings_changed', data);
                break;

            case 'workflow_status':
                this.emit('workflow_status', data);
                break;

            case 'risk_alert':
                this.emit('risk_alert', data);
                break;

            case 'market_update':
                this.emit('market_update', data);
                break;

            case 'pong':
                // Keep-alive response
                break;

            default:
                this.emit('message', { channel, type, data, timestamp });
        }

        // Always emit raw message for debugging
        this.emit('raw', message);
    }

    // Ping to keep connection alive
    startPing(channel) {
        this.pingTimers[channel] = setInterval(() => {
            this.send(channel, { type: 'ping' });
        }, this.pingInterval);
    }

    stopPing(channel) {
        if (this.pingTimers[channel]) {
            clearInterval(this.pingTimers[channel]);
            delete this.pingTimers[channel];
        }
    }

    // Event listener management
    on(event, callback) {
        if (!this.listeners[event]) {
            this.listeners[event] = [];
        }
        this.listeners[event].push(callback);
        return () => this.off(event, callback);
    }

    off(event, callback) {
        if (this.listeners[event]) {
            this.listeners[event] = this.listeners[event].filter(cb => cb !== callback);
        }
    }

    emit(event, data) {
        if (this.listeners[event]) {
            this.listeners[event].forEach(callback => {
                try {
                    callback(data);
                } catch (error) {
                    console.error(`Error in ${event} listener:`, error);
                }
            });
        }
    }

    // Update connection status in UI
    updateStatus(status) {
        const statusElement = document.getElementById('connection-status');
        if (statusElement) {
            statusElement.className = `status-indicator ${status}`;
            statusElement.textContent = status.charAt(0).toUpperCase() + status.slice(1);
        }
    }

    // Check if connected to a channel
    isConnected(channel = 'updates') {
        return this.connections[channel]?.readyState === WebSocket.OPEN;
    }

    // Get connection state
    getState(channel = 'updates') {
        const ws = this.connections[channel];
        if (!ws) return 'disconnected';

        switch (ws.readyState) {
            case WebSocket.CONNECTING:
                return 'connecting';
            case WebSocket.OPEN:
                return 'connected';
            case WebSocket.CLOSING:
                return 'closing';
            case WebSocket.CLOSED:
                return 'disconnected';
            default:
                return 'unknown';
        }
    }
}

// Create global WebSocket instance
const ws = new EquitiesWebSocket();

// Export for module usage
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { EquitiesWebSocket, ws };
}
