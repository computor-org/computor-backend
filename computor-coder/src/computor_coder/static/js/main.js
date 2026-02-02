/**
 * Computor Coder Web Interface - Main JavaScript
 */

// API Base URL - relative to current path
const API_BASE = window.CODER_API_BASE || '/coder';

/**
 * Show notification message
 */
function showNotification(message, type = 'success') {
    const notification = document.getElementById('notification');
    if (!notification) return;

    notification.textContent = message;
    notification.className = `notification ${type}`;

    // Auto-hide after 5 seconds
    setTimeout(() => {
        notification.classList.add('hidden');
    }, 5000);
}

/**
 * Fetch health status
 */
async function fetchHealth() {
    try {
        const response = await fetch(API_BASE + '/health');
        if (!response.ok) {
            throw new Error('Health check failed');
        }
        return await response.json();
    } catch (error) {
        console.error('Health check error:', error);
        return { healthy: false, version: null };
    }
}

/**
 * Update health status indicator
 */
async function updateHealthStatus() {
    const statusEl = document.getElementById('health-status');
    if (!statusEl) return;

    try {
        const data = await fetchHealth();
        if (data.healthy) {
            statusEl.textContent = 'Connected';
            statusEl.className = 'status-indicator healthy';
        } else {
            statusEl.textContent = 'Disconnected';
            statusEl.className = 'status-indicator unhealthy';
        }
    } catch (error) {
        statusEl.textContent = 'Error';
        statusEl.className = 'status-indicator unhealthy';
    }
}

/**
 * Format date string
 */
function formatDate(dateStr) {
    if (!dateStr) return 'Never';
    try {
        const date = new Date(dateStr);
        return date.toLocaleDateString() + ' ' + date.toLocaleTimeString();
    } catch {
        return 'Invalid date';
    }
}

/**
 * Get status CSS class
 */
function getStatusClass(status) {
    switch (status?.toLowerCase()) {
        case 'running':
            return 'running';
        case 'stopped':
            return 'stopped';
        case 'starting':
        case 'stopping':
        case 'pending':
            return 'pending';
        case 'failed':
        case 'error':
            return 'failed';
        default:
            return 'unknown';
    }
}

/**
 * Make authenticated API request
 */
async function apiRequest(endpoint, options = {}) {
    const url = API_BASE + endpoint;
    const defaultOptions = {
        credentials: 'include',  // Send cookies for session auth
        headers: {
            'Content-Type': 'application/json',
        },
    };

    const response = await fetch(url, { ...defaultOptions, ...options });

    if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: 'Request failed' }));
        throw new Error(error.detail || error.message || 'Request failed');
    }

    return response.json();
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    // Update health status
    updateHealthStatus();

    // Refresh health status every 30 seconds
    setInterval(updateHealthStatus, 30000);
});
