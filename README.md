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
- tratamiento explícito de valores ausentes antes de discretizar;
- discretización real por cuantiles, amplitud igual o cortes manuales;
- vista previa antes/después y exportación del dataset procesado;
- validación de la configuración y avisos de valores ausentes;
- ejecución experimental de PRIDE mediante `pylfit`;
- matriz y detalle de reglas aprendidas;
- exportación.

Todavía no incluye:
- modo LFIT longitudinal basado en transiciones temporales;
- métricas de reglas;
- grafo de relaciones.

## Alcance actual de PRIDE

La primera integración aprende reglas estáticas entre entradas discretizadas y una salida discreta.
No representa todavía transiciones temporales entre visitas de un mismo paciente, por lo que no debe
interpretarse como un modelo de evolución clínica.

`pylfit`, la dependencia que proporciona PRIDE, se distribuye bajo licencia GPL-3.0. Revisa esta
implicación con la dirección del TFG antes de distribuir o desplegar el proyecto fuera del ámbito académico.

## Estructura del proyecto

```text
app.py                 # Punto de entrada y navegación
views/                 # Una pantalla de interfaz por módulo
src/                   # Lógica de datos, estado y transformaciones
test_core.py           # Pruebas automatizadas de la lógica principal
```

## Comprobar la lógica

Con el entorno virtual activado:

```powershell
python -m unittest -v test_core.py
```
