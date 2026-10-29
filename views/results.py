"""Pantalla de exploración, métricas y trazabilidad de las reglas aprendidas."""

import pandas as pd
import streamlit as st

from src.rule_analysis import (
    comparison_table,
    descriptive_findings,
    filter_rules,
    format_percentage,
    graphviz_dot,
    relationship_counts,
    rules_for_relationship,
    rules_to_matrix,
    similar_rules,
    sort_rules,
    variable_indicators,
)
from src.theory_map import filter_rules_by_complexity, render_theory_map


def render() -> None:
    st.title("5. Resultados")
    result = st.session_state.analysis_result
    if result is None:
        st.info("Aún no se ha ejecutado PRIDE. Se muestran reglas simuladas de ejemplo.")
        _render_mock_results()
        return
    if not hasattr(result, "trace"):
        st.warning(
            "Este resultado se generó con una versión anterior. Vuelve a ejecutar PRIDE "
            "desde «4. Configuración y ejecución» para calcular métricas y trazabilidad."
        )
        return
    if not result.rules:
        st.warning("PRIDE no devolvió reglas para esta configuración. Revisa los datos y la discretización.")
        return

    filtered_rules = _render_filters(result)
    if not filtered_rules:
        st.warning("Ninguna regla cumple los filtros actuales. Ajusta los filtros de visualización.")
        return
    active_rule = _render_active_rule_selector(filtered_rules)

    tabs = st.tabs(["Resumen", "Mapa de teoría", "Matriz de reglas", "Detalle", "Comparar", "Relaciones"])
    with tabs[0]:
        _render_summary(result, filtered_rules)
    with tabs[1]:
        _render_theory_map(result, filtered_rules, active_rule)
    with tabs[2]:
        _render_rule_matrix(filtered_rules, result.feature_columns, result.observations, active_rule)
    with tabs[3]:
        _render_rule_detail(active_rule, filtered_rules, result.observations)
    with tabs[4]:
        _render_comparison(filtered_rules, result.feature_columns, result.observations, active_rule)
    with tabs[5]:
        _render_relationships(filtered_rules, result)


def _render_summary(result, filtered_rules) -> None:
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Observaciones usadas", result.observations)
    col2.metric("Reglas PRIDE", len(result.rules))
    col3.metric("Salida", result.target_column)
    col4.metric("Reglas visibles", len(filtered_rules))
    st.caption(
        "Las métricas se calculan en el mismo dataset usado para aprender las reglas. "
        "Sirven para explorarlas y documentarlas; no son una validación clínica externa."
    )

    st.subheader("Distribución de la salida")
    distribution = pd.DataFrame(result.target_distribution, columns=["Valor de salida", "Filas"])
    distribution["Frecuencia"] = distribution["Filas"] / result.observations
    distribution["Frecuencia"] = distribution["Frecuencia"].map(format_percentage)
    st.dataframe(distribution, use_container_width=True, hide_index=True)

    st.subheader("Hallazgos descriptivos")
    st.caption("Puntos de partida para revisión clínica; describen asociaciones del dataset, no causalidad.")
    for finding in descriptive_findings(filtered_rules, result.feature_columns):
        st.write(f"• {finding}")

    st.subheader("Indicadores descriptivos por variable")
    st.caption(
        "No representan importancia causal. Ayudan a ver qué variables están más presentes "
        "en la teoría visible y qué cobertura concentran."
    )
    st.dataframe(
        variable_indicators(filtered_rules, result.feature_columns),
        use_container_width=True,
        hide_index=True,
    )

    with st.expander("Cómo interpretar las métricas"):
        st.markdown(
            "- **Cobertura**: filas que cumplen todas las condiciones del antecedente.\n"
            "- **Casos compatibles**: filas cubiertas cuya salida coincide con la regla.\n"
            "- **Consistencia**: casos compatibles / cobertura. Se mide en estos mismos datos.\n"
            "- **Frecuencia de salida**: proporción global de ese valor de salida.\n"
            "- **Lift**: consistencia / frecuencia de salida. Un valor mayor que 1 indica "
            "que el patrón aparece con más frecuencia que ese valor de salida en el conjunto completo."
        )

    with st.expander("Trazabilidad de esta ejecución"):
        trace = result.trace
        trace_rows = pd.DataFrame(
            [
                {"Dato": "Fecha y hora", "Valor": trace.executed_at},
                {"Dato": "Algoritmo", "Valor": trace.algorithm},
                {"Dato": "Versión de pylfit", "Valor": trace.pylfit_version},
                {"Dato": "Filas usadas", "Valor": trace.rows_used},
                {"Dato": "Variables de entrada", "Valor": ", ".join(trace.input_variables)},
                {"Dato": "Variable de salida", "Valor": trace.output_variable},
            ]
        )
        st.dataframe(trace_rows, use_container_width=True, hide_index=True)
        _render_transformation_trace(trace)


