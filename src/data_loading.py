"""Carga y perfilado básico de datasets CSV."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from io import StringIO

import pandas as pd


class DatasetLoadError(ValueError):
    """Error de carga que puede comunicarse de forma clara en la interfaz."""


@dataclass(frozen=True)
class CSVLoadInfo:
    encoding: str
    separator: str

    @property
    def separator_label(self) -> str:
        return {",": "coma", ";": "punto y coma", "\t": "tabulador", "|": "barra vertical"}.get(
            self.separator, repr(self.separator)
        )


def _detect_separator(text: str) -> str:
    sample = text[:8192]
    try:
        return csv.Sniffer().sniff(sample, delimiters=",;\t|").delimiter
    except csv.Error:
        counts = {separator: sample.count(separator) for separator in (",", ";", "\t", "|")}
        return max(counts, key=counts.get) if any(counts.values()) else ","


def load_csv_bytes(content: bytes) -> tuple[pd.DataFrame, CSVLoadInfo]:
    """Lee un CSV común detectando codificación y separador sin modificar sus datos."""
    if not content:
        raise DatasetLoadError("El archivo está vacío.")

    decoding_errors: list[str] = []
    for encoding in ("utf-8-sig", "cp1252"):
        try:
            text = content.decode(encoding)
        except UnicodeDecodeError:
            decoding_errors.append(encoding)
            continue

        separator = _detect_separator(text)
        try:
            dataframe = pd.read_csv(StringIO(text), sep=separator)
        except pd.errors.ParserError as error:
            raise DatasetLoadError(f"No se pudo interpretar el CSV: {error}") from error

        if dataframe.columns.empty:
            raise DatasetLoadError("El archivo no contiene columnas reconocibles.")
        return dataframe, CSVLoadInfo(encoding=encoding, separator=separator)

    attempted = ", ".join(decoding_errors)
    raise DatasetLoadError(
        "No se pudo leer la codificación del archivo. "
        f"Se probaron: {attempted or 'UTF-8 y Windows-1252'}."
    )


def build_variable_summary(dataframe: pd.DataFrame) -> pd.DataFrame:
    """Devuelve indicadores comprensibles de calidad para cada columna."""
    rows = []
    for column in dataframe.columns:
        series = dataframe[column]
        missing = int(series.isna().sum())
        missing_pct = (missing / len(series) * 100) if len(series) else 0.0
        if len(series) == 0:
            status = "Sin filas"
        elif missing == len(series):
            status = "Sin datos"
        elif missing:
            status = "Con ausentes"
        else:
            status = "Completa"
        rows.append(
            {
                "Variable": column,
                "Tipo": str(series.dtype),
                "Únicos": int(series.nunique(dropna=True)),
                "Ausentes": missing,
                "% ausentes": round(missing_pct, 1),
                "Estado": status,
            }
        )
    return pd.DataFrame(rows)
