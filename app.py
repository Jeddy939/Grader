import streamlit as st
from pathlib import Path
import pandas as pd
import yaml
import plotly.express as px

# Import the grading function
try:
    from grader import run_grading_process
except ImportError:
    # Fallback to the main() entry point if run_grading_process doesn't exist
    from grader import main as run_grading_process

OUTPUT_DIR = Path("output_feedback")
RUBRIC_FILE = Path("rubric.yml")
INPUT_DIR = Path("input_assessments")

st.title("AI Grader for Psychology Assignments")

uploaded_files = st.sidebar.file_uploader(
    "Upload DOCX or PDF files", accept_multiple_files=True
)

def save_uploaded_files(files):
    INPUT_DIR.mkdir(exist_ok=True)
    for file in files:
        file_path = INPUT_DIR / file.name
        with open(file_path, "wb") as f:
            f.write(file.getbuffer())

# --- Data Aggregation Helper ---

def load_and_aggregate_data(output_dir: Path, rubric_config: dict):
    summary_path = output_dir / "grading_summary.csv"
    if not summary_path.exists():
        return None

    df = pd.read_csv(summary_path)

    criteria = rubric_config.get("criteria", {})
    for crit in criteria:
        df[f"{crit}_pts"] = pd.NA

    for idx, row in df.iterrows():
        student_id = row["student"]
        yaml_path = output_dir / f"{student_id}_raw_gemini_response.txt"
        if not yaml_path.exists():
            continue
        try:
            text = yaml_path.read_text(encoding="utf-8").strip()
            if text.startswith("```yaml"):
                text = text[7:]
            if text.startswith("```"):
                text = text[3:]
            if text.endswith("```"):
                text = text[:-3]
            parsed = yaml.safe_load(text)
        except Exception:
            continue
        breakdown = (
            parsed.get("assistant_grade", {}).get("breakdown", {}) if isinstance(parsed, dict) else {}
        )
        for crit in criteria:
            pts = breakdown.get(crit, {}).get("points")
            if pts is not None:
                df.at[idx, f"{crit}_pts"] = pts

    return df

# --- Grading Trigger ---

if st.sidebar.button("Run Grader"):
    if uploaded_files:
        save_uploaded_files(uploaded_files)
        run_grading_process()
        st.success("Grading complete! Refresh to see results.")
    else:
        st.warning("Please upload at least one file before running the grader.")

# --- Display Results ---

st.header("Grading Results")
if (OUTPUT_DIR / "grading_summary.csv").exists():
    results_df = pd.read_csv(OUTPUT_DIR / "grading_summary.csv")
    st.dataframe(results_df)

    for docx in OUTPUT_DIR.glob("*_graded.docx"):
        with open(docx, "rb") as f:
            st.download_button(
                label=f"Download {docx.name}",
                data=f.read(),
                file_name=docx.name,
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
else:
    st.info("No grading results found.")

# --- Class-Wide Analysis ---
try:
    rubric_cfg = yaml.safe_load(RUBRIC_FILE.read_text(encoding="utf-8"))
except Exception:
    rubric_cfg = {}

analysis_df = load_and_aggregate_data(OUTPUT_DIR, rubric_cfg)

if analysis_df is not None:
    st.header("Class-Wide Analysis")
    col1, col2 = st.columns(2)

    # Grade Distribution
    grade_order = ["A", "B", "C", "D", "E"]
    grade_counts = analysis_df["grade"].value_counts().reindex(grade_order, fill_value=0)
    fig1 = px.bar(
        x=grade_counts.index,
        y=grade_counts.values,
        labels={"x": "Grade", "y": "Number of Students"},
        title="Overall Grade Distribution",
    )
    col1.plotly_chart(fig1, use_container_width=True)

    # Performance by Criterion
    crit_names = rubric_cfg.get("criteria", {})
    crit_data = []
    for crit_id, details in crit_names.items():
        max_pts = details.get("max_points", 0)
        if max_pts:
            avg = analysis_df[f"{crit_id}_pts"].astype(float).mean()
            pct = (avg / max_pts) * 100 if pd.notna(avg) else 0
            crit_data.append({"Criterion": details.get("name", crit_id), "Average Score (%)": pct})
    crit_df = pd.DataFrame(crit_data)
    crit_df.sort_values("Average Score (%)", inplace=True)
    fig2 = px.bar(
        crit_df,
        x="Average Score (%)",
        y="Criterion",
        orientation="h",
        range_x=[0, 100],
        title="Average Score by Grading Criterion",
    )
    col2.plotly_chart(fig2, use_container_width=True)

