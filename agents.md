# AI Coding Agents Guide

## Purpose

Agents act as senior Python collaborators. Keep responses concise,
clarify uncertainty before coding, and align suggestions with the rules linked below.

## Project Overview

This repository is a Home Assistant custom integration providing water meter and billing data from [Kyivvodokanal](https://vodokanal.kiev.ua). Main codebase lives under `custom_components/kyiv_vodokanal`.

API research lives in `docs/` (`api.md`, `mobile-api.md`, `data-model.md`, `home-assistant.md`). Read it before changing data fetching or auth.

### Code structure

v1 scope and Ukrainian names are defined in `docs/ha-options.md`.

- `translations` — `en.json` (complete fallback) and `uk.json`.
- `__init__.py` — builds the API client and coordinator, refreshes, sets `entry.runtime_data`, forwards the sensor platform.
- `api/` — Kyivvodokanal API package; no HA dependencies. Import from `.api` (re-exports in `__init__.py`).
  - `client.py` — aiohttp client, login/re-login.
  - `const.py` — base URL, provider group, endpoint `PATHS`.
  - `exceptions.py` — `KyivVodokanalError` and subclasses.
  - `models.py` — dataclasses (`Account`, `Meter`, `Balance`, `InvoiceRow`, `Payment`, `Tariff`).
- `config_flow.py` — email/password step and reauth; unique ID is the JWT `sub` (user ID).
- `const.py` — constants, lookback windows, tariff codes.
- `coordinator.py` — `KyivVodokanalCoordinator`, `KyivVodokanalData`, typed entry alias, and pure derived-value helpers (`unpaid_previous`, `last_payment`, `tariffs_by_key`).
- `sensor.py` — meter and personal-account sensor descriptions and entities, with device info.
- `diagnostics.py` — redacted config entry diagnostics.
- `icons.json` — entity icons by `translation_key` (use instead of `icon=` in descriptions).
- `brand/` — integration icon and logo PNGs (HA 2026.3+), rendered from SVGs in `assets/`: logos from vodokanal.kyiv.ua, icon from Wikimedia Commons (`KyivVodokanal.svg`, CC0). Re-render all PNGs after replacing them.
- `manifest.json` — HA manifest.
- `tests/test_parsing.py` — parser and helper tests on synthetic data (`uv run pytest`).

### Using Coordinator to Fetch Data

Use DataUpdateCoordinator to fetch data from the Kyivvodokanal API. Create coordinators in `__init__.py` during setup and keep them in `entry.runtime_data`. Platforms (e.g., `sensor.py`) read from there.

The coordinator:

- Receives the shared API client (dependency injection).
- Re-logs in silently when the JWT is near expiry or a data call returns 401 (see `docs/home-assistant.md`).
- Prefer logging and returning `None`/fallbacks instead of raising; add debug logs when behavior is unclear.
- Keep coordinator instances in `entry.runtime_data`; avoid globals/singletons.

Documentation: https://developers.home-assistant.io/docs/integration_fetching_data

### Decouple API Data from Coordinator

Coordinator should not rely on API response structure. Instead, transform data into plain Python objects (e.g., dataclasses) on API class level, so coordinator only calls API methods and works with stable data structures.

### API

External API: `https://warreg.ssmt.com.ua:5443` (mobile backend; same API as `https://my.vodokanal.kiev.ua`), cloud polling. Email/password login (`POST /api/account/authentication`, no reCAPTCHA) returns a 7-day bearer JWT; no refresh endpoint. All HTTP and parsing lives in `api/`.

Never submit readings, payments, verification applications, or profile changes during development; those endpoints write real data.

## Runtime Data

- `entry.runtime_data` is the single `KyivVodokanalCoordinator` of the login; the coordinator holds the API client as `coordinator.api`.
- Use the typed alias `type KyivVodokanalConfigEntry = ConfigEntry[KyivVodokanalCoordinator]` (in `coordinator.py`) in function signatures.
- Initialization happens in `__init__.py`: build the API client, create and refresh the coordinator, then set `entry.runtime_data`.
- Platforms (e.g., `sensor.py`) read `config_entry.runtime_data.data`.

This pattern keeps setup logic centralized, avoids globals, and makes platform code simple and testable.

## Workflow

- Python deps defined in `pyproject.toml`, locked in `uv.lock`; manage env with `uv`.
- CI (`lint.yml`, `validate.yml`) installs uv via `astral-sh/setup-uv` and runs tools with `uv run`.
- Use `scripts/bootstrap` for fresh setup (installs uv via pipx if missing, syncs deps, installs pre-commit).
- Prefer running tooling via `uv run <tool>` to match the locked environment.

<instruction>Keep this guide synced when tooling, workflows, or runtime data structures change.</instruction>

This project is developed from Devcontainer described in `.devcontainer.json` file.

- **Adding/changing data fetching**
  - Extend `api/` first; return Python objects (dataclasses) independent of raw JSON.
  - Use/extend `coordinator.py` to compute derived values.
  - Keep all shared runtime stuff (API client, coordinators) in `entry.runtime_data`.
- **Entities and platforms**
  - Add new sensor descriptors in `sensor.py` (use `translation_key`).
  - Build unique IDs from stable API identifiers (e.g., meter ID); never from names or account numbers alone (not unique, see `docs/data-model.md`).
- **Config flow**
  - Email/password step; validate by logging in and fetching accounts before creating the entry.
  - Reauth flow on login 401; must not switch to a different account.
- **Migrations**
  - None yet. Add a migration step whenever the stored config entry schema changes.
- **Translations**
  - Edit `translations/*.json` directly. Update Inlang configuration when needed.
  - Translate values only; keep keys the same. Preserve placeholders.
- **When unsure**
  - Prefer adding debug logs and ask for the output to reason about runtime state.

### Develompent Scripts

- `scripts/bootstrap` - sets up development environment.
- `scripts/setup` - installs dependencies and installs pre-commit.
- `scripts/develop` - starts a development Home Assistant instance.
- `scripts/lint` - runs a ruff linter/formatter.
- `uv run pytest` - runs tests in `tests/`.

### Development Process

- Ask for clarification when requirements are ambiguous; surface 2–3 options when trade-offs matter.
- Update documentation and related rules when introducing new patterns or services.
- When unsure or need to make a significant decision ASK the user for guidance.
- Each time you make changes to Python code, run `scripts/lint` to check for errors and formatting issues. Fix any issues reported by the linter.
- Commit only when directly asked to do so. Write descriptive commit messages.

## Code Style

Use code style described in `pyproject.toml` configuration. Standard Python. 2-spaces indentation.

Never import modules in functions. All imports must be located on top of the file.

## Translations

- Translations: copy `translations/en.json` to add locales; translate values only where appropriate per HA guidelines.
- Entities: Use the `translation_key` defined in the sensor descriptions.
- Ukrainian (`uk.json`) entity and device names must match the labels in the Kyivvodokanal personal dashboard (my.vodokanal.kiev.ua), so users recognize the values. See the mapping in `docs/ha-options.md`. Invent a name only when the portal has no label, and mark it as proposed there.
- Placeholders: Reference values from `translation_placeholders` when rendering names or descriptions.
- Add locales by copying `translations/en.json` and translating values per HA guidelines.

## Home Assistant API

Carefully read links to the Home Assistant Developer documentation for guidance.

Fetch these links to get more informations about specific Home Assistant APIs directly from its documentation:

- File structure: https://developers.home-assistant.io/docs/creating_integration_file_structure
- Config Flow: https://developers.home-assistant.io/docs/config_entries_config_flow_handler
- Fetching data: https://developers.home-assistant.io/docs/integration_fetching_data
- Repairs: https://developers.home-assistant.io/docs/core/platform/repairs
- Sensor: https://developers.home-assistant.io/docs/core/entity/sensor
- Config Entries: https://developers.home-assistant.io/docs/config_entries_index
- Data Entry Flow: https://developers.home-assistant.io/docs/data_entry_flow_index
- Manifest: https://developers.home-assistant.io/docs/creating_integration_manifest

## Important directives

<important>
In all interactions and commit messages, be extremely concise and sacrifice grammar for the sake of concision.
</important>

<important>
If anything here is unclear (e.g., adding a new platform beyond sensors and calendar, or debugging with `debugpy`), tell me what you want to do and I'll expand these instructions.
</important>

<important>
If you struggle to find a solution, suggest to add logger statements and ask for output to get more context and understand the flow better. When logger output is provided, analyze it to understand what is going on.
</important>

<important>
When updating this file (`agents.md`), DON'T CHANGE the structure, formatting or style of the document. Just add relevant information, without restructuring: add list items, new sections, etc. NEVER REMOVE tags, like <important> or <instruction>.
</important>

<important>
At the end of each plan, give me a list of unresolved questions to answer, if any. Make the questions extremely concise. Sacrifice grammar for the sake of concision.
</important>
