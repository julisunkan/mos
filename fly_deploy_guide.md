# Fly.io Deployment Guide for Cloud POS Inventory System

## Prerequisites

1. Install Fly.io CLI: https://fly.io/docs/hands-on/install-flyctl/
2. Create Fly.io account: `flyctl auth signup`

## Deployment Steps

### 1. Initialize and Configure App

```bash
# Login to Fly.io
flyctl auth login

# Launch the app (this creates the app and fly.toml)
flyctl launch --name cloudpos-inventory --region ord --no-deploy

# Set secrets
flyctl secrets set SESSION_SECRET=$(openssl rand -base64 32)
```

### 2. Create PostgreSQL Database

```bash
# Create PostgreSQL cluster
flyctl postgres create --name cloudpos-db --region ord

# Get connection string
flyctl postgres connect --app cloudpos-db

# Attach database to your app
flyctl postgres attach --app cloudpos-inventory cloudpos-db
```

### 3. Deploy Application

```bash
# Deploy the application
flyctl deploy

# Check deployment status
flyctl status

# View logs
flyctl logs

# Open the app
flyctl open
```

### 4. Database Setup (if needed)

```bash
# Connect to your app's shell
flyctl ssh console

# Run database migrations if needed
python -c "from production_app import app, db; app.app_context().push(); db.create_all()"
```

### 5. Environment Variables

The following environment variables are automatically set by Fly.io:

- `DATABASE_URL` - PostgreSQL connection string (set by `flyctl postgres attach`)
- `SESSION_SECRET` - Set manually via `flyctl secrets set`
- `FLASK_ENV` - Set to "production" in fly.toml
- `PORT` - Set to 8080 in fly.toml

### 6. Monitoring and Maintenance

```bash
# View app status
flyctl status

# Scale the app
flyctl scale count 2

# View metrics
flyctl dashboard

# Update secrets
flyctl secrets set SESSION_SECRET=new_secret_key

# View database information
flyctl postgres list
```

### 7. Custom Domain (Optional)

```bash
# Add custom domain
flyctl certs add yourdomain.com

# Check certificate status
flyctl certs check yourdomain.com
```

## Important Notes

1. **Default Login Credentials** (change after first login):
   - Super Admin: username 'superadmin', password 'super123'
   - Admin: username 'admin', password 'admin123'
   - Cashier (Main): username 'casava', password 'cashier123'
   - Cashier (Fashion): username 'julisunkan', password 'cashier123'
   - Manager: username 'manager1', password 'manager123'

2. **Security**: Remember to change default passwords after deployment
3. **Database**: PostgreSQL will be automatically provisioned and connected
4. **SSL**: Fly.io provides automatic SSL certificates
5. **Scaling**: The app is configured to auto-start and auto-stop machines based on traffic

## Troubleshooting

### App won't start
```bash
flyctl logs
```

### Database connection issues
```bash
flyctl postgres list
flyctl postgres connect --app cloudpos-db
```

### Health check failures
Check `/health` endpoint and ensure the app responds on port 8080

### View app logs
```bash
flyctl logs --app cloudpos-inventory
```