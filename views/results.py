"""Pantalla de resultados simulados."""

import pandas as pd
import streamlit as st

from src.rule_analysis import (
    comparison_table,
    filter_rules,
    graphviz_dot,
    relationship_counts,
    rules_for_relationship,
    rules_to_matrix,
    similar_rules,
    sort_rules,
    variable_indicators,
)


def render() -> None:
    st.title("5. Resultados")
    result = st.session_state.analysis_result
    if result is None:
        st.info("Aún no se ha ejecutado PRIDE. Se muestran reglas simuladas de ejemplo.")
        _render_mock_results()
        return

    filtered_rules = _render_filters(result)
    if not filtered_rules:
        st.warning("Ninguna regla cumple los filtros actuales. Ajusta los filtros de visualización.")
        return

    tabs = st.tabs(["Resumen", "Matriz de reglas", "Detalle", "Comparar", "Relaciones"])
    with tabs[0]:
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Observaciones usadas", result.observations)
        col2.metric("Reglas PRIDE", len(result.rules))
        col3.metric("Salida", result.target_column)
        col4.metric("Reglas visibles", len(filtered_rules))
        st.caption(
            "Las métricas indican filas cubiertas por cada antecedente y casos compatibles "
            "con la salida de la regla en el dataset procesado."
        )
        st.subheader("Indicadores descriptivos por variable")
        st.caption(
            "No representan importancia causal: describen presencia y cobertura de las reglas visibles."
        )
        st.dataframe(
            variable_indicators(filtered_rules, result.feature_columns),
            use_container_width=True,
            hide_index=True,
        )
    with tabs[1]:
        _render_rule_matrix(filtered_rules, result.feature_columns)
    with tabs[2]:
        _render_rule_detail(filtered_rules)
    with tabs[3]:
        _render_comparison(filtered_rules, result.feature_columns)
    with tabs[4]:
        _render_relationships(filtered_rules, result)


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


def _render_filters(result):
    st.subheader("Filtros de visualización")
    st.caption("Estos filtros no cambian el aprendizaje de PRIDE ni generan reglas nuevas.")
    target_values = sorted({rule.target_value for rule in result.rules})
    max_coverage = max(rule.coverage for rule in result.rules)
    max_conditions = max(rule.conditions_count for rule in result.rules)
    left, middle, right = st.columns(3)
    with left:
        search = st.text_input("Buscar en reglas", placeholder="Ej.: fumador o riesgo alto")
        selected_targets = st.multiselect("Salida", target_values, default=target_values)
    with middle:
        selected_variables = st.multiselect("Variables que deben aparecer", result.feature_columns)
        match_mode = st.radio(
            "Coincidencia de variables",
            ["Al menos una", "Todas"],
            horizontal=True,
        )
    with right:
        min_coverage = st.slider("Cobertura mínima", 0, max_coverage, 0)
        max_selected_conditions = st.slider("Máximo de condiciones", 1, max_conditions, max_conditions)
        sorting = st.selectbox(
            "Ordenar reglas",
            [
                "Cobertura (mayor a menor)",
                "Casos compatibles (mayor a menor)",
                "Complejidad (menos condiciones)",
                "Identificador",
            ],
        )
    filtered = filter_rules(
        result.rules,
        search,
        selected_targets,
        selected_variables,
        match_mode == "Todas",
        min_coverage,
        max_selected_conditions,
    )
    return sort_rules(filtered, sorting)


def _selected_rule(rules, widget_key: str):
    identifiers = [rule.identifier for rule in rules]
    if widget_key in st.session_state and st.session_state[widget_key] not in identifiers:
        del st.session_state[widget_key]
    current = st.session_state.get("selected_rule_id")
    index = identifiers.index(current) if current in identifiers else 0
    selected = st.selectbox("Regla seleccionada", identifiers, index=index, key=widget_key)
    st.session_state.selected_rule_id = selected
    return next(rule for rule in rules if rule.identifier == selected)


def _render_rule_matrix(rules, feature_columns) -> None:
    st.dataframe(rules_to_matrix(rules, feature_columns), use_container_width=True, hide_index=True)
    st.caption("— indica que esa variable no participa en el antecedente de la regla.")
    _selected_rule(rules, "matrix_rule_picker")


def _render_rule_detail(rules) -> None:
    rule = _selected_rule(rules, "detail_rule_picker")
    st.code(rule.text, language=None)
    col1, col2, col3 = st.columns(3)
    col1.metric("Condiciones", rule.conditions_count)
    col2.metric("Filas cubiertas", rule.coverage)
    col3.metric("Casos compatibles", rule.compatible_cases)
    st.caption(
        "La regla describe un patrón aprendido de los datos discretizados; no implica causalidad clínica."
    )
    st.subheader("Reglas con condiciones similares")
    st.dataframe(similar_rules(rule, rules).head(5), use_container_width=True, hide_index=True)


def _render_comparison(rules, feature_columns) -> None:
    if len(rules) < 2:
        st.info("Necesitas al menos dos reglas visibles para compararlas.")
        return
    first = _selected_rule(rules, "comparison_first_rule_picker")
    candidates = [rule.identifier for rule in rules if rule.identifier != first.identifier]
    second_identifier = st.selectbox("Comparar con", candidates, key="comparison_rule_picker")
    second = next(rule for rule in rules if rule.identifier == second_identifier)
    st.dataframe(
        comparison_table(first, second, feature_columns),
        use_container_width=True,
        hide_index=True,
    )
    if first.target_value == second.target_value:
        st.caption("Ambas reglas apuntan a la misma salida; compara qué condiciones comparten o sustituyen.")
    else:
        st.caption("Las reglas tienen salidas distintas; la tabla permite contrastar sus antecedentes.")


def _render_relationships(rules, result) -> None:
    relationships = relationship_counts(rules, result.target_column)
    if relationships.empty:
        st.info("No hay relaciones que visualizar con las reglas visibles.")
        return
    st.caption(
        "El grosor y la etiqueta de cada enlace representan cuántas reglas visibles contienen la relación."
    )
    st.graphviz_chart(graphviz_dot(relationships, result.target_column), use_container_width=True)
    st.subheader("Explorar un enlace")
    labels = [
        f"{row['Origen']} → {row['Destino']} · {row['Tipo']} ({row['Reglas asociadas']} reglas)"
        for _, row in relationships.iterrows()
    ]
    selected_label = st.selectbox("Relación", labels)
    row = relationships.iloc[labels.index(selected_label)]
    related = rules_for_relationship(
        rules,
        row["Origen"],
        row["Destino"],
        row["Tipo"],
        result.target_column,
    )
    st.dataframe(rules_to_matrix(related, result.feature_columns), use_container_width=True, hide_index=True)
