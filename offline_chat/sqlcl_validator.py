"""SQLcl installation validator for Oracle database connections.

This module provides utilities to check if SQLcl is installed and provide
platform-specific installation instructions.
"""

import platform
import shutil
import subprocess
from typing import Tuple


def get_sqlcl_path() -> str | None:
    """Get the path to the SQLcl executable.

    Returns:
        Path to sql executable if found, None otherwise.
    """
    # First check if it's in PATH
    path = shutil.which("sql")
    if path:
        return path

    # Check common Homebrew installation paths (macOS)
    import glob
    import os

    homebrew_paths = [
        "/opt/homebrew/Caskroom/sqlcl/*/sqlcl/bin/sql",  # Apple Silicon
        "/usr/local/Caskroom/sqlcl/*/sqlcl/bin/sql",  # Intel Mac
    ]

    for pattern in homebrew_paths:
        matches = glob.glob(pattern)
        if matches and os.path.isfile(matches[0]):
            return matches[0]

    return None


def is_sqlcl_installed() -> bool:
    """Check if SQLcl is installed and available in PATH.

    Returns:
        True if SQLcl is installed, False otherwise.
    """
    return get_sqlcl_path() is not None


def is_sqlcl_in_path() -> bool:
    """Check if SQLcl is in the system PATH.

    Returns:
        True if SQLcl is in PATH, False otherwise.
    """
    return shutil.which("sql") is not None


def get_sqlcl_version() -> str | None:
    """Get the installed SQLcl version.

    Returns:
        Version string if SQLcl is installed, None otherwise.
    """
    if not is_sqlcl_installed():
        return None

    try:
        result = subprocess.run(
            ["sql", "-version"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            # Parse version from output (e.g., "SQLcl: Release 25.2 Production")
            output = result.stdout.strip()
            if "Release" in output:
                return output.split("Release")[1].split()[0].strip()
        return "unknown"
    except (subprocess.TimeoutExpired, FileNotFoundError, Exception):
        return None


def get_installation_instructions() -> Tuple[str, str]:
    """Get platform-specific SQLcl installation instructions.

    Returns:
        Tuple of (platform_name, installation_instructions).
    """
    from offline_chat.sqlcl_validator import get_sqlcl_path, is_sqlcl_in_path
    import os

    system = platform.system()

    # Check if SQLcl is installed but not in PATH
    sqlcl_path = get_sqlcl_path()
    not_in_path = sqlcl_path and not is_sqlcl_in_path()

    if system == "Darwin":  # macOS
        instructions = """
SQLcl Installation Instructions for macOS:
"""
        
        if not_in_path:
            # SQLcl is installed but not in PATH - provide quick fix
            sqlcl_dir = os.path.dirname(sqlcl_path)
            instructions += f"""
✓ SQLcl is already installed at: {sqlcl_path}

⚠️  However, it's not in your PATH. To fix this immediately:

Quick Fix (run this command in your terminal):
  echo 'export PATH="{sqlcl_dir}:$PATH"' >> ~/.zshrc && source ~/.zshrc

Then restart this application.

"""
        else:
            instructions += """
Option 1: Using Homebrew (Recommended)
  1. Install Homebrew if not already installed:
     /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

  2. Install SQLcl:
     brew install sqlcl

  3. Add SQLcl to your PATH (IMPORTANT):
     For Apple Silicon (M1/M2/M3):
       echo 'export PATH="/opt/homebrew/Caskroom/sqlcl/$(ls /opt/homebrew/Caskroom/sqlcl | tail -1)/sqlcl/bin:$PATH"' >> ~/.zshrc
       source ~/.zshrc

     For Intel Mac:
       echo 'export PATH="/usr/local/Caskroom/sqlcl/$(ls /usr/local/Caskroom/sqlcl | tail -1)/sqlcl/bin:$PATH"' >> ~/.zshrc
       source ~/.zshrc

  4. Verify installation:
     sql -version

Option 2: Manual Installation
  1. Download SQLcl from Oracle:
     https://www.oracle.com/database/sqldeveloper/technologies/sqlcl/download/

  2. Extract the archive and add the bin directory to your PATH:
     export PATH="/path/to/sqlcl/bin:$PATH"

  3. Add the export line to your ~/.zshrc or ~/.bash_profile to make it permanent

Note: SQLcl requires Java 11 or higher. Install with:
  brew install openjdk@11
"""
        
        return ("macOS", instructions)

    elif system == "Linux":
        return (
            "Linux",
            """
SQLcl Installation Instructions for Linux:

Option 1: Using Homebrew (if installed)
  1. Install Homebrew for Linux:
     /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

  2. Install SQLcl:
     brew install sqlcl

  3. Verify installation:
     sql -version

Option 2: Manual Installation
  1. Download SQLcl from Oracle:
     https://www.oracle.com/database/sqldeveloper/technologies/sqlcl/download/

  2. Extract the archive:
     unzip sqlcl-*.zip

  3. Add to PATH in ~/.bashrc or ~/.zshrc:
     export PATH="/path/to/sqlcl/bin:$PATH"

  4. Reload your shell configuration:
     source ~/.bashrc

Note: SQLcl requires Java 11 or higher. Install with:
  sudo apt-get install openjdk-11-jdk  # Debian/Ubuntu
  sudo yum install java-11-openjdk     # RHEL/CentOS
""",
        )

    elif system == "Windows":
        return (
            "Windows",
            """
SQLcl Installation Instructions for Windows:

Manual Installation:
  1. Download SQLcl from Oracle:
     https://www.oracle.com/database/sqldeveloper/technologies/sqlcl/download/

  2. Extract the ZIP file to a location (e.g., C:\\sqlcl)

  3. Add the bin directory to your PATH:
     - Open System Properties > Environment Variables
     - Edit the PATH variable
     - Add: C:\\sqlcl\\bin

  4. Open a new Command Prompt and verify:
     sql -version

Note: SQLcl requires Java 11 or higher. Download from:
  https://www.oracle.com/java/technologies/downloads/
""",
        )

    else:
        return (
            system,
            """
SQLcl Installation Instructions:

Please download SQLcl from Oracle:
  https://www.oracle.com/database/sqldeveloper/technologies/sqlcl/download/

Extract the archive and add the bin directory to your system PATH.

SQLcl requires Java 11 or higher.
""",
        )


def validate_sqlcl_or_raise() -> None:
    """Validate that SQLcl is installed, raise error with instructions if not.

    Raises:
        RuntimeError: If SQLcl is not installed, with installation instructions.
    """
    if not is_sqlcl_installed():
        platform_name, instructions = get_installation_instructions()
        raise RuntimeError(
            f"SQLcl is not installed or not in PATH.\n\n"
            f"Oracle database connections require SQLcl (SQL Developer Command Line).\n"
            f"{instructions}\n"
            f"After installation, restart your terminal and try again."
        )


def get_sqlcl_status() -> str:
    """Get a formatted status message about SQLcl installation.

    Returns:
        Status message string.
    """
    if is_sqlcl_installed():
        version = get_sqlcl_version()
        if version:
            return f"✓ SQLcl is installed (version {version})"
        return "✓ SQLcl is installed"
    else:
        return "✗ SQLcl is not installed"
