from unittest.mock import patch

import pytest

from src.mcp_server_bridge import McpServerBridge


def test_bridge_sets_server_instructions():
    bridge = McpServerBridge("test-bridge", instructions="Use this bridge for tests.")

    assert bridge.server.instructions == "Use this bridge for tests."


@pytest.mark.asyncio
async def test_list_tools_exposes_schema_and_required_fields():
    bridge = McpServerBridge("test-bridge")
    bridge.add_tool(
        name="search",
        description="Search widgets.",
        schema={"query": {"type": "string"}},
        required=["query"],
        command_template=["cartograph", "search", "{query}"],
    )

    tools = await bridge.handle_list_tools()

    assert len(tools) == 1
    assert tools[0].name == "search"
    assert tools[0].inputSchema["required"] == ["query"]


@pytest.mark.asyncio
async def test_call_tool_builds_conditional_flags_and_values():
    bridge = McpServerBridge("test-bridge")
    bridge.add_tool(
        name="inspect",
        description="Inspect a widget.",
        schema={
            "widget_id": {"type": "string"},
            "source": {"type": "boolean"},
            "version": {"type": "string"},
        },
        required=["widget_id"],
        command_template=[
            "cartograph",
            "inspect",
            "{widget_id}",
            ("{source}", "--source"),
            ("--version", "{version}"),
        ],
    )

    with patch.object(bridge, "_run_json_cli", return_value={"status": "success"}) as mock_run:
        await bridge.handle_call_tool(
            "inspect",
            {"widget_id": "backend-retry-python", "source": True, "version": "1.2.3"},
        )

    assert mock_run.call_count == 1
    assert mock_run.call_args.args[0] == [
        "cartograph",
        "inspect",
        "backend-retry-python",
        "--source",
        "--version",
        "1.2.3",
    ]


@pytest.mark.asyncio
async def test_call_tool_omits_unsatisfied_optional_groups():
    bridge = McpServerBridge("test-bridge")
    bridge.add_tool(
        name="status",
        description="Widget status.",
        schema={"widget_dir": {"type": "string"}, "all": {"type": "boolean"}},
        command_template=["cartograph", "status", "{widget_dir}", ("{all}", "--all")],
    )

    with patch.object(bridge, "_run_json_cli", return_value={"status": "success"}) as mock_run:
        await bridge.handle_call_tool("status", {})

    assert mock_run.call_args.args[0] == ["cartograph", "status"]
