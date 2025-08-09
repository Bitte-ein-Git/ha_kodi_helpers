from __future__ import annotations
import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.const import CONF_HOST, CONF_PORT, CONF_USERNAME, CONF_PASSWORD, CONF_SSL
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.helpers.device_registry import DeviceInfo

from .const import DOMAIN, PLATFORMS, DEFAULT_SCAN_INTERVAL
from .api import KodiAPI

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Kodi Helpers from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    # API-Instanz mit SSL-Option erstellen
    api = KodiAPI(
        host=entry.data[CONF_HOST],
        port=entry.data[CONF_PORT],
        username=entry.data.get(CONF_USERNAME),
        password=entry.data.get(CONF_PASSWORD),
        ssl=entry.data[CONF_SSL]
    )

    async def async_update_data():
        """Fetch data from API."""
        # Dein alter Update-Code aus sensor.py kommt hierher.
        # Hier ist er zur Übersichtlichkeit gekürzt.
        if not await api.ping():
            return {
                "media_type": "Offline", "main_info": "Offline",
                "extra_info": "Offline", "audio_info": "Offline"
            }
        # ... (der Rest deiner Logik zum Parsen der Kodi-Daten)
        # Hier ein Platzhalter für die volle Logik:
        return await fetch_and_parse_kodi_data(api)


    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name=f"Kodi Helpers Coordinator ({entry.data[CONF_HOST]})",
        update_method=async_update_data, # Deine Logik wird hier aufgerufen
        update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
    )

    await coordinator.async_config_entry_first_refresh()

    # Speichere API und Coordinator für die Plattformen
    hass.data[DOMAIN][entry.entry_id] = {
        "coordinator": coordinator,
        "api": api
    }
    
    # Lade die Sensor-Plattform
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok

async def fetch_and_parse_kodi_data(api: KodiAPI) -> dict:
    """Deine Logik zum Abfragen und Verarbeiten der Kodi-Daten."""
    # Diese Funktion enthält den Code, der vorher in async_update_data in sensor.py stand.
    players = await api.get_player()
    if not players or not players.get("result"):
        return {"media_type": "Keine Wiedergabe", "main_info": "Keine Wiedergabe", "extra_info": "Keine Wiedergabe", "audio_info": "Keine Audio-Infos"}

    playerid = players["result"][0]["playerid"]
    item_data = await api.get_item(playerid)
    audio_data = await api.get_audio_info(playerid)
    
    # ... Rest deiner Parsing-Logik (unverändert) ...
    media_type = "Other"
    main_info = ""
    extra_info = ""
    audio_info = ""

    if item_data and "result" in item_data:
        item = item_data["result"]["item"]
        if item.get("channeltype") == "tv":  # Live TV
            media_type = "Live TV"
            main_info = item.get("channel", "📺 Live TV")
            extra_info = item.get("title", "Keine Wiedergabe")
        elif item.get("type") == "movie":
            media_type = "Movie"
            main_info = f"{item.get('title', '')} ({item.get('year', '')})".strip()
            extra_info = "🎬 Film"
        elif item.get("type") == "episode":
            media_type = "TV Show"
            main_info = f"{item.get('showtitle', '')} ({item.get('year', '')})".strip()
            if item.get("season") is not None and item.get("episode") is not None:
                extra_info = f"S{item['season']:02d}E{item['episode']:02d} » {item.get('title', '')}"
            else:
                extra_info = "🎞️ Serie"
        else:
            media_type = "Other"
            main_info = item.get("label", "Keine Wiedergabe")
            extra_info = media_type

    if audio_data and "result" in audio_data:
        streams = audio_data["result"].get("audiostreams", [])
        current = audio_data["result"].get("currentaudiostream", {}).get("index")
        if streams and current is not None and current < len(streams):
            codec = streams[current].get("codec", "").lower()
            channels = streams[current].get("channels", 0)
            channel_str = {2: "Stereo", 6: "5.1", 8: "7.1"}.get(channels, f"{channels}-Kanal")
            codec_map = { "ac3": "Dolby Digital", "eac3": "Dolby Digital+", "dts": "DTS", "aac": "AAC"}
            codec_str = codec_map.get(codec, codec.upper())
            audio_info = f"{codec_str} {channel_str}"
        else:
            audio_info = "Keine Audio-Infos"

    return {
        "media_type": media_type,
        "main_info": main_info or "Keine Wiedergabe",
        "extra_info": extra_info or media_type,
        "audio_info": audio_info
    }