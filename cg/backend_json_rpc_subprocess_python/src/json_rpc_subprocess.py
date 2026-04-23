import json
import subprocess
from typing import Any, Dict, List, Optional


def run_json_cli(cmd: List[str], env: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    """Execute a CLI command and parse its stdout as JSON.
    
    Returns the parsed JSON on success.
    If the process exits with non-zero OR stdout is not valid JSON,
    returns a dict with {"status": "error", "message": ...}.
    """
    try:
        process = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False,
            env=env
        )
        
        # Try to parse stdout as JSON
        try:
            if not process.stdout.strip():
                if process.returncode != 0:
                    return {"status": "error", "message": process.stderr.strip() or f"Process exited with {process.returncode}"}
                return {"status": "success", "message": "No output"}
                
            return json.loads(process.stdout)
        except json.JSONDecodeError:
            if process.returncode != 0:
                return {"status": "error", "message": process.stderr.strip() or process.stdout.strip()}
            return {"status": "error", "message": f"Output is not valid JSON: {process.stdout[:100]}..."}
            
    except Exception as e:
        return {"status": "error", "message": str(e)}
