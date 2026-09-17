"""Pantalla de selección de roles de variables."""

import pandas as pd
import streamlit as st

from src.state import reset_after_role_change
from src.validation import validate_analysis_configuration


def render() -> None:
    st.title("2. Selección de variables")
    dataframe = st.session_state.df
    if dataframe is None:
        st.warning("Primero carga un dataset en «1. Datos».")
        return

    st.write("Asigna un papel a cada columna. En este prototipo permitimos una única variable de salida.")
    role_options = ["Entrada", "Salida", "Identificador", "Excluir"]
    roles = {}
    for column in dataframe.columns:
        previous = st.session_state.roles.get(column, "Entrada")
        index = role_options.index(previous) if previous in role_options else 0
        roles[column] = st.selectbox(column, role_options, index=index, key=f"role_{column}")

    if roles != st.session_state.roles:
        reset_after_role_change(st.session_state, dataframe)
    st.session_state.roles = roles

    validation = validate_analysis_configuration(dataframe, roles)
    st.session_state.output_var = validation.output_variable
    if validation.output_variable is not None:
        st.success(f"Variable de salida: {validation.output_variable}")
    for error in validation.errors:
        st.error(error)
    for warning in validation.warnings:
        st.warning(warning)

    st.dataframe(
        pd.DataFrame([{"Variable": column, "Rol": role} for column, role in roles.items()]),
        use_container_width=True,
        hide_index=True,
    )
