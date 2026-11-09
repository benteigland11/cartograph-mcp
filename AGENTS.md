# cartograph-mcp

MCP server that exposes the Cartograph CLI to agents (PyPI `cartograph-mcp`,
module `cartograph_mcp.server`). It wraps CLI commands; it does not
re-implement them (`cg_help` serves local FAQ entries). The CLI owns the logic.

Source of truth for commands and flags: `cartograph --help` and
`cartograph <command> --help`. Do not copy the command list into this file.
Domain, language, and config enums are derived from the CLI in code (below).

## Rules

- **Enums come from the CLI.** DOMAINS / LANGUAGES / CONFIG_KEYS are derived
  at server start via `_cli_enums()` (subprocess). A guard test requires
  `ENUM_SOURCE == "cli"`; the hardcoded boot fallback must not silently take over.
- **JSON contract:** the MCP tools that shell out (search, inspect, install,
  rate, uninstall, upgrade, status, create, validate, checkin, blueprint)
  parse JSON from the CLI. `cg_config` and `cg_rules` call `config` and
  `rules` with `--json`. `cg_help` reads local FAQ data and is not a CLI
  command. stats, rollback, login, doctor, setup, and cloud
  publish/sync/proposals stay off the MCP surface.
- **Release order:** a `cartograph-cli>=X` floor bump lands only after X is
  live on PyPI (check the PyPI listing; the simple index lags the JSON API by
  minutes). Pushing early breaks this repo's CI on dependency resolution.
- Don't bump this package for a plugin skill-only change; bump it only when
  the CLI flags agents actually pass have changed.

## Using Cartograph while working here (workflow)

1. Plan the components before building.
2. Prefer improving a widget you already use; read it before deciding.
3. Search the library before writing new logic.
4. Install widgets, then write glue. Don't edit widget source for wiring.
5. Edit a widget only to check it back in as a general improvement.
6. Validate before checking in; check in before publishing.

Reusable code is any code another project would write. Peel back "project
specific" logic: much of it is a widget.

## Repo rules

- All changes by PR; never push to the default branch. Only Ben merges or releases.
- No `git reset --hard` / `git clean -f` over work that isn't yours; stash first.
- No em dashes. Targeted tests on small changes, full suite before a PR is ready.
