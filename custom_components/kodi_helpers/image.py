from __future__ import annotations
from homeassistant.components.image import ImageEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util
from homeassistant.util import slugify
from .const import DOMAIN

async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]['coordinator']
    async_add_entities([KodiTMDBSensor(coordinator, entry)])

class KodiTMDBSensor(CoordinatorEntity, ImageEntity):
    def __init__(self, coordinator, entry):
        super().__init__(coordinator)
        ImageEntity.__init__(self, coordinator.hass)
        
        self.entry = entry
        
        # force entity_id based on friendly_name
        fname = entry.data.get("friendly_name", "Kodi")
        self.entity_id = f"image.{slugify(fname)}_tmdb_artwork"
        
        self._attr_name = f"{fname} - TMDB Artwork"
        self._attr_unique_id = f"{entry.entry_id}_tmdb_artwork"
        self._attr_content_type = "image/png"
        self._last_content_key = None

    def _handle_coordinator_update(self) -> None:
        if self.coordinator.data:
            current_key = (
                self.coordinator.data.get('main_info'),
                self.coordinator.data.get('media_type_raw')
            )
            if current_key != self._last_content_key:
                self._attr_image_last_updated = dt_util.utcnow()
                self._last_content_key = current_key
        
        super()._handle_coordinator_update()

    @property
    def image_url(self):
        if not self.coordinator.data:
             return 'https://kodi.heyfordy.de/ha_media/kodi.png'

        raw_title = self.coordinator.data.get('main_info', '')
        media_type_raw = self.coordinator.data.get('media_type_raw', 'offline')
        base = 'https://api.heyfordy.de/tmdb'
        
        if media_type_raw in ['offline', 'idle']:
            return 'https://kodi.heyfordy.de/ha_media/kodi.png'

        if '(' in raw_title and ')' in raw_title:
            try:
                parts = raw_title.split('(')
                title = parts[0].strip()
                year = parts[1].split(')')[0]
            except IndexError:
                title = raw_title
                year = ''
        else:
            year = ''
            title = raw_title

        if media_type_raw in ['movie', 'film']:
            tmdb_type = 'movie'
        else:
            tmdb_type = 'tv'
        
        url = f"{base}?type={tmdb_type}"
        if year:
            url += f"&year={year}"
        
        safe_title = title.replace('"', '')
        url += f'&name="{safe_title}"'
        
        return url

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