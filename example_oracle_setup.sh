#!/bin/bash
# Example: Securely configure Oracle database connection for an agent
#
# Usage:
#   1. Set environment variables with your credentials
#   2. Run this script
#
# This approach keeps credentials out of version control and code.

# Set your database credentials (DO NOT commit these!)
export DB_HOST="main-prod.rds.prod.pt-kplus.aws.eos-ws.com"
export DB_PORT="1521"
export DB_SERVICE_NAME="KPPTPROD"
export DB_USERNAME="eos_prt"
export DB_PASSWORD="your-password-here"  # Replace with actual password

# Create connection and assign to agent
python update_to_custom_oracle_server.py \
    database-analyst \
    --connection kplus-prod \
    --access-level read-only \
    --create-connection

# Alternative: If connection already exists, just assign it
# python update_to_custom_oracle_server.py database-analyst --connection kplus-prod

# Unset credentials from environment
unset DB_HOST DB_PORT DB_SERVICE_NAME DB_USERNAME DB_PASSWORD
