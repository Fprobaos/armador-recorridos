# Armador de Recorridos — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** App Streamlit que toma un Excel de clientes (cliente, dirección, cantidad), geocodifica con Google, resuelve un CVRP con OR-Tools y muestra un mapa con las rutas agrupadas por día.

**Architecture:** Lógica pura en el paquete `routing/` (cargador de Excel, geocoder con cache, matriz de distancias haversine, solver OR-Tools, render de mapa, exportador). `app.py` solo orquesta la UI de Streamlit y llama a esas funciones. Cada módulo es testeable de forma aislada inyectando dependencias (ej: el geocoder recibe una función de geocodificación, no llama a la red directo).

**Tech Stack:** Python 3.11+, Streamlit, Google OR-Tools, pandas, openpyxl, folium / streamlit-folium, googlemaps, pytest.

---

## Estructura de archivos

```
direcciones-jefa/
  app.py                    # UI Streamlit (orquestación)
  routing/
    __init__.py
    models.py               # dataclasses: Client, Route, Stop
    excel_loader.py         # cargar + validar Excel
    distance.py             # haversine + matriz de distancias
    geocoder.py             # texto → lat/long con cache JSON
    solver.py               # CVRP con OR-Tools
    map_render.py           # folium map por día
    exporter.py             # DataFrame/Excel resultado
  tests/
    __init__.py
    test_excel_loader.py
    test_distance.py
    test_geocoder.py
    test_solver.py
    test_exporter.py
    fixtures/
      sample_clients.xlsx   # generado en Task 2
  requirements.txt
  .gitignore
  README.md
```

Responsabilidad por archivo:
- `models.py` — tipos compartidos, sin lógica.
- `excel_loader.py` — leer planilla, normalizar columnas, separar filas válidas de "a revisar".
- `distance.py` — cálculo geométrico puro (sin red).
- `geocoder.py` — dirección → coordenada, con cache en disco; geocodificación inyectable.
- `solver.py` — agrupar en días respetando capacidad y minimizar distancia.
- `map_render.py` — pintar rutas.
- `exporter.py` — armar Excel de salida.
- `app.py` — pegamento Streamlit, único módulo que conoce la UI.

---

### Task 1: Scaffolding del proyecto

**Files:**
- Create: `requirements.txt`
- Create: `.gitignore`
- Create: `routing/__init__.py`
- Create: `tests/__init__.py`

- [ ] **Step 1: Crear `requirements.txt`**

```
streamlit>=1.40
ortools>=9.14
pandas>=2.2
openpyxl>=3.1
folium>=0.19
streamlit-folium>=0.25
googlemaps>=4.10
pytest>=8
```

> Pins flexibles (`>=`) a propósito: el entorno corre Python 3.14, donde varias
> de estas libs solo tienen wheels en sus últimas versiones (ej: ortools 9.15+).
> Dejar que pip resuelva evita fallos de instalación por wheels faltantes.

- [ ] **Step 2: Crear `.gitignore`**

```
__pycache__/
*.pyc
.venv/
venv/
.streamlit/secrets.toml
.pytest_cache/
```

- [ ] **Step 3: Crear paquetes vacíos**

`routing/__init__.py` y `tests/__init__.py` como archivos vacíos.

- [ ] **Step 4: Instalar y verificar**

Run: `pip install -r requirements.txt && python -c "import ortools, streamlit, folium, googlemaps; print('ok')"`
Expected: imprime `ok` sin errores de import.

- [ ] **Step 5: Commit**

```bash
git add requirements.txt .gitignore routing/__init__.py tests/__init__.py
git commit -m "chore: scaffolding del proyecto y dependencias"
```

---

### Task 2: Modelos de datos

**Files:**
- Create: `routing/models.py`

- [ ] **Step 1: Escribir `routing/models.py`**

