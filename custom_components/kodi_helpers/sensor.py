from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.device_registry import DeviceInfo

from .const import DOMAIN

SENSOR_TYPES = {
    "media_type": {"name": "Media Type", "icon": "mdi:movie-open"},
    "main_info": {"name": "Playback Main Info", "icon": "mdi:information-outline"},
    "extra_info": {"name": "Playback Extra Info", "icon": "mdi:information-variant"},
    "audio_info": {"name": "Audio Info", "icon": "mdi:speaker"}
}

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the sensor entities."""
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    
    entities = [
        KodiHelpersSensor(coordinator, entry, key) 
        for key in SENSOR_TYPES
    ]
    async_add_entities(entities)


class KodiHelpersSensor(CoordinatorEntity, SensorEntity):
    """Representation of a Kodi Helpers Sensor."""

    def __init__(self, coordinator, entry: ConfigEntry, key: str):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.entry = entry
        self._key = key
        
        # Attribute für den Sensor
        self._attr_name = SENSOR_TYPES[key]['name']
        self._attr_icon = SENSOR_TYPES[key]['icon']
        self._attr_unique_id = f"{entry.unique_id}_{key}"

    @property
    def native_value(self) -> str | None:
        """Return the state of the sensor."""
        return self.coordinator.data.get(self._key)

    @property
    def device_info(self) -> DeviceInfo:
        """Return the device info."""
        return DeviceInfo(
            identifiers={(DOMAIN, self.entry.unique_id)},
            name=self.entry.title, # z.B. "🍿• Kodi-Helpers (192.168.1.10)"
            manufacturer="Kodi Helpers Team",
            model="JSON-RPC API Helper",
            sw_version=self.hass.data["integrations"][DOMAIN].version,
            configuration_url=f"http://{self.entry.data['host']}:{self.entry.data['port']}",
        )