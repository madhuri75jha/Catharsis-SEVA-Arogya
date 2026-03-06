/**
 * Prescription Detail Page JavaScript
 * Handles prescription detail fetching, display, and actions (download PDF, delete, restore)
 */

class PrescriptionDetailManager {
    constructor(prescriptionId) {
        this.prescriptionId = prescriptionId;
        this.prescription = null;
        this.permissions = null;
        
        this.init();
    }
    
    init() {
        this.fetchPrescription();
    }
    
    async fetchPrescription() {
        try {
            const response = await fetch(`/api/v1/prescriptions/${this.prescriptionId}`);
            
            if (!response.ok) {
                if (response.status === 404) {
                    this.showError('Prescription not found');
                } else if (response.status === 403) {
                    this.showError('You do not have permission to view this prescription');
                } else {
                    this.showError(`HTTP error! status: ${response.status}`);
                }
                return;
            }
            
            const data = await response.json();
            
            if (data.success) {
                this.prescription = data.prescription;
                this.permissions = data.permissions;
                this.renderPrescription();
            } else {
                this.showError(data.message || 'Failed to load prescription');
            }
        } catch (error) {
            console.error('Error fetching prescription:', error);
            this.showError('An error occurred while loading the prescription');
        }
    }
    
    renderPrescription() {
        // Hide loading, show content
        document.getElementById('loading-state')?.classList.add('hidden');
        document.getElementById('prescription-content')?.classList.remove('hidden');
        
        // Render patient info
        this.renderPatientInfo();
        
        // Render audio files if available
        if (this.prescription.audio_files && this.prescription.audio_files.length > 0) {
            this.renderAudioFiles();
        }
        
        // Render transcription if available
        if (this.prescription.transcription_text) {
            this.renderTranscription();
        }
        
        // Render sections if available
        if (this.prescription.sections && this.prescription.sections.length > 0) {
            this.renderSections();
        }
        
        // Render action buttons based on permissions
        this.renderActions();
    }
    
    renderPatientInfo() {
        // Patient initials
        const initialsEl = document.getElementById('patient-initials');
        if (initialsEl) {
            initialsEl.textContent = this.getInitials(this.prescription.patient_name);
        }
        
        // Patient name
        const nameEl = document.getElementById('patient-name');
        if (nameEl) {
            nameEl.textContent = this.prescription.patient_name;
        }
        
        // Prescription ID
        const idEl = document.getElementById('prescription-id');
        if (idEl) {
            idEl.textContent = `#${this.prescription.prescription_id}`;
        }
        
        // State badge
        const stateEl = document.getElementById('state-badge');
        if (stateEl) {
            stateEl.className = `state-badge state-${this.prescription.state.toLowerCase()}`;
            stateEl.textContent = this.formatState(this.prescription.state);
        }
        
        // Created date
        const createdEl = document.getElementById('created-date');
        if (createdEl) {
            createdEl.textContent = this.formatDateTime(this.prescription.created_at);
        }
        
        // Doctor name
        const doctorEl = document.getElementById('doctor-name');
        if (doctorEl) {
            doctorEl.textContent = this.prescription.created_by_doctor_id || 'Unknown';
        }
    }
    
    renderAudioFiles() {
        const section = document.getElementById('audio-section');
        const container = document.getElementById('audio-files-container');
        
        if (!section || !container) return;
        
        section.classList.remove('hidden');
        container.innerHTML = '';
        
        this.prescription.audio_files.forEach((audioFile, index) => {
            const audioCard = document.createElement('div');
            audioCard.className = 'bg-slate-50 dark:bg-slate-900/50 rounded-lg p-3';
            audioCard.innerHTML = `
                <div class="flex items-center gap-3">
                    <span class="material-symbols-outlined text-primary">audio_file</span>
                    <div class="flex-1">
                        <p class="text-sm font-medium text-slate-700 dark:text-slate-300">Recording ${index + 1}</p>
                        <p class="text-xs text-slate-500">${audioFile.s3_key || 'Audio file'}</p>
                    </div>
                </div>
                <audio controls class="w-full mt-2" src="${audioFile.url || ''}">
                    Your browser does not support the audio element.
                </audio>
            `;
            container.appendChild(audioCard);
        });
    }
    
