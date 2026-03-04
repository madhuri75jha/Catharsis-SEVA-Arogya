/**
 * Status Tracker Component
 * 
 * Displays status for each clip (recording, uploading, queued, transcribing, completed, failed)
 * Shows queue position, upload progress, and partial transcription results.
 * 
 * Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 11.3, 11.4, 11.7
 */

class StatusTracker {
    constructor(container, websocket, recordingSessionManager, options = {}) {
        this.container = container;
        this.websocket = websocket;
        this.recordingSessionManager = recordingSessionManager;
        this.options = {
            showUploadProgress: options.showUploadProgress !== false,
            showQueuePosition: options.showQueuePosition !== false,
            showPartialResults: options.showPartialResults !== false,
            autoScroll: options.autoScroll !== false
        };
        
        this.clipStatusElements = new Map(); // clipId -> DOM element
        this.eventHandlers = {
            statusChanged: [],
            transcriptionComplete: []
        };
        
        this._initializeWebSocketListeners();
        this._initializeSessionManagerListeners();
    }

    /**
     * Initialize WebSocket event listeners
     */
    _initializeWebSocketListeners() {
        // Listen for chunk_queued events
        this.websocket.on('chunk_queued', (data) => {
            this._handleChunkQueued(data);
        });

        // Listen for transcription_progress events
        this.websocket.on('transcription_progress', (data) => {
            this._handleTranscriptionProgress(data);
        });

        // Listen for clip_finalized events
        this.websocket.on('clip_finalized', (data) => {
            this._handleClipFinalized(data);
        });

        // Listen for error events
        this.websocket.on('error', (error) => {
            this._handleError(error);
        });
    }

    /**
     * Initialize recording session manager listeners
     */
    _initializeSessionManagerListeners() {
        // Listen for clip started events
        this.recordingSessionManager.on('clipStarted', (clip) => {
            this._handleClipStarted(clip);
        });

        // Listen for clip completed events
        this.recordingSessionManager.on('clipCompleted', (clip) => {
            this._handleClipCompleted(clip);
        });

        // Listen for status changed events
        this.recordingSessionManager.on('statusChanged', (data) => {
            this._updateClipStatus(data.clipId, data.status, data.text, data.error);
        });
    }

    /**
     * Handle clip started event
     */
    _handleClipStarted(clip) {
        console.log(`Status tracker: Clip started - ${clip.clipId}`);
        
        // Create status element for this clip
        const statusElement = this._createClipStatusElement(clip);
        this.clipStatusElements.set(clip.clipId, statusElement);
        
        // Append to container
        this.container.appendChild(statusElement);
        
        // Update status to recording
        this._updateClipStatusDisplay(clip.clipId, 'recording', {
            message: 'Recording...'
        });
        
        // Auto-scroll to bottom
        if (this.options.autoScroll) {
            this._scrollToBottom();
        }
    }

    /**
