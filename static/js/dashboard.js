// Dashboard JavaScript functionality

// Utility function to format numbers with comma separators
function formatNumber(number) {
    if (typeof number === 'string') {
        number = parseFloat(number);
    }
    return number.toLocaleString('en-US');
}

// Utility function to format currency with comma separators
function formatCurrency(amount) {
    if (typeof amount === 'string') {
        amount = parseFloat(amount);
    }
    const symbol = window.currencySymbol || '$';
    return symbol + amount.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2});
}

// Theme Management
class ThemeManager {
    constructor() {
        this.currentTheme = localStorage.getItem('theme') || 'light';
        this.init();
    }

    init() {
        this.applyTheme(this.currentTheme);
        this.setupEventListeners();
        this.updateActiveThemeButton();
    }

    applyTheme(theme) {
        document.body.setAttribute('data-theme', theme);
        localStorage.setItem('theme', theme);
        this.currentTheme = theme;
    }

    setupEventListeners() {
        document.addEventListener('click', (e) => {
            if (e.target.classList.contains('theme-option')) {
                e.preventDefault();
                const theme = e.target.getAttribute('data-theme');
                this.applyTheme(theme);
                this.updateActiveThemeButton();
            }
        });
    }

    updateActiveThemeButton() {
        document.querySelectorAll('.theme-option').forEach(btn => {
            btn.classList.remove('active');
            if (btn.getAttribute('data-theme') === this.currentTheme) {
                btn.classList.add('active');
            }
        });
    }
}

document.addEventListener('DOMContentLoaded', function() {
    // Initialize theme system
    new ThemeManager();
    
    // Initialize tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Auto-dismiss alerts after 5 seconds
    const alerts = document.querySelectorAll('.alert:not(.alert-permanent)');
    alerts.forEach(alert => {
        setTimeout(() => {
            if (alert.parentNode) {
                const bsAlert = new bootstrap.Alert(alert);
                bsAlert.close();
            }
        }, 5000);
    });

    // Sidebar toggle functionality for mobile
    const sidebarToggle = document.querySelector('[data-bs-toggle="offcanvas"]');
    if (sidebarToggle) {
        sidebarToggle.addEventListener('click', function() {
            const sidebar = document.getElementById('sidebar');
            if (sidebar) {
                const offcanvas = new bootstrap.Offcanvas(sidebar);
                offcanvas.toggle();
            }
        });
    }

    // Inline confirmation for delete actions
    const deleteButtons = document.querySelectorAll('form[action*="/delete"] button[type="submit"]');
    deleteButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            e.preventDefault();
            showInlineConfirmation(
                'Are you sure you want to delete this item? This action cannot be undone.',
                () => {
                    // User confirmed - submit the form
                    button.closest('form').submit();
                }
            );
        });
    });

    // Auto-refresh dashboard statistics every 30 seconds
    if (window.location.pathname === '/') {
        setInterval(refreshDashboardStats, 30000);
    }

    // Initialize any charts on the page
    initializeCharts();
});

function refreshDashboardStats() {
    // Only refresh if user is still on dashboard
    if (document.hidden || window.location.pathname !== '/') {
        return;
    }

    fetch('/api/dashboard/stats')
        .then(response => response.json())
        .then(data => {
            // Update statistics cards
            updateStatCard('total-products', data.total_products);
            updateStatCard('total-customers', data.total_customers);
            updateStatCard('total-sales', data.total_sales);
            updateStatCard('low-stock-count', data.low_stock_count);
        })
        .catch(error => {
            console.log('Stats refresh failed:', error);
        });
}

// Show inline confirmation dialog
function showInlineConfirmation(message, onConfirm, onCancel = null) {
    // Remove any existing confirmation
    const existingConfirmation = document.querySelector('.inline-confirmation');
    if (existingConfirmation) {
        existingConfirmation.remove();
    }
    
    // Create confirmation element
    const confirmation = document.createElement('div');
    confirmation.className = 'inline-confirmation alert alert-warning position-fixed top-50 start-50 translate-middle';
    confirmation.style.cssText = 'z-index: 9999; min-width: 300px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);';
    
    confirmation.innerHTML = `
        <div class="d-flex align-items-center mb-3">
            <i class="fas fa-exclamation-triangle me-2"></i>
            <span>${message}</span>
        </div>
        <div class="d-flex gap-2 justify-content-end">
            <button class="btn btn-sm btn-secondary cancel-btn">Cancel</button>
            <button class="btn btn-sm btn-danger confirm-btn">Delete</button>
        </div>
    `;
    
    document.body.appendChild(confirmation);
    
    // Handle confirm button
    confirmation.querySelector('.confirm-btn').addEventListener('click', () => {
        confirmation.remove();
        if (onConfirm) onConfirm();
    });
    
    // Handle cancel button
    confirmation.querySelector('.cancel-btn').addEventListener('click', () => {
        confirmation.remove();
        if (onCancel) onCancel();
    });
    
    // Close on escape key
    const escapeHandler = (e) => {
        if (e.key === 'Escape') {
            confirmation.remove();
            document.removeEventListener('keydown', escapeHandler);
            if (onCancel) onCancel();
        }
    };
    document.addEventListener('keydown', escapeHandler);
}

