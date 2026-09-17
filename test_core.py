import unittest

import pandas as pd

from src.data_loading import build_variable_summary, load_csv_bytes
from src.discretization import apply_discretizations
from src.lfit_engine import LearnedRule, run_pride
from src.preprocessing import apply_missing_value_treatments
from src.state import initialize_session_state, reset_for_dataset
from src.validation import validate_analysis_configuration
from src.rule_analysis import (
    comparison_table,
    descriptive_findings,
    filter_rules,
    graphviz_dot,
    relationship_counts,
    rules_to_matrix,
    variable_indicators,
)


class SessionStateStub(dict):
    def __getattr__(self, name):
        return self[name]

    def __setattr__(self, name, value):
        self[name] = value


class DataLoadingTests(unittest.TestCase):
    def test_loads_windows_encoded_semicolon_csv(self):
        content = "edad;diagnóstico\n30;bajo\n".encode("cp1252")

        dataframe, info = load_csv_bytes(content)

        self.assertEqual(info.encoding, "cp1252")
        self.assertEqual(info.separator, ";")
        self.assertEqual(list(dataframe.columns), ["edad", "diagnóstico"])

    def test_variable_summary_reports_missing_values(self):
        dataframe = pd.DataFrame({"edad": [20, None], "salida": ["bajo", "alto"]})

        summary = build_variable_summary(dataframe).set_index("Variable")

        self.assertEqual(summary.loc["edad", "Ausentes"], 1)
        self.assertEqual(summary.loc["edad", "Estado"], "Con ausentes")


class ValidationAndDiscretizationTests(unittest.TestCase):
    def setUp(self):
        self.dataframe = pd.DataFrame(
            {"edad": [20, None, 70], "resultado": ["bajo", "alto", "alto"], "id": [1, 2, 3]}
        )

    def test_valid_configuration_warns_about_missing_values(self):
        validation = validate_analysis_configuration(
            self.dataframe, {"edad": "Entrada", "resultado": "Salida", "id": "Identificador"}
        )

        self.assertTrue(validation.is_ready)
        self.assertEqual(validation.output_variable, "resultado")
        self.assertEqual(len(validation.warnings), 1)

    def test_multiple_outputs_are_rejected(self):
        validation = validate_analysis_configuration(
            self.dataframe, {"edad": "Salida", "resultado": "Salida"}
        )

        self.assertFalse(validation.is_ready)
        self.assertIsNone(validation.output_variable)

    def test_manual_discretization_keeps_missing_values(self):
        processed, summary = apply_discretizations(
            self.dataframe, {"edad": {"method": "manual", "raw_cuts": "40, 65"}}
        )

        self.assertEqual(processed["edad"].isna().sum(), 1)
        self.assertEqual(summary["edad"]["cuts"], [40.0, 65.0])

    def test_missing_value_treatments_are_applied_to_a_copy(self):
        dataframe = pd.DataFrame(
            {"edad": [20, None, 60], "grupo": ["A", None, "B"], "salida": ["bajo", "alto", "alto"]}
        )

        processed, summary = apply_missing_value_treatments(
            dataframe,
            {
                "edad": {"strategy": "median"},
                "grupo": {"strategy": "unknown"},
            },
        )

        self.assertEqual(dataframe["edad"].isna().sum(), 1)
        self.assertEqual(processed["edad"].isna().sum(), 0)
        self.assertEqual(processed.loc[1, "grupo"], "Desconocido")
        self.assertEqual(summary["rows_removed"], 0)

    def test_drop_rows_removes_only_rows_with_selected_missing_values(self):
        processed, summary = apply_missing_value_treatments(
            self.dataframe, {"edad": {"strategy": "drop_rows"}}
        )

        self.assertEqual(len(processed), 2)
        self.assertEqual(summary["rows_removed"], 1)


