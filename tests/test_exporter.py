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
