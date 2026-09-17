import streamlit as st
import pandas as pd

from src.discretization import DiscretizationError, apply_discretizations

st.set_page_config(page_title='LFIT Visualizer', page_icon='🧠', layout='wide')

DEFAULT_RULES = [
    {'Regla':'R1','Edad':'mayor','Tensión':'alta','Fumador':'—','Colesterol':'alto','Salida':'Diagnóstico = alto'},
    {'Regla':'R2','Edad':'adulto','Tensión':'alta','Fumador':'sí','Colesterol':'—','Salida':'Diagnóstico = alto'},
    {'Regla':'R3','Edad':'joven','Tensión':'normal','Fumador':'no','Colesterol':'normal','Salida':'Diagnóstico = bajo'},
]

for key, value in {
    'df': None,
    'processed_df': None,
    'roles': {},
    'output_var': None,
    'discretization_config': {},
    'discretization_summary': {},
    'dataset_signature': None,
    'mock_rules': DEFAULT_RULES,
}.items():
    if key not in st.session_state:
        st.session_state[key] = value

st.sidebar.title('LFIT Visualizer')
section = st.sidebar.radio('Flujo de trabajo', [
    '1. Datos','2. Variables','3. Discretizar','4. Configurar','5. Resultados','6. Exportar'
])
st.sidebar.caption('Prototipo funcional · LFIT todavía simulado')

if section == '1. Datos':
    st.title('1. Carga y exploración de datos')
    st.write('Carga un CSV para revisar su estructura antes de configurar LFIT.')
    uploaded = st.file_uploader('Selecciona un archivo CSV', type=['csv'])
    if uploaded is not None:
        content = uploaded.getvalue()
        signature = (uploaded.name, len(content), hash(content))
        try:
            df = pd.read_csv(pd.io.common.BytesIO(content))
        except Exception:
            df = pd.read_csv(pd.io.common.BytesIO(content), sep=';')
        if st.session_state.dataset_signature != signature:
            st.session_state.df = df
            st.session_state.processed_df = df.copy(deep=True)
            st.session_state.roles = {}
            st.session_state.output_var = None
            st.session_state.discretization_config = {}
            st.session_state.discretization_summary = {}
            st.session_state.dataset_signature = signature
            for state_key in list(st.session_state):
                if state_key.startswith(('role_', 'disc_method_', 'cuts_', 'bins_')):
                    del st.session_state[state_key]

    df = st.session_state.df
    if df is None:
        st.info('Todavía no se ha cargado ningún dataset.')
    else:
        c1,c2,c3,c4 = st.columns(4)
        c1.metric('Filas', len(df))
        c2.metric('Columnas', len(df.columns))
        missing_pct = (df.isna().sum().sum() / df.size * 100) if df.size else 0
        c3.metric('Valores ausentes', f'{missing_pct:.1f}%')
        c4.metric('Columnas numéricas', len(df.select_dtypes(include='number').columns))
        st.subheader('Vista previa')
        st.dataframe(df.head(20), use_container_width=True)
        st.subheader('Resumen de variables')
        summary = pd.DataFrame({
            'Variable': df.columns,
            'Tipo': [str(df[c].dtype) for c in df.columns],
            'Únicos': [df[c].nunique(dropna=True) for c in df.columns],
            'Ausentes': [df[c].isna().sum() for c in df.columns],
        })
        st.dataframe(summary, use_container_width=True, hide_index=True)

elif section == '2. Variables':
    st.title('2. Selección de variables')
    df = st.session_state.df
    if df is None:
        st.warning('Primero carga un dataset en «1. Datos».')
    else:
        st.write('Asigna un papel a cada columna. En este prototipo permitimos una única variable de salida.')
        role_options = ['Entrada','Salida','Identificador','Excluir']
        roles = {}
        for col in df.columns:
            previous = st.session_state.roles.get(col, 'Entrada')
            idx = role_options.index(previous) if previous in role_options else 0
            roles[col] = st.selectbox(col, role_options, index=idx, key=f'role_{col}')
        outputs = [c for c,r in roles.items() if r == 'Salida']
        if len(outputs) > 1:
            st.error('Selecciona únicamente una variable como salida.')
        elif len(outputs) == 0:
            st.info('Debes marcar una columna como «Salida».')
            st.session_state.output_var = None
        else:
            st.session_state.output_var = outputs[0]
            st.success(f'Variable de salida: {outputs[0]}')
        if roles != st.session_state.roles:
            st.session_state.processed_df = df.copy(deep=True)
            st.session_state.discretization_config = {}
            st.session_state.discretization_summary = {}
        st.session_state.roles = roles
        st.dataframe(pd.DataFrame([{'Variable':c,'Rol':r} for c,r in roles.items()]), use_container_width=True, hide_index=True)

