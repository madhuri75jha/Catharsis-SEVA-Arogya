/**
 * Recording Visual Feedback Manager
 * 
 * Manages visual feedback for recording state changes including CSS class toggles
 * and animation triggers.
 * 
 * Requirements: 9.5, 9.6
 */

class RecordingVisualFeedback {
    constructor(options = {}) {
        this.options = {
            iconSelector: options.iconSelector || '.recording-icon',
            buttonSelector: options.buttonSelector || '.recording-button',
            backgroundSelector: options.backgroundSelector || '.recording-background',
            indicatorSelector: options.indicatorSelector || '.recording-indicator',
            dotSelector: options.dotSelector || '.recording-dot',
            micSelector: options.micSelector || '.mic-icon',
            statusBarSelector: options.statusBarSelector || '.recording-status-bar',
            updateDelay: options.updateDelay || 0 // Requirement 9.6: within 100ms
        };
        
        this.currentState = 'idle';
        this.elements = {};
        this._findElements();
    }

    /**
     * Find all visual feedback elements
     */
    _findElements() {
        this.elements = {
            icons: document.querySelectorAll(this.options.iconSelector),
            buttons: document.querySelectorAll(this.options.buttonSelector),
            backgrounds: document.querySelectorAll(this.options.backgroundSelector),
            indicators: document.querySelectorAll(this.options.indicatorSelector),
            dots: document.querySelectorAll(this.options.dotSelector),
            mics: document.querySelectorAll(this.options.micSelector),
            statusBars: document.querySelectorAll(this.options.statusBarSelector)
        };
    }

    /**
     * Set recording state and update all visual indicators
     * 
     * @param {string} state - State ('recording' or 'idle')
     */
    setState(state) {
        if (state !== 'recording' && state !== 'idle') {
            console.warn(`Invalid state: ${state}. Must be 'recording' or 'idle'.`);
            return;
        }

        if (this.currentState === state) {
            return; // No change
        }

        const startTime = performance.now();
        
        this.currentState = state;
        
        // Update all elements with minimal delay (requirement 9.6: within 100ms)
        setTimeout(() => {
            this._updateAllElements(state);
            
            const duration = performance.now() - startTime;
            console.log(`Visual feedback updated to '${state}' in ${duration.toFixed(2)}ms`);
        }, this.options.updateDelay);
    }

    /**
     * Start recording visual feedback
     */
    startRecording() {
        this.setState('recording');
    }

    /**
     * Stop recording visual feedback
     */
    stopRecording() {
        this.setState('idle');
    }

    /**
     * Update all visual elements
     * 
     * @param {string} state - State ('recording' or 'idle')
     */
    _updateAllElements(state) {
        const oppositeState = state === 'recording' ? 'idle' : 'recording';
        
        // Update icons
        this.elements.icons.forEach(el => {
            el.classList.remove(oppositeState);
            el.classList.add(state);
        });
        
        // Update buttons
        this.elements.buttons.forEach(el => {
            el.classList.remove(oppositeState);
            el.classList.add(state);
        });
        
        // Update backgrounds
        this.elements.backgrounds.forEach(el => {
            el.classList.remove(oppositeState);
            el.classList.add(state);
        });
        
        // Update indicators
        this.elements.indicators.forEach(el => {
            el.classList.remove(oppositeState);
            el.classList.add(state);
            
            // Update text content if it has a text node
            if (el.textContent) {
                el.textContent = state === 'recording' ? 'Recording...' : 'Ready';
            }
        });
        
        // Update dots
        this.elements.dots.forEach(el => {
            el.classList.remove(oppositeState);
            el.classList.add(state);
        });
        
        // Update mic icons
        this.elements.mics.forEach(el => {
            el.classList.remove(oppositeState);
            el.classList.add(state);
        });
        
        // Update status bars
        this.elements.statusBars.forEach(el => {
            el.classList.remove(oppositeState);
            el.classList.add(state);
        });
    }

    /**
     * Refresh element references (call after DOM changes)
     */
    refresh() {
        this._findElements();
        this._updateAllElements(this.currentState);
    }

    /**
     * Add custom element to be managed
     * 
     * @param {HTMLElement} element - Element to add
     * @param {string} type - Element type (e.g., 'icon', 'button')
     */
    addElement(element, type = 'icon') {
        if (!element) {
            console.warn('Cannot add null element');
            return;
        }

        const key = type + 's'; // Pluralize
        if (!this.elements[key]) {
            this.elements[key] = [];
        }

        // Convert NodeList to Array if needed
        if (NodeList.prototype.isPrototypeOf(this.elements[key])) {
            this.elements[key] = Array.from(this.elements[key]);
        }

        this.elements[key].push(element);
        
        // Apply current state to new element
        element.classList.add(this.currentState);
    }

    /**
     * Get current state
     * 
     * @returns {string} Current state ('recording' or 'idle')
     */
    getState() {
        return this.currentState;
    }

    /**
     * Check if currently recording
     * 
     * @returns {boolean} True if recording
     */
    isRecording() {
        return this.currentState === 'recording';
    }

    /**
     * Create and add a recording indicator element
     * 
     * @param {HTMLElement} container - Container to append indicator to
     * @returns {HTMLElement} Created indicator element
     */
    createIndicator(container) {
        const indicator = document.createElement('div');
        indicator.className = `recording-indicator ${this.currentState}`;
        
        const dot = document.createElement('span');
        dot.className = `recording-dot ${this.currentState}`;
        
        const text = document.createElement('span');
        text.textContent = this.currentState === 'recording' ? 'Recording...' : 'Ready';
        
        indicator.appendChild(dot);
        indicator.appendChild(text);
        
        if (container) {
            container.appendChild(indicator);
        }
        
        // Add to managed elements
        this.addElement(indicator, 'indicator');
        this.addElement(dot, 'dot');
        
        return indicator;
    }

    /**
     * Create and add a recording button
     * 
     * @param {HTMLElement} container - Container to append button to
     * @param {Function} onClick - Click handler
     * @returns {HTMLElement} Created button element
     */
    createButton(container, onClick) {
        const button = document.createElement('button');
        button.className = `btn recording-button ${this.currentState}`;
        button.type = 'button';
        
        const icon = document.createElement('i');
        icon.className = `fas fa-microphone recording-icon ${this.currentState}`;
        
        const text = document.createElement('span');
        text.textContent = this.currentState === 'recording' ? 'Recording...' : 'Start Recording';
        text.style.marginLeft = '8px';
        
        button.appendChild(icon);
        button.appendChild(text);
        
        if (onClick) {
            button.addEventListener('click', onClick);
        }
        
        if (container) {
            container.appendChild(button);
        }
        
        // Add to managed elements
        this.addElement(button, 'button');
        this.addElement(icon, 'icon');
        
        return button;
    }

    /**
     * Reset all visual feedback to idle state
     */
    reset() {
        this.setState('idle');
    }

    /**
     * Cleanup and remove all managed elements
     */
    cleanup() {
        // Reset to idle state
        this.reset();
        
        // Clear element references
        this.elements = {
            icons: [],
            buttons: [],
            backgrounds: [],
            indicators: [],
            dots: [],
            mics: [],
            statusBars: []
        };
    }
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = RecordingVisualFeedback;
}
