"""Validación independiente de la configuración de un análisis."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class AnalysisValidation:
    input_variables: tuple[str, ...]
    output_variable: str | None
    errors: tuple[str, ...]
    warnings: tuple[str, ...]

    @property
    def is_ready(self) -> bool:
        return not self.errors


def validate_analysis_configuration(
    dataframe: pd.DataFrame, roles: dict[str, str]
) -> AnalysisValidation:
    """Comprueba roles y comunica ausentes sin alterar ni descartar filas."""
    existing_roles = {column: role for column, role in roles.items() if column in dataframe.columns}
    inputs = tuple(column for column, role in existing_roles.items() if role == "Entrada")
    outputs = tuple(column for column, role in existing_roles.items() if role == "Salida")

    errors: list[str] = []
    warnings: list[str] = []

    if len(outputs) == 0:
        errors.append("Selecciona una única variable de salida.")
    elif len(outputs) > 1:
        errors.append("Hay más de una variable de salida; deja solo una para este análisis.")

    if not inputs:
        errors.append("Selecciona al menos una variable de entrada.")

    for column in (*inputs, *outputs):
        missing = int(dataframe[column].isna().sum())
        if missing:
            percentage = missing / len(dataframe) * 100 if len(dataframe) else 0
            warnings.append(
                f"«{column}» contiene {missing} valor(es) ausente(s) ({percentage:.1f}%). "
                "Aún no se eliminarán ni imputarán automáticamente."
            )

    return AnalysisValidation(
        input_variables=inputs,
        output_variable=outputs[0] if len(outputs) == 1 else None,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )
