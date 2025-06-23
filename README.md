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

