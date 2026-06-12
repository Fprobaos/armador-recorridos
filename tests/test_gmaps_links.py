from urllib.parse import urlparse, parse_qs
from routing.models import Client, Route, Stop
from routing.gmaps_links import ruta_a_gmaps_url

DEPOT = (-34.5576, -58.4727)


def _route(paradas):
    r = Route(dia=1)
    for i, (direccion, localidad) in enumerate(paradas, start=1):
        c = Client(cliente=f"C{i}", direccion=direccion, cantidad=1,
                   localidad=localidad, lat=-34.5, lon=-58.5)
        r.stops.append(Stop(client=c, orden_visita=i))
    return r


def _query(url):
    return parse_qs(urlparse(url).query)


def test_sin_fin_destino_es_ultima_parada():
    r = _route([("Calle 1", "Olivos"), ("Calle 2", "San Isidro"),
                ("Calle 3", "Martinez")])
    q = _query(ruta_a_gmaps_url(DEPOT, r))
    assert q["origin"] == ["-34.5576,-58.4727"]
    assert q["destination"] == ["Calle 3, Martinez, Argentina"]
    assert q["waypoints"] == [
        "Calle 1, Olivos, Argentina|Calle 2, San Isidro, Argentina"]
    assert q["travelmode"] == ["driving"]


def test_con_fin_destino_es_la_zona_y_todas_son_waypoints():
    r = _route([("Calle 1", "Olivos"), ("Calle 2", "Boulogne")])
    q = _query(ruta_a_gmaps_url(DEPOT, r, fin=(-34.49, -58.56)))
    assert q["destination"] == ["-34.49,-58.56"]
    assert q["waypoints"] == [
        "Calle 1, Olivos, Argentina|Calle 2, Boulogne, Argentina"]


def test_sin_localidad_usa_solo_direccion_y_pais():
    r = _route([("Calle 1", ""), ("Calle 2", "")])
    q = _query(ruta_a_gmaps_url(DEPOT, r))
    assert q["destination"] == ["Calle 2, Argentina"]
    assert q["waypoints"] == ["Calle 1, Argentina"]


def test_una_sola_parada_sin_fin_no_tiene_waypoints():
    r = _route([("Calle Unica", "Olivos")])
    q = _query(ruta_a_gmaps_url(DEPOT, r))
    assert q["destination"] == ["Calle Unica, Olivos, Argentina"]
    assert "waypoints" not in q