// Show inline prompt dialog
function showInlinePrompt(message, onSubmit, onCancel = null) {
    // Remove any existing prompt
    const existingPrompt = document.querySelector('.inline-prompt');
    if (existingPrompt) {
        existingPrompt.remove();
    }
    
    // Create prompt element
    const prompt = document.createElement('div');
    prompt.className = 'inline-prompt alert alert-info position-fixed top-50 start-50 translate-middle';
    prompt.style.cssText = 'z-index: 9999; min-width: 350px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);';
    
    prompt.innerHTML = `
        <div class="mb-3">
            <label class="form-label">${message}</label>
            <input type="text" class="form-control prompt-input" required>
        </div>
        <div class="d-flex gap-2 justify-content-end">
            <button class="btn btn-sm btn-secondary cancel-btn">Cancel</button>
            <button class="btn btn-sm btn-primary submit-btn">Submit</button>
        </div>
    `;
    
    document.body.appendChild(prompt);
    
    const input = prompt.querySelector('.prompt-input');
    input.focus();
    
    // Handle submit button
    const submitBtn = prompt.querySelector('.submit-btn');
    const handleSubmit = () => {
        const value = input.value.trim();
        if (value) {
            prompt.remove();
            if (onSubmit) onSubmit(value);
        }
    };
    
    submitBtn.addEventListener('click', handleSubmit);
    input.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            handleSubmit();
        }
    });
    
    // Handle cancel button
    prompt.querySelector('.cancel-btn').addEventListener('click', () => {
        prompt.remove();
        if (onCancel) onCancel();
    });
}

function updateStatCard(elementId, value) {
    const element = document.getElementById(elementId);
    if (element) {
        element.textContent = value;
    }
}

function initializeCharts() {
    // Initialize Chart.js charts if Chart is available
    if (typeof Chart !== 'undefined') {
        const chartElements = document.querySelectorAll('canvas[id*="Chart"]');
        chartElements.forEach(canvas => {
            if (canvas.id === 'salesChart') {
                initializeSalesChart(canvas);
            }
        });
    }
}

function initializeSalesChart(canvas) {
    // This function is implemented in the specific pages that need it
    // Left empty here as a placeholder
}

// Utility functions
function formatCurrency(amount, currency = 'USD') {
    return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: currency
    }).format(amount);
}

function formatDate(date) {
    return new Intl.DateTimeFormat('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric'
    }).format(new Date(date));
}

function showToast(message, type = 'info') {
    // Create toast element if toast container exists
    const toastContainer = document.querySelector('.toast-container');
    if (!toastContainer) return;

    const toastId = 'toast-' + Date.now();
    const toastHtml = `
        <div id="${toastId}" class="toast" role="alert" aria-live="assertive" aria-atomic="true">
            <div class="toast-header">
                <i class="fas fa-info-circle me-2 text-${type}"></i>
                <strong class="me-auto">Cloud POS</strong>
                <button type="button" class="btn-close" data-bs-dismiss="toast" aria-label="Close"></button>
            </div>
            <div class="toast-body">
                ${message}
            </div>
        </div>
    `;

    toastContainer.insertAdjacentHTML('beforeend', toastHtml);
    const toastElement = document.getElementById(toastId);
    const toast = new bootstrap.Toast(toastElement);
    toast.show();

    // Remove element after it's hidden
    toastElement.addEventListener('hidden.bs.toast', () => {
        toastElement.remove();
    });
}

// Export functions for use in other scripts
window.CloudPOS = {
    formatCurrency,
    formatDate,
    showToast,
    refreshDashboardStats
};
