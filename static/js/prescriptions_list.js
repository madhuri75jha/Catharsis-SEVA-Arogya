/**
 * Consultations List Page JavaScript
 * Keeps legacy filename for template compatibility.
 */

class DebouncedSearch {
    constructor(callback, delay = 300) {
        this.callback = callback;
        this.delay = delay;
        this.timeoutId = null;
    }

    execute(value) {
        if (this.timeoutId) {
            clearTimeout(this.timeoutId);
        }
        this.timeoutId = setTimeout(() => this.callback(value), this.delay);
    }
}

class ConsultationsListManager {
    constructor() {
        this.consultations = [];
        this.filteredConsultations = [];
        this.defaultDisplayLimit = 15;
        this.fetchLimit = 50;
        this.filters = {
            search: '',
            status: '',
            startDate: '',
            endDate: ''
        };

        this.debouncedSearch = new DebouncedSearch((value) => {
            this.filters.search = value;
            this.applyFiltersAndRender();
        }, 300);

        this.init();
    }

    init() {
        this.setupEventListeners();
        this.loadFiltersFromURL();
        this.fetchConsultations();
    }

    setupEventListeners() {
        const searchInput = document.getElementById('search-input');
        if (searchInput) {
            searchInput.addEventListener('input', (e) => {
                this.debouncedSearch.execute(e.target.value);
            });
        }

        const statusFilter = document.getElementById('status-filter');
        if (statusFilter) {
            statusFilter.addEventListener('change', (e) => {
                this.filters.status = e.target.value;
                this.applyFiltersAndRender();
            });
        }

        const startDateFilter = document.getElementById('start-date-filter');
        if (startDateFilter) {
            startDateFilter.addEventListener('change', (e) => {
                this.filters.startDate = e.target.value;
                this.applyFiltersAndRender();
            });
        }

        const endDateFilter = document.getElementById('end-date-filter');
        if (endDateFilter) {
            endDateFilter.addEventListener('change', (e) => {
                this.filters.endDate = e.target.value;
                this.applyFiltersAndRender();
            });
        }
    }

    loadFiltersFromURL() {
        const urlParams = new URLSearchParams(window.location.search);

        const search = urlParams.get('search');
        if (search) {
            this.filters.search = search;
            const searchInput = document.getElementById('search-input');
            if (searchInput) {
                searchInput.value = search;
            }
        }

        const status = urlParams.get('status');
        if (status) {
            this.filters.status = status;
            const statusFilter = document.getElementById('status-filter');
            if (statusFilter) {
                statusFilter.value = status;
            }
        }
    }

    async fetchConsultations() {
        try {
            this.showLoading();

            const response = await fetch(`/api/consultations?limit=${this.fetchLimit}`);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();
            if (data.success) {
                this.consultations = data.consultations || [];
                this.applyFiltersAndRender();
            } else {
                this.showError(data.error || 'Failed to load consultations');
            }
        } catch (error) {
            console.error('Error fetching consultations:', error);
            this.showError('An error occurred while loading consultations');
        }
    }

    applyFiltersAndRender() {
        const hasAnyFilter = Boolean(
            this.filters.search || this.filters.status || this.filters.startDate || this.filters.endDate
        );

        const searchLower = this.filters.search.trim().toLowerCase();
        let filtered = [...this.consultations];

        if (searchLower) {
            filtered = filtered.filter((c) => {
                const patient = (c.patient_name || '').toLowerCase();
                const consultationId = String(c.consultation_id || '').toLowerCase();
                return patient.includes(searchLower) || consultationId.includes(searchLower);
            });
        }

        if (this.filters.status) {
            filtered = filtered.filter((c) => (c.status || '').toUpperCase() === this.filters.status.toUpperCase());
        }

        if (this.filters.startDate) {
            const start = new Date(`${this.filters.startDate}T00:00:00`);
            filtered = filtered.filter((c) => c.created_at && new Date(c.created_at) >= start);
        }

        if (this.filters.endDate) {
            const end = new Date(`${this.filters.endDate}T23:59:59`);
            filtered = filtered.filter((c) => c.created_at && new Date(c.created_at) <= end);
        }

        this.filteredConsultations = hasAnyFilter
            ? filtered
            : filtered.slice(0, this.defaultDisplayLimit);

        this.renderConsultations();
    }

    renderConsultations() {
        const container = document.getElementById('prescriptions-container');
        const tbody = document.getElementById('prescriptions-tbody');
        const loadingState = document.getElementById('loading-state');
        const emptyState = document.getElementById('empty-state');

        if (loadingState) loadingState.classList.add('hidden');

        if (this.filteredConsultations.length === 0) {
            if (container) container.classList.add('hidden');
            if (emptyState) emptyState.classList.remove('hidden');
            return;
        }

        if (emptyState) emptyState.classList.add('hidden');
        if (container) container.classList.remove('hidden');

        if (tbody) {
            tbody.innerHTML = '';
            this.filteredConsultations.forEach((consultation) => {
                const row = this.createConsultationRow(consultation);
                tbody.appendChild(row);
            });
        }
    }

