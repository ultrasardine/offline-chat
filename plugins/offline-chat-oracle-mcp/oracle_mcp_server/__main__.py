"""Entry point for running oracle_mcp_server as a module.

Usage:
    python -m oracle_mcp_server
"""

import asyncio
from oracle_mcp_server.server import main

if __name__ == "__main__":
    asyncio.run(main())
