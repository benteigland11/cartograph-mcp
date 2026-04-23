import json
import os
import sys
import unittest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from src.json_rpc_subprocess import run_json_cli


class TestJsonRpcSubprocess(unittest.TestCase):
    @patch("subprocess.run")
    def test_run_json_cli_success(self, mock_run):
        mock_run.return_value = MagicMock(
            stdout='{"status": "ok", "data": [1, 2]}',
            stderr="",
            returncode=0
        )
        
        result = run_json_cli(["test-cli", "do-something"])
        self.assertEqual(result, {"status": "ok", "data": [1, 2]})
        
    @patch("subprocess.run")
    def test_run_json_cli_error_exit(self, mock_run):
        mock_run.return_value = MagicMock(
            stdout="",
            stderr="Permission denied",
            returncode=1
        )
        
        result = run_json_cli(["test-cli", "do-something"])
        self.assertEqual(result["status"], "error")
        self.assertIn("Permission denied", result["message"])

    @patch("subprocess.run")
    def test_run_json_cli_empty_success(self, mock_run):
        mock_run.return_value = MagicMock(
            stdout="  ",
            stderr="",
            returncode=0
        )
        
        result = run_json_cli(["test-cli", "do-something"])
        self.assertEqual(result["status"], "success")

    @patch("subprocess.run")
    def test_run_json_cli_invalid_json(self, mock_run):
        mock_run.return_value = MagicMock(
            stdout="Some human readable text",
            stderr="",
            returncode=0
        )
        
        result = run_json_cli(["test-cli", "do-something"])
        self.assertEqual(result["status"], "error")
        self.assertIn("not valid JSON", result["message"])

    @patch("subprocess.run")
    def test_run_json_cli_invalid_json_with_error_code(self, mock_run):
        mock_run.return_value = MagicMock(
            stdout="Malformed output",
            stderr="System error",
            returncode=1
        )
        
        result = run_json_cli(["test-cli", "do-something"])
        self.assertEqual(result["status"], "error")
        self.assertEqual(result["message"], "System error")

    @patch("subprocess.run")
    def test_run_json_cli_exception(self, mock_run):
        mock_run.side_effect = Exception("Spawn failed")
        
        result = run_json_cli(["test-cli", "do-something"])
        self.assertEqual(result["status"], "error")
        self.assertEqual(result["message"], "Spawn failed")

if __name__ == "__main__":
    unittest.main()
