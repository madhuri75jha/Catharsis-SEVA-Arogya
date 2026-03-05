/**
 * Hospitals List Page JavaScript
 * Shows all hospitals for DeveloperAdmin and links to each hospital settings page.
 */

class HospitalsListManager {
    constructor() {
        this.hospitals = [];
        this.filteredHospitals = [];
        this.init();
    }

    async init() {
        await this.fetchProfile();
        await this.fetchHospitals();
        this.bindSearch();
    }

    async fetchProfile() {
        try {
            const response = await fetch('/api/v1/profile');
            const data = await response.json();

            if (!data.success || !data.profile) {
                this.showError('Failed to load profile');
                return;
            }

            if (data.profile.role !== 'DeveloperAdmin') {
                this.showError('You do not have permission to view hospitals');
            }
        } catch (error) {
            console.error('Error fetching profile:', error);
            this.showError('Failed to load profile');
        }
    }

    async fetchHospitals() {
        try {
            const response = await fetch('/api/v1/hospitals');
            if (!response.ok) {
                this.showError('Failed to load hospitals');
                return;
            }

            const data = await response.json();
            if (!data.success) {
                this.showError(data.message || 'Failed to load hospitals');
                return;
            }

            this.hospitals = data.hospitals || [];
            this.filteredHospitals = [...this.hospitals];
            this.renderHospitals();
        } catch (error) {
            console.error('Error fetching hospitals:', error);
            this.showError('Failed to load hospitals');
        }
    }

    bindSearch() {
        const searchInput = document.getElementById('hospital-search');
        if (!searchInput) return;

        searchInput.addEventListener('input', () => {
            const query = searchInput.value.trim().toLowerCase();
            this.filteredHospitals = this.hospitals.filter((hospital) => {
                const name = (hospital.name || '').toLowerCase();
                const id = (hospital.hospital_id || '').toLowerCase();
                return name.includes(query) || id.includes(query);
            });
            this.renderHospitals();
        });
    }

    renderHospitals() {
        const loadingState = document.getElementById('loading-state');
        const errorState = document.getElementById('error-state');
        const content = document.getElementById('hospitals-content');
        const listEl = document.getElementById('hospitals-list');
        const emptyEl = document.getElementById('hospitals-empty');
        const countEl = document.getElementById('hospital-count');

        loadingState?.classList.add('hidden');
        errorState?.classList.add('hidden');
        content?.classList.remove('hidden');

        if (countEl) {
            countEl.textContent = String(this.filteredHospitals.length);
        }

        if (!listEl) return;

        if (this.filteredHospitals.length === 0) {
            listEl.innerHTML = '';
            emptyEl?.classList.remove('hidden');
            return;
        }

        emptyEl?.classList.add('hidden');
        listEl.innerHTML = '';

        this.filteredHospitals.forEach((hospital) => {
            const card = document.createElement('a');
            card.href = `/hospital-settings/${encodeURIComponent(hospital.hospital_id)}`;
            card.className = 'block rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900/40 p-4 hover:border-primary/40 hover:bg-slate-50 dark:hover:bg-slate-900 transition-colors';
            card.innerHTML = `
                <div class="flex items-start justify-between gap-3">
                    <div class="min-w-0">
                        <p class="text-sm font-semibold text-slate-800 dark:text-slate-100 truncate">${this.escapeHtml(hospital.name || 'Unnamed Hospital')}</p>
                        <p class="mt-1 text-xs text-slate-500 truncate">${this.escapeHtml(hospital.hospital_id || '')}</p>
                        <p class="mt-2 text-xs text-slate-500 truncate">${this.escapeHtml(hospital.email || 'No email')}</p>
                    </div>
                    <span class="material-symbols-outlined text-slate-400 text-[20px]">chevron_right</span>
                </div>
            `;
            listEl.appendChild(card);
        });
    }

    showError(message) {
        document.getElementById('loading-state')?.classList.add('hidden');
        document.getElementById('hospitals-content')?.classList.add('hidden');

        const errorState = document.getElementById('error-state');
        const errorMessage = document.getElementById('error-message');

        if (errorState) errorState.classList.remove('hidden');
        if (errorMessage) errorMessage.textContent = message;
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

document.addEventListener('DOMContentLoaded', () => {
    window.hospitalsList = new HospitalsListManager();
});
