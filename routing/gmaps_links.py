from urllib.parse import urlencode
from routing.models import Route

BASE = "https://www.google.com/maps/dir/?"


def _texto(client):
    if client.localidad:
        return f"{client.direccion}, {client.localidad}, Argentina"
    return f"{client.direccion}, Argentina"


def ruta_a_gmaps_url(depot, route: Route, fin=None) -> str:
    """Arma una URL de Google Maps Directions para una ruta.

    origin = depósito (coordenada). Las paradas (clientes) van como texto.
    Sin fin: destination = última parada, waypoints = anteriores.
    Con fin: destination = zona de fin (coordenada), waypoints = todas.
    """
    origin = f"{depot[0]},{depot[1]}"
    textos = [_texto(s.client) for s in route.stops]

    if fin is not None:
        destination = f"{fin[0]},{fin[1]}"
        waypoints = textos
    else:
        destination = textos[-1]
        waypoints = textos[:-1]

    params = {
        "api": 1,
        "origin": origin,
        "destination": destination,
        "travelmode": "driving",
    }
    if waypoints:
        params["waypoints"] = "|".join(waypoints)
    return BASE + urlencode(params)