```python
from dataclasses import dataclass, field


@dataclass
class Client:
    cliente: str
    direccion: str
    cantidad: float
    localidad: str = ""
    lat: float | None = None
    lon: float | None = None
    fila: int = 0  # número de fila original en el Excel (1-based, sin header)


@dataclass
class Stop:
    client: Client
    orden_visita: int  # 1-based dentro del día


@dataclass
class Route:
    dia: int  # 1-based
    stops: list[Stop] = field(default_factory=list)
    carga_total: float = 0.0
    distancia_km: float = 0.0
```

- [ ] **Step 2: Verificar import**

Run: `python -c "from routing.models import Client, Stop, Route; print(Client('a','b',1).cantidad)"`
Expected: imprime `1`

- [ ] **Step 3: Commit**

```bash
git add routing/models.py
git commit -m "feat: modelos de datos Client, Stop, Route"
```

---

### Task 3: Cálculo de distancias (haversine)

**Files:**
- Create: `routing/distance.py`
- Test: `tests/test_distance.py`

- [ ] **Step 1: Escribir el test que falla**

```python
# tests/test_distance.py
from routing.distance import haversine_km, build_distance_matrix


def test_haversine_misma_coordenada_es_cero():
    assert haversine_km(-34.6, -58.4, -34.6, -58.4) == 0.0


def test_haversine_distancia_conocida():
    # Obelisco BA (-34.6037,-58.3816) a La Plata (-34.9215,-57.9545) ≈ 54 km
    d = haversine_km(-34.6037, -58.3816, -34.9215, -57.9545)
    assert 50 < d < 60


def test_matriz_es_simetrica_y_diagonal_cero():
    puntos = [(-34.60, -58.38), (-34.92, -57.95), (-34.70, -58.30)]
    m = build_distance_matrix(puntos)
    assert len(m) == 3
    assert m[0][0] == 0
    assert m[1][2] == m[2][1]  # simétrica
    assert m[0][1] > 0


def test_matriz_devuelve_enteros_en_metros():
    puntos = [(-34.60, -58.38), (-34.92, -57.95)]
    m = build_distance_matrix(puntos)
    assert isinstance(m[0][1], int)
    assert m[0][1] > 40000  # ~54 km en metros
```

- [ ] **Step 2: Correr el test y verificar que falla**

Run: `pytest tests/test_distance.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'routing.distance'`

- [ ] **Step 3: Escribir la implementación mínima**

```python
# routing/distance.py
import math

EARTH_RADIUS_KM = 6371.0088


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    if lat1 == lat2 and lon1 == lon2:
        return 0.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = (math.sin(dphi / 2) ** 2
         + math.cos(p1) * math.cos(p2) * math.sin(dlambda / 2) ** 2)
    return 2 * EARTH_RADIUS_KM * math.asin(math.sqrt(a))


def build_distance_matrix(puntos: list[tuple[float, float]]) -> list[list[int]]:
    """Matriz NxN de distancias en metros enteros (lo que espera OR-Tools)."""
    n = len(puntos)
    matriz = [[0] * n for _ in range(n)]
    for i in range(n):
        for j in range(i + 1, n):
            metros = int(round(haversine_km(*puntos[i], *puntos[j]) * 1000))
            matriz[i][j] = metros
            matriz[j][i] = metros
    return matriz
```

- [ ] **Step 4: Correr el test y verificar que pasa**

Run: `pytest tests/test_distance.py -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add routing/distance.py tests/test_distance.py
git commit -m "feat: distancia haversine y matriz de distancias"
```

---

### Task 4: Cargador de Excel

**Files:**
- Create: `routing/excel_loader.py`
- Test: `tests/test_excel_loader.py`

**Interfaz:** `load_clients(file) -> tuple[list[Client], list[dict]]` donde el
segundo elemento es la lista de filas "a revisar" con `{fila, motivo, datos}`.

- [ ] **Step 1: Escribir el test que falla**

