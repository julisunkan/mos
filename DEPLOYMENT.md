# Deployment Guide for Cloud POS & Inventory Manager

## Deploy to Render

This application is optimized for deployment on [Render](https://render.com) with the following configuration:

### Prerequisites
- GitHub account with this repository
- Render account (free tier supported)

### Deployment Steps

1. **Fork/Clone Repository**
   - Fork this repository to your GitHub account
   - Or clone and push to your own repository

2. **Create Render Account**
   - Sign up at [render.com](https://render.com)
   - Connect your GitHub account

3. **Deploy Database**
   - Go to Render Dashboard
   - Click "New +" → "PostgreSQL"
   - Configure:
     - Name: `cloudpos-db`
     - Database: `cloudpos`
     - User: `cloudpos_user` 
     - Plan: Free (or paid for production)
   - Click "Create Database"
   - **Save the connection details** for the next step

4. **Deploy Web Service**
   - Click "New +" → "Web Service"
   - Connect your repository
   - Configure:
     - **Name**: `cloudpos-inventory-manager`
     - **Environment**: Python 3
     - **Build Command**: `./build.sh`
     - **Start Command**: `gunicorn -c gunicorn.conf.py main:app`
     - **Plan**: Free (or paid for production)

5. **Set Environment Variables**
   - In the web service settings, add:
     - `DATABASE_URL`: Copy from PostgreSQL service
     - `SESSION_SECRET`: Generate a random string (Render can auto-generate)
     - `FLASK_ENV`: `production`
     - `PYTHONPATH`: `.`

6. **Deploy**
   - Click "Create Web Service"
   - Render will automatically build and deploy
   - Initial deployment takes 5-10 minutes

### Post-Deployment Setup

1. **Initialize Database**
   - The build script automatically creates tables
   - Seed data is created on first run

2. **First Login**
   - Username: `admin`
   - Password: `admin123`
   - **Change password immediately after first login**

3. **Configure Company Settings**
   - Go to Admin → Settings
   - Update company profile, currency, tax rates
   - Upload company logo if needed

### Environment Variables Reference

| Variable | Description | Example |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://user:pass@host:port/db` |
| `SESSION_SECRET` | Flask session secret key | Random 32+ character string |
| `FLASK_ENV` | Application environment | `production` |
| `PYTHONPATH` | Python module path | `.` |

### File Structure for Deployment

```
├── render.yaml         # Render service configuration
├── Procfile           # Alternative process file
├── build.sh           # Build script
├── gunicorn.conf.py   # Gunicorn configuration
├── runtime.txt        # Python version
├── pyproject.toml     # Dependencies
├── main.py            # Application entry point
└── README.md          # Documentation
```

### Production Configuration

The application automatically configures for production when `FLASK_ENV=production`:

- **Debug mode**: Disabled
- **Logging**: INFO level
- **Database**: Connection pooling enabled
- **Security**: CSRF protection, secure sessions
- **Performance**: Gunicorn with multiple workers

### Monitoring and Logs

- **Render Logs**: Available in Render dashboard
- **Application Logs**: Structured logging to stdout
- **Health Check**: Automatic via Render
- **Metrics**: Basic metrics available in Render

### Scaling

For production use, consider upgrading:

- **Database**: Paid PostgreSQL plan for better performance
- **Web Service**: Paid plan for more resources
- **Workers**: Increase gunicorn workers for higher traffic

### Security Considerations

- Change default admin password
- Use strong SESSION_SECRET
- Enable SSL/HTTPS (automatic on Render)
- Regular database backups
- Monitor access logs

### Troubleshooting

**Build Fails:**
- Check build logs in Render dashboard
- Ensure all dependencies in pyproject.toml
- Verify Python version compatibility

**Database Connection Issues:**
- Verify DATABASE_URL is correct
- Check PostgreSQL service status
- Ensure database is in same region

**Application Won't Start:**
- Check start command configuration
- Verify gunicorn.conf.py settings
- Review application logs

### Support

For deployment issues:
1. Check Render documentation
2. Review application logs
3. Verify environment variables
4. Test locally first

### Estimated Costs (Render Free Tier)

- **Web Service**: Free (with limitations)
- **PostgreSQL**: Free (500MB storage)
- **Total**: $0/month

For production workloads, paid plans recommended starting at $7/month for web service and $7/month for database.