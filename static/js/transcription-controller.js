/**
 * Transcription Controller
 * 
 * Main application controller that orchestrates audio capture, WebSocket communication,
 * and transcription display for real-time streaming transcription.
 */

class TranscriptionController {
    constructor(config) {
        this.config = config;
        this.audioCapture = null;
        this.websocket = null;
        this.display = null;
        this.isRecording = false;
        this.startButton = null;
        this.stopButton = null;
        this.statusIndicator = null;
    }

    /**
     * Initialize controller and components
     */
    async initialize() {
        try {
            console.log('Initializing TranscriptionController');

            // Get UI elements
            this.startButton = document.getElementById('start-recording');
            this.stopButton = document.getElementById('stop-recording');
            this.statusIndicator = document.getElementById('status-indicator');
            const displayContainer = document.getElementById('transcription-display');

            if (!this.startButton || !this.stopButton || !displayContainer) {
                throw new Error('Required UI elements not found');
            }

            // Initialize components
            this.audioCapture = new AudioCapture(
                this.config.sampleRate || 16000,
                this.config.chunkDurationMs || 250
            );

            this.websocket = new TranscriptionWebSocket(
                this.config.websocketUrl || window.location.origin,
                this.config.userId,
                this.config.quality || 'medium'
            );

            this.display = new TranscriptionDisplay(displayContainer);

            // Set up event handlers
            this._setupEventHandlers();

            // Initial UI state
            this._updateUI('ready');

            console.log('TranscriptionController initialized successfully');

        } catch (error) {
            console.error('Failed to initialize controller:', error);
            this._showError('Initialization failed: ' + error.message);
        }
    }

    /**
     * Set up event handlers for components and UI
     */
    _setupEventHandlers() {
        // Start button
        this.startButton.addEventListener('click', () => this.startRecording());

        // Stop button
        this.stopButton.addEventListener('click', () => this.stopRecording());

        // Audio capture events
        this.audioCapture.on('chunk', (pcmData) => {
            if (this.isRecording && this.websocket) {
                this.websocket.sendAudioChunk(pcmData);
            }
        });

        this.audioCapture.on('error', (error) => {
            console.error('Audio capture error:', error);
            this._showError(error.message);
            this.stopRecording();
        });

        // WebSocket events
        this.websocket.on('connected', () => {
            console.log('WebSocket connected');
            this._updateStatus('Connected');
        });

        this.websocket.on('session_ack', (data) => {
            console.log('Session started:', data.session_id);
            this._updateStatus('Recording...');
        });

        this.websocket.on('result', (data) => {
            if (data.is_partial) {
                this.display.updatePartial(data.text, data.segment_id);
            } else {
                this.display.appendFinal(data.text, data.segment_id);
            }
        });

        this.websocket.on('session_complete', (data) => {
            console.log('Session completed:', data);
            this._updateStatus('Transcription complete');
            this._showSuccess(`Recording saved (${data.total_duration.toFixed(1)}s)`);
        });

        this.websocket.on('error', (error) => {
            console.error('WebSocket error:', error);
            this._showError(error.message);
            
            if (!error.recoverable) {
                this.stopRecording();
            }
        });

        this.websocket.on('closed', () => {
            console.log('WebSocket closed');
            this._updateStatus('Disconnected');
        });

        this.websocket.on('heartbeat', () => {
            // Connection is alive
        });

        // Retry button (from error display)
        this.display.container.addEventListener('retry', () => {
            this.display.clear();
            this.startRecording();
        });
    }

    /**
     * Start recording and transcription
     */
    async startRecording() {
        if (this.isRecording) {
            console.warn('Already recording');
            return;
        }

        try {
            this._updateUI('starting');
            this._updateStatus('Initializing...');

            // Initialize audio capture
            await this.audioCapture.initialize();
            this._updateStatus('Connecting...');

            // Connect to WebSocket
            await this.websocket.connect();
            this._updateStatus('Starting session...');

            // Start session and wait for server acknowledgment before audio streaming
            await this._startSessionAndWaitForAck();

            // Start audio capture
            await this.audioCapture.start();

            this.isRecording = true;
            this._updateUI('recording');

            console.log('Recording started');

        } catch (error) {
            console.error('Failed to start recording:', error);
            this._showError('Failed to start recording: ' + error.message);
            this._updateUI('ready');
            
            // Cleanup on error
            this._cleanup();
        }
    }

