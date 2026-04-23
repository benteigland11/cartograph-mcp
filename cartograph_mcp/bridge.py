import json
import re
import subprocess
from typing import Any, Dict, List, Optional, Tuple, Union

import mcp.server.stdio
from mcp.server import NotificationOptions, Server
from mcp.server.models import InitializationOptions
from mcp.types import EmbeddedResource, ImageContent, TextContent, Tool


class McpServerBridge:
    """Declarative bridge to expose CLI commands as MCP tools."""

    def __init__(self, name: str, version: str = "0.1.0", instructions: Optional[str] = None):
        self.server = Server(name, instructions=instructions)
        self.version = version
        self.tools: Dict[str, Dict[str, Any]] = {}

        self.server.list_tools()(self.handle_list_tools)
        self.server.call_tool()(self.handle_call_tool)

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

    async def handle_list_tools(self) -> List[Tool]:
        """MCP list_tools handler."""
        return [
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
                InitializationOptions(
                    server_name=self.server.name,
                    server_version=self.version,
                    instructions=self.server.instructions,
                    capabilities=self.server.get_capabilities(
                        notification_options=NotificationOptions(),
                        experimental_capabilities={},
                    ),
                ),
            )
