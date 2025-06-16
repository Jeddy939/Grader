import os
import re
import logging
from dotenv import load_dotenv
import google.generativeai as genai
from docx import Document as DocxDocument  # To avoid clash with local 'Document'
from docx.shared import Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH
import PyPDF2
import yaml  # PyYAML

# --- Configuration ---
INPUT_FOLDER = "input_assessments"
OUTPUT_FOLDER = "output_feedback"
MASTER_PROMPT_FILE = "master_prompt.txt"
LOG_FILE = "grading_process.log"

# Setup basic logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(),  # Also print to console
    ],
)

# --- Helper Functions ---


def load_api_key():
    """Loads Gemini API key from .env file."""
    load_dotenv()
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        logging.error("GEMINI_API_KEY not found in .env file.")
        raise ValueError("API Key not configured.")
    return api_key


def get_student_name_from_filename(filename):
    """
    Attempts to extract a student name from filename.
    Example: "JohnDoe_Assignment1.docx" -> "JohnDoe"
    """
    name_part = os.path.splitext(filename)[0]
    # Simple heuristic: look for parts separated by common delimiters
    # that might indicate a name. This can be improved.
    potential_name = re.split(r"[_\-\s.]", name_part)[0]
    # Check if it looks like a name (e.g., starts with capital)
    if potential_name and potential_name[0].isupper():
        # Further refine if needed, e.g. look for CamelCase or multiple capitalized words
        return potential_name
    return None


def extract_text_from_file(filepath):
    """Extracts text and author metadata from supported files."""
    _, extension = os.path.splitext(filepath)
    text = ""
    doc_author = None
    try:
        if extension.lower() == ".docx":
            doc = DocxDocument(filepath)
            doc_author = doc.core_properties.author or None
            for para in doc.paragraphs:
                text += para.text + "\n"
        elif extension.lower() == ".pdf":
            with open(filepath, "rb") as f:
                reader = PyPDF2.PdfReader(f)
                if reader.is_encrypted:
                    logging.warning(
                        f"PDF '{filepath}' is encrypted. Attempting to read anyway if default password allows."
                    )
                    # You might need to handle decryption if password is known: reader.decrypt('')
                for page_num in range(len(reader.pages)):
                    page = reader.pages[page_num]
                    text += page.extract_text() + "\n"
        else:  # Attempt plain text for other files
            logging.info(f"Attempting to read '{filepath}' as plain text.")
            with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                text = f.read()

        text = re.sub(r"\s{3,}", "\n\n", text).strip()
        if not text.strip():
            logging.warning(f"No text extracted or file is empty: {filepath}")
            return None, None
        return text, doc_author

    except FileNotFoundError:
        logging.error(f"File not found: {filepath}")
        return None, None
    except PyPDF2.errors.PdfReadError:
        logging.error(
            f"Could not read PDF (possibly corrupted or password protected): {filepath}"
        )
        return None, None
    except Exception as e:
        logging.error(f"Error extracting text from {filepath}: {e}")
        return None, None


