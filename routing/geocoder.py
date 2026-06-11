import json
from pathlib import Path
from typing import Callable
from routing.models import Client


def _clave(client: Client) -> str:
    if client.localidad:
        return f"{client.direccion}, {client.localidad}"
    return client.direccion


def google_geocode_fn(api_key: str) -> Callable[[str], tuple | None]:
    """Crea una geocode_fn real usando el cliente de googlemaps."""
    import googlemaps
    gm = googlemaps.Client(key=api_key)

    def _fn(q: str):
        res = gm.geocode(q, region="ar")
        if not res:
            return None
        loc = res[0]["geometry"]["location"]
        return (loc["lat"], loc["lng"])

    return _fn


class Geocoder:
    def __init__(self, cache_path, geocode_fn: Callable[[str], tuple | None]):
        self.cache_path = Path(cache_path)
        self.geocode_fn = geocode_fn
        self.cache: dict[str, list] = {}
        if self.cache_path.exists():
            self.cache = json.loads(self.cache_path.read_text(encoding="utf-8"))

    def _guardar(self):
        self.cache_path.write_text(
            json.dumps(self.cache, ensure_ascii=False, indent=2),
            encoding="utf-8")

    def geocode_clients(self, clients: list[Client]):
        ok, fallidos = [], []
        try:
            for c in clients:
                clave = _clave(c)
                coord = self.cache.get(clave)
                if coord is None:
                    coord = self.geocode_fn(clave)
                    if coord is not None:
                        self.cache[clave] = [coord[0], coord[1]]
                if coord is None:
                    fallidos.append(c)
                    continue
                c.lat, c.lon = coord[0], coord[1]
                ok.append(c)
        finally:
            # Persistir el cache aunque geocode_fn falle a mitad (timeout/rate
            # limit): no se pierde lo ya resuelto en esta corrida.
            self._guardar()
        return ok, fallidos
