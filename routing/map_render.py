import folium
from routing.models import Route

PALETA = ["red", "blue", "green", "purple", "orange", "darkred",
          "cadetblue", "darkgreen", "darkpurple", "pink", "gray", "black"]


def _centro(depot, rutas, fin=None):
    lats = [depot[0]] + [s.client.lat for r in rutas for s in r.stops]
    lons = [depot[1]] + [s.client.lon for r in rutas for s in r.stops]
    if fin is not None:
        lats.append(fin[0])
        lons.append(fin[1])
    return (sum(lats) / len(lats), sum(lons) / len(lons))


def render_map(depot, rutas: list[Route], fin=None) -> folium.Map:
    m = folium.Map(location=_centro(depot, rutas, fin), zoom_start=11)

    folium.Marker(
        location=[depot[0], depot[1]],
        tooltip="Depósito",
        icon=folium.Icon(color="black", icon="home", prefix="fa"),
    ).add_to(m)

    if fin is not None:
        folium.Marker(
            location=[fin[0], fin[1]],
            tooltip="Zona de fin",
            icon=folium.Icon(color="green", icon="flag-checkered", prefix="fa"),
        ).add_to(m)

    cierre = fin if fin is not None else depot
    for r in rutas:
        color = PALETA[(r.dia - 1) % len(PALETA)]
        coords = [(depot[0], depot[1])]
        for s in r.stops:
            c = s.client
            coords.append((c.lat, c.lon))
            folium.CircleMarker(
                location=[c.lat, c.lon],
                radius=6,
                color=color,
                fill=True,
                fill_color=color,
                fill_opacity=0.9,
                tooltip=(f"Día {r.dia} · #{s.orden_visita} · "
                         f"{c.cliente} · {c.cantidad}"),
            ).add_to(m)
        coords.append((cierre[0], cierre[1]))
        folium.PolyLine(coords, color=color, weight=3, opacity=0.7).add_to(m)

    return m
