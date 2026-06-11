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
