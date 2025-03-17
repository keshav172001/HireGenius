from celery import Celery
from celery_db_connect import Database 
from models import Resume
# Initialize Celery app
import ssl
# Note: task depencies
import pdfplumber
from docx import Document
import random
from openai import OpenAI
import instructor
from pydantic import BaseModel


ssl_params = {"ssk_cert_reqs": ssl.CERT_NONE}
db = Database()

app = Celery(
    __name__,
        broker='redis://localhost:6379/0',
        backend='redis://localhost:6379/0',
        broker_connection_retry_on_startup = True,
        include = []
    )

def extract_text_from_resume(file_path):
    if file_path.endswith(".pdf"):
        with pdfplumber.open(file_path) as pdf:
            text = "\n".join([page.extract_text() for page in pdf.pages if page.extract_text()])
    elif file_path.endswith(".docx"):
        doc = Document(file_path)
        text = "\n".join([para.text for para in doc.paragraphs])
    else:
        return None  # Unsupported format
    return text


#Note : latest
class ResumeAnalysis(BaseModel):
    summary: str
    score: int



def analyze_resume(resume_text, job_description):
    client = instructor.from_openai(OpenAI())
    prompt = f"""
    You are an AI job screening assistant. Analyze the resume against the job description.

    Resume:
    {resume_text}

    Job Description:
    {job_description}

    Provide:
    1. A short summary of the best-suited role for the candidate.
    2. A score from 0 to 10
    """

    response = client.chat.completions.create(
            model="gpt-4-turbo",
            messages=[{"role": "system", "content": prompt}],
            response_model=ResumeAnalysis  # Enforcing structured output
        )
    return response.score, response.summary



# Define a simple task
@app.task
def score_resume(id, job_description, filepath):
    extracted_text = extract_text_from_resume(filepath)
    # score, summary = analyze_resume(extracted_text, job_description) # Note: free access exhausted
    summary = extracted_text
    score = random.randint(0, 10)
    with db.session() as session:   
        session.query(Resume).filter(Resume.id == id).update({"score": score, "summary": summary})
        session.commit()

    return 'SUCCESS', job_description



