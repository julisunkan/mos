// Enhanced POS System JavaScript
class EnhancedPOS {
    constructor() {
        this.cart = [];
        this.products = [];
        this.customers = [];
        this.currentCustomer = null;
        this.discount = { type: 'none', value: 0, amount: 0 };
        this.paymentMethod = 'cash';
        this.splitPayments = [];
        this.isLoading = false;
        
        this.init();
    }
    
    init() {
        this.loadProducts();
        this.updateCartDisplay();
        this.updateSummary();
        
        // Initialize search debounce
        this.searchTimeout = null;
        
        // Set up event listeners
        document.getElementById('productSearch').addEventListener('input', (e) => {
            clearTimeout(this.searchTimeout);
            this.searchTimeout = setTimeout(() => {
                this.searchProducts(e.target.value);
            }, 300);
        });
        
        // Initialize payment method
        this.selectPaymentMethod('cash');
    }
    
    // Product Management
    async loadProducts() {
        this.showLoading('loadingProducts');
        try {
            const response = await fetch('/pos/api/products');
            const data = await response.json();
            
            if (response.ok) {
                this.products = data;
                this.displayProducts(this.products);
            } else {
                this.showError('Failed to load products: ' + data.error);
            }
        } catch (error) {
            this.showError('Network error: ' + error.message);
        } finally {
            this.hideLoading('loadingProducts');
        }
    }
    
    async searchProducts(searchTerm) {
        if (searchTerm.length < 2) {
            this.displayProducts(this.products);
            return;
        }
        
        try {
            const response = await fetch(`/pos/api/products/search?q=${encodeURIComponent(searchTerm)}`);
            const data = await response.json();
            
            if (response.ok) {
                this.displayProducts(data);
            } else {
                this.showError('Search failed: ' + data.error);
            }
        } catch (error) {
            this.showError('Search error: ' + error.message);
        }
    }
    
    displayProducts(products) {
        const grid = document.getElementById('productsGrid');
        
        if (products.length === 0) {
            grid.innerHTML = `
                <div class="col-12 text-center py-4">
                    <i class="fas fa-search fa-3x text-muted mb-3"></i>
                    <p class="text-muted">No products found</p>
                </div>
            `;
            return;
        }
        
        grid.innerHTML = products.map(product => `
            <div class="product-card ${product.stock <= 10 ? 'low-stock' : ''}" 
                 onclick="posSystem.addToCart(${product.id})">
                <div class="product-info">
                    <h4>${this.escapeHtml(product.name)}</h4>
                    <div class="product-price">$${this.formatCurrency(product.price)}</div>
                    <div class="product-stock">Stock: ${product.stock} units</div>
                    <div class="product-sku">SKU: ${product.sku}</div>
                    ${product.stock <= 10 ? '<div class="text-warning"><i class="fas fa-exclamation-triangle"></i> Low Stock</div>' : ''}
                </div>
            </div>
        `).join('');
    }
    
    // Cart Management
    addToCart(productId) {
        const product = this.products.find(p => p.id === productId);
        if (!product) {
            this.showError('Product not found');
            return;
        }
        
        if (product.stock <= 0) {
            this.showError('Product out of stock');
            return;
        }
        
        const existingItem = this.cart.find(item => item.product_id === productId);
        
        if (existingItem) {
            if (existingItem.quantity < product.stock) {
                existingItem.quantity++;
                existingItem.total = existingItem.quantity * existingItem.unit_price;
            } else {
                this.showError('Not enough stock available');
                return;
            }
        } else {
            this.cart.push({
                product_id: productId,
                name: product.name,
                sku: product.sku,
                unit_price: product.price,
                quantity: 1,
                total: product.price,
                tax_rate: product.tax_rate || 0
            });
        }
        
        this.updateCartDisplay();
        this.updateSummary();
        this.showSuccess('Product added to cart');
    }
    
