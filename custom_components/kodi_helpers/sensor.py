from __future__ import annotations
import logging
from datetime import timedelta, datetime
import re

from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity, DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN, DEFAULT_SCAN_INTERVAL
from .api import KodiAPI

# Third-party library for IMDb access
try:
    from imdb import Cinemagoer
except ImportError:
    Cinemagoer = None

_LOGGER = logging.getLogger(__name__)

SENSOR_TYPES = {
    "media_type": {"name": "Media Type", "icon": "mdi:movie-open"},
    "main_info": {"name": "Playback Main Info", "icon": "mdi:information-outline"},
    "extra_info": {"name": "Playback Extra Info", "icon": "mdi:information-variant"},
    "audio_info": {"name": "Audio Info", "icon": "mdi:speaker"}
}

async def async_setup_entry(hass, entry, async_add_entities):
    cfg = hass.data[DOMAIN][entry.entry_id]
    api = KodiAPI(cfg['host'], cfg.get('port', 8080), cfg.get('username'), cfg.get('password'), scheme=cfg.get('scheme','http'))
    
    # Initialize Cinemagoer instance
    ia = Cinemagoer() if Cinemagoer else None

    async def async_update_data():
        app = await api.get_app_properties()
        if not app or 'result' not in app:
            raise UpdateFailed("Kodi ist nicht erreichbar.")

        device_name = app['result'].get('name') or f"🍿• Kodi-Helper ({cfg.get('host')})"
        players = await api.get_player()
        if not players or not players.get('result'):
            return {'media_type': 'Keine Wiedergabe', 'main_info': 'Keine Wiedergabe', 'extra_info': ' ', 'audio_info': 'Keine Audio-Infos', 'device_name': device_name}

        playerid = players['result'][0]['playerid']
        item_data = await api.get_item(playerid)
        audio_data = await api.get_audio_info(playerid)
        media_type, main_info, extra_info, audio_info = 'Other', '', '', ''

        if item_data and 'result' in item_data:
            item = item_data['result']['item']
            year = item.get('year')

            if not item.get('title') and item.get('label'):
                label = item.get('label')
                match = re.match(r'^(.*)\sS(\d{1,2})E(\d{1,2})', label, re.IGNORECASE)
                if match:
                    media_type = 'TV Show'
                    main_info = match.group(1).strip()
                    extra_info = f"S{int(match.group(2)):02d}E{int(match.group(3)):02d}"

            if not main_info:
                if item.get('channeltype') == 'tv' or item.get('channel'):
                    media_type = 'Live TV'
                    main_info = (item.get('channel') or '📺 Live TV') + ' ᴵᴾᵀⱽ'
                    extra_info = item.get('title') or '🎬 Live TV'
                elif item.get('type') == 'movie':
                    media_type = 'Movie'
                    main_info = f"{item.get('title','')} ({year})".strip()
                    extra_info = '🎬 Film'
                elif item.get('type') == 'episode' or item.get('tvshowid'):
                    media_type = 'TV Show'
                    show_title = item.get('showtitle', '')
                    
                    # IMDb year correction
                    current_year = datetime.now().year
                    if ia and year and year > current_year:
                        try:
                            _LOGGER.debug(f"Incorrect year '{year}' for '{show_title}'. Querying IMDb.")
                            search_results = await hass.async_add_executor_job(ia.search_movie, show_title)
                            if search_results:
                                movie = search_results[0]
                                await hass.async_add_executor_job(ia.update, movie)
                                if movie.get('year'):
                                    year = movie.get('year')
                                    _LOGGER.debug(f"IMDb corrected year to '{year}' for '{show_title}'.")
                        except Exception as e:
                            _LOGGER.warning(f"IMDb search failed for '{show_title}': {e}")

                    main_info = f"{show_title} ({year})".strip()
                    extra_info = f"S{int(item['season']):02d}E{int(item['episode']):02d} » {item.get('title','')}" if item.get('season') is not None and item.get('episode') is not None else '🎞️ Serie'
                else:
                    media_type, main_info, extra_info = 'Other', item.get('label') or ' ', 'Other'

            if 'S-1E-1' in extra_info:
                extra_info = ''

            no_tags = re.sub(r'\[.*?\]', '', main_info)
            no_zero = re.sub(r'\s*\(0\)', '', no_tags)
            main_info = no_zero.strip()

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
