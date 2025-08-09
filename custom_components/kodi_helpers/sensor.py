from __future__ import annotations
import logging
from datetime import timedelta

from homeassistant.components.sensor import SensorEntity
# HIER IST DIE WICHTIGE ERGÄNZUNG
from homeassistant.helpers.update_coordinator import CoordinatorEntity, DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN, DEFAULT_SCAN_INTERVAL
from .api import KodiAPI

_LOGGER = logging.getLogger(__name__)

SENSOR_TYPES = {
    "media_type": {"name": "Media Type", "icon": "mdi:movie-open"},
    "main_info": {"name": "Playback Main Info", "icon": "mdi:information-outline"},
    "extra_info": {"name": "Playback Extra Info", "icon": "mdi:information-variant"},
    "audio_info": {"name": "Audio Info", "icon": "mdi:speaker"}
}

async def async_setup_entry(hass, entry, async_add_entities):
    # Die Logik zum Erstellen des Koordinators bleibt unverändert
    cfg = hass.data[DOMAIN][entry.entry_id]
    api = KodiAPI(cfg['host'], cfg.get('port', 8080), cfg.get('username'), cfg.get('password'), scheme=cfg.get('scheme','http'))

    async def async_update_data():
        app = await api.get_app_properties()
        if not app or 'result' not in app:
            # Wenn Kodi nicht erreichbar ist, wird der Sensor als "unavailable" markiert
            raise UpdateFailed("Kodi ist nicht erreichbar.")

        device_name = app['result'].get('name') or f"🍿• Kodi-Helper ({cfg.get('host')})"
        players = await api.get_player()
        if not players or not players.get('result'):
            return {'media_type': 'Keine Wiedergabe', 'main_info': 'Keine Wiedergabe', 'extra_info': 'Keine Wiedergabe', 'audio_info': 'Keine Audio-Infos', 'device_name': device_name}

        playerid = players['result'][0]['playerid']
        item_data = await api.get_item(playerid)
        audio_data = await api.get_audio_info(playerid)
        media_type, main_info, extra_info, audio_info = 'Other', '', '', ''

        if item_data and 'result' in item_data:
            item = item_data['result']['item']
            if item.get('channeltype') == 'tv' or item.get('channel'):
                media_type, main_info, extra_info = 'Live TV', item.get('channel') or '📺 Live TV', item.get('title') or '🎬 Live TV'
            elif item.get('type') == 'movie':
                media_type, main_info, extra_info = 'Movie', f"{item.get('title','')} ({item.get('year','')})".strip(), '🎬 Film'
            elif item.get('type') == 'episode' or item.get('tvshowid'):
                media_type, main_info = 'TV Show', f"{item.get('showtitle','')} ({item.get('year','')})".strip()
                extra_info = f"S{int(item['season']):02d}E{int(item['episode']):02d} » {item.get('title','')}" if item.get('season') is not None and item.get('episode') is not None else '🎞️ Serie'
            else:
                media_type, main_info, extra_info = 'Other', item.get('label') or 'Keine Wiedergabe', 'Other'

        if audio_data and 'result' in audio_data and audio_data['result'].get('audiostreams'):
            streams = audio_data['result'].get('audiostreams', [])
            current = audio_data['result'].get('currentaudiostream', {}).get('index')
            if current is not None and current < len(streams):
                stream = streams[current]
                codec = stream.get('codec','').lower()
                channels = stream.get('channels', 0)
                channel_str = {2: 'Stereo', 6: '5.1-Kanal', 8: '7.1-Kanal'}.get(channels, f"{channels}-Kanal")
                codec_map = {'ac3':'Dolby Digital','eac3':'Dolby Digital+','dts':'DTS','aac':'AAC'}
                codec_str = codec_map.get(codec, codec.upper())
                audio_info = f"{codec_str} | {channel_str}"
            else:
                audio_info = 'Keine Audio-Infos'
        
        return {'media_type': media_type, 'main_info': main_info or 'Keine Wiedergabe', 'extra_info': extra_info, 'audio_info': audio_info, 'device_name': device_name}

    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name='Kodi Helpers Coordinator',
        update_method=async_update_data,
        update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL)
    )
    
    await coordinator.async_config_entry_first_refresh()

    entities = [KodiHelpersSensor(coordinator, entry, key) for key in SENSOR_TYPES]
    async_add_entities(entities)

# Die Sensor-Klasse wird angepasst
class KodiHelpersSensor(CoordinatorEntity, SensorEntity):
    def __init__(self, coordinator, entry, key):
        # super().__init__() stellt die Verknüpfung zum Koordinator her
        super().__init__(coordinator)
        self.entry = entry
        self._key = key
        # Der Name wird jetzt direkt hier gesetzt, da er sich nicht ändert
        self._attr_name = f"{coordinator.data.get('device_name','Kodi')} - {SENSOR_TYPES[key]['name']}"
        self._attr_icon = SENSOR_TYPES[key]['icon']
        self._attr_unique_id = f"{entry.entry_id}_{key}"

    @property
    def native_value(self):
        # Greift auf die vom Koordinator bereitgestellten Daten zu
        return self.coordinator.data.get(self._key)

    @property
    def device_info(self):
        scheme = self.entry.options.get("scheme", self.entry.data.get("scheme", "http"))
        return {
            'identifiers': {(DOMAIN, self.entry.entry_id)},
            'name': self.coordinator.data.get('device_name', f"🍿• Kodi-Helper ({self.entry.data.get('host')})"),
            'manufacturer': 'Kodi',
            'model': 'Kodi',
            'configuration_url': f"{scheme}://{self.entry.data.get('host')}:{self.entry.data.get('port',8080)}"
        }

    # Die Methoden async_update, should_poll und available sind nicht mehr nötig.
    # Das übernimmt alles die CoordinatorEntity für uns.