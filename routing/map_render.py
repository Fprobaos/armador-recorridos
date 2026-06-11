import folium
from routing.models import Route

PALETA = ["red", "blue", "green", "purple", "orange", "darkred",
          "cadetblue", "darkgreen", "darkpurple", "pink", "gray", "black"]


def _centro(depot, rutas):
    lats = [depot[0]] + [s.client.lat for r in rutas for s in r.stops]
    lons = [depot[1]] + [s.client.lon for r in rutas for s in r.stops]
    return (sum(lats) / len(lats), sum(lons) / len(lons))


def render_map(depot, rutas: list[Route]) -> folium.Map:
    m = folium.Map(location=_centro(depot, rutas), zoom_start=11)

    folium.Marker(
        location=[depot[0], depot[1]],
        tooltip="Depósito",
        icon=folium.Icon(color="black", icon="home", prefix="fa"),
    ).add_to(m)

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
        coords.append((depot[0], depot[1]))
        folium.PolyLine(coords, color=color, weight=3, opacity=0.7).add_to(m)

    return m
