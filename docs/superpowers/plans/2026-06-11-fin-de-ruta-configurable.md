# Fin de ruta configurable — Plan de Implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Permitir que cada ruta termine en una zona configurable (ej. Boulogne) en vez de volver al depósito, y fijar el depósito a una coordenada constante.

**Architecture:** El solver OR-Tools pasa de inicio/fin único (nodo 0) a inicio (depósito) y fin (zona) separados cuando se provee una coordenada de fin. La zona se geocodifica por nombre en la app. Todo es opcional y retrocompatible: sin zona, el comportamiento es idéntico al actual.

**Tech Stack:** Python, OR-Tools (pywrapcp), Streamlit, folium, pytest.

---

## Estructura de archivos

| Archivo | Responsabilidad | Cambio |
|---------|-----------------|--------|
| `routing/solver.py` | Resolver el CVRP | `solve()` acepta `fin=None`; inicio/fin separados |
| `routing/map_render.py` | Dibujar el mapa | Marcador de fin + cierre de polilínea hacia el fin |
| `app.py` | UI Streamlit | Depósito fijo (constante) + campo de zona de fin + geocoding |
| `tests/test_solver.py` | Tests del solver | 2 tests nuevos |
| `tests/test_map_render.py` | Tests del mapa | 1 test nuevo |

---

## Task 1: Solver soporta punto de fin distinto al depósito

**Files:**
- Modify: `routing/solver.py`
- Test: `tests/test_solver.py`

- [ ] **Step 1: Escribir los tests que fallan**

Agregar al final de `tests/test_solver.py`:

```python
FIN = (-34.90, -57.95)


def test_ruta_termina_en_cliente_mas_cercano_al_fin():
    clientes = [
        _c("Cerca_depot", -34.61, -58.39, 1),
        _c("Medio", -34.75, -58.15, 1),
        _c("Cerca_fin", -34.89, -57.96, 1),
    ]
    rutas, _ = solve(DEPOT, clientes, capacidad=100, fin=FIN)
    assert len(rutas) == 1
    assert rutas[0].stops[-1].client.cliente == "Cerca_fin"


def test_fin_none_mantiene_comportamiento():
    clientes = [_c("A", -34.61, -58.39, 1), _c("B", -34.62, -58.40, 1)]
    rutas, sobre = solve(DEPOT, clientes, capacidad=100, fin=None)
    asignados = sorted(s.client.cliente for r in rutas for s in r.stops)
    assert asignados == ["A", "B"]
    assert sobre == []
```

- [ ] **Step 2: Correr los tests para verificar que fallan**

Run: `python -m pytest tests/test_solver.py::test_ruta_termina_en_cliente_mas_cercano_al_fin -v`
Expected: FAIL con `TypeError: solve() got an unexpected keyword argument 'fin'`

- [ ] **Step 3: Implementar el soporte de `fin` en `solve()`**

Reemplazar la función `solve` completa en `routing/solver.py` (líneas 13-43, hasta antes de `routing = pywrapcp.RoutingModel(manager)`) por:

```python
def solve(depot, clients: list[Client], capacidad: float, max_dias=None, fin=None):
    capacidad = int(capacidad)
    sobre = [c for c in clients if int(math.ceil(c.cantidad)) > capacidad]
    validos = [c for c in clients if int(math.ceil(c.cantidad)) <= capacidad]
    if not validos:
        return [], sobre

    # indice 0 = depot; 1..N = clientes; (si hay fin) N+1 = punto de fin
    puntos = [depot] + [(c.lat, c.lon) for c in validos]
    demandas = [0] + [int(math.ceil(c.cantidad)) for c in validos]
    if fin is not None:
        puntos.append(fin)
        demandas.append(0)

    matriz = build_distance_matrix(puntos)

    min_dias = _num_dias_minimo(
        [int(math.ceil(c.cantidad)) for c in validos], capacidad)
    # holgura de vehiculos para que el solver tenga margen
    num_vehiculos = max_dias or (min_dias + len(validos))

    if fin is None:
        manager = pywrapcp.RoutingIndexManager(len(puntos), num_vehiculos, 0)
    else:
        fin_idx = len(puntos) - 1
        manager = pywrapcp.RoutingIndexManager(
            len(puntos), num_vehiculos,
            [0] * num_vehiculos, [fin_idx] * num_vehiculos)

    routing = pywrapcp.RoutingModel(manager)
```

El resto de la función (desde `def dist_cb` hasta el `return rutas, sobre`) queda **sin cambios**. El loop de armado de paradas ya excluye el nodo de fin porque corta en `routing.IsEnd(idx)`, y `validos[nodo - 1]` solo se aplica a nodos de clientes (1..N).

- [ ] **Step 4: Correr los tests para verificar que pasan**

Run: `python -m pytest tests/test_solver.py -v`
Expected: PASS (los 8 tests viejos + los 2 nuevos)

- [ ] **Step 5: Commit**

```bash
git add routing/solver.py tests/test_solver.py
git commit -m "feat: solver soporta punto de fin distinto al deposito"
```

---

## Task 2: Mapa muestra el marcador de fin y cierra la ruta hacia él

