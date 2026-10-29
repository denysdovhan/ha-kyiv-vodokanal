"""Diagnostics for Kyiv Vodokanal."""

from __future__ import annotations

from dataclasses import asdict
from typing import TYPE_CHECKING, Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

    from .coordinator import KyivVodokanalConfigEntry

# Account and meter identifiers, plus the email used as entry title.
TO_REDACT = {CONF_EMAIL, CONF_PASSWORD, "code", "id", "number", "title", "unique_id"}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant,  # noqa: ARG001
    entry: KyivVodokanalConfigEntry,
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    data = entry.runtime_data.data
    return {
        "entry": async_redact_data(entry.as_dict(), TO_REDACT),
        # Lists, not the dicts keyed by account code / meter ID, so keys get no IDs.
        "accounts": async_redact_data(
            [asdict(account) for account in data.accounts.values()], TO_REDACT
        ),
        "meters": async_redact_data(
            [asdict(meter) for meter in data.meters.values()], TO_REDACT
        ),
        "last_sync": data.last_sync,
    }