```python
# tests/test_excel_loader.py
import pandas as pd
import pytest
from routing.excel_loader import load_clients, ColumnaFaltante


def _excel(tmp_path, rows, cols):
    df = pd.DataFrame(rows, columns=cols)
    p = tmp_path / "in.xlsx"
    df.to_excel(p, index=False)
    return p


def test_carga_basica(tmp_path):
    p = _excel(tmp_path,
               [["Don Jose", "San Martin 1234", 8, "Quilmes"]],
               ["cliente", "direccion", "cantidad", "localidad"])
    clientes, revisar = load_clients(p)
    assert len(clientes) == 1
    assert revisar == []
    assert clientes[0].cliente == "Don Jose"
    assert clientes[0].cantidad == 8
    assert clientes[0].localidad == "Quilmes"
    assert clientes[0].fila == 1


def test_columnas_con_acentos_y_mayusculas(tmp_path):
    p = _excel(tmp_path,
               [["X", "Calle 1", 3]],
               ["Cliente", "Direccion", "Cantidad"])
    clientes, _ = load_clients(p)
    assert clientes[0].cliente == "X"


def test_falta_columna_obligatoria(tmp_path):
    p = _excel(tmp_path, [["X", "Calle 1"]], ["cliente", "direccion"])
    with pytest.raises(ColumnaFaltante) as e:
        load_clients(p)
    assert "cantidad" in str(e.value)


def test_localidad_opcional(tmp_path):
    p = _excel(tmp_path, [["X", "Calle 1", 3]],
               ["cliente", "direccion", "cantidad"])
    clientes, _ = load_clients(p)
    assert clientes[0].localidad == ""


def test_cantidad_invalida_va_a_revisar(tmp_path):
    p = _excel(tmp_path,
               [["Bien", "Calle 1", 5], ["Mal", "Calle 2", "abc"]],
               ["cliente", "direccion", "cantidad"])
    clientes, revisar = load_clients(p)
    assert len(clientes) == 1
    assert clientes[0].cliente == "Bien"
    assert len(revisar) == 1
    assert revisar[0]["fila"] == 2
    assert "cantidad" in revisar[0]["motivo"].lower()


def test_cantidad_cero_o_negativa_va_a_revisar(tmp_path):
    p = _excel(tmp_path,
               [["Cero", "Calle 1", 0], ["Neg", "Calle 2", -3]],
               ["cliente", "direccion", "cantidad"])
    clientes, revisar = load_clients(p)
    assert clientes == []
    assert len(revisar) == 2


def test_direccion_vacia_va_a_revisar(tmp_path):
    p = _excel(tmp_path, [["X", "", 5]],
               ["cliente", "direccion", "cantidad"])
    clientes, revisar = load_clients(p)
    assert clientes == []
    assert len(revisar) == 1
    assert "direccion" in revisar[0]["motivo"].lower()
```

- [ ] **Step 2: Correr el test y verificar que falla**

Run: `pytest tests/test_excel_loader.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'routing.excel_loader'`

- [ ] **Step 3: Escribir la implementación mínima**

```python
# routing/excel_loader.py
import unicodedata
import pandas as pd
from routing.models import Client

OBLIGATORIAS = ("cliente", "direccion", "cantidad")
OPCIONALES = ("localidad",)


class ColumnaFaltante(Exception):
    pass


def _normalizar(texto: str) -> str:
    t = unicodedata.normalize("NFKD", str(texto))
    t = "".join(c for c in t if not unicodedata.combining(c))
    return t.strip().lower()


def _mapa_columnas(df: pd.DataFrame) -> dict:
    encontrado = {}
    for col in df.columns:
        norm = _normalizar(col)
        for objetivo in OBLIGATORIAS + OPCIONALES:
            if norm == objetivo:
                encontrado[objetivo] = col
    return encontrado


def load_clients(file) -> tuple[list[Client], list[dict]]:
    df = pd.read_excel(file)
    cols = _mapa_columnas(df)

    faltantes = [c for c in OBLIGATORIAS if c not in cols]
    if faltantes:
        raise ColumnaFaltante(
            f"Faltan columnas obligatorias: {', '.join(faltantes)}")

    clientes: list[Client] = []
    revisar: list[dict] = []

    for idx, row in df.iterrows():
        fila = idx + 1  # 1-based, sin contar header
        datos = row.to_dict()
        direccion = str(row[cols["direccion"]]).strip()
        if direccion == "" or direccion.lower() == "nan":
            revisar.append({"fila": fila, "motivo": "direccion vacia",
                            "datos": datos})
            continue
        try:
            cantidad = float(row[cols["cantidad"]])
        except (ValueError, TypeError):
            revisar.append({"fila": fila, "motivo": "cantidad no numerica",
                            "datos": datos})
            continue
        if cantidad <= 0:
            revisar.append({"fila": fila, "motivo": "cantidad <= 0",
                            "datos": datos})
            continue

        localidad = ""
        if "localidad" in cols:
            val = str(row[cols["localidad"]]).strip()
            localidad = "" if val.lower() == "nan" else val

        clientes.append(Client(
            cliente=str(row[cols["cliente"]]).strip(),
            direccion=direccion,
            cantidad=cantidad,
            localidad=localidad,
            fila=fila,
        ))

    return clientes, revisar
```

