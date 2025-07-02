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





# import fitz
# import streamlit as st
# # Connect to MySQL
# conn = mysql.connector.connect(
#     host="localhost",
#     user="root",
#     password="Kaaru@123",  # <- put your MySQL password here
#     database="ats_resume_db"
# )
# cursor = conn.cursor()

# def input_pdf_setup(uploaded_file):
#     with fitz.open(stream=uploaded_file.read(), filetype="pdf") as doc:
#         text = ""
#         for page in doc:
#             text += page.get_text()
#     return text


# # Create table if not exists
# cursor.execute("""
#     CREATE TABLE IF NOT EXISTS resumes (
#         id INT AUTO_INCREMENT PRIMARY KEY,
#         job_description TEXT,
#         gemini_feedback TEXT,
#         match_percentage VARCHAR(50),
#         created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
#     )
# """)
# conn.commit()


# from dotenv import load_dotenv
# load_dotenv()

# import base64
# import streamlit as st
# import os
# import io
# import mysql.connector
# import re
# from datetime import datetime
# from PIL import Image
# import pdf2image
# import google.generativeai as genai
# from docx import Document

# # Configure Gemini API
# genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

# # Connect to MySQL database
# def connect_to_db():
#     return mysql.connector.connect(
#         host="localhost",
#         user="root",
#         password="Kaaru@123",  # <-- Replace with your actual password
#         database="ats_project"
#     )

# # Extract match percentage from Gemini response
# def extract_match_percentage(text):
#     match = re.search(r'(\d+)%', text)
#     return match.group(1) + "%" if match else "N/A"

# # Convert uploaded PDF to image for Gemini input
# def input_pdf_setup(uploaded_file):
#     if uploaded_file is not None:
#         POPPLER_PATH = r"C:\Program Files (x86)\poppler\Library\bin"
#         pdf_bytes = uploaded_file.read()
#         images = pdf2image.convert_from_bytes(pdf_bytes, poppler_path=POPPLER_PATH)
#         first_page = images[0]
#         img_byte_arr = io.BytesIO()
#         first_page.save(img_byte_arr, format='JPEG')
#         img_byte_arr = img_byte_arr.getvalue()

#         pdf_parts = [{
#             "mime_type": "image/jpeg",
#             "data": base64.b64encode(img_byte_arr).decode()
#         }]
#         return pdf_parts
#     else:
#         raise FileNotFoundError("No file uploaded")

# # Generate response from Gemini
# def get_gemini_response(input, pdf_content, prompt):
#     model = genai.GenerativeModel('gemini-1.5-flash')
#     response = model.generate_content([input, pdf_content[0], prompt])
#     return response.text

# # Streamlit UI
# st.set_page_config(page_title="ATS Resume Expert")
# st.header("ATS Tracking System")

# input_text = st.text_area("Job Description: ", key="input")
# uploaded_file = st.file_uploader("Upload your Resume (PDF)", type=["pdf"])
# if uploaded_file:
#     st.success("PDF Uploaded Successfully ✅")

# submit1 = st.button("Tell me about the Resume")
# submit3 = st.button("Percentage Match")

# input_prompt1 = """You are an exprienced HR with Tech Experience in the field of any one job role from Data Science or Full Stack, web development, Big Data, Data Engineer, Deveops, Data Analytics, your task is to review the provided resume against the job description for these profiles. Please share your professional evaluation on whether the canidate's profile aligns with the role. Highlight the strengths and weakness of the applicant in relation to the specified job role"""
# input_prompt3 = """You are an skilled ATS(Applicant Tracking System) scanner with a deep understanding of any one job role Data Science, Full Stack, web development, Big Data, Data Engineer, Deveops, Data Analytics,and deep ATS functionality, your task is to evaluate the resume against the provided job description. give me the percentage of the match and match if resume matches the job description. First the output should come as percentage and then keywords missing"""
# input_prompt_resume = """
# You are an expert resume evaluator. Given a candidate's resume and a job description, assess how well the resume matches the job.

# Provide:
# 1. A professional evaluation with specific feedback.
# 2. A match percentage (e.g., 75%).

# Be detailed but concise. End your response with the match percentage (e.g., "Match Percentage: 82%").
# """
# # Resume Evaluation
# if submit1:
#     if uploaded_file is not None:
#         pdf_content = input_pdf_setup(uploaded_file)
#         response = get_gemini_response(input_prompt1, pdf_content, input_text)
#         st.subheader("The Response is:")
#         st.write(response)
#         cursor.execute(
#             "INSERT INTO resumes (job_description, gemini_feedback) VALUES (%s, %s)",
#             (input_text, response)
#         )
#         conn.commit()


