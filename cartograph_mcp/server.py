import asyncio
import json

from cartograph_mcp.bridge import McpServerBridge


SERVER_INSTRUCTIONS = """Cartograph preserves reusable implementation work across projects as widgets. Reusable means code, logic, tests, examples, models, geometry, hardware modules, or patterns that would be useful in another project, not just another file in the current project.

Use this MCP for the Cartograph daily-driver surface: registry interaction, installed-widget management, project widget status, widget creation, widget validation, widget checkin, widget rating, custom validation rules, and core workflow config.

This MCP is intentionally not the full Cartograph CLI. For commands or options not exposed here, use the shell and run `cartograph --help` or `cartograph <command> --help`. The CLI is the source of truth for the complete command surface.

When creating widgets through this MCP, pass only the widget slug as `name`; Cartograph composes the full widget_id from `domain`, `name`, and `language`. Installed widgets normally live under `cg/<widget_id>/`."""


bridge = McpServerBridge("cartograph", version="0.1.4", instructions=SERVER_INSTRUCTIONS)

DOMAINS = [
    "backend",
    "data",
    "frontend",
    "infra",
    "ml",
    "modeling",
    "rtl",
    "security",
    "universal",
]

LANGUAGES = [
    "angular",
    "javascript",
    "nim",
    "openscad",
    "php",
    "python",
    "systemverilog",
    "typescript",
]

BUMP_TYPES = ["major", "minor", "patch"]
CONFIG_KEYS = [
    "auto-publish",
    "visibility",
    "governance",
    "cloud",
    "show-unavailable",
    "publish-registry",
]
RULE_ACTIONS = ["list", "init", "reset"]
RULE_SCOPES = ["project", "global"]

