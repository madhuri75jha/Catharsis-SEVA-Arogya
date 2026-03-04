/**
 * Text Reveal Animation Component
 * 
 * Animates transcribed text appearing word-by-word with smooth transitions.
 * 
 * Requirements: 10.1, 10.2, 10.3, 10.5, 10.6
 */

class TextRevealAnimation {
    constructor(container, options = {}) {
        this.container = container;
        this.options = {
            wordDelay: options.wordDelay || 75, // 50-100ms per word (requirement 10.3)
            transitionDuration: options.transitionDuration || 200, // Smooth transition
            animationType: options.animationType || 'fade-in', // 'fade-in', 'slide-in', or 'none'
            maintainReadability: options.maintainReadability !== false, // Requirement 10.5
            nonBlocking: options.nonBlocking !== false // Requirement 10.4
        };
        
        this.isAnimating = false;
        this.animationQueue = [];
        this.currentAnimationId = null;
    }

    /**
     * Reveal text with word-by-word animation
     * 
     * @param {string} text - Text to reveal
     * @param {boolean} append - Whether to append to existing text (default: true)
     * @returns {Promise} Promise that resolves when animation completes
     */
    async revealText(text, append = true) {
        if (!text || text.trim().length === 0) {
            return;
        }

        // Clear container if not appending
        if (!append) {
            this.container.innerHTML = '';
        }

        // Split text into words
        const words = text.trim().split(/\s+/);
        
        if (words.length === 0) {
            return;
        }

        console.log(`Revealing ${words.length} words with ${this.options.wordDelay}ms delay`);

        // Create animation ID
        const animationId = Date.now() + Math.random();
        this.currentAnimationId = animationId;
        this.isAnimating = true;

        // Create container for this text segment
        const segment = document.createElement('span');
        segment.className = 'text-reveal-segment';
        this.container.appendChild(segment);

        // Add space before segment if appending and container has content
        if (append && this.container.textContent.trim().length > 0) {
            const space = document.createTextNode(' ');
            segment.appendChild(space);
        }

        // Animate each word
        for (let i = 0; i < words.length; i++) {
            // Check if animation was cancelled
            if (this.currentAnimationId !== animationId) {
                console.log('Animation cancelled');
                break;
            }

            const word = words[i];
            const wordElement = this._createWordElement(word);
            
            segment.appendChild(wordElement);
            
            // Add space after word (except for last word)
            if (i < words.length - 1) {
                const space = document.createTextNode(' ');
                segment.appendChild(space);
            }

            // Trigger animation
            await this._animateWord(wordElement);
            
            // Non-blocking: yield to browser for UI updates (requirement 10.4)
            if (this.options.nonBlocking && i % 5 === 0) {
                await this._yield();
            }
        }

        this.isAnimating = false;
        
        // Mark segment as complete (requirement 10.6)
        segment.classList.add('complete');
        
        console.log('Text reveal animation complete');
    }

    /**
     * Reveal text instantly without animation
     * 
     * @param {string} text - Text to reveal
     * @param {boolean} append - Whether to append to existing text (default: true)
     */
    revealInstantly(text, append = true) {
        if (!text || text.trim().length === 0) {
            return;
        }

        // Cancel any ongoing animation
        this.cancel();

        // Clear container if not appending
        if (!append) {
            this.container.innerHTML = '';
        }

        // Add space before text if appending and container has content
        if (append && this.container.textContent.trim().length > 0) {
            this.container.appendChild(document.createTextNode(' '));
        }

        // Add text directly
        const textNode = document.createTextNode(text);
        this.container.appendChild(textNode);
    }

