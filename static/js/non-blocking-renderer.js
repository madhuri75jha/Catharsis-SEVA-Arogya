/**
 * Non-Blocking Animation Renderer
 * 
 * Ensures animations don't block user interaction by yielding control
 * to the browser's event loop periodically.
 * 
 * Requirements: 10.4, 10.6
 */

class NonBlockingRenderer {
    constructor(options = {}) {
        this.options = {
            yieldInterval: options.yieldInterval || 5, // Yield every N operations
            yieldDelay: options.yieldDelay || 0, // Delay in ms (0 = next tick)
            maxBatchSize: options.maxBatchSize || 50 // Max operations per batch
        };
        
        this.operationCount = 0;
        this.isRendering = false;
    }

    /**
     * Execute operations in non-blocking batches
     * 
     * @param {Array} items - Items to process
     * @param {Function} operation - Operation to perform on each item
     * @param {Function} onProgress - Progress callback (optional)
     * @returns {Promise} Promise that resolves when all operations complete
     */
    async executeBatched(items, operation, onProgress = null) {
        if (!items || items.length === 0) {
            return;
        }

        this.isRendering = true;
        this.operationCount = 0;

        const totalItems = items.length;
        let processedItems = 0;

        try {
            for (let i = 0; i < items.length; i++) {
                // Execute operation
                await operation(items[i], i);
                
                processedItems++;
                this.operationCount++;

                // Yield to browser periodically
                if (this.operationCount % this.options.yieldInterval === 0) {
                    await this._yield();
                }

                // Report progress
                if (onProgress) {
                    onProgress({
                        processed: processedItems,
                        total: totalItems,
                        progress: (processedItems / totalItems) * 100
                    });
                }

                // Batch size limit check
                if (this.operationCount >= this.options.maxBatchSize) {
                    console.log(`Batch size limit reached (${this.options.maxBatchSize}), yielding...`);
                    await this._yield();
                    this.operationCount = 0;
                }
            }
        } finally {
            this.isRendering = false;
        }
    }

    /**
     * Execute async operation with automatic yielding
     * 
     * @param {Function} asyncOperation - Async operation to execute
     * @returns {Promise} Promise that resolves with operation result
     */
    async executeWithYield(asyncOperation) {
        this.isRendering = true;
        
        try {
            // Execute operation
            const result = await asyncOperation();
            
            // Yield to browser
            await this._yield();
            
            return result;
        } finally {
            this.isRendering = false;
        }
    }

    /**
     * Yield control to browser event loop
     * 
     * This allows the browser to:
     * - Process user input events
     * - Update the UI
     * - Handle other pending tasks
     * 
     * @returns {Promise} Promise that resolves on next tick
     */
    _yield() {
        return new Promise(resolve => {
            if (this.options.yieldDelay > 0) {
                setTimeout(resolve, this.options.yieldDelay);
            } else {
                // Use requestAnimationFrame for smoother animations
                if (typeof requestAnimationFrame !== 'undefined') {
                    requestAnimationFrame(() => resolve());
                } else {
                    setTimeout(resolve, 0);
                }
            }
        });
    }

    /**
     * Check if currently rendering
     * 
     * @returns {boolean} True if rendering
     */
    isActive() {
        return this.isRendering;
    }

    /**
     * Reset operation counter
     */
    reset() {
        this.operationCount = 0;
        this.isRendering = false;
    }

    /**
     * Create a non-blocking animation loop
     * 
     * @param {Function} frameCallback - Callback for each frame
     * @param {number} maxFrames - Maximum number of frames (optional)
     * @returns {Promise} Promise that resolves when loop completes
     */
    async animationLoop(frameCallback, maxFrames = Infinity) {
        this.isRendering = true;
        let frameCount = 0;

        try {
            while (frameCount < maxFrames) {
                // Execute frame callback
                const shouldContinue = await frameCallback(frameCount);
                
                if (shouldContinue === false) {
                    break;
                }

                frameCount++;

                // Yield to browser
                await this._yield();
            }
        } finally {
            this.isRendering = false;
        }

        return frameCount;
    }

    /**
     * Wrap a text reveal animation to ensure non-blocking behavior
     * 
     * @param {TextRevealAnimation} textReveal - Text reveal animation instance
     * @param {string} text - Text to reveal
     * @param {boolean} append - Whether to append text
     * @returns {Promise} Promise that resolves when animation completes
     */
    async wrapTextReveal(textReveal, text, append = true) {
        // Ensure text reveal uses non-blocking mode
        textReveal.setOptions({ nonBlocking: true });
        
        // Execute animation
        return await this.executeWithYield(() => {
            return textReveal.revealText(text, append);
        });
    }

    /**
     * Create a debounced non-blocking renderer
     * 
     * @param {number} delay - Debounce delay in ms
     * @returns {Function} Debounced render function
     */
    createDebouncedRenderer(delay = 100) {
        let timeoutId = null;
        
        return (operation) => {
            if (timeoutId) {
                clearTimeout(timeoutId);
            }
            
            timeoutId = setTimeout(async () => {
                await this.executeWithYield(operation);
                timeoutId = null;
            }, delay);
        };
    }

    /**
     * Create a throttled non-blocking renderer
     * 
     * @param {number} interval - Throttle interval in ms
     * @returns {Function} Throttled render function
     */
    createThrottledRenderer(interval = 100) {
        let lastExecutionTime = 0;
        let pendingOperation = null;
        let timeoutId = null;
        
        return async (operation) => {
            const now = Date.now();
            const timeSinceLastExecution = now - lastExecutionTime;
            
            if (timeSinceLastExecution >= interval) {
                // Execute immediately
                lastExecutionTime = now;
                await this.executeWithYield(operation);
            } else {
                // Schedule for later
                pendingOperation = operation;
                
                if (!timeoutId) {
                    const remainingTime = interval - timeSinceLastExecution;
                    timeoutId = setTimeout(async () => {
                        if (pendingOperation) {
                            lastExecutionTime = Date.now();
                            await this.executeWithYield(pendingOperation);
                            pendingOperation = null;
                        }
                        timeoutId = null;
                    }, remainingTime);
                }
            }
        };
    }
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = NonBlockingRenderer;
}
