# Rutas en Google Maps + fix de geocoding

**Fecha:** 2026-06-11
**Estado:** Aprobado, pendiente de implementación

## Problema

Dos problemas relacionados:

1. **Geocoding impreciso:** los pines caen lejísimos (otra provincia/país). Causa raíz confirmada: el geocoder usa `gm.geocode(q, region="ar")`, donde `region` **sesga pero no restringe**. Ante una dirección sin match exacto en Argentina (ej. "Boulogne"), Google devuelve el mejor match global (Boulogne-sur-Mer, Francia). Además toma `res[0]` a ciegas, ignorando la bandera `partial_match`.
2. **Visualización poco útil:** el mapa folium muestra líneas rectas entre paradas, no rutas por calles. El repartidor no tiene forma de navegar la ruta.

## Solución

### Parte A — Fix de geocoding (prerequisito)

En `routing/geocoder.py`, `google_geocode_fn`:
- Reemplazar `gm.geocode(q, region="ar")` por `gm.geocode(q, components={"country": "AR"})`. `components` **restringe** los resultados a Argentina: una dirección ambigua ya no puede resolverse en otro país.
- Detectar `partial_match`: si `res[0].get("partial_match")` es `True`, el geocoding no encontró match exacto. Se devuelve la coordenada igual (no se descarta), pero el dato queda disponible para avisar al usuario que esa dirección es dudosa.

Esto es prerequisito: sin direcciones bien ubicadas, ni el mapa ni los links de Google Maps sirven.

### Parte B — Botón "Abrir en Google Maps" por día

Módulo nuevo `routing/gmaps_links.py`:
```python
ruta_a_gmaps_url(depot, route, fin=None) -> str
```
Construye una URL de **Google Maps Directions** (formato `https://www.google.com/maps/dir/?api=1&...`):
- **origin** = depósito, como coordenada `lat,lon` (el depósito no tiene dirección de texto).
- **Sin zona de fin:** `destination` = la **última** parada del día (dirección de texto); `waypoints` = las paradas anteriores (1..n-1) en orden. La última parada NO se duplica en waypoints.
- **Con zona de fin:** `destination` = la zona de fin (coordenada `lat,lon`); `waypoints` = **todas** las paradas del día (1..n) en orden.
- Las paradas (clientes) van como **direcciones de texto con contexto**: `"{direccion}, {localidad}, Argentina"` (o `"{direccion}, Argentina"` si no hay localidad).
- **travelmode** = `driving`.

**Decisión: texto vs coordenadas.** Los clientes van como dirección de texto (no coordenada) para que Google Maps muestre el nombre real del lugar y navegue a la dirección exacta, incluso si el geocoding interno tuvo un error menor. El depósito y la zona de fin van como coordenada (el depósito es fijo sin dirección; la zona de fin es un punto de referencia).

En `app.py`, debajo del mapa folium, por cada ruta:
```python
st.link_button(f"🗺️ Abrir Día {r.dia} en Google Maps", url)
```
En el celular, abre la app de Google Maps con navegación turn-by-turn, parada por parada, en el orden de la app.

## Comportamiento ante errores / casos límite

- **Límite de waypoints:** la URL de Google Maps soporta ~10 puntos. Si una ruta tiene más de 10 paradas, se genera el link igual (Google Maps puede recortar) y se muestra un `st.caption` de aviso bajo ese botón. Con la capacidad típica, cada día tiene pocas paradas, así que rara vez se alcanza.
- **partial_match:** las direcciones marcadas como dudosas por Google se siguen geocodificando y se incluyen en las rutas; el aviso es informativo.

## Componentes y archivos

| Archivo | Cambio |
|---------|--------|
| `routing/geocoder.py` | `components={"country": "AR"}` en lugar de `region="ar"`; lectura de `partial_match`. |
| `routing/gmaps_links.py` (nuevo) | `ruta_a_gmaps_url(depot, route, fin=None) -> str`. Arma la Directions URL con origin/waypoints/destination. |
| `app.py` | Debajo del mapa folium, un `st.link_button` por día con la URL; caption de aviso si la ruta supera 10 paradas. |
| `tests/test_gmaps_links.py` (nuevo) | Verifica estructura de la URL: origin es el depósito, waypoints en orden, destination correcta (última parada o fin), URL-encoding de las direcciones, travelmode=driving. |
| `tests/test_geocoder.py` | Test con mock de `googlemaps.Client` que confirma que `google_geocode_fn` llama a `gm.geocode` con `components={"country": "AR"}`. |

## Fuera de alcance

- Mapa de Google embebido en la app (se eligió solo los botones que abren Google Maps).
- Re-optimizar el orden de visita con la Directions API real (la app sigue ordenando por distancia en línea recta; Google Maps solo navega ese orden).
- Cambiar el mapa folium (queda como vista general de líneas rectas).
