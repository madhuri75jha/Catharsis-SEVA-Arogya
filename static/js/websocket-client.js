/**
 * Transcription WebSocket Client
 * 
 * Manages WebSocket connection to backend for real-time audio streaming
 * and transcription result delivery using Socket.IO.
 */

class TranscriptionWebSocket {
    constructor(url, userId, quality = 'medium') {
        this.url = url;
        this.userId = userId;
        this.quality = quality;
        this.socket = null;
        this.sessionId = null;
        this.isConnected = false;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 3;
        this.reconnectDelay = 1000; // Start with 1 second
        this.audioBuffer = [];
        this.bufferedBytes = 0;
        this.nextChunkId = 0;
        this.maxBufferSize = 5 * 16000 * 2; // 5 seconds at 16kHz, 16-bit
        this.eventHandlers = {
            connected: [],
            result: [],
            error: [],
            closed: [],
            session_ack: [],
            session_complete: [],
            heartbeat: []
        };
    }

    /**
     * Connect to WebSocket server
     */
    async connect() {
        return new Promise((resolve, reject) => {
            try {
                // Reuse an already connected socket instead of creating duplicates.
                if (this.socket && this.socket.connected) {
                    this.isConnected = true;
                    resolve();
                    return;
                }

                // Ensure stale sockets are fully torn down before creating a new one.
                if (this.socket) {
                    try {
                        this.socket.removeAllListeners();
                        this.socket.disconnect();
                    } catch (cleanupError) {
                        console.warn('Error cleaning up stale socket:', cleanupError);
                    }
                    this.socket = null;
                    this.isConnected = false;
                }

                // Initialize Socket.IO connection
                this.socket = io(this.url, {
                    transports: ['websocket', 'polling'],
                    reconnection: false, // We'll handle reconnection manually
                    timeout: 10000
                });

                // Connection successful
                this.socket.on('connect', () => {
                    console.log('WebSocket connected');
                    this.isConnected = true;
                    this.reconnectAttempts = 0;
                    this._emitEvent('connected');
                    resolve();
                });

                // Connection error
                this.socket.on('connect_error', (error) => {
                    console.error('WebSocket connection error:', error);
                    
                    if (this.reconnectAttempts < this.maxReconnectAttempts) {
                        this._attemptReconnect();
                    } else {
                        this._emitEvent('error', {
                            code: 'CONNECTION_FAILED',
                            message: 'Connection lost. Please check your internet connection.',
                            recoverable: false
                        });
                        reject(error);
                    }
                });

                // Disconnection
                this.socket.on('disconnect', (reason) => {
                    console.log('WebSocket disconnected:', reason);
                    this.isConnected = false;
                    
                    if (reason === 'io server disconnect') {
                        // Server disconnected us, don't reconnect
                        this._emitEvent('closed', { reason });
                    } else if (reason === 'transport close' || reason === 'ping timeout') {
                        // Connection lost, attempt reconnect
                        if (this.reconnectAttempts < this.maxReconnectAttempts) {
                            this._attemptReconnect();
                        } else {
                            this._emitEvent('error', {
                                code: 'CONNECTION_LOST',
                                message: 'Connection lost. Please check your internet connection.',
                                recoverable: false
                            });
                        }
                    }
                });

                // Session acknowledgment
                this.socket.on('session_ack', (data) => {
                    console.log('Session acknowledged:', data);
                    this.sessionId = data.session_id;
                    this._emitEvent('session_ack', data);
                });

                // Transcription results
                this.socket.on('transcription_result', (data) => {
                    console.log('Transcription result:', data.is_partial ? 'partial' : 'final', data.text);
                    this._emitEvent('result', data);
                });

                // Session complete
                this.socket.on('session_complete', (data) => {
                    console.log('Session complete:', data);
                    this._emitEvent('session_complete', data);
                });

                // Error messages
                this.socket.on('error', (data) => {
                    console.error('Server error:', data);
                    this._emitEvent('error', data);
                });

                // Heartbeat
                this.socket.on('heartbeat', (data) => {
                    this._emitEvent('heartbeat', data);
                });

            } catch (error) {
                console.error('Failed to initialize WebSocket:', error);
                reject(error);
            }
        });
    }

    /**
     * Attempt to reconnect with exponential backoff
     */
    _attemptReconnect() {
        this.reconnectAttempts++;
        const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1);
        
        console.log(`Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts}/${this.maxReconnectAttempts})`);
        
