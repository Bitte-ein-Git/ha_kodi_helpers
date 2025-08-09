from __future__ import annotations
import logging
from homeassistant.components.switch import SwitchEntity
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from .const import DOMAIN
from .api import KodiAPI

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, entry, async_add_entities):
    cfg = hass.data[DOMAIN][entry.entry_id]
    # get coordinator created by sensor platform to access API instance
    coordinator = hass.data[DOMAIN].get(entry.entry_id+'_coordinator')
    api = None
    if coordinator:
        # coordinator closure doesn't expose api, so re-create API for switch control
        api = KodiAPI(cfg['host'], cfg.get('port',8080), cfg.get('username'), cfg.get('password'), scheme=cfg.get('scheme','http'))
    else:
        api = KodiAPI(cfg['host'], cfg.get('port',8080), cfg.get('username'), cfg.get('password'), scheme=cfg.get('scheme','http'))

    async_add_entities([KodiProtocolSwitch(api, entry)])

class KodiProtocolSwitch(SwitchEntity):
    def __init__(self, api: KodiAPI, entry):
        self._api = api
        self.entry = entry
        self._attr_name = f"🍿• Kodi-Helper ({entry.data.get('host')}) - Use HTTPS"
        self._attr_unique_id = f"{entry.entry_id}_use_https"

    @property
    def is_on(self):
        return self._api.scheme == 'https'

    async def async_turn_on(self, **kwargs):
        self._api.set_scheme('https')
        # Changing scheme affects only this runtime API instance.
        # To apply system-wide, user should reload the integration (or we could store setting in entry.options).
        return True

    async def async_turn_off(self, **kwargs):
        self._api.set_scheme('http')
        return True
