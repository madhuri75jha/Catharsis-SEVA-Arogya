/**
 * Transcription Result Display Component
 * 
 * Displays transcription results with support for:
 * - Appending transcriptions in recording order
 * - Displaying partial results with "processing" indicator
 * - Showing final complete transcription when ready
 * - Persisting transcriptions across page navigation
 * 
 * Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 11.7
 */

class TranscriptionResultDisplay {
    constructor(container, options = {}) {
        this.container = container;
        this.options = {
            showPartialResults: options.showPartialResults !== false, // Requirement 11.3, 11.4
            animateText: options.animateText !== false, // Use text reveal animation
            persistToStorage: options.persistToStorage !== false, // Requirement 4.4
            storageKey: options.storageKey || 'transcription_results',
            consultationId: options.consultationId || null,
            wordDelay: options.wordDelay || 75, // For text reveal animation
            ...options
        };
        
        this.clips = new Map(); // clipId -> clip display data
        this.textRevealAnimators = new Map(); // clipId -> TextRevealAnimation instance
        this.consultationId = this.options.consultationId;
        
        // Initialize container
        this._initializeContainer();
        
        // Load persisted transcriptions if enabled
        if (this.options.persistToStorage) {
            this._loadFromStorage();
        }
    }

    /**
     * Initialize the display container
     */
    _initializeContainer() {
        this.container.innerHTML = '';
        this.container.className = 'transcription-results-container space-y-4';
    }

    /**
     * Add or update a clip transcription
     * 
     * @param {Object} clipData - Clip data
     * @param {string} clipData.clipId - Unique clip identifier
     * @param {number} clipData.clipOrder - Order of clip in consultation
     * @param {string} clipData.text - Transcription text
     * @param {boolean} clipData.isPartial - Whether this is a partial result
     * @param {boolean} clipData.isComplete - Whether transcription is complete
     * @param {string} clipData.status - Status ('recording', 'uploading', 'queued', 'transcribing', 'completed', 'failed')
     */
    addOrUpdateClip(clipData) {
        const { clipId, clipOrder, text, isPartial, isComplete, status } = clipData;
        
        // Validate required fields
        if (!clipId) {
            console.error('clipId is required');
            return;
        }
        
        // Check if clip already exists
        const existingClip = this.clips.get(clipId);
        
        if (existingClip) {
            // Update existing clip
            this._updateClip(clipId, clipData);
        } else {
            // Create new clip
            this._createClip(clipData);
        }
        
        // Persist to storage
        if (this.options.persistToStorage) {
            this._saveToStorage();
        }
    }

    /**
     * Create a new clip display element
     * 
     * @param {Object} clipData - Clip data
     */
    _createClip(clipData) {
        const { clipId, clipOrder, text, isPartial, isComplete, status } = clipData;
        
        // Create clip container
        const clipElement = document.createElement('div');
        clipElement.className = 'transcription-clip';
        clipElement.dataset.clipId = clipId;
        clipElement.dataset.clipOrder = clipOrder || 0;
        
        // Create clip header (order number + status)
        const header = document.createElement('div');
        header.className = 'clip-header flex items-center justify-between mb-2';
        
        const orderLabel = document.createElement('span');
        orderLabel.className = 'clip-order text-xs font-semibold text-slate-500 dark:text-slate-400';
        orderLabel.textContent = `Clip ${clipOrder || '?'}`;
        
        const statusIndicator = document.createElement('span');
        statusIndicator.className = 'clip-status text-xs';
        this._updateStatusIndicator(statusIndicator, status, isPartial, isComplete);
        
        header.appendChild(orderLabel);
        header.appendChild(statusIndicator);
        
        // Create text container
        const textContainer = document.createElement('div');
        textContainer.className = 'clip-text text-base text-slate-700 dark:text-slate-300 leading-relaxed';
        
        // Add elements to clip
        clipElement.appendChild(header);
        clipElement.appendChild(textContainer);
        
        // Store clip data
        this.clips.set(clipId, {
            element: clipElement,
            textContainer: textContainer,
            statusIndicator: statusIndicator,
            clipOrder: clipOrder || 0,
            text: text || '',
            isPartial: isPartial || false,
            isComplete: isComplete || false,
            status: status || 'queued'
        });
        
        // Insert clip in correct order (Requirement 4.2, 4.5)
        this._insertClipInOrder(clipElement, clipOrder || 0);
        
        // Display text if provided
        if (text && text.length > 0) {
            this._displayText(clipId, text, false);
        }
    }

