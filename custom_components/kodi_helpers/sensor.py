from __future__ import annotations
from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .const import DOMAIN

SENSOR_TYPES = {
    "media_type": {"name": "Media Type", "icon": "mdi:movie-open"},
    "main_info": {"name": "Playback Main Info", "icon": "mdi:information-outline"},
    "extra_info": {"name": "Playback Extra Info", "icon": "mdi:information-variant"},
    "audio_info": {"name": "Audio Info", "icon": "mdi:speaker"}
}

async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]['coordinator']
    entities = [KodiHelpersSensor(coordinator, entry, key) for key in SENSOR_TYPES]
    async_add_entities(entities)

class KodiHelpersSensor(CoordinatorEntity, SensorEntity):
    def __init__(self, coordinator, entry, key):
        super().__init__(coordinator)
        self.entry = entry
        self._key = key
        self._attr_name = f"{coordinator.data.get('device_name','Kodi')} - {SENSOR_TYPES[key]['name']}"
        self._attr_icon = SENSOR_TYPES[key]['icon']
        self._attr_unique_id = f"{entry.entry_id}_{key}"

    @property
    def native_value(self):
        # get value safely
        return self.coordinator.data.get(self._key)

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