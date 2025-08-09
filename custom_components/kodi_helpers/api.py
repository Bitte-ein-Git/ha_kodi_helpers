# In deiner api.py Datei
import aiohttp

class KodiAPI:
    def __init__(self, host, port, username, password, ssl=False):
        protocol = "https" if ssl else "http"
        self._url = f"{protocol}://{host}:{port}/jsonrpc"
        self._auth = aiohttp.BasicAuth(username, password) if username else None
        self._session = aiohttp.ClientSession(auth=self._auth)

    # ... Rest deiner API-Methoden wie ping, get_player, etc.
    # Sie sollten alle self._session und self._url verwenden.
    
    async def ping(self):
        # Beispiel für eine Methode
        try:
            payload = {"jsonrpc": "2.0", "method": "JSONRPC.Ping", "id": 1}
            async with self._session.post(self._url, json=payload, timeout=5) as response:
                return response.status == 200 and await response.json() == {"id":1,"jsonrpc":"2.0","result":"pong"}
        except Exception:
            return False

    # ... deine anderen Methoden