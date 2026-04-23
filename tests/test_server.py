import json
import os
import sys
from unittest.mock import patch

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from server import bridge, handle_call_tool, handle_list_tools


async def _assert_command(tool_name, arguments, expected_cmd):
    with patch.object(bridge, "_run_json_cli", return_value={"status": "success"}) as mock_run:
        await handle_call_tool(tool_name, arguments)
    assert mock_run.call_args.args[0] == expected_cmd


@pytest.mark.asyncio
async def test_list_tools():
    tools = await handle_list_tools()
    assert len(tools) == 8
    assert [t.name for t in tools] == [
        "registry_widget",
        "installed_widget",
        "widget_status",
        "create_widget",
        "validate_widget",
        "checkin_widget",
        "cartograph_config",
        "cartograph_rules",
    ]


def test_server_instructions_explain_cli_fallback():
    assert bridge.server.instructions
    assert "cartograph --help" in bridge.server.instructions
    assert "not the full Cartograph CLI" in bridge.server.instructions


@pytest.mark.asyncio
async def test_registry_search_includes_optional_filters():
    await _assert_command(
        "registry_widget",
        {"action": "search", "query": "retry", "domain": "backend", "language": "python", "top_k": 5},
        [
        "cartograph",
        "search",
        "retry",
        "--domain",
        "backend",
        "--language",
        "python",
        "--top-k",
        "5",
        ],
    )


@pytest.mark.asyncio
async def test_registry_inspect_supports_all_versions_flag():
    await _assert_command(
        "registry_widget",
        {"action": "inspect", "widget_id": "backend-retry-python", "all_versions": True},
        [
        "cartograph",
        "inspect",
        "backend-retry-python",
        "--all-versions",
        ],
    )


@pytest.mark.asyncio
async def test_checkin_widget_accepts_widget_dir_alias():
    await _assert_command(
        "checkin_widget",
        {"widget_dir": "cg/backend_retry_python", "reason": "tighten docs"},
        [
        "cartograph",
        "checkin",
        "cg/backend_retry_python",
        "--reason",
        "tighten docs",
        ],
    )


@pytest.mark.asyncio
async def test_installed_widget_rejects_missing_widget_dir():
    result = await handle_call_tool("installed_widget", {"action": "upgrade"})
    data = json.loads(result[0].text)
    assert data["status"] == "error"
    assert "widget_dir" in data["message"]


@pytest.mark.asyncio
async def test_registry_widget_rate_builds_expected_command():
    await _assert_command(
        "registry_widget",
        {"action": "rate", "widget_ref": "@owner/backend-retry-python", "score": 4.5, "comment": "Solid"},
        [
        "cartograph",
        "rate",
        "@owner/backend-retry-python",
        "4.5",
        "--comment",
        "Solid",
        ],
    )


@pytest.mark.asyncio
async def test_cartograph_config_reads_current_value():
    await _assert_command("cartograph_config", {"key": "auto-publish"}, ["cartograph", "config", "--json", "auto-publish"])


