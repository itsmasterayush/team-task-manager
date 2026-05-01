const API_URL = window.location.origin + '/api';

const app = {
    state: {
        token: localStorage.getItem('token'),
        user: JSON.parse(localStorage.getItem('user') || 'null'),
        users: [],
        projects: [],
        tasks: []
    },

    init() {
        if (this.state.token) {
            this.showApp();
        } else {
            this.showAuth();
        }
    },

    // --- Navigation & UI ---
    showAuth() {
        document.getElementById('auth-view').classList.remove('hidden');
        document.getElementById('app-view').classList.add('hidden');
    },

    showApp() {
        document.getElementById('auth-view').classList.add('hidden');
        document.getElementById('app-view').classList.remove('hidden');
        
        document.getElementById('user-info').innerText = `${this.state.user.name} (${this.state.user.role})`;
        
        if (this.state.user.role !== 'ADMIN') {
            document.querySelectorAll('.admin-only').forEach(el => el.classList.add('hidden'));
        } else {
            document.querySelectorAll('.admin-only').forEach(el => el.classList.remove('hidden'));
        }

        this.navigate('dashboard');
        this.loadInitialData();
    },

    navigate(screen) {
        document.querySelectorAll('.main-content > div').forEach(el => el.classList.add('hidden'));
        document.getElementById(`screen-${screen}`).classList.remove('hidden');
        
        document.querySelectorAll('.sidebar .nav-item').forEach(el => el.classList.remove('active'));
        const navItems = document.querySelectorAll('.sidebar .nav-item');
        for(let item of navItems) {
            if(item.innerText.toLowerCase() === screen) {
                item.classList.add('active');
            }
        }

        if (screen === 'dashboard') this.fetchDashboard();
        if (screen === 'projects') this.fetchProjects();
        if (screen === 'tasks') this.fetchTasks();
    },

    toggleAuth() {
        const login = document.getElementById('login-form');
        const reg = document.getElementById('register-form');
        if (login.classList.contains('hidden')) {
            login.classList.remove('hidden');
            reg.classList.add('hidden');
        } else {
            login.classList.add('hidden');
            reg.classList.remove('hidden');
        }
    },

    openModal(id) { document.getElementById(id).classList.remove('hidden'); },
    closeModal(id) { document.getElementById(id).classList.add('hidden'); },

    // --- API Helpers ---
    async api(endpoint, method = 'GET', body = null) {
        const headers = { 'Content-Type': 'application/json' };
        if (this.state.token) headers['Authorization'] = `Bearer ${this.state.token}`;
        
        const options = { method, headers };
        if (body) options.body = JSON.stringify(body);

        try {
            const res = await fetch(`${API_URL}${endpoint}`, options);
            const data = await res.json();
            if (!res.ok) throw new Error(data.message || 'API Error');
            return data;
        } catch (err) {
            alert(err.message);
            if (err.message === 'Token is invalid!' || err.message === 'Token is missing!') {
                this.logout();
            }
            throw err;
        }
    },

    // --- Authentication ---
    async login() {
        const email = document.getElementById('login-email').value;
        const password = document.getElementById('login-password').value;
        try {
            const data = await this.api('/auth/login', 'POST', { email, password });
            this.setSession(data.token, data.user);
            this.showApp();
        } catch (e) {}
    },

    async register() {
        const name = document.getElementById('reg-name').value;
        const email = document.getElementById('reg-email').value;
        const password = document.getElementById('reg-password').value;
        const role = document.getElementById('reg-role').value;
        try {
            await this.api('/auth/register', 'POST', { name, email, password, role });
            alert('Registration successful! Please login.');
            this.toggleAuth();
        } catch (e) {}
    },

    setSession(token, user) {
        this.state.token = token;
        this.state.user = user;
        localStorage.setItem('token', token);
        localStorage.setItem('user', JSON.stringify(user));
    },

    logout() {
        this.state.token = null;
        this.state.user = null;
        localStorage.removeItem('token');
        localStorage.removeItem('user');
        this.showAuth();
    },

    // --- Data Loading ---
    async loadInitialData() {
        try {
            this.state.users = await this.api('/users');
            this.state.projects = await this.api('/projects');
            this.populateSelects();
        } catch (e) {}
    },

    populateSelects() {
        const projSelect = document.getElementById('task-project');
        projSelect.innerHTML = this.state.projects.map(p => `<option value="${p.id}">${p.name}</option>`).join('');
        
        const assignSelect = document.getElementById('task-assignee');
        assignSelect.innerHTML = '<option value="">Unassigned</option>' + 
            this.state.users.map(u => `<option value="${u.id}">${u.name}</option>`).join('');
    },

    // --- Dashboard ---
    async fetchDashboard() {
        try {
            const data = await this.api('/dashboard');
            document.getElementById('stat-total').innerText = data.total;
            document.getElementById('stat-todo').innerText = data.todo;
            document.getElementById('stat-progress').innerText = data.in_progress;
            document.getElementById('stat-done').innerText = data.done;
            document.getElementById('stat-overdue').innerText = data.overdue;
        } catch (e) {}
    },

    // --- Projects ---
    async fetchProjects() {
        try {
            this.state.projects = await this.api('/projects');
            const tbody = document.getElementById('projects-list');
            tbody.innerHTML = this.state.projects.map(p => `
                <tr>
                    <td style="font-weight: 500">${p.name}</td>
                    <td style="color: var(--text-muted)">${p.description || '-'}</td>
                    <td>${p.members.map(m => `<span class="badge badge-MEMBER">${m.name}</span>`).join(' ')}</td>
                </tr>
            `).join('');
            this.populateSelects();
        } catch (e) {}
    },

    async createProject() {
        const name = document.getElementById('proj-name').value;
        const description = document.getElementById('proj-desc').value;
        try {
            await this.api('/projects', 'POST', { name, description });
            this.closeModal('modal-project');
            document.getElementById('proj-name').value = '';
            document.getElementById('proj-desc').value = '';
            this.fetchProjects();
        } catch (e) {}
    },

    // --- Tasks ---
    async fetchTasks() {
        try {
            this.state.tasks = await this.api('/tasks');
            const tbody = document.getElementById('tasks-list');
            tbody.innerHTML = this.state.tasks.map(t => `
                <tr>
                    <td style="font-weight: 500">${t.title}</td>
                    <td>${t.project_name}</td>
                    <td>${t.assignee_name || '-'}</td>
                    <td><span class="badge badge-${t.status}">${t.status.replace('_', ' ')}</span></td>
                    <td>${t.due_date ? new Date(t.due_date).toLocaleDateString() : '-'}</td>
                    <td>
                        <button class="btn btn-outline" style="padding: 0.25rem 0.5rem; font-size: 0.75rem" 
                            onclick="app.openEditTaskModal(${t.id}, '${t.status}')">Update Status</button>
                    </td>
                </tr>
            `).join('');
        } catch (e) {}
    },

    async createTask() {
        const title = document.getElementById('task-title').value;
        const project_id = document.getElementById('task-project').value;
        const assignee_id = document.getElementById('task-assignee').value;
        const due_date = document.getElementById('task-due').value;
        const status = document.getElementById('task-status').value;

        try {
            await this.api('/tasks', 'POST', {
                title, 
                project_id: project_id ? parseInt(project_id) : null, 
                assignee_id: assignee_id ? parseInt(assignee_id) : null,
                due_date: due_date ? new Date(due_date).toISOString() : null,
                status
            });
            this.closeModal('modal-task');
            document.getElementById('task-title').value = '';
            this.fetchTasks();
        } catch (e) {}
    },

    openEditTaskModal(taskId, currentStatus) {
        document.getElementById('edit-task-id').value = taskId;
        document.getElementById('edit-task-status').value = currentStatus;
        this.openModal('modal-edit-task');
    },

    async updateTaskStatus() {
        const taskId = document.getElementById('edit-task-id').value;
        const status = document.getElementById('edit-task-status').value;
        
        try {
            await this.api(`/tasks/${taskId}`, 'PATCH', { status });
            this.closeModal('modal-edit-task');
            this.fetchTasks();
        } catch (e) {}
    }
};

// Initialize
window.onload = () => app.init();