    /**
     * Start websocket session and wait until session_ack arrives
     */
    _startSessionAndWaitForAck(timeoutMs = 10000) {
        return new Promise((resolve, reject) => {
            let settled = false;
            let timeoutId = null;
            let unsubscribeAck = null;
            let unsubscribeError = null;

            const cleanup = () => {
                if (timeoutId) {
                    clearTimeout(timeoutId);
                }
                if (unsubscribeAck) {
                    unsubscribeAck();
                }
                if (unsubscribeError) {
                    unsubscribeError();
                }
            };

            const onAck = () => {
                if (settled) return;
                settled = true;
                cleanup();
                resolve();
            };

            const onError = (error) => {
                if (settled) return;
                if (error && error.error_code === 'SESSION_START_FAILED') {
                    settled = true;
                    cleanup();
                    reject(new Error(error.message || 'Failed to start transcription session'));
                }
            };

            unsubscribeAck = this.websocket.on('session_ack', onAck);
            unsubscribeError = this.websocket.on('error', onError);

            timeoutId = setTimeout(() => {
                if (settled) return;
                settled = true;
                cleanup();
                reject(new Error('Timed out waiting for session acknowledgment'));
            }, timeoutMs);

            try {
                this.websocket.startSession();
            } catch (error) {
                settled = true;
                cleanup();
                reject(error);
            }
        });
    }

    /**
     * Stop recording and transcription
     */
    stopRecording() {
        if (!this.isRecording) {
            console.warn('Not recording');
            return;
        }

        try {
            this._updateUI('stopping');
            this._updateStatus('Stopping...');

            // Stop audio capture
            this.audioCapture.stop();

            // End WebSocket session
            this.websocket.endSession();

            this.isRecording = false;
            this._updateUI('ready');
            this._updateStatus('Ready');

            console.log('Recording stopped');

        } catch (error) {
            console.error('Error stopping recording:', error);
            this._showError('Error stopping recording: ' + error.message);
        }
    }

    /**
     * Convenience method - alias for startRecording()
     */
    async start() {
        return this.startRecording();
    }

    /**
     * Convenience method - alias for stopRecording()
     */
    async stop() {
        return this.stopRecording();
    }

    /**
     * Cleanup resources
     */
    _cleanup() {
        if (this.audioCapture) {
            try {
                this.audioCapture.stop();
            } catch (e) {
                console.warn('Error stopping audio capture:', e);
            }
        }

        if (this.websocket && this.websocket.isConnected) {
            try {
                this.websocket.disconnect();
            } catch (e) {
                console.warn('Error disconnecting websocket:', e);
            }
        }

        this.isRecording = false;
    }

    /**
     * Update UI state
     */
    _updateUI(state) {
        switch (state) {
            case 'ready':
                this.startButton.disabled = false;
                this.stopButton.disabled = true;
                this.startButton.textContent = 'Start Recording';
                break;

            case 'starting':
                this.startButton.disabled = true;
                this.stopButton.disabled = true;
                this.startButton.textContent = 'Starting...';
                break;

            case 'recording':
                this.startButton.disabled = true;
                this.stopButton.disabled = false;
                this.startButton.textContent = 'Recording...';
                this.stopButton.textContent = 'Stop Recording';
                break;

            case 'stopping':
                this.startButton.disabled = true;
                this.stopButton.disabled = true;
                this.stopButton.textContent = 'Stopping...';
                break;
        }
    }

    /**
     * Update status indicator
     */
    _updateStatus(message) {
        if (this.statusIndicator) {
            this.statusIndicator.textContent = message;
        }
    }

    /**
     * Show error message
     */
    _showError(message) {
        this.display.showError(message);
        this._updateStatus('Error: ' + message);
    }

    /**
     * Show success message
     */
    _showSuccess(message) {
        this.display.showStatus(message);
    }

    /**
     * Get current transcript
     */
    getTranscript() {
        return this.display.getTranscript();
    }

    /**
     * Backward-compatible alias used by page scripts.
     */
    getTranscriptText() {
        return this.getTranscript();
    }
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = TranscriptionController;
}