TOOL_SPECS = [
    {
        "name": "registry_widget",
        "description": (
            "Registry-facing daily workflow for Cartograph widgets. "
            "Use search before writing reusable logic, inspect before installing or editing, "
            "install to add a widget to the current project, and rate to leave registry feedback. "
            "Actions: search requires query; inspect requires widget_id; install requires widget_id; "
            "rate requires widget_ref and score."
        ),
        "schema": {
            "action": {
                "type": "string",
                "enum": ["search", "inspect", "install", "rate"],
                "description": "Registry action to perform.",
            },
            "query": {"type": "string", "description": "Search query for action=search."},
            "domain": {"type": "string", "enum": DOMAINS, "description": "Optional search domain filter."},
            "language": {"type": "string", "enum": LANGUAGES, "description": "Optional search language filter."},
            "top_k": {"type": "integer", "description": "Maximum search results to return."},
            "widget_id": {"type": "string", "description": "Widget ID for inspect or install."},
            "source": {"type": "boolean", "description": "Include source files for inspect."},
            "all_versions": {"type": "boolean", "description": "Include all historical versions for inspect."},
            "reviews": {"type": "boolean", "description": "Include reviews for inspect."},
            "version": {"type": "string", "description": "Version for inspect or install."},
            "target": {"type": "string", "description": "Install target project root."},
            "widget_ref": {
                "type": "string",
                "description": "Widget dir path or @handle/widget-id for rate.",
            },
            "score": {"type": "number", "description": "Rating score from 1.0 to 5.0."},
            "comment": {"type": "string", "description": "Optional rating comment."},
        },
        "required": ["action"],
    },
    {
        "name": "installed_widget",
        "description": (
            "Mutate widgets already installed in the current project under cg/<widget_id>/. "
            "Use this for installed copies only; use registry_widget install for adding a new widget. "
            "Actions: upgrade requires widget_dir and optionally version; uninstall requires widget_dir."
        ),
        "schema": {
            "action": {
                "type": "string",
                "enum": ["upgrade", "uninstall"],
                "description": "Installed-widget action to perform.",
            },
            "widget_dir": {
                "type": "string",
                "description": "Installed widget path like cg/backend_retry_python.",
            },
            "version": {"type": "string", "description": "Target version for upgrade."},
        },
        "required": ["action"],
    },
    {
        "name": "widget_status",
        "description": (
            "Check health/status for installed widgets in the current project. "
            "Omit widget_dir to scan all installed widgets; provide widget_dir to inspect one."
        ),
        "schema": {
            "widget_dir": {"type": "string", "description": "Installed widget dir, or omit to scan all."},
            "page": {"type": "integer", "description": "1-indexed page for aggregate listing."},
            "size": {"type": "integer", "description": "Page size for aggregate listing."},
            "all": {"type": "boolean", "description": "Return every widget without pagination."},
        },
    },
    {
        "name": "create_widget",
        "description": (
            "Scaffold a new Cartograph widget. Use name for the slug only, not the full widget_id; "
            "Cartograph combines domain + name + language."
        ),
        "schema": {
            "name": {"type": "string", "description": "Widget slug, for example retry-backoff."},
            "domain": {"type": "string", "enum": DOMAINS, "description": "Widget domain."},
            "language": {"type": "string", "enum": LANGUAGES, "description": "Implementation language."},
            "display_name": {"type": "string", "description": "Optional display name for widget.json."},
            "target": {"type": "string", "description": "Project root to create the widget under."},
        },
        "required": ["name", "domain", "language"],
    },
    {
        "name": "validate_widget",
        "description": (
            "Run the full preflight / smoke pipeline without checking the widget into the library. "
            "Use this as the dry run for checkin before recording reusable widget changes."
        ),
        "schema": {
            "path": {"type": "string", "description": "Widget directory or widget ID with lib=true."},
            "lib": {"type": "boolean", "description": "Treat path as a library widget ID."},
        },
    },
    {
        "name": "checkin_widget",
        "description": (
            "Run the full validation / smoke pipeline and then check the widget into the library. "
            "Use this only for changes that should become reusable widget logic. "
            "Requires reason. Supports either path or widget_dir for compatibility."
        ),
        "schema": {
            "path": {"type": "string", "description": "Widget directory (default: .)."},
            "widget_dir": {"type": "string", "description": "Alias for path."},
            "reason": {"type": "string", "description": "What changed and why."},
            "bump": {"type": "string", "enum": BUMP_TYPES, "description": "Version bump type."},
            "publish": {"type": "boolean", "description": "Publish to cloud after checkin."},
            "override_warnings": {"type": "boolean", "description": "Proceed despite validation warnings."},
            "override_reason": {"type": "string", "description": "Why warnings should be overridden."},
        },
        "required": ["reason"],
    },
    {
        "name": "cartograph_config",
        "description": (
            "Read or update Cartograph workflow defaults used by the daily widget loop. "
            "Provide key to read the current value; provide both key and value to update it."
        ),
        "schema": {
            "key": {"type": "string", "enum": CONFIG_KEYS, "description": "Configuration key to read or update."},
            "value": {"type": "string", "description": "Optional new value to set."},
        },
        "required": ["key"],
    },
    {
        "name": "cartograph_rules",
        "description": (
            "List or manage custom validation rules that run during Cartograph validate and checkin. "
            "Actions: list shows active rules; init creates a project or global rules file and requires language; "
            "reset restores a rules file template, requires language, and requires confirm=true."
        ),
        "schema": {
            "action": {
                "type": "string",
                "enum": RULE_ACTIONS,
                "description": "Rules action to perform.",
            },
            "language": {
                "type": "string",
                "description": "Language for init/reset or optional filter for list, for example python.",
            },
            "scope": {
                "type": "string",
                "enum": RULE_SCOPES,
                "description": "Whether to target project rules or global rules. Defaults to project.",
            },
            "confirm": {
                "type": "boolean",
                "description": "Required as true for reset because reset overwrites rule edits.",
            },
        },
        "required": ["action"],
    },
]


def _register_tools() -> None:
    for spec in TOOL_SPECS:
        bridge.add_tool(
            name=spec["name"],
            description=spec["description"],
            schema=spec["schema"],
            required=spec.get("required"),
            command_template=["cartograph"],
        )


def _error(message: str):
    return {"status": "error", "message": message}


def _run(cmd: list[str]):
    return bridge._run_json_cli(cmd)


def _build_registry_widget(args: dict) -> list[str]:
    action = args.get("action")
    if action == "search":
        if "query" not in args:
            raise ValueError("registry_widget action=search requires query")
        cmd = ["cartograph", "search", str(args["query"])]
        if "domain" in args:
            cmd.extend(["--domain", str(args["domain"])])
        if "language" in args:
            cmd.extend(["--language", str(args["language"])])
        if "top_k" in args:
            cmd.extend(["--top-k", str(args["top_k"])])
        return cmd
    if action == "inspect":
        if "widget_id" not in args:
            raise ValueError("registry_widget action=inspect requires widget_id")
        cmd = ["cartograph", "inspect", str(args["widget_id"])]
        if args.get("source") is True:
            cmd.append("--source")
        if args.get("all_versions") is True:
            cmd.append("--all-versions")
        if args.get("reviews") is True:
            cmd.append("--reviews")
        if "version" in args:
            cmd.extend(["--version", str(args["version"])])
        return cmd
    if action == "install":
        if "widget_id" not in args:
            raise ValueError("registry_widget action=install requires widget_id")
        cmd = ["cartograph", "install", str(args["widget_id"])]
        if "target" in args:
            cmd.extend(["--target", str(args["target"])])
        if "version" in args:
            cmd.extend(["--version", str(args["version"])])
        return cmd
    if action == "rate":
        if "widget_ref" not in args:
            raise ValueError("registry_widget action=rate requires widget_ref")
        if "score" not in args:
            raise ValueError("registry_widget action=rate requires score")
        cmd = ["cartograph", "rate", str(args["widget_ref"]), str(args["score"])]
        if "comment" in args:
            cmd.extend(["--comment", str(args["comment"])])
        return cmd
    raise ValueError("registry_widget action must be one of: search, inspect, install, rate")


