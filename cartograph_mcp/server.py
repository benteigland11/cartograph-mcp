import asyncio
import json
from pathlib import Path

from cartograph_mcp.bridge import McpServerBridge

FAQ_PATH = Path(__file__).parent / "faq.json"
HELP_ACTIONS = ["list", "get"]


SERVER_INSTRUCTIONS = """Cartograph preserves reusable implementation work across projects as widgets and blueprints. Reusable means code, logic, tests, examples, models, geometry, hardware modules, or patterns that would be useful in another project, not just another file in the current project.

Use this MCP for the Cartograph daily-driver surface: registry interaction, installed-widget management, project widget status, widget creation, widget validation, widget checkin, widget rating, custom validation rules, and core workflow config.

This MCP is intentionally not the full Cartograph CLI. For commands or options not exposed here, use the shell and run `cartograph --help` or `cartograph <command> --help`. The CLI is the source of truth for the complete command surface.

When creating widgets through this MCP, pass only the widget slug as `name`; Cartograph composes the full widget_id from `domain`, `name`, and `language`. Installed widgets normally live under `cg/<widget_id>/`."""


bridge = McpServerBridge("cartograph", version="0.2.1", instructions=SERVER_INSTRUCTIONS)

# Enums are derived from cartograph-cli (a hard dependency) so they track the
# CLI surface instead of drifting as new domains/languages/settings land.
#
# Derivation runs in a `python -P` subprocess rather than a direct import:
# the CLI ships its bundled widgets as a top-level `cg` package, and a direct
# import from a consumer project root would let that project's own cg/
# directory shadow it. -P keeps sys.path[0] (cwd/script dir) out of the
# interpreter, so resolution always hits the installed CLI.
#
# Hardcoded fallbacks only keep the server bootable if the contract ever
# breaks; they are not maintained as a second source of truth, and
# ENUM_SOURCE lets tests forbid them from silently taking over.
def _cli_enums() -> dict:
    import subprocess
    import sys
    code = (
        "import json\n"
        "from cartograph.validator import VALID_DOMAINS\n"
        "from cartograph.languages.registry import supported_languages\n"
        "from cartograph.config import config_keys\n"
        "print(json.dumps({"
        "'domains': sorted(VALID_DOMAINS),"
        "'languages': sorted(supported_languages()),"
        "'config_keys': config_keys()}))"
    )
    proc = subprocess.run([sys.executable, "-P", "-c", code],
                          capture_output=True, text=True, timeout=30)
    if proc.returncode != 0:
        raise RuntimeError(f"cartograph-cli enum derivation failed: {proc.stderr.strip()}")
    return json.loads(proc.stdout)


try:
    _enums = _cli_enums()
    DOMAINS = _enums["domains"]
    LANGUAGES = _enums["languages"]
    CONFIG_KEYS = _enums["config_keys"]
    ENUM_SOURCE = "cli"
except Exception:
    DOMAINS = ["backend", "data", "devops", "frontend", "infra", "ml",
               "modeling", "rtl", "security", "universal"]
    LANGUAGES = ["angular", "javascript", "nim", "openscad", "php",
                 "python", "systemverilog", "terraform", "typescript"]
    CONFIG_KEYS = ["auto-publish", "auto-update", "cloud", "governance",
                   "publish-registry", "search-priority", "show-unavailable",
                   "visibility"]
    ENUM_SOURCE = "fallback"

BUMP_TYPES = ["major", "minor", "patch"]
RULE_ACTIONS = ["list", "init", "reset"]
RULE_SCOPES = ["project", "global"]
BLUEPRINT_ACTIONS = ["create", "add-dep", "remove-dep"]