**Files:**
- Modify: `routing/map_render.py`
- Test: `tests/test_map_render.py`

- [ ] **Step 1: Escribir el test que falla**

Agregar al final de `tests/test_map_render.py`:

```python
def test_marcador_de_fin_cuando_hay_zona():
    rutas = [_ruta(1, [(-34.61, -58.39)])]
    m = render_map((-34.60, -58.38), rutas, fin=(-34.90, -57.95))
    html = m.get_root().render()
    assert "Zona de fin" in html
```

- [ ] **Step 2: Correr el test para verificar que falla**

Run: `python -m pytest tests/test_map_render.py::test_marcador_de_fin_cuando_hay_zona -v`
Expected: FAIL con `TypeError: render_map() got an unexpected keyword argument 'fin'`

- [ ] **Step 3: Implementar el soporte de `fin` en `render_map()`**

Reemplazar el contenido completo de `routing/map_render.py` (desde `def _centro` hasta el final) por:

```python
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
```

- [ ] **Step 4: Correr los tests para verificar que pasan**

Run: `python -m pytest tests/test_map_render.py -v`
Expected: PASS (los 3 tests viejos + el nuevo)

- [ ] **Step 5: Commit**

```bash
git add routing/map_render.py tests/test_map_render.py
git commit -m "feat: mapa marca la zona de fin y cierra la ruta hacia ella"
```

---

## Task 3: App con depósito fijo y campo de zona de fin

**Files:**
- Modify: `app.py`

(Este task es de integración UI — no tiene test automatizado; se valida corriendo la app.)

- [ ] **Step 1: Fijar el depósito como constante**

En `app.py`, reemplazar el bloque de configuración del depósito en el sidebar (líneas 14-24, el `with st.sidebar:` completo) por:

```python
DEPOT = (-34.557597673622126, -58.47277351349536)

with st.sidebar:
    st.header("Configuración")
    capacidad = st.number_input(
        "Capacidad del vehículo (maples/cajones)",
        min_value=1, value=100, step=1)
    st.caption(f"Depósito fijo: {DEPOT[0]:.5f}, {DEPOT[1]:.5f}")
    zona_fin = st.text_input(
        "Zona donde termina el repartidor (opcional)",
        help="Ej: Boulogne, San Isidro. Vacío = la ruta vuelve al depósito.")
```

- [ ] **Step 2: Geocodificar la zona de fin antes de resolver**

En `app.py`, dentro del bloque `if archivo and st.button(...)`, después del bloque de geocoding de clientes (después de `if not ok: ... st.stop()`) y **antes** de `with st.spinner("Calculando rutas óptimas..."):`, insertar:

```python
    fin_coord = None
    if zona_fin.strip():
        fin_coord = geocoder.geocode_fn(zona_fin.strip())
        if fin_coord is None:
            st.warning(f"No se pudo ubicar la zona de fin «{zona_fin}». "
                       "Las rutas vuelven al depósito.")
```

- [ ] **Step 3: Pasar el depósito fijo y el fin al solver y al mapa**

En `app.py`, reemplazar la llamada al solver:

```python
        rutas, sobre = solve((depot_lat, depot_lon), ok, capacidad)
```
por:
```python
        rutas, sobre = solve(DEPOT, ok, capacidad, fin=fin_coord)
```

Y reemplazar la llamada al render del mapa:
```python
    st_folium(render_map((depot_lat, depot_lon), rutas),
              use_container_width=True, height=600)
```
por:
```python
    st_folium(render_map(DEPOT, rutas, fin=fin_coord),
              use_container_width=True, height=600)
```

- [ ] **Step 4: Verificar que no queden referencias a `depot_lat`/`depot_lon`**

Run: `python -m pytest -q` (regresión completa)
Expected: PASS (28 + 3 nuevos = 31 tests)

Verificar manualmente que `depot_lat` y `depot_lon` ya no aparecen en `app.py` (búsqueda en el archivo).

- [ ] **Step 5: Validar en la app**

Run: `python -m streamlit run app.py`
- Subir `tests/fixtures/sample_clients.xlsx`.
- Con el campo de zona **vacío**: las rutas cierran en el depósito (marcador 🏠).
- Con `Boulogne, San Isidro` en el campo: aparece marcador de fin (🏁) y las últimas paradas caen hacia esa zona.

- [ ] **Step 6: Commit**

```bash
git add app.py
git commit -m "feat: deposito fijo y zona de fin configurable en la UI"
```

---

## Notas de implementación

- **Geocoding de la zona:** se reusa `geocoder.geocode_fn` (la misma función de Google ya instanciada para los clientes). Devuelve `(lat, lon)` o `None`.
- **Distancia mostrada:** el tramo final (última entrega → zona de fin) se cuenta en los km del día, porque el loop suma `GetArcCostForVehicle` hasta el nodo de fin. Es intencional (representa el viaje hacia la zona).
- **Vehículos vacíos:** con inicio/fin separados, un vehículo sin paradas va directo depósito→fin y se descarta con el `continue` existente (`if routing.IsEnd(sol.Value(routing.NextVar(idx)))`), sin sumar distancia.
