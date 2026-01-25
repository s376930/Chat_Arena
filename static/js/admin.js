/**
 * Admin page JavaScript for Chat Arena
 * Password-protected admin panel with file and conversation management
 */
const Admin = {
    // Authentication state
    password: null,

    // Current editing state
    editingType: null, // 'topic' or 'task'
    editingId: null,
    editingFilename: null,
    currentConversationId: null,

    /**
     * Initialize admin page
     */
    init() {
        this.setupLoginHandler();
        this.setupLogoutHandler();
        this.setupTabHandlers();

        // Check if already authenticated (session storage)
        const savedPassword = sessionStorage.getItem('adminPassword');
        if (savedPassword) {
            this.password = savedPassword;
            this.verifyPassword().then(valid => {
                if (valid) {
                    this.showAdminPanel();
                } else {
                    sessionStorage.removeItem('adminPassword');
                    this.password = null;
                }
            });
        }
    },

    /**
     * Setup login form handler
     */
    setupLoginHandler() {
        const form = document.getElementById('login-form');
        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            const passwordInput = document.getElementById('password-input');
            const password = passwordInput.value;

            this.password = password;
            const valid = await this.verifyPassword();

            if (valid) {
                sessionStorage.setItem('adminPassword', password);
                document.getElementById('login-error').classList.add('hidden');
                this.showAdminPanel();
            } else {
                document.getElementById('login-error').classList.remove('hidden');
                passwordInput.value = '';
                passwordInput.focus();
            }
        });
    },

    /**
     * Setup logout handler
     */
    setupLogoutHandler() {
        document.getElementById('logout-btn').addEventListener('click', () => {
            this.logout();
        });
    },

    /**
     * Verify password with server
     */
    async verifyPassword() {
        try {
            const response = await fetch('/api/admin/auth', {
                method: 'POST',
                headers: {
                    'X-Admin-Password': this.password
                }
            });
            return response.ok;
        } catch (e) {
            console.error('Auth failed:', e);
            return false;
        }
    },

    /**
     * Logout
     */
    logout() {
        this.password = null;
        sessionStorage.removeItem('adminPassword');
        document.getElementById('admin-panel').classList.add('hidden');
        document.getElementById('login-screen').classList.remove('hidden');
        document.getElementById('password-input').value = '';
        document.getElementById('password-input').focus();
    },

    /**
     * Show admin panel and load data
     */
    showAdminPanel() {
        document.getElementById('login-screen').classList.add('hidden');
        document.getElementById('admin-panel').classList.remove('hidden');
        this.setupEventListeners();
        this.loadAllData();
    },

    /**
     * Setup tab handlers
     */
    setupTabHandlers() {
        document.querySelectorAll('.tab').forEach(tab => {
            tab.addEventListener('click', () => {
                // Update active tab
                document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
                tab.classList.add('active');

                // Show corresponding content
                const tabName = tab.dataset.tab;
                document.querySelectorAll('.tab-content').forEach(content => {
                    content.classList.add('hidden');
                });
                document.getElementById(`${tabName}-tab`).classList.remove('hidden');
            });
        });
    },

    /**
     * Setup event listeners
     */
    setupEventListeners() {
        // Add buttons
        document.getElementById('add-topic-btn').addEventListener('click', () => this.openAddModal('topic'));
        document.getElementById('add-task-btn').addEventListener('click', () => this.openAddModal('task'));
        document.getElementById('add-checkbox-btn').addEventListener('click', () => this.addCheckboxRow());

        // Save consent
        document.getElementById('save-consent-btn').addEventListener('click', () => this.saveConsent());
        document.getElementById('preview-consent-btn').addEventListener('click', () => this.previewConsent());

        // Modal buttons
        document.getElementById('edit-cancel-btn').addEventListener('click', () => this.closeEditModal());
        document.getElementById('edit-save-btn').addEventListener('click', () => this.saveEdit());
        document.getElementById('preview-close-btn').addEventListener('click', () => this.closePreviewModal());

        // File editor modal
        document.getElementById('file-editor-cancel').addEventListener('click', () => this.closeFileEditor());
        document.getElementById('file-editor-save').addEventListener('click', () => this.saveFileEdit());
        document.getElementById('file-editor-format').addEventListener('click', () => this.formatJSON());

        // Conversation modal
        document.getElementById('conversation-close').addEventListener('click', () => this.closeConversationModal());
        document.getElementById('conversation-download').addEventListener('click', () => this.downloadCurrentConversation());

        // Download all conversations
        document.getElementById('download-all-conversations').addEventListener('click', () => this.downloadAllConversations());

        // File upload
        document.getElementById('upload-file-input').addEventListener('change', (e) => this.handleFileUpload(e));

        // Close modals on outside click
        document.querySelectorAll('.modal').forEach(modal => {
            modal.addEventListener('click', (e) => {
                if (e.target === modal) {
                    modal.classList.add('hidden');
                }
            });
        });
    },

    /**
     * Make authenticated API request
     */
    async apiRequest(url, options = {}) {
        const headers = {
            ...options.headers,
            'X-Admin-Password': this.password
        };
        return fetch(url, { ...options, headers });
    },

    /**
     * Load all data
     */
    async loadAllData() {
        await Promise.all([
            this.loadDataFiles(),
            this.loadConversations(),
            this.loadTopics(),
            this.loadTasks(),
            this.loadConsent()
        ]);
    },

    // ==================== Data Files ====================

    /**
     * Load data files list
     */
    async loadDataFiles() {
        try {
            const response = await this.apiRequest('/api/admin/data-files');
            if (!response.ok) throw new Error('Failed to load files');
            const files = await response.json();
            this.renderDataFiles(files);
        } catch (e) {
            console.error('Failed to load data files:', e);
            document.getElementById('data-files-list').innerHTML = '<div class="empty-state">Failed to load files</div>';
        }
    },

    /**
     * Render data files list
     */
    renderDataFiles(files) {
        const container = document.getElementById('data-files-list');

        if (files.length === 0) {
            container.innerHTML = '<div class="empty-state">No data files found</div>';
            return;
        }

        container.innerHTML = files.map(file => `
            <div class="item-row file-row">
                <div class="item-content">
                    <div class="file-name">${this.escapeHtml(file.name)}</div>
                    <div class="file-meta">
                        <span class="file-size">${this.formatFileSize(file.size)}</span>
                        <span class="file-modified">Modified: ${this.formatDate(file.modified)}</span>
                    </div>
                </div>
                <div class="item-actions">
                    <button class="btn btn-secondary btn-small" onclick="Admin.viewFile('${this.escapeAttr(file.name)}')">View</button>
                    <button class="btn btn-secondary btn-small" onclick="Admin.editFile('${this.escapeAttr(file.name)}')">Edit</button>
                    <button class="btn btn-secondary btn-small" onclick="Admin.downloadFile('${this.escapeAttr(file.name)}')">Download</button>
                    <button class="btn btn-danger btn-small" onclick="Admin.deleteFile('${this.escapeAttr(file.name)}')">Delete</button>
                </div>
            </div>
        `).join('');
    },

    /**
     * View file content (read-only)
     */
    async viewFile(filename) {
        try {
            const response = await this.apiRequest(`/api/admin/data-files/${encodeURIComponent(filename)}`);
            if (!response.ok) throw new Error('Failed to load file');
            const data = await response.json();

            document.getElementById('file-editor-title').textContent = `View: ${filename}`;
            const editor = document.getElementById('file-editor-content');
            try {
                editor.value = JSON.stringify(JSON.parse(data.content), null, 2);
            } catch {
                editor.value = data.content;
            }
            editor.readOnly = true;
            document.getElementById('file-editor-save').classList.add('hidden');
            document.getElementById('file-editor-format').classList.add('hidden');
            document.getElementById('file-editor-modal').classList.remove('hidden');
            this.editingFilename = null;
        } catch (e) {
            console.error('Failed to view file:', e);
            this.showToast('Failed to load file', 'error');
        }
    },

    /**
     * Edit file content
     */
    async editFile(filename) {
        try {
            const response = await this.apiRequest(`/api/admin/data-files/${encodeURIComponent(filename)}`);
            if (!response.ok) throw new Error('Failed to load file');
            const data = await response.json();

            document.getElementById('file-editor-title').textContent = `Edit: ${filename}`;
            const editor = document.getElementById('file-editor-content');
            try {
                editor.value = JSON.stringify(JSON.parse(data.content), null, 2);
            } catch {
                editor.value = data.content;
            }
            editor.readOnly = false;
            document.getElementById('file-editor-save').classList.remove('hidden');
            document.getElementById('file-editor-format').classList.remove('hidden');
            document.getElementById('file-editor-modal').classList.remove('hidden');
            this.editingFilename = filename;
        } catch (e) {
            console.error('Failed to edit file:', e);
            this.showToast('Failed to load file', 'error');
        }
    },

    /**
     * Close file editor
     */
    closeFileEditor() {
        document.getElementById('file-editor-modal').classList.add('hidden');
        this.editingFilename = null;
    },

    /**
     * Format JSON in editor
     */
    formatJSON() {
        const editor = document.getElementById('file-editor-content');
        try {
            const parsed = JSON.parse(editor.value);
            editor.value = JSON.stringify(parsed, null, 2);
        } catch (e) {
            this.showToast('Invalid JSON format', 'error');
        }
    },

    /**
     * Save file edit
     */
    async saveFileEdit() {
        if (!this.editingFilename) return;

        const content = document.getElementById('file-editor-content').value;

        try {
            const response = await this.apiRequest(`/api/admin/data-files/${encodeURIComponent(this.editingFilename)}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ content })
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || 'Failed to save');
            }

            this.showToast('File saved successfully', 'success');
            this.closeFileEditor();
            this.loadDataFiles();
        } catch (e) {
            console.error('Failed to save file:', e);
            this.showToast(e.message || 'Failed to save file', 'error');
        }
    },

    /**
     * Download file
     */
    async downloadFile(filename) {
        try {
            const response = await this.apiRequest(`/api/admin/data-files/${encodeURIComponent(filename)}/download`);
            if (!response.ok) throw new Error('Failed to download');

            const blob = await response.blob();
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = filename;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
        } catch (e) {
            console.error('Failed to download file:', e);
            this.showToast('Failed to download file', 'error');
        }
    },

    /**
     * Delete file
     */
    async deleteFile(filename) {
        if (!confirm(`Are you sure you want to delete "${filename}"? This cannot be undone.`)) return;

        try {
            const response = await this.apiRequest(`/api/admin/data-files/${encodeURIComponent(filename)}`, {
                method: 'DELETE'
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || 'Failed to delete');
            }

            this.showToast('File deleted', 'success');
            this.loadDataFiles();
        } catch (e) {
            console.error('Failed to delete file:', e);
            this.showToast(e.message || 'Failed to delete file', 'error');
        }
    },

    /**
     * Handle file upload
     */
    async handleFileUpload(event) {
        const file = event.target.files[0];
        if (!file) return;

        if (!file.name.endsWith('.json')) {
            this.showToast('Only JSON files are allowed', 'error');
            return;
        }

        const formData = new FormData();
        formData.append('file', file);

        try {
            const response = await fetch('/api/admin/data-files/upload', {
                method: 'POST',
                headers: {
                    'X-Admin-Password': this.password
                },
                body: formData
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || 'Failed to upload');
            }

            this.showToast('File uploaded successfully', 'success');
            this.loadDataFiles();
        } catch (e) {
            console.error('Failed to upload file:', e);
            this.showToast(e.message || 'Failed to upload file', 'error');
        }

        // Reset input
        event.target.value = '';
    },

    // ==================== Conversations ====================

    /**
     * Load conversations list
     */
    async loadConversations() {
        try {
            const response = await this.apiRequest('/api/admin/conversations');
            if (!response.ok) throw new Error('Failed to load conversations');
            const conversations = await response.json();
            this.renderConversations(conversations);
        } catch (e) {
            console.error('Failed to load conversations:', e);
            document.getElementById('conversations-list').innerHTML = '<div class="empty-state">Failed to load conversations</div>';
        }
    },

    /**
     * Render conversations list
     */
    renderConversations(conversations) {
        const container = document.getElementById('conversations-list');

        if (conversations.length === 0) {
            container.innerHTML = '<div class="empty-state">No conversations found</div>';
            return;
        }

        container.innerHTML = conversations.map(conv => `
            <div class="item-row conversation-row">
                <div class="item-content">
                    <div class="conversation-id">${this.escapeHtml(conv.session_id)}</div>
                    <div class="conversation-topic">${this.escapeHtml(conv.topic)}</div>
                    <div class="conversation-meta">
                        <span class="message-count">${conv.message_count} messages</span>
                        <span class="file-size">${this.formatFileSize(conv.size)}</span>
                        <span class="file-modified">${conv.ended_at ? 'Ended: ' + this.formatDate(conv.ended_at) : 'In progress'}</span>
                    </div>
                </div>
                <div class="item-actions">
                    <button class="btn btn-secondary btn-small" onclick="Admin.viewConversation('${this.escapeAttr(conv.session_id)}')">View</button>
                    <button class="btn btn-secondary btn-small" onclick="Admin.downloadConversation('${this.escapeAttr(conv.session_id)}')">Download</button>
                    <button class="btn btn-danger btn-small" onclick="Admin.deleteConversation('${this.escapeAttr(conv.session_id)}')">Delete</button>
                </div>
            </div>
        `).join('');
    },

    /**
     * View conversation
     */
    async viewConversation(sessionId) {
        try {
            const response = await this.apiRequest(`/api/admin/conversations/${encodeURIComponent(sessionId)}`);
            if (!response.ok) throw new Error('Failed to load conversation');
            const conversation = await response.json();

            this.currentConversationId = sessionId;
            document.getElementById('conversation-title').textContent = `Conversation: ${sessionId}`;

            // Render metadata
            const metaHtml = `
                <div class="meta-item"><strong>Topic:</strong> ${this.escapeHtml(conversation.topic)}</div>
                <div class="meta-item"><strong>Started:</strong> ${this.formatDate(conversation.started_at)}</div>
                <div class="meta-item"><strong>Ended:</strong> ${conversation.ended_at ? this.formatDate(conversation.ended_at) : 'In progress'}</div>
                <div class="meta-item"><strong>Participants:</strong></div>
                <ul class="participants-list">
                    ${conversation.participants.map(p => `<li>${this.escapeHtml(p.user_id)} - Task: ${this.escapeHtml(p.task)}</li>`).join('')}
                </ul>
            `;
            document.getElementById('conversation-meta').innerHTML = metaHtml;

            // Render messages
            const messagesHtml = conversation.messages.map(msg => {
                const thinkMatch = msg.content.match(/<think>([\s\S]*?)<\/think>/);
                const think = thinkMatch ? thinkMatch[1] : '';
                const speech = msg.content.replace(/<think>[\s\S]*?<\/think>/, '').trim();

                return `
                    <div class="message">
                        <div class="message-header">
                            <span class="message-role">${this.escapeHtml(msg.role)}</span>
                            <span class="message-time">${this.formatDate(msg.timestamp)}</span>
                        </div>
                        ${think ? `<div class="message-think"><em>Thinking:</em> ${this.escapeHtml(think)}</div>` : ''}
                        <div class="message-speech">${this.escapeHtml(speech)}</div>
                    </div>
                `;
            }).join('');
            document.getElementById('conversation-messages').innerHTML = messagesHtml || '<div class="empty-state">No messages</div>';

            document.getElementById('conversation-modal').classList.remove('hidden');
        } catch (e) {
            console.error('Failed to view conversation:', e);
            this.showToast('Failed to load conversation', 'error');
        }
    },

    /**
     * Close conversation modal
     */
    closeConversationModal() {
        document.getElementById('conversation-modal').classList.add('hidden');
        this.currentConversationId = null;
    },

    /**
     * Download current conversation
     */
    downloadCurrentConversation() {
        if (this.currentConversationId) {
            this.downloadConversation(this.currentConversationId);
        }
    },

    /**
     * Download conversation
     */
    async downloadConversation(sessionId) {
        try {
            const response = await this.apiRequest(`/api/admin/conversations/${encodeURIComponent(sessionId)}/download`);
            if (!response.ok) throw new Error('Failed to download');

            const blob = await response.blob();
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `${sessionId}.json`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
        } catch (e) {
            console.error('Failed to download conversation:', e);
            this.showToast('Failed to download conversation', 'error');
        }
    },

    /**
     * Delete conversation
     */
    async deleteConversation(sessionId) {
        if (!confirm(`Are you sure you want to delete conversation "${sessionId}"? This cannot be undone.`)) return;

        try {
            const response = await this.apiRequest(`/api/admin/conversations/${encodeURIComponent(sessionId)}`, {
                method: 'DELETE'
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || 'Failed to delete');
            }

            this.showToast('Conversation deleted', 'success');
            this.loadConversations();
        } catch (e) {
            console.error('Failed to delete conversation:', e);
            this.showToast(e.message || 'Failed to delete conversation', 'error');
        }
    },

    /**
     * Download all conversations as ZIP
     */
    async downloadAllConversations() {
        try {
            this.showToast('Preparing ZIP download...', 'success');
            const response = await this.apiRequest('/api/admin/conversations-download-all');
            if (!response.ok) throw new Error('Failed to download');

            const blob = await response.blob();
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            const disposition = response.headers.get('Content-Disposition');
            const match = disposition && disposition.match(/filename="(.+)"/);
            a.download = match ? match[1] : 'conversations.zip';
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
        } catch (e) {
            console.error('Failed to download conversations:', e);
            this.showToast('Failed to download conversations', 'error');
        }
    },

    // ==================== Topics ====================

    /**
     * Load topics from API
     */
    async loadTopics() {
        try {
            const response = await fetch('/api/admin/topics');
            const topics = await response.json();
            this.renderTopics(topics);
        } catch (e) {
            console.error('Failed to load topics:', e);
            this.showToast('Failed to load topics', 'error');
        }
    },

    /**
     * Render topics list
     */
    renderTopics(topics) {
        const container = document.getElementById('topics-list');

        if (topics.length === 0) {
            container.innerHTML = '<div class="empty-state">No topics yet. Add one above.</div>';
            return;
        }

        container.innerHTML = topics.map(topic => `
            <div class="item-row" data-id="${topic.id}">
                <div class="item-content">
                    <div class="item-id">ID: ${topic.id}</div>
                    <div class="item-text">${this.escapeHtml(topic.text)}</div>
                </div>
                <div class="item-actions">
                    <button class="btn btn-secondary btn-small" onclick="Admin.editTopic(${topic.id}, '${this.escapeAttr(topic.text)}')">Edit</button>
                    <button class="btn btn-danger btn-small" onclick="Admin.deleteTopic(${topic.id})">Delete</button>
                </div>
            </div>
        `).join('');
    },

    // ==================== Tasks ====================

    /**
     * Load tasks from API
     */
    async loadTasks() {
        try {
            const response = await fetch('/api/admin/tasks');
            const tasks = await response.json();
            this.renderTasks(tasks);
        } catch (e) {
            console.error('Failed to load tasks:', e);
            this.showToast('Failed to load tasks', 'error');
        }
    },

    /**
     * Render tasks list
     */
    renderTasks(tasks) {
        const container = document.getElementById('tasks-list');

        if (tasks.length === 0) {
            container.innerHTML = '<div class="empty-state">No tasks yet. Add one above.</div>';
            return;
        }

        container.innerHTML = tasks.map(task => `
            <div class="item-row" data-id="${task.id}">
                <div class="item-content">
                    <div class="item-id">ID: ${task.id}</div>
                    <div class="item-text">${this.escapeHtml(task.text)}</div>
                </div>
                <div class="item-actions">
                    <button class="btn btn-secondary btn-small" onclick="Admin.editTask(${task.id}, '${this.escapeAttr(task.text)}')">Edit</button>
                    <button class="btn btn-danger btn-small" onclick="Admin.deleteTask(${task.id})">Delete</button>
                </div>
            </div>
        `).join('');
    },

    // ==================== Consent ====================

    /**
     * Load consent from API
     */
    async loadConsent() {
        try {
            const response = await fetch('/api/admin/consent');
            const consent = await response.json();
            this.renderConsent(consent);
        } catch (e) {
            console.error('Failed to load consent:', e);
            this.showToast('Failed to load consent', 'error');
        }
    },

    /**
     * Render consent form
     */
    renderConsent(consent) {
        document.getElementById('consent-title').value = consent.title;
        document.getElementById('consent-version').value = consent.version;
        document.getElementById('consent-content').value = consent.content;

        const checkboxesList = document.getElementById('consent-checkboxes-list');
        checkboxesList.innerHTML = consent.checkboxes.map((text, index) => `
            <div class="checkbox-row">
                <input type="text" value="${this.escapeAttr(text)}" data-index="${index}">
                <button class="btn btn-danger btn-small" onclick="Admin.removeCheckbox(this)">Remove</button>
            </div>
        `).join('');
    },

    // ==================== Edit Modal (Topics/Tasks) ====================

    /**
     * Open add/edit modal
     */
    openAddModal(type) {
        this.editingType = type;
        this.editingId = null;

        document.getElementById('edit-modal-title').textContent = `Add ${type === 'topic' ? 'Topic' : 'Task'}`;
        document.getElementById('edit-input').value = '';
        document.getElementById('edit-modal').classList.remove('hidden');
    },

    /**
     * Edit topic
     */
    editTopic(id, text) {
        this.editingType = 'topic';
        this.editingId = id;

        document.getElementById('edit-modal-title').textContent = 'Edit Topic';
        document.getElementById('edit-input').value = text;
        document.getElementById('edit-modal').classList.remove('hidden');
    },

    /**
     * Edit task
     */
    editTask(id, text) {
        this.editingType = 'task';
        this.editingId = id;

        document.getElementById('edit-modal-title').textContent = 'Edit Task';
        document.getElementById('edit-input').value = text;
        document.getElementById('edit-modal').classList.remove('hidden');
    },

    /**
     * Close edit modal
     */
    closeEditModal() {
        document.getElementById('edit-modal').classList.add('hidden');
        this.editingType = null;
        this.editingId = null;
    },

    /**
     * Save edit (create or update)
     */
    async saveEdit() {
        const text = document.getElementById('edit-input').value.trim();

        if (!text) {
            this.showToast('Please enter some text', 'error');
            return;
        }

        const isNew = this.editingId === null;
        const endpoint = this.editingType === 'topic' ? '/api/admin/topics' : '/api/admin/tasks';

        try {
            const response = await fetch(isNew ? endpoint : `${endpoint}/${this.editingId}`, {
                method: isNew ? 'POST' : 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ text })
            });

            if (!response.ok) throw new Error('Failed to save');

            this.showToast(`${this.editingType === 'topic' ? 'Topic' : 'Task'} ${isNew ? 'added' : 'updated'}`, 'success');
            this.closeEditModal();

            // Reload data
            if (this.editingType === 'topic') {
                await this.loadTopics();
            } else {
                await this.loadTasks();
            }
        } catch (e) {
            console.error('Failed to save:', e);
            this.showToast('Failed to save', 'error');
        }
    },

    /**
     * Delete topic
     */
    async deleteTopic(id) {
        if (!confirm('Are you sure you want to delete this topic?')) return;

        try {
            const response = await fetch(`/api/admin/topics/${id}`, { method: 'DELETE' });
            if (!response.ok) throw new Error('Failed to delete');

            this.showToast('Topic deleted', 'success');
            await this.loadTopics();
        } catch (e) {
            console.error('Failed to delete topic:', e);
            this.showToast('Failed to delete topic', 'error');
        }
    },

    /**
     * Delete task
     */
    async deleteTask(id) {
        if (!confirm('Are you sure you want to delete this task?')) return;

        try {
            const response = await fetch(`/api/admin/tasks/${id}`, { method: 'DELETE' });
            if (!response.ok) throw new Error('Failed to delete');

            this.showToast('Task deleted', 'success');
            await this.loadTasks();
        } catch (e) {
            console.error('Failed to delete task:', e);
            this.showToast('Failed to delete task', 'error');
        }
    },

    // ==================== Consent Form ====================

    /**
     * Add checkbox row
     */
    addCheckboxRow() {
        const container = document.getElementById('consent-checkboxes-list');
        const row = document.createElement('div');
        row.className = 'checkbox-row';
        row.innerHTML = `
            <input type="text" value="" placeholder="Enter checkbox text">
            <button class="btn btn-danger btn-small" onclick="Admin.removeCheckbox(this)">Remove</button>
        `;
        container.appendChild(row);
    },

    /**
     * Remove checkbox row
     */
    removeCheckbox(button) {
        button.parentElement.remove();
    },

    /**
     * Save consent configuration
     */
    async saveConsent() {
        const title = document.getElementById('consent-title').value.trim();
        const version = document.getElementById('consent-version').value.trim();
        const content = document.getElementById('consent-content').value.trim();

        const checkboxInputs = document.querySelectorAll('#consent-checkboxes-list input');
        const checkboxes = Array.from(checkboxInputs)
            .map(input => input.value.trim())
            .filter(text => text.length > 0);

        if (!title || !content) {
            this.showToast('Title and content are required', 'error');
            return;
        }

        try {
            const response = await fetch('/api/admin/consent', {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ title, version, content, checkboxes })
            });

            if (!response.ok) throw new Error('Failed to save');

            this.showToast('Consent form saved', 'success');
        } catch (e) {
            console.error('Failed to save consent:', e);
            this.showToast('Failed to save consent', 'error');
        }
    },

    /**
     * Preview consent form
     */
    previewConsent() {
        const title = document.getElementById('consent-title').value;
        const content = document.getElementById('consent-content').value;

        const checkboxInputs = document.querySelectorAll('#consent-checkboxes-list input');
        const checkboxes = Array.from(checkboxInputs)
            .map(input => input.value.trim())
            .filter(text => text.length > 0);

        document.getElementById('preview-title').textContent = title;
        document.getElementById('preview-content').textContent = content;

        const previewCheckboxes = document.getElementById('preview-checkboxes');
        previewCheckboxes.innerHTML = checkboxes.map(text => `
            <label>
                <input type="checkbox" disabled>
                ${this.escapeHtml(text)}
            </label>
        `).join('');

        document.getElementById('preview-modal').classList.remove('hidden');
    },

    /**
     * Close preview modal
     */
    closePreviewModal() {
        document.getElementById('preview-modal').classList.add('hidden');
    },

    // ==================== Utilities ====================

    /**
     * Show toast notification
     */
    showToast(message, type = 'success') {
        const toast = document.getElementById('toast');
        toast.textContent = message;
        toast.className = `toast ${type}`;

        setTimeout(() => {
            toast.classList.add('hidden');
        }, 3000);
    },

    /**
     * Escape HTML
     */
    escapeHtml(text) {
        if (!text) return '';
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    },

    /**
     * Escape attribute value
     */
    escapeAttr(text) {
        if (!text) return '';
        return text
            .replace(/\\/g, '\\\\')
            .replace(/'/g, "\\'")
            .replace(/"/g, '\\"')
            .replace(/\n/g, '\\n');
    },

    /**
     * Format file size
     */
    formatFileSize(bytes) {
        if (bytes < 1024) return bytes + ' B';
        if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
        return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
    },

    /**
     * Format date
     */
    formatDate(dateStr) {
        if (!dateStr) return 'N/A';
        try {
            const date = new Date(dateStr);
            return date.toLocaleString();
        } catch {
            return dateStr;
        }
    }
};

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    Admin.init();
});
