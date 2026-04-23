import json
import os
import shutil
import site
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from server import handle_call_tool


def _ensure_cartograph_available() -> None:
    try:
        subprocess.run(
            ["cartograph", "--help"],
            check=True,
            capture_output=True,
            text=True,
        )
    except (FileNotFoundError, subprocess.CalledProcessError) as exc:
        pytest.skip(f"cartograph CLI unavailable for integration tests: {exc}")


@pytest.fixture
def isolated_env(tmp_path, monkeypatch):
    _ensure_cartograph_available()

    home_dir = tmp_path / "home"
    config_dir = tmp_path / "xdg-config"
    data_dir = tmp_path / "xdg-data"
    cache_dir = tmp_path / "xdg-cache"
    library_dir = tmp_path / "widget-library"
    project_dir = tmp_path / "project"

    for path in [home_dir, config_dir, data_dir, cache_dir, library_dir, project_dir]:
        path.mkdir(parents=True, exist_ok=True)

    monkeypatch.setenv("HOME", str(home_dir))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(config_dir))
    monkeypatch.setenv("XDG_DATA_HOME", str(data_dir))
    monkeypatch.setenv("XDG_CACHE_HOME", str(cache_dir))
    monkeypatch.setenv("WIDGET_LIBRARY_PATH", str(library_dir))
    monkeypatch.setenv("PYTHONUSERBASE", site.getuserbase())
    monkeypatch.chdir(project_dir)

    return {
        "home_dir": home_dir,
        "config_dir": config_dir,
        "data_dir": data_dir,
        "cache_dir": cache_dir,
        "library_dir": library_dir,
        "project_dir": project_dir,
    }


async def _call_and_parse(tool_name: str, arguments: dict):
    result = await handle_call_tool(tool_name, arguments)
    assert len(result) == 1
    return json.loads(result[0].text)


def _find_created_widget_dir(project_dir: Path) -> Path:
    cg_dir = project_dir / "cg"
    matches = list(cg_dir.iterdir())
    assert len(matches) == 1
    return matches[0]


def _make_scaffold_valid(widget_dir: Path) -> None:
    widget_json_path = widget_dir / "widget.json"
    widget_data = json.loads(widget_json_path.read_text())
    widget_data["meta"]["tags"] = ["mcp", "smoke", "backend"]
    widget_data["description"] = "Integration smoke-test widget for the Cartograph MCP server."
    widget_json_path.write_text(json.dumps(widget_data, indent=2))

    example_path = widget_dir / "examples" / "example_usage.py"
    if example_path.exists():
        example_path.write_text(
            'import sys, os\n'
            "sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))\n"
            "from src.mcp_smoke import mcp_smoke\n\n"
            'result = mcp_smoke("hello")\n'
            'print(f"Result: {result}")\n'
        )

    test_path = widget_dir / "tests" / "test_mcp_smoke.py"
    if test_path.exists():
        test_path.write_text(
            "import sys, os\n"
            "sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))\n"
            "from src.mcp_smoke import mcp_smoke\n\n"
            "def test_mcp_smoke():\n"
            '    assert mcp_smoke("hello") == "hello"\n'
        )


@pytest.mark.asyncio
async def test_end_to_end_daily_workflow(isolated_env):
    project_dir = isolated_env["project_dir"]

    create_data = await _call_and_parse(
        "create_widget",
        {
            "name": "mcp-smoke",
            "domain": "backend",
            "language": "python",
            "display_name": "MCP Smoke",
        },
    )
    assert create_data["status"] == "success"

    created_widget_dir = _find_created_widget_dir(project_dir)
    _make_scaffold_valid(created_widget_dir)

    validate_data = await _call_and_parse(
        "validate_widget",
        {"path": str(created_widget_dir)},
    )
    assert validate_data["status"] == "success"

    checkin_data = await _call_and_parse(
        "checkin_widget",
        {"path": str(created_widget_dir), "reason": "initial mcp integration smoke"},
    )
    assert checkin_data["status"] == "success"

    search_data = await _call_and_parse(
        "registry_widget",
        {"action": "search", "query": "mcp-smoke"},
    )
    assert "widgets" in search_data
    assert any(widget["id"] == "backend-mcp-smoke-python" for widget in search_data["widgets"])

    inspect_data = await _call_and_parse(
        "registry_widget",
        {"action": "inspect", "widget_id": "backend-mcp-smoke-python"},
    )
    assert inspect_data["id"] == "backend-mcp-smoke-python"

    shutil.rmtree(created_widget_dir)

    status_before_install = await _call_and_parse("widget_status", {})
    assert "widgets" in status_before_install
    assert status_before_install["widgets"] == []

    install_data = await _call_and_parse(
        "registry_widget",
        {"action": "install", "widget_id": "backend-mcp-smoke-python"},
    )
    assert install_data["status"] == "success"

    installed_widget_dir = project_dir / "cg" / "backend_mcp_smoke_python"
    assert installed_widget_dir.is_dir()

    widget_status_data = await _call_and_parse(
        "widget_status",
        {"widget_dir": str(installed_widget_dir)},
    )
    assert widget_status_data["widget_id"] == "backend-mcp-smoke-python"

    upgrade_data = await _call_and_parse(
        "installed_widget",
        {"action": "upgrade", "widget_dir": str(installed_widget_dir)},
    )
    assert upgrade_data["status"] == "success"

    uninstall_data = await _call_and_parse(
        "installed_widget",
        {"action": "uninstall", "widget_dir": str(installed_widget_dir)},
    )
    assert uninstall_data["status"] == "success"
    assert not installed_widget_dir.exists()


@pytest.mark.asyncio
async def test_cartograph_config_round_trip(isolated_env):
    read_default = await _call_and_parse("cartograph_config", {"key": "auto-publish"})
    assert read_default["status"] == "success"
    assert read_default["key"] == "auto-publish"

    write_value = await _call_and_parse(
        "cartograph_config",
        {"key": "auto-publish", "value": "False"},
    )
    assert write_value["status"] == "success"

    read_updated = await _call_and_parse("cartograph_config", {"key": "auto-publish"})
    assert read_updated["status"] == "success"
    assert read_updated["value"] is False
