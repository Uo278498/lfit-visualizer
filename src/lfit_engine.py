"""Adaptador mínimo entre el dataset procesado y PRIDE de pylfit."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


class LFITEngineError(ValueError):
    """Error comunicable al usuario antes o durante la ejecución de PRIDE."""


@dataclass(frozen=True)
class LearnedRule:
    identifier: str
    antecedents: dict[str, str]
    target_variable: str
    target_value: str
    text: str
    conditions_count: int
    coverage: int
    compatible_cases: int


@dataclass(frozen=True)
class PRIDEResult:
    observations: int
    feature_columns: tuple[str, ...]
    target_column: str
    rules: tuple[LearnedRule, ...]


def _validate_dataset(
    dataframe: pd.DataFrame, feature_columns: list[str], target_column: str
) -> None:
    if not feature_columns:
        raise LFITEngineError("Selecciona al menos una variable de entrada.")
    if target_column not in dataframe.columns:
        raise LFITEngineError("La variable de salida no existe en el dataset procesado.")

    missing_columns = [column for column in [*feature_columns, target_column] if column not in dataframe.columns]
    if missing_columns:
        raise LFITEngineError(f"No se encontraron estas variables: {', '.join(missing_columns)}.")
    if dataframe.empty:
        raise LFITEngineError("No quedan filas para entrenar el modelo.")

    selected = dataframe[[*feature_columns, target_column]]
    if selected.isna().any().any():
        columns = selected.columns[selected.isna().any()].tolist()
        raise LFITEngineError(
            "PRIDE requiere estados definidos. Trata los valores ausentes de: "
            f"{', '.join(columns)}."
        )

    continuous = [
        column
        for column in feature_columns
        if pd.api.types.is_numeric_dtype(dataframe[column])
    ]
    if continuous:
        raise LFITEngineError(
            "Discretiza antes las entradas numéricas: " + ", ".join(continuous) + "."
        )
    if pd.api.types.is_numeric_dtype(dataframe[target_column]):
        raise LFITEngineError(
            "La salida numérica debe discretizarse antes de ejecutar PRIDE."
        )


def run_pride(
    dataframe: pd.DataFrame, feature_columns: list[str], target_column: str
) -> PRIDEResult:
    """Aprende reglas estáticas entradas → salida mediante la API DMVLP de pylfit."""
    _validate_dataset(dataframe, feature_columns, target_column)
    try:
        from pylfit import models, preprocessing
    except ImportError as error:
        raise LFITEngineError(
            "No se encontró pylfit. Instala las dependencias del proyecto antes de ejecutar PRIDE."
        ) from error

    data = [
        ([str(row[column]) for column in feature_columns], [str(row[target_column])])
        for _, row in dataframe.iterrows()
    ]
    dataset = preprocessing.discrete_state_transitions_dataset_from_array(
        data=data,
        feature_names=feature_columns,
        target_names=[target_column],
    )
    model = models.DMVLP(features=dataset.features, targets=dataset.targets)
    model.compile(algorithm="pride")
    model.fit(dataset=dataset)

    rules: list[LearnedRule] = []
    string_dataframe = dataframe[[*feature_columns, target_column]].astype("string")
    for index, rule in enumerate(model.rules, start=1):
        antecedents = {
            column: str(rule.body[column].value)
            for column in feature_columns
            if column in rule.body
        }
        target_value = str(rule.head.value)
        mask = pd.Series(True, index=string_dataframe.index)
        for column, value in antecedents.items():
            mask &= string_dataframe[column] == value
        coverage = int(mask.sum())
        compatible_cases = int((mask & (string_dataframe[target_column] == target_value)).sum())
        condition_text = " AND ".join(f"{column} = {value}" for column, value in antecedents.items())
        text = f"{condition_text} → {target_column} = {target_value}"
        rules.append(
            LearnedRule(
                identifier=f"R{index}",
                antecedents=antecedents,
                target_variable=target_column,
                target_value=target_value,
                text=text,
                conditions_count=len(antecedents),
                coverage=coverage,
                compatible_cases=compatible_cases,
            )
        )

    return PRIDEResult(
        observations=len(data),
        feature_columns=tuple(feature_columns),
        target_column=target_column,
        rules=tuple(rules),
    )
