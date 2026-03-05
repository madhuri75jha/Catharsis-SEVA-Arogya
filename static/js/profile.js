/**
 * Profile Page JavaScript
 * Handles profile data fetching and display
 */

class ProfileManager {
    constructor() {
        this.profile = null;
        this.init();
    }
    
    init() {
        this.fetchProfile();
    }
    
    async fetchProfile() {
        try {
            const response = await fetch('/api/v1/profile');
            
            if (!response.ok) {
                this.showError(`HTTP error! status: ${response.status}`);
                return;
            }
            
            const data = await response.json();
            
            if (data.success) {
                this.profile = data.profile;
                this.renderProfile();
            } else {
                this.showError(data.message || 'Failed to load profile');
            }
        } catch (error) {
            console.error('Error fetching profile:', error);
            this.showError('An error occurred while loading the profile');
        }
    }
    
    renderProfile() {
        // Hide loading, show content
        document.getElementById('loading-state')?.classList.add('hidden');
        document.getElementById('profile-content')?.classList.remove('hidden');
        
        // Profile initials
        const initialsEl = document.getElementById('profile-initials');
        if (initialsEl) {
            initialsEl.textContent = this.getInitials(this.profile.name || this.profile.email);
        }
        
        // Name
        const nameEl = document.getElementById('profile-name');
        if (nameEl) {
            nameEl.textContent = this.profile.name || this.profile.email;
        }
        
        // Email
        const emailEl = document.getElementById('profile-email');
        if (emailEl) {
            emailEl.textContent = this.profile.email || this.profile.user_id;
        }
        
        // Role
        const roleEl = document.getElementById('profile-role');
        if (roleEl) {
            roleEl.textContent = this.formatRole(this.profile.role);
        }
        
        // Specialty (if available)
        if (this.profile.specialty) {
            const specialtySection = document.getElementById('specialty-section');
            const specialtyEl = document.getElementById('profile-specialty');
            if (specialtySection && specialtyEl) {
                specialtySection.classList.remove('hidden');
                specialtyEl.textContent = this.profile.specialty;
            }
        }
        
        // Hospital (if available)
        if (this.profile.hospital_name) {
            const hospitalSection = document.getElementById('hospital-section');
            const hospitalEl = document.getElementById('profile-hospital');
            if (hospitalSection && hospitalEl) {
                hospitalSection.classList.remove('hidden');
                hospitalEl.textContent = this.profile.hospital_name;
            }
        }
        
        // Availability (if available)
        if (this.profile.availability) {
            const availabilitySection = document.getElementById('availability-section');
            const availabilityEl = document.getElementById('profile-availability');
            if (availabilitySection && availabilityEl) {
                availabilitySection.classList.remove('hidden');
                availabilityEl.textContent = this.profile.availability;
            }
        }
        
        // Signature (if available)
        if (this.profile.signature_url) {
            const signatureSection = document.getElementById('signature-section');
            const signatureEl = document.getElementById('profile-signature');
            if (signatureSection && signatureEl) {
                signatureSection.classList.remove('hidden');
                signatureEl.src = this.profile.signature_url;
            }
        }
    }
    
    showError(message) {
        document.getElementById('loading-state')?.classList.add('hidden');
        document.getElementById('profile-content')?.classList.add('hidden');
        
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
    
    formatRole(role) {
        const roleMap = {
            'Doctor': 'Doctor',
            'HospitalAdmin': 'Hospital Admin',
            'DeveloperAdmin': 'Developer Admin'
        };
        return roleMap[role] || role;
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    new ProfileManager();
});
