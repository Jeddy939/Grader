import streamlit as st
import pandas as pd
from pathlib import Path
import yaml
import plotly.express as px

from grader import (
    run_grading_process,
    INPUT_FOLDER,
    OUTPUT_FOLDER,
    SUMMARY_FILE,
    load_rubric_config,
)


def load_and_aggregate_data(output_dir: Path, rubric_config: dict):
    """Return a DataFrame with criterion-level scores for all students."""
    summary_path = output_dir / SUMMARY_FILE
    if not summary_path.exists():
        return None

    try:
        df = pd.read_csv(summary_path)
    except Exception:
        return None

    criteria = rubric_config.get("criteria", {})
    for cid in criteria:
        df[f"{cid}_pts"] = pd.NA

    for idx, row in df.iterrows():
        student = str(row["student"])
        raw_path = output_dir / f"{student}_raw_gemini_response.txt"
        if not raw_path.exists():
            continue
        try:
            text = raw_path.read_text()
            cleaned = text.strip()
            if cleaned.startswith("```yaml"):
                cleaned = cleaned[len("```yaml") :]
            if cleaned.startswith("```"):
                cleaned = cleaned[3:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            cleaned = cleaned.strip()
            data = yaml.safe_load(cleaned)
        except Exception:
            continue

        breakdown = (
            data.get("assistant_grade", {}).get("breakdown", {}) if isinstance(data, dict) else {}
        )
        for cid in criteria:
            pts = breakdown.get(cid, {}).get("points")
            if pts is not None:
                df.at[idx, f"{cid}_pts"] = pts

    return df

st.title("AI Student Assessment Grader")

uploaded_files = st.file_uploader(
    "Upload student assignments (.docx or .pdf)",
    type=["docx", "pdf"],
    accept_multiple_files=True,
)

if "run_complete" not in st.session_state:
    st.session_state["run_complete"] = False

if st.button("Run Grading"):
    if uploaded_files:
        INPUT_FOLDER.mkdir(exist_ok=True)
        for file in uploaded_files:
            save_path = INPUT_FOLDER / file.name
            with open(save_path, "wb") as f:
                f.write(file.getbuffer())
    with st.spinner("Grading in progress..."):
        run_grading_process()
    st.success("Grading complete!")
    st.session_state["run_complete"] = True

if st.session_state.get("run_complete"):
    summary_path = OUTPUT_FOLDER / SUMMARY_FILE
    rubric_cfg = load_rubric_config()
    if summary_path.exists():
        st.subheader("Grading Summary")
        df = pd.read_csv(summary_path)
        st.dataframe(df)
        with open(summary_path, "rb") as f:
            st.download_button(
                "Download Summary CSV",
                data=f,
                file_name=SUMMARY_FILE,
                mime="text/csv",
            )

        agg_df = load_and_aggregate_data(OUTPUT_FOLDER, rubric_cfg)
        if agg_df is not None:
            st.header("Class-Wide Analysis")
            col1, col2 = st.columns(2)

            grade_counts = (
                agg_df["grade"].value_counts().sort_index().reset_index()
            )
            grade_counts.columns = ["grade", "count"]
            fig1 = px.bar(
                grade_counts,
                x="grade",
                y="count",
                title="Overall Grade Distribution",
            )
            col1.plotly_chart(fig1, use_container_width=True)

            crit_data = []
            for cid, cfg in rubric_cfg.get("criteria", {}).items():
                colname = f"{cid}_pts"
                if colname in agg_df:
                    max_pts = cfg.get("max_points", 0) or 0
                    avg = pd.to_numeric(agg_df[colname], errors="coerce").mean()
                    if max_pts:
                        perc = (avg / max_pts) * 100 if avg is not None else 0
                        crit_data.append({
                            "criterion": cfg.get("name", cid),
                            "avg_pct": perc,
                        })
            if crit_data:
                crit_df = pd.DataFrame(crit_data).sort_values("avg_pct")
                fig2 = px.bar(
                    crit_df,
                    x="avg_pct",
                    y="criterion",
                    orientation="h",
                    labels={"avg_pct": "Average Score (%)", "criterion": ""},
                    title="Average Score by Grading Criterion",
                    range_x=[0, 100],
                )
                col2.plotly_chart(fig2, use_container_width=True)

    st.subheader("Feedback Reports")
    for report_path in sorted(OUTPUT_FOLDER.glob("*_graded.docx")):
        with open(report_path, "rb") as f:
            st.download_button(
                label=f"Download {report_path.name}",
                data=f,
                file_name=report_path.name,
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                key=report_path.name,
            )

