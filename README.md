# Armador de Recorridos 🥚

App que arma rutas de reparto óptimas a partir de un Excel de clientes.

## Formato del Excel
Columnas: `cliente`, `direccion`, `cantidad` (obligatorias), `localidad` (opcional).

## Correr local
```bash
pip install -r requirements.txt
streamlit run app.py
```

## API key de Google (geocoding)
1. Entrar a https://console.cloud.google.com/ → crear proyecto.
2. Habilitar **Geocoding API**.
3. Crear credencial → API key.
4. Local: crear `.streamlit/secrets.toml` con:
   ```toml
   GOOGLE_MAPS_API_KEY = "tu_key"
   ```
5. En Streamlit Cloud: cargar el mismo secret en Settings → Secrets.

## Publicar
Subir el repo a GitHub y conectar en https://share.streamlit.io.

## Tests
```bash
pytest -v
```
