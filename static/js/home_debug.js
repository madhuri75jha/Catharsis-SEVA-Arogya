/**
 * Debug version of home.js with console logging
 */

// Global state
let allConsultations = [];
let isExpanded = false;

/**
 * Fetch consultations from API
 */
async function fetchConsultations(limit = 10) {
    console.log('[DEBUG] Fetching consultations with limit:', limit);
    
    try {
        const url = `/api/consultations?limit=${limit}`;
        console.log('[DEBUG] Fetching from URL:', url);
        
        const response = await fetch(url);
        console.log('[DEBUG] Response status:', response.status);
        console.log('[DEBUG] Response headers:', response.headers);
        
        if (!response.ok) {
            if (response.status === 401) {
                console.error('[DEBUG] Authentication failure - redirecting to login');
                window.location.href = '/login';
                return [];
            }
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        console.log('[DEBUG] Response data:', data);
        
        if (data.success) {
            console.log('[DEBUG] Successfully retrieved', data.consultations.length, 'consultations');
            return data.consultations || [];
        } else {
            console.error('[DEBUG] API returned error:', data.error);
            return [];
        }
    } catch (error) {
        console.error('[DEBUG] Failed to fetch consultations:', error);
        console.error('[DEBUG] Error stack:', error.stack);
        return [];
    }
}

/**
 * Render consultation cards in the DOM
 */
function renderConsultations(consultations, showAll = false) {
    console.log('[DEBUG] Rendering consultations:', consultations.length, 'showAll:', showAll);
    
    const container = document.getElementById('consultations-container');
    const emptyState = document.getElementById('empty-state');
    const viewAllBtn = document.getElementById('view-all-btn');
    
    console.log('[DEBUG] Container:', container);
    console.log('[DEBUG] Empty state:', emptyState);
    console.log('[DEBUG] View all button:', viewAllBtn);
    
    if (!container) {
        console.error('[DEBUG] Consultations container not found!');
        return;
    }
    
    // Clear existing content
    container.innerHTML = '';
    
    // Handle empty state
    if (!consultations || consultations.length === 0) {
        console.log('[DEBUG] No consultations - showing empty state');
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
    console.log('[DEBUG] Displaying', displayCount, 'of', consultations.length, 'consultations');
    
    const consultationsToRender = consultations.slice(0, displayCount);
    
    // Render consultation cards
    consultationsToRender.forEach((consultation, index) => {
        console.log('[DEBUG] Rendering consultation', index, ':', consultation);
        const card = createConsultationCard(consultation);
        container.appendChild(card);
    });
    
    // Update "View All" button visibility and text
    if (viewAllBtn) {
        if (consultations.length > 2) {
            viewAllBtn.classList.remove('hidden');
            viewAllBtn.textContent = showAll ? 'Show Less' : 'View All';
            console.log('[DEBUG] View All button visible, text:', viewAllBtn.textContent);
        } else {
            viewAllBtn.classList.add('hidden');
            console.log('[DEBUG] View All button hidden (not enough consultations)');
        }
    }
}

/**
 * Create a consultation card DOM element
 */
function createConsultationCard(consultation) {
    console.log('[DEBUG] Creating card for:', consultation.patient_name);
    
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
        const options = { year: 'numeric', month: 'short', day: 'numeric' };
        return then.toLocaleDateString('en-US', options);
    }
}

/**
 * Get status badge HTML element
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
 */
function handleViewAllClick() {
    console.log('[DEBUG] View All clicked, current isExpanded:', isExpanded);
    isExpanded = !isExpanded;
    console.log('[DEBUG] New isExpanded:', isExpanded);
    renderConsultations(allConsultations, isExpanded);
}

/**
 * Handle consultation card click
 */
function handleConsultationClick(consultationId) {
    console.log('[DEBUG] Consultation clicked:', consultationId);
    if (consultationId) {
        window.location.href = `/consultation/${consultationId}`;
    }
}

/**
 * Initialize the home page
 */
async function initHomePage() {
    console.log('[DEBUG] Initializing home page...');
    
    // Show loading state
    const container = document.getElementById('consultations-container');
    if (container) {
        container.innerHTML = '<p class="text-xs text-slate-500">Loading consultations...</p>';
    }
    
    // Fetch consultations
    console.log('[DEBUG] Fetching consultations...');
    allConsultations = await fetchConsultations(10);
    console.log('[DEBUG] Fetched consultations:', allConsultations);
    
    // Render initial view (2 consultations)
    console.log('[DEBUG] Rendering initial view...');
    renderConsultations(allConsultations, false);
    
    // Set up "View All" button event listener
    const viewAllBtn = document.getElementById('view-all-btn');
    if (viewAllBtn) {
        console.log('[DEBUG] Setting up View All button listener');
        viewAllBtn.onclick = handleViewAllClick;
    } else {
        console.error('[DEBUG] View All button not found!');
    }
    
    console.log('[DEBUG] Home page initialization complete');
}

// Initialize on page load
console.log('[DEBUG] Script loaded, waiting for DOMContentLoaded...');
document.addEventListener('DOMContentLoaded', () => {
    console.log('[DEBUG] DOMContentLoaded fired');
    initHomePage();
});
