import unittest

import pandas as pd

from src.data_loading import build_variable_summary, load_csv_bytes
from src.discretization import apply_discretizations
from src.validation import validate_analysis_configuration


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


if __name__ == "__main__":
    unittest.main()