    updateQuantity(productId, newQuantity) {
        const item = this.cart.find(item => item.product_id === productId);
        const product = this.products.find(p => p.id === productId);
        
        if (!item || !product) return;
        
        if (newQuantity <= 0) {
            this.removeFromCart(productId);
            return;
        }
        
        if (newQuantity > product.stock) {
            this.showError('Not enough stock available');
            return;
        }
        
        item.quantity = newQuantity;
        item.total = item.quantity * item.unit_price;
        
        this.updateCartDisplay();
        this.updateSummary();
    }
    
    removeFromCart(productId) {
        this.cart = this.cart.filter(item => item.product_id !== productId);
        this.updateCartDisplay();
        this.updateSummary();
    }
    
    clearCart() {
        if (this.cart.length === 0) return;
        
        if (confirm('Are you sure you want to clear the cart?')) {
            this.cart = [];
            this.discount = { type: 'none', value: 0, amount: 0 };
            this.currentCustomer = null;
            this.splitPayments = [];
            
            document.getElementById('customerSelect').value = '';
            document.getElementById('discountType').value = 'none';
            document.getElementById('discountValue').value = '';
            document.getElementById('promoCodeInput').value = '';
            
            this.updateCartDisplay();
            this.updateSummary();
            this.updateDiscountType();
        }
    }
    
    updateCartDisplay() {
        const cartItems = document.getElementById('cartItems');
        
        if (this.cart.length === 0) {
            cartItems.innerHTML = `
                <div class="empty-cart">
                    <i class="fas fa-shopping-cart"></i>
                    <p>Your cart is empty<br>Add products to get started</p>
                </div>
            `;
            document.getElementById('checkoutBtn').disabled = true;
            return;
        }
        
        cartItems.innerHTML = this.cart.map(item => `
            <div class="cart-item">
                <div class="item-info">
                    <div class="item-name">${this.escapeHtml(item.name)}</div>
                    <div class="item-price">$${this.formatCurrency(item.unit_price)} each</div>
                </div>
                <div class="quantity-controls">
                    <button class="qty-btn" onclick="posSystem.updateQuantity(${item.product_id}, ${item.quantity - 1})">-</button>
                    <span class="qty-display">${item.quantity}</span>
                    <button class="qty-btn" onclick="posSystem.updateQuantity(${item.product_id}, ${item.quantity + 1})">+</button>
                </div>
                <button class="remove-btn" onclick="posSystem.removeFromCart(${item.product_id})">
                    <i class="fas fa-times"></i>
                </button>
            </div>
        `).join('');
        
        document.getElementById('checkoutBtn').disabled = false;
    }
    
    // Customer Management
    updateCustomer() {
        const select = document.getElementById('customerSelect');
        const selectedOption = select.options[select.selectedIndex];
        
        if (select.value) {
            this.currentCustomer = {
                id: parseInt(select.value),
                name: selectedOption.text,
                type: selectedOption.dataset.type,
                loyalty_points: parseInt(selectedOption.dataset.loyalty || 0)
            };
        } else {
            this.currentCustomer = null;
        }
        
        this.updateSummary();
    }
    
    // Discount & Promotion Management
    updateDiscountType() {
        const discountType = document.getElementById('discountType').value;
        const discountValue = document.getElementById('discountValue');
        const promoCodeInput = document.getElementById('promoCodeInput');
        
        discountValue.style.display = discountType === 'none' || discountType === 'promo_code' ? 'none' : 'inline-block';
        promoCodeInput.style.display = discountType === 'promo_code' ? 'block' : 'none';
        
        if (discountType === 'none') {
            this.discount = { type: 'none', value: 0, amount: 0 };
            discountValue.value = '';
            promoCodeInput.value = '';
        }
        
        this.updateSummary();
    }
    
