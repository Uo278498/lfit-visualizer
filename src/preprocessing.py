"""Transformaciones explícitas y trazables previas a la discretización."""

from __future__ import annotations

from typing import Any

import pandas as pd


class PreprocessingError(ValueError):
    """Error de configuración del preprocesamiento."""


STRATEGY_LABELS = {
    "keep": "Conservar valores ausentes",
    "drop_rows": "Eliminar filas con ausentes",
    "median": "Imputar con la mediana",
    "unknown": "Asignar la categoría «Desconocido»",
}


def apply_missing_value_treatments(
    dataframe: pd.DataFrame, configurations: dict[str, dict[str, Any]]
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Aplica decisiones de ausentes sobre una copia del dataframe original."""
    processed = dataframe.copy(deep=True)
    rows_before = len(processed)

    for column, configuration in configurations.items():
        if column not in processed.columns:
            raise PreprocessingError(f"La variable «{column}» ya no existe en el dataset.")
        if configuration.get("strategy") not in STRATEGY_LABELS:
            raise PreprocessingError(f"La estrategia de «{column}» no es válida.")

    drop_columns = [
        column
        for column, configuration in configurations.items()
        if configuration["strategy"] == "drop_rows"
    ]
    if drop_columns:
        processed = processed.dropna(subset=drop_columns).copy()

    applied: list[dict[str, Any]] = []
    for column, configuration in configurations.items():
        strategy = configuration["strategy"]
        missing_before = int(dataframe[column].isna().sum())
        detail = ""

        if strategy == "median":
            if not pd.api.types.is_numeric_dtype(processed[column]):
                raise PreprocessingError(
                    f"«{column}» no es numérica y no puede imputarse con la mediana."
                )
            median = processed[column].median(skipna=True)
            if pd.isna(median):
                raise PreprocessingError(
                    f"«{column}» no tiene valores válidos para calcular una mediana."
                )
            processed[column] = processed[column].fillna(median)
            detail = f"Mediana aplicada: {median:g}"
        elif strategy == "unknown":
            processed[column] = processed[column].astype("string").fillna("Desconocido")
            detail = "Etiqueta aplicada: Desconocido"

        applied.append(
            {
                "Variable": column,
                "Estrategia": STRATEGY_LABELS[strategy],
                "Ausentes originales": missing_before,
                "Detalle": detail or "Sin modificación de valores",
            }
        )

    summary = {
        "rows_before": rows_before,
        "rows_after": len(processed),
        "rows_removed": rows_before - len(processed),
        "variables": applied,
    }
    return processed, summary