@pytest.mark.asyncio
async def test_cartograph_config_updates_value():
    await _assert_command(
        "cartograph_config",
        {"key": "visibility", "value": "private"},
        ["cartograph", "config", "--json", "visibility", "private"],
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("tool_name", "arguments", "expected_cmd"),
    [
        (
            "registry_widget",
            {"action": "search", "query": "retry"},
            ["cartograph", "search", "retry"],
        ),
        (
            "registry_widget",
            {
                "action": "inspect",
                "widget_id": "backend-retry-python",
                "source": True,
                "reviews": True,
                "version": "1.2.3",
            },
            ["cartograph", "inspect", "backend-retry-python", "--source", "--reviews", "--version", "1.2.3"],
        ),
        (
            "registry_widget",
            {"action": "install", "widget_id": "backend-retry-python", "target": "/tmp/demo", "version": "2.0.0"},
            ["cartograph", "install", "backend-retry-python", "--target", "/tmp/demo", "--version", "2.0.0"],
        ),
        (
            "installed_widget",
            {"action": "upgrade", "widget_dir": "cg/backend_retry_python"},
            ["cartograph", "upgrade", "cg/backend_retry_python"],
        ),
        (
            "installed_widget",
            {"action": "upgrade", "widget_dir": "cg/backend_retry_python", "version": "3.1.0"},
            ["cartograph", "upgrade", "cg/backend_retry_python", "--version", "3.1.0"],
        ),
        (
            "installed_widget",
            {"action": "uninstall", "widget_dir": "cg/backend_retry_python"},
            ["cartograph", "uninstall", "cg/backend_retry_python"],
        ),
        (
            "widget_status",
            {},
            ["cartograph", "status"],
        ),
        (
            "widget_status",
            {"widget_dir": "cg/backend_retry_python", "page": 2, "size": 50, "all": True},
            ["cartograph", "status", "cg/backend_retry_python", "--page", "2", "--size", "50", "--all"],
        ),
        (
            "create_widget",
            {"name": "retry-backoff", "domain": "backend", "language": "python"},
            ["cartograph", "create", "retry-backoff", "--language", "python", "--domain", "backend"],
        ),
        (
            "create_widget",
            {
                "name": "retry-backoff",
                "domain": "backend",
                "language": "python",
                "display_name": "Retry With Backoff",
                "target": "/tmp/project",
            },
            [
                "cartograph",
                "create",
                "retry-backoff",
                "--language",
                "python",
                "--domain",
                "backend",
                "--name",
                "Retry With Backoff",
                "--target",
                "/tmp/project",
            ],
        ),
        (
            "validate_widget",
            {},
            ["cartograph", "validate"],
        ),
        (
            "validate_widget",
            {"path": "cg/backend-retry-python", "lib": True},
            ["cartograph", "validate", "cg/backend-retry-python", "--lib"],
        ),
        (
            "checkin_widget",
            {"path": "cg/backend_retry_python", "reason": "improve retries"},
            ["cartograph", "checkin", "cg/backend_retry_python", "--reason", "improve retries"],
        ),
        (
            "checkin_widget",
            {
                "path": "cg/backend_retry_python",
                "reason": "improve retries",
                "bump": "major",
                "publish": True,
                "override_warnings": True,
                "override_reason": "known warning",
            },
            [
                "cartograph",
                "checkin",
                "cg/backend_retry_python",
                "--reason",
                "improve retries",
                "--bump",
                "major",
                "--publish",
                "--override-warnings",
                "--override-reason",
                "known warning",
            ],
        ),
        (
            "cartograph_rules",
            {"action": "list"},
            ["cartograph", "rules", "--json"],
        ),
        (
            "cartograph_rules",
            {"action": "list", "language": "python", "scope": "global"},
            ["cartograph", "rules", "--json", "--language", "python", "--global"],
        ),
        (
            "cartograph_rules",
            {"action": "init", "language": "python"},
            ["cartograph", "rules", "--json", "init", "--language", "python"],
        ),
        (
            "cartograph_rules",
            {"action": "reset", "language": "python", "scope": "global", "confirm": True},
            ["cartograph", "rules", "--json", "reset", "--language", "python", "--global", "--confirm"],
        ),
    ],
)
async def test_command_shapes_are_fully_expected(tool_name, arguments, expected_cmd):
    await _assert_command(tool_name, arguments, expected_cmd)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("tool_name", "arguments", "message_fragment"),
    [
        ("registry_widget", {"action": "search"}, "requires query"),
        ("registry_widget", {"action": "inspect"}, "requires widget_id"),
        ("registry_widget", {"action": "install"}, "requires widget_id"),
        ("registry_widget", {"action": "rate", "widget_ref": "@owner/widget"}, "requires score"),
        ("registry_widget", {"action": "publish"}, "must be one of"),
        ("installed_widget", {"action": "upgrade"}, "requires widget_dir"),
        ("installed_widget", {"action": "delete", "widget_dir": "cg/x"}, "must be one of"),
        ("cartograph_rules", {"action": "publish"}, "must be one of"),
        ("cartograph_rules", {"action": "init"}, "requires language"),
        ("cartograph_rules", {"action": "reset", "language": "python"}, "requires confirm=true"),
    ],
)
async def test_invalid_argument_combinations_return_clear_errors(tool_name, arguments, message_fragment):
    result = await handle_call_tool(tool_name, arguments)
    data = json.loads(result[0].text)
    assert data["status"] == "error"
    assert message_fragment in data["message"]