    calculateDiscount() {
        const discountType = document.getElementById('discountType').value;
        const discountValue = parseFloat(document.getElementById('discountValue').value) || 0;
        
        if (discountType === 'none' || discountValue <= 0) {
            this.discount = { type: 'none', value: 0, amount: 0 };
            this.updateSummary();
            return;
        }
        
        const subtotal = this.calculateSubtotal();
        let discountAmount = 0;
        
        if (discountType === 'percentage') {
            if (discountValue > 100) {
                this.showError('Discount percentage cannot exceed 100%');
                document.getElementById('discountValue').value = '';
                return;
            }
            discountAmount = (subtotal * discountValue) / 100;
        } else if (discountType === 'fixed') {
            if (discountValue > subtotal) {
                this.showError('Discount amount cannot exceed subtotal');
                document.getElementById('discountValue').value = '';
                return;
            }
            discountAmount = discountValue;
        }
        
        this.discount = {
            type: discountType,
            value: discountValue,
            amount: discountAmount
        };
        
        this.updateSummary();
    }
    
    async applyPromoCode() {
        const promoCode = document.getElementById('promoCodeInput').value.trim();
        
        if (!promoCode) {
            this.discount = { type: 'none', value: 0, amount: 0 };
            this.updateSummary();
            return;
        }
        
        try {
            const response = await fetch('/pos/api/promo-code/validate', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                body: JSON.stringify({
                    code: promoCode,
                    subtotal: this.calculateSubtotal()
                })
            });
            
            const data = await response.json();
            
            if (response.ok) {
                this.discount = {
                    type: 'promo_code',
                    value: data.discount_value,
                    amount: data.discount_amount,
                    code: promoCode
                };
                this.showSuccess('Promo code applied successfully!');
            } else {
                this.discount = { type: 'none', value: 0, amount: 0 };
                this.showError('Invalid promo code: ' + data.error);
            }
        } catch (error) {
            this.showError('Error validating promo code: ' + error.message);
        }
        
