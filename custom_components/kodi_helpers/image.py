from __future__ import annotations
from homeassistant.components.image import ImageEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util
from .const import DOMAIN

async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]['coordinator']
    async_add_entities([KodiTMDBSensor(coordinator, entry)])

class KodiTMDBSensor(CoordinatorEntity, ImageEntity):
    def __init__(self, coordinator, entry):
        super().__init__(coordinator)
        # ImageEntity muss manuell initialisiert werden für Access Tokens
        ImageEntity.__init__(self, coordinator.hass)
        
        self.entry = entry
        self._attr_name = f"{coordinator.data.get('device_name','Kodi')} - TMDB Artwork"
        self._attr_unique_id = f"{entry.entry_id}_tmdb_artwork"
        self._attr_content_type = "image/png"
        self._last_content_key = None

    def _handle_coordinator_update(self) -> None:
        """Prüft auf Änderungen und setzt den Timestamp für Frontend-Refresh."""
        if self.coordinator.data:
            # Wir bauen einen Key aus Titel und Typ
            current_key = (
                self.coordinator.data.get('main_info'),
                self.coordinator.data.get('media_type_raw')
            )
            
            # Nur wenn sich was ändert, Timestamp aktualisieren -> zwingt Frontend zum Neuladen
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
        
        # Fallback bei Offline/Idle
        if media_type_raw in ['offline', 'idle']:
            return 'https://kodi.heyfordy.de/ha_media/kodi.png'

        # Titel und Jahr parsen
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

        # Typ bestimmen
        if media_type_raw in ['movie', 'film']:
            tmdb_type = 'movie'
        else:
            tmdb_type = 'tv'
        
        # URL bauen
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
