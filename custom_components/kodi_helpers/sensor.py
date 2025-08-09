from __future__ import annotations
import logging
from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from datetime import timedelta
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
    cfg = hass.data[DOMAIN][entry.entry_id]
    api = KodiAPI(cfg['host'], cfg.get('port', 8080), cfg.get('username'), cfg.get('password'), scheme=cfg.get('scheme','http'))

    async def async_update_data():
        # Check app properties to get device name and availability
        app = await api.get_app_properties()
        if not app or 'result' not in app:
            # Kodi unreachable
            return {
                'available': False,
                'media_type': 'Keine Wiedergabe',
                'main_info': 'Keine Wiedergabe',
                'extra_info': 'Keine Wiedergabe',
                'audio_info': 'Keine Audio-Infos',
                'device_name': f"🍿• Kodi-Helper ({cfg.get('host')})"
            }

        device_name = app['result'].get('name') or f"🍿• Kodi-Helper ({cfg.get('host')})"

        players = await api.get_player()
        if not players or not players.get('result'):
            return {
                'available': True,
                'media_type': 'Keine Wiedergabe',
                'main_info': 'Keine Wiedergabe',
                'extra_info': 'Keine Wiedergabe',
                'audio_info': 'Keine Audio-Infos',
                'device_name': device_name
            }

        playerid = players['result'][0]['playerid']
        item_data = await api.get_item(playerid)
        audio_data = await api.get_audio_info(playerid)

        media_type = 'Other'
        main_info = ''
        extra_info = ''
        audio_info = ''

        if item_data and 'result' in item_data:
            item = item_data['result']['item']
            # Live TV (channeltype == 'tv' or presence of 'channel')
            if item.get('channeltype') == 'tv' or item.get('channel'):
                media_type = 'Live TV'
                main_info = item.get('channel') or '📺 Live TV'
                extra_info = item.get('title') or '🎬 Live TV'
            elif item.get('type') == 'movie':
                media_type = 'Movie'
                main_info = f"{item.get('title','')} ({item.get('year','')})".strip()
                extra_info = '🎬 Film'
            elif item.get('type') == 'episode' or item.get('tvshowid'):
                media_type = 'TV Show'
                main_info = f"{item.get('showtitle','')} ({item.get('year','')})".strip()
                if item.get('season') is not None and item.get('episode') is not None:
                    extra_info = f"S{int(item['season']):02d}E{int(item['episode']):02d} » {item.get('title','')}"
                else:
                    extra_info = '🎞️ Serie'
            else:
                media_type = 'Other'
                main_info = item.get('label') or 'Keine Wiedergabe'
                extra_info = media_type

        if audio_data and 'result' in audio_data:
            streams = audio_data['result'].get('audiostreams', [])
            current = audio_data['result'].get('currentaudiostream', {}).get('index')
            if streams and current is not None and current < len(streams):
                codec = streams[current].get('codec','').lower()
                channels = streams[current].get('channels', 0)
                channel_str = {2: 'Stereo', 6: '5.1', 8: '7.1'}.get(channels, f"{channels}-Kanal")
                codec_map = {'ac3':'Dolby Digital','eac3':'Dolby Digital+','dts':'DTS','aac':'AAC'}
                codec_str = codec_map.get(codec, codec.upper())
                audio_info = f"{codec_str} {channel_str}"
            else:
                audio_info = 'Keine Audio-Infos'

        return {
            'available': True,
            'media_type': media_type,
            'main_info': main_info or 'Keine Wiedergabe',
            'extra_info': extra_info or media_type,
            'audio_info': audio_info,
            'device_name': device_name
        }

    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name='Kodi Helpers Coordinator',
        update_method=async_update_data,
        update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL)
    )

    # store coordinator so other platforms can access API if needed (e.g., the switch)
    hass.data[DOMAIN][entry.entry_id+'_coordinator'] = coordinator

    await coordinator.async_config_entry_first_refresh()

    entities = [KodiHelpersSensor(coordinator, entry, key) for key in SENSOR_TYPES]
    async_add_entities(entities)

class KodiHelpersSensor(SensorEntity):
    def __init__(self, coordinator, entry, key):
        self.coordinator = coordinator
        self.entry = entry
        self._key = key
        self._attr_name = f"{coordinator.data.get('device_name','Kodi')} - {SENSOR_TYPES[key]['name']}"
        self._attr_icon = SENSOR_TYPES[key]['icon']
        self._attr_unique_id = f"{entry.entry_id}_{key}"

    @property
    def native_value(self):
        return self.coordinator.data.get(self._key)

    @property
    def available(self):
        return bool(self.coordinator.data.get('available', False))

    @property
    def device_info(self):
        # Put all sensors under one device (the kodi instance)
        return {
            'identifiers': {(DOMAIN, self.entry.entry_id)},
            'name': self.coordinator.data.get('device_name', f"🍿• Kodi-Helper ({self.entry.data.get('host')})"),
            'manufacturer': 'Kodi',
            'model': 'Kodi',
            'configuration_url': f"http://{self.entry.data.get('host')}:{self.entry.data.get('port',8080)}"
        }

    async def async_update(self):
        await self.coordinator.async_request_refresh()

    @property
    def should_poll(self):
        return False
