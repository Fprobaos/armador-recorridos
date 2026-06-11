import json
from routing.geocoder import Geocoder
from routing.models import Client


def _cliente(direccion, localidad=""):
    return Client(cliente="C", direccion=direccion, cantidad=1,
                  localidad=localidad)


def test_geocodifica_y_escribe_coordenadas(tmp_path):
    llamadas = []

    def fake(q):
        llamadas.append(q)
        return (-34.6, -58.4)

    g = Geocoder(tmp_path / "cache.json", geocode_fn=fake)
    ok, fallidos = g.geocode_clients([_cliente("Calle 1", "Quilmes")])
    assert fallidos == []
    assert ok[0].lat == -34.6 and ok[0].lon == -58.4
    assert llamadas == ["Calle 1, Quilmes"]


def test_usa_cache_y_no_rellama(tmp_path):
    llamadas = []

    def fake(q):
        llamadas.append(q)
        return (-34.6, -58.4)

    cache = tmp_path / "cache.json"
    Geocoder(cache, geocode_fn=fake).geocode_clients([_cliente("Calle 1")])
    Geocoder(cache, geocode_fn=fake).geocode_clients([_cliente("Calle 1")])
    assert len(llamadas) == 1  # segunda corrida sale del cache


def test_direccion_fallida_va_a_fallidos(tmp_path):
    def fake(q):
        return None

    g = Geocoder(tmp_path / "cache.json", geocode_fn=fake)
    ok, fallidos = g.geocode_clients([_cliente("Direccion inexistente")])
    assert ok == []
    assert len(fallidos) == 1
    assert fallidos[0].direccion == "Direccion inexistente"


def test_cache_persiste_en_disco(tmp_path):
    cache = tmp_path / "cache.json"
    Geocoder(cache, geocode_fn=lambda q: (-1.0, -2.0)).geocode_clients(
        [_cliente("Calle 9")])
    guardado = json.loads(cache.read_text(encoding="utf-8"))
    assert guardado["Calle 9"] == [-1.0, -2.0]
