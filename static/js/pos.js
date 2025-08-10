// POS JavaScript functionality

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
// Get currency symbol from global configuration (should be set in template)
const CURRENCY_SYMBOL = window.currencySymbol || '$';

class POSSystem {
    constructor() {
        this.cart = [];
        this.currentCustomer = null;
        this.init();
    }

    init() {
        this.bindEvents();
        this.updateCartDisplay();
    }

    bindEvents() {
        // Product search
        const searchInput = document.getElementById('productSearch');
        if (searchInput) {
            searchInput.addEventListener('input', this.debounce(this.searchProducts.bind(this), 300));
        }

        // Product cards click
        document.addEventListener('click', (e) => {
            if (e.target.closest('.product-card')) {
                this.addProductToCart(e.target.closest('.product-card'));
            }
        });

        // Cart item quantity changes
        document.addEventListener('change', (e) => {
            if (e.target.classList.contains('cart-quantity')) {
                this.updateCartItemQuantity(e.target);
            }
        });
        
        // Also listen for input events for real-time updates
        document.addEventListener('input', (e) => {
            if (e.target.classList.contains('cart-quantity')) {
                this.updateCartItemQuantity(e.target);
            }
        });

        // Remove cart item
        document.addEventListener('click', (e) => {
            if (e.target.classList.contains('remove-cart-item')) {
                this.removeCartItem(e.target.dataset.index);
            }
        });

        // Customer selection
        const customerSelect = document.getElementById('customerSelect');
        if (customerSelect) {
            customerSelect.addEventListener('change', (e) => {
                this.currentCustomer = e.target.value || null;
            });
        }

        // Discount input
        const discountInput = document.getElementById('discount');
        if (discountInput) {
            discountInput.addEventListener('input', this.updateTotals.bind(this));
        }

        // Process sale button
        const processSaleBtn = document.getElementById('processSale');
        if (processSaleBtn) {
            processSaleBtn.addEventListener('click', this.processSale.bind(this));
        }

        // Clear cart button
        const clearCartBtn = document.getElementById('clearCart');
        if (clearCartBtn) {
            clearCartBtn.addEventListener('click', this.clearCart.bind(this));
        }

        // Hold sale button
        const holdSaleBtn = document.getElementById('holdSale');
        if (holdSaleBtn) {
            holdSaleBtn.addEventListener('click', this.holdSale.bind(this));
        }
        
        // View held sales button
        const viewHeldSalesBtn = document.getElementById('viewHeldSales');
        if (viewHeldSalesBtn) {
            viewHeldSalesBtn.addEventListener('click', this.showHeldSales.bind(this));
        }

        // Barcode scan button (mock functionality)
        const scanBarcodeBtn = document.getElementById('scanBarcode');
        if (scanBarcodeBtn) {
            scanBarcodeBtn.addEventListener('click', this.scanBarcode.bind(this));
        }

        // Print receipt button
        const printReceiptBtn = document.getElementById('printReceipt');
        if (printReceiptBtn) {
            printReceiptBtn.addEventListener('click', this.printReceipt.bind(this));
        }
    }

    debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }

    async searchProducts(event) {
        const query = event.target.value.trim();
        if (query.length < 2) {
            document.getElementById('searchResults').innerHTML = '';
            return;
        }

        try {
            const response = await fetch(`/pos/api/products/search?q=${encodeURIComponent(query)}`);
            const products = await response.json();
            this.displaySearchResults(products);
        } catch (error) {
            console.error('Search error:', error);
        }
    }

    displaySearchResults(products) {
        const resultsContainer = document.getElementById('searchResults');
        
        if (products.length === 0) {
            resultsContainer.innerHTML = '<div class="col-12"><p class="text-muted">No products found.</p></div>';
            return;
        }

        const html = products.map(product => `
            <div class="col-md-3 col-sm-4 col-6 mb-3">
                <div class="card product-card h-100" 
                     data-product-id="${product.id}" 
                     data-product-name="${product.name}" 
                     data-product-price="${product.price}"
                     data-product-stock="${product.stock}"
                     data-product-tax="${product.tax_rate}">
                    <div class="card-body text-center p-2">
                        <h6 class="card-title mb-1">${product.name}</h6>
                        <p class="card-text mb-1">
                            <strong>${CURRENCY_SYMBOL}${product.price.toFixed(2)}</strong>
                        </p>
                        <small class="text-muted">Stock: ${product.stock}</small>
                    </div>
                </div>
            </div>
        `).join('');
        
        resultsContainer.innerHTML = html;
    }

    addProductToCart(productCard) {
        const productId = parseInt(productCard.dataset.productId);
        const productName = productCard.dataset.productName;
        const productPrice = parseFloat(productCard.dataset.productPrice);
        const productStock = parseInt(productCard.dataset.productStock);
        const productTax = parseFloat(productCard.dataset.productTax) || 0;

        console.log('Adding product to cart:', { productId, productName, productPrice, productStock, productTax }); // Debug log

        if (productStock <= 0) {
            this.showAlert('Product is out of stock!', 'warning');
            return;
        }

        // Check if product already in cart
        const existingItem = this.cart.find(item => item.id === productId);
        
        if (existingItem) {
            if (existingItem.quantity >= productStock) {
                this.showAlert('Cannot add more items than available in stock!', 'warning');
                return;
            }
            existingItem.quantity++;
        } else {
            this.cart.push({
                id: parseInt(productId),
                name: productName,
                price: parseFloat(productPrice),
                quantity: 1,
                tax_rate: parseFloat(productTax),
                max_stock: parseInt(productStock)
            });
        }

        console.log('Cart after adding product:', this.cart); // Debug log
        this.updateCartDisplay();
        this.updateTotals();
    }

    updateCartDisplay() {
        const cartContainer = document.getElementById('cartItems');
        const emptyCart = document.getElementById('emptyCart');
        const processSaleBtn = document.getElementById('processSale');

        if (this.cart.length === 0) {
            emptyCart.style.display = 'block';
            processSaleBtn.disabled = true;
            return;
        }

        emptyCart.style.display = 'none';
        processSaleBtn.disabled = false;

        const cartHtml = this.cart.map((item, index) => `
            <div class="cart-item border-bottom pb-2 mb-2">
                <div class="d-flex justify-content-between align-items-start">
                    <div class="flex-grow-1">
                        <h6 class="mb-1">${item.name}</h6>
                        <small class="text-muted">${CURRENCY_SYMBOL}${item.price.toFixed(2)} each</small>
                    </div>
                    <button type="button" class="btn btn-sm btn-outline-danger remove-cart-item" 
                            data-index="${index}">
                        <i class="fas fa-times"></i>
                    </button>
                </div>
                <div class="d-flex justify-content-between align-items-center mt-2">
                    <div class="input-group input-group-sm" style="width: 80px;">
                        <input type="number" class="form-control cart-quantity" 
                               value="${item.quantity}" min="1" max="${item.max_stock}"
                               data-index="${index}">
                    </div>
                    <strong>${CURRENCY_SYMBOL}${(item.price * item.quantity).toFixed(2)}</strong>
                </div>
            </div>
        `).join('');

        cartContainer.innerHTML = cartHtml;
    }

    updateCartItemQuantity(input) {
        const index = parseInt(input.dataset.index);
        const newQuantity = parseInt(input.value);
        const item = this.cart[index];

        if (newQuantity <= 0) {
            this.removeCartItem(index);
            return;
        }

        if (newQuantity > item.max_stock) {
            input.value = item.max_stock;
            this.showAlert('Cannot exceed available stock!', 'warning');
            return;
        }

        item.quantity = newQuantity;
        this.updateCartDisplay();
        this.updateTotals();
    }

    removeCartItem(index) {
        this.cart.splice(index, 1);
        this.updateCartDisplay();
        this.updateTotals();
    }

    updateTotals() {
        console.log('Updating totals, cart:', this.cart); // Debug log
        
        let subtotal = 0;
        let taxTotal = 0;

        this.cart.forEach(item => {
            const itemTotal = item.price * item.quantity;
            subtotal += itemTotal;
            taxTotal += (itemTotal * (item.tax_rate || 0)) / 100;
        });

        const discountElement = document.getElementById('discount');
        const discount = discountElement ? parseFloat(discountElement.value) || 0 : 0;
        const total = subtotal + taxTotal - discount;

        console.log('Calculated totals:', { subtotal, taxTotal, discount, total }); // Debug log

        // Update DOM elements
        const subtotalElement = document.getElementById('subtotal');
        const taxElement = document.getElementById('taxAmount');
        const totalElement = document.getElementById('total');

        if (subtotalElement) subtotalElement.textContent = `${CURRENCY_SYMBOL}${subtotal.toFixed(2)}`;
        if (taxElement) taxElement.textContent = `${CURRENCY_SYMBOL}${taxTotal.toFixed(2)}`;
        if (totalElement) totalElement.textContent = `${CURRENCY_SYMBOL}${total.toFixed(2)}`;
    }

    async processSale() {
        if (this.cart.length === 0) {
            this.showAlert('Cart is empty!', 'warning');
            return;
        }

        const saleData = {
            items: this.cart.map(item => ({
                product_id: parseInt(item.id),
                quantity: parseInt(item.quantity),
                unit_price: parseFloat(item.price)
            })),
            customer_id: this.currentCustomer,
            payment_method: document.getElementById('paymentMethod').value,
            discount: parseFloat(document.getElementById('discount').value) || 0,
            notes: document.getElementById('saleNotes') ? document.getElementById('saleNotes').value : ''
        };

        try {
            const response = await fetch('/pos/api/sale/process', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(saleData)
            });

            const result = await response.json();

            if (response.ok && result.success) {
                this.showSaleSuccess(result.receipt_number, result.total_amount);
                this.clearCart();
            } else {
                this.showAlert(result.error || 'Sale processing failed!', 'danger');
            }
        } catch (error) {
            console.error('Sale processing error:', error);
            this.showAlert('Network error occurred!', 'danger');
        }
    }

    showSaleSuccess(receiptNumber, totalAmount) {
        document.getElementById('receiptNumber').textContent = `Receipt: ${receiptNumber}`;
        document.getElementById('saleTotal').textContent = `Total: ${CURRENCY_SYMBOL}${totalAmount.toFixed(2)}`;
        
        // Store receipt data for printing
        this.lastReceiptData = {
            receiptNumber,
            totalAmount,
            items: [...this.cart],
            customer: this.currentCustomer,
            paymentMethod: document.getElementById('paymentMethod').value,
            timestamp: new Date()
        };
        
        const modal = new bootstrap.Modal(document.getElementById('saleSuccessModal'));
        modal.show();
    }

    clearCart() {
        this.cart = [];
        this.currentCustomer = null;
        document.getElementById('customerSelect').value = '';
        document.getElementById('discount').value = '0';
        const notesField = document.getElementById('saleNotes');
        if (notesField) notesField.value = '';
        document.getElementById('paymentMethod').value = 'Cash';
        this.updateCartDisplay();
        this.updateTotals();
    }

    holdSale() {
        if (this.cart.length === 0) {
            this.showAlert('Cart is empty!', 'warning');
            return;
        }
        
        // Save to localStorage for later
        const heldSale = {
            cart: this.cart,
            customer: this.currentCustomer,
            discount: document.getElementById('discount').value,
            notes: document.getElementById('saleNotes').value,
            timestamp: new Date().toISOString()
        };
        
        localStorage.setItem('heldSale', JSON.stringify(heldSale));
        this.showAlert('Sale held successfully!', 'success');
        this.clearCart();
    }

    scanBarcode() {
        // Mock barcode scanning - in real implementation, this would use a barcode scanner API
        const barcode = prompt('Enter barcode:');
        if (barcode) {
            document.getElementById('productSearch').value = barcode;
            this.searchProducts({ target: { value: barcode } });
        }
    }

    getCSRFToken() {
        // CSRF disabled for API endpoints
        return '';
    }

    printReceipt() {
        if (!this.lastReceiptData) {
            this.showAlert('No receipt data available!', 'warning');
            return;
        }

        const receiptNumber = this.lastReceiptData.receiptNumber;
        
        // Create a download link for the PDF
        const downloadUrl = `/pos/receipt/print/${receiptNumber}`;
        
        // Create temporary link element and trigger download
        const link = document.createElement('a');
        link.href = downloadUrl;
        link.download = `receipt_${receiptNumber}.pdf`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        
        this.showAlert('Receipt PDF generated and downloaded!', 'success');
    }

    showAlert(message, type) {
        const messageArea = document.getElementById('messageArea');
        const messageContent = document.getElementById('messageContent');
        const messageText = document.getElementById('messageText');
        
        if (!messageArea || !messageContent || !messageText) {
            // Fallback to console if message area doesn't exist
            console.log(`${type.toUpperCase()}: ${message}`);
            return;
        }
        
        // Set message content and type
        messageText.textContent = message;
        messageContent.className = `alert alert-${type} alert-dismissible fade show`;
        
        // Show message area
        messageArea.classList.remove('d-none');
        
        // Auto-hide after 5 seconds
        setTimeout(() => {
            this.hideMessage();
        }, 5000);
    }

    hideMessage() {
        const messageArea = document.getElementById('messageArea');
        if (messageArea) {
            messageArea.classList.add('d-none');
        }
    }
}

// Initialize POS system when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new POSSystem();
});