def _build_installed_widget(args: dict) -> list[str]:
    action = args.get("action")
    if "widget_dir" not in args:
        raise ValueError("installed_widget requires widget_dir")
    if action == "upgrade":
        cmd = ["cartograph", "upgrade", str(args["widget_dir"])]
        if "version" in args:
            cmd.extend(["--version", str(args["version"])])
        return cmd
    if action == "uninstall":
        return ["cartograph", "uninstall", str(args["widget_dir"])]
    raise ValueError("installed_widget action must be one of: upgrade, uninstall")


def _build_widget_status(args: dict) -> list[str]:
    cmd = ["cartograph", "status"]
    if "widget_dir" in args:
        cmd.append(str(args["widget_dir"]))
    if "page" in args:
        cmd.extend(["--page", str(args["page"])])
    if "size" in args:
        cmd.extend(["--size", str(args["size"])])
    if args.get("all") is True:
        cmd.append("--all")
    return cmd


def _build_create_widget(args: dict) -> list[str]:
    cmd = [
        "cartograph",
        "create",
        str(args["name"]),
        "--language",
        str(args["language"]),
        "--domain",
        str(args["domain"]),
    ]
    if "display_name" in args:
        cmd.extend(["--name", str(args["display_name"])])
    if "target" in args:
        cmd.extend(["--target", str(args["target"])])
    return cmd


def _build_validate_widget(args: dict) -> list[str]:
    cmd = ["cartograph", "validate"]
    if "path" in args:
        cmd.append(str(args["path"]))
    if args.get("lib") is True:
        cmd.append("--lib")
    return cmd


def _build_checkin_widget(args: dict) -> list[str]:
    path = args.get("path", args.get("widget_dir"))
    cmd = ["cartograph", "checkin"]
    if path is not None:
        cmd.append(str(path))
    cmd.extend(["--reason", str(args["reason"])])
    if "bump" in args:
        cmd.extend(["--bump", str(args["bump"])])
    if args.get("publish") is True:
        cmd.append("--publish")
    if args.get("override_warnings") is True:
        cmd.append("--override-warnings")
    if "override_reason" in args:
        cmd.extend(["--override-reason", str(args["override_reason"])])
    return cmd


def _build_cartograph_config(args: dict) -> list[str]:
    cmd = ["cartograph", "config", "--json", str(args["key"])]
    if "value" in args:
        cmd.append(str(args["value"]))
    return cmd


def _build_cartograph_rules(args: dict) -> list[str]:
    action = args.get("action")
    if action not in RULE_ACTIONS:
        raise ValueError("cartograph_rules action must be one of: list, init, reset")
    if action in {"init", "reset"} and "language" not in args:
        raise ValueError(f"cartograph_rules action={action} requires language")
    if action == "reset" and args.get("confirm") is not True:
        raise ValueError("cartograph_rules action=reset requires confirm=true")

    cmd = ["cartograph", "rules", "--json"]
    if action != "list":
        cmd.append(str(action))
    if "language" in args:
        cmd.extend(["--language", str(args["language"])])
    if args.get("scope") == "global":
        cmd.append("--global")
    if args.get("confirm") is True:
        cmd.append("--confirm")
    return cmd


BUILDERS = {
    "registry_widget": _build_registry_widget,
    "installed_widget": _build_installed_widget,
    "widget_status": _build_widget_status,
    "create_widget": _build_create_widget,
    "validate_widget": _build_validate_widget,
    "checkin_widget": _build_checkin_widget,
    "cartograph_config": _build_cartograph_config,
    "cartograph_rules": _build_cartograph_rules,
}


_register_tools()


async def handle_list_tools():
    return await bridge.handle_list_tools()


async def handle_call_tool(name, arguments):
    args = dict(arguments or {})
    if name not in BUILDERS:
        return _error(f"Unknown tool: {name}")
    try:
        cmd = BUILDERS[name](args)
    except ValueError as exc:
        return _error(str(exc))
    return _run(cmd)


bridge.server.call_tool()(handle_call_tool)


async def _run_server():
    await bridge.run()


def main():
    asyncio.run(_run_server())


if __name__ == "__main__":
    main()
