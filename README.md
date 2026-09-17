# LFIT Visualizer — prototipo inicial

## Ejecutar en Windows

1. Abre PowerShell en esta carpeta.
2. Crea un entorno virtual:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

3. Instala dependencias:

```powershell
pip install -r requirements.txt
```

4. Ejecuta la aplicación:

```powershell
streamlit run app.py
```

## Estado actual

Incluye:
- carga y exploración real de CSV;
- selección de variables;
- configuración visual de discretización;
- configuración de ejecución;
- resultados simulados;
- exportación.

Todavía no incluye:
- discretización real;
- integración con LFIT/PRIDE;
- métricas de reglas;
- grafo de relaciones.
