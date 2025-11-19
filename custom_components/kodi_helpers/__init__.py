from __future__ import annotations
import logging
import re
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN, PLATFORMS, DEFAULT_SCAN_INTERVAL
from .api import KodiAPI

_LOGGER = logging.getLogger(__name__)

async def async_setup(hass: HomeAssistant, config: ConfigType):
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {}
    
    cfg = {
        "host": entry.data.get("host"),
        "port": entry.data.get("port", 8080),
        "username": entry.data.get("username"),
        "password": entry.data.get("password"),
        "scheme": entry.options.get("scheme", entry.data.get("scheme", "http")),
    }
    
    api = KodiAPI(cfg['host'], cfg['port'], cfg['username'], cfg['password'], scheme=cfg['scheme'])

    # Hardcoded English strings - no more json loading
    TXT = {
        "no_playback": "No Playback",
        "no_audio_info": "No Audio Info",
        "kodi_offline": "Kodi offline",
        "stereo": "Stereo",
        "channel_5_1": "5.1-Channel",
        "channel_7_1": "7.1-Channel",
        "movie": "🎬 Movie",
        "tv_show": "🎞️ TV Show",
        "live_tv": "📺 Live TV",
        "keyboard": "⌨️ Keyboard"
    }

    async def async_update_data():
        data = {
            'media_type': TXT['kodi_offline'],
            'media_type_raw': 'offline',
            'main_info': TXT['kodi_offline'],
            'extra_info': TXT['kodi_offline'],
            'audio_info': TXT['kodi_offline'],
            'device_name': f"🍿• Kodi-Helper ({cfg.get('host')})",
            'keyboard_visible': False
        }

        # check kodi connection & properties
        app = await api.get_app_properties()
        if not app or 'result' not in app:
            return data

        data['device_name'] = app['result'].get('name') or data['device_name']

        # check keyboard
        gui = await api.get_gui_properties()
        if gui and 'result' in gui:
            # 10103=VirtualKeyboard, 10104=NumericInput
            win_id = gui['result'].get('currentwindow', {}).get('id')
            data['keyboard_visible'] = win_id in [10103, 10104]

        # check playback
        players = await api.get_player()
        if not players or not players.get('result'):
            data.update({
                'media_type': TXT['no_playback'],
                'media_type_raw': 'idle',
                'main_info': TXT['no_playback'],
                'extra_info': TXT['no_playback'],
                'audio_info': TXT['no_audio_info']
            })
            return data

        playerid = players['result'][0]['playerid']
        item_data = await api.get_item(playerid)
        audio_data = await api.get_audio_info(playerid)

        if item_data and 'result' in item_data:
            item = item_data['result']['item']
            media_type, main_info, extra_info = 'Other', '', ''
            raw_type = 'unknown'

            if not item.get('title') and item.get('label'):
                label = item.get('label')
                match = re.match(r'^(.*)\sS(\d{1,2})E(\d{1,2})', label, re.IGNORECASE)
                if match:
                    media_type = TXT['tv_show']
                    raw_type = 'tv'
                    main_info = match.group(1).strip()
                    extra_info = f"S{int(match.group(2)):02d}E{int(match.group(3)):02d}"

            if not main_info:
                if item.get('channeltype') == 'tv' or item.get('channel'):
                    media_type = TXT['live_tv']
                    raw_type = 'tv'
                    main_info = (item.get('channel') or TXT['live_tv']) + ' ᴵᴾᵀⱽ'
                    extra_info = item.get('title') or TXT['live_tv']
                elif item.get('type') == 'movie':
                    media_type = TXT['movie']
                    raw_type = 'movie'
                    main_info = f"{item.get('title','')} ({item.get('year','')})".strip()
                    extra_info = TXT['movie']
                elif item.get('type') == 'episode' or item.get('tvshowid'):
                    if item.get('season') == -1 and item.get('episode') == -1:
                        media_type = TXT['movie']
                        raw_type = 'movie'
                        main_info = item.get('label')
                        extra_info = TXT['movie']
                    else:
                        media_type = TXT['tv_show']
                        raw_type = 'tv'
                        main_info = f"{item.get('showtitle','')} ({item.get('year','')})".strip()
                        extra_info = f"S{int(item['season']):02d}E{int(item['episode']):02d} » {item.get('title','')}" if item.get('season') is not None and item.get('episode') is not None else TXT['tv_show']
                else:
                    media_type = item.get('label') or TXT['no_playback']
                    main_info = item.get('label') or TXT['no_playback']
                    extra_info = 'Other'
                    raw_type = 'other'

            if 'S-1E-1' in extra_info:
                extra_info = ''

            no_tags = re.sub(r'\[.*?\]', '', main_info)
            no_zero = re.sub(r'\s*\(0\)', '', no_tags)
            
            data['media_type'] = media_type
            data['media_type_raw'] = raw_type
            data['main_info'] = no_zero.strip()
            data['extra_info'] = extra_info

        if audio_data and 'result' in audio_data and audio_data['result'].get('audiostreams'):
            streams = audio_data['result'].get('audiostreams', [])
            current = audio_data['result'].get('currentaudiostream', {}).get('index')
            
            if current is not None and current < len(streams):
                stream = streams[current]
                codec = stream.get('codec','').lower()
                channels = stream.get('channels', 0)
                
                channel_str_map = {
                    2: TXT['stereo'],
                    6: TXT['channel_5_1'],
                    8: TXT['channel_7_1']
                }
                channel_str = channel_str_map.get(channels, f"{channels}-Channel")

                codec_map = {
                    'ac3': 'Dolby Digital', 'eac3': 'Dolby Digital+', 'dts': 'DTS', 'aac': 'AAC',
                    'dca': 'DTS', 'dolbydigital': 'Dolby Digital', 'dtshd_hra': 'DTS-HD HRA',
                    'dtshd_ma': 'DTS-HD MA', 'dtshd_ma_x': 'DTS-HD MA X',
                    'dtshd_ma_x_ima': 'DTS-HD MA X (IMAX)', 'dtsma': 'DTS Master Audio',
                    'eac3_ddp_atmos': 'Dolby Atmos (DD+)', 'truehd': 'Dolby TrueHD',
                    'truehd_atmos': 'Dolby Atmos+TrueHD'
                }

                codec_str = 'PCM' if codec.startswith('pcm') else codec_map.get(codec, codec.upper())
                data['audio_info'] = f"{codec_str} | {channel_str}"
            else:
                data['audio_info'] = TXT['no_audio_info']

        return data

    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name='Kodi Helpers Coordinator',
        update_method=async_update_data,
        update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL)
    )

    await coordinator.async_config_entry_first_refresh()
    hass.data[DOMAIN][entry.entry_id]['coordinator'] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok