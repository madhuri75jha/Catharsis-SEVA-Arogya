/**
 * Hospital Settings Page JavaScript
 * Handles hospital information editing and doctor management
 */

class HospitalSettingsManager {
    constructor() {
        this.hospital = null;
        this.doctors = [];
        this.hospitalId = null;
        this.userRole = null;
        this.isDeveloperAdmin = false;
        
        this.init();
    }
    
    async init() {
        await this.fetchProfile();
        this.setupDeveloperNavigation();

        if (this.hospitalId) {
            await this.fetchHospital();
            await this.fetchDoctors();
        } else if (!this.isDeveloperAdmin) {
            this.showError('No hospital associated with your account');
        } else {
            window.navigateWithTransition('/hospitals');
        }
    }
    
    async fetchProfile() {
        try {
            const response = await fetch('/api/v1/profile');
            const data = await response.json();
            
            if (!data.success || !data.profile) {
                this.showError('Failed to load profile');
                return;
            }

            this.userRole = data.profile.role;
            this.isDeveloperAdmin = this.userRole === 'DeveloperAdmin';

            if (this.isDeveloperAdmin) {
                this.hospitalId = this.getHospitalIdFromPath();
            } else if (data.profile.hospital_id) {
                this.hospitalId = data.profile.hospital_id;
            }
        } catch (error) {
            console.error('Error fetching profile:', error);
            this.showError('Failed to load profile');
        }
    }
    
    async fetchHospital() {
        try {
            const response = await fetch(`/api/v1/hospitals/${this.hospitalId}`);
            
            if (!response.ok) {
                if (response.status === 403) {
                    this.showError('You do not have permission to manage hospital settings');
                } else {
                    this.showError(`HTTP error! status: ${response.status}`);
                }
                return;
            }
            
            const data = await response.json();
            
            if (data.success) {
                this.hospital = data.hospital;
                this.renderHospital();
            } else {
                this.showError(data.message || 'Failed to load hospital');
            }
        } catch (error) {
            console.error('Error fetching hospital:', error);
            this.showError('An error occurred while loading hospital information');
        }
    }
    
    async fetchDoctors() {
        try {
            const response = await fetch(`/api/v1/hospitals/${this.hospitalId}/doctors`);
            
            if (!response.ok) {
                console.error('Failed to fetch doctors');
                return;
            }
            
            const data = await response.json();
            
            if (data.success) {
                this.doctors = data.doctors || [];
                this.renderDoctors();
            }
        } catch (error) {
            console.error('Error fetching doctors:', error);
        }
    }
    
    renderHospital() {
        // Hide loading, show content
        document.getElementById('loading-state')?.classList.add('hidden');
        document.getElementById('settings-content')?.classList.remove('hidden');
        
        // Populate form fields
        document.getElementById('hospital-name').value = this.hospital.name || '';
        document.getElementById('hospital-address').value = this.hospital.address || '';
        document.getElementById('hospital-phone').value = this.hospital.phone || '';
        document.getElementById('hospital-email').value = this.hospital.email || '';
        document.getElementById('hospital-registration').value = this.hospital.registration_number || '';
        document.getElementById('hospital-website').value = this.hospital.website || '';
        document.getElementById('hospital-logo').value = this.hospital.logo_url || '';
        
        // Setup save button
        const saveBtn = document.getElementById('save-hospital-btn');
        if (saveBtn) {
            saveBtn.onclick = () => this.handleSaveHospital();
        }
        
        // Setup add doctor button
        const addDoctorBtn = document.getElementById('add-doctor-btn');
        if (addDoctorBtn) {
            addDoctorBtn.onclick = () => this.showAddDoctorModal();
        }

        const configBtn = document.getElementById('manage-prescription-config-btn');
        if (configBtn && this.hospitalId) {
            configBtn.onclick = () => {
                window.navigateWithTransition(`/hospital-settings/${encodeURIComponent(this.hospitalId)}/prescription-config`);
            };
        }
    }
    
    renderDoctors() {
        const listEl = document.getElementById('doctors-list');
        const emptyEl = document.getElementById('doctors-empty');
        
        if (!listEl) return;
        
        if (this.doctors.length === 0) {
            listEl.classList.add('hidden');
            if (emptyEl) emptyEl.classList.remove('hidden');
            return;
        }
        
        listEl.classList.remove('hidden');
        if (emptyEl) emptyEl.classList.add('hidden');
        
        listEl.innerHTML = '';
        
        this.doctors.forEach(doctor => {
            const doctorCard = document.createElement('div');
            doctorCard.className = 'bg-slate-50 dark:bg-slate-900/50 rounded-lg p-3 flex items-center justify-between';
            doctorCard.innerHTML = `
                <div class="flex-1">
                    <p class="text-sm font-medium text-slate-800 dark:text-white">${this.escapeHtml(doctor.name)}</p>
                    <p class="text-xs text-slate-500">${this.escapeHtml(doctor.specialty || 'No specialty')}</p>
                    <p class="text-xs text-slate-400">${this.escapeHtml(doctor.doctor_id)}</p>
                </div>
                <button 
                    onclick="window.hospitalSettings.removeDoctor('${doctor.doctor_id}')"
                    class="flex items-center justify-center w-8 h-8 rounded-full bg-red-100 dark:bg-red-900/30 text-red-600 dark:text-red-400 hover:bg-red-200 dark:hover:bg-red-900/50 transition-colors"
                >
                    <span class="material-symbols-outlined text-[18px]">delete</span>
                </button>
            `;
            listEl.appendChild(doctorCard);
        });
    }
    
