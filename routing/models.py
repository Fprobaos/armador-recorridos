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
