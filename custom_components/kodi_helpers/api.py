import aiohttp
import async_timeout

class KodiAPI:
    """Eine optimierte Klasse zur Interaktion mit der Kodi JSON-RPC API."""

    def __init__(self, host: str, port: int, username: str = None, password: str = None, ssl: bool = False, timeout: int = 5):
        """
        Initialisiert die KodiAPI-Instanz.

        Args:
            host (str): Der Hostname oder die IP-Adresse von Kodi.
            port (int): Der Port des Kodi Webservers.
            username (str, optional): Der Benutzername für die Authentifizierung. Defaults to None.
            password (str, optional): Das Passwort für die Authentifizierung. Defaults to None.
            ssl (bool, optional): Ob eine sichere Verbindung (HTTPS) verwendet werden soll. Defaults to False.
            timeout (int, optional): Der Standard-Timeout für Anfragen in Sekunden. Defaults to 5.
        """
        protocol = "https" if ssl else "http"
        self._url = f"{protocol}://{host}:{port}/jsonrpc"
        auth = aiohttp.BasicAuth(login=username, password=password) if username else None
        self._session = aiohttp.ClientSession(auth=auth)
        self._timeout = timeout

    async def _post(self, payload: dict) -> dict | None:
        """Sendet eine POST-Anfrage an die Kodi JSON-RPC API."""
        try:
            async with async_timeout.timeout(self._timeout):
                async with self._session.post(self._url, json=payload) as resp:
                    if resp.status == 200:
                        return await resp.json()
                    return None
        except Exception:
            return None

    async def close(self):
        """Schließt die aiohttp ClientSession."""
        await self._session.close()

    async def ping(self) -> bool:
        """
        Prüft, ob die Kodi-Instanz erreichbar ist und korrekt antwortet.

        Returns:
            bool: True, wenn der Ping erfolgreich war, sonst False.
        """
        payload = {"jsonrpc": "2.0", "method": "JSONRPC.Ping", "id": 1}
        response = await self._post(payload)
        return response is not None and response.get("result") == "pong"

    async def get_player(self) -> dict | None:
        """Ruft die aktiven Player ab."""
        return await self._post({"jsonrpc": "2.0", "id": 1, "method": "Player.GetActivePlayers"})

    async def get_item(self, playerid: int) -> dict | None:
        """Ruft Details zum aktuell abgespielten Item eines Players ab."""
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

    async def get_audio_info(self, playerid: int) -> dict | None:
        """Ruft Audio-Eigenschaften des Players ab."""
        return await self._post({
            "jsonrpc": "2.0",
            "id": 1,
            "method": "Player.GetProperties",
            "params": {
                "playerid": playerid,
                "properties": ["audiostreams", "currentaudiostream"]
            }
        })

    async def get_app_properties(self) -> dict | None:
        """Ruft Anwendungs-Eigenschaften wie Name und Version ab."""
        return await self._post({
            "jsonrpc": "2.0", 
            "id": 1, 
            "method": "Application.GetProperties", 
            "params": {"properties": ["name", "version"]}
        })