    /**
     * Update an existing clip
     * 
     * @param {string} clipId - Clip ID
     * @param {Object} clipData - Updated clip data
     */
    _updateClip(clipId, clipData) {
        const clip = this.clips.get(clipId);
        if (!clip) {
            console.error(`Clip not found: ${clipId}`);
            return;
        }
        
        const { text, isPartial, isComplete, status } = clipData;
        
        // Update status
        if (status !== undefined && status !== clip.status) {
            clip.status = status;
            this._updateStatusIndicator(clip.statusIndicator, status, isPartial, isComplete);
        }
        
        // Update partial/complete flags
        if (isPartial !== undefined) {
            clip.isPartial = isPartial;
        }
        if (isComplete !== undefined) {
            clip.isComplete = isComplete;
        }
        
        // Update text if provided and different
        if (text !== undefined && text !== clip.text) {
            const shouldAppend = text.startsWith(clip.text);
            const newText = shouldAppend ? text.substring(clip.text.length) : text;
            
            clip.text = text;
            this._displayText(clipId, newText, shouldAppend);
        }
        
        // Update status indicator with current flags
        this._updateStatusIndicator(clip.statusIndicator, clip.status, clip.isPartial, clip.isComplete);
    }

    /**
     * Display text in a clip with optional animation
     * 
     * @param {string} clipId - Clip ID
     * @param {string} text - Text to display
     * @param {boolean} append - Whether to append to existing text
     */
    _displayText(clipId, text, append = false) {
        const clip = this.clips.get(clipId);
        if (!clip) {
            console.error(`Clip not found: ${clipId}`);
            return;
        }
        
        if (!text || text.trim().length === 0) {
            return;
        }
        
        // Use text reveal animation if enabled
        if (this.options.animateText) {
            // Get or create text reveal animator for this clip
            let animator = this.textRevealAnimators.get(clipId);
            
            if (!animator) {
                animator = new TextRevealAnimation(clip.textContainer, {
                    wordDelay: this.options.wordDelay,
                    animationType: 'fade-in',
                    nonBlocking: true
                });
                this.textRevealAnimators.set(clipId, animator);
            }
            
            // Reveal text with animation
            animator.revealText(text, append);
        } else {
            // Display text instantly
            if (append) {
                clip.textContainer.appendChild(document.createTextNode(' ' + text));
            } else {
                clip.textContainer.textContent = text;
            }
        }
    }

    /**
     * Update status indicator
     * 
     * @param {HTMLElement} indicator - Status indicator element
     * @param {string} status - Status value
     * @param {boolean} isPartial - Whether result is partial
     * @param {boolean} isComplete - Whether transcription is complete
     */
    _updateStatusIndicator(indicator, status, isPartial, isComplete) {
        // Determine display text and style
        let displayText = '';
        let className = 'clip-status text-xs ';
        
        if (isComplete) {
            // Final complete transcription (Requirement 11.7)
            displayText = 'Complete';
            className += 'text-green-600 dark:text-green-400';
        } else if (isPartial) {
            // Partial result with processing indicator (Requirement 11.3, 11.4, 11.7)
            displayText = 'Processing...';
            className += 'text-yellow-600 dark:text-yellow-400 animate-pulse';
        } else {
            // Status-based display
            switch (status) {
                case 'recording':
                    displayText = 'Recording';
                    className += 'text-red-600 dark:text-red-400 animate-pulse';
                    break;
                case 'uploading':
                    displayText = 'Uploading';
                    className += 'text-blue-600 dark:text-blue-400';
                    break;
                case 'queued':
                    displayText = 'Queued';
                    className += 'text-slate-600 dark:text-slate-400';
                    break;
                case 'transcribing':
                    displayText = 'Transcribing';
                    className += 'text-yellow-600 dark:text-yellow-400 animate-pulse';
                    break;
                case 'completed':
                    displayText = 'Complete';
                    className += 'text-green-600 dark:text-green-400';
                    break;
                case 'failed':
                    displayText = 'Failed';
                    className += 'text-red-600 dark:text-red-400';
                    break;
                default:
                    displayText = status || 'Unknown';
                    className += 'text-slate-600 dark:text-slate-400';
            }
        }
        
        indicator.textContent = displayText;
        indicator.className = className;
    }

