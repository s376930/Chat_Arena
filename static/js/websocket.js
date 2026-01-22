/**
 * WebSocket client handler for Chat Arena
 */
class WebSocketClient {
    constructor() {
        this.socket = null;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.reconnectDelay = 1000;
        this.handlers = {};
    }

    /**
     * Connect to the WebSocket server
     */
    connect() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws`;

        this.socket = new WebSocket(wsUrl);

        this.socket.onopen = () => {
            console.log('WebSocket connected');
            this.reconnectAttempts = 0;
            this.trigger('connected');
        };

        this.socket.onclose = (event) => {
            console.log('WebSocket closed:', event.code, event.reason);
            this.trigger('disconnected');
            this.attemptReconnect();
        };

        this.socket.onerror = (error) => {
            console.error('WebSocket error:', error);
            this.trigger('error', error);
        };

        this.socket.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                this.handleMessage(data);
            } catch (e) {
                console.error('Failed to parse message:', e);
            }
        };
    }

    /**
     * Attempt to reconnect after disconnection
     */
    attemptReconnect() {
        if (this.reconnectAttempts >= this.maxReconnectAttempts) {
            console.log('Max reconnection attempts reached');
            this.trigger('reconnectFailed');
            return;
        }

        this.reconnectAttempts++;
        const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1);

        console.log(`Attempting to reconnect in ${delay}ms (attempt ${this.reconnectAttempts})`);

        setTimeout(() => {
            if (!this.isConnected()) {
                this.connect();
            }
        }, delay);
    }

    /**
     * Handle incoming messages from server
     */
    handleMessage(data) {
        const type = data.type;
        console.log('Received message:', type, data);

        switch (type) {
            case 'waiting':
                this.trigger('waiting', data);
                break;
            case 'paired':
                this.trigger('paired', data);
                break;
            case 'partner_message':
                this.trigger('partnerMessage', data);
                break;
            case 'message_sent':
                this.trigger('messageSent', data);
                break;
            case 'partner_left':
                this.trigger('partnerLeft', data);
                break;
            case 'error':
                this.trigger('serverError', data);
                break;
            default:
                console.log('Unknown message type:', type);
        }
    }

    /**
     * Send a message to the server
     */
    send(data) {
        if (this.isConnected()) {
            this.socket.send(JSON.stringify(data));
        } else {
            console.error('Cannot send message: WebSocket not connected');
        }
    }

    /**
     * Send join message (after consent)
     */
    join() {
        this.send({ type: 'join', consent: true });
    }

    /**
     * Send a chat message
     */
    sendMessage(think, speech) {
        this.send({
            type: 'message',
            think: think,
            speech: speech
        });
    }

    /**
     * Request reassignment to a new partner
     */
    requestReassign() {
        this.send({ type: 'reassign' });
    }

    /**
     * Send disconnect message
     */
    disconnect() {
        this.send({ type: 'disconnect' });
        if (this.socket) {
            this.socket.close();
        }
    }

    /**
     * Check if WebSocket is connected
     */
    isConnected() {
        return this.socket && this.socket.readyState === WebSocket.OPEN;
    }

    /**
     * Register an event handler
     */
    on(event, handler) {
        if (!this.handlers[event]) {
            this.handlers[event] = [];
        }
        this.handlers[event].push(handler);
    }

    /**
     * Remove an event handler
     */
    off(event, handler) {
        if (this.handlers[event]) {
            this.handlers[event] = this.handlers[event].filter(h => h !== handler);
        }
    }

    /**
     * Trigger an event
     */
    trigger(event, data) {
        if (this.handlers[event]) {
            this.handlers[event].forEach(handler => handler(data));
        }
    }
}

// Export global instance
window.wsClient = new WebSocketClient();
