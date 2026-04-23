import json
import os
import sys
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from src.json_rpc_subprocess import run_json_cli

# Mocking subprocess for demonstration purposes
with patch("subprocess.run") as mock_run:
    mock_run.return_value = MagicMock(
        stdout='{"status": "success", "widgets": [{"id": "test-widget"}]}',
        stderr="",
        returncode=0
    )
    
    # In a real use case, you'd call a real CLI like:
    # result = run_json_cli(["cartograph", "search", "retry"])
    result = run_json_cli(["example-cli", "search", "retry"])
    
    print("Parsed JSON result from CLI:")
    print(json.dumps(result, indent=2))