    async handleSaveHospital() {
        try {
            const saveBtn = document.getElementById('save-hospital-btn');
            if (saveBtn) {
                saveBtn.disabled = true;
                saveBtn.textContent = 'Saving...';
            }
            
            const data = {
                name: document.getElementById('hospital-name').value.trim(),
                address: document.getElementById('hospital-address').value.trim(),
                phone: document.getElementById('hospital-phone').value.trim(),
                email: document.getElementById('hospital-email').value.trim(),
                registration_number: document.getElementById('hospital-registration').value.trim(),
                website: document.getElementById('hospital-website').value.trim(),
                logo_url: document.getElementById('hospital-logo').value.trim()
            };
            
            if (!data.name) {
                alert('Hospital name is required');
                return;
            }
            
            const response = await fetch(`/api/v1/hospitals/${this.hospitalId}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(data)
            });
            
            const result = await response.json();
            
            if (result.success) {
                alert('Hospital information saved successfully');
                await this.fetchHospital();
            } else {
                alert(result.message || 'Failed to save hospital information');
            }
        } catch (error) {
            console.error('Error saving hospital:', error);
            alert('An error occurred while saving');
        } finally {
            const saveBtn = document.getElementById('save-hospital-btn');
            if (saveBtn) {
                saveBtn.disabled = false;
                saveBtn.textContent = 'Save Hospital Information';
            }
        }
    }
    
    showAddDoctorModal() {
        const modal = document.getElementById('add-doctor-modal');
        if (modal) {
            modal.classList.remove('hidden');
            
            // Clear form
            document.getElementById('new-doctor-id').value = '';
            document.getElementById('new-doctor-name').value = '';
            document.getElementById('new-doctor-specialty').value = '';
        }
    }
    
    cancelAddDoctor() {
        const modal = document.getElementById('add-doctor-modal');
        if (modal) {
            modal.classList.add('hidden');
        }
    }
    
    async confirmAddDoctor() {
        try {
            const doctorId = document.getElementById('new-doctor-id').value.trim();
            const name = document.getElementById('new-doctor-name').value.trim();
            const specialty = document.getElementById('new-doctor-specialty').value.trim();
            
            if (!doctorId || !name) {
                alert('Doctor ID and Name are required');
                return;
            }
            
            const response = await fetch(`/api/v1/hospitals/${this.hospitalId}/doctors`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    doctor_id: doctorId,
                    name: name,
                    specialty: specialty
                })
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.cancelAddDoctor();
                await this.fetchDoctors();
            } else {
                alert(data.message || 'Failed to add doctor');
            }
        } catch (error) {
            console.error('Error adding doctor:', error);
            alert('An error occurred while adding doctor');
        }
    }
    
    async removeDoctor(doctorId) {
        if (!confirm('Are you sure you want to remove this doctor?')) {
            return;
        }
        
        try {
            const response = await fetch(`/api/v1/hospitals/${this.hospitalId}/doctors/${doctorId}`, {
                method: 'DELETE'
            });
            
            const data = await response.json();
            
            if (data.success) {
                await this.fetchDoctors();
            } else {
                alert(data.message || 'Failed to remove doctor');
            }
        } catch (error) {
            console.error('Error removing doctor:', error);
            alert('An error occurred while removing doctor');
        }
    }
    
    showError(message) {
        document.getElementById('loading-state')?.classList.add('hidden');
        document.getElementById('settings-content')?.classList.add('hidden');
        
        const errorState = document.getElementById('error-state');
        const errorMessage = document.getElementById('error-message');
        
        if (errorState) errorState.classList.remove('hidden');
        if (errorMessage) errorMessage.textContent = message;
    }

    showLoading() {
        document.getElementById('loading-state')?.classList.remove('hidden');
        document.getElementById('error-state')?.classList.add('hidden');
        document.getElementById('settings-content')?.classList.add('hidden');
    }

    getHospitalIdFromPath() {
        const parts = window.location.pathname.split('/').filter(Boolean);
        if (parts.length >= 2 && parts[0] === 'hospital-settings') {
            return decodeURIComponent(parts[1]);
        }
        return null;
    }

    setupDeveloperNavigation() {
        const developerNav = document.getElementById('developer-nav');
        if (this.isDeveloperAdmin) {
            developerNav?.classList.remove('hidden');
        } else {
            developerNav?.classList.add('hidden');
        }
    }
    
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.hospitalSettings = new HospitalSettingsManager();
});
