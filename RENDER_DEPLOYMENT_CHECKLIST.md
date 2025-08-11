# Render Deployment Checklist

## Pre-Deployment Checklist

### Repository Setup
- [ ] Code pushed to Git repository (GitHub, GitLab, or Bitbucket)
- [ ] `render.yaml` configuration file present
- [ ] `build.sh` script executable
- [ ] `pyproject.toml` with all dependencies
- [ ] Migration scripts in `migrations/` folder

### Account Setup
- [ ] Render account created and verified
- [ ] Payment method added (for non-free plans)
- [ ] Repository connected to Render

## Database Setup Checklist

### Create PostgreSQL Database
- [ ] New PostgreSQL service created in Render
- [ ] Database name: `cloudpos-db`
- [ ] Database user: `cloudpos_user`
- [ ] Database plan selected (Free/Starter/Pro)
- [ ] Database region chosen
- [ ] Database URL noted and saved

## Web Service Setup Checklist

### Basic Configuration
- [ ] New Web Service created
- [ ] Repository connected
- [ ] Service name: `cloudpos-inventory-manager`
- [ ] Environment: Python 3
- [ ] Build command: `./build.sh`
- [ ] Start command: `gunicorn -c gunicorn.conf.py main:app`

### Environment Variables
Required variables configured:
- [ ] `DATABASE_URL` (from PostgreSQL service)
- [ ] `SESSION_SECRET` (generated secure random string)
- [ ] `FLASK_ENV=production`
- [ ] `PYTHONPATH=.`
- [ ] `WEB_CONCURRENCY=2`

Optional production variables:
- [ ] `DATABASE_POOL_SIZE=5`
- [ ] `DATABASE_MAX_OVERFLOW=10`
- [ ] `SECURE_SSL_REDIRECT=true`
- [ ] `SESSION_COOKIE_SECURE=true`

## Deployment Verification Checklist

### Initial Deployment
- [ ] Service deploys successfully (no build errors)
- [ ] Application starts without crashes
- [ ] Health check passes (if implemented)
- [ ] Application accessible via Render URL

### Database Migration Verification
Check deployment logs for these success messages:
- [ ] "🚀 Starting simple deployment migration..."
- [ ] "✓ Database tables ensured"
- [ ] "✓ Company profile created"
- [ ] "✓ Main Store created"
- [ ] "✓ Fashion Store created"
- [ ] "✓ Super Admin user 'superadmin' created"
- [ ] "✓ Admin user 'admin' created"
- [ ] "✓ Manager user 'manager1' created"
- [ ] "✓ Cashier user 'casava' created"
- [ ] "✓ Cashier user 'julisunkan' created"
- [ ] "✓ Categories created"
- [ ] "✓ Products created with store assignments"

### Login Testing
Test all default user accounts:
- [ ] Super Admin: `superadmin` / `super123`
- [ ] Admin: `admin` / `admin123`
- [ ] Manager: `manager1` / `manager123`
- [ ] Cashier (Main): `casava` / `cashier123`
- [ ] Cashier (Fashion): `julisunkan` / `cashier123`

### Functionality Testing
- [ ] Dashboard loads with statistics
- [ ] User management accessible (Admin accounts)
- [ ] Store management functional
- [ ] Product inventory displays correctly
- [ ] POS system accessible to cashiers
- [ ] Store-specific product filtering works
- [ ] Sales can be processed
- [ ] Reports generate correctly

## Post-Deployment Security Checklist

### Password Security
- [ ] Changed Super Admin password
- [ ] Changed Admin password
- [ ] Changed Manager password
- [ ] Changed all Cashier passwords
- [ ] Passwords are strong and unique

### Configuration Security
- [ ] Company profile updated with real information
- [ ] Currency settings configured correctly
- [ ] Tax rates set appropriately
- [ ] Default settings reviewed and customized

### Access Control Verification
- [ ] Super Admin can manage all users
- [ ] Admin cannot edit Super Admin
- [ ] Cashiers restricted to assigned stores
- [ ] Store-specific product access working
- [ ] User roles functioning correctly

## Production Readiness Checklist

### Performance
- [ ] Database plan appropriate for expected load
- [ ] Web service plan sufficient for traffic
- [ ] `WEB_CONCURRENCY` optimized
- [ ] Database connection pooling configured

### Monitoring
- [ ] Render alerts configured for downtime
- [ ] Log monitoring set up
- [ ] Database backup schedule enabled
- [ ] Error tracking configured

### Backups
- [ ] Database automatic backups enabled
- [ ] Backup retention period set (7-30 days recommended)
- [ ] Backup restoration tested (if critical)

### Domain & SSL
- [ ] Custom domain configured (if using)
- [ ] SSL certificate automatically provisioned
- [ ] HTTPS redirect enabled
- [ ] Domain DNS configured correctly

## Troubleshooting Checklist

### Common Issues to Check
- [ ] Database connection string format correct
- [ ] All environment variables properly set
- [ ] Build logs reviewed for dependency issues
- [ ] Application logs checked for runtime errors
- [ ] Database connectivity verified
- [ ] Service region matches database region

### Migration Issues
- [ ] Migration logs reviewed for SQL errors
- [ ] Database permissions verified
- [ ] Foreign key constraints checked
- [ ] Missing columns or tables identified
- [ ] Transaction rollback issues resolved

### Access Issues
- [ ] User accounts created successfully
- [ ] Password hashing working correctly
- [ ] Store assignments properly configured
- [ ] Role permissions functioning
- [ ] Session management operational

## Go-Live Checklist

### Final Verification
- [ ] All tests passed
- [ ] Security review completed
- [ ] Performance acceptable
- [ ] Backup system operational
- [ ] Monitoring active

### User Training
- [ ] Admin training completed
- [ ] Cashier training completed
- [ ] Manager training completed
- [ ] Documentation provided to users
- [ ] Support contact information shared

### Business Operations
- [ ] Company information configured
- [ ] Product catalog imported
- [ ] Customer database migrated
- [ ] Store locations configured
- [ ] Staff accounts created and trained

## Post-Launch Maintenance

### Regular Tasks
- [ ] Monitor application performance
- [ ] Review error logs weekly
- [ ] Check database usage monthly
- [ ] Update user passwords quarterly
- [ ] Review user access permissions quarterly

### Updates and Upgrades
- [ ] Plan for code updates
- [ ] Database upgrade strategy
- [ ] Service plan evaluation
- [ ] Security patch schedule

---

## Quick Reference

**Render Dashboard**: https://dashboard.render.com
**Application URL**: https://your-service-name.onrender.com
**Database Console**: Available in Render dashboard
**Support**: Render documentation and support

**Default Credentials** (Change immediately):
- Super Admin: superadmin / super123
- Admin: admin / admin123
- Manager: manager1 / manager123
- Cashier (Main): casava / cashier123
- Cashier (Fashion): julisunkan / cashier123