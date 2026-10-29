"""Config flow for Kyiv Vodokanal."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import voluptuous as vol
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

from .api import KyivVodokanalApi, KyivVodokanalAuthError, KyivVodokanalError
from .const import DOMAIN, PORTAL_URL

if TYPE_CHECKING:
    from collections.abc import Mapping

PASSWORD_SELECTOR = TextSelector(
    TextSelectorConfig(type=TextSelectorType.PASSWORD, autocomplete="current-password")
)
USER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_EMAIL): TextSelector(
            TextSelectorConfig(type=TextSelectorType.EMAIL, autocomplete="username")
        ),
        vol.Required(CONF_PASSWORD): PASSWORD_SELECTOR,
    }
)
REAUTH_SCHEMA = vol.Schema({vol.Required(CONF_PASSWORD): PASSWORD_SELECTOR})


class KyivVodokanalConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Kyiv Vodokanal."""

    VERSION = 1

    async def _login(
        self, data: Mapping[str, Any]
    ) -> tuple[str | None, dict[str, str]]:
        """Log in and return the user ID, or form errors."""
        api = KyivVodokanalApi(
            async_get_clientsession(self.hass), data[CONF_EMAIL], data[CONF_PASSWORD]
        )
        try:
            user_id = await api.login()
            # Setup fails later if the account data cannot be read.
            await api.get_accounts()
        except KyivVodokanalAuthError:
            return None, {"base": "invalid_auth"}
        except KyivVodokanalError:
            return None, {"base": "cannot_connect"}
        return user_id, {}

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Ask for the personal account email and password."""
        errors: dict[str, str] = {}
        if user_input is not None:
            user_id, errors = await self._login(user_input)
            if user_id:
                await self.async_set_unique_id(user_id)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=user_input[CONF_EMAIL], data=user_input
                )

        return self.async_show_form(
            step_id="user",
            data_schema=self.add_suggested_values_to_schema(USER_SCHEMA, user_input),
            description_placeholders={"portal_url": PORTAL_URL},
            errors=errors,
        )

    async def async_step_reauth(
        self,
        entry_data: Mapping[str, Any],  # noqa: ARG002
    ) -> ConfigFlowResult:
        """Start reauthentication after the password stopped working."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Ask for the current password."""
        entry = self._get_reauth_entry()
        errors: dict[str, str] = {}
        if user_input is not None:
            user_id, errors = await self._login({**entry.data, **user_input})
            if user_id:
                await self.async_set_unique_id(user_id)
                self._abort_if_unique_id_mismatch()
                return self.async_update_reload_and_abort(
                    entry, data_updates=user_input
                )

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=REAUTH_SCHEMA,
            description_placeholders={"email": entry.data[CONF_EMAIL]},
            errors=errors,
        )