        this.updateSummary();
    }
    
    // Payment Management
    selectPaymentMethod(method) {
        this.paymentMethod = method;
        
        // Update UI
        document.querySelectorAll('.payment-method').forEach(btn => {
            btn.classList.remove('active');
        });
        document.querySelector(`[data-method="${method}"]`).classList.add('active');
        
        // Show/hide payment details
        document.querySelectorAll('.payment-details').forEach(div => {
            div.classList.remove('active');
        });
        document.getElementById(`${method}Payment`).classList.add('active');
        
        // Reset split payments if not split method
        if (method !== 'split') {
            this.splitPayments = [];
        }
        
        this.updateSummary();
    }
    
    calculateChange() {
        const total = this.calculateTotal();
        const tendered = parseFloat(document.getElementById('amountTendered').value) || 0;
        const changeAmount = tendered - total;
        
        const changeDiv = document.getElementById('changeAmount');
        
        if (tendered >= total && tendered > 0) {
            changeDiv.style.display = 'block';
            changeDiv.textContent = `Change: $${this.formatCurrency(changeAmount)}`;
            changeDiv.className = 'change-amount';
        } else if (tendered > 0) {
            changeDiv.style.display = 'block';
            changeDiv.textContent = `Insufficient: Need $${this.formatCurrency(total - tendered)} more`;
            changeDiv.className = 'change-amount text-danger';
        } else {
            changeDiv.style.display = 'none';
        }
    }
    
    manageSplitPayment() {
        // Implementation for split payment management
        // This would open a modal or expand interface for adding multiple payment methods
        this.showInfo('Split payment feature - would open detailed payment management interface');
    }
    
    // Calculations
    calculateSubtotal() {
        return this.cart.reduce((sum, item) => sum + item.total, 0);
    }
    
    calculateTax() {
        return this.cart.reduce((sum, item) => {
            const taxAmount = (item.total * (item.tax_rate || 0)) / 100;
            return sum + taxAmount;
        }, 0);
    }
    
    calculateTotal() {
        const subtotal = this.calculateSubtotal();
        const tax = this.calculateTax();
        const discount = this.discount.amount || 0;
        return Math.max(0, subtotal + tax - discount);
    }
    
    updateSummary() {
        const subtotal = this.calculateSubtotal();
        const tax = this.calculateTax();
        const discount = this.discount.amount || 0;
        const total = this.calculateTotal();
        
        document.getElementById('subtotal').textContent = `$${this.formatCurrency(subtotal)}`;
        document.getElementById('discountAmount').textContent = `-$${this.formatCurrency(discount)}`;
        document.getElementById('taxAmount').textContent = `$${this.formatCurrency(tax)}`;
        document.getElementById('totalAmount').textContent = `$${this.formatCurrency(total)}`;
        
        // Update change calculation if cash payment
        if (this.paymentMethod === 'cash') {
            this.calculateChange();
        }
    }
    
    // Checkout Process
    async processCheckout() {
        if (this.cart.length === 0) {
            this.showError('Cart is empty');
            return;
        }
        
        if (this.isLoading) return;
        
        // Validate payment details
        if (!this.validatePayment()) {
            return;
        }
        
        this.isLoading = true;
        document.getElementById('checkoutBtn').disabled = true;
        document.getElementById('checkoutBtn').innerHTML = '<div class="spinner"></div> Processing...';
        
        try {
            const saleData = {
                items: this.cart.map(item => ({
                    product_id: item.product_id,
                    quantity: item.quantity,
                    unit_price: item.unit_price
                })),
                customer_id: this.currentCustomer?.id || null,
                payment_method: this.paymentMethod,
                discount: this.discount,
                notes: ''
            };
            
            // Add payment-specific data
            if (this.paymentMethod === 'cash') {
                saleData.amount_tendered = parseFloat(document.getElementById('amountTendered').value) || 0;
            } else if (this.paymentMethod === 'card') {
                saleData.payment_reference = document.getElementById('cardReference').value;
            } else if (this.paymentMethod === 'digital') {
                saleData.payment_reference = document.getElementById('digitalReference').value;
            }
            
            const response = await fetch('/pos/api/sale/process', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                body: JSON.stringify(saleData)
            });
            
            const result = await response.json();
            
            if (response.ok) {
                this.showSuccess('Sale completed successfully!');
                this.showReceipt(result);
                this.clearCart();
                this.loadProducts(); // Refresh product stock
            } else {
                this.showError('Sale failed: ' + result.error);
            }
        } catch (error) {
            this.showError('Network error: ' + error.message);
        } finally {
            this.isLoading = false;
            document.getElementById('checkoutBtn').disabled = false;
            document.getElementById('checkoutBtn').innerHTML = '<i class="fas fa-cash-register"></i> Checkout';
        }
    }
    
    validatePayment() {
        const total = this.calculateTotal();
        
        if (this.paymentMethod === 'cash') {
            const tendered = parseFloat(document.getElementById('amountTendered').value) || 0;
            if (tendered < total) {
                this.showError('Insufficient amount tendered');
                return false;
            }
        } else if (this.paymentMethod === 'card') {
            const reference = document.getElementById('cardReference').value.trim();
            if (!reference) {
                this.showError('Card transaction reference is required');
                return false;
            }
        } else if (this.paymentMethod === 'digital') {
            const reference = document.getElementById('digitalReference').value.trim();
            if (!reference) {
                this.showError('Digital wallet reference is required');
                return false;
            }
        }
        
        return true;
    }
    
    // Receipt Management
    showReceipt(saleData) {
        const receiptContent = document.getElementById('receiptContent');
        const modal = new bootstrap.Modal(document.getElementById('receiptModal'));
        
        receiptContent.innerHTML = this.generateReceiptHTML(saleData);
        modal.show();
    }
    
    generateReceiptHTML(saleData) {
        const now = new Date();
        const subtotal = this.calculateSubtotal();
        const tax = this.calculateTax();
        const discount = this.discount.amount || 0;
        
        return `
            <div class="receipt-container" style="font-family: 'Courier New', monospace; padding: 20px; background: white; border: 1px solid #ddd;">
                <div class="text-center mb-4">
                    <h3>{{ store.name }}</h3>
                    <p>{{ store.address or 'Store Address' }}<br>
                    {{ store.phone or 'Store Phone' }}</p>
                    <hr>
                </div>
                
                <div class="receipt-details mb-3">
                    <div class="row">
                        <div class="col-6">Receipt #: ${saleData.receipt_number}</div>
                        <div class="col-6 text-end">Date: ${now.toLocaleString()}</div>
                    </div>
                    <div class="row">
                        <div class="col-6">Cashier: {{ current_user.full_name }}</div>
                        <div class="col-6 text-end">Customer: ${this.currentCustomer?.name || 'Walk-in'}</div>
                    </div>
                </div>
                
                <hr>
                <div class="receipt-items mb-3">
                    ${this.cart.map(item => `
                        <div class="d-flex justify-content-between">
                            <div>${item.name}</div>
                            <div>$${this.formatCurrency(item.total)}</div>
                        </div>
                        <div class="small text-muted">
                            ${item.quantity} x $${this.formatCurrency(item.unit_price)}
                        </div>
                    `).join('')}
                </div>
                
                <hr>
                <div class="receipt-summary">
                    <div class="d-flex justify-content-between">
                        <div>Subtotal:</div>
                        <div>$${this.formatCurrency(subtotal)}</div>
                    </div>
                    ${discount > 0 ? `
                        <div class="d-flex justify-content-between">
                            <div>Discount:</div>
                            <div>-$${this.formatCurrency(discount)}</div>
                        </div>
                    ` : ''}
                    <div class="d-flex justify-content-between">
                        <div>Tax:</div>
                        <div>$${this.formatCurrency(tax)}</div>
                    </div>
                    <hr>
                    <div class="d-flex justify-content-between fw-bold">
                        <div>Total:</div>
                        <div>$${this.formatCurrency(saleData.total_amount)}</div>
                    </div>
                    
                    <div class="mt-3">
                        <div class="d-flex justify-content-between">
                            <div>Payment Method:</div>
                            <div>${this.paymentMethod.toUpperCase()}</div>
                        </div>
                        ${this.paymentMethod === 'cash' ? `
                            <div class="d-flex justify-content-between">
                                <div>Amount Tendered:</div>
                                <div>$${this.formatCurrency(saleData.amount_tendered || 0)}</div>
                            </div>
                            <div class="d-flex justify-content-between">
                                <div>Change:</div>
                                <div>$${this.formatCurrency(saleData.change_amount || 0)}</div>
                            </div>
                        ` : ''}
                    </div>
                </div>
                
                <hr>
                <div class="text-center">
                    <p>Thank you for your business!</p>
                    <p class="small">Return Policy: 30 days with receipt</p>
                </div>
            </div>
        `;
    }
    
    printReceipt() {
        const receiptContent = document.getElementById('receiptContent').innerHTML;
        const printWindow = window.open('', '_blank');
        printWindow.document.write(`
            <html>
                <head>
                    <title>Receipt</title>
                    <style>
                        body { font-family: 'Courier New', monospace; margin: 0; padding: 20px; }
                        @media print { body { margin: 0; } }
                    </style>
                </head>
                <body>${receiptContent}</body>
            </html>
        `);
        printWindow.document.close();
        printWindow.print();
    }
    
    emailReceipt() {
        this.showInfo('Email receipt feature would be implemented here');
    }
    
    // Sales History
    viewSalesHistory() {
        const modal = new bootstrap.Modal(document.getElementById('salesHistoryModal'));
        modal.show();
        this.loadSalesHistory();
    }
    
    async loadSalesHistory() {
        const startDate = document.getElementById('startDate').value;
        const endDate = document.getElementById('endDate').value;
        
        try {
            const response = await fetch(`/pos/api/sales/history?start_date=${startDate}&end_date=${endDate}`);
            const data = await response.json();
            
            if (response.ok) {
                this.displaySalesHistory(data);
            } else {
                this.showError('Failed to load sales history: ' + data.error);
            }
        } catch (error) {
            this.showError('Network error: ' + error.message);
        }
    }
    
    displaySalesHistory(sales) {
        const content = document.getElementById('salesHistoryContent');
        
        if (sales.length === 0) {
            content.innerHTML = '<div class="text-center py-4"><p>No sales found for the selected period.</p></div>';
            return;
        }
        
        content.innerHTML = `
            <div class="table-responsive">
                <table class="table table-hover">
                    <thead>
                        <tr>
                            <th>Receipt #</th>
                            <th>Time</th>
                            <th>Customer</th>
                            <th>Items</th>
                            <th>Total</th>
                            <th>Payment</th>
                            <th>Actions</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${sales.map(sale => `
                            <tr>
                                <td>${sale.receipt_number}</td>
                                <td>${new Date(sale.created_at).toLocaleString()}</td>
                                <td>${sale.customer_name || 'Walk-in'}</td>
                                <td>${sale.item_count}</td>
                                <td>$${this.formatCurrency(sale.total_amount)}</td>
                                <td>${sale.payment_method}</td>
                                <td>
                                    <button class="btn btn-sm btn-outline-primary" onclick="posSystem.viewSaleDetails(${sale.id})">
                                        <i class="fas fa-eye"></i>
                                    </button>
                                </td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            </div>
        `;
    }
    
    // Barcode Scanner (placeholder)
    startBarcodeScanner() {
        this.showInfo('Barcode scanner would be implemented here using camera API');
    }
    
    // Cash Register Management
    closeCashRegister() {
        if (confirm('Are you sure you want to close the cash register?')) {
            window.location.href = '/pos/register/close';
        }
    }
    
    // Utility Functions
    formatCurrency(amount) {
        return typeof amount === 'number' ? amount.toFixed(2) : '0.00';
    }
    
    escapeHtml(text) {
        const map = {
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            '"': '&quot;',
            "'": '&#039;'
        };
        return text.replace(/[&<>"']/g, (m) => map[m]);
    }
    
    getCSRFToken() {
        return document.querySelector('meta[name="csrf-token"]').getAttribute('content');
    }
    
    showLoading(elementId) {
        document.getElementById(elementId).style.display = 'block';
    }
    
    hideLoading(elementId) {
        document.getElementById(elementId).style.display = 'none';
    }
    
    showSuccess(message) {
        this.showNotification(message, 'success');
    }
    
    showError(message) {
        this.showNotification(message, 'error');
    }
    
    showInfo(message) {
        this.showNotification(message, 'info');
    }
    
    showNotification(message, type) {
        // Use existing notification system or create toast
        console.log(`${type.toUpperCase()}: ${message}`);
        
        // Simple alert fallback
        if (type === 'error') {
            alert('Error: ' + message);
        }
    }
}

// Initialize POS system when page loads
let posSystem;
document.addEventListener('DOMContentLoaded', function() {
    posSystem = new EnhancedPOS();
});

// Global functions for HTML onclick handlers
function searchProducts(searchTerm) {
    posSystem.searchProducts(searchTerm);
}

function updateCustomer() {
    posSystem.updateCustomer();
}

function updateDiscountType() {
    posSystem.updateDiscountType();
}

function calculateDiscount() {
    posSystem.calculateDiscount();
}

function applyPromoCode() {
    posSystem.applyPromoCode();
}

function selectPaymentMethod(method) {
    posSystem.selectPaymentMethod(method);
}

function calculateChange() {
    posSystem.calculateChange();
}

function manageSplitPayment() {
    posSystem.manageSplitPayment();
}

function clearCart() {
    posSystem.clearCart();
}

function processCheckout() {
    posSystem.processCheckout();
}

function printReceipt() {
    posSystem.printReceipt();
}

function emailReceipt() {
    posSystem.emailReceipt();
}

function viewSalesHistory() {
    posSystem.viewSalesHistory();
}

function loadSalesHistory() {
    posSystem.loadSalesHistory();
}

function startBarcodeScanner() {
    posSystem.startBarcodeScanner();
}

function closeCashRegister() {
    posSystem.closeCashRegister();
}