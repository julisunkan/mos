// Dashboard JavaScript functionality
document.addEventListener('DOMContentLoaded', function() {
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

    // Confirmation dialogs for delete actions
    const deleteButtons = document.querySelectorAll('form[action*="/delete"] button[type="submit"]');
    deleteButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            if (!confirm('Are you sure you want to delete this item? This action cannot be undone.')) {
                e.preventDefault();
                return false;
            }
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
function formatCurrency(amount) {
    return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD'
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
