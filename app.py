import streamlit as st
import mysql.connector
import google.generativeai as genai
import PyPDF2
import re
import os
import pandas as pd
from dotenv import load_dotenv
from st_aggrid import AgGrid, GridOptionsBuilder


# Load API key from .env
load_dotenv()
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
model = genai.GenerativeModel("models/gemini-1.5-flash")

# DB Connection
def connect_to_db():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="Kaaru@123",
        database="ats_project"
    )

# Extract text from PDF
def extract_text_from_pdf(uploaded_file):
    reader = PyPDF2.PdfReader(uploaded_file)
    return " ".join(page.extract_text() or "" for page in reader.pages)

# Feedback + Match % from Gemini
def get_feedback_and_match(resume_text, job_description):
    prompt = f"""
You are an expert resume evaluator. Evaluate the following resume for the job described below.

Resume:
{resume_text}

Job Description:
{job_description}

Give your feedback and match percentage.
"""
    response = model.generate_content(prompt).text
    return response, extract_match_percentage(response)

# Extract % from feedback
def extract_match_percentage(response):
    match = re.search(r"(\d+)%", response)
    return f"{match.group(1)}%" if match else "0%"

# Save to DB
def insert_to_db(resume_text, job_description, feedback, match):
    db = connect_to_db()
    cursor = db.cursor()
    cursor.execute(
        "INSERT INTO resumes (resume_text, job_description, gemini_feedback, match_percentage) VALUES (%s, %s, %s, %s)",
        (resume_text, job_description, feedback, f"{match}%")
    )
    db.commit()
    cursor.close()
    db.close()

# Fetch resumes
def fetch_all_resumes():
    db = connect_to_db()
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM resumes ORDER BY CAST(SUBSTRING_INDEX(match_percentage, '%', 1) AS UNSIGNED) DESC")
    results = cursor.fetchall()
    cursor.close()
    db.close()
    return results

# Streamlit setup
st.set_page_config(page_title="ATS App", layout="wide")
st.title("🧠 AI Resume Evaluator & Tracker")

tab1, tab2 = st.tabs(["📤 Upload Resume", "📊 Dashboard"])

with tab1:
    job_description = st.text_area("📝 Enter Job Description", height=160)

    uploaded_file = st.file_uploader("📎 Upload Resume (PDF)", type=["pdf"])
    if st.button("🔍 Analyze Resume") and uploaded_file and job_description:
        with st.spinner("Analyzing resume with Gemini..."):
            resume_text = extract_text_from_pdf(uploaded_file)
            feedback, match_percent = get_feedback_and_match(resume_text, job_description)

            insert_to_db(resume_text, job_description, feedback, match_percent)

        st.success("✅ Analysis complete!")
        st.metric("Match Percentage", f"{match_percent}%")
        st.markdown("#### 🧾 Gemini Feedback")
        st.write(feedback)

with tab2:
    st.markdown("### 📚 Evaluated Resumes")
    resumes = fetch_all_resumes()

    if resumes:
        # Prepare data safely
        for res in resumes:
            try:
                res['match_num'] = int(res['match_percentage'].replace('%', ''))
            except (ValueError, AttributeError):
                res['match_num'] = 0  # Default to 0% if bad data

        # Build DataFrame for AgGrid
        table_data = [{
            'ID': r['id'],
            'Match %': r['match_num'],
            'Feedback Summary': (r['gemini_feedback'] or "")[:150] + '...',
            'Job Description': (r['job_description'] or "")[:80] + '...'
        } for r in resumes]

        df = pd.DataFrame(table_data)

        gb = GridOptionsBuilder.from_dataframe(df)
        gb.configure_pagination()
        gb.configure_default_column(enableSorting=True)  
        gb.configure_selection('single')
        grid_options = gb.build()


        st.info("Click on a row to see full feedback ⬇️")
        grid_table = AgGrid(df, gridOptions=grid_options, height=400)

        selected = grid_table['selected_rows']
        if isinstance(selected, list) and len(selected) > 0:
            sel_id = selected[0]['ID']
            sel_res = next(r for r in resumes if r['id'] == sel_id)
            st.markdown("---")
            st.subheader(f"📋 Full Feedback for Resume ID {sel_id}")
            st.markdown(f"**Match:** {sel_res['match_percentage']}")
            st.markdown(f"**Feedback:**\n\n{sel_res['gemini_feedback']}")
            
        elif isinstance(selected, pd.DataFrame) and not selected.empty:
            sel_id = selected.iloc[0]['ID']
            sel_res = next(r for r in resumes if r['id'] == sel_id)
            st.markdown("---")
            st.subheader(f"📋 Full Feedback for Resume ID {sel_id}")
            st.markdown(f"**Match:** {sel_res['match_percentage']}")
            st.markdown(f"**Feedback:**\n\n{sel_res['gemini_feedback']}")


    else:
        st.warning("No resumes evaluated yet.")
