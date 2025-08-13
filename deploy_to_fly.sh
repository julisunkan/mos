#!/bin/bash

# Fly.io Deployment Script for Cloud POS Inventory System

set -e

echo "🚀 Starting Fly.io deployment for Cloud POS Inventory System"

# Check if flyctl is installed
if ! command -v flyctl &> /dev/null; then
    echo "❌ flyctl is not installed. Please install it first:"
    echo "   curl -L https://fly.io/install.sh | sh"
    exit 1
fi

# Check if user is logged in
if ! flyctl auth whoami &> /dev/null; then
    echo "🔐 Please log in to Fly.io first:"
    echo "   flyctl auth login"
    exit 1
fi

# Generate session secret
SESSION_SECRET=$(openssl rand -base64 32)

echo "📝 Setting up application configuration..."

# Set secrets
echo "🔒 Setting application secrets..."
flyctl secrets set SESSION_SECRET="$SESSION_SECRET" --app cloudpos-inventory

echo "🗄️  Creating PostgreSQL database..."

# Check if database already exists
if flyctl postgres list | grep -q "cloudpos-db"; then
    echo "ℹ️  Database 'cloudpos-db' already exists"
else
    echo "📊 Creating new PostgreSQL database..."
    flyctl postgres create --name cloudpos-db --region ord --vm-size shared-cpu-1x --volume-size 3
fi

# Attach database to app
echo "🔗 Attaching database to application..."
flyctl postgres attach --app cloudpos-inventory cloudpos-db

# Deploy application
echo "🚢 Deploying application..."
flyctl deploy --app cloudpos-inventory

# Wait for deployment
echo "⏳ Waiting for deployment to complete..."
sleep 10

# Check app status
echo "📊 Checking application status..."
flyctl status --app cloudpos-inventory

# Show connection information
echo ""
echo "✅ Deployment completed successfully!"
echo ""
echo "🌐 Your Cloud POS application is now available at:"
flyctl info --app cloudpos-inventory | grep "Hostname" | awk '{print "   https://" $2}'
echo ""
echo "📝 Default login credentials (CHANGE THESE AFTER FIRST LOGIN):"
echo "   Super Admin - Username: superadmin, Password: super123"
echo "   Admin - Username: admin, Password: admin123"
echo "   Cashier (Main) - Username: casava, Password: cashier123"
echo "   Cashier (Fashion) - Username: julisunkan, Password: cashier123"
echo "   Manager - Username: manager1, Password: manager123"
echo ""
echo "🔧 Useful commands:"
echo "   flyctl logs --app cloudpos-inventory          # View logs"
echo "   flyctl ssh console --app cloudpos-inventory   # Access shell"
echo "   flyctl open --app cloudpos-inventory          # Open in browser"
echo "   flyctl status --app cloudpos-inventory        # Check status"
echo ""
echo "🔒 Security reminder: Please change all default passwords after your first login!"