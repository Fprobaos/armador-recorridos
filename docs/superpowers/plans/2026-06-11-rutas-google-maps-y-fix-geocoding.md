# Rutas en Google Maps + fix de geocoding — Plan de Implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restringir el geocoding a Argentina (corrige pines que caen en otro país) y agregar un botón "Abrir en Google Maps" por día que abre la navegación real parada por parada.

**Architecture:** El geocoder pasa de `region="ar"` (sesgo) a `components={"country":"AR"}` (restricción dura) y registra direcciones con `partial_match`. Un módulo nuevo arma URLs de Google Maps Directions a partir de cada ruta. La app agrega un `st.link_button` por día.

**Tech Stack:** Python, googlemaps, Streamlit, urllib.parse, pytest, unittest.mock.

---

## Estructura de archivos

| Archivo | Responsabilidad | Cambio |
|---------|-----------------|--------|
| `routing/geocoder.py` | Geocodificar direcciones | Restringir a AR + registrar dudosas |
| `routing/gmaps_links.py` | Armar URLs de Google Maps Directions | Crear |
| `app.py` | UI Streamlit | Botones por día + aviso de dudosas |
| `tests/test_geocoder.py` | Tests del geocoder | +2 tests con mock |
| `tests/test_gmaps_links.py` | Tests del generador de URLs | Crear |

---

## Task 1: Geocoder restringe a Argentina y registra direcciones dudosas

**Files:**
- Modify: `routing/geocoder.py`
- Test: `tests/test_geocoder.py`

- [ ] **Step 1: Escribir los tests que fallan**

Agregar al final de `tests/test_geocoder.py`:

```python
from unittest.mock import patch, MagicMock
from routing.geocoder import google_geocode_fn


def test_google_geocode_fn_restringe_a_argentina():
    fake_gm = MagicMock()
    fake_gm.geocode.return_value = [
        {"geometry": {"location": {"lat": -34.5, "lng": -58.5}}}]
    with patch("googlemaps.Client", return_value=fake_gm):
        fn = google_geocode_fn("FAKE")
        coord = fn("Av. Centenario 1000, San Isidro")
    assert coord == (-34.5, -58.5)
    _, kwargs = fake_gm.geocode.call_args
    assert kwargs.get("components") == {"country": "AR"}


def test_google_geocode_fn_registra_partial_match():
    fake_gm = MagicMock()
    fake_gm.geocode.return_value = [
        {"partial_match": True,
         "geometry": {"location": {"lat": -34.5, "lng": -58.5}}}]
    with patch("googlemaps.Client", return_value=fake_gm):
        fn = google_geocode_fn("FAKE")
        fn("Direccion rara")
    assert fn.dudosas == ["Direccion rara"]
```

- [ ] **Step 2: Correr los tests para verificar que fallan**

Run: `python -m pytest tests/test_geocoder.py::test_google_geocode_fn_restringe_a_argentina -v`
Expected: FAIL — `gm.geocode` se llama con `region="ar"`, no con `components`; `assert kwargs.get("components") == {"country": "AR"}` falla.

- [ ] **Step 3: Implementar el fix en `google_geocode_fn`**

Reemplazar la función `google_geocode_fn` completa en `routing/geocoder.py` por:

```python
def google_geocode_fn(api_key: str) -> Callable[[str], tuple | None]:
    """Crea una geocode_fn real usando el cliente de googlemaps.

    Restringe los resultados a Argentina (components country=AR) para que
    direcciones ambiguas no caigan en otro país. Registra en `_fn.dudosas`
    las consultas que Google resolvió con partial_match (sin match exacto).
    """
    import googlemaps
    gm = googlemaps.Client(key=api_key)
    dudosas: list[str] = []

    def _fn(q: str):
        res = gm.geocode(q, components={"country": "AR"})
        if not res:
            return None
        if res[0].get("partial_match"):
            dudosas.append(q)
        loc = res[0]["geometry"]["location"]
        return (loc["lat"], loc["lng"])

    _fn.dudosas = dudosas
    return _fn
```

- [ ] **Step 4: Correr los tests para verificar que pasan**

Run: `python -m pytest tests/test_geocoder.py -v`
Expected: PASS (los 4 tests viejos + los 2 nuevos).

- [ ] **Step 5: Commit**

```bash
git add routing/geocoder.py tests/test_geocoder.py
git commit -m "fix: geocoding restringido a Argentina y registro de direcciones dudosas"
```

---

## Task 2: Generador de URLs de Google Maps Directions

**Files:**
- Create: `routing/gmaps_links.py`
- Test: `tests/test_gmaps_links.py`

- [ ] **Step 1: Escribir los tests que fallan**

Crear `tests/test_gmaps_links.py` con:

```python
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
```

- [ ] **Step 2: Correr los tests para verificar que fallan**

Run: `python -m pytest tests/test_gmaps_links.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'routing.gmaps_links'`.

- [ ] **Step 3: Implementar el módulo**

Crear `routing/gmaps_links.py` con:

```python
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
```