        setTimeout(() => {
            if (this.socket) {
                this.socket.connect();
            }
        }, delay);
    }

    /**
     * Start a new transcription session
     */
    startSession() {
        if (!this.isConnected) {
            throw new Error('Not connected to server');
        }

        this.sessionId = this._generateSessionId();
        this.nextChunkId = 0;
        
        const sessionData = {
            type: 'session_start',
            user_id: this.userId,
            session_id: this.sessionId,
            quality: this.quality,
            timestamp: Date.now() / 1000
        };

        console.log('Starting session:', this.sessionId);
        this.socket.emit('session_start', sessionData);
    }

    /**
     * Send audio chunk to server
     * 
     * @param {ArrayBuffer|Int16Array} audioData - PCM audio data
     * @param {boolean} isFlushingBuffer - Internal flag to prevent recursive flushing
     */
    sendAudioChunk(audioData, isFlushingBuffer = false, forcedChunkId = null) {
        const chunkId = Number.isInteger(forcedChunkId) ? forcedChunkId : this.nextChunkId++;

        if (!this.isConnected) {
            // Buffer audio during disconnection
            this._bufferAudio(audioData, chunkId);
            return;
        }

        if (!this.sessionId) {
            console.warn('No active session, cannot send audio chunk');
            return;
        }

        try {
            // Convert to base64 for JSON transmission
            const int16Array = audioData instanceof Int16Array ? audioData : new Int16Array(audioData);
            const uint8Array = new Uint8Array(int16Array.buffer);
            const base64Audio = this._arrayBufferToBase64(uint8Array);

            const chunkData = {
                session_id: this.sessionId,
                audio_data: base64Audio,
                chunk_id: chunkId
            };

            this.socket.emit('audio_chunk', chunkData);

            // Send any buffered audio (but only if not already flushing to prevent recursion)
            if (!isFlushingBuffer && this.audioBuffer.length > 0) {
                this._flushBuffer();
            }

        } catch (error) {
            console.error('Failed to send audio chunk:', error);
            this._emitEvent('error', {
                code: 'SEND_FAILED',
                message: 'Failed to send audio data',
                recoverable: true
            });
        }
    }

    /**
     * End the current session
     */
    endSession() {
        if (!this.sessionId) {
            console.warn('No active session to end');
            return;
        }

        const endData = {
            type: 'session_end',
            session_id: this.sessionId,
            timestamp: Date.now() / 1000
        };

        console.log('Ending session:', this.sessionId);
        this.socket.emit('session_end', endData);
        
        this.sessionId = null;
        this.audioBuffer = [];
        this.bufferedBytes = 0;
    }

    /**
     * Disconnect from server
     */
    disconnect() {
        if (this.socket) {
            this.socket.disconnect();
            this.socket = null;
        }
        this.isConnected = false;
        this.sessionId = null;
        this.audioBuffer = [];
        this.bufferedBytes = 0;
        console.log('WebSocket disconnected');
    }

    /**
     * Buffer audio during temporary disconnection
     */
    _bufferAudio(audioData, chunkId) {
        const int16Array = audioData instanceof Int16Array ? audioData : new Int16Array(audioData);
        const bytes = int16Array.length * 2;

        if (this.bufferedBytes + bytes > this.maxBufferSize) {
            console.warn('Audio buffer overflow, dropping oldest chunks');
            // Remove oldest chunks to make room
            const removeBytes = bytes;
            let removed = 0;
            while (removed < removeBytes && this.audioBuffer.length > 0) {
                const chunk = this.audioBuffer.shift();
                removed += chunk.data.length * 2;
            }
            this.bufferedBytes = Math.max(0, this.bufferedBytes - removed);
        }

        this.audioBuffer.push({
            id: chunkId,
            data: int16Array
        });
        this.bufferedBytes += bytes;
        console.log(`Buffered audio chunk: ${this.audioBuffer.length} chunks in buffer`);
    }

    /**
     * Flush buffered audio chunks
     */
    _flushBuffer() {
        console.log(`Flushing ${this.audioBuffer.length} buffered chunks`);
        
        while (this.audioBuffer.length > 0) {
            const chunk = this.audioBuffer.shift();
            this.bufferedBytes = Math.max(0, this.bufferedBytes - (chunk.data.length * 2));
            // Pass true to prevent recursive flushing
            this.sendAudioChunk(chunk.data, true, chunk.id);
        }
    }

    /**
     * Convert ArrayBuffer to base64 string
     */
    _arrayBufferToBase64(buffer) {
        let binary = '';
        const bytes = new Uint8Array(buffer);
        const len = bytes.byteLength;
        
        for (let i = 0; i < len; i++) {
            binary += String.fromCharCode(bytes[i]);
        }
        
        return window.btoa(binary);
    }

    /**
     * Generate unique session ID
     */
    _generateSessionId() {
        if (window.crypto && typeof window.crypto.randomUUID === 'function') {
            return window.crypto.randomUUID();
        }

        // RFC4122 v4 fallback for older browsers.
        return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
            const r = Math.random() * 16 | 0;
            const v = c === 'x' ? r : (r & 0x3 | 0x8);
            return v.toString(16);
        });
    }

    /**
     * Register event handler
     * 
     * @param {string} event - Event name
     * @param {Function} callback - Callback function
     */
    on(event, callback) {
        if (!this.eventHandlers[event]) {
            throw new Error(`Unknown event: ${event}`);
        }
        
        this.eventHandlers[event].push(callback);
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
     * Get connection status
     */
    getStatus() {
        return {
            connected: this.isConnected,
            sessionId: this.sessionId,
            reconnectAttempts: this.reconnectAttempts,
            bufferedChunks: this.audioBuffer.length
        };
    }
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = TranscriptionWebSocket;
}
