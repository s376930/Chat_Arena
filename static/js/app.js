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

        // Setup return from inactivity button handler
        UI.elements.returnBtn.addEventListener('click', () => this.handleReturnFromInactivity());

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
            UI.showError('Tilkoblingen ble brutt. Vennligst oppdater siden.');
        });

        wsClient.on('waiting', (data) => {
            console.log('Waiting for partner, position:', data.position);
            UI.showWaiting(data.position);
        });

        wsClient.on('paired', (data) => {
            console.log('Paired!', data);
            this.sessionId = data.session_id;
            UI.showChat(data.topic, data.task, data.max_time);
        });

        wsClient.on('partnerMessage', (data) => {
            console.log('Partner message:', data);
            UI.addMessage(data.content, false, data.timestamp);
            // Reset inactivity timer on partner message
            if (data.max_time) {
                UI.startTimer(data.max_time);
            }
        });

        wsClient.on('messageSent', (data) => {
            console.log('Message sent:', data);
            const { speech } = UI.getInputValues();
            UI.addMessage(speech, true, data.timestamp);
            UI.resetInputs();
            // Reset inactivity timer on own message
            if (data.max_time) {
                UI.startTimer(data.max_time);
            }
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

        wsClient.on('inactivityKick', () => {
            console.log('Kicked due to inactivity');
            this.sessionId = null;
            UI.showInactivityScreen();
        });

        wsClient.on('conversationEnded', (data) => {
            console.log('Conversation ended:', data.reason);
            this.sessionId = null;
            if (data.reason === 'time_up') {
                UI.addSystemMessage('Tiden er ute! Samtalen er avsluttet. Du blir n\u00e5 satt i k\u00f8 igjen.');
                UI.stopTimer();
                UI.elements.sendBtn.disabled = true;
                UI.elements.speechInput.disabled = true;
                UI.elements.speechMicBtn.disabled = true;
            }
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

        if (!speech.trim()) {
            UI.showError('Vennligst skriv noe i feltet.');
            return;
        }

        wsClient.sendMessage(think, speech);
    },

    /**
     * Handle reassign request
     */
    handleReassign() {
        if (confirm('Er du sikker på at du vil finne en ny partner? Dette avslutter den nåværende samtalen.')) {
            wsClient.requestReassign();
            this.sessionId = null;
        }
    },

    /**
     * Handle return from inactivity screen
     */
    handleReturnFromInactivity() {
        // Hide inactivity screen
        UI.hideInactivityScreen();

        // Rejoin the queue
        wsClient.join();
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
