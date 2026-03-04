/**
 * Audio Chunker Module
 * 
 * Splits audio recording into 5-10 second chunks using MediaRecorder API
 * for asynchronous push-to-talk transcription.
 * 
 * Requirements: 11.1, 11.5
 */

class AudioChunker {
    constructor(chunkDurationMs = 7000) {
        this.chunkDurationMs = chunkDurationMs; // Default 7 seconds
        this.mediaRecorder = null;
        this.mediaStream = null;
        this.isRecording = false;
        this.chunkSequence = 0;
        this.eventHandlers = {
            chunk: [],
            error: [],
            started: [],
            stopped: []
        };
    }

    /**
     * Initialize audio chunker and request microphone permissions
     */
    async initialize() {
        try {
            // Check browser support
            if (!window.MediaRecorder) {
                throw new Error('MediaRecorder API not supported in this browser');
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
                    sampleRate: 16000,
                    echoCancellation: true,
                    noiseSuppression: true,
                    autoGainControl: true
                }
            });

            // Determine best audio format
            const mimeType = this._getBestMimeType();
            
            // Create MediaRecorder with timeslice for chunking
            this.mediaRecorder = new MediaRecorder(this.mediaStream, {
                mimeType: mimeType,
                audioBitsPerSecond: 64000 // 64 kbps for good quality
            });

            // Set up event handlers
            this.mediaRecorder.ondataavailable = (event) => {
                if (event.data && event.data.size > 0) {
                    this._handleChunk(event.data);
                }
            };

            this.mediaRecorder.onerror = (event) => {
                console.error('MediaRecorder error:', event.error);
                this._emitEvent('error', {
                    code: 'RECORDING_ERROR',
                    message: event.error?.message || 'Recording error occurred',
                    originalError: event.error
                });
            };

            this.mediaRecorder.onstart = () => {
                console.log('MediaRecorder started');
                this._emitEvent('started');
            };

            this.mediaRecorder.onstop = () => {
                console.log('MediaRecorder stopped');
                this._emitEvent('stopped');
            };

            console.log(`AudioChunker initialized: ${this.chunkDurationMs}ms chunks, ${mimeType}`);

        } catch (error) {
            console.error('Failed to initialize audio chunker:', error);
            this._emitEvent('error', {
                code: 'INITIALIZATION_FAILED',
                message: error.message || 'Failed to access microphone',
                originalError: error
            });
            throw error;
        }
    }

    /**
     * Start recording with automatic chunking
     */
    start() {
        if (!this.mediaRecorder) {
            throw new Error('Audio chunker not initialized. Call initialize() first.');
        }

        if (this.isRecording) {
            console.warn('Audio chunker already recording');
            return;
        }

        // Reset chunk sequence
        this.chunkSequence = 0;

        // Start recording with timeslice for automatic chunking
        this.mediaRecorder.start(this.chunkDurationMs);
        this.isRecording = true;

        console.log(`Audio chunking started: ${this.chunkDurationMs}ms chunks`);
    }

    /**
     * Stop recording
     */
    stop() {
        if (!this.isRecording) {
            console.warn('Audio chunker not recording');
            return;
        }

        if (this.mediaRecorder && this.mediaRecorder.state !== 'inactive') {
            this.mediaRecorder.stop();
        }

        this.isRecording = false;
        console.log('Audio chunking stopped');
    }

    /**
     * Cleanup resources
     */
    cleanup() {
        this.stop();

        if (this.mediaStream) {
            this.mediaStream.getTracks().forEach(track => track.stop());
            this.mediaStream = null;
        }

        this.mediaRecorder = null;
        console.log('Audio chunker cleaned up');
    }

    /**
     * Handle audio chunk from MediaRecorder
     * 
     * @param {Blob} blob - Audio chunk blob
     */
    async _handleChunk(blob) {
        try {
            const chunkId = this._generateChunkId();
            const sequence = this.chunkSequence++;

            // Convert blob to ArrayBuffer
            const arrayBuffer = await blob.arrayBuffer();

            // Emit chunk event with metadata
            this._emitEvent('chunk', {
                chunkId: chunkId,
                sequence: sequence,
                data: arrayBuffer,
                blob: blob,
                size: blob.size,
                mimeType: blob.type,
                timestamp: Date.now()
            });

            console.log(`Audio chunk ready: sequence=${sequence}, size=${blob.size} bytes`);

        } catch (error) {
            console.error('Error handling audio chunk:', error);
            this._emitEvent('error', {
                code: 'CHUNK_PROCESSING_FAILED',
                message: 'Failed to process audio chunk',
                originalError: error
            });
        }
    }

    /**
     * Get best supported MIME type for recording
     * 
     * @returns {string} MIME type
     */
    _getBestMimeType() {
        const types = [
            'audio/webm;codecs=opus',
            'audio/webm',
            'audio/ogg;codecs=opus',
            'audio/ogg',
            'audio/mp4',
            'audio/mpeg'
        ];

        for (const type of types) {
            if (MediaRecorder.isTypeSupported(type)) {
                return type;
            }
        }

        // Fallback to default
        return '';
    }

    /**
     * Generate unique chunk ID
     * 
     * @returns {string} Chunk ID
     */
    _generateChunkId() {
        const timestamp = Date.now();
        const random = Math.floor(Math.random() * 10000);
        return `chunk_${timestamp}_${random}`;
    }

    /**
     * Register event handler
     * 
     * @param {string} event - Event name ('chunk', 'error', 'started', 'stopped')
     * @param {Function} callback - Callback function
     */
    on(event, callback) {
        if (!this.eventHandlers[event]) {
            throw new Error(`Unknown event: ${event}`);
        }
        
        this.eventHandlers[event].push(callback);
        
        // Return unsubscribe function
        return () => this.off(event, callback);
    }

    /**
     * Unregister event handler
     * 
     * @param {string} event - Event name
     * @param {Function} callback - Callback function
     */
    off(event, callback) {
        if (!this.eventHandlers[event]) {
            return;
        }
        
        this.eventHandlers[event] = this.eventHandlers[event]
            .filter(handler => handler !== callback);
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
     * Check if currently recording
     * 
     * @returns {boolean} True if recording
     */
    isActive() {
        return this.isRecording;
    }

    /**
     * Get current state
     * 
     * @returns {string} State ('inactive', 'recording', 'paused')
     */
    getState() {
        if (!this.mediaRecorder) {
            return 'not_initialized';
        }
        return this.mediaRecorder.state;
    }
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = AudioChunker;
}