- [ ] **Step 4: Correr los tests para verificar que pasan**

Run: `python -m pytest tests/test_gmaps_links.py -v`
Expected: PASS (4 tests).

Luego la suite completa: `python -m pytest -q` (esperado: 37 passed — 31 previos + 2 geocoder + 4 gmaps_links).

- [ ] **Step 5: Commit**

```bash
git add routing/gmaps_links.py tests/test_gmaps_links.py
git commit -m "feat: generador de URLs de Google Maps Directions por ruta"
```

---

## Task 3: Botones de Google Maps y aviso de direcciones dudosas en la app

**Files:**
- Modify: `app.py`

(Integración UI — sin test automatizado; se valida corriendo la app.)

- [ ] **Step 1: Importar el generador de URLs**

En `app.py`, agregar el import junto a los otros imports de `routing` (después de `from routing.map_render import render_map`):

```python
from routing.gmaps_links import ruta_a_gmaps_url
```

- [ ] **Step 2: Guardar las direcciones dudosas en session_state**

En `app.py`, en el bloque `st.session_state["resultado"] = {...}`, agregar la clave `dudosas` leyendo el atributo que expone `google_geocode_fn`. El bloque queda así:

```python
    st.session_state["resultado"] = {
        "rutas": rutas,
        "sobre": sobre,
        "fin_coord": fin_coord,
        "fallidos": fallidos,
        "revisar": revisar,
        "dudosas": list(geocode_fn.dudosas),
    }
```

- [ ] **Step 3: Leer `dudosas` en el bloque de render**

En `app.py`, en el bloque `if "resultado" in st.session_state:`, donde se desempaquetan los valores de `res`, agregar la línea de `dudosas`. Queda así:

```python
    res = st.session_state["resultado"]
    rutas = res["rutas"]
    sobre = res["sobre"]
    fin_coord = res["fin_coord"]
    fallidos = res["fallidos"]
    revisar = res["revisar"]
    dudosas = res["dudosas"]
```

- [ ] **Step 4: Agregar la sección de botones de Google Maps**

En `app.py`, inmediatamente después del bloque del mapa (la llamada a `st_folium(...)`) y antes del comentario `# Descarga`, insertar:

```python
    # Botones de Google Maps por día
    st.subheader("Abrir en Google Maps")
    st.caption("Cada día abre la navegación real por calles, parada por "
               "parada, en el orden calculado.")
    for r in rutas:
        url = ruta_a_gmaps_url(DEPOT, r, fin=fin_coord)
        st.link_button(f"🗺️ Día {r.dia} ({len(r.stops)} paradas)", url)
        if len(r.stops) > 10:
            st.caption("⚠️ Más de 10 paradas: Google Maps puede recortar "
                       "la ruta.")
```

- [ ] **Step 5: Agregar el aviso de direcciones dudosas**

En `app.py`, en la sección de avisos del final (después del bloque `if fallidos:` y antes o después de `if revisar:`), agregar:

```python
    if dudosas:
        st.warning("Direcciones que Google ubicó de forma aproximada "
                   "(revisá que estén bien):")
        st.dataframe([{"direccion": d} for d in dudosas])
```

- [ ] **Step 6: Validar sintaxis y suite**

Run: `python -c "import ast; ast.parse(open('app.py', encoding='utf-8').read()); print('app.py OK sintaxis')"`
Expected: imprime "app.py OK sintaxis".

Run: `python -m pytest -q`
Expected: 37 passed.

- [ ] **Step 7: Validar en la app**

Run: `python -m streamlit run app.py`
- Subir un Excel con **direcciones reales** (las inventadas siguen cayendo mal aunque restrinjamos a AR, porque no existen).
- Verificar: aparece un botón "🗺️ Día N" por cada día; al hacer clic abre Google Maps con la ruta depósito → paradas → fin.
- Si alguna dirección es aproximada, aparece el aviso amarillo de direcciones dudosas.

- [ ] **Step 8: Commit**

```bash
git add app.py
git commit -m "feat: botones Abrir en Google Maps por dia y aviso de direcciones dudosas"
```

---

## Notas de implementación

- **`geocode_fn.dudosas`:** `google_geocode_fn` expone el atributo `dudosas` (lista) en la función que devuelve. La app lo lee después de geocodificar, dentro del click (no en reruns), y lo persiste en `session_state`. Las direcciones servidas desde el cache no se re-evalúan, así que `dudosas` refleja solo lo geocodificado en esa corrida — es un aviso informativo, no exhaustivo.
- **Texto vs coordenadas:** las paradas van como dirección de texto (`"dir, localidad, Argentina"`) para que Google Maps navegue a la dirección real y muestre el nombre del lugar. El depósito y la zona de fin van como coordenada.
- **`urlencode`:** codifica `|` y las comas/espacios; `parse_qs` los decodifica en los tests, por eso las aserciones comparan contra el texto sin encodear.
- **Datos:** este plan NO arregla direcciones inexistentes. Con direcciones reales + restricción a AR, los pines y los links de Google Maps quedan bien ubicados.