    createConsultationRow(consultation) {
        const row = document.createElement('tr');
        row.onclick = () => this.navigateToConsultation(consultation.consultation_id);

        const patientCell = document.createElement('td');
        patientCell.className = 'px-4 py-3';
        patientCell.innerHTML = `
            <div class="flex items-center gap-2">
                <div class="flex-shrink-0 w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center">
                    <span class="text-xs font-semibold text-primary">${this.getInitials(consultation.patient_name)}</span>
                </div>
                <div>
                    <p class="text-sm font-medium text-slate-800 dark:text-white">${this.escapeHtml(consultation.patient_name || 'Unknown Patient')}</p>
                    <p class="text-xs text-slate-500">#${this.escapeHtml(String(consultation.consultation_id || ''))}</p>
                </div>
            </div>
        `;
        row.appendChild(patientCell);

        const dateCell = document.createElement('td');
        dateCell.className = 'px-4 py-3';
        dateCell.innerHTML = `
            <div class="text-sm text-slate-600 dark:text-slate-300">${this.formatDate(consultation.created_at)}</div>
            <div class="text-xs text-slate-500">${this.formatTime(consultation.created_at)}</div>
        `;
        row.appendChild(dateCell);

        const statusCell = document.createElement('td');
        statusCell.className = 'px-4 py-3';
        statusCell.innerHTML = `<span class="status-badge ${this.getStatusClass(consultation.status)}">${this.formatStatus(consultation.status)}</span>`;
        row.appendChild(statusCell);

        const prescriptionCell = document.createElement('td');
        prescriptionCell.className = 'px-4 py-3';
        if (consultation.has_prescription) {
            const prescId = consultation.prescription_id ? ` #${this.escapeHtml(String(consultation.prescription_id))}` : '';
            prescriptionCell.innerHTML = `<span class="text-xs font-medium text-green-700 dark:text-green-300">Available${prescId}</span>`;
        } else {
            prescriptionCell.innerHTML = '<span class="text-xs text-slate-400">Not created</span>';
        }
        row.appendChild(prescriptionCell);

        return row;
    }

    navigateToConsultation(consultationId) {
        if (!consultationId) return;
        window.navigateWithTransition(`/consultation/${consultationId}`);
    }

    showLoading() {
        const loadingState = document.getElementById('loading-state');
        const emptyState = document.getElementById('empty-state');
        const container = document.getElementById('prescriptions-container');

        if (loadingState) loadingState.classList.remove('hidden');
        if (emptyState) emptyState.classList.add('hidden');
        if (container) container.classList.add('hidden');
    }

    showError(message) {
        const loadingState = document.getElementById('loading-state');
        const emptyState = document.getElementById('empty-state');
        const container = document.getElementById('prescriptions-container');

        if (loadingState) loadingState.classList.add('hidden');
        if (container) container.classList.add('hidden');

        if (emptyState) {
            emptyState.classList.remove('hidden');
            emptyState.innerHTML = `
                <div class="text-center px-6">
                    <span class="material-symbols-outlined text-[64px] text-red-300 dark:text-red-700">error</span>
                    <p class="mt-2 text-sm text-red-500">${this.escapeHtml(message)}</p>
                </div>
            `;
        }
    }

    getInitials(name) {
        if (!name) return '?';
        const parts = String(name).trim().split(' ');
        if (parts.length === 1) return parts[0].charAt(0).toUpperCase();
        return (parts[0].charAt(0) + parts[parts.length - 1].charAt(0)).toUpperCase();
    }

    formatDate(dateString) {
        if (!dateString) return 'N/A';
        const date = new Date(dateString);
        return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
    }

    formatTime(dateString) {
        if (!dateString) return '';
        const date = new Date(dateString);
        return date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
    }

    formatStatus(status) {
        const statusMap = {
            COMPLETED: 'Completed',
            IN_PROGRESS: 'In Progress',
            FAILED: 'Failed'
        };
        const normalized = String(status || '').toUpperCase();
        return statusMap[normalized] || status || 'Unknown';
    }

    getStatusClass(status) {
        const normalized = String(status || '').toLowerCase();
        if (normalized === 'completed') return 'status-completed';
        if (normalized === 'in_progress') return 'status-in_progress';
        if (normalized === 'failed') return 'status-failed';
        return 'status-in_progress';
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

document.addEventListener('DOMContentLoaded', () => {
    new ConsultationsListManager();
});
