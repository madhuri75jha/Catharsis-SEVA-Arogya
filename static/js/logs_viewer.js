/**
 * CloudWatch Logs Viewer JavaScript
 * Handles log fetching, filtering, search, and auto-refresh
 */

class LogsViewerManager {
    constructor() {
        this.logs = [];
        this.nextToken = null;
        this.hasMore = false;
        this.autoRefreshInterval = null;
        this.searchQuery = '';
        this.timeRangeHours = 24;
        
        this.init();
    }
    
    init() {
        this.setupEventListeners();
        this.fetchLogs();
    }
    
    setupEventListeners() {
        // Search input
        const searchInput = document.getElementById('search-input');
        if (searchInput) {
            let searchTimeout;
            searchInput.addEventListener('input', (e) => {
                clearTimeout(searchTimeout);
                searchTimeout = setTimeout(() => {
                    this.searchQuery = e.target.value;
                    this.fetchLogs(true);
                }, 500);
            });
        }
        
        // Time range filter
        const timeRangeFilter = document.getElementById('time-range-filter');
        if (timeRangeFilter) {
            timeRangeFilter.addEventListener('change', (e) => {
                this.timeRangeHours = parseInt(e.target.value);
                this.fetchLogs(true);
            });
        }
        
        // Auto-refresh toggle
        const autoRefreshToggle = document.getElementById('auto-refresh-toggle');
        if (autoRefreshToggle) {
            autoRefreshToggle.addEventListener('change', (e) => {
                if (e.target.checked) {
                    this.startAutoRefresh();
                } else {
                    this.stopAutoRefresh();
                }
            });
        }
        
        // Refresh button
        const refreshBtn = document.getElementById('refresh-btn');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', () => {
                this.fetchLogs(true);
            });
        }
        
        // Load more button
        const loadMoreBtn = document.getElementById('load-more-btn');
        if (loadMoreBtn) {
            loadMoreBtn.addEventListener('click', () => {
                this.fetchLogs(false);
            });
        }
    }
    
    async fetchLogs(reset = true) {
        try {
            if (reset) {
                this.showLoading();
                this.logs = [];
                this.nextToken = null;
            }
            
            // Calculate time range
            const endTime = new Date();
            const startTime = new Date(endTime.getTime() - this.timeRangeHours * 60 * 60 * 1000);
            
            // Build query parameters
            const params = new URLSearchParams();
            params.append('start_time', startTime.toISOString());
            params.append('end_time', endTime.toISOString());
            params.append('limit', '100');
            
            if (this.searchQuery) {
                params.append('search', this.searchQuery);
            }
            
            if (this.nextToken) {
                params.append('next_token', this.nextToken);
            }
            
            const response = await fetch(`/api/v1/logs?${params.toString()}`);
            
            if (!response.ok) {
                if (response.status === 403) {
                    this.showError('You do not have permission to view logs');
                } else if (response.status === 503) {
                    this.showError('CloudWatch service not configured');
                } else {
                    this.showError(`HTTP error! status: ${response.status}`);
                }
                return;
            }
            
            const data = await response.json();
            
            if (data.success) {
                const newLogs = data.logs || [];
                this.logs = reset ? newLogs : [...this.logs, ...newLogs];
                this.nextToken = data.next_token;
                this.hasMore = data.has_more || false;
                
                this.renderLogs();
            } else {
                this.showError(data.message || 'Failed to load logs');
            }
        } catch (error) {
            console.error('Error fetching logs:', error);
            this.showError('An error occurred while loading logs');
        }
    }
    
    renderLogs() {
        const container = document.getElementById('logs-container');
        const loadingState = document.getElementById('loading-state');
        const emptyState = document.getElementById('empty-state');
        const logsContent = document.getElementById('logs-content');
        const loadMoreContainer = document.getElementById('load-more-container');
        
        // Hide loading
        if (loadingState) loadingState.classList.add('hidden');
        
        if (this.logs.length === 0) {
            // Show empty state
            if (logsContent) logsContent.classList.add('hidden');
            if (emptyState) emptyState.classList.remove('hidden');
            return;
        }
        
        // Show logs
        if (emptyState) emptyState.classList.add('hidden');
        if (logsContent) logsContent.classList.remove('hidden');
        
        // Render log entries
        if (container) {
            container.innerHTML = '';
            
            this.logs.forEach(log => {
                const logEntry = this.createLogEntry(log);
                container.appendChild(logEntry);
            });
        }
        
        // Show/hide load more button
        if (loadMoreContainer) {
            if (this.hasMore && this.nextToken) {
                loadMoreContainer.classList.remove('hidden');
            } else {
                loadMoreContainer.classList.add('hidden');
            }
        }
    }
    
    createLogEntry(log) {
        const entry = document.createElement('div');
        entry.className = 'log-entry';
        
        // Detect log level from message
        const message = log.message || '';
        if (message.toLowerCase().includes('error')) {
            entry.classList.add('log-level-error');
        } else if (message.toLowerCase().includes('warning') || message.toLowerCase().includes('warn')) {
            entry.classList.add('log-level-warning');
        } else if (message.toLowerCase().includes('info')) {
            entry.classList.add('log-level-info');
        }
        
        // Timestamp
        const timestamp = document.createElement('div');
        timestamp.className = 'log-timestamp';
        timestamp.textContent = this.formatTimestamp(log.timestamp);
        entry.appendChild(timestamp);
        
        // Message
        const messageEl = document.createElement('div');
        messageEl.className = 'log-message';
        messageEl.textContent = message;
        entry.appendChild(messageEl);
        
        return entry;
    }
    
    startAutoRefresh() {
        this.stopAutoRefresh();
        this.autoRefreshInterval = setInterval(() => {
            this.fetchLogs(true);
        }, 30000); // Refresh every 30 seconds
    }
    
    stopAutoRefresh() {
        if (this.autoRefreshInterval) {
            clearInterval(this.autoRefreshInterval);
            this.autoRefreshInterval = null;
        }
    }
    
    showLoading() {
        document.getElementById('loading-state')?.classList.remove('hidden');
        document.getElementById('error-state')?.classList.add('hidden');
        document.getElementById('empty-state')?.classList.add('hidden');
        document.getElementById('logs-content')?.classList.add('hidden');
    }
    
    showError(message) {
        document.getElementById('loading-state')?.classList.add('hidden');
        document.getElementById('logs-content')?.classList.add('hidden');
        document.getElementById('empty-state')?.classList.add('hidden');
        
        const errorState = document.getElementById('error-state');
        const errorMessage = document.getElementById('error-message');
        
        if (errorState) errorState.classList.remove('hidden');
        if (errorMessage) errorMessage.textContent = message;
    }
    
    formatTimestamp(timestamp) {
        if (!timestamp) return 'N/A';
        const date = new Date(timestamp);
        return date.toLocaleString('en-US', {
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit'
        });
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    new LogsViewerManager();
});
