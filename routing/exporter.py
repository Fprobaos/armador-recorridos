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
