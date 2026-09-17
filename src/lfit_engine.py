"""Adaptador entre el dataset procesado y PRIDE de pylfit."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime, timezone
from importlib.metadata import PackageNotFoundError, version
from typing import Any, Mapping

import pandas as pd


class LFITEngineError(ValueError):
    """Error comunicable al usuario antes o durante la ejecución de PRIDE."""


@dataclass(frozen=True)
class LearnedRule:
    """Regla aprendida junto a métricas descriptivas calculadas en los mismos datos."""

    identifier: str
    antecedents: dict[str, str]
    target_variable: str
    target_value: str
    text: str
    conditions_count: int
    coverage: int
    compatible_cases: int
    data_consistency: float = 0.0
    target_prevalence: float = 0.0
    lift: float | None = None


@dataclass(frozen=True)
class ExecutionTrace:
    """Contexto reproducible de una ejecución, sin guardar datos clínicos."""

    executed_at: str
    rows_used: int
    input_variables: tuple[str, ...]
    output_variable: str
    preprocessing_summary: dict[str, Any]
    discretization_summary: dict[str, dict[str, Any]]
    algorithm: str
    pylfit_version: str


@dataclass(frozen=True)
class PRIDEResult:
    observations: int
    feature_columns: tuple[str, ...]
    target_column: str
    rules: tuple[LearnedRule, ...]
    target_distribution: tuple[tuple[str, int], ...]
    trace: ExecutionTrace


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


def _pylfit_version() -> str:
    try:
        return version("pylfit")
    except PackageNotFoundError:
        return "No disponible"


def run_pride(
    dataframe: pd.DataFrame,
    feature_columns: list[str],
    target_column: str,
    preprocessing_summary: Mapping[str, Any] | None = None,
    discretization_summary: Mapping[str, Mapping[str, Any]] | None = None,
) -> PRIDEResult:
    """Aprende reglas estáticas entradas → salida mediante la API DMVLP de pylfit.

    Las métricas se calculan sobre el mismo dataset usado para aprender; sirven para
    explorar y documentar la teoría, no para validar rendimiento clínico externo.
    """
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
    target_counts = string_dataframe[target_column].value_counts(dropna=False)
    observations = len(string_dataframe)
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
        data_consistency = compatible_cases / coverage if coverage else 0.0
        target_prevalence = int(target_counts.get(target_value, 0)) / observations
        lift = data_consistency / target_prevalence if target_prevalence else None
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
                data_consistency=data_consistency,
                target_prevalence=target_prevalence,
                lift=lift,
            )
        )

    trace = ExecutionTrace(
        executed_at=datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        rows_used=observations,
        input_variables=tuple(feature_columns),
        output_variable=target_column,
        preprocessing_summary=deepcopy(dict(preprocessing_summary or {})),
        discretization_summary=deepcopy(dict(discretization_summary or {})),
        algorithm="PRIDE (pylfit)",
        pylfit_version=_pylfit_version(),
    )
    return PRIDEResult(
        observations=observations,
        feature_columns=tuple(feature_columns),
        target_column=target_column,
        rules=tuple(rules),
        target_distribution=tuple((str(value), int(count)) for value, count in target_counts.items()),
        trace=trace,
    )