- [ ] **Step 4: Correr el test y verificar que pasa**

Run: `pytest tests/test_excel_loader.py -v`
Expected: PASS (7 tests)

- [ ] **Step 5: Commit**

```bash
git add routing/excel_loader.py tests/test_excel_loader.py
git commit -m "feat: cargador de Excel con validacion de filas"
```

---

### Task 5: Geocoder con cache

**Files:**
- Create: `routing/geocoder.py`
- Test: `tests/test_geocoder.py`

**Interfaz:** `Geocoder(cache_path, geocode_fn)`. `geocode_fn(direccion) -> (lat, lon) | None`
se inyecta para testear sin red. `geocode_clients(clients) -> (ok, fallidos)`
escribe coordenadas en cada Client y persiste el cache.

- [ ] **Step 1: Escribir el test que falla**

```python
# tests/test_geocoder.py
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
```

- [ ] **Step 2: Correr el test y verificar que falla**

Run: `pytest tests/test_geocoder.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'routing.geocoder'`

- [ ] **Step 3: Escribir la implementación mínima**

```python
# routing/geocoder.py
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
        self._guardar()
        return ok, fallidos
```

- [ ] **Step 4: Correr el test y verificar que pasa**

Run: `pytest tests/test_geocoder.py -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add routing/geocoder.py tests/test_geocoder.py
git commit -m "feat: geocoder con cache en disco e inyeccion de funcion"
```

---

### Task 6: Solver CVRP con OR-Tools

**Files:**
- Create: `routing/solver.py`
- Test: `tests/test_solver.py`

**Interfaz:** `solve(depot, clients, capacidad, max_dias=None) -> tuple[list[Route], list[Client]]`.
`depot` es `(lat, lon)`. El segundo retorno son clientes "sobredimensionados"
(demanda > capacidad) que no entran en ningún viaje.

- [ ] **Step 1: Escribir el test que falla**

