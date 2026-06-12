import math
from ortools.constraint_solver import pywrapcp, routing_enums_pb2
from routing.models import Client, Route, Stop
from routing.distance import build_distance_matrix, haversine_km


def _num_dias_minimo(demandas: list[int], capacidad: int) -> int:
    total = sum(demandas)
    por_pico = math.ceil(total / capacidad) if capacidad else 1
    return max(1, por_pico)


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