    /**
     * Insert clip element in correct order (Requirement 4.2, 4.5)
     * 
     * @param {HTMLElement} clipElement - Clip element to insert
     * @param {number} clipOrder - Clip order number
     */
    _insertClipInOrder(clipElement, clipOrder) {
        const existingClips = Array.from(this.container.children);
        
        // Find insertion point
        let insertBefore = null;
        for (const existing of existingClips) {
            const existingOrder = parseInt(existing.dataset.clipOrder || '0', 10);
            if (existingOrder > clipOrder) {
                insertBefore = existing;
                break;
            }
        }
        
        // Insert at correct position
        if (insertBefore) {
            this.container.insertBefore(clipElement, insertBefore);
        } else {
            this.container.appendChild(clipElement);
        }
    }

    /**
     * Remove a clip from display
     * 
     * @param {string} clipId - Clip ID
     */
    removeClip(clipId) {
        const clip = this.clips.get(clipId);
        if (!clip) {
            return;
        }
        
        // Remove element
        if (clip.element && clip.element.parentNode) {
            clip.element.parentNode.removeChild(clip.element);
        }
        
        // Remove animator
        const animator = this.textRevealAnimators.get(clipId);
        if (animator) {
            animator.cancel();
            this.textRevealAnimators.delete(clipId);
        }
        
        // Remove from map
        this.clips.delete(clipId);
        
        // Update storage
        if (this.options.persistToStorage) {
            this._saveToStorage();
        }
    }

    /**
     * Clear all clips
     */
    clear() {
        // Cancel all animations
        this.textRevealAnimators.forEach(animator => animator.cancel());
        this.textRevealAnimators.clear();
        
        // Clear clips
        this.clips.clear();
        
        // Clear container
        this.container.innerHTML = '';
        
        // Clear storage
        if (this.options.persistToStorage) {
            this._clearStorage();
        }
    }

    /**
     * Get all clips ordered by clip order
     * 
     * @returns {Array} Array of clip data
     */
    getClipsOrdered() {
        return Array.from(this.clips.entries())
            .map(([clipId, clip]) => ({
                clipId: clipId,
                clipOrder: clip.clipOrder,
                text: clip.text,
                isPartial: clip.isPartial,
                isComplete: clip.isComplete,
                status: clip.status
            }))
            .sort((a, b) => a.clipOrder - b.clipOrder);
    }

    /**
     * Get full transcription text (all clips in order)
     * 
     * @returns {string} Combined transcription text
     */
    getFullTranscription() {
        return this.getClipsOrdered()
            .map(clip => clip.text)
            .filter(text => text && text.length > 0)
            .join(' ')
            .replace(/\s+/g, ' ')
            .trim();
    }

    /**
     * Set consultation ID
     * 
     * @param {string} consultationId - Consultation ID
     */
    setConsultationId(consultationId) {
        this.consultationId = consultationId;
        this.options.consultationId = consultationId;
        
        // Update storage key to include consultation ID
        if (this.options.persistToStorage) {
            this.options.storageKey = `transcription_results_${consultationId}`;
            this._saveToStorage();
        }
    }

    /**
     * Save transcriptions to localStorage (Requirement 4.4)
     */
    _saveToStorage() {
        if (!this.options.persistToStorage) {
            return;
        }
        
        try {
            const data = {
                consultationId: this.consultationId,
                clips: this.getClipsOrdered(),
                timestamp: Date.now()
            };
            
            const key = this.consultationId 
                ? `transcription_results_${this.consultationId}`
                : this.options.storageKey;
            
            localStorage.setItem(key, JSON.stringify(data));
            console.log(`Saved ${data.clips.length} clips to storage`);
        } catch (error) {
            console.error('Failed to save transcriptions to storage:', error);
        }
    }

