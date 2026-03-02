/**
 * Bedrock Extraction API Client
 * Handles API calls for medical prescription extraction
 */

/**
 * Extract prescription data from transcript
 * @param {string} transcript - Medical transcript text
 * @param {string} hospitalId - Hospital identifier
 * @param {string} requestId - Optional request ID for idempotency
 * @returns {Promise<object>} Extraction result
 */
async function extractPrescriptionData(transcript, hospitalId = 'default', requestId = null) {
    const payload = {
        transcript: transcript,
        hospital_id: hospitalId
    };
    
    if (requestId) {
        payload.request_id = requestId;
    }
    
    const response = await fetch('/api/v1/extract', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(payload)
    });
    
    const data = await response.json();
    
    if (!response.ok) {
        throw new Error(data.error_message || 'Extraction failed');
    }
    
    return data;
}

/**
 * Load hospital configuration
 * @param {string} hospitalId - Hospital identifier
 * @returns {Promise<object>} Hospital configuration
 */
async function loadHospitalConfig(hospitalId) {
    const response = await fetch(`/api/v1/config/${hospitalId}`);
    
    if (!response.ok) {
        throw new Error(`Failed to load configuration: ${response.statusText}`);
    }
    
    return await response.json();
}

/**
 * Submit transcript for extraction and navigate to prescription form
 * @param {string} transcript - Medical transcript text
 * @param {string} hospitalId - Hospital identifier
 */
async function submitTranscriptForExtraction(transcript, hospitalId = 'default') {
    try {
        // Validate transcript
        if (!transcript || transcript.trim().length === 0) {
            throw new Error('Transcript is required');
        }
        
        if (transcript.length > 10000) {
            throw new Error('Transcript exceeds maximum length of 10,000 characters');
        }
        
        // Show loading state
        showExtractionLoading();
        
        // Call extraction API
        const result = await extractPrescriptionData(transcript, hospitalId);
        
        if (result.status === 'success') {
            // Store prescription data in sessionStorage
            sessionStorage.setItem('prescriptionData', JSON.stringify(result.prescription_data));
            
            // Navigate to prescription form
            window.location.href = `/bedrock-prescription?hospital_id=${hospitalId}`;
        } else {
            throw new Error(result.error_message || 'Extraction failed');
        }
        
    } catch (error) {
        console.error('Extraction error:', error);
        showExtractionError(error.message);
    }
}

/**
 * Show extraction loading state
 */
function showExtractionLoading() {
    // Create or update loading overlay
    let overlay = document.getElementById('extractionLoadingOverlay');
    
    if (!overlay) {
        overlay = document.createElement('div');
        overlay.id = 'extractionLoadingOverlay';
        overlay.className = 'fixed inset-0 bg-black/50 z-50 flex items-center justify-center';
        overlay.innerHTML = `
            <div class="bg-white dark:bg-slate-900 rounded-xl p-8 max-w-sm mx-4 text-center">
                <div class="animate-spin rounded-full h-16 w-16 border-b-2 border-primary mx-auto mb-4"></div>
                <h3 class="text-slate-900 dark:text-white text-lg font-bold mb-2">Extracting Prescription Data</h3>
                <p class="text-slate-600 dark:text-slate-400 text-sm">
                    Analyzing transcript with AI...<br>
                    This may take a few moments.
                </p>
            </div>
        `;
        document.body.appendChild(overlay);
    }
    
    overlay.classList.remove('hidden');
}

/**
 * Hide extraction loading state
 */
function hideExtractionLoading() {
    const overlay = document.getElementById('extractionLoadingOverlay');
    if (overlay) {
        overlay.classList.add('hidden');
    }
}

/**
 * Show extraction error
 * @param {string} message - Error message
 */
function showExtractionError(message) {
    hideExtractionLoading();
    
    // Map common error codes to user-friendly messages
    const errorMessages = {
        'INVALID_INPUT': 'The transcript format is invalid. Please try recording again.',
        'VALIDATION_ERROR': 'The transcript could not be validated. Please check the recording quality.',
        'EXTRACTION_FAILED': 'AI extraction failed. This may be due to unclear audio or missing information. You can try manual review instead.',
        'INTERNAL_ERROR': 'An unexpected error occurred. Please try again or use manual review.',
        'COMPREHEND_UNAVAILABLE': 'Medical entity extraction service is temporarily unavailable. Please try again in a moment.',
        'BEDROCK_UNAVAILABLE': 'AI extraction service is temporarily unavailable. Please try again in a moment.',
        'RATE_LIMIT': 'Too many requests. Please wait a moment and try again.',
        'TIMEOUT': 'The extraction took too long. Please try again with a shorter transcript.'
    };
    
    // Try to extract error code from message
    let userMessage = message;
    for (const [code, msg] of Object.entries(errorMessages)) {
        if (message.includes(code)) {
            userMessage = msg;
            break;
        }
    }
    
    // Create or update error overlay
    let overlay = document.getElementById('extractionErrorOverlay');
    
    if (!overlay) {
        overlay = document.createElement('div');
        overlay.id = 'extractionErrorOverlay';
        overlay.className = 'fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4';
        document.body.appendChild(overlay);
    }
    
    overlay.innerHTML = `
        <div class="bg-white dark:bg-slate-900 rounded-xl p-8 max-w-sm mx-4">
            <div class="flex items-center gap-3 mb-4">
                <span class="material-symbols-outlined text-red-600 text-3xl">error</span>
                <h3 class="text-slate-900 dark:text-white text-lg font-bold">Extraction Failed</h3>
            </div>
            <p class="text-slate-600 dark:text-slate-400 text-sm mb-6">${userMessage}</p>
            <div class="flex gap-3">
                <button onclick="useManualReview()" class="flex-1 bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 rounded-lg py-3 px-4 font-bold">
                    Manual Review
                </button>
                <button onclick="retryExtraction()" class="flex-1 bg-primary text-white rounded-lg py-3 px-4 font-bold">
                    Retry
                </button>
            </div>
        </div>
    `;
    
    overlay.classList.remove('hidden');
}

/**
 * Use manual review instead of AI extraction
 */
function useManualReview() {
    closeExtractionError();
    window.location.href = '/final-prescription';
}

/**
 * Close extraction error overlay
 */
function closeExtractionError() {
    const overlay = document.getElementById('extractionErrorOverlay');
    if (overlay) {
        overlay.classList.add('hidden');
    }
}

/**
 * Retry extraction (to be implemented by calling page)
 */
function retryExtraction() {
    closeExtractionError();
    // This function should be overridden by the calling page
    console.warn('retryExtraction() should be implemented by the calling page');
}

/**
 * Format confidence score as percentage
 * @param {number} confidence - Confidence score (0-1)
 * @returns {string} Formatted percentage
 */
function formatConfidence(confidence) {
    return `${Math.round(confidence * 100)}%`;
}

/**
 * Get confidence level label
 * @param {number} confidence - Confidence score (0-1)
 * @returns {string} Confidence level (high, medium, low)
 */
function getConfidenceLevel(confidence) {
    if (confidence >= 0.8) return 'high';
    if (confidence >= 0.5) return 'medium';
    return 'low';
}

/**
 * Get confidence color class
 * @param {number} confidence - Confidence score (0-1)
 * @returns {string} Tailwind color class
 */
function getConfidenceColorClass(confidence) {
    if (confidence >= 0.8) return 'text-green-600';
    if (confidence >= 0.5) return 'text-yellow-600';
    return 'text-red-600';
}
