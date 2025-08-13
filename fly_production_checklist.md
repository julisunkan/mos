# Fly.io Production Deployment Checklist

## Pre-Deployment Setup

### 1. Install Fly.io CLI
```bash
curl -L https://fly.io/install.sh | sh
flyctl auth login
```

### 2. Initialize Application
```bash
flyctl launch --name cloudpos-inventory --region ord --no-deploy
```

### 3. Configure Secrets
```bash
# Generate and set session secret
flyctl secrets set SESSION_SECRET=$(openssl rand -base64 32)
```

### 4. Create PostgreSQL Database
```bash
# Create database cluster
flyctl postgres create --name cloudpos-db --region ord --vm-size shared-cpu-1x

# Attach to application
flyctl postgres attach --app cloudpos-inventory cloudpos-db
```

## Deployment Process

### 5. Deploy Application
```bash
flyctl deploy
```

### 6. Verify Deployment
```bash
# Check status
flyctl status

# View logs
flyctl logs

# Open application
flyctl open
```

## Post-Deployment Configuration

### 7. Initial Login and Security
1. Access the application URL
2. Login with default credentials:
   - Super Admin: `superadmin` / `super123`
   - Admin: `admin` / `admin123`
   - Manager: `manager1` / `manager123`
   - Cashier (Main): `casava` / `cashier123`
   - Cashier (Fashion): `julisunkan` / `cashier123`

3. **IMMEDIATELY** change all default passwords

### 8. System Configuration
1. Update company information
2. Configure store details
3. Add inventory products
4. Set up customer data
5. Configure user roles and permissions

### 9. Testing
- [ ] User authentication works
- [ ] POS system functions properly
- [ ] Inventory management operates correctly
- [ ] Reports generate successfully
- [ ] Customer management works
- [ ] Store operations function

### 10. Production Monitoring
```bash
# Monitor application
flyctl dashboard

# Scale if needed
flyctl scale count 2

# View metrics
flyctl logs --app cloudpos-inventory
```

## Environment Variables (Auto-configured)

- `DATABASE_URL` - PostgreSQL connection (set by Fly.io)
- `SESSION_SECRET` - Application secret key
- `FLASK_ENV` - Set to "production"
- `PORT` - Set to 8080

## File Structure for Deployment

```
cloudpos-inventory/
├── fly.toml                 # Fly.io configuration
├── Dockerfile              # Container configuration
├── .dockerignore           # Docker ignore rules
├── production_app.py       # Production application entry
├── app.py                  # Development application
├── main.py                 # Application entry point
├── models.py               # Database models
├── utils.py                # Utility functions
├── blueprints/             # Application modules
├── templates/              # HTML templates
├── static/                 # Static assets
└── migrations/             # Database migrations
```

## Troubleshooting

### Database Issues
```bash
# Check database status
flyctl postgres list

# Connect to database
flyctl postgres connect --app cloudpos-db

# View database logs
flyctl logs --app cloudpos-db
```

### Application Issues
```bash
# View application logs
flyctl logs --app cloudpos-inventory

# SSH into application
flyctl ssh console --app cloudpos-inventory

# Restart application
flyctl restart --app cloudpos-inventory
```

### Performance Issues
```bash
# Scale application
flyctl scale count 2 --app cloudpos-inventory

# Monitor resource usage
flyctl dashboard --app cloudpos-inventory
```

## Security Best Practices

1. **Change Default Passwords**: First priority after deployment
2. **Regular Backups**: Set up automatic database backups
3. **SSL/TLS**: Enabled automatically by Fly.io
4. **Environment Variables**: Never commit secrets to version control
5. **User Management**: Regularly review user permissions
6. **Updates**: Keep application dependencies updated

## Support Resources

- [Fly.io Documentation](https://fly.io/docs/)
- [PostgreSQL on Fly.io](https://fly.io/docs/postgres/)
- [Flask Deployment Guide](https://flask.palletsprojects.com/en/2.3.x/deploying/)