    /**
     * Load transcriptions from localStorage (Requirement 4.4)
     */
    _loadFromStorage() {
        if (!this.options.persistToStorage) {
            return;
        }
        
        try {
            const key = this.consultationId 
                ? `transcription_results_${this.consultationId}`
                : this.options.storageKey;
            
            const stored = localStorage.getItem(key);
            if (!stored) {
                return;
            }
            
            const data = JSON.parse(stored);
            
            // Validate data
            if (!data.clips || !Array.isArray(data.clips)) {
                console.warn('Invalid stored transcription data');
                return;
            }
            
            // Restore consultation ID
            if (data.consultationId) {
                this.consultationId = data.consultationId;
            }
            
            // Restore clips
            data.clips.forEach(clipData => {
                this.addOrUpdateClip(clipData);
            });
            
            console.log(`Loaded ${data.clips.length} clips from storage`);
        } catch (error) {
            console.error('Failed to load transcriptions from storage:', error);
        }
    }

    /**
     * Clear storage
     */
    _clearStorage() {
        if (!this.options.persistToStorage) {
            return;
        }
        
        try {
            const key = this.consultationId 
                ? `transcription_results_${this.consultationId}`
                : this.options.storageKey;
            
            localStorage.removeItem(key);
            console.log('Cleared transcription storage');
        } catch (error) {
            console.error('Failed to clear storage:', error);
        }
    }

    /**
     * Get CSS styles for transcription display
     * 
     * @returns {string} CSS styles
     */
    static getStyles() {
        return `
            .transcription-results-container {
                display: flex;
                flex-direction: column;
                gap: 1rem;
            }
            
            .transcription-clip {
                padding: 1rem;
                background-color: rgba(248, 250, 252, 0.5);
                border: 1px solid rgba(226, 232, 240, 0.8);
                border-radius: 0.75rem;
                transition: all 0.2s ease;
            }
            
            .dark .transcription-clip {
                background-color: rgba(15, 23, 42, 0.5);
                border-color: rgba(51, 65, 85, 0.8);
            }
            
            .transcription-clip:hover {
                background-color: rgba(248, 250, 252, 0.8);
                border-color: rgba(203, 213, 225, 1);
            }
            
            .dark .transcription-clip:hover {
                background-color: rgba(15, 23, 42, 0.8);
                border-color: rgba(71, 85, 105, 1);
            }
            
            .clip-header {
                display: flex;
                align-items: center;
                justify-content: space-between;
                margin-bottom: 0.5rem;
            }
            
            .clip-order {
                font-size: 0.75rem;
                font-weight: 600;
                text-transform: uppercase;
                letter-spacing: 0.05em;
            }
            
            .clip-status {
                font-size: 0.75rem;
                font-weight: 500;
            }
            
            .clip-text {
                font-size: 1rem;
                line-height: 1.625;
                min-height: 1.5rem;
            }
            
            /* Animation for processing indicator */
            @keyframes pulse {
                0%, 100% {
                    opacity: 1;
                }
                50% {
                    opacity: 0.5;
                }
            }
            
            .animate-pulse {
                animation: pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite;
            }
            
            /* Accessibility: Respect prefers-reduced-motion */
            @media (prefers-reduced-motion: reduce) {
                .animate-pulse {
                    animation: none;
                }
            }
        `;
    }

    /**
     * Inject CSS styles into document
     */
    static injectStyles() {
        if (document.getElementById('transcription-result-display-styles')) {
            return; // Already injected
        }

        const style = document.createElement('style');
        style.id = 'transcription-result-display-styles';
        style.textContent = TranscriptionResultDisplay.getStyles();
        document.head.appendChild(style);
    }
}

// Auto-inject styles when module loads
if (typeof document !== 'undefined') {
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => {
            TranscriptionResultDisplay.injectStyles();
        });
    } else {
        TranscriptionResultDisplay.injectStyles();
    }
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = TranscriptionResultDisplay;
}
