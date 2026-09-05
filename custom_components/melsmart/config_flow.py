"""Config flow for melsmart."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .client import MelSmartClient, MelSmartError
from .const import CONF_HOST, CONF_NAME, DEFAULT_NAME, DOMAIN

_LOGGER = logging.getLogger(__name__)

STEP_USER = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): str,
    }
)


class MelSmartConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Add a Lossnay adapter by IP."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            host = user_input[CONF_HOST].strip()
            name = (user_input.get(CONF_NAME) or DEFAULT_NAME).strip()
            session = async_get_clientsession(self.hass)
            client = MelSmartClient(host, session)
            try:
                status = await client.async_status()
            except MelSmartError:
                _LOGGER.exception("Cannot reach Mitsubishi /smart at %s", host)
                errors["base"] = "cannot_connect"
            else:
                unique = status.unique_id or host
                await self.async_set_unique_id(unique)
                self._abort_if_unique_id_configured()
                title = name
                if status.device_class == 0x34:
                    title = name
                return self.async_create_entry(
                    title=title,
                    data={CONF_HOST: host, CONF_NAME: name},
                )

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER, errors=errors
        )
