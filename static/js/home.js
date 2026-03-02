/**
 * Home Page JavaScript Module
 * Handles consultation display, fetching, and interaction
 */

// Global state
let allConsultations = [];
let isExpanded = false;

/**
 * Fetch consultations from API
 * @param {number} limit - Maximum number of consultations to retrieve
 * @returns {Promise<Array>} Array of consultation objects
 */
async function fetchConsultations(limit = 10) {
    try {
        const response = await fetch(`/api/consultations?limit=${limit}`);
        
        if (!response.ok) {
            if (response.status === 401) {
                // Authentication failure - redirect to login
                window.location.href = '/login';
                return [];
            }
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        
        if (data.success) {
            return data.consultations || [];
        } else {
            console.error('API returned error:', data.error);
            return [];
        }
    } catch (error) {
        console.error('Failed to fetch consultations:', error);
        return [];
    }
}

/**
 * Render consultation cards in the DOM
 * @param {Array} consultations - Array of consultation objects
 * @param {boolean} showAll - Whether to show all consultations or just first 2
 */
function renderConsultations(consultations, showAll = false) {
    const container = document.getElementById('consultations-container');
    const emptyState = document.getElementById('empty-state');
    const viewAllBtn = document.getElementById('view-all-btn');
    
    if (!container) {
        console.error('Consultations container not found');
        return;
    }
    
    // Clear existing content
    container.innerHTML = '';
    
    // Handle empty state
    if (!consultations || consultations.length === 0) {
        if (emptyState) {
            emptyState.classList.remove('hidden');
        }
        if (viewAllBtn) {
            viewAllBtn.classList.add('hidden');
        }
        return;
    }
    
    // Hide empty state
    if (emptyState) {
        emptyState.classList.add('hidden');
    }
    
    // Determine how many consultations to display
    const displayCount = showAll ? consultations.length : Math.min(2, consultations.length);
    const consultationsToRender = consultations.slice(0, displayCount);
    
    // Render consultation cards
    consultationsToRender.forEach(consultation => {
        const card = createConsultationCard(consultation);
        container.appendChild(card);
    });
    
    // Update "View All" button visibility and text
    if (viewAllBtn) {
        if (consultations.length > 2) {
            viewAllBtn.classList.remove('hidden');
            viewAllBtn.textContent = showAll ? 'Show Less' : 'View All';
        } else {
            viewAllBtn.classList.add('hidden');
        }
    }
}

/**
 * Create a consultation card DOM element
 * @param {Object} consultation - Consultation object
 * @returns {HTMLElement} Consultation card element
 */
function createConsultationCard(consultation) {
    const card = document.createElement('div');
    card.className = 'flex-shrink-0 flex items-center gap-3 bg-slate-50 dark:bg-slate-900 p-3 rounded-xl border border-slate-100 dark:border-slate-800 cursor-pointer hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors';
    card.onclick = () => handleConsultationClick(consultation.consultation_id);
    
    // Create initials avatar
    const avatar = document.createElement('div');
    avatar.className = 'size-8 rounded-full bg-blue-100 flex items-center justify-center text-primary text-xs font-bold';
    avatar.textContent = consultation.patient_initials || '?';
    
    // Create info container
    const infoContainer = document.createElement('div');
    infoContainer.className = 'flex-1';
    
    // Patient name
    const nameElement = document.createElement('p');
    nameElement.className = 'text-xs font-bold text-slate-800 dark:text-slate-200';
    nameElement.textContent = consultation.patient_name || 'Unknown Patient';
    
    // Timestamp and status container
    const metaContainer = document.createElement('div');
    metaContainer.className = 'flex items-center gap-2';
    
    // Timestamp
    const timeElement = document.createElement('p');
    timeElement.className = 'text-[10px] text-slate-500';
    timeElement.textContent = formatRelativeTime(consultation.created_at);
    
    // Status badge
    const statusBadge = getStatusBadge(consultation.status);
    
    // Assemble the card
    metaContainer.appendChild(timeElement);
    if (statusBadge) {
        metaContainer.appendChild(statusBadge);
    }
    
    infoContainer.appendChild(nameElement);
    infoContainer.appendChild(metaContainer);
    
    card.appendChild(avatar);
    card.appendChild(infoContainer);
    
    return card;
}

/**
 * Format ISO timestamp to relative time
 * @param {string} isoTimestamp - ISO 8601 timestamp string
 * @returns {string} Formatted relative time string
 */
function formatRelativeTime(isoTimestamp) {
    if (!isoTimestamp) {
        return 'Unknown';
    }
    
    const now = new Date();
    const then = new Date(isoTimestamp);
    const diffMs = now - then;
    const diffMinutes = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    
    if (diffMinutes < 1) {
        return 'Just now';
    } else if (diffMinutes < 60) {
        return `${diffMinutes} minute${diffMinutes !== 1 ? 's' : ''} ago`;
    } else if (diffHours < 24) {
        return `${diffHours} hour${diffHours !== 1 ? 's' : ''} ago`;
    } else {
        // Format as "MMM DD, YYYY"
        const options = { year: 'numeric', month: 'short', day: 'numeric' };
        return then.toLocaleDateString('en-US', options);
    }
}

/**
 * Get status badge HTML element
 * @param {string} status - Consultation status (COMPLETED, IN_PROGRESS, FAILED)
 * @returns {HTMLElement|null} Status badge element or null
 */
function getStatusBadge(status) {
    if (!status) {
        return null;
    }
    
    const badge = document.createElement('span');
    badge.className = 'text-[10px] px-2 py-0.5 rounded-full font-medium';
    
    switch (status.toUpperCase()) {
        case 'COMPLETED':
            badge.className += ' bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300';
            badge.textContent = 'Complete';
            break;
        case 'IN_PROGRESS':
            badge.className += ' bg-yellow-100 text-yellow-700 dark:bg-yellow-900 dark:text-yellow-300';
            badge.textContent = 'In Progress';
            break;
        case 'FAILED':
            badge.className += ' bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-300';
            badge.textContent = 'Failed';
            break;
        default:
            badge.className += ' bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300';
            badge.textContent = status;
    }
    
    return badge;
}

/**
 * Handle "View All" button click
 * Toggles between showing 2 consultations and all consultations
 */
function handleViewAllClick() {
    isExpanded = !isExpanded;
    renderConsultations(allConsultations, isExpanded);
}

/**
 * Handle consultation card click
 * Navigates to consultation detail view
 * @param {string} consultationId - Consultation ID (transcription_id)
 */
function handleConsultationClick(consultationId) {
    if (consultationId) {
        window.location.href = `/consultation/${consultationId}`;
    }
}

/**
 * Initialize the home page
 * Fetches consultations and sets up event listeners
 */
async function initHomePage() {
    // Show loading state
    const container = document.getElementById('consultations-container');
    if (container) {
        container.innerHTML = '<p class="text-xs text-slate-500">Loading consultations...</p>';
    }
    
    // Fetch consultations
    allConsultations = await fetchConsultations(10);
    
    // Render initial view (2 consultations)
    renderConsultations(allConsultations, false);
    
    // Set up "View All" button event listener
    const viewAllBtn = document.getElementById('view-all-btn');
    if (viewAllBtn) {
        viewAllBtn.onclick = handleViewAllClick;
    }
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', initHomePage);
