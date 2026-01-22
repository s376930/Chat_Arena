/**
 * Main application controller for Chat Arena
 */
const App = {
    sessionId: null,

    /**
     * Initialize the application
     */
    async init() {
        // Initialize UI
        UI.init();

        // Initialize speech recognition
        Speech.init();

        // Load and show consent form
        await UI.loadConsent();

        // Setup consent button handler
        UI.elements.consentBtn.addEventListener('click', () => this.handleConsent());

        // Setup send button handler
        UI.elements.sendBtn.addEventListener('click', () => this.handleSend());

        // Setup speech input change handler
        UI.elements.speechInput.addEventListener('input', () => UI.updateSendButton());

        // Setup reassign button handler
        UI.elements.reassignBtn.addEventListener('click', () => this.handleReassign());

        // Setup WebSocket event handlers
        this.setupWebSocketHandlers();
    },

    /**
     * Setup WebSocket event handlers
     */
    setupWebSocketHandlers() {
        wsClient.on('connected', () => {
            console.log('Connected to server');
            UI.setConnectionStatus(true);
        });

        wsClient.on('disconnected', () => {
            console.log('Disconnected from server');
            UI.setConnectionStatus(false);
        });

        wsClient.on('reconnectFailed', () => {
            UI.showError('Connection lost. Please refresh the page.');
        });

        wsClient.on('waiting', (data) => {
            console.log('Waiting for partner, position:', data.position);
            UI.showWaiting(data.position);
        });

        wsClient.on('paired', (data) => {
            console.log('Paired!', data);
            this.sessionId = data.session_id;
            UI.showChat(data.topic, data.task);
        });

        wsClient.on('partnerMessage', (data) => {
            console.log('Partner message:', data);
            UI.addMessage(data.content, false, data.timestamp);
        });

        wsClient.on('messageSent', (data) => {
            console.log('Message sent:', data);
            const { speech } = UI.getInputValues();
            UI.addMessage(speech, true, data.timestamp);
            UI.resetInputs();
        });

        wsClient.on('partnerLeft', () => {
            console.log('Partner left');
            UI.showPartnerLeft();
            this.sessionId = null;
        });

        wsClient.on('serverError', (data) => {
            console.error('Server error:', data.message);
            UI.showError(data.message);
        });
    },

    /**
     * Handle consent acceptance
     */
    handleConsent() {
        // Hide consent, show app
        UI.hideConsent();

        // Connect to WebSocket
        wsClient.connect();

        // Wait for connection, then join
        wsClient.on('connected', () => {
            wsClient.join();
        });

        // If already connected (reconnection), join immediately
        if (wsClient.isConnected()) {
            wsClient.join();
        }
    },

    /**
     * Handle sending a message
     */
    handleSend() {
        const { think, speech } = UI.getInputValues();

        if (think.length < 10) {
            UI.showError('Please write at least 10 characters in the Think field.');
            return;
        }

        if (!speech.trim()) {
            UI.showError('Please write something in the Speech field.');
            return;
        }

        wsClient.sendMessage(think, speech);
    },

    /**
     * Handle reassign request
     */
    handleReassign() {
        if (confirm('Are you sure you want to find a new partner? This will end your current conversation.')) {
            wsClient.requestReassign();
            this.sessionId = null;
        }
    }
};

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    App.init();
});

// Handle page unload
window.addEventListener('beforeunload', () => {
    if (wsClient.isConnected()) {
        wsClient.disconnect();
    }
});
