/**
 * Chunk Upload Manager
 * 
 * Manages immediate upload of audio chunks with retry logic and progress tracking.
 * 
 * Requirements: 1.4, 5.1, 5.2, 6.3, 6.4
 */

class ChunkUploadManager {
    constructor(websocket, maxPendingUploads = 5, maxRetries = 3) {
        this.websocket = websocket;
        this.maxPendingUploads = maxPendingUploads;
        this.maxRetries = maxRetries;
        this.pendingUploads = new Map(); // chunkId -> upload metadata
        this.uploadQueue = [];
        this.failedChunks = new Map(); // chunkId -> {chunk, consultationId, clipId}
        this.eventHandlers = {
            progress: [],
            success: [],
            error: [],
            queued: []
        };
    }

    /**
     * Upload audio chunk immediately
     * 
     * @param {Object} chunk - Chunk data from AudioChunker
     * @param {string} consultationId - Consultation identifier
     * @param {string} clipId - Clip identifier
     * @returns {Promise} Upload promise
     */
    async uploadChunk(chunk, consultationId, clipId) {
        try {
            // Check if we've reached the pending upload limit
            if (this.pendingUploads.size >= this.maxPendingUploads) {
                console.warn(`Pending upload limit reached (${this.maxPendingUploads}), queueing chunk`);
                
                // Queue the chunk
                this.uploadQueue.push({ chunk, consultationId, clipId });
                
                this._emitEvent('queued', {
                    chunkId: chunk.chunkId,
                    sequence: chunk.sequence,
                    queuePosition: this.uploadQueue.length
                });
                
                // Show warning to user
                this._emitEvent('error', {
                    code: 'UPLOAD_LIMIT_REACHED',
                    message: 'Upload limit reached. Please wait for current uploads to complete.',
                    recoverable: true,
                    chunkId: chunk.chunkId
                });
                
                return;
            }

            // Create upload metadata
            const uploadMetadata = {
                chunkId: chunk.chunkId,
                sequence: chunk.sequence,
                consultationId: consultationId,
                clipId: clipId,
                retryCount: 0,
                startTime: Date.now(),
                size: chunk.size
            };

            // Add to pending uploads
            this.pendingUploads.set(chunk.chunkId, uploadMetadata);

            // Emit progress event
            this._emitEvent('progress', {
                chunkId: chunk.chunkId,
                sequence: chunk.sequence,
                status: 'uploading',
                progress: 0
            });

            // Perform upload with retry logic
            await this._uploadWithRetry(chunk, uploadMetadata);

        } catch (error) {
            console.error('Upload failed:', error);
            
            // Store failed chunk for manual retry
            this.failedChunks.set(chunk.chunkId, {
                chunk: chunk,
                consultationId: consultationId,
                clipId: clipId
            });
            
            // Remove from pending uploads
            this.pendingUploads.delete(chunk.chunkId);
            
            // Emit error event with retry option
            this._emitEvent('error', {
                code: 'UPLOAD_FAILED',
                message: error.message || 'Failed to upload audio chunk',
                recoverable: true,
                chunkId: chunk.chunkId,
                sequence: chunk.sequence,
                canRetry: true
            });
            
            // Process next queued upload
            this._processQueue();
        }
    }

    /**
     * Upload chunk with retry logic
     * 
     * @param {Object} chunk - Chunk data
     * @param {Object} metadata - Upload metadata
     */
    async _uploadWithRetry(chunk, metadata) {
        while (metadata.retryCount <= this.maxRetries) {
            try {
                // Convert ArrayBuffer to base64
                const base64Audio = await this._arrayBufferToBase64(chunk.data);

                // Send via WebSocket
                await this._sendChunkViaWebSocket(
                    metadata.consultationId,
                    metadata.clipId,
                    chunk.sequence,
                    base64Audio
                );

                // Upload successful
                const duration = Date.now() - metadata.startTime;
                console.log(`Chunk uploaded successfully: ${chunk.chunkId} (${duration}ms)`);

                // Remove from pending uploads
                this.pendingUploads.delete(chunk.chunkId);

                // Emit success event
                this._emitEvent('success', {
                    chunkId: chunk.chunkId,
                    sequence: chunk.sequence,
                    duration: duration,
                    size: chunk.size
                });

                // Process next queued upload
                this._processQueue();

                return;

            } catch (error) {
                metadata.retryCount++;
                
                if (metadata.retryCount <= this.maxRetries) {
                    // Calculate exponential backoff delay
                    const backoffDelay = Math.pow(2, metadata.retryCount - 1) * 1000; // 1s, 2s, 4s
                    
                    console.warn(`Upload failed, retrying in ${backoffDelay}ms (attempt ${metadata.retryCount}/${this.maxRetries})`);
                    
                    // Emit progress event with retry status
                    this._emitEvent('progress', {
                        chunkId: chunk.chunkId,
                        sequence: chunk.sequence,
                        status: 'retrying',
                        retryCount: metadata.retryCount,
                        maxRetries: this.maxRetries
                    });
                    
                    // Wait for backoff period
                    await this._sleep(backoffDelay);
                } else {
                    // Max retries exceeded
                    throw new Error(`Upload failed after ${this.maxRetries} retries: ${error.message}`);
                }
            }
        }
    }