```python
# tests/test_solver.py
from routing.models import Client
from routing.solver import solve


DEPOT = (-34.60, -58.38)


def _c(nombre, lat, lon, cant):
    return Client(cliente=nombre, direccion=nombre, cantidad=cant,
                  lat=lat, lon=lon)


def test_todos_los_clientes_quedan_asignados():
    clientes = [
        _c("A", -34.61, -58.39, 2),
        _c("B", -34.62, -58.40, 2),
        _c("C", -34.90, -57.95, 2),
    ]
    rutas, sobre = solve(DEPOT, clientes, capacidad=10)
    asignados = [s.client.cliente for r in rutas for s in r.stops]
    assert sorted(asignados) == ["A", "B", "C"]
    assert sobre == []


def test_capacidad_se_respeta_y_genera_varios_dias():
    clientes = [_c(str(i), -34.6 - i / 100, -58.4, 6) for i in range(4)]
    rutas, sobre = solve(DEPOT, clientes, capacidad=10)
    # 4 clientes x 6 = 24, capacidad 10 -> al menos 3 dias
    assert len(rutas) >= 3
    for r in rutas:
        assert r.carga_total <= 10


def test_cada_ruta_tiene_orden_de_visita_consecutivo():
    clientes = [_c(str(i), -34.6 - i / 100, -58.4, 1) for i in range(5)]
    rutas, _ = solve(DEPOT, clientes, capacidad=100)
    for r in rutas:
        ordenes = [s.orden_visita for s in r.stops]
        assert ordenes == list(range(1, len(r.stops) + 1))


def test_cliente_que_excede_capacidad_va_a_sobredimensionados():
    clientes = [_c("Grande", -34.61, -58.39, 50), _c("Chico", -34.62, -58.40, 2)]
    rutas, sobre = solve(DEPOT, clientes, capacidad=10)
    asignados = [s.client.cliente for r in rutas for s in r.stops]
    assert "Chico" in asignados
    assert [c.cliente for c in sobre] == ["Grande"]


def test_carga_total_por_ruta_es_correcta():
    clientes = [_c("A", -34.61, -58.39, 3), _c("B", -34.62, -58.40, 4)]
    rutas, _ = solve(DEPOT, clientes, capacidad=100)
    total = sum(r.carga_total for r in rutas)
    assert total == 7


def test_distancia_km_por_ruta_es_positiva():
    clientes = [_c("A", -34.61, -58.39, 1), _c("B", -34.90, -57.95, 1)]
    rutas, _ = solve(DEPOT, clientes, capacidad=100)
    assert all(r.distancia_km > 0 for r in rutas)
```

- [ ] **Step 2: Correr el test y verificar que falla**

Run: `pytest tests/test_solver.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'routing.solver'`

- [ ] **Step 3: Escribir la implementación mínima**

```python
# routing/solver.py
import math
from ortools.constraint_solver import pywrapcp, routing_enums_pb2
from routing.models import Client, Route, Stop
from routing.distance import build_distance_matrix, haversine_km


def _num_dias_minimo(demandas: list[int], capacidad: int) -> int:
    total = sum(demandas)
    por_pico = math.ceil(total / capacidad) if capacidad else 1
    return max(1, por_pico)


def solve(depot, clients: list[Client], capacidad: float, max_dias=None):
    capacidad = int(capacidad)
    sobre = [c for c in clients if int(math.ceil(c.cantidad)) > capacidad]
    validos = [c for c in clients if int(math.ceil(c.cantidad)) <= capacidad]
    if not validos:
        return [], sobre

    # indice 0 = depot; 1..N = clientes
    puntos = [depot] + [(c.lat, c.lon) for c in validos]
    matriz = build_distance_matrix(puntos)
    demandas = [0] + [int(math.ceil(c.cantidad)) for c in validos]

    min_dias = _num_dias_minimo(demandas[1:], capacidad)
    # holgura de vehiculos para que el solver tenga margen
    num_vehiculos = max_dias or (min_dias + len(validos))

    manager = pywrapcp.RoutingIndexManager(len(puntos), num_vehiculos, 0)
    routing = pywrapcp.RoutingModel(manager)

    def dist_cb(i, j):
        return matriz[manager.IndexToNode(i)][manager.IndexToNode(j)]

    transit = routing.RegisterTransitCallback(dist_cb)
    routing.SetArcCostEvaluatorOfAllVehicles(transit)

    def demand_cb(i):
        return demandas[manager.IndexToNode(i)]

    demand_idx = routing.RegisterUnaryTransitCallback(demand_cb)
    routing.AddDimensionWithVehicleCapacity(
        demand_idx, 0, [capacidad] * num_vehiculos, True, "Capacidad")

    params = pywrapcp.DefaultRoutingSearchParameters()
    params.first_solution_strategy = (
        routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC)
    params.local_search_metaheuristic = (
        routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH)
    params.time_limit.FromSeconds(10)

    sol = routing.SolveWithParameters(params)
    if sol is None:
        raise RuntimeError("OR-Tools no encontro solucion")

    rutas: list[Route] = []
    dia = 0
    for v in range(num_vehiculos):
        idx = routing.Start(v)
        if routing.IsEnd(sol.Value(routing.NextVar(idx))):
            continue  # vehiculo sin paradas
        dia += 1
        ruta = Route(dia=dia)
        orden = 0
        dist_m = 0
        prev = idx
        while not routing.IsEnd(idx):
            nodo = manager.IndexToNode(idx)
            if nodo != 0:
                orden += 1
                cli = validos[nodo - 1]
                ruta.stops.append(Stop(client=cli, orden_visita=orden))
                ruta.carga_total += cli.cantidad
            nxt = sol.Value(routing.NextVar(idx))
            dist_m += routing.GetArcCostForVehicle(idx, nxt, v)
            idx = nxt
        ruta.distancia_km = round(dist_m / 1000, 2)
        rutas.append(ruta)

    return rutas, sobre
```

