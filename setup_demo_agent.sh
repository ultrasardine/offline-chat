#!/bin/bash
# Quick setup script for demo sales analyst agent

set -e

echo "=================================="
echo "Sales Analyst Agent Setup"
echo "=================================="
echo ""

# Get absolute path to database
DB_PATH="$(pwd)/sample_company.db"

# Check if database exists
if [ ! -f "$DB_PATH" ]; then
    echo "Error: sample_company.db not found!"
    echo "Run: uv run python create_sample_db.py"
    exit 1
fi

echo "✓ Found database at: $DB_PATH"
echo ""

# Check if connection already exists
CONNECTION_FILE="$HOME/.offline-chat/database_connections.json"
if [ -f "$CONNECTION_FILE" ]; then
    if grep -q "company-sales-db" "$CONNECTION_FILE"; then
        echo "✓ Database connection 'company-sales-db' already exists"
    else
        echo "Note: Connection file exists but 'company-sales-db' not found"
        echo "You'll need to create it manually via the CLI"
    fi
else
    echo "Note: No connections configured yet"
    echo "You'll need to create the connection via the CLI"
fi

echo ""
echo "=================================="
echo "Next Steps:"
echo "=================================="
echo ""
echo "1. Run the application:"
echo "   make run"
echo ""
echo "2. Create database connection (if not exists):"
echo "   - Select: 7. Manage database connections"
echo "   - Select: 1. Create new connection"
echo "   - Name: company-sales-db"
echo "   - Type: sqlite"
echo "   - Path: $DB_PATH"
echo ""
echo "3. Create sales analyst agent:"
echo "   - Select: 1. Create new agent"
echo "   - Name: sales-analyst"
echo "   - Display: Sales Data Analyst"
echo "   - Model: llama3:latest"
echo "   - Purpose: You are a sales data analyst..."
echo "   - Temperature: 0.3"
echo ""
echo "4. Assign database to agent:"
echo "   - Select: 6. Update agent"
echo "   - Select: sales-analyst"
echo "   - Select: 2. Update database connections"
echo "   - Select: 1. Assign connection"
echo "   - Select: company-sales-db"
echo "   - Access: 1. READ_ONLY"
echo ""
echo "5. Start chatting:"
echo "   - Select: 4. Chat with agent"
echo "   - Select: sales-analyst"
echo "   - Ask: What were our total sales last month?"
echo ""
echo "=================================="
echo "Database Path (copy this):"
echo "$DB_PATH"
echo "=================================="
