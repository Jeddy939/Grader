import logging
import yaml
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import bigbraingrader
import grader


def test_rule_with_missing_band_bigbrain(caplog):
    with open('rubric.yml') as f:
        rubric_config = yaml.safe_load(f)

    # bands missing 'diagnostic_primary'
    bands = {
        'symptom_analysis': 5,
        'bps_factors': 5,
        # omit diagnostic_primary intentionally
        'diagnostic_diff': 4,
        'treatment': 5,
        'communication': 5,
    }

    caplog.set_level(logging.WARNING)
    result = bigbraingrader.calculate_final_grade(bands, 1000, rubric_config)

    # Rule should execute and cap treatment points to 3
    assert result['breakdown']['treatment']['points'] == 3

    # No warning about failed rule evaluation should be logged
    assert "Failed to evaluate rule" not in caplog.text


def test_rule_with_missing_band_grader(caplog):
    with open('rubric.yml') as f:
        rubric_config = yaml.safe_load(f)

    bands = {
        'symptom_analysis': 5,
        'bps_factors': 5,
        'diagnostic_diff': 4,
        'treatment': 5,
        'communication': 5,
    }

    caplog.set_level(logging.WARNING)
    result = grader.calculate_final_grade(bands, 1000, rubric_config)

    assert result['breakdown']['treatment']['points'] == 3

    assert "Failed to evaluate rule" not in caplog.text
