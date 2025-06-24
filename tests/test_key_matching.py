import yaml
import grader


def test_case_whitespace_insensitive_lookup():
    with open('rubric.yml') as f:
        rubric_config = yaml.safe_load(f)

    bands = {
        'Symptom_Analysis ': 4,
        '  COMMUNICATION  ': 5,
        'Primary Diagnosis Accuracy & Justification': 3,
        'bps_factors': 4,
        'diagnostic_diff': 4,
        'treatment': 4,
    }

    result = grader.calculate_final_grade(bands, 1000, rubric_config)

    assert result['breakdown']['symptom_analysis']['band'] == 4
    assert result['breakdown']['communication']['band'] == 5
    assert result['breakdown']['diagnostic_primary']['band'] == 3
