# AI Grader

This repository contains Python scripts to generate automated grading reports and draft feedback for student case study assignments. The grader relies on Google's **Gemini** API and a custom rubric provided in plain text.

## Contents

- `grader.py` – grades final submissions and outputs a DOCX report summarising rubric scores and reasoning.
- `draft_grader.py` – generates formative feedback for draft submissions without assigning a grade.
- `master_prompt.txt` – prompt template and rubric for the main grader.
- `draft_feedback_prompt.txt` – prompt for draft feedback.
- `grading_process.log` and `draft_grading_process.log` – example log files created by the scripts.
- `venv/` – Python virtual environment containing all dependencies (committed for portability).

## Requirements

The scripts expect Python 3.12 and the following packages:

```
dotenv
google-generativeai
python-docx
PyPDF2
PyYAML
```

A local virtual environment is included, but you can recreate one with `python -m venv venv` and install the packages manually.

## Configuration

1. Create a `.env` file with your Gemini API key:

```
GEMINI_API_KEY="YOUR_API_KEY"
```

2. Ensure the directories `input_assessments/` and `output_feedback/` exist in the repository root (they will be created automatically if missing). Place student files (`.docx` or `.pdf`) inside `input_assessments/`.

3. Adjust the prompt templates if required. Both contain a `{{STUDENT_SUBMISSION_TEXT_HERE}}` placeholder where the extracted student text is inserted.

## Usage

Run the main grader:

```bash
python grader.py
```

For draft feedback instead of a final grade:

```bash
python draft_grader.py
```

Each script processes all files in `input_assessments/` and writes DOCX reports to the appropriate output folder. Logs describing progress and any errors are written to `grading_process.log` or `draft_grading_process.log`.

## Notes

- PDF text extraction uses `PyPDF2`; encrypted or malformed PDFs may fail.
- DOCX extraction now captures text inside tables.
- The repository currently includes a Windows-based `venv` directory which can be removed if you prefer to create your own environment.
- There are no automated tests.
