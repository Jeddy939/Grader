# AI Grader

This project provides a simple web interface for generating AI powered feedback on student assignments. Files are graded using Google's Gemini API according to the rubric in `rubric.yml`.

## Setup

1. Install Python 3.12 or newer.
2. Install the dependencies:

```bash
pip install -r requirements.txt
```

3. Create a `.env` file in the repository root containing your API key:

```bash
GEMINI_API_KEY="YOUR_API_KEY"
```

## Running the App

Start the Streamlit interface with:

```bash
streamlit run app.py
```

Upload one or more `.docx` or `.pdf` files from the browser and click **Run Grading**. The files are stored in `input_assessments/` and the generated feedback DOCX reports and `grading_summary.csv` appear in `output_feedback/`.

After grading completes the app displays the summary table and download links for all reports and the CSV file.

## Batch Grading Scripts

The repository provides two command‑line scripts for offline processing of
submissions:

* **`grader.py`** &ndash; uses the lightweight `gemini-1.5-flash` model. Run this
  when you want quick grading with minimal API usage.
* **`bigbraingrader.py`** &ndash; uses the larger `gemini-1.5-pro` model for the
  initial grade and falls back to `gemini-1.5-flash` for an optional fairness
  review. A delay is built in to respect rate limits, so processing is slower
  but typically produces higher quality feedback.

Both scripts read files in `input_assessments/` and generate a feedback DOCX
report per student as well as a `grading_summary.csv` file in
`output_feedback/`.

The DOCX reports now include a summary table of points for each criterion and a
new **Suggested Improvements** section under every criterion. These additions
make it easy to see where marks were gained or lost and give students concrete
advice on how to improve.

