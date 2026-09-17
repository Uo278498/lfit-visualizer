import streamlit as st
import pandas as pd
from hashlib import sha256

from src.data_loading import DatasetLoadError, build_variable_summary, load_csv_bytes
from src.discretization import DiscretizationError, apply_discretizations
from src.preprocessing import (
    STRATEGY_LABELS,
    PreprocessingError,
    apply_missing_value_treatments,
)
from src.validation import validate_analysis_configuration

st.set_page_config(page_title='LFIT Visualizer', page_icon='🧠', layout='wide')

DEFAULT_RULES = [
    {'Regla':'R1','Edad':'mayor','Tensión':'alta','Fumador':'—','Colesterol':'alto','Salida':'Diagnóstico = alto'},
    {'Regla':'R2','Edad':'adulto','Tensión':'alta','Fumador':'sí','Colesterol':'—','Salida':'Diagnóstico = alto'},
    {'Regla':'R3','Edad':'joven','Tensión':'normal','Fumador':'no','Colesterol':'normal','Salida':'Diagnóstico = bajo'},
]

for key, value in {
    'df': None,
    'preprocessed_df': None,
    'processed_df': None,
    'roles': {},
    'output_var': None,
    'discretization_config': {},
    'discretization_summary': {},
    'preprocessing_config': {},
    'preprocessing_summary': {},
    'dataset_signature': None,
    'dataset_load_info': None,
    'mock_rules': DEFAULT_RULES,
}.items():
    if key not in st.session_state:
        st.session_state[key] = value

if st.session_state.df is not None and st.session_state.preprocessed_df is None:
    st.session_state.preprocessed_df = st.session_state.df.copy(deep=True)
    st.session_state.processed_df = st.session_state.df.copy(deep=True)

st.sidebar.title('LFIT Visualizer')
section = st.sidebar.radio('Flujo de trabajo', [
    '1. Datos','2. Variables','3. Preprocesar y discretizar','4. Configurar','5. Resultados','6. Exportar'
])
st.sidebar.caption('Prototipo funcional · LFIT todavía simulado')

if section == '1. Datos':
    st.title('1. Carga y exploración de datos')
    st.write('Carga un CSV para revisar su estructura antes de configurar LFIT.')
    uploaded = st.file_uploader('Selecciona un archivo CSV', type=['csv'])
    if uploaded is not None:
        content = uploaded.getvalue()
        try:
            df, load_info = load_csv_bytes(content)
        except DatasetLoadError as error:
            st.error(str(error))
        else:
            signature = (uploaded.name, len(content), sha256(content).hexdigest())
            if st.session_state.dataset_signature != signature:
                st.session_state.df = df
                st.session_state.preprocessed_df = df.copy(deep=True)
                st.session_state.processed_df = df.copy(deep=True)
                st.session_state.roles = {}
                st.session_state.output_var = None
                st.session_state.discretization_config = {}
                st.session_state.discretization_summary = {}
                st.session_state.preprocessing_config = {}
                st.session_state.preprocessing_summary = {}
                st.session_state.dataset_signature = signature
                for state_key in list(st.session_state):
                    if state_key.startswith(('role_', 'disc_method_', 'cuts_', 'bins_', 'missing_strategy_')):
                        del st.session_state[state_key]
            st.session_state.dataset_load_info = load_info

    df = st.session_state.df
    if df is None:
        st.info('Todavía no se ha cargado ningún dataset.')
    else:
        load_info = st.session_state.dataset_load_info
        if load_info is not None:
            st.caption(f'Lectura detectada: {load_info.encoding}; separador: {load_info.separator_label}.')
        c1,c2,c3,c4 = st.columns(4)
        c1.metric('Filas', len(df))
        c2.metric('Columnas', len(df.columns))
        missing_pct = (df.isna().sum().sum() / df.size * 100) if df.size else 0
        c3.metric('Valores ausentes', f'{missing_pct:.1f}%')
        c4.metric('Columnas numéricas', len(df.select_dtypes(include='number').columns))
        st.subheader('Vista previa')
        st.dataframe(df.head(20), use_container_width=True)
        st.subheader('Resumen de variables')
        summary = build_variable_summary(df)
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
        if roles != st.session_state.roles:
            st.session_state.preprocessed_df = df.copy(deep=True)
            st.session_state.processed_df = df.copy(deep=True)
            st.session_state.discretization_config = {}
            st.session_state.discretization_summary = {}
            st.session_state.preprocessing_config = {}
            st.session_state.preprocessing_summary = {}
        st.session_state.roles = roles
        validation = validate_analysis_configuration(df, roles)
        st.session_state.output_var = validation.output_variable
        if validation.output_variable is not None:
            st.success(f'Variable de salida: {validation.output_variable}')
        for error in validation.errors:
            st.error(error)
        for warning in validation.warnings:
            st.warning(warning)
        st.dataframe(pd.DataFrame([{'Variable':c,'Rol':r} for c,r in roles.items()]), use_container_width=True, hide_index=True)

