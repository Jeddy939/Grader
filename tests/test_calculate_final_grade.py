import logging
import sys
from pathlib import Path
import types

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# Stub out optional dependencies required by bigbraingrader on import
for name in ["google", "google.generativeai", "docx", "PyPDF2", "yaml"]:
    if name not in sys.modules:
        module = types.ModuleType(name)
        if name == "docx":
            module.Document = object
        sys.modules[name] = module

from bigbraingrader import calculate_final_grade


def test_rule_execution_with_missing_band(caplog):
    rubric = {
        "criteria": {
            "crit_a": {"max_points": 5},
            "crit_b": {"max_points": 5},
        },
        "rules": [
            {
                "name": "default rule",
                "condition": "crit_b_band == 1",
                "action": "set_band",
                "target": "crit_a",
                "band": 5,
            }
        ],
        "grade_bands": {"A": 10},
        "total_points_possible": 10,
    }

    with caplog.at_level(logging.WARNING):
        result = calculate_final_grade({"crit_a": 2}, 100, rubric)

    # Ensure the rule executed and no evaluation warning was logged
    assert not any(
        "Failed to evaluate rule" in record.message for record in caplog.records
    )
    assert result["breakdown"]["crit_a"]["band"] == 5
