"""Config flow for melsmart."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .client import MelSmartClient, MelSmartError
from .const import (
    CONF_HOST,
    CONF_NAME,
    CONF_SCAN_INTERVAL,
    DEFAULT_NAME,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    MAX_SCAN_INTERVAL,
    MIN_SCAN_INTERVAL,
)
from .protocol import LossnayStatus, probe_error

_LOGGER = logging.getLogger(__name__)

STEP_USER = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): str,
    }
)


def _options_schema(host: str, name: str, interval: int) -> vol.Schema:
    return vol.Schema(
        {
            vol.Required(CONF_HOST, default=host): str,
            vol.Optional(CONF_NAME, default=name): str,
            vol.Required(CONF_SCAN_INTERVAL, default=interval): vol.All(
                vol.Coerce(int),
                vol.Range(min=MIN_SCAN_INTERVAL, max=MAX_SCAN_INTERVAL),
            ),
        }
    )


async def _async_probe(hass, host: str) -> tuple[LossnayStatus | None, bool]:
    session = async_get_clientsession(hass)
    client = MelSmartClient(host, session)
    try:
        return await client.async_status(), False
    except MelSmartError:
        _LOGGER.exception("Cannot reach Mitsubishi /smart at %s", host)
        return None, True


class MelSmartConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Add a Lossnay adapter by IP."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> MelSmartOptionsFlow:
        return MelSmartOptionsFlow(config_entry)

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            host = user_input[CONF_HOST].strip()
            name = (user_input.get(CONF_NAME) or DEFAULT_NAME).strip()
            status, failed = await _async_probe(self.hass, host)
            error = probe_error(status, failed=failed)
            if error == "not_lossnay":
                return self.async_abort(reason="not_lossnay")
            if error:
                errors["base"] = error
            else:
                assert status is not None and status.unique_id is not None
                await self.async_set_unique_id(status.unique_id)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=name,
                    data={CONF_HOST: host, CONF_NAME: name},
                    options={CONF_SCAN_INTERVAL: DEFAULT_SCAN_INTERVAL},
                )

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER, errors=errors
        )


class MelSmartOptionsFlow(config_entries.OptionsFlow):
    """Change host, name, or poll interval after setup."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        self._config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        errors: dict[str, str] = {}
        entry = self._config_entry
        if user_input is not None:
            host = user_input[CONF_HOST].strip()
            name = (user_input.get(CONF_NAME) or DEFAULT_NAME).strip()
            interval = user_input[CONF_SCAN_INTERVAL]
            if host != entry.data[CONF_HOST]:
                status, failed = await _async_probe(self.hass, host)
                error = probe_error(status, failed=failed)
                if error:
                    errors["base"] = error
                elif status is None or status.unique_id != entry.unique_id:
                    errors["base"] = "wrong_device"
            if not errors:
                self.hass.config_entries.async_update_entry(
                    entry,
                    title=name,
                    data={CONF_HOST: host, CONF_NAME: name},
                )
                return self.async_create_entry(
                    title="",
                    data={CONF_SCAN_INTERVAL: interval},
                )

        return self.async_show_form(
            step_id="init",
            data_schema=_options_schema(
                entry.data[CONF_HOST],
                entry.data.get(CONF_NAME, DEFAULT_NAME),
                entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
            ),
            errors=errors,
        )
