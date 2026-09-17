"""Pantalla de tratamiento de ausentes y discretización."""

import pandas as pd
import streamlit as st

from src.discretization import DiscretizationError, apply_discretizations
from src.preprocessing import STRATEGY_LABELS, PreprocessingError, apply_missing_value_treatments


METHOD_LABELS = {
    "Cuantiles": "quantiles",
    "Intervalos de igual amplitud": "equal_width",
    "Puntos de corte manuales": "manual",
}


def _render_missing_value_treatment(dataframe: pd.DataFrame, inputs: list[str], output: str | None) -> None:
    analysis_variables = [*inputs, *([output] if output else [])]
    missing_variables = [column for column in analysis_variables if dataframe[column].isna().any()]

    st.subheader("Tratamiento de valores ausentes")
    st.caption(
        "Estas decisiones se aplican a una copia del dataset. La variable de salida "
        "no se imputa para no alterar el resultado observado."
    )
    configurations = {}
    if missing_variables:
        for column in missing_variables:
            role = st.session_state.roles[column]
            is_numeric_input = role == "Entrada" and pd.api.types.is_numeric_dtype(dataframe[column])
            is_categorical_input = role == "Entrada" and not pd.api.types.is_numeric_dtype(dataframe[column])
            strategies = ["keep", "drop_rows"]
            if is_numeric_input:
                strategies.append("median")
            elif is_categorical_input:
                strategies.append("unknown")

            saved = st.session_state.preprocessing_config.get(column, {})
            current = saved.get("strategy", "keep")
            current = current if current in strategies else "keep"
            selected = st.selectbox(
                f"{column} ({role})",
                strategies,
                index=strategies.index(current),
                format_func=lambda strategy: STRATEGY_LABELS[strategy],
                key=f"missing_strategy_{column}",
            )
            configurations[column] = {"strategy": selected}

        if st.button("Aplicar tratamiento de ausentes", type="primary"):
            try:
                preprocessed, summary = apply_missing_value_treatments(dataframe, configurations)
            except PreprocessingError as error:
                st.error(str(error))
            else:
                st.session_state.preprocessed_df = preprocessed
                st.session_state.processed_df = preprocessed.copy(deep=True)
                st.session_state.preprocessing_config = configurations
                st.session_state.preprocessing_summary = summary
                st.session_state.discretization_config = {}
                st.session_state.discretization_summary = {}
                st.session_state.analysis_result = None
                st.success("Tratamiento de valores ausentes aplicado.")
    else:
        st.info("No hay valores ausentes en las variables seleccionadas para el análisis.")

    if st.session_state.preprocessing_summary:
        summary = st.session_state.preprocessing_summary
        st.caption(
            f"Filas: {summary['rows_before']} → {summary['rows_after']} "
            f"(eliminadas: {summary['rows_removed']})."
        )
        st.dataframe(pd.DataFrame(summary["variables"]), use_container_width=True, hide_index=True)


def _render_discretization(original: pd.DataFrame, inputs: list[str]) -> None:
    source = st.session_state.preprocessed_df
    numeric_inputs = [column for column in inputs if pd.api.types.is_numeric_dtype(source[column])]
    st.divider()
    st.subheader("Discretización")
    if not numeric_inputs:
        st.info("No hay variables numéricas de entrada que discretizar. Revisa primero los roles en «2. Variables».")
        return

    st.write("Configura cómo convertir variables continuas en estados discretos.")
    configurations = {}
    for column in numeric_inputs:
        with st.expander(column, expanded=True):
            saved = st.session_state.discretization_config.get(column, {})
            labels = list(METHOD_LABELS)
            saved_label = next(
                (label for label, value in METHOD_LABELS.items() if value == saved.get("method")), labels[0]
            )
            method_label = st.selectbox(
                "Método", labels, index=labels.index(saved_label), key=f"disc_method_{column}"
            )
            method = METHOD_LABELS[method_label]
            if method == "manual":
                raw_cuts = st.text_input(
                    "Puntos de corte separados por comas",
                    value=saved.get("raw_cuts", ""),
                    placeholder="40, 65",
                    help="Usa punto para los decimales, por ejemplo: 18.5, 25, 30.",
                    key=f"cuts_{column}",
                )
                configurations[column] = {"method": method, "raw_cuts": raw_cuts}
            else:
                bins = st.slider(
                    "Número de categorías", 2, 6, saved.get("bins", 3), key=f"bins_{column}"
                )
                configurations[column] = {"method": method, "bins": bins}

    if st.button("Aplicar discretización"):
        try:
            processed, summary = apply_discretizations(source, configurations)
        except DiscretizationError as error:
            st.error(str(error))
        else:
            st.session_state.processed_df = processed
            st.session_state.discretization_config = configurations
            st.session_state.discretization_summary = summary
            st.session_state.analysis_result = None
            st.success("Discretización aplicada al dataset procesado.")

    if not st.session_state.discretization_summary:
        return

    st.subheader("Vista previa antes y después")
    preview_columns = st.multiselect(
        "Variables que comparar",
        numeric_inputs,
        default=[column for column in numeric_inputs if column in st.session_state.discretization_summary],
    )
    if preview_columns:
        preview = pd.DataFrame(index=st.session_state.processed_df.index)
        for column in preview_columns:
            preview[f"{column} (original)"] = original[column].reindex(preview.index)
            preview[f"{column} (discretizada)"] = st.session_state.processed_df[column]
        st.dataframe(preview.head(20), use_container_width=True)

    st.subheader("Resumen de categorías")
    rows = [
        {
            "Variable": column,
            "Método": metadata["method_name"],
            "Categorías": " | ".join(metadata["categories"]),
        }
        for column, metadata in st.session_state.discretization_summary.items()
    ]
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


def render() -> None:
    st.title("3. Preprocesamiento y discretización")
    dataframe = st.session_state.df
    if dataframe is None:
        st.warning("Primero carga un dataset.")
        return

    inputs = [column for column, role in st.session_state.roles.items() if role == "Entrada" and column in dataframe.columns]
    _render_missing_value_treatment(dataframe, inputs, st.session_state.output_var)
    _render_discretization(dataframe, inputs)
