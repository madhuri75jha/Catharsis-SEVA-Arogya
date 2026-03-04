/**
 * Async Transcription Controller
 * 
 * Integrates all async push-to-talk transcription components:
 * - AudioChunker for recording
 * - ChunkUploadManager for uploads
 * - WebSocketManager for connectivity
 * - RecordingSessionManager for session state
 * - Visual feedback and text reveal animations
 * 
 * Requirements: 1.1, 1.2, 3.8, 4.1
 */

class AsyncTranscriptionController {
    constructor(socketIO, consultationId) {
        this.consultationId = consultationId;
        
        // Initialize WebSocket manager
        this.websocket = new WebSocketManager(socketIO);
        
        // Initialize audio chunker
        this.audioChunker = new AudioChunker(7000); // 7 second chunks
        
        // Initialize upload manager
        this.uploadManager = new ChunkUploadManager(this.websocket, 5, 3);
        
        // Initialize session manager
        this.sessionManager = new RecordingSessionManager(consultationId);
        
        // Initialize visual feedback
        this.visualFeedback = new RecordingVisualFeedback();
        
        // Initialize text reveal animation
        this.textReveal = new TextRevealAnimation();
        
        // State
        this.isInitialized = false;
        this.currentClipId = null;
        
        // Bind methods
        this._setupEventHandlers();
    }
    
    /**
     * Initialize the controller
     */
    async initialize() {
        if (this.isInitialized) {
            console.warn('Controller already initialized');
            return;
        }
        
        try {
            // Initialize audio chunker (requests microphone permission)
            await this.audioChunker.initialize();
            
            console.log('Async Transcription Controller initialized');
            this.isInitialized = true;
            
        } catch (error) {
            console.error('Failed to initialize controller:', error);
            throw error;
        }
    }
    
    /**
     * Setup event handlers for all components
     */
    _setupEventHandlers() {
        // Audio chunker events
        this.audioChunker.on('chunk', (chunkData) => {
            this._handleAudioChunk(chunkData);
        });
        
        this.audioChunker.on('started', () => {
            console.log('Recording started');
            this.visualFeedback.startRecording();
        });
        
        this.audioChunker.on('stopped', () => {
            console.log('Recording stopped');
            this.visualFeedback.stopRecording();
            this._finalizeClip();
        });
        
        this.audioChunker.on('error', (error) => {
            console.error('Audio chunker error:', error);
            this._handleError(error);
        });
        
        // Upload manager events
        this.uploadManager.on('progress', (data) => {
            console.log('Upload progress:', data);
            this._updateUploadStatus(data);
        });
        
        this.uploadManager.on('success', (data) => {
            console.log('Upload success:', data);
        });
        
        this.uploadManager.on('error', (error) => {
            console.error('Upload error:', error);
            this._handleError(error);
        });
        
        // WebSocket events
        this.websocket.on('chunk_queued', (data) => {
            console.log('Chunk queued:', data);
        });
        
        this.websocket.on('transcription_progress', (data) => {
            console.log('Transcription progress:', data);
            this._handleTranscriptionProgress(data);
        });
        
        this.websocket.on('clip_finalized', (data) => {
            console.log('Clip finalized:', data);
        });
        
        this.websocket.on('reconnected', (data) => {
            console.log('WebSocket reconnected:', data);
        });
        
        this.websocket.on('error', (error) => {
            console.error('WebSocket error:', error);
            this._handleError(error);
        });
    }
    
    /**
     * Start recording a new clip
     */
    async startRecording() {
        if (!this.isInitialized) {
            throw new Error('Controller not initialized');
        }
        
        try {
            // Create new clip in session
            this.currentClipId = this.sessionManager.startNewClip();
            
            // Start audio chunking
            this.audioChunker.start();
            
            console.log(`Started recording clip: ${this.currentClipId}`);
            
        } catch (error) {
            console.error('Failed to start recording:', error);
            throw error;
        }
    }
    
