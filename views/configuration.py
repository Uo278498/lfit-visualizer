"""Pantalla de resumen y ejecución simulada."""

import streamlit as st

from src.lfit_engine import LFITEngineError, run_pride
from src.validation import validate_analysis_configuration


def render() -> None:
    st.title("4. Configuración y ejecución")
    dataframe = st.session_state.df
    if dataframe is None:
        st.warning("Primero carga un dataset.")
        return

    analysis_dataframe = st.session_state.preprocessed_df
    validation = validate_analysis_configuration(analysis_dataframe, st.session_state.roles)
    inputs = list(validation.input_variables)
    output = validation.output_variable

    st.subheader("Estado de la configuración")
    if validation.is_ready:
        st.success("La selección de variables es válida para preparar el análisis.")
    else:
        for error in validation.errors:
            st.error(error)
    for warning in validation.warnings:
        st.warning(warning)

    col1, col2 = st.columns(2)
    col1.write("**Entradas**")
    col1.write(", ".join(inputs) if inputs else "Ninguna")
    col2.write("**Salida**")
    col2.write(output if output else "No seleccionada")

    if st.session_state.preprocessing_summary:
        summary = st.session_state.preprocessing_summary
        st.write("**Preprocesamiento aplicado**")
        st.write(f"Filas: {summary['rows_before']} → {summary['rows_after']}")
    if st.session_state.discretization_summary:
        st.write("**Variables discretizadas**")
        st.write(", ".join(st.session_state.discretization_summary))
    else:
        st.info("Aún no se ha aplicado ninguna discretización.")

    st.selectbox("Algoritmo", ["PRIDE (pylfit)"])
    st.caption(
        "Modo experimental: aprende reglas estáticas entre entradas discretizadas y una salida discreta. "
        "No representa una dinámica temporal de pacientes."
    )
    if st.button("Ejecutar LFIT", type="primary", disabled=not validation.is_ready):
        try:
            result = run_pride(st.session_state.processed_df, inputs, output)
        except LFITEngineError as error:
            st.error(str(error))
        else:
            st.session_state.analysis_result = result
            st.success(f"PRIDE completó el aprendizaje: {len(result.rules)} reglas generadas.")
