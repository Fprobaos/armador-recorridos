import streamlit as st
from streamlit_folium import st_folium
from routing.excel_loader import load_clients, ColumnaFaltante
from routing.geocoder import Geocoder, google_geocode_fn
from routing.solver import solve
from routing.map_render import render_map
from routing.exporter import to_result_dataframe, to_excel_bytes

CACHE_PATH = "geocode_cache.json"
DEPOT = (-34.557597673622126, -58.47277351349536)

st.set_page_config(page_title="Armador de Recorridos", layout="wide")
st.title("🥚 Armador de Recorridos")

with st.sidebar:
    st.header("Configuración")
    capacidad = st.number_input(
        "Capacidad del vehículo (maples/cajones)",
        min_value=1, value=100, step=1)
    st.caption(f"Depósito fijo: {DEPOT[0]:.5f}, {DEPOT[1]:.5f}")
    zona_fin = st.text_input(
        "Zona donde termina el repartidor (opcional)",
        help="Ej: Boulogne, San Isidro. Vacío = la ruta vuelve al depósito.")

archivo = st.file_uploader("Subí el Excel de clientes", type=["xlsx"])

if archivo and st.button("Calcular rutas", type="primary"):
    try:
        clientes, revisar = load_clients(archivo)
    except ColumnaFaltante as e:
        st.error(str(e))
        st.stop()

    api_key = st.secrets.get("GOOGLE_MAPS_API_KEY")
    if not api_key:
        st.error("Falta configurar GOOGLE_MAPS_API_KEY en los secrets de "
                 "Streamlit. Ver README.")
        st.stop()

    with st.spinner("Geocodificando direcciones..."):
        geocoder = Geocoder(CACHE_PATH, google_geocode_fn(api_key))
        ok, fallidos = geocoder.geocode_clients(clientes)

    if not ok:
        st.error("Ninguna dirección pudo geocodificarse. Revisá la planilla.")
        st.stop()

    fin_coord = None
    if zona_fin.strip():
        fin_coord = geocoder.geocode_fn(zona_fin.strip())
        if fin_coord is None:
            st.warning(f"No se pudo ubicar la zona de fin «{zona_fin}». "
                       "Las rutas vuelven al depósito.")

    with st.spinner("Calculando rutas óptimas..."):
        rutas, sobre = solve(DEPOT, ok, capacidad, fin=fin_coord)

    if not rutas:
        st.error("No se pudo armar ninguna ruta. Probablemente todos los "
                 "pedidos superan la capacidad del vehículo — revisá los "
                 "avisos de abajo y/o subí la capacidad.")
        if sobre:
            st.dataframe([{"cliente": c.cliente, "cantidad": c.cantidad}
                          for c in sobre])
        st.stop()

    st.success(f"{len(rutas)} días de reparto para {sum(len(r.stops) for r in rutas)} clientes.")
    st.caption("Distancias y orden de visita calculados en línea recta "
               "(no por calles). Sirven para agrupar zonas; el recorrido fino "
               "lo ajusta el repartidor.")

    # Resumen por día
    resumen = [{
        "Día": r.dia,
        "Paradas": len(r.stops),
        "Carga": r.carga_total,
        "Distancia (km)": r.distancia_km,
    } for r in rutas]
    st.subheader("Resumen por día")
    st.dataframe(resumen, use_container_width=True)

    # Mapa
    st.subheader("Mapa de rutas")
    st_folium(render_map(DEPOT, rutas, fin=fin_coord),
              use_container_width=True, height=600)

    # Descarga
    df = to_result_dataframe(rutas)
    st.download_button(
        "⬇️ Descargar Excel de rutas",
        data=to_excel_bytes(df),
        file_name="rutas.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    # Avisos
    if sobre:
        st.warning("Clientes que piden más que la capacidad del vehículo "
                   "(dividir a mano):")
        st.dataframe([{"cliente": c.cliente, "cantidad": c.cantidad}
                      for c in sobre])
    if fallidos:
        st.warning("Direcciones que Google no encontró (corregir y reprocesar):")
        st.dataframe([{"fila": c.fila, "cliente": c.cliente,
                       "direccion": c.direccion} for c in fallidos])
    if revisar:
        st.warning("Filas con datos inválidos:")
        st.dataframe(revisar)
