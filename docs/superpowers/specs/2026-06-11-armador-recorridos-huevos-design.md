# Armador de Recorridos — Reparto de Huevos

**Fecha:** 2026-06-11
**Estado:** Diseño aprobado

## Objetivo

App web donde la jefa sube un Excel con clientes a repartir y obtiene un mapa
con las rutas agrupadas por día, optimizadas para recorrer la menor distancia
posible respetando la capacidad del vehículo.

## El problema

Variante de **VRP con capacidad (CVRP)**:

- Depósito único: cada día sale y vuelve al mismo punto.
- Cada cliente tiene una demanda (`cantidad`).
- El vehículo tiene una capacidad máxima por viaje.
- **Objetivo:** minimizar la distancia total recorrida.
- **Cantidad de días:** sale sola — es el mínimo de viajes para cubrir todo
  sin pasarse de carga, repartido parejo.

## Contexto de uso

- 200 a 1000 clientes. La lista cambia cada semana.
- Usuaria no técnica: subir planilla → ver resultado. Cero instalación.
- Resultado principal: mapa visual con rutas pintadas por día.

## Arquitectura

**Streamlit + Google OR-Tools**, publicada en Streamlit Community Cloud.

```
Excel → Geocodificar (Google + cache) → Resolver ruteo (OR-Tools) → Mapa + descargas
```

Una sola pantalla con barra lateral de configuración. La usuaria sube el Excel,
aprieta "Calcular rutas", y abajo aparece el mapa + descargas.

### Componentes

| Componente | Responsabilidad | Depende de |
|---|---|---|
| `app.py` | UI Streamlit: upload, sidebar, render de resultados | streamlit, folium |
| Lector de Excel | Validar columnas, normalizar datos | pandas |
| Geocodificador | Texto → lat/long, con cache | Google Geocoding API |
| Solver de ruteo | CVRP: agrupar en días + ordenar paradas | OR-Tools |
| Render de mapa | Pintar rutas por día | folium / Leaflet |
| Exportador | Excel resultado con `dia` y `orden_visita` | pandas |

Cada componente tiene una función clara y se puede probar por separado.

## Formato del Excel de entrada

Detección de columnas flexible (ignora mayúsculas/acentos):

| Columna | Obligatoria | Ejemplo |
|---|---|---|
| `cliente` | sí | Almacén Don José |
| `direccion` | sí | Av. San Martín 1234 |
| `cantidad` | sí | 8 |
| `localidad` | opcional (recomendada) | Quilmes, Buenos Aires |

`localidad` mejora la precisión del geocoding (evita confusión con calles
repetidas en distintas ciudades).

El **depósito** se carga una vez en la barra lateral (dirección o coordenada),
no va en el Excel.

## Geocodificación + cache

- Cada dirección de texto se convierte a lat/long con **Google Geocoding API**.
- **Cache** en `geocode_cache.json`: las direcciones ya resueltas no se vuelven
  a consultar → no se re-pagan y son instantáneas. Solo se cobran las nuevas.
- **Costo:** Google da USD 200 gratis/mes (~40.000 direcciones). Con cache, en
  la práctica es gratis o centavos.
- **Direcciones que fallan:** no frenan la app. Van a una lista aparte de
  "direcciones a revisar"; la ruta se arma con el resto.
- **Requisito único:** una API key de Google Cloud (guardada como secret en
  Streamlit, nunca en el repo).

## Motor de ruteo (días + capacidad)

OR-Tools configurado como CVRP:

- Cada día = una ruta que arranca y termina en el depósito.
- **Restricción de capacidad:** la suma de `cantidad` por día no supera la
  capacidad del vehículo. Al llenarse, se cierra el día y se abre otro.
- **Objetivo:** minimizar la distancia total de todos los días.
- **Cantidad de días:** mínima necesaria, repartida pareja.
- **Distancia:** línea recta (haversine). Rápida, gratis, suficiente para
  agrupar zonas y ordenar paradas a esta escala. (Distancia real por calles
  queda como mejora futura opcional, con costo de API.)

### Controles editables (barra lateral)

- Capacidad del vehículo (valor por defecto editable).
- Opcional: máximo de días o máximo de paradas por día.

## Mapa y descargas

- **Mapa interactivo** (folium/Leaflet): un color por día, puntos numerados en
  orden de visita, depósito marcado, tooltip con cliente/dirección/cantidad.
- **Resumen por día:** tabla con paradas, carga total, distancia estimada.
- **Descargas:**
  - Excel resultado: listado + columnas `dia` y `orden_visita`.
  - Lista de "direcciones a revisar".

> Link de Google Maps por día: fuera de alcance por ahora, fácil de sumar luego.

## Manejo de errores

- Falta columna obligatoria → mensaje claro, no rompe.
- Dirección no encontrada → lista "a revisar", ruta con el resto.
- Cantidad vacía o no numérica → fila a revisar.
- Cliente que pide más que la capacidad → aviso (no entra en ningún viaje).
- Sin API key → mensaje con instrucciones de configuración.

## Publicación

- Código en este repo. Local: `streamlit run app.py`.
- Producción: **Streamlit Community Cloud** (gratis), acceso por URL.
- API key de Google como secret de Streamlit.
- `geocode_cache.json` versionado en el repo para no re-pagar direcciones.

## Fuera de alcance (por ahora)

- Link de Google Maps por día.
- Distancia real por calles.
- Ventanas horarias, prioridades, múltiples vehículos con distinta capacidad,
  múltiples depósitos.
- Frecuencia de visita distinta por cliente (hoy: todos una vez por ciclo).

## Pruebas

- Lector de Excel: archivos con/sin columnas, acentos, cantidad inválida.
- Geocodificador: hit de cache, dirección fallida, sin API key.
- Solver: capacidad respetada, demanda > capacidad, depósito presente.
- End-to-end: planilla de ejemplo → días esperados + mapa renderiza.
