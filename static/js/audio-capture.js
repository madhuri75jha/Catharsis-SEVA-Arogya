/**
 * Audio Capture Module
 * 
 * Captures microphone audio using Web Audio API and converts to PCM format
 * for streaming to the backend.
 */

class AudioCapture {
    constructor(sampleRate = 16000, chunkDurationMs = 250) {
        this.sampleRate = sampleRate;
        this.chunkDurationMs = chunkDurationMs;
        this.audioContext = null;
        this.mediaStream = null;
        this.sourceNode = null;
        this.processorNode = null;
        this.isCapturing = false;
        this.eventHandlers = {
            chunk: [],
            error: []
        };
    }

    /**
     * Initialize audio capture and request microphone permissions
     */
    async initialize() {
        try {
            // Check browser support
            const AudioContextCtor = window.AudioContext || window.webkitAudioContext;
            if (!AudioContextCtor) {
                throw new Error('Web Audio API (AudioContext) not supported in this browser');
            }

            if (!window.isSecureContext) {
                throw new Error('Microphone access requires a secure context (HTTPS or localhost)');
            }

            if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
                throw new Error('Microphone access is not available in this browser');
            }

            // Request microphone access
            this.mediaStream = await navigator.mediaDevices.getUserMedia({
                audio: {
                    channelCount: 1,
                    sampleRate: this.sampleRate,
                    echoCancellation: true,
                    noiseSuppression: true,
                    autoGainControl: true
                }
            });

            // Create AudioContext with target sample rate
            this.audioContext = new AudioContextCtor({
                sampleRate: this.sampleRate
            });

            // iOS/Safari can require a user gesture to resume AudioContext
            if (this.audioContext.state === 'suspended') {
                const resumeContext = async () => {
                    try {
                        await this.audioContext.resume();
                    } catch (e) {
                        console.warn('AudioContext resume failed:', e);
                    }
                };

                document.addEventListener('click', resumeContext, { once: true });
                document.addEventListener('touchend', resumeContext, { once: true });
            }

            // Create source node from media stream
            this.sourceNode = this.audioContext.createMediaStreamSource(this.mediaStream);

            // Create processor node for audio processing
            // Buffer size: 4096 samples = ~256ms at 16kHz
            const bufferSize = 4096;
            this.processorNode = this.audioContext.createScriptProcessor(bufferSize, 1, 1);

            // Set up audio processing callback
            this.processorNode.onaudioprocess = (event) => {
                if (!this.isCapturing) return;

                const inputData = event.inputBuffer.getChannelData(0);
                const pcmData = this._convertToPCM(inputData);
                
                // Emit chunk event
                this._emitEvent('chunk', pcmData);
            };

            console.log(`AudioCapture initialized: ${this.sampleRate}Hz, ${this.chunkDurationMs}ms chunks`);

        } catch (error) {
            console.error('Failed to initialize audio capture:', error);
            
            // Emit error event
            this._emitEvent('error', {
                code: 'INITIALIZATION_FAILED',
                message: error.message || 'Failed to access microphone',
                originalError: error
            });
            
            throw error;
        }
    }

    /**
     * Start audio capture
     */
    async start() {
        if (!this.audioContext || !this.sourceNode || !this.processorNode) {
            throw new Error('Audio capture not initialized. Call initialize() first.');
        }

        if (this.isCapturing) {
            console.warn('Audio capture already started');
            return;
        }

        // Ensure AudioContext is running before connecting processing graph.
        // In some browsers, autostart flows can leave context suspended.
        if (this.audioContext.state === 'suspended') {
            try {
                await this.audioContext.resume();
            } catch (resumeError) {
                console.error('AudioContext resume failed on start:', resumeError);
                throw new Error('Microphone is blocked. Tap/click the page and try again.');
            }
        }

        if (this.audioContext.state !== 'running') {
            throw new Error('Microphone audio engine did not start. Tap/click the page and try again.');
        }

        // Connect audio nodes
        this.sourceNode.connect(this.processorNode);
        this.processorNode.connect(this.audioContext.destination);

        this.isCapturing = true;
        console.log('Audio capture started');
    }

    /**
     * Stop audio capture and cleanup resources
     */
    stop() {
        if (!this.isCapturing) {
            return;
        }

        this.isCapturing = false;

        // Disconnect audio nodes
        if (this.sourceNode && this.processorNode) {
            try {
                this.sourceNode.disconnect();
                this.processorNode.disconnect();
            } catch (e) {
                console.warn('Error disconnecting audio nodes:', e);
            }
        }

        // Stop media stream tracks
        if (this.mediaStream) {
            this.mediaStream.getTracks().forEach(track => track.stop());
        }

        // Close audio context
        if (this.audioContext && this.audioContext.state !== 'closed') {
            this.audioContext.close();
        }

        console.log('Audio capture stopped');
    }

    /**
     * Convert Float32Array audio data to Int16Array PCM format
     * 
     * @param {Float32Array} float32Data - Audio data in range [-1.0, 1.0]
     * @returns {Int16Array} PCM audio data (16-bit signed integers)
     */
    _convertToPCM(float32Data) {
        const pcmData = new Int16Array(float32Data.length);
        
        for (let i = 0; i < float32Data.length; i++) {
            // Clamp to [-1.0, 1.0] range
            let sample = Math.max(-1, Math.min(1, float32Data[i]));
            
            // Convert to 16-bit signed integer
            pcmData[i] = sample < 0 ? sample * 0x8000 : sample * 0x7FFF;
        }
        
        return pcmData;
    }

    /**
     * Register event handler
     * 
     * @param {string} event - Event name ('chunk' or 'error')
     * @param {Function} callback - Callback function
     */
    on(event, callback) {
        if (!this.eventHandlers[event]) {
            throw new Error(`Unknown event: ${event}`);
        }
        
        this.eventHandlers[event].push(callback);
    }

    /**
     * Emit event to registered handlers
     * 
     * @param {string} event - Event name
     * @param {*} data - Event data
     */
    _emitEvent(event, data) {
        if (this.eventHandlers[event]) {
            this.eventHandlers[event].forEach(callback => {
                try {
                    callback(data);
                } catch (error) {
                    console.error(`Error in ${event} event handler:`, error);
                }
            });
        }
    }

    /**
     * Get current audio context state
     * 
     * @returns {string} Audio context state
     */
    getState() {
        return this.audioContext ? this.audioContext.state : 'not_initialized';
    }

    /**
     * Check if currently capturing
     * 
     * @returns {boolean} True if capturing
     */
    isActive() {
        return this.isCapturing;
    }
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = AudioCapture;
}
