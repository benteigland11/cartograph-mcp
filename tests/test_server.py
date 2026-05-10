import json
import os
import sys
from unittest.mock import patch

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from mcp import types

from cartograph_mcp.server import bridge, handle_call_tool, handle_list_tools


async def _assert_command(tool_name, arguments, expected_cmd):
    with patch.object(bridge, "_run_json_cli", return_value={"status": "success"}) as mock_run:
        await handle_call_tool(tool_name, arguments)
    assert mock_run.call_args.args[0] == expected_cmd


@pytest.mark.asyncio
async def test_list_tools():
    tools = await handle_list_tools()
    assert len(tools) == 10
    assert [t.name for t in tools] == [
        "cg_registry",
        "cg_installed",
        "cg_status",
        "cg_create",
        "cg_validate",
        "cg_checkin",
        "cg_blueprint",
        "cg_architect",
        "cg_config",
        "cg_rules",
    ]


def test_server_instructions_explain_cli_fallback():
    assert bridge.server.instructions
    assert "cartograph --help" in bridge.server.instructions
    assert "not the full Cartograph CLI" in bridge.server.instructions


@pytest.mark.asyncio
async def test_registry_search_includes_optional_filters():
    await _assert_command(
        "cg_registry",
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
        "cg_registry",
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
        "cg_checkin",
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
    result = await handle_call_tool("cg_installed", {"action": "upgrade"})
    assert result["status"] == "error"
    assert "widget_dir" in result["message"]


@pytest.mark.asyncio
async def test_registry_widget_rate_builds_expected_command():
    await _assert_command(
        "cg_registry",
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
    await _assert_command("cg_config", {"key": "auto-publish"}, ["cartograph", "config", "--json", "auto-publish"])


@pytest.mark.asyncio
async def test_cartograph_config_updates_value():
    await _assert_command(
        "cg_config",
        {"key": "visibility", "value": "private"},
        ["cartograph", "config", "--json", "visibility", "private"],
    )


@pytest.mark.asyncio
async def test_registered_mcp_handler_uses_custom_dispatcher():
    request = types.CallToolRequest(
        method="tools/call",
        params=types.CallToolRequestParams(
            name="cg_config",
            arguments={"key": "auto-publish"},
        ),
    )

    with patch.object(bridge, "_run_json_cli", return_value={"status": "success", "key": "auto-publish"}) as mock_run:
        result = await bridge.server.request_handlers[types.CallToolRequest](request)

    assert mock_run.call_args.args[0] == ["cartograph", "config", "--json", "auto-publish"]
    assert result.root.structuredContent == {"status": "success", "key": "auto-publish"}
    assert json.loads(result.root.content[0].text) == {"status": "success", "key": "auto-publish"}


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("tool_name", "arguments", "expected_cmd"),
    [
        (
            "cg_registry",
            {"action": "search", "query": "retry"},
            ["cartograph", "search", "retry"],
        ),
        (
            "cg_registry",
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
            "cg_registry",
            {"action": "install", "widget_id": "backend-retry-python", "target": "/tmp/demo", "version": "2.0.0"},
            ["cartograph", "install", "backend-retry-python", "--target", "/tmp/demo", "--version", "2.0.0"],
        ),
        (
            "cg_installed",
            {"action": "upgrade", "widget_dir": "cg/backend_retry_python"},
            ["cartograph", "upgrade", "cg/backend_retry_python"],
        ),
        (
            "cg_installed",
            {"action": "upgrade", "widget_dir": "cg/backend_retry_python", "version": "3.1.0"},
            ["cartograph", "upgrade", "cg/backend_retry_python", "--version", "3.1.0"],
        ),
        (
            "cg_installed",
            {"action": "uninstall", "widget_dir": "cg/backend_retry_python"},
            ["cartograph", "uninstall", "cg/backend_retry_python"],
        ),
        (
            "cg_status",
            {},
            ["cartograph", "status"],
        ),
        (
            "cg_status",
            {"widget_dir": "cg/backend_retry_python", "page": 2, "size": 50, "all": True},
            ["cartograph", "status", "cg/backend_retry_python", "--page", "2", "--size", "50", "--all"],
        ),
        (
            "cg_create",
            {"name": "retry-backoff", "domain": "backend", "language": "python"},
            ["cartograph", "create", "retry-backoff", "--language", "python", "--domain", "backend"],
        ),
        (
            "cg_create",
            {"name": "my-bp", "is_blueprint": True, "target": "/tmp/bp"},
            ["cartograph", "blueprint", "create", "my-bp", "--target", "/tmp/bp"],
        ),
        (
            "cg_create",
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
            "cg_validate",
            {},
            ["cartograph", "validate"],
        ),
        (
            "cg_validate",
            {"path": "cg/backend-retry-python", "lib": True},
            ["cartograph", "validate", "cg/backend-retry-python", "--lib"],
        ),
        (
            "cg_checkin",
            {"path": "cg/backend_retry_python", "reason": "improve retries"},
            ["cartograph", "checkin", "cg/backend_retry_python", "--reason", "improve retries"],
        ),
        (
            "cg_checkin",
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
            "cg_blueprint",
            {"action": "add-dep", "widget_id": "backend-retry-python", "blueprint_path": "cg/my-bp", "no_validate": True},
            ["cartograph", "blueprint", "add-dep", "backend-retry-python", "--path", "cg/my-bp", "--no-validate"],
        ),
        (
            "cg_architect",
            {"action": "init", "path": "project/"},
            ["cartograph", "architect", "init", "--path", "project/"],
        ),
        (
            "cg_architect",
            {"action": "link", "component_id": "api", "widget": "backend-api-python"},
            ["cartograph", "architect", "link", "api", "backend-api-python"],
        ),
        (
            "cg_config",
            {},
            ["cartograph", "config", "--json"],
        ),
        (
            "cg_rules",
            {"action": "list"},
            ["cartograph", "rules", "--json"],
        ),
    ],
)
async def test_command_shapes_are_fully_expected(tool_name, arguments, expected_cmd):
    await _assert_command(tool_name, arguments, expected_cmd)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("tool_name", "arguments", "message_fragment"),
    [
        ("cg_registry", {"action": "search"}, "requires query"),
        ("cg_registry", {"action": "inspect"}, "requires widget_id"),
        ("cg_registry", {"action": "install"}, "requires widget_id"),
        ("cg_registry", {"action": "rate", "widget_ref": "@owner/widget"}, "requires score"),
        ("cg_registry", {"action": "publish"}, "must be one of"),
        ("cg_installed", {"action": "upgrade"}, "requires widget_dir"),
        ("cg_installed", {"action": "delete", "widget_dir": "cg/x"}, "must be one of"),
        ("cg_rules", {"action": "publish"}, "must be one of"),
        ("cg_rules", {"action": "init"}, "requires language"),
        ("cg_rules", {"action": "reset", "language": "python"}, "requires confirm=true"),
        ("cg_blueprint", {"action": "add-dep"}, "requires widget_id"),
        ("cg_architect", {"action": "link"}, "requires component_id"),
    ],
)
async def test_invalid_argument_combinations_return_clear_errors(tool_name, arguments, message_fragment):
    result = await handle_call_tool(tool_name, arguments)
    assert result["status"] == "error"
    assert message_fragment in result["message"]
