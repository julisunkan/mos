from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from models import *
from app import db
import logging
from utils import generate_receipt_number
from blueprints.pos_clean import get_user_store, get_user_cash_register, get_store_products
from decimal import Decimal

pos_api_bp = Blueprint('pos_api', __name__, url_prefix='/pos/api')

@pos_api_bp.route('/products/search')
@login_required
def search_products():
    """Search products by name, SKU, or barcode"""
    user_store = get_user_store()
    if not user_store:
        return jsonify({'error': 'No store assigned'}), 400
    
    try:
        search_term = request.args.get('q', '').strip().lower()
        if not search_term:
            return jsonify([])
        
        products = get_store_products(user_store.id)
        
        # Filter products based on search term
        filtered_products = []
        for product in products:
            if (search_term in product.name.lower() or 
                search_term in product.sku.lower() or 
                (product.barcode and search_term in product.barcode.lower())):
                filtered_products.append(product)
        
        results = []
        for product in filtered_products:
            # Get current stock from store_stock table
            stock_info = StoreStock.query.filter_by(
                store_id=user_store.id, 
                product_id=product.id
            ).first()
            
            current_stock = stock_info.quantity if stock_info else 0
            
            results.append({
                'id': product.id,
                'name': product.name,
                'sku': product.sku,
                'barcode': product.barcode,
                'price': float(product.selling_price),
                'cost': float(product.cost_price) if product.cost_price else 0,
                'stock': int(current_stock),
                'tax_rate': float(product.tax_rate) if product.tax_rate else 0,
                'category': product.category.name if product.category else 'Uncategorized'
            })
        
        return jsonify(results)
        
    except Exception as e:
        logging.error(f'Error searching products: {e}')
        return jsonify({'error': 'Search failed'}), 500

@pos_api_bp.route('/sale/process', methods=['POST'])
@login_required
def process_sale():
    """Process a complete sale transaction"""
    try:
        data = request.get_json()
        
        user_store = get_user_store()
        if not user_store:
            return jsonify({'error': 'No store assigned'}), 400
        
        cash_register = get_user_cash_register()
        if not cash_register:
            return jsonify({'error': 'No open cash register'}), 400
        
        # Validate required data
        items = data.get('items', [])
        if not items:
            return jsonify({'error': 'No items in cart'}), 400
        
        # Calculate totals
        subtotal = 0
        total_tax = 0
        
        for item in items:
            item_total = float(item['quantity']) * float(item['unit_price'])
            subtotal += item_total
            
            # Calculate tax for this item
            product = Product.query.get(item['product_id'])
            if product and product.tax_rate:
                tax_amount = (item_total * float(product.tax_rate)) / 100
                total_tax += tax_amount
        
        # Apply discount
        discount_info = data.get('discount', {})
        discount_amount = float(discount_info.get('amount', 0))
        
        total_amount = subtotal + total_tax - discount_amount
        
        # Create sale record
        sale = Sale()
        sale.receipt_number = generate_receipt_number()
        sale.user_id = current_user.id
        sale.customer_id = data.get('customer_id')
        sale.store_id = user_store.id
        sale.subtotal = subtotal
        sale.tax_amount = total_tax
        sale.discount_amount = discount_amount
        sale.total_amount = total_amount
        sale.payment_method = data.get('payment_method', 'cash')
        sale.payment_status = 'Completed'
        sale.amount_tendered = data.get('amount_tendered', total_amount)
        sale.change_amount = max(0, float(data.get('amount_tendered', total_amount)) - total_amount)
        sale.payment_reference = data.get('payment_reference', '')
        sale.currency = 'USD'
        sale.exchange_rate = 1.0
        sale.notes = data.get('notes', '')
        
        # Add new discount fields
        sale.discount_type = discount_info.get('type', 'none')
        sale.discount_percentage = float(discount_info.get('value', 0)) if discount_info.get('type') == 'percentage' else 0
        sale.promo_code = discount_info.get('code', '')
        
        db.session.add(sale)
        db.session.flush()  # Get the sale ID
        
        # Create sale items
        for item in items:
            sale_item = SaleItem()
            sale_item.sale_id = sale.id
            sale_item.product_id = item['product_id']
            sale_item.quantity = item['quantity']
            sale_item.unit_price = item['unit_price']
            sale_item.total_price = float(item['quantity']) * float(item['unit_price'])
            db.session.add(sale_item)
            
            # Update stock
            stock_record = StoreStock.query.filter_by(
                store_id=user_store.id, 
                product_id=item['product_id']
            ).first()
            if stock_record:
                stock_record.quantity = max(0, stock_record.quantity - item['quantity'])
        
        # Update promotion code usage if used
        if sale.promo_code:
            promo = PromotionCode.query.filter_by(code=sale.promo_code, is_active=True).first()
            if promo:
                promo.usage_count += 1
        
        # Update customer loyalty points if applicable
        if sale.customer_id:
            customer = Customer.query.get(sale.customer_id)
            if customer and customer.loyalty_program:
                # Earn 1 point per dollar spent
                points_earned = int(total_amount)
                customer.loyalty_program.points_balance += points_earned
                sale.loyalty_points_earned = points_earned
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'sale_id': sale.id,
            'receipt_number': sale.receipt_number,
            'total_amount': float(total_amount),
            'change_amount': float(sale.change_amount),
            'loyalty_points_earned': sale.loyalty_points_earned or 0
        })
        
    except Exception as e:
        db.session.rollback()
        logging.error(f'Error processing sale: {e}')
        return jsonify({'error': 'Sale processing failed'}), 500