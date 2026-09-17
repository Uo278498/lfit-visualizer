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
- detección básica de codificación y separador CSV;
- selección de variables;
- discretización real por cuantiles, amplitud igual o cortes manuales;
- vista previa antes/después y exportación del dataset procesado;
- validación de la configuración y avisos de valores ausentes;
- configuración de ejecución;
- resultados simulados;
- exportación.

Todavía no incluye:
- integración con LFIT/PRIDE;
- métricas de reglas;
- grafo de relaciones.

## Comprobar la lógica

Con el entorno virtual activado:

```powershell
python -m unittest -v test_core.py
```
