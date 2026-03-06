class PrescriptionConfigSettingsManager {
    constructor() {
        this.hospitalId = selectedHospitalId || null;
        this.userRole = null;
        this.profileHospitalId = null;
        this.config = null;
        this.source = 'unknown';

        this.init();
    }

    async init() {
        this.setupStaticEvents();
        await this.fetchProfile();
        this.resolveHospitalId();

        if (!this.hospitalId) {
            this.showError('No hospital selected');
            return;
        }

        await this.loadConfig();
    }

    setupStaticEvents() {
        const reloadBtn = document.getElementById('reload-config-btn');
        if (reloadBtn) reloadBtn.onclick = () => this.loadConfig();

        const saveBtn = document.getElementById('save-config-btn');
        if (saveBtn) saveBtn.onclick = () => this.saveConfig();

        const generateBtn = document.getElementById('generate-default-btn');
        if (generateBtn) generateBtn.onclick = () => this.generateFromDefault();
    }

    async fetchProfile() {
        try {
            const response = await fetch('/api/v1/profile');
            const data = await response.json();
            if (data.success && data.profile) {
                this.userRole = data.profile.role;
                this.profileHospitalId = data.profile.hospital_id || null;
            }
        } catch (error) {
            console.error('Failed to fetch profile:', error);
        }
    }

    resolveHospitalId() {
        if (this.userRole !== 'DeveloperAdmin' && this.profileHospitalId) {
            this.hospitalId = this.profileHospitalId;
        }
    }

    async loadConfig() {
        try {
            this.showLoading();
            const response = await fetch(`/api/v1/hospitals/${encodeURIComponent(this.hospitalId)}/prescription-config`);
            const data = await response.json();

            if (!response.ok || !data.success) {
                this.showError(data.message || 'Failed to load prescription config');
                return;
            }

            this.config = data.config || {};
            this.source = data.source || 'unknown';
            this.render();
        } catch (error) {
            console.error('Failed to load config:', error);
            this.showError('Failed to load prescription config');
        }
    }

    render() {
        document.getElementById('loading-state')?.classList.add('hidden');
        document.getElementById('error-state')?.classList.add('hidden');
        document.getElementById('config-content')?.classList.remove('hidden');

        const subtitle = document.getElementById('config-page-subtitle');
        if (subtitle) subtitle.textContent = `Hospital: ${this.hospitalId}`;

        const badge = document.getElementById('config-source-badge');
        if (badge) {
            badge.textContent = this.source === 'hospital' ? 'Hospital File' : 'Default Fallback';
            badge.className = this.source === 'hospital'
                ? 'text-[10px] px-2 py-1 rounded-full bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300'
                : 'text-[10px] px-2 py-1 rounded-full bg-yellow-100 dark:bg-yellow-900/30 text-yellow-700 dark:text-yellow-300';
        }

        const summary = document.getElementById('config-summary');
        if (summary) {
            const sections = Array.isArray(this.config.sections) ? this.config.sections : [];
            const fieldsCount = sections.reduce((acc, s) => acc + (Array.isArray(s.fields) ? s.fields.length : 0), 0);
            summary.innerHTML = `
                <p><strong>Hospital Name:</strong> ${this.escapeHtml(this.config.hospital_name || '-')}</p>
                <p><strong>Version:</strong> ${this.escapeHtml(this.config.version || '-')}</p>
                <p><strong>Sections:</strong> ${sections.length}</p>
                <p><strong>Total Fields:</strong> ${fieldsCount}</p>
            `;
        }

        const sectionSummary = document.getElementById('section-summary');
        if (sectionSummary) {
            const sections = Array.isArray(this.config.sections) ? [...this.config.sections] : [];
            sections.sort((a, b) => (a.display_order || 0) - (b.display_order || 0));

            if (sections.length === 0) {
                sectionSummary.innerHTML = '<p class="text-xs text-slate-500">No sections configured</p>';
            } else {
                sectionSummary.innerHTML = sections.map((section) => {
                    const fields = Array.isArray(section.fields) ? section.fields.length : 0;
                    const repeatable = section.repeatable ? 'Repeatable' : 'Single';
                    return `
                        <div class="rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 p-2">
                            <p class="text-xs font-semibold text-slate-700 dark:text-slate-200">${this.escapeHtml(section.section_label || section.section_id || 'Section')}</p>
                            <p class="text-[11px] text-slate-500">${this.escapeHtml(section.section_id || '')} · ${fields} fields · ${repeatable}</p>
                        </div>
                    `;
                }).join('');
            }
        }

        const editor = document.getElementById('config-json-editor');
        if (editor) {
            editor.value = JSON.stringify(this.config, null, 2);
        }
    }

    async saveConfig() {
        try {
            const editor = document.getElementById('config-json-editor');
            if (!editor) return;

            let parsed;
            try {
                parsed = JSON.parse(editor.value);
            } catch (e) {
                window.showUIPopup('Invalid JSON. Please fix formatting before saving.');
                return;
            }

            const saveBtn = document.getElementById('save-config-btn');
            if (saveBtn) {
                saveBtn.disabled = true;
                saveBtn.textContent = 'Saving...';
            }

            const response = await fetch(`/api/v1/hospitals/${encodeURIComponent(this.hospitalId)}/prescription-config`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ config: parsed })
            });
            const data = await response.json();

            if (!response.ok || !data.success) {
                window.showUIPopup(data.message || 'Failed to save config');
                return;
            }

            this.config = data.config || parsed;
            this.source = 'hospital';
            this.render();
            window.showUIPopup('Prescription config saved');
        } catch (error) {
            console.error('Failed to save config:', error);
            window.showUIPopup('Failed to save config');
        } finally {
            const saveBtn = document.getElementById('save-config-btn');
            if (saveBtn) {
                saveBtn.disabled = false;
                saveBtn.textContent = 'Save Config';
            }
        }
    }

    async generateFromDefault() {
        const proceed = confirm('Generate config from default template? This will overwrite current file for this hospital.');
        if (!proceed) return;

        try {
            const button = document.getElementById('generate-default-btn');
            if (button) {
                button.disabled = true;
                button.textContent = 'Generating...';
            }

            const response = await fetch(`/api/v1/hospitals/${encodeURIComponent(this.hospitalId)}/prescription-config/generate-default`, {
                method: 'POST'
            });
            const data = await response.json();

            if (!response.ok || !data.success) {
                window.showUIPopup(data.message || 'Failed to generate config from default');
                return;
            }

            this.config = data.config || {};
            this.source = 'hospital';
            this.render();
            window.showUIPopup('Generated and saved from default template');
        } catch (error) {
            console.error('Failed to generate from default:', error);
            window.showUIPopup('Failed to generate config');
        } finally {
            const button = document.getElementById('generate-default-btn');
            if (button) {
                button.disabled = false;
                button.textContent = 'Generate from Default';
            }
        }
    }

    showLoading() {
        document.getElementById('loading-state')?.classList.remove('hidden');
        document.getElementById('error-state')?.classList.add('hidden');
        document.getElementById('config-content')?.classList.add('hidden');
    }

    showError(message) {
        document.getElementById('loading-state')?.classList.add('hidden');
        document.getElementById('config-content')?.classList.add('hidden');
        document.getElementById('error-state')?.classList.remove('hidden');
        const errorMessage = document.getElementById('error-message');
        if (errorMessage) errorMessage.textContent = message;
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = String(text || '');
        return div.innerHTML;
    }
}

document.addEventListener('DOMContentLoaded', () => {
    const manager = new PrescriptionConfigSettingsManager();
    window.prescriptionConfigSettings = manager;

    const backBtn = document.getElementById('back-btn');
    if (backBtn) {
        backBtn.onclick = () => {
            const hospitalId = manager.hospitalId || selectedHospitalId;
            if (hospitalId) {
                window.navigateWithTransition(`/hospital-settings/${encodeURIComponent(hospitalId)}`);
            } else {
                window.navigateWithTransition('/hospital-settings');
            }
        };
    }
});