    /**
     * Send chunk via WebSocket
     * 
     * @param {string} consultationId - Consultation ID
     * @param {string} clipId - Clip ID
     * @param {number} sequence - Chunk sequence
     * @param {string} base64Audio - Base64 encoded audio
     * @returns {Promise} Promise that resolves when chunk is queued
     */
    _sendChunkViaWebSocket(consultationId, clipId, sequence, base64Audio) {
        return new Promise((resolve, reject) => {
            if (!this.websocket || !this.websocket.isConnected) {
                reject(new Error('WebSocket not connected'));
                return;
            }

            // Set up one-time listeners for response
            let timeoutId = null;
            let unsubscribeQueued = null;
            let unsubscribeError = null;

            const cleanup = () => {
                if (timeoutId) clearTimeout(timeoutId);
                if (unsubscribeQueued) unsubscribeQueued();
                if (unsubscribeError) unsubscribeError();
            };

            // Listen for chunk_queued event
            unsubscribeQueued = this.websocket.on('chunk_queued', (data) => {
                if (data.clip_id === clipId && data.chunk_sequence === sequence) {
                    cleanup();
                    resolve(data);
                }
            });

            // Listen for error event
            unsubscribeError = this.websocket.on('error', (error) => {
                if (error.error_code === 'CHUNK_UPLOAD_FAILED') {
                    cleanup();
                    reject(new Error(error.message));
                }
            });

            // Set timeout
            timeoutId = setTimeout(() => {
                cleanup();
                reject(new Error('Upload timeout'));
            }, 10000); // 10 second timeout

            // Send chunk_upload event
            try {
                this.websocket.socket.emit('chunk_upload', {
                    consultation_id: consultationId,
                    clip_id: clipId,
                    chunk_sequence: sequence,
                    audio_data: base64Audio
                });
            } catch (error) {
                cleanup();
                reject(error);
            }
        });
    }

    /**
     * Process next queued upload
     */
    _processQueue() {
        if (this.uploadQueue.length === 0) {
            return;
        }

        if (this.pendingUploads.size >= this.maxPendingUploads) {
            return;
        }

        // Get next upload from queue
        const { chunk, consultationId, clipId } = this.uploadQueue.shift();
        
        // Upload it
        this.uploadChunk(chunk, consultationId, clipId);
    }

    /**
     * Retry failed upload manually
     * 
     * @param {string} chunkId - Chunk ID to retry
     * @returns {Promise} Upload promise
     */
    async retryUpload(chunkId) {
        const failedChunk = this.failedChunks.get(chunkId);
        
        if (!failedChunk) {
            this._emitEvent('error', {
                code: 'CHUNK_NOT_FOUND',
                message: 'Failed chunk not found. It may have already been retried.',
                recoverable: false,
                chunkId: chunkId
            });
            return;
        }
        
        // Remove from failed chunks
        this.failedChunks.delete(chunkId);
        
        // Retry the upload
        console.log(`Manually retrying upload for chunk: ${chunkId}`);
        await this.uploadChunk(
            failedChunk.chunk,
            failedChunk.consultationId,
            failedChunk.clipId
        );
    }

    /**
     * Convert ArrayBuffer to base64 string
     * 
     * @param {ArrayBuffer} buffer - Array buffer
     * @returns {Promise<string>} Base64 string
     */
    async _arrayBufferToBase64(buffer) {
        return new Promise((resolve, reject) => {
            try {
                const blob = new Blob([buffer]);
                const reader = new FileReader();
                
                reader.onloadend = () => {
                    // Extract base64 data (remove data URL prefix)
                    const base64 = reader.result.split(',')[1];
                    resolve(base64);
                };
                
                reader.onerror = () => {
                    reject(new Error('Failed to convert to base64'));
                };
                
                reader.readAsDataURL(blob);
            } catch (error) {
                reject(error);
            }
        });
    }

    /**
     * Sleep for specified milliseconds
     * 
     * @param {number} ms - Milliseconds
     * @returns {Promise} Promise that resolves after delay
     */
    _sleep(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }

    /**
     * Get upload statistics
     * 
     * @returns {Object} Statistics
     */
    getStatistics() {
        return {
            pendingUploads: this.pendingUploads.size,
            queuedUploads: this.uploadQueue.length,
            failedUploads: this.failedChunks.size,
            maxPendingUploads: this.maxPendingUploads
        };
    }

    /**
     * Clear all pending uploads and queue
     */
    clear() {
        this.pendingUploads.clear();
        this.uploadQueue = [];
        this.failedChunks.clear();
        console.log('Upload manager cleared');
    }

    /**
     * Register event handler
     * 
     * @param {string} event - Event name ('progress', 'success', 'error', 'queued')
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
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = ChunkUploadManager;
}
