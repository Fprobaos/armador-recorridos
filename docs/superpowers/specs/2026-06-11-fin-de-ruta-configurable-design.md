# Fin de ruta configurable (zona de término)

**Fecha:** 2026-06-11
**Estado:** Aprobado, pendiente de implementación

## Problema

Hoy cada ruta sale del depósito y vuelve al depósito (CVRP clásico con nodo único de inicio/fin). En la práctica el repartidor termina la jornada cerca de su zona (ej. Boulogne) y no necesita volver al depósito. Queremos que las últimas entregas del día caigan por esa zona para que termine cerca.

## Decisiones de diseño

- **Es una zona, no un punto exacto.** Se usa un punto de referencia (centro aproximado de la zona) como destino final. No se exige una parada exacta ahí; es una preferencia *suave* que tira el recorrido hacia esa zona.
- **Carga por nombre.** El usuario escribe el nombre de la zona (ej. "Boulogne, San Isidro") y la app lo geocodifica con la misma API de Google que ya usa (cacheado en `geocode_cache.json`).
- **Opcional y retrocompatible.** Campo vacío → comportamiento actual (sale y vuelve al depósito).
- **Aplica a todos los días/viajes.** El repartidor siempre quiere terminar cerca de casa.

## Comportamiento

### Sidebar
Nuevo campo de texto: **"Zona donde termina el repartidor (opcional)"**.

- **Vacío** → cada ruta sale y vuelve al depósito (igual que hoy).
- **Con texto** → la app geocodifica la zona y arma cada ruta para que **salga del depósito y termine en esa zona**. Las últimas entregas del día son las más cercanas al punto de referencia.

### Manejo de errores
- **Geocoding de la zona falla** (Google no la encuentra) → aviso amarillo (`st.warning`) y la ruta vuelve al depósito como hoy. No se interrumpe el cálculo de rutas.

## Cómo funciona por dentro

OR-Tools hoy usa el nodo 0 (depósito) como inicio **y** fin de todos los vehículos:
```python
manager = pywrapcp.RoutingIndexManager(len(puntos), num_vehiculos, 0)
```

Se cambia a inicio/fin separados cuando hay zona de fin:
- **Layout de nodos:** índice `0` = depósito; `1..N` = clientes; `N+1` = punto de referencia de la zona de fin (demanda 0, no es cliente).
- **Inicio = depósito** (nodo 0) para todos los vehículos.
- **Fin = nodo de la zona** (nodo N+1) para todos los vehículos.
```python
starts = [0] * num_vehiculos
ends = [fin_idx] * num_vehiculos
manager = pywrapcp.RoutingIndexManager(len(puntos), num_vehiculos, starts, ends)
```
- El nodo de fin nunca se visita como cliente: el loop de armado de paradas corta en `IsEnd`, así que no aparece como parada.
- Es una preferencia suave: minimizar la distancia total naturalmente hace que la última entrega real sea la más cercana a la zona y que el recorrido fluya hacia allá. No fuerza una parada exacta.

### Distancia mostrada
El último tramo (última entrega → zona de fin) se cuenta en los km del día, porque representa el viaje real hacia esa zona. (El loop ya suma `GetArcCostForVehicle` hasta el nodo final.)

## Componentes y archivos

| Archivo | Cambio |
|---------|--------|
| `routing/solver.py` | `solve()` acepta parámetro opcional `fin` (coordenada `(lat, lon)` o `None`). Si `fin` es `None`, comportamiento actual. Si no, agrega el nodo de fin a la matriz e instancia el manager con `starts`/`ends` separados. |
| `app.py` | Campo de texto nuevo en el sidebar. Si tiene valor, geocodificar la zona (reusando `Geocoder`); pasar la coordenada a `solve(..., fin=coord)`. Manejar geocoding fallido con warning + fallback a depósito. |
| `routing/map_render.py` | Marcador distinto (ej. 🏁) en la zona de fin cuando está definida. |
| `tests/test_solver.py` | Tests nuevos: (1) ruta con `fin` distinto al depósito termina cerca de la zona; (2) `fin=None` mantiene el comportamiento actual (vuelve al depósito). |

## Fuera de alcance

- Zona de fin distinta por día.
- Que el repartidor arranque desde Boulogne (inicio sigue siendo el depósito).
- Lista de zonas predefinidas / desplegable.
- Que el tramo final no sume a los km (se decidió contarlo).
