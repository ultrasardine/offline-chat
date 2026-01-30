#!/bin/bash
# Script to add SQLcl to PATH for macOS

echo "Checking for SQLcl installation..."

# Check for Apple Silicon path
if [ -d "/opt/homebrew/Caskroom/sqlcl" ]; then
    SQLCL_VERSION=$(ls /opt/homebrew/Caskroom/sqlcl | tail -1)
    SQLCL_PATH="/opt/homebrew/Caskroom/sqlcl/$SQLCL_VERSION/sqlcl/bin"
    echo "✓ Found SQLcl at: $SQLCL_PATH"
# Check for Intel Mac path
elif [ -d "/usr/local/Caskroom/sqlcl" ]; then
    SQLCL_VERSION=$(ls /usr/local/Caskroom/sqlcl | tail -1)
    SQLCL_PATH="/usr/local/Caskroom/sqlcl/$SQLCL_VERSION/sqlcl/bin"
    echo "✓ Found SQLcl at: $SQLCL_PATH"
else
    echo "✗ SQLcl not found. Please install it with: brew install sqlcl"
    exit 1
fi

# Check if already in PATH
if command -v sql &> /dev/null; then
    echo "✓ SQLcl is already in your PATH"
    sql -version
    exit 0
fi

# Add to .zshrc
echo ""
echo "Adding SQLcl to your PATH..."
echo "export PATH=\"$SQLCL_PATH:\$PATH\"" >> ~/.zshrc

echo "✓ Added to ~/.zshrc"
echo ""
echo "To apply the changes, run:"
echo "  source ~/.zshrc"
echo ""
echo "Or restart your terminal."
