import pandas as pd
import pytest
from routing.excel_loader import load_clients, ColumnaFaltante


def _excel(tmp_path, rows, cols):
    df = pd.DataFrame(rows, columns=cols)
    p = tmp_path / "in.xlsx"
    df.to_excel(p, index=False)
    return p


def test_carga_basica(tmp_path):
    p = _excel(tmp_path,
               [["Don Jose", "San Martin 1234", 8, "Quilmes"]],
               ["cliente", "direccion", "cantidad", "localidad"])
    clientes, revisar = load_clients(p)
    assert len(clientes) == 1
    assert revisar == []
    assert clientes[0].cliente == "Don Jose"
    assert clientes[0].cantidad == 8
    assert clientes[0].localidad == "Quilmes"
    assert clientes[0].fila == 1


def test_columnas_con_acentos_y_mayusculas(tmp_path):
    p = _excel(tmp_path,
               [["X", "Calle 1", 3]],
               ["Cliente", "Direccion", "Cantidad"])
    clientes, _ = load_clients(p)
    assert clientes[0].cliente == "X"


def test_falta_columna_obligatoria(tmp_path):
    p = _excel(tmp_path, [["X", "Calle 1"]], ["cliente", "direccion"])
    with pytest.raises(ColumnaFaltante) as e:
        load_clients(p)
    assert "cantidad" in str(e.value)


def test_localidad_opcional(tmp_path):
    p = _excel(tmp_path, [["X", "Calle 1", 3]],
               ["cliente", "direccion", "cantidad"])
    clientes, _ = load_clients(p)
    assert clientes[0].localidad == ""


def test_cantidad_invalida_va_a_revisar(tmp_path):
    p = _excel(tmp_path,
               [["Bien", "Calle 1", 5], ["Mal", "Calle 2", "abc"]],
               ["cliente", "direccion", "cantidad"])
    clientes, revisar = load_clients(p)
    assert len(clientes) == 1
    assert clientes[0].cliente == "Bien"
    assert len(revisar) == 1
    assert revisar[0]["fila"] == 2
    assert "cantidad" in revisar[0]["motivo"].lower()


def test_cantidad_cero_o_negativa_va_a_revisar(tmp_path):
    p = _excel(tmp_path,
               [["Cero", "Calle 1", 0], ["Neg", "Calle 2", -3]],
               ["cliente", "direccion", "cantidad"])
    clientes, revisar = load_clients(p)
    assert clientes == []
    assert len(revisar) == 2


def test_direccion_vacia_va_a_revisar(tmp_path):
    p = _excel(tmp_path, [["X", "", 5]],
               ["cliente", "direccion", "cantidad"])
    clientes, revisar = load_clients(p)
    assert clientes == []
    assert len(revisar) == 1
    assert "direccion" in revisar[0]["motivo"].lower()