    /**
     * Create word element with animation classes
     * 
     * @param {string} word - Word text
     * @returns {HTMLElement} Word element
     */
    _createWordElement(word) {
        const wordElement = document.createElement('span');
        wordElement.className = 'text-reveal-word';
        wordElement.textContent = word;
        
        // Add animation type class
        if (this.options.animationType !== 'none') {
            wordElement.classList.add(`animate-${this.options.animationType}`);
        }
        
        // Initially hidden
        wordElement.style.opacity = '0';
        
        // Maintain readability (requirement 10.5)
        if (this.options.maintainReadability) {
            wordElement.style.display = 'inline';
            wordElement.style.whiteSpace = 'normal';
        }
        
        return wordElement;
    }

    /**
     * Animate a single word
     * 
     * @param {HTMLElement} wordElement - Word element to animate
     * @returns {Promise} Promise that resolves when animation completes
     */
    _animateWord(wordElement) {
        return new Promise((resolve) => {
            // Set transition
            wordElement.style.transition = `opacity ${this.options.transitionDuration}ms ease-in-out, transform ${this.options.transitionDuration}ms ease-in-out`;
            
            // Apply animation based on type
            switch (this.options.animationType) {
                case 'fade-in':
                    wordElement.style.opacity = '1';
                    break;
                    
                case 'slide-in':
                    wordElement.style.transform = 'translateX(-5px)';
                    wordElement.style.opacity = '0';
                    
                    // Trigger reflow
                    wordElement.offsetHeight;
                    
                    wordElement.style.transform = 'translateX(0)';
                    wordElement.style.opacity = '1';
                    break;
                    
                case 'none':
                default:
                    wordElement.style.opacity = '1';
                    break;
            }
            
            // Wait for word delay before resolving
            setTimeout(resolve, this.options.wordDelay);
        });
    }

    /**
     * Yield control to browser for UI updates (non-blocking)
     * 
     * @returns {Promise} Promise that resolves on next tick
     */
    _yield() {
        return new Promise(resolve => setTimeout(resolve, 0));
    }

    /**
     * Cancel current animation
     */
    cancel() {
        this.currentAnimationId = null;
        this.isAnimating = false;
    }

    /**
     * Clear all text from container
     */
    clear() {
        this.cancel();
        this.container.innerHTML = '';
    }

    /**
     * Check if currently animating
     * 
     * @returns {boolean} True if animating
     */
    isActive() {
        return this.isAnimating;
    }

    /**
     * Get current text content
     * 
     * @returns {string} Text content
     */
    getText() {
        return this.container.textContent;
    }

    /**
     * Update animation options
     * 
     * @param {Object} options - New options
     */
    setOptions(options) {
        this.options = { ...this.options, ...options };
    }

    /**
     * Create CSS styles for text reveal animation
     * 
     * @returns {string} CSS styles
     */
    static getStyles() {
        return `
            .text-reveal-segment {
                display: inline;
            }
            
            .text-reveal-word {
                display: inline;
                white-space: normal;
            }
            
            .text-reveal-word.animate-fade-in {
                transition: opacity 200ms ease-in-out;
            }
            
            .text-reveal-word.animate-slide-in {
                transition: opacity 200ms ease-in-out, transform 200ms ease-in-out;
            }
            
            .text-reveal-segment.complete .text-reveal-word {
                opacity: 1 !important;
                transform: none !important;
            }
            
            /* Accessibility: Respect prefers-reduced-motion */
            @media (prefers-reduced-motion: reduce) {
                .text-reveal-word {
                    transition: none !important;
                    opacity: 1 !important;
                    transform: none !important;
                }
            }
        `;
    }

    /**
     * Inject CSS styles into document
     */
    static injectStyles() {
        if (document.getElementById('text-reveal-styles')) {
            return; // Already injected
        }

        const style = document.createElement('style');
        style.id = 'text-reveal-styles';
        style.textContent = TextRevealAnimation.getStyles();
        document.head.appendChild(style);
    }
}

// Auto-inject styles when module loads
if (typeof document !== 'undefined') {
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => {
            TextRevealAnimation.injectStyles();
        });
    } else {
        TextRevealAnimation.injectStyles();
    }
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = TextRevealAnimation;
}
