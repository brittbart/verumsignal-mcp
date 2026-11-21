"""Entry point for the Verum Signal MCP bundle (.mcpb).

The bundle carries its own copy of the verumsignal_mcp package next to this file;
it goes first on the import path so an older pip-installed copy is never used instead.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from verumsignal_mcp.server import main  # noqa: E402

if __name__ == "__main__":
    main()
