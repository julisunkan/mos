#!/bin/bash

# PostgreSQL startup script for Replit
export PGDATA="/tmp/postgres_data"
export PGPORT="5433"  # Use different port to avoid conflicts

# Clean up any existing data
rm -rf $PGDATA
mkdir -p $PGDATA

# Initialize database
initdb -D $PGDATA --auth-local=trust --auth-host=md5

# Configure PostgreSQL
cat >> $PGDATA/postgresql.conf << EOF
unix_socket_directories = '/tmp'
port = $PGPORT
listen_addresses = 'localhost'
max_connections = 20
shared_buffers = 32MB
EOF

# Start PostgreSQL
pg_ctl -D $PGDATA -l /tmp/postgres.log start

# Wait for startup
sleep 3

# Create database and user
createdb -p $PGPORT cloudpos
psql -p $PGPORT -d cloudpos -c "CREATE USER cloudpos_user WITH PASSWORD 'cloudpos_pass';"
psql -p $PGPORT -d cloudpos -c "GRANT ALL PRIVILEGES ON DATABASE cloudpos TO cloudpos_user;"
psql -p $PGPORT -d cloudpos -c "GRANT ALL ON SCHEMA public TO cloudpos_user;"

echo "PostgreSQL setup complete on port $PGPORT"