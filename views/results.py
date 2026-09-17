"""Pantalla de resultados simulados."""

import pandas as pd
import streamlit as st


def render() -> None:
    st.title("5. Resultados")
    tabs = st.tabs(["Resumen", "Matriz de reglas", "Detalle"])
    rules = st.session_state.mock_rules
    with tabs[0]:
        st.metric("Reglas generadas", len(rules))
        st.write("Aquí mostraremos métricas descriptivas de la teoría aprendida.")
    with tabs[1]:
        st.dataframe(pd.DataFrame(rules), use_container_width=True, hide_index=True)
    with tabs[2]:
        names = [rule["Regla"] for rule in rules]
        selected = st.selectbox("Selecciona una regla", names)
        rule = next(rule for rule in rules if rule["Regla"] == selected)
        st.json(rule)
        st.caption("Más adelante añadiremos cobertura, frecuencia y casos compatibles con la regla.")
