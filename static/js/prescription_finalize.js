/**
 * Prescription Finalization Page JavaScript
 * Handles section approval/rejection, inline editing, and finalization
 */

class PrescriptionFinalizeManager {
    constructor(prescriptionId) {
        this.prescriptionId = prescriptionId;
        this.prescription = null;
        this.sections = [];
        this.editingSection = null;
        
        this.init();
    }
    
    async init() {
        await this.fetchPrescription();
        
        // If prescription is in Draft state, transition to InProgress
        if (this.prescription && this.prescription.state === 'Draft') {
            await this.transitionToInProgress();
        }
    }
    
    async fetchPrescription() {
        try {
            const response = await fetch(`/api/v1/prescriptions/${this.prescriptionId}`);
            
            if (!response.ok) {
                if (response.status === 404) {
                    this.showError('Prescription not found');
                } else if (response.status === 403) {
                    this.showError('You do not have permission to edit this prescription');
                } else {
                    this.showError(`HTTP error! status: ${response.status}`);
                }
                return;
            }
            
            const data = await response.json();
            
            if (data.success) {
                this.prescription = data.prescription;
                this.sections = data.prescription.sections || [];
                
                // Check if prescription can be finalized
                if (this.prescription.state === 'Finalized') {
                    this.showError('This prescription has already been finalized');
                    return;
                }
                
                if (this.prescription.state === 'Deleted') {
                    this.showError('This prescription has been deleted');
                    return;
                }
                
                this.renderPrescription();
            } else {
                this.showError(data.message || 'Failed to load prescription');
            }
        } catch (error) {
            console.error('Error fetching prescription:', error);
            this.showError('An error occurred while loading the prescription');
        }
    }
    
