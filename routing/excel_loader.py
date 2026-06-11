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
