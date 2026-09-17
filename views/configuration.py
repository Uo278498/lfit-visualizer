"""Pantalla de resumen y ejecución simulada."""

import streamlit as st

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

    st.selectbox("Algoritmo", ["PRIDE (propuesto)", "LFIT / otro algoritmo"])
    if st.button("Ejecutar LFIT", type="primary", disabled=not validation.is_ready):
        st.success("Ejecución simulada completada. La integración real con LFIT/PRIDE llegará después.")
