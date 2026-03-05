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
            roleEl.textContent = this.profile.role_display || this.profile.role || 'Unknown';
        }

        // Last login and email verification
        const lastLoginEl = document.getElementById('profile-last-login');
        if (lastLoginEl) {
            lastLoginEl.textContent = this.formatDateTime(this.profile.last_login_at);
        }

        const emailVerifiedEl = document.getElementById('profile-email-verified');
        if (emailVerifiedEl) {
            if (this.profile.email_verified === true) {
                emailVerifiedEl.textContent = 'Yes';
            } else if (this.profile.email_verified === false) {
                emailVerifiedEl.textContent = 'No';
            } else {
                emailVerifiedEl.textContent = 'Unavailable';
            }
        }

        // Consultation metrics
        const metrics = this.profile.metrics || {};
        this.setText('metric-total', metrics.total_consultations ?? 0);
        this.setText('metric-completed', metrics.completed_consultations ?? 0);
        this.setText('metric-in-progress', metrics.in_progress_consultations ?? 0);
        this.renderActivityChart(metrics.consultation_trend_last_7_days || []);
        
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

    setText(elementId, value) {
        const element = document.getElementById(elementId);
        if (element) {
            element.textContent = String(value);
        }
    }

    formatDateTime(value) {
        if (!value) return 'Unavailable';
        try {
            const date = new Date(value);
            if (Number.isNaN(date.getTime())) return 'Unavailable';
            return date.toLocaleString([], {
                year: 'numeric',
                month: 'short',
                day: 'numeric',
                hour: '2-digit',
                minute: '2-digit'
            });
        } catch (error) {
            return 'Unavailable';
        }
    }

    renderActivityChart(points) {
        const chartEl = document.getElementById('profile-activity-chart');
        if (!chartEl) return;

        const data = Array.isArray(points) && points.length > 0
            ? points
            : [
                { label: 'Mon', count: 0 },
                { label: 'Tue', count: 0 },
                { label: 'Wed', count: 0 },
                { label: 'Thu', count: 0 },
                { label: 'Fri', count: 0 },
                { label: 'Sat', count: 0 },
                { label: 'Sun', count: 0 }
            ];

        const maxCount = Math.max(...data.map((item) => Number(item.count || 0)), 1);
        chartEl.innerHTML = '';

        data.forEach((item) => {
            const value = Number(item.count || 0);
            const barHeight = Math.max((value / maxCount) * 72, value > 0 ? 8 : 2);

            const wrapper = document.createElement('div');
            wrapper.className = 'flex-1 min-w-0 flex flex-col items-center justify-end';
            wrapper.innerHTML = `
                <span class="text-[10px] text-slate-500 mb-1">${value}</span>
                <div class="w-full rounded-t-md bg-primary/80" style="height:${barHeight}px"></div>
                <span class="text-[10px] text-slate-400 mt-1">${this.escapeHtml(item.label || '')}</span>
            `;
            chartEl.appendChild(wrapper);
        });
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    new ProfileManager();
});
