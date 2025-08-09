import aiohttp
import async_timeout
from urllib.parse import quote

class KodiAPI:
    def __init__(self, host, port, username, password, scheme='http'):
        self.host = host
        self.port = port
        self.username = username or ''
        self.password = password or ''
        self.scheme = scheme or 'http'
        self._build_url()

    def _build_url(self):
        auth = ''
        if self.username or self.password:
            auth = f"{quote(self.username)}:{quote(self.password)}@"
        self._url = f"{self.scheme}://{auth}{self.host}:{self.port}/jsonrpc"

    def set_scheme(self, scheme: str):
        self.scheme = scheme
        self._build_url()

    async def _post(self, payload, timeout=5):
        async with aiohttp.ClientSession() as session:
            try:
                with async_timeout.timeout(timeout):
                    async with session.post(self._url, json=payload) as resp:
                        if resp.status == 200:
                            return await resp.json()
                        return None
            except Exception:
                return None

    async def get_player(self):
        return await self._post({"jsonrpc": "2.0", "id": 1, "method": "Player.GetActivePlayers"})

    async def get_item(self, playerid):
        return await self._post({
            "jsonrpc": "2.0",
            "id": 1,
            "method": "Player.GetItem",
            "params": {
                "playerid": playerid,
                "properties": [
                    "title", "showtitle", "season", "episode", "year",
                    "tvshowid", "file", "streamdetails", "art",
                    "channel", "channeltype", "label"
                ]
            }
        })

    async def get_audio_info(self, playerid):
        return await self._post({
            "jsonrpc": "2.0",
            "id": 1,
            "method": "Player.GetProperties",
            "params": {
                "playerid": playerid,
                "properties": ["audiostreams", "currentaudiostream"]
            }
        })

    async def get_app_properties(self):
        return await self._post({"jsonrpc": "2.0", "id": 1, "method": "Application.GetProperties", "params": {"properties": ["name","version"]}})

    async def ping(self):
        return await self._post({"jsonrpc": "2.0", "id": 1, "method": "JSONRPC.Ping"})
