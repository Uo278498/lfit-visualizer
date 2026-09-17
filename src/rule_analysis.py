"""Transformaciones de reglas para filtros, comparación e indicadores visuales."""

from __future__ import annotations

from itertools import combinations

import pandas as pd

from src.lfit_engine import LearnedRule


def filter_rules(
    rules: tuple[LearnedRule, ...],
    search: str,
    target_values: list[str],
    required_variables: list[str],
    require_all_variables: bool,
    min_coverage: int,
    max_conditions: int,
) -> list[LearnedRule]:
    """Filtra reglas únicamente para su exploración visual."""
    query = search.strip().casefold()
    filtered = []
    for rule in rules:
        has_variables = set(required_variables).issubset(rule.antecedents)
        if required_variables and not require_all_variables:
            has_variables = bool(set(required_variables) & set(rule.antecedents))
        if (
            rule.target_value in target_values
            and has_variables
            and rule.coverage >= min_coverage
            and rule.conditions_count <= max_conditions
            and (not query or query in rule.text.casefold())
        ):
            filtered.append(rule)
    return filtered


def sort_rules(rules: list[LearnedRule], criterion: str) -> list[LearnedRule]:
    options = {
        "Cobertura (mayor a menor)": lambda rule: (-rule.coverage, rule.conditions_count, rule.identifier),
        "Casos compatibles (mayor a menor)": lambda rule: (-rule.compatible_cases, -rule.coverage, rule.identifier),
        "Complejidad (menos condiciones)": lambda rule: (rule.conditions_count, -rule.coverage, rule.identifier),
        "Identificador": lambda rule: rule.identifier,
    }
    return sorted(rules, key=options[criterion])


def rules_to_matrix(rules: list[LearnedRule], feature_columns: tuple[str, ...]) -> pd.DataFrame:
    """Construye una matriz alineada de reglas, con una columna por variable."""
    rows = []
    for rule in rules:
        row = {"Regla": rule.identifier}
        row.update({column: rule.antecedents.get(column, "—") for column in feature_columns})
        row.update(
            {
                "Salida": f"{rule.target_variable} = {rule.target_value}",
                "Condiciones": rule.conditions_count,
                "Cobertura": rule.coverage,
                "Casos compatibles": rule.compatible_cases,
            }
        )
        rows.append(row)
    return pd.DataFrame(rows)


def comparison_table(
    first: LearnedRule, second: LearnedRule, feature_columns: tuple[str, ...]
) -> pd.DataFrame:
    """Explicita qué condiciones comparten o diferencian dos reglas."""
    rows = []
    for column in feature_columns:
        first_value = first.antecedents.get(column, "—")
        second_value = second.antecedents.get(column, "—")
        if first_value == second_value == "—":
            relation = "No participa"
        elif first_value == second_value:
            relation = "Condición compartida"
        elif first_value == "—":
            relation = f"Solo {second.identifier}"
        elif second_value == "—":
            relation = f"Solo {first.identifier}"
        else:
            relation = "Valores distintos"
        rows.append(
            {
                "Variable": column,
                first.identifier: first_value,
                second.identifier: second_value,
                "Relación": relation,
            }
        )
    return pd.DataFrame(rows)


def similar_rules(selected: LearnedRule, rules: list[LearnedRule]) -> pd.DataFrame:
    """Calcula solapamiento de condiciones exactas con las demás reglas visibles."""
    selected_conditions = set(selected.antecedents.items())
    rows = []
    for candidate in rules:
        if candidate.identifier == selected.identifier:
            continue
        candidate_conditions = set(candidate.antecedents.items())
        shared = selected_conditions & candidate_conditions
        union = selected_conditions | candidate_conditions
        score = len(shared) / len(union) if union else 0.0
        rows.append(
            {
                "Regla": candidate.identifier,
                "Condiciones compartidas": len(shared),
                "Solapamiento": round(score, 2),
                "Salida": candidate.target_value,
            }
        )
    return pd.DataFrame(rows).sort_values(
        ["Solapamiento", "Condiciones compartidas"], ascending=False
    ) if rows else pd.DataFrame(columns=["Regla", "Condiciones compartidas", "Solapamiento", "Salida"])


def variable_indicators(rules: list[LearnedRule], feature_columns: tuple[str, ...]) -> pd.DataFrame:
    """Indicadores descriptivos, no una medida de importancia causal."""
    rows = []
    for column in feature_columns:
        related = [rule for rule in rules if column in rule.antecedents]
        rows.append(
            {
                "Variable": column,
                "Reglas en las que aparece": len(related),
                "Cobertura acumulada": sum(rule.coverage for rule in related),
                "Reglas simples (≤ 2 condiciones)": sum(rule.conditions_count <= 2 for rule in related),
                "Salidas distintas asociadas": len({rule.target_value for rule in related}),
            }
        )
    return pd.DataFrame(rows)


def relationship_counts(rules: list[LearnedRule], target_column: str) -> pd.DataFrame:
    """Cuenta enlaces variable→salida y coapariciones entre variables."""
    counts: dict[tuple[str, str, str], int] = {}
    for rule in rules:
        variables = sorted(rule.antecedents)
        for variable in variables:
            key = (variable, target_column, "Variable → salida")
            counts[key] = counts.get(key, 0) + 1
        for first, second in combinations(variables, 2):
            key = (first, second, "Coaparición")
            counts[key] = counts.get(key, 0) + 1
    rows = [
        {"Origen": first, "Destino": second, "Tipo": kind, "Reglas asociadas": count}
        for (first, second, kind), count in counts.items()
    ]
    return pd.DataFrame(rows).sort_values("Reglas asociadas", ascending=False) if rows else pd.DataFrame(
        columns=["Origen", "Destino", "Tipo", "Reglas asociadas"]
    )


def graphviz_dot(relationships: pd.DataFrame, target_column: str) -> str:
    """Genera un grafo de dependencias compacto para Streamlit/Graphviz."""
    lines = ["digraph rules {", "rankdir=LR;", 'node [shape=box, style="rounded,filled", fillcolor="#F8FAFC"];']
    lines.append(f'"{target_column}" [shape=oval, fillcolor="#DBEAFE"];')
    for _, relation in relationships.iterrows():
        source = str(relation["Origen"]).replace('"', "\\\"")
        target = str(relation["Destino"]).replace('"', "\\\"")
        count = int(relation["Reglas asociadas"])
        color = "#2563EB" if relation["Tipo"] == "Variable → salida" else "#94A3B8"
        lines.append(
            f'"{source}" -> "{target}" [label="{count}", color="{color}", penwidth="{1 + count}"];'
        )
    lines.append("}")
    return "\n".join(lines)


def rules_for_relationship(
    rules: list[LearnedRule], origin: str, destination: str, relationship_type: str, target_column: str
) -> list[LearnedRule]:
    """Devuelve las reglas relacionadas con un enlace visible en el grafo."""
    if relationship_type == "Variable → salida" and destination == target_column:
        return [rule for rule in rules if origin in rule.antecedents]
    return [rule for rule in rules if origin in rule.antecedents and destination in rule.antecedents]