    /**
     * Stop recording current clip
     */
    stopRecording() {
        if (!this.currentClipId) {
            console.warn('No active recording to stop');
            return;
        }
        
        // Stop audio chunking
        this.audioChunker.stop();
        
        console.log(`Stopped recording clip: ${this.currentClipId}`);
    }
    
    /**
     * Handle audio chunk from chunker
     */
    async _handleAudioChunk(chunkData) {
        if (!this.currentClipId) {
            console.warn('Received chunk without active clip');
            return;
        }
        
        try {
            // Upload chunk immediately
            await this.uploadManager.uploadChunk(
                chunkData,
                this.consultationId,
                this.currentClipId
            );
            
        } catch (error) {
            console.error('Failed to handle audio chunk:', error);
        }
    }
    
    /**
     * Finalize current clip
     */
    _finalizeClip() {
        if (!this.currentClipId) {
            return;
        }
        
        // Mark clip as complete in session
        this.sessionManager.completeClip(this.currentClipId);
        
        // Notify server that clip is complete
        this.websocket.socket.emit('clip_complete', {
            consultation_id: this.consultationId,
            clip_id: this.currentClipId
        });
        
        console.log(`Finalized clip: ${this.currentClipId}`);
        this.currentClipId = null;
    }
    
    /**
     * Handle transcription progress updates
     */
    _handleTranscriptionProgress(data) {
        const { clip_id, status, transcript_text, queue_position } = data;
        
        // Update session state
        this.sessionManager.updateClipStatus(clip_id, status);
        
        // Display transcription with text reveal animation
        if (transcript_text) {
            this.textReveal.revealText(transcript_text, document.getElementById('transcript-container'));
        }
        
        // Update status display
        this._updateStatusDisplay(data);
    }
    
    /**
     * Update upload status display
     */
    _updateUploadStatus(data) {
        const { chunkId, status, progress, retryCount } = data;
        
        // Update UI with upload status
        // This would be connected to a status display component
        console.log(`Upload status: ${status}`, data);
    }
    
    /**
     * Update status display
     */
    _updateStatusDisplay(data) {
        const { status, queue_position } = data;
        
        let statusText = '';
        switch (status) {
            case 'queued':
                statusText = `Queued (position: ${queue_position || 'unknown'})`;
                break;
            case 'transcribing':
                statusText = 'Transcribing...';
                break;
            case 'completed':
                statusText = 'Completed';
                break;
            case 'failed':
                statusText = 'Failed';
                break;
            default:
                statusText = status;
        }
        
        // Update status element if it exists
        const statusElement = document.getElementById('transcription-status');
        if (statusElement) {
            statusElement.textContent = statusText;
        }
    }
    
    /**
     * Handle errors
     */
    _handleError(error) {
        console.error('Controller error:', error);
        
        // Display error to user
        const errorElement = document.getElementById('error-message');
        if (errorElement) {
            errorElement.textContent = error.message || 'An error occurred';
            errorElement.style.display = 'block';
            
            // Hide after 5 seconds
            setTimeout(() => {
                errorElement.style.display = 'none';
            }, 5000);
        }
    }
    
    /**
     * Retry failed upload
     */
    async retryUpload(chunkId) {
        try {
            await this.uploadManager.retryUpload(chunkId);
        } catch (error) {
            console.error('Failed to retry upload:', error);
            this._handleError(error);
        }
    }
    
    /**
     * Retry failed transcription job
     */
    retryJob(jobId) {
        this.websocket.socket.emit('retry_job', {
            job_id: jobId
        });
    }
    
    /**
     * Get session statistics
     */
    getStatistics() {
        return {
            session: this.sessionManager.getStatistics(),
            uploads: this.uploadManager.getStatistics(),
            websocket: this.websocket.getStatus()
        };
    }
    
    /**
     * Cleanup resources
     */
    cleanup() {
        this.audioChunker.cleanup();
        this.uploadManager.clear();
        this.websocket.disconnect();
        this.visualFeedback.stopRecording();
        
        console.log('Controller cleaned up');
    }
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = AsyncTranscriptionController;
}
