#!/usr/bin/env python3
"""
MySQL Setup and Migration Script for PythonAnywhere
"""

import os
import pymysql
import logging
from sqlalchemy import create_engine, text

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_mysql_database():
    """Create MySQL database if it doesn't exist"""
    try:
        # MySQL connection parameters
        mysql_user = os.environ.get("MYSQL_USER", "root")
        mysql_password = os.environ.get("MYSQL_PASSWORD", "")
        mysql_host = os.environ.get("MYSQL_HOST", "localhost")
        mysql_db = os.environ.get("MYSQL_DATABASE", "cloudpos")
        
        # Connect to MySQL server (without database)
        connection = pymysql.connect(
            host=mysql_host,
            user=mysql_user,
            password=mysql_password,
            charset='utf8mb4'
        )
        
        with connection.cursor() as cursor:
            # Create database if it doesn't exist
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{mysql_db}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
            logger.info(f"✅ Database '{mysql_db}' created or already exists")
            
        connection.close()
        return True
        
    except Exception as e:
        logger.error(f"❌ Error creating database: {e}")
        return False

def test_connection():
    """Test MySQL connection"""
    try:
        # Build connection URL
        mysql_user = os.environ.get("MYSQL_USER", "root")
        mysql_password = os.environ.get("MYSQL_PASSWORD", "")
        mysql_host = os.environ.get("MYSQL_HOST", "localhost")
        mysql_db = os.environ.get("MYSQL_DATABASE", "cloudpos")
        
        database_url = f"mysql+pymysql://{mysql_user}:{mysql_password}@{mysql_host}/{mysql_db}"
        
        # Create engine and test connection
        engine = create_engine(database_url)
        with engine.connect() as conn:
            result = conn.execute(text("SELECT VERSION()"))
            version = result.fetchone()[0]
            logger.info(f"✅ MySQL connection successful! Version: {version}")
            return True
            
    except Exception as e:
        logger.error(f"❌ MySQL connection failed: {e}")
        return False

def migrate_to_mysql():
    """Run migration from PostgreSQL to MySQL"""
    logger.info("🚀 Starting PostgreSQL to MySQL migration...")
    
    # Step 1: Create MySQL database
    if not create_mysql_database():
        return False
    
    # Step 2: Test connection
    if not test_connection():
        return False
    
    # Step 3: Import app and create tables
    try:
        from app import app, db
        
        with app.app_context():
            # Drop all existing tables to start fresh
            db.drop_all()
            logger.info("🗑️  Dropped all existing tables")
            
            # Create all tables with MySQL-compatible schema
            db.create_all()
            logger.info("✅ Created all tables with MySQL schema")
            
            # Run data migration
            from migrations.simple_deploy_migration import ensure_data_exists
            ensure_data_exists()
            logger.info("✅ Data migration completed")
            
        logger.info("🎉 PostgreSQL to MySQL migration completed successfully!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        return False

if __name__ == "__main__":
    print("MySQL Setup and Migration for PythonAnywhere")
    print("=" * 50)
    
    # Check environment variables
    required_vars = ["MYSQL_USER", "MYSQL_PASSWORD", "MYSQL_HOST", "MYSQL_DATABASE"]
    missing_vars = [var for var in required_vars if not os.environ.get(var)]
    
    if missing_vars:
        print(f"⚠️  Missing environment variables: {', '.join(missing_vars)}")
        print("Using default values for development...")
    
    # Run migration
    if migrate_to_mysql():
        print("\n🎉 Migration completed successfully!")
        print("Your Cloud POS system is now ready for MySQL/PythonAnywhere!")
    else:
        print("\n❌ Migration failed. Please check the logs above.")