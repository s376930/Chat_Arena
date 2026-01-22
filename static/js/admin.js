/**
 * Admin page JavaScript for Chat Arena
 */
const Admin = {
    // Current editing state
    editingType: null, // 'topic' or 'task'
    editingId: null,

    /**
     * Initialize admin page
     */
    async init() {
        this.setupEventListeners();
        await this.loadAllData();
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

        // Close modals on outside click
        document.getElementById('edit-modal').addEventListener('click', (e) => {
            if (e.target.id === 'edit-modal') this.closeEditModal();
        });
        document.getElementById('preview-modal').addEventListener('click', (e) => {
            if (e.target.id === 'preview-modal') this.closePreviewModal();
        });
    },

    /**
     * Load all data (topics, tasks, consent)
     */
    async loadAllData() {
        await Promise.all([
            this.loadTopics(),
            this.loadTasks(),
            this.loadConsent()
        ]);
    },

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
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    },

    /**
     * Escape attribute value
     */
    escapeAttr(text) {
        return text
            .replace(/\\/g, '\\\\')
            .replace(/'/g, "\\'")
            .replace(/"/g, '\\"')
            .replace(/\n/g, '\\n');
    }
};

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    Admin.init();
});