TOOL_SPECS = [
    {
        "name": "cg_registry",
        "description": (
            "Registry-facing daily workflow for Cartograph widgets and blueprints. "
            "Use search before writing reusable logic, inspect before installing or editing, "
            "install to add a widget to the current project, and rate to leave registry feedback. "
            "When installing or inspecting, use the exact value from the 'id' field returned by search."
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
            "registry": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Restrict search fan-out to the given registry prefixes (e.g. ['cg'], ['myorg', 'cg']). Without this, all configured registries are searched.",
            },
            "owner": {
                "type": "string",
                "description": "Filter search to widgets owned by @handle. Requires registry (owner is scoped per-registry).",
            },
            "local_only": {
                "type": "boolean",
                "description": "Search only the local library; skip all registry calls. Cannot combine with registry/owner.",
            },
            "widget_id": {"type": "string", "description": "Widget ID. Use the exact value from the 'id' field returned by search."},
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
        "name": "cg_installed",
        "description": (
            "Mutate widgets already installed in the current project. "
            "Use this for installed copies only; use cg_registry install for adding a new widget. "
            "Actions: upgrade requires widget_dir and optionally version; uninstall requires widget_dir. "
            "Pass the widget directory path (e.g. cg/backend-retry-python)."
        ),
        "schema": {
            "action": {
                "type": "string",
                "enum": ["upgrade", "uninstall"],
                "description": "Installed-widget action to perform.",
            },
            "widget_dir": {
                "type": "string",
                "description": "The local widget directory path (e.g. cg/backend-retry-python).",
            },
            "version": {"type": "string", "description": "Target version for upgrade."},
        },
        "required": ["action"],
    },
    {
        "name": "cg_status",
        "description": (
            "Check health/status for installed widgets in the current project. Use this to see if "
            "widgets are out of sync with the library, have local modifications, or have updates available. "
            "Omit widget_dir to scan all installed widgets; provide a specific directory (e.g. cg/backend-retry-python) to inspect one."
        ),
        "schema": {
            "widget_dir": {"type": "string", "description": "Installed widget directory (e.g. cg-infra-agent-cli-python) or path; omit to scan all."},
            "page": {"type": "integer", "description": "1-indexed page for aggregate listing."},
            "size": {"type": "integer", "description": "Page size for aggregate listing."},
            "all": {"type": "boolean", "description": "Return every widget without pagination."},
        },
    },
    {
        "name": "cg_create",
        "description": (
            "Scaffold a new Cartograph widget or blueprint. Use name for the slug only, not the full widget_id; "
            "Cartograph combines domain + name + language for widgets. For blueprints, just use the name."
        ),
        "schema": {
            "name": {"type": "string", "description": "Slug, for example retry-backoff."},
            "domain": {"type": "string", "enum": DOMAINS, "description": "Domain (required for widgets)."},
            "language": {"type": "string", "enum": LANGUAGES, "description": "Language (required for widgets)."},
            "is_blueprint": {"type": "boolean", "description": "Whether to scaffold a blueprint instead of a widget."},
            "display_name": {"type": "string", "description": "Optional display name for manifest."},
            "target": {"type": "string", "description": "Project root to create the module under."},
        },
        "required": ["name"],
    },
    {
        "name": "cg_validate",
        "description": (
            "Run the full preflight / smoke pipeline without checking the module into the library. "
            "Use this as the dry run for checkin before recording reusable changes."
        ),
        "schema": {
            "path": {"type": "string", "description": "Module directory (e.g. cg/backend-retry-python) or ID with lib=true."},
            "lib": {"type": "boolean", "description": "Treat path as a library widget ID."},
        },
    },
    {
        "name": "cg_checkin",
        "description": (
            "Run the full validation / smoke pipeline and then check the module into the library. "
            "Use this only for changes that should become reusable logic. "
            "Requires reason. Supports either path or widget_dir for compatibility."
        ),
        "schema": {
            "path": {"type": "string", "description": "Directory (default: .)."},
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
        "name": "cg_blueprint",
        "description": (
            "Blueprint-specific composition management. Blueprints are higher-order widgets that "
            "compose other widgets as dependencies. Use this to add or remove dependencies."
        ),
        "schema": {
            "action": {
                "type": "string",
                "enum": BLUEPRINT_ACTIONS,
                "description": "Blueprint action to perform.",
            },
            "name": {"type": "string", "description": "Blueprint name (for create action)."},
            "blueprint_path": {"type": "string", "description": "Path to the blueprint directory (default: .)."},
            "widget_id": {"type": "string", "description": "Widget ID to add or remove as a dependency."},
            "target": {"type": "string", "description": "Target root for create."},
            "no_validate": {"type": "boolean", "description": "Skip validation when adding dependency."},
        },
        "required": ["action"],
    },
    {
        "name": "cg_config",
        "description": (
            "Read or update Cartograph workflow defaults. "
            "Provide key to read the current value; provide both key and value to update it."
        ),
        "schema": {
            "key": {"type": "string", "enum": CONFIG_KEYS, "description": "Configuration key to read or update. Omit to list all settings."},
            "value": {"type": "string", "description": "Optional new value to set."},
        },
    },
    {
        "name": "cg_rules",
        "description": (
            "List or manage custom validation rules that run during Cartograph validate and checkin."
        ),
        "schema": {
            "action": {
                "type": "string",
                "enum": RULE_ACTIONS,
                "description": "Rules action to perform.",
            },
            "language": {
                "type": "string",
                "description": "Language filter or target.",
            },
            "scope": {
                "type": "string",
                "enum": RULE_SCOPES,
                "description": "Whether to target project rules or global rules. Defaults to project.",
            },
            "confirm": {
                "type": "boolean",
                "description": "Required as true for reset.",
            },
        },
        "required": ["action"],
    },
    {
        "name": "cg_help",
        "description": (
            "Recovery guidance for common Cartograph trouble states (e.g. local out of sync with cloud, "
            "checkin blocked, validation contamination, publish rejected). Use action=list to browse topics "
            "with one-line summaries, then action=get with a topic to read the full resolution. "
            "Reach for this before guessing when an agent is stuck on a Cartograph error state."
        ),
        "schema": {
            "action": {
                "type": "string",
                "enum": HELP_ACTIONS,
                "description": "list returns available topics; get returns the full entry for one topic.",
            },
            "topic": {"type": "string", "description": "Topic slug for action=get (from the list output)."},
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


def _build_cg_registry(args: dict) -> list[str]:
    action = args.get("action")
    if action == "search":
        if "query" not in args:
            raise ValueError("cg_registry action=search requires query")
        if "owner" in args and "registry" not in args:
            raise ValueError("cg_registry search 'owner' requires 'registry' (owner is scoped per-registry)")
        if args.get("local_only") is True and ("registry" in args or "owner" in args):
            raise ValueError("cg_registry search 'local_only' cannot combine with 'registry' or 'owner'")
        cmd = ["cartograph", "search", str(args["query"])]
        if "domain" in args:
            cmd.extend(["--domain", str(args["domain"])])
        if "language" in args:
            cmd.extend(["--language", str(args["language"])])
        if "top_k" in args:
            cmd.extend(["--top-k", str(args["top_k"])])
        if "registry" in args:
            regs = args["registry"]
            if not isinstance(regs, list):
                raise ValueError("cg_registry search 'registry' must be an array of prefix strings")
            for prefix in regs:
                cmd.extend(["--registry", str(prefix)])
        if "owner" in args:
            cmd.extend(["--owner", str(args["owner"])])
        if args.get("local_only") is True:
            cmd.append("--local-only")
        return cmd
    if action == "inspect":
        if "widget_id" not in args:
            raise ValueError("cg_registry action=inspect requires widget_id")
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
            raise ValueError("cg_registry action=install requires widget_id")
        cmd = ["cartograph", "install", str(args["widget_id"])]
        if "target" in args:
            cmd.extend(["--target", str(args["target"])])
        if "version" in args:
            cmd.extend(["--version", str(args["version"])])
        return cmd
    if action == "rate":
        if "widget_ref" not in args:
            raise ValueError("cg_registry action=rate requires widget_ref")
        if "score" not in args:
            raise ValueError("cg_registry action=rate requires score")
        cmd = ["cartograph", "rate", str(args["widget_ref"]), str(args["score"])]
        if "comment" in args:
            cmd.extend(["--comment", str(args["comment"])])
        return cmd
    raise ValueError("cg_registry action must be one of: search, inspect, install, rate")


def _build_cg_installed(args: dict) -> list[str]:
    action = args.get("action")
    if "widget_dir" not in args:
        raise ValueError("cg_installed requires widget_dir")
    if action == "upgrade":
        cmd = ["cartograph", "upgrade", str(args["widget_dir"])]
        if "version" in args:
            cmd.extend(["--version", str(args["version"])])
        return cmd
    if action == "uninstall":
        return ["cartograph", "uninstall", str(args["widget_dir"])]
    raise ValueError("cg_installed action must be one of: upgrade, uninstall")


def _build_cg_status(args: dict) -> list[str]:
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


def _build_cg_create(args: dict) -> list[str]:
    if args.get("is_blueprint"):
        cmd = ["cartograph", "blueprint", "create", str(args["name"])]
        if "target" in args:
            cmd.extend(["--target", str(args["target"])])
        return cmd
        
    if "domain" not in args or "language" not in args:
         raise ValueError("cg_create for widgets requires domain and language")

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


def _build_cg_validate(args: dict) -> list[str]:
    cmd = ["cartograph", "validate"]
    if "path" in args:
        cmd.append(str(args["path"]))
    if args.get("lib") is True:
        cmd.append("--lib")
    return cmd


def _build_cg_checkin(args: dict) -> list[str]:
    path = args.get("path", args.get("widget_dir"))
    cmd = ["cartograph", "checkin"]
    if path is not None:
        cmd.append(str(path))
    cmd.extend(["--reason", str(args["reason"])])
    if "bump" in args:
        cmd.extend(["--bump", str(args["bump"])])
    if args.get("publish") is True:
        cmd.append("--publish")
    elif args.get("publish") is False:
        cmd.append("--no-publish")
    if args.get("override_warnings") is True:
        cmd.append("--override-warnings")
    if "override_reason" in args:
        cmd.extend(["--override-reason", str(args["override_reason"])])
    return cmd


def _build_cg_blueprint(args: dict) -> list[str]:
    action = args.get("action")
    if action == "create":
        if "name" not in args:
            raise ValueError("cg_blueprint action=create requires name")
        cmd = ["cartograph", "blueprint", "create", str(args["name"])]
        if "target" in args:
            cmd.extend(["--target", str(args["target"])])
        return cmd
    if action == "add-dep":
        if "widget_id" not in args:
            raise ValueError("cg_blueprint action=add-dep requires widget_id")
        cmd = ["cartograph", "blueprint", "add-dep", str(args["widget_id"])]
        if "blueprint_path" in args:
            cmd.extend(["--path", str(args["blueprint_path"])])
        if args.get("no_validate"):
            cmd.append("--no-validate")
        return cmd
    if action == "remove-dep":
        if "widget_id" not in args:
            raise ValueError("cg_blueprint action=remove-dep requires widget_id")
        cmd = ["cartograph", "blueprint", "remove-dep", str(args["widget_id"])]
        if "blueprint_path" in args:
            cmd.extend(["--path", str(args["blueprint_path"])])
        return cmd
    raise ValueError(f"cg_blueprint action must be one of: {BLUEPRINT_ACTIONS}")


def _build_cg_config(args: dict) -> list[str]:
    cmd = ["cartograph", "config", "--json"]
    if "key" in args:
        cmd.append(str(args["key"]))
        if "value" in args:
            cmd.append(str(args["value"]))
    return cmd


def _build_cg_rules(args: dict) -> list[str]:
    action = args.get("action")
    if action not in RULE_ACTIONS:
        raise ValueError("cg_rules action must be one of: list, init, reset")
    if action in {"init", "reset"} and "language" not in args:
        raise ValueError(f"cg_rules action={action} requires language")
    if action == "reset" and args.get("confirm") is not True:
        raise ValueError("cg_rules action=reset requires confirm=true")

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


def _load_faq() -> dict:
    try:
        with FAQ_PATH.open() as f:
            return json.load(f)
    except FileNotFoundError:
        return {}
    except json.JSONDecodeError as exc:
        raise ValueError(f"faq.json is malformed: {exc}")


def _handle_cg_help(args: dict) -> dict:
    action = args.get("action")
    if action not in HELP_ACTIONS:
        return _error(f"cg_help action must be one of: {HELP_ACTIONS}")
    faq = _load_faq()
    if action == "list":
        return {
            "status": "success",
            "topics": [{"topic": k, "summary": v.get("summary", "")} for k, v in faq.items()],
        }
    topic = args.get("topic")
    if not topic:
        return _error("cg_help action=get requires topic")
    entry = faq.get(topic)
    if not entry:
        return _error(f"Unknown topic: {topic}. Call action=list to see available topics.")
    return {"status": "success", "topic": topic, **entry}


BUILDERS = {
    "cg_registry": _build_cg_registry,
    "cg_installed": _build_cg_installed,
    "cg_status": _build_cg_status,
    "cg_create": _build_cg_create,
    "cg_validate": _build_cg_validate,
    "cg_checkin": _build_cg_checkin,
    "cg_blueprint": _build_cg_blueprint,
    "cg_config": _build_cg_config,
    "cg_rules": _build_cg_rules,
}


_register_tools()


async def handle_list_tools():
    return await bridge.handle_list_tools()


async def handle_call_tool(name, arguments):
    args = dict(arguments or {})
    if name == "cg_help":
        try:
            return _handle_cg_help(args)
        except ValueError as exc:
            return _error(str(exc))
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