    renderTranscription() {
        const section = document.getElementById('transcription-section');
        const textEl = document.getElementById('transcription-text');
        
        if (!section || !textEl) return;
        
        section.classList.remove('hidden');
        textEl.textContent = this.prescription.transcription_text;
    }
    
    renderSections() {
        const container = document.getElementById('sections-container');
        const listEl = document.getElementById('sections-list');
        
        if (!container || !listEl) return;
        
        container.classList.remove('hidden');
        listEl.innerHTML = '';
        
        // Sort sections by order
        const sortedSections = [...this.prescription.sections].sort((a, b) => a.order - b.order);
        
        sortedSections.forEach(section => {
            const sectionCard = document.createElement('div');
            sectionCard.className = 'section-card';
            
            let statusBadge = '';
            if (section.status) {
                const statusClass = section.status.toLowerCase();
                statusBadge = `<span class="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-${statusClass === 'approved' ? 'green' : statusClass === 'rejected' ? 'red' : 'slate'}-100 text-${statusClass === 'approved' ? 'green' : statusClass === 'rejected' ? 'red' : 'slate'}-600">${section.status}</span>`;
            }
            
            sectionCard.innerHTML = `
                <div class="flex items-center justify-between mb-2">
                    <h4 class="section-title">${this.escapeHtml(section.title)}</h4>
                    ${statusBadge}
                </div>
                <div class="section-content">${this.escapeHtml(section.content || 'No content')}</div>
            `;
            
            listEl.appendChild(sectionCard);
        });
    }
    
    renderActions() {
        // Download PDF button
        if (this.permissions?.can_download_pdf) {
            const downloadBtn = document.getElementById('download-pdf-btn');
            if (downloadBtn) {
                downloadBtn.classList.remove('hidden');
                downloadBtn.onclick = () => this.handleDownloadPDF();
            }
        }
        
        // Delete button
        if (this.permissions?.can_delete && this.prescription.state !== 'Deleted') {
            const deleteBtn = document.getElementById('delete-btn');
            if (deleteBtn) {
                deleteBtn.classList.remove('hidden');
                deleteBtn.onclick = () => this.handleDelete();
            }
        }
        
        // Restore button
        if (this.permissions?.can_restore && this.prescription.state === 'Deleted') {
            const restoreBtn = document.getElementById('restore-btn');
            if (restoreBtn) {
                restoreBtn.classList.remove('hidden');
                restoreBtn.onclick = () => this.handleRestore();
            }
            
            // Show restore deadline
            if (this.prescription.deleted_at) {
                const deadlineEl = document.getElementById('restore-deadline');
                const dateEl = document.getElementById('deadline-date');
                if (deadlineEl && dateEl) {
                    const deletedDate = new Date(this.prescription.deleted_at);
                    const deadlineDate = new Date(deletedDate.getTime() + 30 * 24 * 60 * 60 * 1000);
                    dateEl.textContent = this.formatDate(deadlineDate);
                    deadlineEl.classList.remove('hidden');
                }
            }
        }
    }
    