    async transitionToInProgress() {
        try {
            // Get bedrock_payload from prescription
            const bedrockPayload = this.prescription.bedrock_payload;
            
            if (!bedrockPayload) {
                this.showError('No Bedrock content available. Please generate prescription content first.');
                return;
            }
            
            const response = await fetch(`/api/v1/prescriptions/${this.prescriptionId}/transition-to-in-progress`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ bedrock_payload: bedrockPayload })
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.prescription.state = data.state;
                this.sections = data.sections || [];
                this.renderPrescription();
            } else {
                this.showError(data.message || 'Failed to load prescription content');
            }
        } catch (error) {
            console.error('Error transitioning to InProgress:', error);
            this.showError('An error occurred while loading prescription content');
        }
    }
    
    renderPrescription() {
        // Hide loading, show content
        document.getElementById('loading-state')?.classList.add('hidden');
        document.getElementById('prescription-content')?.classList.remove('hidden');
        
        // Render patient info
        this.renderPatientInfo();
        
        // Render sections
        this.renderSections();
        
        // Update progress
        this.updateProgress();
    }
    
    renderPatientInfo() {
        const initialsEl = document.getElementById('patient-initials');
        if (initialsEl) {
            initialsEl.textContent = this.getInitials(this.prescription.patient_name);
        }
        
        const nameEl = document.getElementById('patient-name');
        if (nameEl) {
            nameEl.textContent = this.prescription.patient_name;
        }
        
        const idEl = document.getElementById('prescription-id');
        if (idEl) {
            idEl.textContent = `#${this.prescription.prescription_id}`;
        }
    }
    
    renderSections() {
        const container = document.getElementById('sections-container');
        if (!container) return;
        
        container.innerHTML = '';
        
        // Sort sections by order
        const sortedSections = [...this.sections].sort((a, b) => a.order - b.order);
        
        sortedSections.forEach(section => {
            const sectionCard = this.createSectionCard(section);
            container.appendChild(sectionCard);
        });
    }
    
    createSectionCard(section) {
        const card = document.createElement('div');
        card.className = `section-card section-${section.status.toLowerCase()}`;
        card.id = `section-${section.key}`;
        
        // Header
        const header = document.createElement('div');
        header.className = 'section-header';
        header.innerHTML = `
            <h3 class="section-title">
                ${this.escapeHtml(section.title)}
                ${section.required ? '<span class="required-indicator">*</span>' : ''}
            </h3>
            <span class="section-badge badge-${section.status.toLowerCase()}">${section.status}</span>
        `;
        card.appendChild(header);
        
        // Content (editable if rejected)
        if (this.editingSection === section.key) {
            const textarea = document.createElement('textarea');
            textarea.className = 'section-content-editable';
            textarea.rows = 6;
            textarea.value = section.content || '';
            textarea.id = `content-${section.key}`;
            card.appendChild(textarea);
        } else {
            const content = document.createElement('div');
            content.className = 'section-content';
            content.textContent = section.content || 'No content';
            card.appendChild(content);
        }
        
        // Actions
        const actions = document.createElement('div');
        actions.className = 'section-actions';
        
        if (this.editingSection === section.key) {
            // Save and Cancel buttons
            actions.innerHTML = `
                <button class="btn-save" onclick="window.finalizeManager.saveSection('${section.key}')">
                    <span class="material-symbols-outlined text-[16px]">save</span>
                    Save
                </button>
                <button class="btn-cancel" onclick="window.finalizeManager.cancelEdit()">
                    Cancel
                </button>
            `;
        } else if (section.status === 'Pending' || section.status === 'Rejected') {
            // Approve and Reject buttons
            actions.innerHTML = `
                <button class="btn-approve" onclick="window.finalizeManager.approveSection('${section.key}')">
                    <span class="material-symbols-outlined text-[16px]">check</span>
                    Approve
                </button>
                <button class="btn-reject" onclick="window.finalizeManager.rejectSection('${section.key}')">
                    <span class="material-symbols-outlined text-[16px]">close</span>
                    Reject
                </button>
            `;
        } else if (section.status === 'Approved') {
            // Show approved message
            actions.innerHTML = `
                <div class="flex-1 text-center text-sm text-green-600 dark:text-green-400 font-medium">
                    ✓ Section approved
                </div>
            `;
        }
        
        card.appendChild(actions);
        
        return card;
    }
    
    async approveSection(sectionKey) {
        try {
            const response = await fetch(`/api/v1/prescriptions/${this.prescriptionId}/sections/${sectionKey}/approve`, {
                method: 'POST'
            });
            
            const data = await response.json();
            
            if (data.success) {
                // Update section status
                const section = this.sections.find(s => s.key === sectionKey);
                if (section) {
                    section.status = 'Approved';
                }
                
                // Re-render sections
                this.renderSections();
                this.updateProgress();
            } else {
                alert(data.message || 'Failed to approve section');
            }
        } catch (error) {
            console.error('Error approving section:', error);
            alert('An error occurred while approving the section');
        }
    }
    
    async rejectSection(sectionKey) {
        try {
            const response = await fetch(`/api/v1/prescriptions/${this.prescriptionId}/sections/${sectionKey}/reject`, {
                method: 'POST'
            });
            
            const data = await response.json();
            
            if (data.success) {
                // Update section status
                const section = this.sections.find(s => s.key === sectionKey);
                if (section) {
                    section.status = 'Rejected';
                }
                
                // Enable editing for rejected section
                this.editingSection = sectionKey;
                
                // Re-render sections
                this.renderSections();
                this.updateProgress();
            } else {
                alert(data.message || 'Failed to reject section');
            }
        } catch (error) {
            console.error('Error rejecting section:', error);
            alert('An error occurred while rejecting the section');
        }
    }
    
    async saveSection(sectionKey) {
        try {
            const textarea = document.getElementById(`content-${sectionKey}`);
            if (!textarea) return;
            
            const newContent = textarea.value.trim();
            
            if (!newContent) {
                alert('Section content cannot be empty');
                return;
            }
            
            const response = await fetch(`/api/v1/prescriptions/${this.prescriptionId}/sections/${sectionKey}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ content: newContent })
            });
            
            const data = await response.json();
            
            if (data.success) {
                // Update section content and status
                const section = this.sections.find(s => s.key === sectionKey);
                if (section) {
                    section.content = newContent;
                    section.status = 'Pending';
                }
                
                // Clear editing state
                this.editingSection = null;
                
                // Re-render sections
                this.renderSections();
                this.updateProgress();
            } else {
                alert(data.message || 'Failed to save section');
            }
        } catch (error) {
            console.error('Error saving section:', error);
            alert('An error occurred while saving the section');
        }
    }
    
    cancelEdit() {
        this.editingSection = null;
        this.renderSections();
    }
    
    updateProgress() {
        const requiredSections = this.sections.filter(s => s.required);
        const approvedSections = requiredSections.filter(s => s.status === 'Approved');
        
        const approvedCount = approvedSections.length;
        const requiredCount = requiredSections.length;
        const percentage = requiredCount > 0 ? Math.round((approvedCount / requiredCount) * 100) : 0;
        
        // Update progress text
        const approvedCountEl = document.getElementById('approved-count');
        const requiredCountEl = document.getElementById('required-count');
        const percentageEl = document.getElementById('progress-percentage');
        
        if (approvedCountEl) approvedCountEl.textContent = approvedCount;
        if (requiredCountEl) requiredCountEl.textContent = requiredCount;
        if (percentageEl) percentageEl.textContent = `${percentage}%`;
        
        // Update progress bar
        const progressBar = document.getElementById('progress-bar');
        if (progressBar) {
            progressBar.style.width = `${percentage}%`;
        }
        
        // Enable/disable finalize button
        const finalizeBtn = document.getElementById('finalize-btn');
        if (finalizeBtn) {
            finalizeBtn.disabled = approvedCount < requiredCount;
        }
    }
    
    async handleFinalize() {
        if (!confirm('Are you sure you want to finalize this prescription? This action cannot be undone.')) {
            return;
        }
        
        try {
            const finalizeBtn = document.getElementById('finalize-btn');
            if (finalizeBtn) {
                finalizeBtn.disabled = true;
                finalizeBtn.innerHTML = '<span class="inline-block animate-spin rounded-full h-5 w-5 border-b-2 border-white"></span><span>Finalizing...</span>';
            }
            
            const response = await fetch(`/api/v1/prescriptions/${this.prescriptionId}/finalize`, {
                method: 'POST'
            });
            
            const data = await response.json();
            
            if (data.success) {
                // Redirect to thank you page
                window.navigateWithTransition(data.redirect_url || '/thank-you');
            } else {
                alert(data.message || 'Failed to finalize prescription');
                
                if (finalizeBtn) {
                    finalizeBtn.disabled = false;
                    finalizeBtn.innerHTML = '<span class="material-symbols-outlined text-[20px]">check_circle</span><span>Finalize Prescription</span>';
                }
            }
        } catch (error) {
            console.error('Error finalizing prescription:', error);
            alert('An error occurred while finalizing the prescription');
            
            const finalizeBtn = document.getElementById('finalize-btn');
            if (finalizeBtn) {
                finalizeBtn.disabled = false;
                finalizeBtn.innerHTML = '<span class="material-symbols-outlined text-[20px]">check_circle</span><span>Finalize Prescription</span>';
            }
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
    
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    if (typeof prescriptionId !== 'undefined') {
        window.finalizeManager = new PrescriptionFinalizeManager(prescriptionId);
        
        // Setup finalize button click handler
        const finalizeBtn = document.getElementById('finalize-btn');
        if (finalizeBtn) {
            finalizeBtn.addEventListener('click', () => {
                window.finalizeManager.handleFinalize();
            });
        }
    }
});