class StateTests(unittest.TestCase):
    def test_dataset_reset_clears_previous_analysis_state(self):
        session_state = SessionStateStub()
        initialize_session_state(session_state)
        session_state["role_edad"] = "Salida"
        session_state.roles = {"edad": "Salida"}
        session_state.discretization_summary = {"edad": {"method": "manual"}}
        dataframe = pd.DataFrame({"edad": [20, 30]})

        reset_for_dataset(session_state, dataframe, ("nuevo.csv", 10, "hash"))

        self.assertEqual(session_state.roles, {})
        self.assertIsNone(session_state.output_var)
        self.assertNotIn("role_edad", session_state)
        self.assertTrue(session_state.df.equals(dataframe))


class PRIDEIntegrationTests(unittest.TestCase):
    def test_pride_learns_static_rules_from_discrete_data(self):
        dataframe = pd.DataFrame(
            {
                "tension": ["alta", "alta", "normal", "normal"],
                "fumador": ["si", "no", "si", "no"],
                "riesgo": ["alto", "alto", "bajo", "bajo"],
            }
        )

        result = run_pride(
            dataframe,
            ["tension", "fumador"],
            "riesgo",
            preprocessing_summary={"rows_before": 4, "rows_after": 4, "variables": []},
            discretization_summary={},
        )

        self.assertEqual(result.observations, 4)
        self.assertEqual(result.target_column, "riesgo")
        self.assertGreater(len(result.rules), 0)
        self.assertTrue(all(rule.coverage >= rule.compatible_cases for rule in result.rules))
        self.assertTrue(all(0 <= rule.data_consistency <= 1 for rule in result.rules))
        self.assertTrue(all(rule.lift is not None for rule in result.rules))
        self.assertEqual(sum(count for _, count in result.target_distribution), 4)
        self.assertEqual(result.trace.input_variables, ("tension", "fumador"))
        self.assertEqual(result.trace.preprocessing_summary["rows_after"], 4)


class RuleAnalysisTests(unittest.TestCase):
    def setUp(self):
        self.rules = (
            LearnedRule("R1", {"edad": "mayor", "tension": "alta"}, "riesgo", "alto", "", 2, 8, 7),
            LearnedRule("R2", {"edad": "mayor", "fumador": "si"}, "riesgo", "alto", "", 2, 5, 5),
            LearnedRule("R3", {"tension": "normal"}, "riesgo", "bajo", "", 1, 10, 9),
        )

    def test_filters_rules_without_changing_the_source_collection(self):
        filtered = filter_rules(
            self.rules,
            search="",
            target_values=["alto"],
            required_variables=["edad"],
            require_all_variables=True,
            min_coverage=6,
            max_conditions=2,
        )

        self.assertEqual([rule.identifier for rule in filtered], ["R1"])
        self.assertEqual(len(self.rules), 3)

    def test_matrix_comparison_and_relationships_are_aligned_by_variable(self):
        matrix = rules_to_matrix(list(self.rules), ("edad", "tension", "fumador"))
        comparison = comparison_table(self.rules[0], self.rules[1], ("edad", "tension", "fumador"))
        relationships = relationship_counts(list(self.rules), "riesgo")

        self.assertEqual(matrix.loc[0, "fumador"], "—")
        self.assertIn("Condición compartida", comparison["Relación"].tolist())
        self.assertIn("Variable → salida", relationships["Tipo"].tolist())
        self.assertIn("digraph rules", graphviz_dot(relationships, "riesgo"))


    def test_metrics_and_findings_are_descriptive(self):
        measured_rules = [
            LearnedRule(
                "R4",
                {"edad": "mayor"},
                "riesgo",
                "alto",
                "",
                1,
                10,
                8,
                0.8,
                0.4,
                2.0,
            )
        ]

        filtered = filter_rules(
            tuple(measured_rules), "", ["alto"], [], False, 0, 2, min_consistency=0.75
        )
        indicators = variable_indicators(measured_rules, ("edad", "tension"))
        findings = descriptive_findings(measured_rules, ("edad", "tension"))

        self.assertEqual(filtered, measured_rules)
        self.assertEqual(indicators.loc[0, "Consistencia ponderada"], "80.0%")
        self.assertIn("mayor lift", findings[0])


if __name__ == "__main__":
    unittest.main()
