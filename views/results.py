"""Pantalla de resultados simulados."""

import pandas as pd
import streamlit as st


def render() -> None:
    st.title("5. Resultados")
    result = st.session_state.analysis_result
    if result is None:
        st.info("Aún no se ha ejecutado PRIDE. Se muestran reglas simuladas de ejemplo.")
        _render_mock_results()
        return

    tabs = st.tabs(["Resumen", "Matriz de reglas", "Detalle"])
    with tabs[0]:
        col1, col2, col3 = st.columns(3)
        col1.metric("Observaciones usadas", result.observations)
        col2.metric("Reglas PRIDE", len(result.rules))
        col3.metric("Salida", result.target_column)
        st.caption(
            "Las métricas indican filas cubiertas por cada antecedente y casos compatibles "
            "con la salida de la regla en el dataset procesado."
        )
    with tabs[1]:
        _render_rule_matrix(result)
    with tabs[2]:
        _render_rule_detail(result)


def _render_mock_results() -> None:
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


def _render_rule_matrix(result) -> None:
    target_values = sorted({rule.target_value for rule in result.rules})
    selected_values = st.multiselect("Filtrar por salida", target_values, default=target_values)
    rows = []
    for rule in result.rules:
        if rule.target_value not in selected_values:
            continue
        row = {"Regla": rule.identifier}
        row.update({column: rule.antecedents.get(column, "—") for column in result.feature_columns})
        row.update(
            {
                "Salida": f"{rule.target_variable} = {rule.target_value}",
                "Condiciones": rule.conditions_count,
                "Cobertura": rule.coverage,
                "Casos compatibles": rule.compatible_cases,
            }
        )
        rows.append(row)
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


def _render_rule_detail(result) -> None:
    identifiers = [rule.identifier for rule in result.rules]
    if not identifiers:
        st.warning("PRIDE no generó reglas para esta configuración.")
        return
    selected = st.selectbox("Selecciona una regla", identifiers)
    rule = next(rule for rule in result.rules if rule.identifier == selected)
    st.code(rule.text, language=None)
    col1, col2, col3 = st.columns(3)
    col1.metric("Condiciones", rule.conditions_count)
    col2.metric("Filas cubiertas", rule.coverage)
    col3.metric("Casos compatibles", rule.compatible_cases)
    st.caption(
        "La regla describe un patrón aprendido de los datos discretizados; no implica causalidad clínica."
    )
