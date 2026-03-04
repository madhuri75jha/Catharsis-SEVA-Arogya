/**
 * Recording Session State Manager
 * 
 * Manages multi-clip recording sessions within a consultation.
 * Tracks multiple clips, assigns clip ordering, and allows starting new recordings
 * while previous clips are transcribing.
 * 
 * Requirements: 1.1, 1.2, 1.3, 4.3
 */

class RecordingSessionManager {
    constructor(consultationId) {
        this.consultationId = consultationId;
        this.clips = new Map(); // clipId -> clip metadata
        this.nextClipOrder = 1;
        this.currentClipId = null;
        this.eventHandlers = {
            clipStarted: [],
            clipCompleted: [],
            statusChanged: []
        };
    }

    /**
     * Start a new recording clip
     * 
     * @returns {Object} Clip metadata
     */
    startClip() {
        // Generate unique clip ID
        const clipId = this._generateClipId();
        const clipOrder = this.nextClipOrder++;

        // Create clip metadata
        const clip = {
            clipId: clipId,
            clipOrder: clipOrder,
            consultationId: this.consultationId,
            status: 'recording',
            startTime: Date.now(),
            endTime: null,
            chunks: [],
            transcriptionStatus: 'pending',
            transcriptionText: '',
            error: null
        };

        // Store clip
        this.clips.set(clipId, clip);
        this.currentClipId = clipId;

        console.log(`Recording clip started: clipId=${clipId}, clipOrder=${clipOrder}`);

        // Emit event
        this._emitEvent('clipStarted', clip);

        return clip;
    }

    /**
     * Complete the current recording clip
     * 
     * @returns {Object|null} Completed clip metadata or null if no active clip
     */
    completeClip() {
        if (!this.currentClipId) {
            console.warn('No active clip to complete');
            return null;
        }

        const clip = this.clips.get(this.currentClipId);
        if (!clip) {
            console.error(`Clip not found: ${this.currentClipId}`);
            return null;
        }

        // Update clip metadata
        clip.status = 'completed';
        clip.endTime = Date.now();
        clip.duration = clip.endTime - clip.startTime;

        console.log(`Recording clip completed: clipId=${clip.clipId}, duration=${clip.duration}ms`);

        // Emit event
        this._emitEvent('clipCompleted', clip);

        // Clear current clip
        this.currentClipId = null;

        return clip;
    }

    /**
     * Add chunk to current clip
     * 
     * @param {Object} chunkMetadata - Chunk metadata
     */
    addChunkToCurrentClip(chunkMetadata) {
        if (!this.currentClipId) {
            console.warn('No active clip to add chunk to');
            return;
        }

        const clip = this.clips.get(this.currentClipId);
        if (!clip) {
            console.error(`Clip not found: ${this.currentClipId}`);
            return;
        }

        clip.chunks.push(chunkMetadata);
        console.log(`Chunk added to clip: clipId=${clip.clipId}, chunks=${clip.chunks.length}`);
    }

    /**
     * Update clip transcription status
     * 
     * @param {string} clipId - Clip ID
     * @param {string} status - Status ('queued', 'transcribing', 'completed', 'failed')
     * @param {string} text - Transcription text (optional)
     * @param {string} error - Error message (optional)
     */
    updateClipTranscriptionStatus(clipId, status, text = null, error = null) {
        const clip = this.clips.get(clipId);
        if (!clip) {
            console.error(`Clip not found: ${clipId}`);
            return;
        }

        clip.transcriptionStatus = status;
        
        if (text) {
            clip.transcriptionText = text;
        }
        
        if (error) {
            clip.error = error;
        }

        console.log(`Clip transcription status updated: clipId=${clipId}, status=${status}`);

        // Emit event
        this._emitEvent('statusChanged', {
            clipId: clipId,
            status: status,
            text: text,
            error: error
        });
    }

    /**
     * Get clip by ID
     * 
     * @param {string} clipId - Clip ID
     * @returns {Object|null} Clip metadata or null if not found
     */
    getClip(clipId) {
        return this.clips.get(clipId) || null;
    }

    /**
     * Get current active clip
     * 
     * @returns {Object|null} Current clip metadata or null if no active clip
     */
    getCurrentClip() {
        if (!this.currentClipId) {
            return null;
        }
        return this.clips.get(this.currentClipId) || null;
    }

    /**
     * Get all clips ordered by clip order
     * 
     * @returns {Array} Array of clip metadata ordered by clipOrder
     */
    getClipsOrdered() {
        return Array.from(this.clips.values())
            .sort((a, b) => a.clipOrder - b.clipOrder);
    }

    /**
     * Check if currently recording
     * 
     * @returns {boolean} True if recording
     */
    isRecording() {
        return this.currentClipId !== null;
    }

    /**
     * Check if can start new recording
     * 
     * Requirements: 1.1, 1.2 - Allow starting new recording while previous clips are transcribing
     * 
     * @returns {boolean} True if can start new recording
     */
    canStartNewRecording() {
        // Can start new recording if not currently recording
        return !this.isRecording();
    }

    /**
     * Get session statistics
     * 
     * @returns {Object} Statistics
     */
    getStatistics() {
        const clips = Array.from(this.clips.values());
        
        return {
            consultationId: this.consultationId,
            totalClips: clips.length,
            recordingClips: clips.filter(c => c.status === 'recording').length,
            completedClips: clips.filter(c => c.status === 'completed').length,
            transcribingClips: clips.filter(c => c.transcriptionStatus === 'transcribing').length,
            transcribedClips: clips.filter(c => c.transcriptionStatus === 'completed').length,
            failedClips: clips.filter(c => c.transcriptionStatus === 'failed').length,
            nextClipOrder: this.nextClipOrder
        };
    }

    /**
     * Get full transcription text (all clips in order)
     * 
     * @returns {string} Combined transcription text
     */
    getFullTranscription() {
        return this.getClipsOrdered()
            .map(clip => clip.transcriptionText)
            .filter(text => text && text.length > 0)
            .join(' ');
    }

    /**
     * Clear all clips (for testing or reset)
     */
    clear() {
        this.clips.clear();
        this.currentClipId = null;
        this.nextClipOrder = 1;
        console.log('Recording session cleared');
    }

    /**
     * Generate unique clip ID
     * 
     * @returns {string} Clip ID
     */
    _generateClipId() {
        const timestamp = Date.now();
        const random = Math.floor(Math.random() * 10000);
        return `clip_${this.consultationId}_${timestamp}_${random}`;
    }

    /**
     * Register event handler
     * 
     * @param {string} event - Event name ('clipStarted', 'clipCompleted', 'statusChanged')
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
    module.exports = RecordingSessionManager;
}
