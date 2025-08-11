# Cloud POS & Inventory Manager - Render Deployment Guide

## Complete Step-by-Step Guide for Render Deployment

This guide will walk you through deploying your Cloud POS application to Render with database migration.

## Prerequisites

- A Render account (sign up at [render.com](https://render.com))
- Your project code in a Git repository (GitHub, GitLab, or Bitbucket)
- Basic understanding of environment variables

## Step 1: Prepare Your Repository

### 1.1 Ensure Required Files Exist

Your project should have these deployment files (they're already included):

```
├── render.yaml          # Render configuration
├── build.sh            # Build script
├── Procfile           # Process definition
├── pyproject.toml     # Python dependencies
├── gunicorn.conf.py   # Gunicorn configuration
├── runtime.txt        # Python version
└── migrations/        # Database migration scripts
```

### 1.2 Dependencies Setup

Your project uses `pyproject.toml` for dependency management. The improved build script (`build.sh`) will:

1. **Upgrade pip** for better package resolution
2. **Install from pyproject.toml** using `pip install -e .`
3. **Install gunicorn explicitly** to ensure the server is available
4. **Verify core dependencies** are properly installed

**Key dependencies included:**
- Flask web framework with SQLAlchemy ORM
- PostgreSQL database driver (psycopg2-binary)
- Authentication (Flask-Login, bcrypt)
- Forms and validation (Flask-WTF, WTForms)
- PDF generation (ReportLab) and QR codes
- Production server (Gunicorn)

**Build process handles dependency installation automatically** - no manual setup required.

## Step 2: Set Up Database on Render

### 2.1 Create PostgreSQL Database

1. **Log in to Render Dashboard**
   - Go to https://dashboard.render.com
   - Click "New +" button
   - Select "PostgreSQL"

2. **Configure Database Settings**
   ```
   Name: cloudpos-db
   Database: cloudpos
   User: cloudpos_user
   Region: Choose closest to your target users
   PostgreSQL Version: 15 (recommended)
   Plan: Free (for testing) or Starter (for production)
   ```

3. **Note Database Connection Details**
   After creation, Render will provide:
   - **External Database URL**: `postgresql://user:password@host:port/database`
   - **Internal Database URL**: For app-to-database communication
   - **Host, Port, Username, Password**: Individual credentials

### 2.2 Database Security Configuration

1. **Access Control** (Optional for production)
   - Navigate to your database settings
   - Configure IP restrictions if needed
   - Enable SSL (recommended for production)

## Step 3: Deploy Web Application

### 3.1 Create Web Service

1. **Start New Web Service**
   - In Render Dashboard, click "New +"
   - Select "Web Service"
   - Connect your Git repository

2. **Basic Configuration**
   ```
   Name: cloudpos-inventory-manager
   Environment: Python 3
   Region: Same as your database
   Branch: main (or your primary branch)
   ```

3. **Build & Deploy Settings**
   ```
   Build Command: ./build.sh
   Start Command: gunicorn -c gunicorn.conf.py main:app
   ```

### 3.2 Configure Environment Variables

In your web service settings, add these environment variables:

#### Required Variables
```bash
# Database Connection
DATABASE_URL=<paste-your-external-database-url-here>

# Flask Configuration
SESSION_SECRET=<generate-secure-random-string>
FLASK_ENV=production
PYTHONPATH=.

# Performance Settings
WEB_CONCURRENCY=2
```

#### How to Get DATABASE_URL
1. Go to your PostgreSQL database in Render dashboard
2. Click on "Info" tab
3. Copy the "External Database URL"
4. Paste it as the value for `DATABASE_URL`

#### Generate SESSION_SECRET
Use a secure random generator:
```bash
# Option 1: Python
python -c "import secrets; print(secrets.token_hex(32))"

# Option 2: Online generator
# Visit: https://generate-secret.vercel.app/32
```

### 3.3 Advanced Configuration (Optional)

For production deployments, consider these additional variables:

```bash
# Database Pool Settings
DATABASE_POOL_SIZE=5
DATABASE_MAX_OVERFLOW=10

# Security Headers
SECURE_SSL_REDIRECT=true
SESSION_COOKIE_SECURE=true

# Logging
LOG_LEVEL=INFO
```

## Step 4: Database Migration Process

### 4.1 Automatic Migration System

Your application includes an **automatic migration system** that:

✅ **Runs automatically on app startup (not during build)**
✅ **Creates all required database tables**
✅ **Imports all default data safely**
✅ **Never overwrites existing data**
✅ **Dependencies are installed before migration runs**

#### What Gets Migrated Automatically:

1. **Database Schema**
   - All tables (users, products, stores, sales, etc.)
   - Indexes and constraints
   - Relationships and foreign keys

2. **Default Data**
   - Company profile settings
   - Two default stores (Main Store, Fashion Store)
   - Default user accounts with secure passwords
   - Product categories
   - Sample products with store assignments
   - Default customers

3. **User Accounts Created**
   | Role | Username | Password | Store |
   |------|----------|----------|-------|
   | Super Admin | `superadmin` | `super123` | Main Store |
   | Admin | `admin` | `admin123` | Main Store |
   | Manager | `manager1` | `manager123` | Main Store |
   | Cashier | `casava` | `cashier123` | Main Store |
   | Cashier | `julisunkan` | `cashier123` | Fashion Store |

### 4.2 Migration Verification

After deployment, check the logs to verify migration success:

1. **In Render Dashboard**
   - Go to your web service
   - Click "Logs" tab
   - Look for migration success messages:

```
🚀 Starting simple deployment migration...
✓ Database tables ensured
✓ Company profile created
✓ Main Store created
✓ Fashion Store created
✓ Super Admin user 'superadmin' created
✓ Admin user 'admin' created
✓ Manager user 'manager1' created
✓ Cashier user 'casava' created
✓ Cashier user 'julisunkan' created
✓ Categories created
✓ Products created with store assignments
Default data created successfully
```

## Step 5: Deploy and Test

### 5.1 Initial Deployment

1. **Deploy Application**
   - In your web service settings, click "Deploy Latest Commit"
   - Monitor the build logs for any errors
   - Wait for deployment to complete (usually 3-5 minutes)

2. **Access Your Application**
   - Your app will be available at: `https://your-service-name.onrender.com`
   - Example: `https://cloudpos-inventory-manager.onrender.com`

### 5.2 Post-Deployment Testing

#### Test 1: Login Verification
```
1. Visit your application URL
2. Try logging in with default credentials:
   - Username: admin
   - Password: admin123
3. Verify you can access the dashboard
```

#### Test 2: Database Connectivity
```
1. Navigate to Reports > Dashboard
2. Check if sales statistics load
3. Go to Inventory > Products
4. Verify products are displayed
```

#### Test 3: POS System
```
1. Login as cashier: casava / cashier123
2. Go to POS system
3. Try adding products to cart
4. Verify store-specific products appear
```

#### Test 4: Admin Functions
```
1. Login as superadmin: superadmin / super123
2. Go to Admin > Users
3. Verify all default users are created
4. Check Admin > Stores for store assignments
```

## Step 6: Security Configuration

### 6.1 Change Default Passwords

**⚠️ CRITICAL SECURITY STEP**

Immediately after successful deployment:

1. **Login as Super Admin**
   - Username: `superadmin`
   - Password: `super123`

2. **Change All Default Passwords**
   ```
   1. Go to Admin > Users
   2. Edit each user account
   3. Set strong, unique passwords
   4. Save changes
   ```

3. **Update Company Profile**
   ```
   1. Go to Admin > Company Profile
   2. Update with your actual business information
   3. Set correct currency and tax rates
   ```

### 6.2 Environment Security

1. **Verify Environment Variables**
   - Ensure `SESSION_SECRET` is set and unique
   - Confirm `FLASK_ENV=production`
   - Check database URL is correct

2. **Database Security**
   - Consider upgrading to paid plan for production
   - Enable automated backups
   - Monitor database usage

## Step 7: Ongoing Maintenance

### 7.1 Backups

**Database Backups (Recommended for Production)**
```
1. In Render Dashboard, go to your PostgreSQL database
2. Navigate to "Backups" tab
3. Enable automatic daily backups
4. Set retention period (7-30 days recommended)
```

### 7.2 Monitoring

**Application Monitoring**
```
1. Set up monitoring in Render Dashboard
2. Configure alerts for downtime
3. Monitor resource usage
4. Review application logs regularly
```

### 7.3 Updates and Redeployments

**For Code Updates**
```
1. Push changes to your Git repository
2. Render will auto-deploy if auto-deploy is enabled
3. Or manually deploy from Render Dashboard
4. Migration system will preserve all existing data
```

## Troubleshooting

### Common Issues and Solutions

#### Issue 1: Build Fails - "gunicorn: command not found"
```
Error: bash: line 1: gunicorn: command not found
Solution:
1. Verify build script ran successfully (pip install -e .)
2. Check build logs for dependency installation errors
3. Ensure pyproject.toml is properly formatted
4. In render.yaml, verify buildCommand: "./build.sh"
```

#### Issue 2: Migration Fails - "ModuleNotFoundError"
```
Error: ModuleNotFoundError: No module named 'werkzeug'
Solution:
1. Dependencies now installed before migration runs
2. Check build logs for successful dependency installation
3. Verify all required packages in pyproject.toml
4. Migration now runs after app startup, not during build
```

#### Issue 3: Database Connection Error
```
Error: could not connect to server
Solution:
1. Verify DATABASE_URL is correct in environment variables
2. Check database is running in Render Dashboard
3. Ensure database and web service are in same region
4. Confirm database URL format: postgresql://user:pass@host:port/db
```

#### Issue 4: Migration Succeeds but No Data
```
Error: empty product lists or missing store data
Solution:
1. Check application startup logs for migration messages
2. Look for "✅ Deployment migration completed successfully"
3. Verify store assignments in Admin panel
4. Migration runs automatically on every app startup
```

#### Issue 5: Login Issues
```
Error: cannot login with default credentials
Solution:
1. Check migration logs for user creation success
2. Try all default accounts (see credentials table above)
3. Verify password hashing is working correctly
4. Check for database table creation errors
```

### Getting Help

1. **Check Logs First**
   - Render Dashboard > Your Service > Logs
   - Look for error messages and stack traces

2. **Database Console Access**
   ```bash
   # Connect to your database for debugging
   psql $DATABASE_URL
   ```

3. **Application Health Check**
   - Your app includes health endpoints
   - Visit: `https://your-app.onrender.com/health` (if implemented)

## Advanced Configuration

### Custom Domain Setup

1. **Purchase Domain** (optional)
2. **In Render Dashboard**
   - Go to your web service
   - Click "Settings" > "Custom Domains"
   - Add your domain and configure DNS

### SSL Certificate

- Render provides automatic SSL certificates
- No additional configuration needed
- Your app will be accessible via HTTPS

### Performance Optimization

For production deployments:

```bash
# In environment variables
WEB_CONCURRENCY=4          # Increase for more traffic
DATABASE_POOL_SIZE=10      # Larger connection pool
DATABASE_MAX_OVERFLOW=20   # Higher overflow limit
```

## Conclusion

Your Cloud POS & Inventory Manager is now successfully deployed to Render with:

✅ **Complete database migration**
✅ **All default data imported**
✅ **Secure user accounts created**
✅ **Multi-store setup configured**
✅ **Production-ready configuration**

**Next Steps:**
1. Change all default passwords
2. Update company information
3. Add your actual products and inventory
4. Train your team on the system
5. Set up regular backups

Your application URL: `https://your-service-name.onrender.com`

**Support:** Refer to the application's built-in help system and user documentation for operational guidance.