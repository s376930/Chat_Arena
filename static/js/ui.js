/**
 * UI module for Chat Arena
 */
const UI = {
    // DOM element references
    elements: {},

    /**
     * Initialize UI elements
     */
    init() {
        // Modals
        this.elements.consentModal = document.getElementById('consent-modal');
        this.elements.instructionsModal = document.getElementById('instructions-modal');
        this.elements.inactivityModal = document.getElementById('inactivity-modal');
        this.elements.returnBtn = document.getElementById('return-btn');
        this.elements.consentTitle = document.getElementById('consent-title');
        this.elements.consentText = document.getElementById('consent-text');
        this.elements.consentCheckboxes = document.getElementById('consent-checkboxes');
        this.elements.consentBtn = document.getElementById('consent-btn');
        this.elements.closeInstructionsBtn = document.getElementById('close-instructions-btn');

        // App container
        this.elements.app = document.getElementById('app');

        // Header
        this.elements.connectionStatus = document.getElementById('connection-status');
        this.elements.topicBanner = document.getElementById('topic-banner');
        this.elements.topicText = document.getElementById('topic-text');
        this.elements.themeToggle = document.getElementById('theme-toggle');

        // Task bar
        this.elements.taskBar = document.getElementById('task-bar');
        this.elements.taskText = document.getElementById('task-text');

        // Screens
        this.elements.waitingScreen = document.getElementById('waiting-screen');
        this.elements.queuePosition = document.getElementById('queue-position');
        this.elements.chatContainer = document.getElementById('chat-container');
        this.elements.chatMessages = document.getElementById('chat-messages');

        // Inputs
        this.elements.thinkInput = document.getElementById('think-input');
        this.elements.speechInput = document.getElementById('speech-input');
        this.elements.thinkCharCount = document.getElementById('think-char-count');
        this.elements.thinkMicBtn = document.getElementById('think-mic-btn');
        this.elements.speechMicBtn = document.getElementById('speech-mic-btn');
        this.elements.sendBtn = document.getElementById('send-btn');

        // Footer
        this.elements.reassignBtn = document.getElementById('reassign-btn');
        this.elements.instructionsBtn = document.getElementById('instructions-btn');

        // Initialize theme
        this.initTheme();

        // Setup event listeners
        this.setupEventListeners();
    },

    /**
     * Setup UI event listeners
     */
    setupEventListeners() {
        // Theme toggle
        this.elements.themeToggle.addEventListener('click', () => this.toggleTheme());

        // Instructions modal
        this.elements.instructionsBtn.addEventListener('click', () => {
            this.elements.instructionsModal.classList.remove('hidden');
        });

        this.elements.closeInstructionsBtn.addEventListener('click', () => {
            this.elements.instructionsModal.classList.add('hidden');
        });

        // Think input character counting
        this.elements.thinkInput.addEventListener('input', () => {
            this.updateThinkCharCount();
        });

        // Keyboard shortcut for sending (Ctrl+Enter)
        document.addEventListener('keydown', (e) => {
            if (e.ctrlKey && e.key === 'Enter') {
                if (!this.elements.sendBtn.disabled) {
                    this.elements.sendBtn.click();
                }
            }
        });
    },

    /**
     * Initialize theme from localStorage or system preference
     */
    initTheme() {
        const savedTheme = localStorage.getItem('theme');
        if (savedTheme) {
            document.documentElement.setAttribute('data-theme', savedTheme);
        } else if (window.matchMedia('(prefers-color-scheme: dark)').matches) {
            document.documentElement.setAttribute('data-theme', 'dark');
        } else {
            document.documentElement.setAttribute('data-theme', 'light');
        }
        this.updateThemeIcon();
    },

    /**
     * Toggle between light and dark theme
     */
    toggleTheme() {
        const currentTheme = document.documentElement.getAttribute('data-theme');
        const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
        document.documentElement.setAttribute('data-theme', newTheme);
        localStorage.setItem('theme', newTheme);
        this.updateThemeIcon();
    },

    /**
     * Update theme toggle icon
     */
    updateThemeIcon() {
        const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
        document.querySelector('.theme-icon-light').classList.toggle('hidden', isDark);
        document.querySelector('.theme-icon-dark').classList.toggle('hidden', !isDark);
    },

    /**
     * Load and display consent form
     */
    async loadConsent() {
        try {
            const response = await fetch('/api/consent');
            const consent = await response.json();

            this.elements.consentTitle.textContent = consent.title;
            this.elements.consentText.textContent = consent.content;

            // Create checkboxes
            this.elements.consentCheckboxes.innerHTML = '';
            consent.checkboxes.forEach((text, index) => {
                const label = document.createElement('label');
                const checkbox = document.createElement('input');
                checkbox.type = 'checkbox';
                checkbox.id = `consent-check-${index}`;
                checkbox.addEventListener('change', () => this.updateConsentButton());
                label.appendChild(checkbox);
                label.appendChild(document.createTextNode(text));
                this.elements.consentCheckboxes.appendChild(label);
            });
        } catch (error) {
            console.error('Failed to load consent:', error);
            this.elements.consentText.textContent = 'Failed to load consent form. Please refresh the page.';
        }
    },

    /**
     * Update consent button state based on checkbox status
     */
    updateConsentButton() {
        const checkboxes = this.elements.consentCheckboxes.querySelectorAll('input[type="checkbox"]');
        const allChecked = Array.from(checkboxes).every(cb => cb.checked);
        this.elements.consentBtn.disabled = !allChecked;
    },

    /**
     * Hide consent modal and show app
     */
    hideConsent() {
        this.elements.consentModal.classList.add('hidden');
        this.elements.app.classList.remove('hidden');
    },

    /**
     * Update connection status indicator
     */
    setConnectionStatus(connected) {
        this.elements.connectionStatus.classList.toggle('connected', connected);
        this.elements.connectionStatus.classList.toggle('disconnected', !connected);
        this.elements.connectionStatus.title = connected ? 'Connected' : 'Disconnected';
    },

    /**
     * Show waiting screen
     */
    showWaiting(position) {
        this.elements.waitingScreen.classList.remove('hidden');
        this.elements.chatContainer.classList.add('hidden');
        this.elements.taskBar.classList.add('hidden');
        this.elements.topicBanner.classList.add('hidden');
        this.elements.queuePosition.textContent = position;
        this.elements.reassignBtn.disabled = true;
    },

    /**
     * Update queue position
     */
    updateQueuePosition(position) {
        this.elements.queuePosition.textContent = position;
    },

    /**
     * Show chat interface after pairing
     */
    showChat(topic, task) {
        this.elements.waitingScreen.classList.add('hidden');
        this.elements.chatContainer.classList.remove('hidden');
        this.elements.taskBar.classList.remove('hidden');
        this.elements.topicBanner.classList.remove('hidden');

        this.elements.topicText.textContent = topic;
        this.elements.topicBanner.setAttribute('data-full-topic', topic);
        this.elements.topicBanner.setAttribute('title', topic);
        this.elements.taskText.textContent = task;

        this.elements.reassignBtn.disabled = false;

        // Clear previous messages
        this.elements.chatMessages.innerHTML = '';

        // Add system message
        this.addSystemMessage('You have been paired with a partner. Start the conversation!');

        // Reset inputs
        this.resetInputs();
    },

    /**
     * Reset input fields
     */
    resetInputs() {
        this.elements.thinkInput.value = '';
        this.elements.speechInput.value = '';
        this.elements.speechInput.disabled = true;
        this.elements.speechMicBtn.disabled = true;
        this.elements.sendBtn.disabled = true;
        this.updateThinkCharCount();
    },

    /**
     * Update think character count and enable/disable speech input
     */
    updateThinkCharCount() {
        const count = this.elements.thinkInput.value.length;
        this.elements.thinkCharCount.textContent = count;

        const isValid = count >= 10;
        this.elements.thinkCharCount.parentElement.classList.toggle('valid', isValid);
        this.elements.speechInput.disabled = !isValid;
        this.elements.speechMicBtn.disabled = !isValid;

        this.updateSendButton();
    },

    /**
     * Update send button state
     */
    updateSendButton() {
        const thinkValid = this.elements.thinkInput.value.length >= 10;
        const speechValid = this.elements.speechInput.value.trim().length > 0;
        this.elements.sendBtn.disabled = !(thinkValid && speechValid);
    },

    /**
     * Add a system message to chat
     */
    addSystemMessage(text) {
        const div = document.createElement('div');
        div.className = 'system-message';
        div.innerHTML = `<span>${text}</span>`;
        this.elements.chatMessages.appendChild(div);
        this.scrollToBottom();
    },

    /**
     * Add a chat message to the display
     */
    addMessage(content, isSelf, timestamp) {
        const div = document.createElement('div');
        div.className = `message ${isSelf ? 'self' : 'partner'}`;

        const time = new Date(timestamp).toLocaleTimeString([], {
            hour: '2-digit',
            minute: '2-digit'
        });

        div.innerHTML = `
            <div class="message-content">${this.escapeHtml(content)}</div>
            <div class="message-time">${time}</div>
        `;

        this.elements.chatMessages.appendChild(div);
        this.scrollToBottom();
    },

    /**
     * Scroll chat to bottom
     */
    scrollToBottom() {
        this.elements.chatMessages.scrollTop = this.elements.chatMessages.scrollHeight;
    },

    /**
     * Escape HTML to prevent XSS
     */
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    },

    /**
     * Show partner left message
     */
    showPartnerLeft() {
        this.addSystemMessage('Your partner has left the conversation.');
        this.elements.sendBtn.disabled = true;
        this.elements.speechInput.disabled = true;
        this.elements.speechMicBtn.disabled = true;
    },

    /**
     * Get input values
     */
    getInputValues() {
        return {
            think: this.elements.thinkInput.value,
            speech: this.elements.speechInput.value
        };
    },

    /**
     * Show error message
     */
    showError(message) {
        alert(message); // Simple alert for now
    },

    /**
     * Show inactivity screen
     */
    showInactivityScreen() {
        // Hide everything else
        this.elements.waitingScreen.classList.add('hidden');
        this.elements.chatContainer.classList.add('hidden');
        this.elements.taskBar.classList.add('hidden');
        this.elements.topicBanner.classList.add('hidden');
        this.elements.app.classList.add('hidden');

        // Show inactivity modal
        this.elements.inactivityModal.classList.remove('hidden');
    },

    /**
     * Hide inactivity screen and return to app
     */
    hideInactivityScreen() {
        this.elements.inactivityModal.classList.add('hidden');
        this.elements.app.classList.remove('hidden');
    }
};

// Export
window.UI = UI;
