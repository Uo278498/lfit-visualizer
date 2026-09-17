"""Pantalla de descarga de los artefactos disponibles."""

import pandas as pd
import streamlit as st


def render() -> None:
    st.title("6. Exportación")
    rules = pd.DataFrame(st.session_state.mock_rules)
    st.download_button(
        "Descargar reglas simuladas (CSV)",
        rules.to_csv(index=False).encode("utf-8"),
        "reglas_lfit.csv",
        "text/csv",
    )
    if st.session_state.df is not None:
        processed = (
            st.session_state.processed_df
            if st.session_state.processed_df is not None
            else st.session_state.df
        )
        st.download_button(
            "Descargar dataset procesado (CSV)",
            processed.to_csv(index=False).encode("utf-8"),
            "dataset_procesado.csv",
            "text/csv",
        )
    st.info("Más adelante añadiremos la configuración del análisis y un informe resumido.")