    async handleDownloadPDF() {
        try {
            const optionsResponse = await fetch(`/api/v1/prescriptions/${this.prescriptionId}/pdf-options`);
            const optionsData = await optionsResponse.json();
            if (!optionsResponse.ok || !optionsData.success) {
                window.showUIPopup(optionsData.message || 'Failed to load PDF options');
                return;
            }

            let selectedLanguage = {
                code: optionsData.default_language_code || 'en',
                name: optionsData.default_language_name || 'English'
            };
            if (optionsData.requires_language_selection) {
                if (typeof window.showPrescriptionLanguagePicker !== 'function') {
                    window.showUIPopup('Language picker is unavailable');
                    return;
                }
                const picked = await window.showPrescriptionLanguagePicker(
                    optionsData.languages || [],
                    selectedLanguage.code
                );
                if (!picked) {
                    return;
                }
                selectedLanguage = picked;
            }

            const downloadBtn = document.getElementById('download-pdf-btn');
            if (downloadBtn) {
                downloadBtn.disabled = true;
                downloadBtn.innerHTML = '<span class="inline-block animate-spin rounded-full h-5 w-5 border-b-2 border-white"></span><span>Generating PDF...</span>';
            }
            
            const response = await fetch(`/api/v1/prescriptions/${this.prescriptionId}/pdf`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    language_code: selectedLanguage.code || 'en',
                    language_name: selectedLanguage.name || 'English'
                })
            });
            
            const data = await response.json();
            
            if (data.success && data.download_url) {
                // Open PDF in new tab
                window.open(data.download_url, '_blank');
            } else {
                window.showUIPopup(data.message || 'Failed to generate PDF');
            }
        } catch (error) {
            console.error('Error generating PDF:', error);
            window.showUIPopup('An error occurred while generating the PDF');
        } finally {
            const downloadBtn = document.getElementById('download-pdf-btn');
            if (downloadBtn) {
                downloadBtn.disabled = false;
                downloadBtn.innerHTML = '<span class="material-symbols-outlined text-[20px]">download</span><span>Download PDF</span>';
            }
        }
    }
    
    handleDelete() {
        const modal = document.getElementById('delete-modal');
        if (modal) {
            modal.classList.remove('hidden');
        }
    }
    
    async confirmDelete() {
        try {
            const response = await fetch(`/api/v1/prescriptions/${this.prescriptionId}`, {
                method: 'DELETE'
            });
            
            const data = await response.json();
            
            if (data.success) {
                // Reload page to show updated state
                window.location.reload();
            } else {
                window.showUIPopup(data.message || 'Failed to delete prescription');
            }
        } catch (error) {
            console.error('Error deleting prescription:', error);
            window.showUIPopup('An error occurred while deleting the prescription');
        } finally {
            this.cancelDelete();
        }
    }
    
    cancelDelete() {
        const modal = document.getElementById('delete-modal');
        if (modal) {
            modal.classList.add('hidden');
        }
    }
    
    async handleRestore() {
        if (!confirm('Are you sure you want to restore this prescription?')) {
            return;
        }
        
        try {
            const response = await fetch(`/api/v1/prescriptions/${this.prescriptionId}/restore`, {
                method: 'POST'
            });
            
            const data = await response.json();
            
            if (data.success) {
                // Reload page to show updated state
                window.location.reload();
            } else {
                window.showUIPopup(data.message || 'Failed to restore prescription');
            }
        } catch (error) {
            console.error('Error restoring prescription:', error);
            window.showUIPopup('An error occurred while restoring the prescription');
        }
    }
    
    showError(message) {
        document.getElementById('loading-state')?.classList.add('hidden');
        document.getElementById('prescription-content')?.classList.add('hidden');
        
        const errorState = document.getElementById('error-state');
        const errorMessage = document.getElementById('error-message');
        
        if (errorState) errorState.classList.remove('hidden');
        if (errorMessage) errorMessage.textContent = message;
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
    
    formatDateTime(dateString) {
        if (!dateString) return 'N/A';
        const date = new Date(dateString);
        return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' }) + ' ' +
               date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
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

// Global functions for modal
function cancelDelete() {
    if (window.prescriptionManager) {
        window.prescriptionManager.cancelDelete();
    }
}

function confirmDelete() {
    if (window.prescriptionManager) {
        window.prescriptionManager.confirmDelete();
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    if (typeof prescriptionId !== 'undefined') {
        window.prescriptionManager = new PrescriptionDetailManager(prescriptionId);
    }
});