- [ ] **Step 4: Correr el test y verificar que pasa**

Run: `pytest tests/test_solver.py -v`
Expected: PASS (6 tests). Nota: cada test corre <10s por el time_limit.

- [ ] **Step 5: Commit**

```bash
git add routing/solver.py tests/test_solver.py
git commit -m "feat: solver CVRP con OR-Tools y agrupacion por dia"
```

---

### Task 7: Exportador de resultado

**Files:**
- Create: `routing/exporter.py`
- Test: `tests/test_exporter.py`

**Interfaz:** `to_result_dataframe(rutas) -> pd.DataFrame` y
`to_excel_bytes(df) -> bytes`.

- [ ] **Step 1: Escribir el test que falla**

```python
# tests/test_exporter.py
import io
import pandas as pd
from routing.models import Client, Route, Stop
from routing.exporter import to_result_dataframe, to_excel_bytes


def _ruta(dia, clientes):
    r = Route(dia=dia)
    for i, c in enumerate(clientes, start=1):
        r.stops.append(Stop(client=c, orden_visita=i))
        r.carga_total += c.cantidad
    return r


def _c(nombre, cant):
    return Client(cliente=nombre, direccion=f"dir {nombre}", cantidad=cant,
                  localidad="Quilmes", lat=-34.6, lon=-58.4)


def test_dataframe_tiene_columnas_dia_y_orden():
    rutas = [_ruta(1, [_c("A", 2), _c("B", 3)]), _ruta(2, [_c("C", 1)])]
    df = to_result_dataframe(rutas)
    assert list(df.columns) == [
        "dia", "orden_visita", "cliente", "direccion",
        "localidad", "cantidad", "lat", "lon"]
    assert len(df) == 3
    assert df.iloc[0]["dia"] == 1
    assert df.iloc[0]["orden_visita"] == 1
    assert df.iloc[2]["dia"] == 2


def test_excel_bytes_es_legible_por_pandas():
    rutas = [_ruta(1, [_c("A", 2)])]
    data = to_excel_bytes(to_result_dataframe(rutas))
    assert isinstance(data, bytes) and len(data) > 0
    df = pd.read_excel(io.BytesIO(data))
    assert df.iloc[0]["cliente"] == "A"
```

- [ ] **Step 2: Correr el test y verificar que falla**

Run: `pytest tests/test_exporter.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'routing.exporter'`

- [ ] **Step 3: Escribir la implementación mínima**

```python
# routing/exporter.py
import io
import pandas as pd
from routing.models import Route

COLUMNAS = ["dia", "orden_visita", "cliente", "direccion",
            "localidad", "cantidad", "lat", "lon"]


def to_result_dataframe(rutas: list[Route]) -> pd.DataFrame:
    filas = []
    for r in rutas:
        for s in r.stops:
            c = s.client
            filas.append({
                "dia": r.dia,
                "orden_visita": s.orden_visita,
                "cliente": c.cliente,
                "direccion": c.direccion,
                "localidad": c.localidad,
                "cantidad": c.cantidad,
                "lat": c.lat,
                "lon": c.lon,
            })
    return pd.DataFrame(filas, columns=COLUMNAS)


def to_excel_bytes(df: pd.DataFrame) -> bytes:
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as w:
        df.to_excel(w, index=False, sheet_name="Rutas")
    return buf.getvalue()
```

