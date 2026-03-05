/**
 * Prescriptions List Page JavaScript
 * Handles prescription list fetching, filtering, search, and navigation
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
        
        this.timeoutId = setTimeout(() => {
            this.callback(value);
        }, this.delay);
    }
    
    cancel() {
        if (this.timeoutId) {
            clearTimeout(this.timeoutId);
            this.timeoutId = null;
        }
    }
}

class PrescriptionsListManager {
    constructor() {
        this.prescriptions = [];
        this.filters = {
            search: '',
            state: '',
            startDate: '',
            endDate: ''
        };
        
        this.debouncedSearch = new DebouncedSearch((value) => {
            this.filters.search = value;
            this.fetchPrescriptions();
        }, 300);
        
        this.init();
    }
    
    init() {
        this.setupEventListeners();
        this.loadFiltersFromURL();
        this.fetchPrescriptions();
    }
    
    setupEventListeners() {
        // Search input
        const searchInput = document.getElementById('search-input');
        if (searchInput) {
            searchInput.addEventListener('input', (e) => {
                this.debouncedSearch.execute(e.target.value);
            });
        }
        
        // State filter
        const stateFilter = document.getElementById('state-filter');
        if (stateFilter) {
            stateFilter.addEventListener('change', (e) => {
                this.filters.state = e.target.value;
                this.fetchPrescriptions();
            });
        }
        
        // Date filters
        const startDateFilter = document.getElementById('start-date-filter');
        if (startDateFilter) {
            startDateFilter.addEventListener('change', (e) => {
                this.filters.startDate = e.target.value;
                this.fetchPrescriptions();
            });
        }
        
        const endDateFilter = document.getElementById('end-date-filter');
        if (endDateFilter) {
            endDateFilter.addEventListener('change', (e) => {
                this.filters.endDate = e.target.value;
                this.fetchPrescriptions();
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
        
        const state = urlParams.get('state');
        if (state) {
            this.filters.state = state;
            const stateFilter = document.getElementById('state-filter');
            if (stateFilter) {
                stateFilter.value = state;
            }
        }
    }
    
    async fetchPrescriptions() {
        try {
            this.showLoading();
            
            // Build query parameters
            const params = new URLSearchParams();
            if (this.filters.search) params.append('search', this.filters.search);
            if (this.filters.state) params.append('state', this.filters.state);
            if (this.filters.startDate) params.append('start_date', this.filters.startDate);
            if (this.filters.endDate) params.append('end_date', this.filters.endDate);
            params.append('limit', '50');
            params.append('offset', '0');
            
            const response = await fetch(`/api/v1/prescriptions?${params.toString()}`);
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const data = await response.json();
            
            if (data.success) {
                this.prescriptions = data.prescriptions || [];
                this.renderPrescriptions();
            } else {
                console.error('Failed to fetch prescriptions:', data.message);
                this.showError('Failed to load prescriptions');
            }
        } catch (error) {
            console.error('Error fetching prescriptions:', error);
            this.showError('An error occurred while loading prescriptions');
        }
    }
    
    renderPrescriptions() {
        const container = document.getElementById('prescriptions-container');
        const tbody = document.getElementById('prescriptions-tbody');
        const loadingState = document.getElementById('loading-state');
        const emptyState = document.getElementById('empty-state');
        
        // Hide loading state
        if (loadingState) loadingState.classList.add('hidden');
        
        if (this.prescriptions.length === 0) {
            // Show empty state
            if (container) container.classList.add('hidden');
            if (emptyState) emptyState.classList.remove('hidden');
            return;
        }
        
        // Show prescriptions table
        if (emptyState) emptyState.classList.add('hidden');
        if (container) container.classList.remove('hidden');
        
        // Clear existing rows
        if (tbody) {
            tbody.innerHTML = '';
            
            // Render each prescription
            this.prescriptions.forEach(prescription => {
                const row = this.createPrescriptionRow(prescription);
                tbody.appendChild(row);
            });
        }
    }
    
    createPrescriptionRow(prescription) {
        const row = document.createElement('tr');
        row.onclick = () => this.navigateToPrescription(prescription.prescription_id);
        
        // Patient name
        const patientCell = document.createElement('td');
        patientCell.className = 'px-4 py-3';
        patientCell.innerHTML = `
            <div class="flex items-center gap-2">
                <div class="flex-shrink-0 w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center">
                    <span class="text-xs font-semibold text-primary">${this.getInitials(prescription.patient_name)}</span>
                </div>
                <div>
                    <p class="text-sm font-medium text-slate-800 dark:text-white">${this.escapeHtml(prescription.patient_name)}</p>
                    <p class="text-xs text-slate-500">#${prescription.prescription_id}</p>
                </div>
            </div>
        `;
        row.appendChild(patientCell);
        
        // Date
        const dateCell = document.createElement('td');
        dateCell.className = 'px-4 py-3';
        dateCell.innerHTML = `
            <div class="text-sm text-slate-600 dark:text-slate-300">${this.formatDate(prescription.created_at)}</div>
            <div class="text-xs text-slate-500">${this.formatTime(prescription.created_at)}</div>
        `;
        row.appendChild(dateCell);
        
        // State
        const stateCell = document.createElement('td');
        stateCell.className = 'px-4 py-3';
        stateCell.innerHTML = `<span class="state-badge state-${prescription.state.toLowerCase()}">${this.formatState(prescription.state)}</span>`;
        row.appendChild(stateCell);
        
        // Section statuses
        const sectionsCell = document.createElement('td');
        sectionsCell.className = 'px-4 py-3';
        sectionsCell.innerHTML = this.renderSectionStatuses(prescription.section_statuses);
        row.appendChild(sectionsCell);
        
        return row;
    }
    
    renderSectionStatuses(sectionStatuses) {
        if (!sectionStatuses || Object.keys(sectionStatuses).length === 0) {
            return '<span class="text-xs text-slate-400">No sections</span>';
        }
        
        const statuses = Object.values(sectionStatuses);
        const approved = statuses.filter(s => s === 'Approved').length;
        const rejected = statuses.filter(s => s === 'Rejected').length;
        const pending = statuses.filter(s => s === 'Pending').length;
        
        let html = '<div class="flex gap-1">';
        
        if (approved > 0) {
            html += `<span class="section-status section-approved" title="${approved} approved">✓</span>`;
        }
        if (rejected > 0) {
            html += `<span class="section-status section-rejected" title="${rejected} rejected">✗</span>`;
        }
        if (pending > 0) {
            html += `<span class="section-status section-pending" title="${pending} pending">•</span>`;
        }
        
        html += '</div>';
        return html;
    }
    
    navigateToPrescription(prescriptionId) {
        window.location.href = `/prescriptions/${prescriptionId}`;
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
    
    // Utility methods
    getInitials(name) {
        if (!name) return '?';
        const parts = name.trim().split(' ');
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
    
    formatState(state) {
        const stateMap = {
            'Draft': 'Draft',
            'InProgress': 'In Progress',
            'Finalized': 'Finalized',
            'Deleted': 'Deleted'
        };
        return stateMap[state] || state;
    }
    
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    new PrescriptionsListManager();
});
