"""
Example usage of Mcp Server Bridge.

This file must run and exit cleanly with no user input, no network calls,
and no external services or API keys. Use fake/hardcoded data to demonstrate the API.
The widget's own declared dependencies are fine - the validator installs them first.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from src.mcp_server_bridge import mcp_server_bridge

# [TODO] Replace with a realistic call using fake data
result = mcp_server_bridge("hello")
print(f"Result: {result}")
