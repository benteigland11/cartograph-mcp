# cartograph-mcp

Model Context Protocol (MCP) server for [Cartograph](https://github.com/Vinscen/Cartograph) widget library.

## Installation

```bash
pip install cartograph-mcp
```

## Release

Intended standalone repository: `benteigland11/cartograph-mcp`

PyPI trusted publishing is configured around the GitHub Actions workflow file
`.github/workflows/pypi-publish.yml` and the GitHub environment `pypi`.

## Configuration for Claude Desktop

Add this to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "cartograph": {
      "command": "cartograph-mcp"
    }
  }
}
```

## Tools

The MCP server intentionally exposes a small daily-driving surface:

- `registry_widget`
  Actions: `search`, `inspect`, `install`, `rate`
- `installed_widget`
  Actions: `upgrade`, `uninstall`
- `widget_status`
- `create_widget`
- `validate_widget`
- `checkin_widget`
- `cartograph_config`

## Usage

Cartograph is a widget library manager, so the normal loop still applies: search first, inspect existing widgets, install and wire them in, then validate and check in improvements when you generalize logic.

The MCP surface is workflow-oriented rather than a 1:1 mirror of the CLI. `registry_widget` handles library-facing actions, `installed_widget` handles mutations for already-installed widget dirs, and `widget_status` is the project health check. `create_widget` uses the Cartograph mental model directly: pass `name` as the slug only, and the CLI composes the full widget ID from `domain` and `language`.

`validate_widget` is the dry run for `checkin_widget`: it runs the same preflight / smoke path without mutating library state. `checkin_widget` runs that pipeline and then performs the actual checkin.

`cartograph_config` is the one setup/defaults tool in MCP. Use it to read or update core workflow settings like `auto-publish`, `visibility`, `governance`, `cloud`, `show-unavailable`, and `publish-registry`.

For everything beyond this daily-driving surface, use the shell and `cartograph --help` or `cartograph <command> --help`. The CLI is the source of truth for rollback/delete, cloud ops, config/setup/auth, doctor/stats/dashboard/export/import, and other uncommon or administrative operations.
