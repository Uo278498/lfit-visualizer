"""Pantalla de descarga de reglas, datos procesados y trazabilidad."""

from dataclasses import asdict
import json

import pandas as pd
import streamlit as st

from src.rule_analysis import descriptive_findings, format_percentage


def _rules_dataframe(result) -> pd.DataFrame:
    return pd.DataFrame(
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
                "Consistencia": format_percentage(rule.data_consistency),
                "Frecuencia de salida": format_percentage(rule.target_prevalence),
                "Lift": round(rule.lift, 3) if rule.lift is not None else "",
            }
            for rule in result.rules
        ]
    )


def _analysis_report(result) -> str:
    trace = result.trace
    distribution = ", ".join(
        f"{value}: {count} ({format_percentage(count / result.observations)})"
        for value, count in result.target_distribution
    )
    findings = descriptive_findings(list(result.rules), result.feature_columns)
    lines = [
        "# Informe de análisis — LFIT Visualizer",
        "",
        "## Alcance",
        "Reglas estáticas aprendidas con PRIDE sobre datos discretizados. Las métricas se calculan "
        "en el mismo conjunto de aprendizaje; no constituyen validación clínica externa ni causalidad.",
        "",
        "## Trazabilidad",
        f"- Fecha y hora: {trace.executed_at}",
        f"- Algoritmo: {trace.algorithm} {trace.pylfit_version}",
        f"- Filas usadas: {trace.rows_used}",
        f"- Entradas: {', '.join(trace.input_variables)}",
        f"- Salida: {trace.output_variable}",
        f"- Distribución de salida: {distribution}",
        "",
        "## Hallazgos descriptivos",
        *(f"- {finding}" for finding in findings),
        "",
        "## Interpretación de métricas",
        "- Cobertura: filas que cumplen el antecedente.",
        "- Consistencia: proporción de filas cubiertas cuya salida coincide con la regla.",
        "- Lift: consistencia dividida por la frecuencia global de la salida.",
    ]
    return "\n".join(lines) + "\n"


def render() -> None:
    st.title("6. Exportación")
    result = st.session_state.analysis_result
    if result is not None and not hasattr(result, "trace"):
        st.warning(
            "Este resultado no incluye métricas ni trazabilidad. Vuelve a ejecutar PRIDE antes de exportar reglas."
        )
        result = None
    if result is None:
        rules = pd.DataFrame(st.session_state.mock_rules)
        rules_filename = "reglas_simuladas.csv"
    else:
        rules = _rules_dataframe(result)
        rules_filename = "reglas_pride.csv"
    st.download_button(
        "Descargar reglas (CSV)",
        rules.to_csv(index=False).encode("utf-8-sig"),
        rules_filename,
        "text/csv",
    )

    if result is not None:
        trace_export = asdict(result.trace)
        trace_export["target_distribution"] = dict(result.target_distribution)
        st.download_button(
            "Descargar trazabilidad (JSON)",
            json.dumps(trace_export, ensure_ascii=False, indent=2).encode("utf-8"),
            "trazabilidad_ejecucion.json",
            "application/json",
        )
        st.download_button(
            "Descargar informe resumido (Markdown)",
            _analysis_report(result).encode("utf-8"),
            "informe_analisis.md",
            "text/markdown",
        )
        st.caption("La trazabilidad guarda configuración y métricas, no las filas clínicas originales.")

    if st.session_state.df is not None:
        processed = (
            st.session_state.processed_df
            if st.session_state.processed_df is not None
            else st.session_state.df
        )
        st.download_button(
            "Descargar dataset procesado (CSV)",
            processed.to_csv(index=False).encode("utf-8-sig"),
            "dataset_procesado.csv",
            "text/csv",
        )