- [ ] **Step 4: Correr el test y verificar que pasa**

Run: `pytest tests/test_exporter.py -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add routing/exporter.py tests/test_exporter.py
git commit -m "feat: exportador de resultado a DataFrame y Excel"
```

---

### Task 8: Render de mapa

**Files:**
- Create: `routing/map_render.py`
- Test: `tests/test_map_render.py`

**Interfaz:** `render_map(depot, rutas) -> folium.Map`. Sin red. Test verifica
que devuelve un mapa folium y que el HTML contiene marcadores.

- [ ] **Step 1: Escribir el test que falla**

```python
# tests/test_map_render.py
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
```

- [ ] **Step 2: Correr el test y verificar que falla**

Run: `pytest tests/test_map_render.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'routing.map_render'`

- [ ] **Step 3: Escribir la implementación mínima**

```python
# routing/map_render.py
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
```

- [ ] **Step 4: Correr el test y verificar que pasa**

Run: `pytest tests/test_map_render.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add routing/map_render.py tests/test_map_render.py
git commit -m "feat: render de mapa folium con rutas por dia"
```

---

### Task 9: App Streamlit (orquestación)

**Files:**
- Create: `app.py`

No lleva test unitario (es UI); se valida corriendo la app. Toda la lógica ya
está testeada en `routing/`.

- [ ] **Step 1: Escribir `app.py`**

```python
import streamlit as st
from streamlit_folium import st_folium
from routing.excel_loader import load_clients, ColumnaFaltante
from routing.geocoder import Geocoder, google_geocode_fn
from routing.solver import solve
from routing.map_render import render_map
from routing.exporter import to_result_dataframe, to_excel_bytes

CACHE_PATH = "geocode_cache.json"

st.set_page_config(page_title="Armador de Recorridos", layout="wide")
st.title("🥚 Armador de Recorridos")

with st.sidebar:
    st.header("Configuración")
    capacidad = st.number_input(
        "Capacidad del vehículo (maples/cajones)",
        min_value=1, value=100, step=1)
    depot_lat = st.number_input("Latitud del depósito",
                                value=-34.6037, format="%.6f")
    depot_lon = st.number_input("Longitud del depósito",
                                value=-58.3816, format="%.6f")
    st.caption("Cargá las coordenadas de tu depósito (Google Maps → "
               "clic derecho → copiar lat/long).")

archivo = st.file_uploader("Subí el Excel de clientes", type=["xlsx"])

if archivo and st.button("Calcular rutas", type="primary"):
    try:
        clientes, revisar = load_clients(archivo)
    except ColumnaFaltante as e:
        st.error(str(e))
        st.stop()

    api_key = st.secrets.get("GOOGLE_MAPS_API_KEY")
    if not api_key:
        st.error("Falta configurar GOOGLE_MAPS_API_KEY en los secrets de "
                 "Streamlit. Ver README.")
        st.stop()

    with st.spinner("Geocodificando direcciones..."):
        geocoder = Geocoder(CACHE_PATH, google_geocode_fn(api_key))
        ok, fallidos = geocoder.geocode_clients(clientes)

    if not ok:
        st.error("Ninguna dirección pudo geocodificarse. Revisá la planilla.")
        st.stop()

    with st.spinner("Calculando rutas óptimas..."):
        rutas, sobre = solve((depot_lat, depot_lon), ok, capacidad)

    st.success(f"{len(rutas)} días de reparto para {sum(len(r.stops) for r in rutas)} clientes.")

    # Resumen por día
    resumen = [{
        "Día": r.dia,
        "Paradas": len(r.stops),
        "Carga": r.carga_total,
        "Distancia (km)": r.distancia_km,
    } for r in rutas]
    st.subheader("Resumen por día")
    st.dataframe(resumen, use_container_width=True)

    # Mapa
    st.subheader("Mapa de rutas")
    st_folium(render_map((depot_lat, depot_lon), rutas),
              use_container_width=True, height=600)

    # Descarga
    df = to_result_dataframe(rutas)
    st.download_button(
        "⬇️ Descargar Excel de rutas",
        data=to_excel_bytes(df),
        file_name="rutas.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    # Avisos
    if sobre:
        st.warning("Clientes que piden más que la capacidad del vehículo "
                   "(dividir a mano):")
        st.dataframe([{"cliente": c.cliente, "cantidad": c.cantidad}
                      for c in sobre])
    if fallidos:
        st.warning("Direcciones que Google no encontró (corregir y reprocesar):")
        st.dataframe([{"fila": c.fila, "cliente": c.cliente,
                       "direccion": c.direccion} for c in fallidos])
    if revisar:
        st.warning("Filas con datos inválidos:")
        st.dataframe(revisar)
```

