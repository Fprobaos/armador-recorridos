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
