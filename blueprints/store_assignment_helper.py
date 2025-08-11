"""
Helper functions for store assignment management
This module provides utilities to ensure proper store-user-product relationships
"""

from app import db
from models import User, Store, StoreStock, Product

def assign_user_to_store(user_id, store_id):
    """
    Assign a user to a store with proper validation
    Returns (success: bool, message: str)
    """
    try:
        user = User.query.get(user_id)
        store = Store.query.get(store_id)
        
        if not user:
            return False, "User not found"
        if not store:
            return False, "Store not found"
        
        # Update user's store assignment
        user.store_id = store_id
        db.session.commit()
        
        return True, f"User {user.username} assigned to {store.name}"
    
    except Exception as e:
        db.session.rollback()
        return False, f"Error assigning user to store: {str(e)}"

def ensure_store_has_products(store_id, min_products=3):
    """
    Ensure a store has at least minimum number of products assigned
    Auto-assigns products if needed
    Returns (success: bool, message: str, products_assigned: int)
    """
    try:
        store = Store.query.get(store_id)
        if not store:
            return False, "Store not found", 0
        
        # Check current product assignments
        current_assignments = StoreStock.query.filter_by(store_id=store_id).count()
        
        if current_assignments >= min_products:
            return True, f"Store {store.name} already has {current_assignments} products", current_assignments
        
        # Get products that are not yet assigned to this store
        assigned_product_ids = db.session.query(StoreStock.product_id).filter_by(store_id=store_id).all()
        assigned_product_ids = [pid[0] for pid in assigned_product_ids]
        
        available_products = Product.query.filter(
            Product.is_active == True,
            ~Product.id.in_(assigned_product_ids)
        ).limit(min_products - current_assignments).all()
        
        products_assigned = 0
        for product in available_products:
            store_stock = StoreStock()
            store_stock.store_id = store_id
            store_stock.product_id = product.id
            store_stock.quantity = 10  # Default starter quantity
            db.session.add(store_stock)
            products_assigned += 1
        
        db.session.commit()
        
        total_products = current_assignments + products_assigned
        return True, f"Assigned {products_assigned} products to {store.name}. Total: {total_products}", products_assigned
    
    except Exception as e:
        db.session.rollback()
        return False, f"Error assigning products to store: {str(e)}", 0

def verify_store_setup(store_id):
    """
    Verify that a store is properly set up with users and products
    Returns (is_valid: bool, issues: list, suggestions: list)
    """
    try:
        store = Store.query.get(store_id)
        if not store:
            return False, ["Store not found"], []
        
        issues = []
        suggestions = []
        
        # Check if store has assigned users
        assigned_users = User.query.filter_by(store_id=store_id).count()
        if assigned_users == 0:
            issues.append("No users assigned to this store")
            suggestions.append("Assign at least one cashier or manager to this store")
        
        # Check if store has products
        product_count = StoreStock.query.filter_by(store_id=store_id).count()
        if product_count == 0:
            issues.append("No products assigned to this store")
            suggestions.append("Assign products to this store for POS operations")
        elif product_count < 3:
            suggestions.append(f"Consider adding more products (currently {product_count})")
        
        # Check if store has products with stock
        products_with_stock = StoreStock.query.filter(
            StoreStock.store_id == store_id,
            StoreStock.quantity > 0
        ).count()
        
        if products_with_stock == 0:
            issues.append("No products have stock quantities")
            suggestions.append("Add stock quantities to products for sales")
        
        is_valid = len(issues) == 0
        return is_valid, issues, suggestions
    
    except Exception as e:
        return False, [f"Error verifying store setup: {str(e)}"], []

def sync_user_store_assignments():
    """
    Synchronize user.store_id with UserStore relationships for consistency
    This fixes any mismatches between direct assignments and relationship table
    Returns (success: bool, message: str, fixes_applied: int)
    """
    try:
        from models import User, UserStore
        
        fixes_applied = 0
        users_with_relationships = db.session.query(User).join(UserStore).all()
        
        for user in users_with_relationships:
            # Get user's first store relationship as primary
            primary_user_store = UserStore.query.filter_by(user_id=user.id).first()
            
            if primary_user_store and user.store_id != primary_user_store.store_id:
                print(f"Fixing user {user.username}: store_id {user.store_id} -> {primary_user_store.store_id}")
                user.store_id = primary_user_store.store_id
                fixes_applied += 1
        
        # Also check users with store_id but no relationships
        users_with_direct_only = User.query.filter(
            User.store_id.isnot(None)
        ).filter(
            ~User.id.in_(db.session.query(UserStore.user_id))
        ).all()
        
        for user in users_with_direct_only:
            # Create missing UserStore relationship
            user_store = UserStore()
            user_store.user_id = user.id
            user_store.store_id = user.store_id
            user_store.is_default = True
            db.session.add(user_store)
            fixes_applied += 1
            print(f"Created missing relationship for user {user.username} -> store {user.store_id}")
        
        if fixes_applied > 0:
            db.session.commit()
            return True, f"Fixed {fixes_applied} user-store assignment inconsistencies", fixes_applied
        else:
            return True, "All user-store assignments are consistent", 0
    
    except Exception as e:
        db.session.rollback()
        return False, f"Error syncing user store assignments: {str(e)}", 0

def fix_store_setup(store_id):
    """
    Automatically fix common store setup issues
    Returns (success: bool, actions_taken: list, remaining_issues: list)
    """
    actions_taken = []
    remaining_issues = []
    
    try:
        # Ensure store has products
        success, message, products_assigned = ensure_store_has_products(store_id, min_products=5)
        if success and products_assigned > 0:
            actions_taken.append(f"Auto-assigned {products_assigned} products")
        elif not success:
            remaining_issues.append(message)
        
        # Verify final setup
        is_valid, issues, suggestions = verify_store_setup(store_id)
        remaining_issues.extend(issues)
        
        return True, actions_taken, remaining_issues
    
    except Exception as e:
        return False, actions_taken, [f"Error fixing store setup: {str(e)}"]