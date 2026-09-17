"""Funciones de discretización independientes de la interfaz Streamlit."""

from __future__ import annotations

from math import isfinite
from typing import Any

import pandas as pd


class DiscretizationError(ValueError):
    """Error de configuración que puede mostrarse al usuario."""


def parse_manual_cuts(raw_cuts: str) -> list[float]:
    """Convierte una lista de cortes separados por comas en valores ordenados."""
    values = [value.strip() for value in raw_cuts.split(",") if value.strip()]
    if not values:
        raise DiscretizationError("Introduce al menos un punto de corte.")

    try:
        cuts = [float(value) for value in values]
    except ValueError as error:
        raise DiscretizationError(
            "Los puntos de corte deben ser números separados por comas. "
            "Usa punto para los decimales."
        ) from error

    if not all(isfinite(cut) for cut in cuts):
        raise DiscretizationError("Los puntos de corte deben ser números finitos.")
    if cuts != sorted(cuts) or len(set(cuts)) != len(cuts):
        raise DiscretizationError(
            "Los puntos de corte deben estar ordenados de menor a mayor y no repetirse."
        )
    return cuts


def _manual_labels(cuts: list[float]) -> list[str]:
    def format_value(value: float) -> str:
        return f"{value:g}"

    labels = [f"< {format_value(cuts[0])}"]
    labels.extend(
        f"{format_value(lower)} – < {format_value(upper)}"
        for lower, upper in zip(cuts, cuts[1:])
    )
    labels.append(f"≥ {format_value(cuts[-1])}")
    return labels


def discretize_series(
    series: pd.Series,
    method: str,
    bins: int | None = None,
    raw_cuts: str | None = None,
) -> tuple[pd.Series, dict[str, Any]]:
    """Discretiza una serie numérica y devuelve la serie y su trazabilidad."""
    if not pd.api.types.is_numeric_dtype(series):
        raise DiscretizationError(f"«{series.name}» no es una variable numérica.")

    non_null = series.dropna()
    if non_null.empty:
        raise DiscretizationError(f"«{series.name}» no contiene valores numéricos válidos.")

    if method in {"quantiles", "equal_width"}:
        if bins is None or not 2 <= int(bins) <= 20:
            raise DiscretizationError("El número de categorías debe estar entre 2 y 20.")
        if non_null.nunique() < 2:
            raise DiscretizationError(
                f"«{series.name}» necesita al menos dos valores distintos para discretizarse."
            )

        try:
            if method == "quantiles":
                result = pd.qcut(series, q=int(bins), duplicates="drop", precision=3)
                method_name = "Cuantiles"
            else:
                result = pd.cut(series, bins=int(bins), include_lowest=True, precision=3)
                method_name = "Intervalos de igual amplitud"
        except ValueError as error:
            raise DiscretizationError(
                f"No se pudo discretizar «{series.name}»: {error}"
            ) from error

        labels = [str(category) for category in result.cat.categories]
        return result.astype("string"), {
            "method": method,
            "method_name": method_name,
            "categories": labels,
            "requested_bins": int(bins),
            "actual_bins": len(labels),
        }

    if method == "manual":
        cuts = parse_manual_cuts(raw_cuts or "")
        labels = _manual_labels(cuts)
        edges = [float("-inf"), *cuts, float("inf")]
        result = pd.cut(series, bins=edges, labels=labels, right=False)
        return result.astype("string"), {
            "method": method,
            "method_name": "Puntos de corte manuales",
            "categories": labels,
            "cuts": cuts,
        }

    raise DiscretizationError("Método de discretización no reconocido.")


def apply_discretizations(
    dataframe: pd.DataFrame, configurations: dict[str, dict[str, Any]]
) -> tuple[pd.DataFrame, dict[str, dict[str, Any]]]:
    """Aplica configuraciones a una copia y conserva el dataframe original intacto."""
    processed = dataframe.copy(deep=True)
    applied: dict[str, dict[str, Any]] = {}

    for column, configuration in configurations.items():
        if column not in processed.columns:
            raise DiscretizationError(f"La variable «{column}» ya no existe en el dataset.")

        discretized, metadata = discretize_series(
            processed[column],
            method=configuration["method"],
            bins=configuration.get("bins"),
            raw_cuts=configuration.get("raw_cuts"),
        )
        processed[column] = discretized
        applied[column] = metadata

    return processed, applied
