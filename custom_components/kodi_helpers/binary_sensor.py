from __future__ import annotations
from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .const import DOMAIN

async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]['coordinator']
    async_add_entities([KodiKeyboardSensor(coordinator, entry)])

class KodiKeyboardSensor(CoordinatorEntity, BinarySensorEntity):
    def __init__(self, coordinator, entry):
        super().__init__(coordinator)
        self.entry = entry
        self._attr_name = f"{coordinator.data.get('device_name','Kodi')} - Keyboard"
        self._attr_icon = "mdi:keyboard"
        self._attr_unique_id = f"{entry.entry_id}_keyboard"

    @property
    def is_on(self):
        return self.coordinator.data.get('keyboard_visible', False)

    @property
    def device_info(self):
        scheme = self.entry.options.get("scheme", self.entry.data.get("scheme", "http"))
        return {
            'identifiers': {(DOMAIN, self.entry.entry_id)},
            'name': self.coordinator.data.get('device_name'),
            'manufacturer': 'Kodi',
            'model': 'Kodi',
            'configuration_url': f"{scheme}://{self.entry.data.get('host')}:{self.entry.data.get('port',8080)}"
        }