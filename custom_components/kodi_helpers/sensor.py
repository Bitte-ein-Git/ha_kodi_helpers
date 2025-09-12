# /config/custom_components/kodi_helpers/sensor.py
from __future__ import annotations
import logging
from datetime import timedelta
import re
import json
from pathlib import Path

from homeassistant.components.sensor import SensorEntity
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
    # setup api connection
    cfg = hass.data[DOMAIN][entry.entry_id]
    api = KodiAPI(cfg['host'], cfg.get('port', 8080), cfg.get('username'), cfg.get('password'), scheme=cfg.get('scheme','http'))

    # load translations
    translations = {}
    lang = hass.config.language
    translation_path = Path(hass.config.config_dir) / f"custom_components/{DOMAIN}/translations/{lang}.json"

    # fallback to english
    if not translation_path.is_file():
        translation_path = Path(hass.config.config_dir) / f"custom_components/{DOMAIN}/translations/en.json"

    # load translations if file exists
    if translation_path.is_file():
        with translation_path.open(encoding='utf-8') as f:
            translations = json.load(f).get("state", {})

    def get_translation(key, placeholders=None):
        if placeholders is None:
            placeholders = {}
        return translations.get(key, key).format(**placeholders)

    async def async_update_data():
        # check kodi connection
        app = await api.get_app_properties()
        if not app or 'result' not in app:
            device_name = f"🍿• Kodi-Helper ({cfg.get('host')})"
            offline_state = get_translation('kodi_offline')
            return {
                'media_type': offline_state,
                'main_info': offline_state,
                'extra_info': offline_state,
                'audio_info': offline_state,
                'device_name': device_name
            }

        # get device name
        device_name = app['result'].get('name') or f"🍿• Kodi-Helper ({cfg.get('host')})"
        
        # check for active players
        players = await api.get_player()
        if not players or not players.get('result'):
            no_playback_state = get_translation('no_playback')
            no_audio_state = get_translation('no_audio_info')
            return {'media_type': no_playback_state, 'main_info': no_playback_state, 'extra_info': no_playback_state, 'audio_info': no_audio_state, 'device_name': device_name}

        playerid = players['result'][0]['playerid']
        item_data = await api.get_item(playerid)
        audio_data = await api.get_audio_info(playerid)
        media_type, main_info, extra_info, audio_info = 'Other', '', '', ''

        if item_data and 'result' in item_data:
            item = item_data['result']['item']
            no_playback_state = get_translation('no_playback')

            if not item.get('title') and item.get('label'):
                # label parsing for tv shows
                label = item.get('label')
                match = re.match(r'^(.*)\sS(\d{1,2})E(\d{1,2})', label, re.IGNORECASE)
                if match:
                    media_type = 'TV Show'
                    main_info = match.group(1).strip()
                    extra_info = f"S{int(match.group(2)):02d}E{int(match.group(3)):02d}"

            if not main_info:
                # default processing for media types
                if item.get('channeltype') == 'tv' or item.get('channel'):
                    media_type = 'Live TV'
                    main_info = (item.get('channel') or '📺 Live TV') + ' ᴵᴾᵀⱽ'
                    extra_info = item.get('title') or '🎬 Live TV'
                elif item.get('type') == 'movie':
                    media_type = 'Movie'
                    main_info = f"{item.get('title','')} ({item.get('year','')})".strip()
                    extra_info = '🎬 Film'
                elif item.get('type') == 'episode' or item.get('tvshowid'):
                    media_type = 'TV Show'
                    main_info = f"{item.get('showtitle','')} ({item.get('year','')})".strip()
                    extra_info = f"S{int(item['season']):02d}E{int(item['episode']):02d} » {item.get('title','')}" if item.get('season') is not None and item.get('episode') is not None else '🎞️ Serie'
                else:
                    media_type, main_info, extra_info = 'Other', item.get('label') or no_playback_state, 'Other'

            # cleanup extra info
            if 'S-1E-1' in extra_info:
                extra_info = ''

            # cleanup main info
            no_tags = re.sub(r'\[.*?\]', '', main_info)
            no_zero = re.sub(r'\s*\(0\)', '', no_tags)
            main_info = no_zero.strip()

        if audio_data and 'result' in audio_data and audio_data['result'].get('audiostreams'):
            # audio info processing
            streams = audio_data['result'].get('audiostreams', [])
            current = audio_data['result'].get('currentaudiostream', {}).get('index')
            no_audio_state = get_translation('no_audio_info')
            if current is not None and current < len(streams):
                stream = streams[current]
                codec = stream.get('codec','').lower()
                channels = stream.get('channels', 0)
                channel_str_map = {
                    2: get_translation('stereo'),
                    6: get_translation('channel_5_1'),
                    8: get_translation('channel_7_1')
                }
                channel_str = channel_str_map.get(channels, get_translation('channel_multi', {"channels": str(channels)}))

                codec_map = {'ac3':'Dolby Digital','eac3':'Dolby Digital+','dts':'DTS','aac':'AAC'}
                codec_str = codec_map.get(codec, codec.upper())
                audio_info = f"{codec_str} | {channel_str}"
            else:
                audio_info = no_audio_state
        
        no_playback_state = get_translation('no_playback')
        return {'media_type': media_type, 'main_info': main_info or no_playback_state, 'extra_info': extra_info, 'audio_info': audio_info, 'device_name': device_name}

    # setup coordinator
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
        # return sensor value
        return self.coordinator.data.get(self._key)

    @property
    def device_info(self):
        # return device info
        scheme = self.entry.options.get("scheme", self.entry.data.get("scheme", "http"))
        return {
            'identifiers': {(DOMAIN, self.entry.entry_id)},
            'name': self.coordinator.data.get('device_name', f"🍿• Kodi-Helper ({self.entry.data.get('host')})"),
            'manufacturer': 'Kodi',
            'model': 'Kodi',
            'configuration_url': f"{scheme}://{self.entry.data.get('host')}:{self.entry.data.get('port',8080)}"
        }