#         # Insert into database
#         try:
#             db = connect_to_db()
#             cursor = db.cursor()
#             query = "INSERT INTO resume_reviews (name, job_description, evaluation, match_percentage) VALUES (%s, %s, %s, %s)"
#             values = ("Candidate", input_text, response, "N/A")
#             cursor.execute(query, values)
#             db.commit()
#             st.success("✅ Evaluation saved to database.")
#         except Exception as e:
#             st.error(f"❌ Error saving to DB: {e}")
#     else:
#         st.warning("Upload a resume first.")

# # Percentage Match Evaluation
# elif submit3:
#     if uploaded_file is not None:
#         pdf_content = input_pdf_setup(uploaded_file)
#         response = get_gemini_response(input_prompt3, pdf_content, input_text)
#         import re
#         # Extract match percentage from response
#         match = re.search(r"\b\d{1,3}%", response)
#         match_percent = match.group() if match else "0%"

#         st.subheader("The Response is:")
#         st.write(response)
#         match_percent = response.split("%")[0].strip() + "%"
#         cursor.execute(
#             "INSERT INTO resumes (job_description, gemini_feedback, match_percentage) VALUES (%s, %s, %s)",
#             (input_text, response, match_percent)
#         )
#         conn.commit()

#         # Extract % and insert into DB
#         match_percent = extract_match_percentage(response)
#         try:
#             db = connect_to_db()
#             cursor = db.cursor()
#             query = "INSERT INTO resume_reviews (name, job_description, evaluation, match_percentage) VALUES (%s, %s, %s, %s)"
#             values = ("Candidate", input_text, response, match_percent)
#             cursor.execute(query, values)
#             db.commit()
#             st.success("✅ Match saved to database.")
#         except Exception as e:
#             st.error(f"❌ Error saving match: {e}")
#     else:
#         st.warning("Upload a resume first.")

# # Resume Generator Button
# generate_resume_button = st.button("Generate Tailored Resume")
# if generate_resume_button:
#     if uploaded_file and input_text.strip() != "":
#         pdf_content = input_pdf_setup(uploaded_file)
#         response = get_gemini_response(input_prompt_resume, pdf_content, input_text)

#         doc = Document()
#         doc.add_heading("Tailored Resume", 0)
#         for line in response.split("\n"):
#             if line.strip():
#                 doc.add_paragraph(line)

#         timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
#         filename = f"tailored_resume_{timestamp}.docx"
#         doc.save(filename)

#         cursor.execute(
#             "INSERT INTO resumes (job_description, gemini_feedback) VALUES (%s, %s)",
#             (input_text, response)
#         )
#         conn.commit()


#         with open(filename, "rb") as f:
#             st.download_button(
#                 label="Download Tailored Resume",
#                 data=f,
#                 file_name=filename,
#                 mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
#             )
#     else:
#         st.warning("Please upload a resume and job description.")

#         # ===========================
# # 📂 Display Stored Results
# # ===========================

# st.subheader("🗂️ Stored Resume Evaluations")

# cursor.execute("SELECT id, job_description, match_percentage, created_at FROM resumes ORDER BY created_at DESC")
# rows = cursor.fetchall()

# if rows:
#     for row in rows:
#         st.markdown(f"""
#         **🆔 ID**: {row[0]}  
#         **📄 Job Description**: {row[1][:100]}...  
#         **📊 Match %**: {row[2] if row[2] else 'N/A'}  
#         **🕒 Submitted On**: {row[3]}  
#         ---
#         """)
# else:
#     st.info("No evaluations stored yet.")


# # View History
# if st.button("📜 Show All Evaluations"):
#     try:
#         db = connect_to_db()
#         cursor = db.cursor()
#         cursor.execute("SELECT name, job_description, evaluation, match_percentage, timestamp FROM resume_reviews ORDER BY timestamp DESC")
#         rows = cursor.fetchall()
#         for row in rows:
#             st.markdown("---")
#             st.write(f"👤 Name: {row[0]}")
#             st.write(f"📝 JD: {row[1][:100]}...")
#             st.write(f"💬 Evaluation: {row[2][:300]}...")
#             st.write(f"📊 Match %: {row[3]}")
#             st.write(f"🕓 Time: {row[4]}")
#     except Exception as e:
#         st.error(f"Could not load evaluations: {e}")
# cursor.close()
# conn.close()
