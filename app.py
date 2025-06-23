import streamlit as st
import pandas as pd
from pathlib import Path

from grader import run_grading_process, INPUT_FOLDER, OUTPUT_FOLDER, SUMMARY_FILE

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

