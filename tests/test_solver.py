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


def test_todos_sobredimensionados_no_genera_rutas():
    clientes = [_c("A", -34.61, -58.39, 50), _c("B", -34.62, -58.40, 80)]
    rutas, sobre = solve(DEPOT, clientes, capacidad=10)
    assert rutas == []
    assert [c.cliente for c in sobre] == ["A", "B"]


def test_un_solo_cliente_genera_un_dia_con_una_parada():
    rutas, sobre = solve(DEPOT, [_c("Unico", -34.61, -58.39, 3)], capacidad=10)
    assert sobre == []
    assert len(rutas) == 1
    assert len(rutas[0].stops) == 1
    assert rutas[0].stops[0].client.cliente == "Unico"


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