elif section == '3. Discretizar':
    st.title('3. Discretización')
    df = st.session_state.df
    if df is None:
        st.warning('Primero carga un dataset.')
    else:
        inputs = [c for c,r in st.session_state.roles.items() if r == 'Entrada' and c in df.columns]
        numeric_inputs = [c for c in inputs if pd.api.types.is_numeric_dtype(df[c])]
        if not numeric_inputs:
            st.info('No hay variables numéricas de entrada que discretizar. Revisa primero los roles en «2. Variables».')
        else:
            st.write('Configura cómo convertir variables continuas en estados discretos. El dataset original no se modifica.')
            method_labels = {
                'Cuantiles': 'quantiles',
                'Intervalos de igual amplitud': 'equal_width',
                'Puntos de corte manuales': 'manual',
            }
            configurations = {}
            for col in numeric_inputs:
                with st.expander(col, expanded=True):
                    saved = st.session_state.discretization_config.get(col, {})
                    labels = list(method_labels)
                    saved_label = next(
                        (label for label, value in method_labels.items() if value == saved.get('method')),
                        labels[0],
                    )
                    method_label = st.selectbox(
                        'Método', labels, index=labels.index(saved_label), key=f'disc_method_{col}'
                    )
                    method = method_labels[method_label]
                    if method == 'manual':
                        raw_cuts = st.text_input(
                            'Puntos de corte separados por comas',
                            value=saved.get('raw_cuts', ''),
                            placeholder='40, 65',
                            help='Usa punto para los decimales, por ejemplo: 18.5, 25, 30.',
                            key=f'cuts_{col}',
                        )
                        configurations[col] = {'method': method, 'raw_cuts': raw_cuts}
                    else:
                        bins = st.slider(
                            'Número de categorías', 2, 6, saved.get('bins', 3), key=f'bins_{col}'
                        )
                        configurations[col] = {'method': method, 'bins': bins}

            if st.button('Aplicar discretización', type='primary'):
                try:
                    processed_df, summary = apply_discretizations(df, configurations)
                except DiscretizationError as error:
                    st.error(str(error))
                else:
                    st.session_state.processed_df = processed_df
                    st.session_state.discretization_config = configurations
                    st.session_state.discretization_summary = summary
                    st.success('Discretización aplicada al dataset procesado.')

            if st.session_state.discretization_summary:
                st.subheader('Vista previa antes y después')
                preview_columns = st.multiselect(
                    'Variables que comparar',
                    numeric_inputs,
                    default=[col for col in numeric_inputs if col in st.session_state.discretization_summary],
                )
                if preview_columns:
                    preview = pd.DataFrame(index=df.index)
                    for col in preview_columns:
                        preview[f'{col} (original)'] = df[col]
                        preview[f'{col} (discretizada)'] = st.session_state.processed_df[col]
                    st.dataframe(preview.head(20), use_container_width=True)

                st.subheader('Resumen de categorías')
                summary_rows = []
                for col, metadata in st.session_state.discretization_summary.items():
                    summary_rows.append({
                        'Variable': col,
                        'Método': metadata['method_name'],
                        'Categorías': ' | '.join(metadata['categories']),
                    })
                st.dataframe(pd.DataFrame(summary_rows), use_container_width=True, hide_index=True)

elif section == '4. Configurar':
    st.title('4. Configuración y ejecución')
    df = st.session_state.df
    if df is None:
        st.warning('Primero carga un dataset.')
    else:
        inputs = [c for c,r in st.session_state.roles.items() if r == 'Entrada']
        output = st.session_state.output_var
        c1,c2 = st.columns(2)
        c1.write('**Entradas**')
        c1.write(', '.join(inputs) if inputs else 'Ninguna')
        c2.write('**Salida**')
        c2.write(output if output else 'No seleccionada')
        if st.session_state.discretization_summary:
            st.write('**Variables discretizadas**')
            st.write(', '.join(st.session_state.discretization_summary))
        else:
            st.info('Aún no se ha aplicado ninguna discretización.')
        st.selectbox('Algoritmo', ['PRIDE (propuesto)','LFIT / otro algoritmo'])
        if st.button('Ejecutar LFIT', type='primary', disabled=(not output or not inputs)):
            st.success('Ejecución simulada completada. La integración real con LFIT/PRIDE llegará después.')

elif section == '5. Resultados':
    st.title('5. Resultados')
    tabs = st.tabs(['Resumen','Matriz de reglas','Detalle'])
    with tabs[0]:
        st.metric('Reglas generadas', len(st.session_state.mock_rules))
        st.write('Aquí mostraremos métricas descriptivas de la teoría aprendida.')
    with tabs[1]:
        st.dataframe(pd.DataFrame(st.session_state.mock_rules), use_container_width=True, hide_index=True)
    with tabs[2]:
        names = [r['Regla'] for r in st.session_state.mock_rules]
        selected = st.selectbox('Selecciona una regla', names)
        rule = next(r for r in st.session_state.mock_rules if r['Regla'] == selected)
        st.json(rule)
        st.caption('Más adelante añadiremos cobertura, frecuencia y casos compatibles con la regla.')

elif section == '6. Exportar':
    st.title('6. Exportación')
    rules_df = pd.DataFrame(st.session_state.mock_rules)
    st.download_button('Descargar reglas simuladas (CSV)', rules_df.to_csv(index=False).encode('utf-8'), 'reglas_lfit.csv', 'text/csv')
    if st.session_state.df is not None:
        processed_df = st.session_state.processed_df if st.session_state.processed_df is not None else st.session_state.df
        st.download_button('Descargar dataset procesado (CSV)', processed_df.to_csv(index=False).encode('utf-8'), 'dataset_procesado.csv', 'text/csv')
    st.info('Más adelante añadiremos la configuración del análisis y un informe resumido.')
