import folium
from routing.models import Client, Route, Stop
from routing.map_render import render_map


def _ruta(dia, coords):
    r = Route(dia=dia)
    for i, (lat, lon) in enumerate(coords, start=1):
        c = Client(cliente=f"C{i}", direccion="d", cantidad=1, lat=lat, lon=lon)
        r.stops.append(Stop(client=c, orden_visita=i))
    return r


def test_devuelve_mapa_folium():
    rutas = [_ruta(1, [(-34.61, -58.39), (-34.62, -58.40)])]
    m = render_map((-34.60, -58.38), rutas)
    assert isinstance(m, folium.Map)


def test_html_incluye_marcadores_y_polilinea():
    rutas = [_ruta(1, [(-34.61, -58.39), (-34.62, -58.40)])]
    m = render_map((-34.60, -58.38), rutas)
    html = m.get_root().render()
    assert "marker" in html.lower()
    assert "polyline" in html.lower()


def test_dias_distintos_usan_colores_distintos():
    rutas = [_ruta(1, [(-34.61, -58.39)]), _ruta(2, [(-34.90, -57.95)])]
    m = render_map((-34.60, -58.38), rutas)
    html = m.get_root().render()
    # al menos dos colores de la paleta presentes
    from routing.map_render import PALETA
    presentes = [col for col in PALETA if col in html]
    assert len(presentes) >= 2
