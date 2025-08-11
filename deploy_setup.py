#!/usr/bin/env python3
"""
Pre-deployment setup script for Cloud POS & Inventory Manager
Ensures all data is migrated and system is ready for deployment
"""

import os
import sys
import subprocess

def run_migration():
    """Run the deployment migration script"""
    try:
        print("Running deployment migration...")
        result = subprocess.run([sys.executable, 'migrations/simple_deploy_migration.py'], 
                              capture_output=True, text=True)
        
        if result.returncode == 0:
            print(result.stdout)
            return True
        else:
            print(f"Migration failed: {result.stderr}")
            # Try fallback
            print("Attempting fallback migration...")
            try:
                result = subprocess.run([sys.executable, 'seed_data.py'], 
                                      capture_output=True, text=True)
                if result.returncode == 0:
                    print("Fallback seed data completed successfully!")
                    return True
                else:
                    print(f"Fallback also failed: {result.stderr}")
                    return False
            except:
                return False
    except Exception as e:
        print(f"Error running migration: {e}")
        return False

def main():
    """Main deployment setup function"""
    print("🌟 Cloud POS & Inventory Manager - Deployment Setup")
    print("=" * 50)
    
    # Run data migration
    if run_migration():
        print("✅ Deployment setup completed successfully!")
        return 0
    else:
        print("❌ Deployment setup failed!")
        return 1

if __name__ == '__main__':
    sys.exit(main())