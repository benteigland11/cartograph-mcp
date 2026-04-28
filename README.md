# cartograph-mcp

[![CI](https://github.com/benteigland11/cartograph-mcp/actions/workflows/ci.yml/badge.svg)](https://github.com/benteigland11/cartograph-mcp/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/cartograph-mcp?cacheSeconds=60)](https://pypi.org/project/cartograph-mcp/)

mcp-name: io.github.benteigland11/cartograph

Sick and tired of vibe coding the same solutions **over and over** again? So are we! Time to stop spending money on **redundant tokens** and start spending it on **innovate solutions**.

This MCP server is for [Cartograph](https://github.com/benteigland11/Cartograph) that exposes the daily widget workflow for agents without mirroring the entire CLI. On installation of the MCP the CLI will be installed automatically. Once you have it, Search, inspect, install, create, validate, check in, custom rules, and configure Cartograph defaults through a compact agent-facing surface, then fall back to the CLI for the full administrative and recovery surface.

It is highly recommended to use the [plugins](https://github.com/benteigland11/cartograph-plugins) for the skills that go with this MCP. It will give your agent what it needs to explain a lot of the configuration and give you a very powerful workflow tool.

## Why this exists

I personally have spent hours and hours working on solutions I'm proud of, only to hit a wall trying to get the same one done. The reality was prompting was never good enough, I needed a way to know my llama.cpp server client integration was going to be the same everytime I used it. I also needed to know that when I found an improvement, that improvement would stick.

If you are sick and tired of wasting money and time on redoing things you've done before, like a **mouse on a wheel** then get your agents to start using Cartograph.

The Cartograph CLI is the source of truth, but agents do better when the common path is small and explicit.

This MCP keeps the top-level tool surface focused on daily driving:

- finding reusable widgets
- inspecting and installing them
- managing installed widget copies
- creating new widgets
- validating and checking them back in
- adjusting the core Cartograph defaults that affect normal workflow

Everything else stays in the CLI. That keeps the MCP easier to teach, easier to test, and less likely to drift into a second full interface.

## Quick start

```bash
pip install cartograph-mcp
```

Claude Desktop example:

```json
{
  "mcpServers": {
    "cartograph": {
      "command": "cartograph-mcp"
    }
  }
}
```

The package depends on `cartograph-cli` and shells out to it as the source of truth for the full command surface.

Common CLI setup commands:

```bash
# Claude Code
claude mcp add cartograph --scope user -- cartograph-mcp

# Codex
codex mcp add cartograph -- cartograph-mcp

# Gemini CLI
gemini mcp add cartograph cartograph-mcp

# Cursor
cursor --add-mcp '{"name":"cartograph","command":"cartograph-mcp"}'
```

Claude Code expects an explicit scope flag such as `--scope user`.

## Tool surface

The MCP intentionally exposes a small workflow-oriented surface:

- `registry_widget`
  Actions: `search`, `inspect`, `install`, `rate`
- `installed_widget`
  Actions: `upgrade`, `uninstall`
- `widget_status`
- `create_widget`
- `validate_widget`
- `checkin_widget`
- `cartograph_config`
- `cartograph_rules`

These are not a 1:1 mirror of the CLI. They are grouped around agent intent:

- registry-facing work
- installed-widget mutation
- project health/status
- widget authoring
- workflow configuration
- custom validation rules

## Example workflow

```text
1. Search the registry before writing logic.
2. Inspect the widget you want to reuse.
3. Install it into the project.
4. If no existing widget fits, create one.
5. Validate it with the full dry-run pipeline.
6. Check it in with a reason once it is ready.
```

In Cartograph terms:

- `registry_widget` handles discovery and install
- `installed_widget` handles already-installed widget paths like `cg/backend_retry_python`
- `validate_widget` is the dry run for `checkin_widget`
- `cartograph_config` manages the defaults that change how your day-to-day loop behaves
- `cartograph_rules` manages custom rules that run during validate and checkin

## Philosophy

This MCP is deliberately not the whole CLI.

The common path belongs in MCP. The official full surface belongs in `cartograph`.

For uncommon, administrative, or recovery operations, use:

```bash
cartograph --help
cartograph <command> --help
```

That includes things like rollback/delete, cloud operations, auth, setup, rules, doctor, export/import, and other non-daily commands.

## Configuration

`cartograph_config` exposes the workflow defaults that matter most to agents:

- `auto-publish`
- `visibility`
- `governance`
- `cloud`
- `show-unavailable`
- `publish-registry`

Reading and writing config is done through the CLI's `--json` path so MCP can consume it safely.

## Testing

This package is tested in two layers:

- command-contract tests that mock the CLI runner and assert the exact commands the MCP builds
- isolated integration tests that run the real Cartograph CLI in a temporary environment

The integration suite isolates:

- `HOME`
- `XDG_CONFIG_HOME`
- `XDG_DATA_HOME`
- `XDG_CACHE_HOME`
- `WIDGET_LIBRARY_PATH`
- project working directory

That means validate/checkin/install flows are exercised without touching the real widget library or user config on the machine running tests.


## Development

```bash
pip install -e .
pytest -q
```

The repo includes:

- `ci.yml` for normal test/build validation on pushes and pull requests
- `pypi-publish.yml` for automated release publishing after a successful version-bump CI run

For the full product story and complete CLI surface, see [Cartograph](https://github.com/benteigland11/Cartograph).
