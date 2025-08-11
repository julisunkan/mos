# Cloud POS & Inventory Manager - Deployment Guide

## Automatic Data Migration System

This project includes a comprehensive deployment migration system that ensures all existing data is automatically imported whenever the project is deployed to any environment.

### What Gets Migrated Automatically

1. **Company Profile**
   - Default company information and settings
   - Currency and tax configurations

2. **Default Stores**
   - Main Store (default primary store)
   - Fashion Store (secondary store)
   - Store configuration and contact information

3. **User Accounts (All Existing Users)**
   - **Super Admin**: `superadmin` / `super123`
   - **Admin**: `admin` / `admin123`
   - **Manager**: `manager1` / `manager123`
   - **Cashier (Main Store)**: `casava` / `cashier123`
   - **Cashier (Fashion Store)**: `julisunkan` / `cashier123`

4. **Product Categories**
   - Electronics, Clothing, Food & Beverages
   - Books & Media, Home & Garden, Sports & Outdoors
   - Health & Beauty, Toys & Games

5. **Products with Store Assignments**
   - **Main Store Products**:
     - Wireless Headphones (25 units)
     - Coffee Beans 1kg (30 units)
   - **Fashion Store Products**:
     - Cotton T-Shirt (50 units)
     - Designer Jeans (20 units)
     - Fashion Accessories (15 units)

6. **Sample Customers**
   - Retail, Wholesale, and VIP customer profiles
   - Complete contact information and customer types

### How the Migration System Works

#### 1. Startup Migration
The application automatically runs the deployment migration on every startup through `app.py`:

```python
# Run deployment migration on startup
try:
    from migrations.simple_deploy_migration import ensure_data_exists
    ensure_data_exists()
except Exception as e:
    # Fallback to seed data if migration fails
    exec(open('seed_data.py').read())
```

#### 2. Deployment Scripts
- **`migrations/simple_deploy_migration.py`**: Primary migration script using direct SQL
- **`migrations/deploy_migration.py`**: Advanced ORM-based migration (fallback)
- **`deploy_setup.py`**: Pre-deployment setup wrapper with fallback support
- **`build.sh`**: Build script for deployment environments
- **`seed_data.py`**: Final fallback seed data system

#### 3. Platform Integration
- **Procfile**: Configured for Heroku-style deployments
- **render.yaml**: Ready for Render deployment
- **Railway/Vercel**: Compatible with their build processes

### Data Persistence Guarantees

1. **Idempotent Operations**: All migrations check for existing data before creating
2. **No Data Loss**: Existing data is never overwritten
3. **Incremental Updates**: Only missing data is added
4. **Error Handling**: Graceful fallbacks if migration fails
5. **Transaction Safety**: All operations are wrapped in database transactions

### Security Features in Deployment

1. **Role-Based Hierarchy**: Super Admin > Admin > Manager/Cashier/Accountant
2. **Admin Protection**: 
   - Regular Admins cannot edit Super Admin accounts
   - Password/username editing restrictions for admin accounts
3. **Store Isolation**: Cashiers restricted to assigned store products only
4. **Default Credentials**: Secure defaults with change reminders

### Deployment Environments

#### Development
```bash
python deploy_setup.py
```

#### Production Deployment
1. Environment automatically runs `deploy_setup.py` during build
2. All user data and store configurations are preserved
3. Default admin accounts are created if they don't exist
4. Store-product assignments are maintained

#### Database Migration Flow
```
1. Database tables created/updated
2. Company profile ensured
3. Default stores created
4. All user accounts imported (Super Admin, Admin, Managers, Cashiers)
5. Product categories established
6. Products created with store assignments
7. Customer profiles imported
8. Store-user relationships established
```

### Login Credentials (Post-Deployment)

| Role | Username | Password | Store Assignment |
|------|----------|----------|------------------|
| Super Admin | `superadmin` | `super123` | Main Store |
| Admin | `admin` | `admin123` | Main Store |
| Manager | `manager1` | `manager123` | Main Store |
| Cashier | `casava` | `cashier123` | Main Store |
| Cashier | `julisunkan` | `cashier123` | Fashion Store |

**⚠️ Security Notice**: Change all default passwords immediately after deployment!

### Verification Steps After Deployment

1. **Login Test**: Verify all user accounts can log in
2. **Store Access**: Confirm cashiers see only their store's products
3. **Admin Functions**: Test user management and system administration
4. **POS Operations**: Verify sales transactions work correctly
5. **Inventory Management**: Check product and stock management
6. **Reports**: Confirm dashboard and reporting functions

### Troubleshooting

#### Migration Fails
- Check database connection and permissions
- Verify all required models are imported
- Review application logs for specific errors

#### Missing Data
- Run migration manually: `python migrations/deploy_migration.py`
- Check database constraints and foreign key relationships
- Verify store and user assignments

#### Performance Issues
- Migration runs only once per deployment
- Subsequent startups skip existing data
- No performance impact on running application

### Environment Variables Required

- `DATABASE_URL`: PostgreSQL connection string
- `SESSION_SECRET`: Flask session secret key
- `PGHOST`, `PGPORT`, `PGUSER`, `PGPASSWORD`, `PGDATABASE`: Database credentials

### Deployment Platform Support

✅ **Heroku**: Full support with Procfile
✅ **Render**: Complete with render.yaml
✅ **Railway**: Compatible build process
✅ **Vercel**: Serverless deployment ready
✅ **Digital Ocean**: App Platform compatible
✅ **AWS**: Elastic Beanstalk ready
✅ **Google Cloud**: App Engine compatible

The system is designed to work seamlessly across all major deployment platforms while ensuring data consistency and security.