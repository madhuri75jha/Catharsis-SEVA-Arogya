/**
 * Transcription Display
 * 
 * Renders real-time transcription results with partial/final result handling,
 * auto-scrolling, and visual feedback.
 */

class TranscriptionDisplay {
    constructor(containerElement) {
        this.container = containerElement;
        this.segments = new Map(); // segment_id -> element
        this.currentSegmentId = null;
        this.autoScroll = true;
        this.initialize();
    }

    /**
     * Initialize display container
     */
    initialize() {
        // Clear container
        this.container.innerHTML = '';
        
        // Add CSS classes
        this.container.classList.add('transcription-display');
        
        // Create transcript container
        this.transcriptContainer = document.createElement('div');
        this.transcriptContainer.classList.add('transcript-container');
        this.container.appendChild(this.transcriptContainer);
        
        console.log('TranscriptionDisplay initialized');
    }

    /**
     * Update partial transcription result
     * 
     * @param {string} text - Transcription text
     * @param {string} segmentId - Segment identifier
     */
    updatePartial(text, segmentId) {
        if (!text || !text.trim()) {
            return;
        }

        let segmentElement = this.segments.get(segmentId);
        
        if (!segmentElement) {
            // Create new segment element
            segmentElement = document.createElement('span');
            segmentElement.classList.add('transcript-segment', 'partial');
            segmentElement.dataset.segmentId = segmentId;
            
            this.transcriptContainer.appendChild(segmentElement);
            this.segments.set(segmentId, segmentElement);
        }
        
        // Update text content
        segmentElement.textContent = text;
        
        // Highlight current segment
        this._highlightSegment(segmentId);
        
        // Auto-scroll
        if (this.autoScroll) {
            this._scrollToBottom();
        }
    }

    /**
     * Append final transcription result
     * 
     * @param {string} text - Transcription text
     * @param {string} segmentId - Segment identifier
     */
    appendFinal(text, segmentId) {
        if (!text || !text.trim()) {
            return;
        }

        let segmentElement = this.segments.get(segmentId);
        
        if (segmentElement) {
            // Update existing partial segment to final
            segmentElement.classList.remove('partial');
            segmentElement.classList.add('final');
            segmentElement.textContent = text;
        } else {
            // Create new final segment
            segmentElement = document.createElement('span');
            segmentElement.classList.add('transcript-segment', 'final');
            segmentElement.dataset.segmentId = segmentId;
            segmentElement.textContent = text;
            
            this.transcriptContainer.appendChild(segmentElement);
            this.segments.set(segmentId, segmentElement);
        }
        
        // Add space after final segment
        const space = document.createTextNode(' ');
        this.transcriptContainer.appendChild(space);
        
        // Remove highlight from finalized segment
        segmentElement.classList.remove('current');
        this.currentSegmentId = null;
        
        // Auto-scroll
        if (this.autoScroll) {
            this._scrollToBottom();
        }
    }

    /**
     * Highlight current segment being transcribed
     */
    _highlightSegment(segmentId) {
        // Remove highlight from previous segment
        if (this.currentSegmentId && this.currentSegmentId !== segmentId) {
            const prevSegment = this.segments.get(this.currentSegmentId);
            if (prevSegment) {
                prevSegment.classList.remove('current');
            }
        }
        
        // Highlight new segment
        const segment = this.segments.get(segmentId);
        if (segment) {
            segment.classList.add('current');
            this.currentSegmentId = segmentId;
        }
    }

    /**
     * Auto-scroll to bottom of transcript
     */
    _scrollToBottom() {
        requestAnimationFrame(() => {
            this.container.scrollTop = this.container.scrollHeight;
        });
    }

    /**
     * Show error message
     * 
     * @param {string} message - Error message
     */
    showError(message) {
        const errorElement = document.createElement('div');
        errorElement.classList.add('error-message');
        errorElement.innerHTML = `
            <div class="error-icon">⚠️</div>
            <div class="error-text">${this._escapeHtml(message)}</div>
            <button class="retry-button">Retry</button>
        `;
        
        this.container.insertBefore(errorElement, this.transcriptContainer);
        
        // Add retry button handler
        const retryButton = errorElement.querySelector('.retry-button');
        retryButton.addEventListener('click', () => {
            errorElement.remove();
            // Emit retry event (handled by controller)
            const event = new CustomEvent('retry', { bubbles: true });
            this.container.dispatchEvent(event);
        });
        
        console.log('Error displayed:', message);
    }

    /**
     * Show status message
     * 
     * @param {string} status - Status message
     */
    showStatus(status) {
        // Remove existing status
        const existingStatus = this.container.querySelector('.status-message');
        if (existingStatus) {
            existingStatus.remove();
        }
        
        const statusElement = document.createElement('div');
        statusElement.classList.add('status-message');
        statusElement.textContent = status;
        
        this.container.insertBefore(statusElement, this.transcriptContainer);
        
        console.log('Status displayed:', status);
    }

    /**
     * Clear all transcription content
     */
    clear() {
        this.transcriptContainer.innerHTML = '';
        this.segments.clear();
        this.currentSegmentId = null;
        
        // Remove error and status messages
        this.container.querySelectorAll('.error-message, .status-message').forEach(el => el.remove());
        
        console.log('Transcription display cleared');
    }

    /**
     * Get full transcript text
     * 
     * @returns {string} Complete transcript
     */
    getTranscript() {
        return this.transcriptContainer.textContent.trim();
    }

    /**
     * Enable/disable auto-scroll
     * 
     * @param {boolean} enabled - Auto-scroll enabled
     */
    setAutoScroll(enabled) {
        this.autoScroll = enabled;
    }

    /**
     * Escape HTML to prevent XSS
     */
    _escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    /**
     * Get segment count
     * 
     * @returns {number} Number of segments
     */
    getSegmentCount() {
        return this.segments.size;
    }
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = TranscriptionDisplay;
}
