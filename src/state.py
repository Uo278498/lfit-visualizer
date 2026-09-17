"""Estado de sesión y reinicios controlados del flujo de análisis."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

import pandas as pd


DEFAULT_RULES = [
    {"Regla": "R1", "Edad": "mayor", "Tensión": "alta", "Fumador": "—", "Colesterol": "alto", "Salida": "Diagnóstico = alto"},
    {"Regla": "R2", "Edad": "adulto", "Tensión": "alta", "Fumador": "sí", "Colesterol": "—", "Salida": "Diagnóstico = alto"},
    {"Regla": "R3", "Edad": "joven", "Tensión": "normal", "Fumador": "no", "Colesterol": "normal", "Salida": "Diagnóstico = bajo"},
]

DEFAULT_SESSION_VALUES = {
    "df": None,
    "preprocessed_df": None,
    "processed_df": None,
    "roles": {},
    "output_var": None,
    "discretization_config": {},
    "discretization_summary": {},
    "preprocessing_config": {},
    "preprocessing_summary": {},
    "dataset_signature": None,
    "dataset_load_info": None,
    "analysis_result": None,
    "mock_rules": DEFAULT_RULES,
}

WIDGET_PREFIXES = ("role_", "disc_method_", "cuts_", "bins_", "missing_strategy_")


def initialize_session_state(session_state: Any) -> None:
    """Inicializa las claves de Streamlit sin sobrescribir una sesión en curso."""
    for key, value in DEFAULT_SESSION_VALUES.items():
        if key not in session_state:
            session_state[key] = deepcopy(value)

    if session_state.df is not None and session_state.preprocessed_df is None:
        session_state.preprocessed_df = session_state.df.copy(deep=True)
        session_state.processed_df = session_state.df.copy(deep=True)


def _clear_widget_state(session_state: Any) -> None:
    for key in list(session_state):
        if key.startswith(WIDGET_PREFIXES):
            del session_state[key]


def reset_for_dataset(session_state: Any, dataframe: pd.DataFrame, signature: tuple[Any, ...]) -> None:
    """Reinicia decisiones que dejarían de ser válidas al cambiar el CSV."""
    session_state.df = dataframe
    session_state.preprocessed_df = dataframe.copy(deep=True)
    session_state.processed_df = dataframe.copy(deep=True)
    session_state.roles = {}
    session_state.output_var = None
    session_state.discretization_config = {}
    session_state.discretization_summary = {}
    session_state.preprocessing_config = {}
    session_state.preprocessing_summary = {}
    session_state.dataset_signature = signature
    session_state.analysis_result = None
    _clear_widget_state(session_state)


def reset_after_role_change(session_state: Any, dataframe: pd.DataFrame) -> None:
    """Invalida transformaciones calculadas con una selección de variables anterior."""
    session_state.preprocessed_df = dataframe.copy(deep=True)
    session_state.processed_df = dataframe.copy(deep=True)
    session_state.discretization_config = {}
    session_state.discretization_summary = {}
    session_state.preprocessing_config = {}
    session_state.preprocessing_summary = {}
    session_state.analysis_result = None
