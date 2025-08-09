import aiohttp
import async_timeout

class KodiAPI:
    def __init__(self, host, port, username, password, ssl=False):
        protocol = "https" if ssl else "http"
        self._url = f"{protocol}://{host}:{port}/jsonrpc"
        self._auth = aiohttp.BasicAuth(username, password) if username else None
        self._session = aiohttp.ClientSession(auth=self._auth)

    async def _post(self, payload):
        async with aiohttp.ClientSession() as session:
            with async_timeout.timeout(5):
                async with session.post(self._url, json=payload) as resp:
                    if resp.status == 200:
                        return await resp.json()
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
                    "channel", "channeltype"
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

    async def ping(self):
        return await self._post({"jsonrpc": "2.0", "id": 1, "method": "JSONRPC.Ping"})