def load_master_prompt():
    """Loads the master prompt template from file."""
    try:
        with open(MASTER_PROMPT_FILE, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        logging.error(f"Master prompt file '{MASTER_PROMPT_FILE}' not found.")
        raise
    except Exception as e:
        logging.error(f"Error reading master prompt file: {e}")
        raise


def construct_full_prompt(student_text, master_prompt_template):
    """Inserts student text into the master prompt template."""
    if "{{STUDENT_SUBMISSION_TEXT_HERE}}" not in master_prompt_template:
        logging.error(
            "Placeholder '{{STUDENT_SUBMISSION_TEXT_HERE}}' not found in master prompt."
        )
        # Fallback: append student text if placeholder is missing
        return (
            master_prompt_template
            + "\n\n### STUDENT_SUBMISSION_TEXT_TO_GRADE:\n"
            + student_text
        )
    return master_prompt_template.replace(
        "{{STUDENT_SUBMISSION_TEXT_HERE}}", student_text
    )


def call_gemini_api(prompt_text, api_key):
    """Calls the Gemini API and returns the response text."""
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-1.5-flash-latest")  # Or your preferred model
    # Safety settings can be adjusted if needed
    safety_settings = [
        {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
    ]
    try:
        logging.info("Sending request to Gemini API...")
        # Add a timeout to generation_config if needed
        response = model.generate_content(prompt_text, safety_settings=safety_settings)
        # Check for empty or blocked responses
        if not response.parts:
            if response.prompt_feedback and response.prompt_feedback.block_reason:
                logging.error(
                    f"Gemini API request blocked. Reason: {response.prompt_feedback.block_reason_message}"
                )
                return None
            else:
                logging.error("Gemini API returned an empty response with no parts.")
                return None

        # Assuming the response is text. If it could be multi-modal, access response.text
        ai_response_text = response.text
        logging.info("Received response from Gemini API.")
        return ai_response_text
    except Exception as e:
        logging.error(f"Gemini API call failed: {e}")
        return None


def parse_gemini_yaml_response(response_text):
    """Parses the YAML response from Gemini."""
    if not response_text:
        return None
    try:
        # LLMs can sometimes add markdown backticks around YAML
        cleaned_response = response_text.strip()
        if cleaned_response.startswith("```yaml"):
            cleaned_response = cleaned_response[7:]
        if cleaned_response.startswith("```"):
            cleaned_response = cleaned_response[3:]
        if cleaned_response.endswith("```"):
            cleaned_response = cleaned_response[:-3]

        cleaned_response = cleaned_response.strip()

        parsed_data = yaml.safe_load(cleaned_response)
        # Basic validation of expected structure
        if "assistant_reasons" in parsed_data and "assistant_grade" in parsed_data:
            return parsed_data
        else:
            logging.error(
                f"Parsed YAML does not have expected structure. Parsed: {parsed_data}"
            )
            return None
    except yaml.YAMLError as e:
        logging.error(
            f"Failed to parse YAML response from Gemini: {e}\nRaw response:\n{response_text}"
        )
        return None
    except Exception as e:
        logging.error(
            f"An unexpected error occurred during YAML parsing: {e}\nRaw response:\n{response_text}"
        )
        return None


def format_feedback_as_docx(yaml_data, output_filepath, student_identifier, doc_author=None):
    """Formats the YAML data into a human-readable DOCX report."""
    try:
        doc = DocxDocument()
        doc.add_heading(f"Feedback Report for: {student_identifier}", level=1)
        if doc_author:
            doc.add_paragraph(f"Author (from file metadata): {doc_author}")

        # Overall Grade and Points
        grade_info = yaml_data.get("assistant_grade", {})
        overall_grade = grade_info.get("overall_grade", "N/A")
        total_points = grade_info.get("total_points", "N/A")
        # Assuming max points is 25 as per rubric JSON, or you can extract it if present
        max_total_points = 25

        doc.add_heading("Overall Assessment", level=2)
        doc.add_paragraph(f"Overall Grade: {overall_grade}")
        doc.add_paragraph(f"Total Points: {total_points} / {max_total_points}")
        doc.add_paragraph()  # Spacer

        # Criteria Breakdown
        doc.add_heading("Detailed Breakdown by Criterion", level=2)
        reasons = yaml_data.get("assistant_reasons", [])
        breakdown = grade_info.get("breakdown", {})

        # You'll need to map criterion IDs from 'assistant_reasons' (e.g., 'symptom_analysis')
        # to their full names and max points if you want to display them nicely.
        # This mapping can be hardcoded or derived from your rubric JSON if it were loaded.
        # For simplicity, we'll use the IDs for now.
        # Example mapping (you'd get this from your RUBRIC_JSON ideally)
        rubric_criteria_details = {
            "symptom_analysis": {
                "name": "Knowledge & Symptom Analysis",
                "max_points": 5,
            },
            "bps_factors": {
                "name": "Biological, Psychological & Social Factors",
                "max_points": 4,
            },
            "diagnostic_primary": {
                "name": "Primary Diagnosis Accuracy & Justification",
                "max_points": 4,
            },
            "diagnostic_diff": {
                "name": "Differential Diagnosis Reasoning",
                "max_points": 4,
            },
            "treatment": {
                "name": "Treatment Selection & Justification",
                "max_points": 5,
            },
            "communication": {"name": "Communication & Referencing", "max_points": 3},
        }

        for idx, reason_item in enumerate(reasons, start=1):
            criterion_id = reason_item.get("criterion", "Unknown Criterion")
            band = reason_item.get("band", "N/A")
            rationale = reason_item.get("rationale", "No rationale provided.")
            evidence = reason_item.get("evidence", "No evidence quoted.")

            criterion_details = rubric_criteria_details.get(
                criterion_id,
                {"name": criterion_id.replace("_", " ").title(), "max_points": "N/A"},
            )
            criterion_name = criterion_details["name"]

            criterion_grade_info = breakdown.get(criterion_id, {})
            points_achieved = criterion_grade_info.get("points", "N/A")
            max_criterion_points = criterion_details["max_points"]

            doc.add_heading(f"{idx}. {criterion_name}", level=3)

            doc.add_paragraph(f"Band Achieved: {band}")
            doc.add_paragraph(f"Points: {points_achieved} / {max_criterion_points}")

            doc.add_paragraph("AI's Rationale:", style="Intense Quote")
            doc.add_paragraph(rationale)

            doc.add_paragraph("Evidence from Student's Work:", style="Intense Quote")
            if "\n" in evidence:
                for line in evidence.splitlines():
                    line = line.strip()
                    if not line:
                        continue
                    doc.add_paragraph(line, style="List Bullet")
            else:
                doc.add_paragraph(evidence if evidence else "N/A")

            doc.add_paragraph()  # Spacer

        doc.save(output_filepath)
        logging.info(f"Feedback report saved to: {output_filepath}")

    except Exception as e:
        logging.error(f"Failed to create DOCX report for {student_identifier}: {e}")


# --- Main Processing Logic ---
def main():
    logging.info("Starting AI Student Assessment Grader...")
    try:
        api_key = load_api_key()
        master_prompt_template = load_master_prompt()
    except Exception as e:
        logging.critical(f"Initialization failed: {e}")
        return

    if not os.path.exists(INPUT_FOLDER):
        logging.error(f"Input folder '{INPUT_FOLDER}' not found.")
        return
    if not os.path.exists(OUTPUT_FOLDER):
        os.makedirs(OUTPUT_FOLDER)
        logging.info(f"Created output folder: {OUTPUT_FOLDER}")

    processed_files = 0
    successful_grades = 0

    for filename in os.listdir(INPUT_FOLDER):
        filepath = os.path.join(INPUT_FOLDER, filename)
        if not os.path.isfile(filepath):
            continue  # Skip directories

        logging.info(f"--- Processing file: {filename} ---")
        processed_files += 1

        student_name_guess = get_student_name_from_filename(filename)
        student_identifier = (
            student_name_guess if student_name_guess else os.path.splitext(filename)[0]
        )

        extracted_text, doc_author = extract_text_from_file(filepath)
        if not extracted_text:
            logging.warning(
                f"Skipping {filename} due to text extraction failure or empty content."
            )
            continue

        # Simple word count for info, AI will use its own logic based on rubric
        word_count = len(extracted_text.split())
        logging.info(f"Extracted approx. {word_count} words from {filename}.")
        if word_count < 50:  # Arbitrary threshold for very short/empty files
            logging.warning(
                f"Extracted text for {filename} is very short ({word_count} words). May not be suitable for grading."
            )
            # continue # Optional: skip very short files

        full_prompt = construct_full_prompt(extracted_text, master_prompt_template)

        # For debugging, you might want to save the full prompt
        # with open(os.path.join(OUTPUT_FOLDER, f"{student_identifier}_prompt.txt"), "w", encoding="utf-8") as pf:
        #    pf.write(full_prompt)

        api_response = call_gemini_api(full_prompt, api_key)
        if not api_response:
            logging.warning(f"Skipping {filename} due to Gemini API call failure.")
            continue

        parsed_data = parse_gemini_yaml_response(api_response)
        if not parsed_data:
            logging.warning(f"Skipping {filename} due to YAML parsing failure.")
            # Save raw response for debugging
            raw_response_path = os.path.join(
                OUTPUT_FOLDER, f"{student_identifier}_raw_gemini_response.txt"
            )
            with open(raw_response_path, "w", encoding="utf-8") as f:
                f.write(api_response if api_response else "No response received.")
            logging.info(f"Raw Gemini response saved to: {raw_response_path}")
            continue

        output_filename_base = student_identifier
        output_docx_path = os.path.join(
            OUTPUT_FOLDER, f"{output_filename_base}_graded.docx"
        )

        format_feedback_as_docx(parsed_data, output_docx_path, student_identifier, doc_author=doc_author)
        successful_grades += 1
        logging.info(f"Successfully processed and graded: {filename}")

    logging.info("--- Processing Complete ---")
    logging.info(
        f"Total files found: {len(os.listdir(INPUT_FOLDER))}"
    )  # This will count folders too, refine if needed
    logging.info(f"Files attempted for processing: {processed_files}")
    logging.info(f"Successfully graded: {successful_grades}")
    logging.info(f"Reports saved in: {OUTPUT_FOLDER}")
    logging.info(f"Log file saved at: {LOG_FILE}")


if __name__ == "__main__":
    main()