def _render_transformation_trace(trace) -> None:
    st.markdown("**Tratamiento de ausentes registrado**")
    if trace.preprocessing_summary:
        summary = trace.preprocessing_summary
        st.write(
            f"Filas: {summary.get('rows_before', '—')} → {summary.get('rows_after', '—')} "
            f"(eliminadas: {summary.get('rows_removed', '—')})."
        )
        variables = summary.get("variables", [])
        if variables:
            st.dataframe(pd.DataFrame(variables), use_container_width=True, hide_index=True)
    else:
        st.write("No se registró un tratamiento de ausentes en esta ejecución.")

    st.markdown("**Discretización registrada**")
    if trace.discretization_summary:
        rows = []
        for variable, metadata in trace.discretization_summary.items():
            rows.append(
                {
                    "Variable": variable,
                    "Método": metadata.get("method_name", metadata.get("method", "—")),
                    "Categorías": " | ".join(metadata.get("categories", [])),
                    "Cortes": ", ".join(str(cut) for cut in metadata.get("cuts", [])) or "—",
                }
            )
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    else:
        st.write("No se discretizaron entradas numéricas en esta ejecución.")


def _render_mock_results() -> None:
    tabs = st.tabs(["Resumen", "Matriz de reglas", "Detalle"])
    rules = st.session_state.mock_rules
    with tabs[0]:
        st.metric("Reglas generadas", len(rules))
        st.write("Aquí mostraremos métricas y trazabilidad cuando se ejecute PRIDE con datos reales.")
    with tabs[1]:
        st.dataframe(pd.DataFrame(rules), use_container_width=True, hide_index=True)
    with tabs[2]:
        names = [rule["Regla"] for rule in rules]
        selected = st.selectbox("Selecciona una regla", names)
        rule = next(rule for rule in rules if rule["Regla"] == selected)
        st.json(rule)


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
        min_consistency = st.slider("Consistencia mínima", 0.0, 1.0, 0.0, 0.05)
        max_selected_conditions = st.slider("Máximo de condiciones", 1, max_conditions, max_conditions)
        sorting = st.selectbox(
            "Ordenar reglas",
            [
                "Cobertura (mayor a menor)",
                "Consistencia (mayor a menor)",
                "Lift (mayor a menor)",
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
        min_consistency,
    )
    return sort_rules(filtered, sorting)


def _render_active_rule_selector(rules):
    identifiers = [rule.identifier for rule in rules]
    if st.session_state.get("active_rule_id") not in identifiers:
        st.session_state.active_rule_id = identifiers[0]
    st.selectbox(
        "Regla activa para Mapa, Detalle y Comparar",
        identifiers,
        key="active_rule_id",
        help="La regla elegida queda resaltada en el mapa y se reutiliza en las vistas de detalle y comparación.",
    )
    selected = st.session_state.active_rule_id
    return next(rule for rule in rules if rule.identifier == selected)


def _render_theory_map(result, filtered_rules, active_rule) -> None:
    st.subheader("Mapa interactivo de teoría")
    st.caption(
        "El mapa mantiene cada antecedente conjunto como una regla propia: las condiciones "
        "no se interpretan como influencias independientes."
    )
    target_values = sorted({rule.target_value for rule in filtered_rules})
    left, right = st.columns(2)
    with left:
        target_value = st.selectbox(
            f"Valor de {result.target_column} que representar",
            target_values,
            key="theory_map_target_value",
        )
    with right:
        layer = st.selectbox(
            "Capa de complejidad del antecedente",
            ["Todas", "1 condición", "2 condiciones", "3 condiciones", "4 o más condiciones"],
            key="theory_map_complexity",
            help="Permite examinar reglas simples, pares, tríos o reglas más complejas.",
        )

    target_rules = [rule for rule in filtered_rules if rule.target_value == target_value]
    candidate_rules = filter_rules_by_complexity(target_rules, layer)

    filter_left, filter_middle, filter_right = st.columns(3)
    with filter_left:
        map_search = st.text_input(
            "Buscar dentro del mapa",
            placeholder="Ej.: fumador o R7",
            key="theory_map_search",
        ).strip().casefold()
    with filter_middle:
        map_variables = st.multiselect(
            "Variables del antecedente",
            result.feature_columns,
            key="theory_map_variables",
        )
    with filter_right:
        match_all = st.radio(
            "Coincidencia de variables",
            ["Al menos una", "Todas"],
            horizontal=True,
            key="theory_map_variable_match",
        ) == "Todas"

    if map_search:
        candidate_rules = [
            rule
            for rule in candidate_rules
            if map_search in rule.identifier.casefold() or map_search in rule.text.casefold()
        ]
    if map_variables:
        expected = set(map_variables)
        candidate_rules = [
            rule
            for rule in candidate_rules
            if (expected.issubset(rule.antecedents) if match_all else bool(expected & set(rule.antecedents)))
        ]
    if not candidate_rules:
        st.info("No hay reglas visibles para esa salida y capa. Ajusta los filtros o la complejidad.")
        return

    candidate_rules = sorted(candidate_rules, key=lambda rule: (-rule.coverage, rule.identifier))
    visible_limit = st.slider(
        "Máximo de reglas a dibujar",
        1,
        len(candidate_rules),
        min(40, len(candidate_rules)),
        key="theory_map_rule_limit",
        help="En teorías grandes se dibujan primero las reglas de mayor cobertura; aumenta el límite si lo necesitas.",
    )
    map_rules = candidate_rules[:visible_limit]

    metrics = st.columns(3)
    metrics[0].metric("Reglas en el mapa", len(map_rules))
    maximum_coverage = max(rule.coverage for rule in map_rules)
    metrics[1].metric("Cobertura máxima", f"{maximum_coverage} · {format_percentage(maximum_coverage / result.observations)}")
    metrics[2].metric("Condiciones distintas", len({item for rule in map_rules for item in rule.antecedents.items()}))
    selected_rule_id = render_theory_map(
        map_rules,
        result.target_column,
        target_value,
        observations=result.observations,
        active_rule_id=active_rule.identifier if active_rule in map_rules else None,
        key="theory_map_component",
    )
    if selected_rule_id and selected_rule_id != active_rule.identifier:
        st.session_state.active_rule_id = selected_rule_id
        st.rerun()
    st.caption(
        "Pasa el ratón por un nodo para una vista rápida. Haz clic en una condición, regla o salida "
        "para fijar sus métricas y metadatos en el panel derecho. Usa la rueda para zoom y arrastra "
        "el fondo para desplazarte; doble clic reinicia la vista. La regla activa seleccionada arriba "
        "queda resaltada también en Detalle y Comparar."
    )
    with st.expander("Reglas incluidas en el mapa"):
        st.dataframe(
            rules_to_matrix(map_rules, result.feature_columns, result.observations),
            use_container_width=True,
            hide_index=True,
        )


def _render_rule_matrix(rules, feature_columns, observations, active_rule) -> None:
    st.dataframe(
        rules_to_matrix(rules, feature_columns, observations), use_container_width=True, hide_index=True
    )
    st.caption("— indica que esa variable no participa en el antecedente de la regla.")
    st.caption(f"Regla activa: {active_rule.identifier}. Puedes cambiarla en el selector situado sobre las pestañas.")


def _render_rule_detail(rule, visible_rules, observations) -> None:
    st.code(rule.text, language=None)
    first_row = st.columns(3)
    first_row[0].metric("Filas cubiertas", rule.coverage)
    first_row[1].metric("Cobertura", format_percentage(rule.coverage / observations))
    first_row[2].metric("Casos compatibles", rule.compatible_cases)
    second_row = st.columns(3)
    second_row[0].metric("Condiciones", rule.conditions_count)
    second_row[1].metric("Consistencia", format_percentage(rule.data_consistency))
    second_row[2].metric("Lift", f"{rule.lift:.2f}" if rule.lift is not None else "—")
    st.caption(
        "La consistencia y el lift se calculan sobre el dataset de aprendizaje. "
        "La regla describe una asociación en datos discretizados; no implica causalidad clínica."
    )
    st.subheader("Reglas con condiciones similares")
    st.dataframe(similar_rules(rule, visible_rules).head(5), use_container_width=True, hide_index=True)


def _render_comparison(rules, feature_columns, observations, active_rule) -> None:
    if len(rules) < 2:
        st.info("Necesitas al menos dos reglas visibles para compararlas.")
        return
    first = active_rule
    candidates = [rule.identifier for rule in rules if rule.identifier != first.identifier]
    second_identifier = st.selectbox("Comparar con", candidates, key="comparison_rule_picker")
    second = next(rule for rule in rules if rule.identifier == second_identifier)
    st.dataframe(
        comparison_table(first, second, feature_columns),
        use_container_width=True,
        hide_index=True,
    )
    metrics = pd.DataFrame(
        {
            "Métrica": ["Cobertura", "Cobertura (%)", "Consistencia", "Lift", "Condiciones"],
            first.identifier: [
                first.coverage,
                format_percentage(first.coverage / observations),
                format_percentage(first.data_consistency),
                f"{first.lift:.2f}" if first.lift is not None else "—",
                first.conditions_count,
            ],
            second.identifier: [
                second.coverage,
                format_percentage(second.coverage / observations),
                format_percentage(second.data_consistency),
                f"{second.lift:.2f}" if second.lift is not None else "—",
                second.conditions_count,
            ],
        }
    )
    st.dataframe(metrics, use_container_width=True, hide_index=True)
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
    st.dataframe(
        rules_to_matrix(related, result.feature_columns, result.observations),
        use_container_width=True,
        hide_index=True,
    )