elif section == '3. Preprocesar y discretizar':
    st.title('3. Preprocesamiento y discretización')
    df = st.session_state.df
    if df is None:
        st.warning('Primero carga un dataset.')
    else:
        inputs = [c for c,r in st.session_state.roles.items() if r == 'Entrada' and c in df.columns]
        output = st.session_state.output_var
        analysis_variables = [*inputs, *([output] if output else [])]
        missing_variables = [
            column for column in analysis_variables if df[column].isna().any()
        ]

        st.subheader('Tratamiento de valores ausentes')
        st.caption(
            'Estas decisiones se aplican a una copia del dataset. La variable de salida '
            'no se imputa para no alterar el resultado observado.'
        )
        preprocessing_configurations = {}
        if missing_variables:
            for col in missing_variables:
                role = st.session_state.roles[col]
                is_numeric_input = role == 'Entrada' and pd.api.types.is_numeric_dtype(df[col])
                is_categorical_input = role == 'Entrada' and not pd.api.types.is_numeric_dtype(df[col])
                strategies = ['keep', 'drop_rows']
                if is_numeric_input:
                    strategies.append('median')
                elif is_categorical_input:
                    strategies.append('unknown')

                saved = st.session_state.preprocessing_config.get(col, {})
                current_strategy = saved.get('strategy', 'keep')
                if current_strategy not in strategies:
                    current_strategy = 'keep'
                selected_strategy = st.selectbox(
                    f'{col} ({role})',
                    strategies,
                    index=strategies.index(current_strategy),
                    format_func=lambda strategy: STRATEGY_LABELS[strategy],
                    key=f'missing_strategy_{col}',
                )
                preprocessing_configurations[col] = {'strategy': selected_strategy}

            if st.button('Aplicar tratamiento de ausentes', type='primary'):
                try:
                    preprocessed_df, preprocessing_summary = apply_missing_value_treatments(
                        df, preprocessing_configurations
                    )
                except PreprocessingError as error:
                    st.error(str(error))
                else:
                    st.session_state.preprocessed_df = preprocessed_df
                    st.session_state.processed_df = preprocessed_df.copy(deep=True)
                    st.session_state.preprocessing_config = preprocessing_configurations
                    st.session_state.preprocessing_summary = preprocessing_summary
                    st.session_state.discretization_config = {}
                    st.session_state.discretization_summary = {}
                    st.success('Tratamiento de valores ausentes aplicado.')
        else:
            st.info('No hay valores ausentes en las variables seleccionadas para el análisis.')

        if st.session_state.preprocessing_summary:
            preprocessing_summary = st.session_state.preprocessing_summary
            st.caption(
                f"Filas: {preprocessing_summary['rows_before']} → "
                f"{preprocessing_summary['rows_after']} "
                f"(eliminadas: {preprocessing_summary['rows_removed']})."
            )
            st.dataframe(
                pd.DataFrame(preprocessing_summary['variables']),
                use_container_width=True,
                hide_index=True,
            )

        source_df = st.session_state.preprocessed_df
        numeric_inputs = [c for c in inputs if pd.api.types.is_numeric_dtype(source_df[c])]
        st.divider()
        st.subheader('Discretización')
        if not numeric_inputs:
            st.info('No hay variables numéricas de entrada que discretizar. Revisa primero los roles en «2. Variables».')
        else:
            st.write('Configura cómo convertir variables continuas en estados discretos.')
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

            if st.button('Aplicar discretización'):
                try:
                    processed_df, summary = apply_discretizations(source_df, configurations)
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
                    preview = pd.DataFrame(index=st.session_state.processed_df.index)
                    for col in preview_columns:
                        preview[f'{col} (original)'] = df[col].reindex(preview.index)
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
        analysis_df = st.session_state.preprocessed_df
        validation = validate_analysis_configuration(analysis_df, st.session_state.roles)
        inputs = list(validation.input_variables)
        output = validation.output_variable
        st.subheader('Estado de la configuración')
        if validation.is_ready:
            st.success('La selección de variables es válida para preparar el análisis.')
        else:
            for error in validation.errors:
                st.error(error)
        for warning in validation.warnings:
            st.warning(warning)
        c1,c2 = st.columns(2)
        c1.write('**Entradas**')
        c1.write(', '.join(inputs) if inputs else 'Ninguna')
        c2.write('**Salida**')
        c2.write(output if output else 'No seleccionada')
        if st.session_state.preprocessing_summary:
            preprocessing_summary = st.session_state.preprocessing_summary
            st.write('**Preprocesamiento aplicado**')
            st.write(
                f"Filas: {preprocessing_summary['rows_before']} → "
                f"{preprocessing_summary['rows_after']}"
            )
        if st.session_state.discretization_summary:
            st.write('**Variables discretizadas**')
            st.write(', '.join(st.session_state.discretization_summary))
        else:
            st.info('Aún no se ha aplicado ninguna discretización.')
        st.selectbox('Algoritmo', ['PRIDE (propuesto)','LFIT / otro algoritmo'])
        if st.button('Ejecutar LFIT', type='primary', disabled=not validation.is_ready):
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
