# LFIT Visualizer

Prototipo de TFG para preparar datasets clínicos, aprender reglas estáticas con PRIDE y explorar la teoría resultante de forma trazable.

## Ejecutar en Windows

En PowerShell, dentro de esta carpeta:

```powershell
.\.venv\Scripts\Activate.ps1
streamlit run app.py
```

Si el entorno aún no existe:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
streamlit run app.py
```

## Flujo de trabajo

1. Cargar un CSV y revisar sus variables.
2. Asignar roles: entradas, una salida, identificador o exclusión.
3. Tratar los valores ausentes y discretizar las entradas numéricas.
4. Ejecutar PRIDE.
5. Explorar, comparar y filtrar las reglas; revisar sus métricas y trazabilidad.
6. Exportar reglas, datos procesados, trazabilidad e informe resumido.

## Estado actual

Incluye:

- carga de CSV con detección básica de codificación y separador;
- selección de variables, tratamiento explícito de ausentes y discretización;
- ejecución experimental de PRIDE mediante `pylfit`;
- matriz de reglas, filtros, comparador, detalle y grafo de relaciones;
- métricas por regla: cobertura, casos compatibles, consistencia observada, frecuencia de salida y lift;
- indicadores descriptivos por variable y hallazgos para revisión;
- trazabilidad de la ejecución: entradas, salida, filas, transformaciones, algoritmo y versión;
- exportación CSV, JSON de trazabilidad e informe resumido.

### Interpretación responsable

Las métricas se calculan en el mismo dataset usado para aprender la teoría:

- **Cobertura**: filas que cumplen el antecedente.
- **Consistencia**: proporción de filas cubiertas cuya salida coincide con la regla.
- **Lift**: consistencia dividida por la frecuencia global de ese valor de salida.

Por tanto, ayudan a explorar patrones y priorizar su revisión, pero no demuestran validación clínica externa, generalización ni causalidad. La presencia de una variable en reglas tampoco constituye una medida de importancia causal.

## Alcance de PRIDE en este prototipo

La integración actual aprende reglas estáticas entre entradas discretizadas y una salida discreta. No representa todavía transiciones temporales entre visitas de un mismo paciente, por lo que no debe interpretarse como un modelo de evolución clínica longitudinal.

`pylfit`, la dependencia que proporciona PRIDE, se distribuye bajo licencia GPL-3.0. Consulta esta implicación con la dirección del TFG antes de distribuir o desplegar el proyecto fuera del ámbito académico.

## Estructura

```text
app.py                 # Punto de entrada y navegación
views/                 # Pantallas de la interfaz
src/                   # Lógica de datos, PRIDE, métricas y estado
test_core.py           # Pruebas automatizadas
```

## Comprobar la lógica

Con el entorno virtual activado:

```powershell
python -m unittest -v test_core.py
```
