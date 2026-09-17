"""Pantalla de carga y exploración del CSV."""

from hashlib import sha256

import streamlit as st

from src.data_loading import DatasetLoadError, build_variable_summary, load_csv_bytes
from src.state import reset_for_dataset


def render() -> None:
    st.title("1. Carga y exploración de datos")
    st.write("Carga un CSV para revisar su estructura antes de configurar LFIT.")
    uploaded = st.file_uploader("Selecciona un archivo CSV", type=["csv"])
    if uploaded is not None:
        content = uploaded.getvalue()
        try:
            dataframe, load_info = load_csv_bytes(content)
        except DatasetLoadError as error:
            st.error(str(error))
        else:
            signature = (uploaded.name, len(content), sha256(content).hexdigest())
            if st.session_state.dataset_signature != signature:
                reset_for_dataset(st.session_state, dataframe, signature)
            st.session_state.dataset_load_info = load_info

    dataframe = st.session_state.df
    if dataframe is None:
        st.info("Todavía no se ha cargado ningún dataset.")
        return

    load_info = st.session_state.dataset_load_info
    if load_info is not None:
        st.caption(f"Lectura detectada: {load_info.encoding}; separador: {load_info.separator_label}.")

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Filas", len(dataframe))
    col2.metric("Columnas", len(dataframe.columns))
    missing_pct = (dataframe.isna().sum().sum() / dataframe.size * 100) if dataframe.size else 0
    col3.metric("Valores ausentes", f"{missing_pct:.1f}%")
    col4.metric("Columnas numéricas", len(dataframe.select_dtypes(include="number").columns))

    st.subheader("Vista previa")
    st.dataframe(dataframe.head(20), use_container_width=True)
    st.subheader("Resumen de variables")
    st.dataframe(build_variable_summary(dataframe), use_container_width=True, hide_index=True)
