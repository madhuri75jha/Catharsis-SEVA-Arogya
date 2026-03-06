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
        this.fetchLimit = 50;
        this.filters = {
            search: '',
            status: '',
            startDate: '',
            endDate: ''
        };

        this.debouncedFetch = new DebouncedSearch((value) => {
            this.filters.search = value;
            this.fetchConsultations();
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
                this.debouncedFetch.execute(e.target.value);
            });
        }

        const statusFilter = document.getElementById('status-filter');
        if (statusFilter) {
            statusFilter.addEventListener('change', (e) => {
                this.filters.status = e.target.value;
                this.fetchConsultations();
            });
        }

        const startDateFilter = document.getElementById('start-date-filter');
        if (startDateFilter) {
            startDateFilter.addEventListener('change', (e) => {
                this.filters.startDate = e.target.value;
                this.fetchConsultations();
            });
        }

        const endDateFilter = document.getElementById('end-date-filter');
        if (endDateFilter) {
            endDateFilter.addEventListener('change', (e) => {
                this.filters.endDate = e.target.value;
                this.fetchConsultations();
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

            const hasFilters = Boolean(
                this.filters.search || this.filters.status || this.filters.startDate || this.filters.endDate
            );
            const limit = hasFilters ? this.fetchLimit : 15;

            const params = new URLSearchParams();
            params.set('limit', String(limit));
            if (this.filters.search) params.set('search', this.filters.search);
            if (this.filters.status) params.set('status', this.filters.status);
            if (this.filters.startDate) params.set('start_date', this.filters.startDate);
            if (this.filters.endDate) params.set('end_date', this.filters.endDate);

            const response = await fetch(`/api/consultations?${params.toString()}`);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();
            if (data.success) {
                this.consultations = data.consultations || [];
                this.renderConsultations();
            } else {
                this.showError(data.error || 'Failed to load consultations');
            }
        } catch (error) {
            console.error('Error fetching consultations:', error);
            this.showError('An error occurred while loading consultations');
        }
    }

    renderConsultations() {
        const container = document.getElementById('prescriptions-container');
        const tbody = document.getElementById('prescriptions-tbody');
        const loadingState = document.getElementById('loading-state');
        const emptyState = document.getElementById('empty-state');

        if (loadingState) loadingState.classList.add('hidden');

        if (this.consultations.length === 0) {
            if (container) container.classList.add('hidden');
            if (emptyState) emptyState.classList.remove('hidden');
            return;
        }

        if (emptyState) emptyState.classList.add('hidden');
        if (container) container.classList.remove('hidden');

        if (tbody) {
            tbody.innerHTML = '';
            this.consultations.forEach((consultation) => {
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

        const actionsCell = document.createElement('td');
        actionsCell.className = 'px-4 py-3';
        const isDeleted = String(consultation.status || '').toUpperCase() === 'DELETED';
        if (isDeleted) {
            actionsCell.innerHTML = '<span class="text-xs text-slate-400">Deleted</span>';
        } else {
            const deleteBtn = document.createElement('button');
            deleteBtn.type = 'button';
            deleteBtn.className = 'text-xs font-medium px-2.5 py-1.5 rounded-md bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300 hover:bg-red-200 dark:hover:bg-red-900/50 transition-colors';
            deleteBtn.textContent = 'Delete';
            deleteBtn.addEventListener('click', (event) => {
                event.preventDefault();
                event.stopPropagation();
                this.softDeleteConsultation(consultation.consultation_id, deleteBtn);
            });
            actionsCell.appendChild(deleteBtn);
        }
        row.appendChild(actionsCell);

        return row;
    }

    async softDeleteConsultation(consultationId, buttonEl) {
        if (!consultationId) return;

        const confirmed = window.confirm('Move this consultation to deleted status?');
        if (!confirmed) return;

        const originalLabel = buttonEl ? buttonEl.textContent : null;
        if (buttonEl) {
            buttonEl.disabled = true;
            buttonEl.textContent = 'Deleting...';
        }

        try {
            const response = await fetch(`/api/v1/consultations/${encodeURIComponent(consultationId)}/delete`, {
                method: 'POST'
            });
            const data = await response.json();
            if (!response.ok || !data.success) {
                throw new Error(data.message || `Delete failed with status ${response.status}`);
            }
            await this.fetchConsultations();
            if (window.showUIPopup) {
                window.showUIPopup('Consultation marked as deleted');
            }
        } catch (error) {
            console.error('Error deleting consultation:', error);
            if (window.showUIPopup) {
                window.showUIPopup(error.message || 'Failed to delete consultation');
            } else {
                window.alert(error.message || 'Failed to delete consultation');
            }
            if (buttonEl) {
                buttonEl.disabled = false;
                buttonEl.textContent = originalLabel || 'Delete';
            }
        }
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
            FAILED: 'Failed',
            DELETED: 'Deleted'
        };
        const normalized = String(status || '').toUpperCase();
        return statusMap[normalized] || status || 'Unknown';
    }

    getStatusClass(status) {
        const normalized = String(status || '').toLowerCase();
        if (normalized === 'completed') return 'status-completed';
        if (normalized === 'in_progress') return 'status-in_progress';
        if (normalized === 'failed') return 'status-failed';
        if (normalized === 'deleted') return 'status-failed';
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