- [ ] **Step 2: Correr la app localmente**

Run: `streamlit run app.py`
Expected: abre el navegador, muestra el título y el uploader sin errores de import.

- [ ] **Step 3: Commit**

```bash
git add app.py
git commit -m "feat: app Streamlit que orquesta carga, geocoding, ruteo y mapa"
```

---

### Task 10: Datos de ejemplo + README

**Files:**
- Create: `tests/fixtures/sample_clients.xlsx` (vía script)
- Create: `README.md`

- [ ] **Step 1: Generar planilla de ejemplo**

Run:
```bash
python -c "import pandas as pd; pd.DataFrame([
 ['Almacen Don Jose','Av San Martin 1234','Quilmes',8],
 ['Kiosco La Esquina','Calle 9 de Julio 500','Quilmes',4],
 ['Super Norte','Av Mitre 2000','Avellaneda',12],
 ['Despensa Sur','Belgrano 150','Lanus',6],
], columns=['cliente','direccion','localidad','cantidad']).to_excel('tests/fixtures/sample_clients.xlsx', index=False)"
```
Expected: crea el archivo sin error.

- [ ] **Step 2: Escribir `README.md`**

````markdown
# Armador de Recorridos 🥚

App que arma rutas de reparto óptimas a partir de un Excel de clientes.

## Formato del Excel
Columnas: `cliente`, `direccion`, `cantidad` (obligatorias), `localidad` (opcional).

## Correr local
```bash
pip install -r requirements.txt
streamlit run app.py
```

## API key de Google (geocoding)
1. Entrar a https://console.cloud.google.com/ → crear proyecto.
2. Habilitar **Geocoding API**.
3. Crear credencial → API key.
4. Local: crear `.streamlit/secrets.toml` con:
   ```toml
   GOOGLE_MAPS_API_KEY = "tu_key"
   ```
5. En Streamlit Cloud: cargar el mismo secret en Settings → Secrets.

## Publicar
Subir el repo a GitHub y conectar en https://share.streamlit.io.

## Tests
```bash
pytest -v
```
````

- [ ] **Step 3: Correr toda la suite**

Run: `pytest -v`
Expected: PASS (todos los tests de las tareas 3-8).

- [ ] **Step 4: Commit**

```bash
git add tests/fixtures/sample_clients.xlsx README.md
git commit -m "docs: README y planilla de ejemplo"
```

---

## Self-Review (cobertura del spec)

- App web subir Excel → resultado → **Tasks 4, 9** ✓
- Geocoding Google + cache + fallidos → **Task 5** ✓
- CVRP capacidad + días automáticos + minimizar distancia → **Task 6** ✓
- Distancia haversine → **Task 3** ✓
- Mapa por día con colores → **Task 8** ✓
- Capacidad editable en sidebar → **Task 9** ✓
- Excel resultado con `dia`/`orden_visita` → **Task 7** ✓
- Manejo de errores (columna faltante, dirección fallida, cantidad inválida, demanda > capacidad, sin API key) → **Tasks 4, 5, 6, 9** ✓
- Publicación Streamlit Cloud + secret → **Task 10 (README)** ✓
- Fuera de alcance (link Google Maps, distancia por calles) → no se implementa ✓
```
