/**
 * WebSocket Manager with Reconnection Handling
 * 
 * Manages WebSocket connection with automatic reconnection,
 * exponential backoff, and state synchronization.
 * 
 * Requirements: 5.5, 5.6
 */

class WebSocketManager {
    constructor(socketIOInstance) {
        this.socket = socketIOInstance;
        this.isConnected = false;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 10;
        this.reconnectDelay = 1000; // Start with 1 second
        this.maxReconnectDelay = 30000; // Max 30 seconds
        this.reconnectTimer = null;
        this.pendingStateSync = false;
        
        this.eventHandlers = {
            connected: [],
            disconnected: [],
            reconnecting: [],
            reconnected: [],
            error: []
        };
        
        this._setupSocketListeners();
    }
    
    /**
     * Setup Socket.IO event listeners
     */
    _setupSocketListeners() {
        // Connection established
        this.socket.on('connect', () => {
            console.log('WebSocket connected');
            this.isConnected = true;
            
            // Check if this is a reconnection
            if (this.reconnectAttempts > 0) {
                console.log(`WebSocket reconnected after ${this.reconnectAttempts} attempts`);
                this._emitEvent('reconnected', {
                    attempts: this.reconnectAttempts
                });
                
                // Trigger state synchronization
                this._synchronizeState();
            } else {
                this._emitEvent('connected', {});
            }
            
            // Reset reconnection state
            this.reconnectAttempts = 0;
            this.reconnectDelay = 1000;
            if (this.reconnectTimer) {
                clearTimeout(this.reconnectTimer);
                this.reconnectTimer = null;
            }
        });
        
        // Connection lost
        this.socket.on('disconnect', (reason) => {
            console.log(`WebSocket disconnected: ${reason}`);
            this.isConnected = false;
            
            this._emitEvent('disconnected', {
                reason: reason
            });
            
            // Attempt reconnection if not intentional disconnect
            if (reason !== 'io client disconnect') {
                this._scheduleReconnect();
            }
        });
        
        // Connection error
        this.socket.on('connect_error', (error) => {
            console.error('WebSocket connection error:', error);
            
            this._emitEvent('error', {
                type: 'connection_error',
                message: error.message || 'Connection error',
                error: error
            });
            
            // Schedule reconnection
            this._scheduleReconnect();
        });
        
        // Reconnection attempt
        this.socket.io.on('reconnect_attempt', () => {
            this.reconnectAttempts++;
            console.log(`WebSocket reconnection attempt ${this.reconnectAttempts}/${this.maxReconnectAttempts}`);
            
            this._emitEvent('reconnecting', {
                attempt: this.reconnectAttempts,
                maxAttempts: this.maxReconnectAttempts
            });
        });
    }
    
    /**
     * Schedule reconnection with exponential backoff
     */
    _scheduleReconnect() {
        if (this.reconnectTimer) {
            return; // Already scheduled
        }
        
        if (this.reconnectAttempts >= this.maxReconnectAttempts) {
            console.error('Max reconnection attempts reached');
            this._emitEvent('error', {
                type: 'max_reconnect_attempts',
                message: 'Failed to reconnect after maximum attempts',
                attempts: this.reconnectAttempts
            });
            return;
        }
        
        // Calculate exponential backoff: 2^attempt * base delay
        const delay = Math.min(
            this.reconnectDelay * Math.pow(2, this.reconnectAttempts),
            this.maxReconnectDelay
        );
        
        console.log(`Scheduling reconnection in ${delay}ms`);
        
        this.reconnectTimer = setTimeout(() => {
            this.reconnectTimer = null;
            
            if (!this.isConnected) {
                console.log('Attempting manual reconnection...');
                this.socket.connect();
            }
        }, delay);
    }
    
    /**
     * Synchronize state after reconnection
     */
    _synchronizeState() {
        if (this.pendingStateSync) {
            return; // Already syncing
        }
        
        this.pendingStateSync = true;
        
        console.log('Synchronizing state after reconnection...');
        
        // Emit state sync request
        this.socket.emit('sync_state', {
            timestamp: Date.now()
        });
        
        // Listen for sync response
        const syncTimeout = setTimeout(() => {
            console.warn('State sync timeout');
            this.pendingStateSync = false;
        }, 5000);
        
        this.socket.once('state_synced', (data) => {
            clearTimeout(syncTimeout);
            this.pendingStateSync = false;
            console.log('State synchronized:', data);
        });
    }
    
    /**
     * Manually trigger reconnection
     */
    reconnect() {
        console.log('Manual reconnection triggered');
        this.reconnectAttempts = 0;
        this.socket.disconnect();
        this.socket.connect();
    }
    
    /**
     * Disconnect WebSocket
     */
    disconnect() {
        console.log('Disconnecting WebSocket');
        if (this.reconnectTimer) {
            clearTimeout(this.reconnectTimer);
            this.reconnectTimer = null;
        }
        this.socket.disconnect();
    }
    
    /**
     * Register event handler
     * 
     * @param {string} event - Event name
     * @param {Function} callback - Callback function
     * @returns {Function} Unsubscribe function
     */
    on(event, callback) {
        // Check if this is a Socket.IO event or manager event
        if (this.eventHandlers[event]) {
            // Manager event
            this.eventHandlers[event].push(callback);
            
            return () => this.off(event, callback);
        } else {
            // Socket.IO event - delegate to socket
            this.socket.on(event, callback);
            
            return () => this.socket.off(event, callback);
        }
    }
    
    /**
     * Unregister event handler
     * 
     * @param {string} event - Event name
     * @param {Function} callback - Callback function
     */
    off(event, callback) {
        if (this.eventHandlers[event]) {
            this.eventHandlers[event] = this.eventHandlers[event]
                .filter(handler => handler !== callback);
        } else {
            this.socket.off(event, callback);
        }
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
     * Get connection status
     * 
     * @returns {Object} Status information
     */
    getStatus() {
        return {
            isConnected: this.isConnected,
            reconnectAttempts: this.reconnectAttempts,
            maxReconnectAttempts: this.maxReconnectAttempts,
            pendingStateSync: this.pendingStateSync
        };
    }
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = WebSocketManager;
}
