import json
import re
import subprocess
from typing import Any, Dict, List, Optional, Tuple, Union

import mcp.server.stdio
from mcp.server import Server
from mcp.types import (
    CallToolRequestParams,
    CallToolResult,
    EmbeddedResource,
    ImageContent,
    ListToolsRequest,
    ListToolsResult,
    TextContent,
    Tool,
)


class McpServerBridge:
    """Declarative bridge to expose CLI commands as MCP tools."""

    def __init__(self, name: str, version: str = "0.1.0", instructions: Optional[str] = None):
        self.version = version
        self.tools: Dict[str, Dict[str, Any]] = {}

        # MCP 2.0 removed the low-level decorator registration methods. The
        # constructor is now the supported way to register protocol handlers.
        self.server = Server(
            name,
            version=version,
            instructions=instructions,
            on_list_tools=self._handle_list_tools_request,
            on_call_tool=self._handle_call_tool_request,
        )

    def add_tool(
        self,
        name: str,
        description: str,
        command_template: List[Union[str, Tuple[str, ...]]],
        schema: Dict[str, Any],
        required: Optional[List[str]] = None,
        env: Optional[Dict[str, str]] = None,
    ) -> None:
        """Add a tool that maps to a CLI command."""
        self.tools[name] = {
            "description": description,
            "command_template": command_template,
            "schema": schema,
            "required": required or [],
            "env": env,
        }

    async def _handle_list_tools_request(self, _ctx, _params) -> ListToolsResult:
        return await self.handle_list_tools(_params)

    async def handle_list_tools(self, request: ListToolsRequest | None = None) -> ListToolsResult:
        """Return the MCP 2.0 ``tools/list`` result envelope.

        The SDK's current handler contract passes a ``ListToolsRequest`` and
        expects a ``ListToolsResult``.  This server has a small, non-paginated
        tool catalog, so the cursor is intentionally ignored and all tools
        are returned in registration order.
        """
        del request
        return ListToolsResult(
            tools=[
                Tool(
                    name=name,
                    description=t["description"],
                    inputSchema={
                        "type": "object",
                        "properties": t["schema"],
                        "required": t["required"],
                    },
                )
                for name, t in self.tools.items()
            ]
        )

    async def _handle_call_tool_request(self, _ctx, params: CallToolRequestParams) -> CallToolResult:
        content = await self.handle_call_tool(params.name, params.arguments)
        return CallToolResult(content=content)

    async def handle_call_tool(
        self, name: str, arguments: Dict[str, Any] | None
    ) -> List[TextContent | ImageContent | EmbeddedResource]:
        """MCP call_tool handler."""
        if name not in self.tools:
            raise ValueError(f"Unknown tool: {name}")

        tool = self.tools[name]
        args = arguments or {}

        cmd = []
        for part in tool["command_template"]:
            if isinstance(part, (list, tuple)):
                if len(part) == 2 and part[0].startswith("{") and part[0].endswith("}") and not part[1].startswith("{"):
                    arg_name = part[0][1:-1]
                    if args.get(arg_name) is True:
                        cmd.append(part[1])
                else:
                    group_placeholders = []
                    for item in part:
                        group_placeholders.extend(re.findall(r"\{([^}]+)\}", item))

                    if all(p in args for p in group_placeholders):
                        for item in part:
                            formatted = item
                            for p in group_placeholders:
                                formatted = formatted.replace(f"{{{p}}}", str(args[p]))
                            cmd.append(formatted)
            else:
                placeholders = re.findall(r"\{([^}]+)\}", part)
                if not placeholders:
                    cmd.append(part)
                elif all(p in args for p in placeholders):
                    formatted = part
                    for p in placeholders:
                        formatted = formatted.replace(f"{{{p}}}", str(args[p]))
                    cmd.append(formatted)

        result = self._run_json_cli(cmd, env=tool["env"])
        return [TextContent(type="text", text=json.dumps(result, indent=2))]

    def _run_json_cli(self, cmd: List[str], env: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """Run a CLI command and parse JSON stdout."""
        try:
            process = subprocess.run(cmd, capture_output=True, text=True, check=False, env=env)

            stdout = process.stdout.strip()
            stderr = process.stderr.strip()

            if not stdout:
                if process.returncode != 0:
                    return {"status": "error", "message": stderr or f"Process exited with {process.returncode}"}
                return {"status": "success", "message": "No output"}

            try:
                return json.loads(stdout)
            except json.JSONDecodeError:
                if process.returncode != 0:
                    return {"status": "error", "message": stderr or stdout}
                return {"status": "error", "message": f"Output is not valid JSON: {stdout[:100]}..."}

        except Exception as exc:
            return {"status": "error", "message": str(exc)}

    async def run(self):
        """Run the stdio server."""
        async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                self.server.create_initialization_options(),
            )
