#!/usr/bin/env python3
"""Run the Verum Signal MCP server from a clone of this repository.

Installed copies use the `verumsignal-mcp` command instead (pip install verumsignal-mcp).
The server itself lives in verumsignal_mcp/server.py.
"""
from verumsignal_mcp.server import main

if __name__ == "__main__":
    main()
