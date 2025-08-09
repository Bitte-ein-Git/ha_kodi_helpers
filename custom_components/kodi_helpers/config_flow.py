from __future__ import annotations
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult
from .const import DOMAIN, DEFAULT_PORT, DEFAULT_USERNAME, DEFAULT_PASSWORD

class KodiHelpersConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None) -> FlowResult:
        errors = {}
        if user_input is not None:
            data = dict(user_input)
            data.setdefault("scheme", "http")
            return self.async_create_entry(title=f"🍿• Kodi-Helper ({data.get('host')})", data=data)

        data_schema = vol.Schema({
            vol.Required("host"): str,
            vol.Optional("port", default=DEFAULT_PORT): int,
            vol.Optional("username", default=DEFAULT_USERNAME): str,
            vol.Optional("password", default=DEFAULT_PASSWORD): str,
            vol.Optional("scheme", default="http"): vol.In(["http","https"])
        })

        return self.async_show_form(step_id="user", data_schema=data_schema, errors=errors)
