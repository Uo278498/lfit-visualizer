"""Pantalla de descarga de los artefactos disponibles."""

import pandas as pd
import streamlit as st


def render() -> None:
    st.title("6. Exportación")
    result = st.session_state.analysis_result
    if result is None:
        rules = pd.DataFrame(st.session_state.mock_rules)
        rules_filename = "reglas_simuladas.csv"
    else:
        rules = pd.DataFrame(
            [
                {
                    "Regla": rule.identifier,
                    "Antecedente": " AND ".join(
                        f"{column} = {value}" for column, value in rule.antecedents.items()
                    ),
                    "Salida": f"{rule.target_variable} = {rule.target_value}",
                    "Condiciones": rule.conditions_count,
                    "Cobertura": rule.coverage,
                    "Casos compatibles": rule.compatible_cases,
                }
                for rule in result.rules
            ]
        )
        rules_filename = "reglas_pride.csv"
    st.download_button(
        "Descargar reglas (CSV)",
        rules.to_csv(index=False).encode("utf-8"),
        rules_filename,
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
