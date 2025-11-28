# parser_utils.py
import spacy
from spacy.pipeline import EntityRuler
import pdfplumber
import docx2txt
import re

# Load English tokenizer, tagger, parser and NER
nlp = spacy.load("en_core_web_sm")

# --- CUSTOM SKILL EXTRACTION LOGIC ---
# We add a pipeline component to identify technical skills
ruler = nlp.add_pipe("entity_ruler", before="ner")
patterns = [
    {"label": "SKILL", "pattern": "Python"},
    {"label": "SKILL", "pattern": "Java"},
    {"label": "SKILL", "pattern": "Flask"},
    {"label": "SKILL", "pattern": "Django"},
    {"label": "SKILL", "pattern": "SQL"},
    {"label": "SKILL", "pattern": "Machine Learning"},
    {"label": "SKILL", "pattern": "React"},
    {"label": "SKILL", "pattern": "AWS"},
    {"label": "SKILL", "pattern": "Docker"},
    {"label": "SKILL", "pattern": "Kubernetes"}
]
ruler.add_patterns(patterns)

def extract_text(filepath, filename):
    """Extract text from PDF or DOCX."""
    text = ""
    if filename.endswith('.pdf'):
        with pdfplumber.open(filepath) as pdf:
            for page in pdf.pages:
                text += page.extract_text() + "\n"
    elif filename.endswith('.docx'):
        text = docx2txt.process(filepath)
    return text

def parse_resume(text):
    """Extract Name, Email, Skills, and Education using spaCy and Regex."""
    doc = nlp(text)
    data = {
        "name": None,
        "email": None,
        "skills": [],
        "education": "Not found"
    }

    # 1. Extract Name (First PERSON entity)
    for ent in doc.ents:
        if ent.label_ == "PERSON" and not data["name"]:
            data["name"] = ent.text

    # 2. Extract Email (Regex is often more reliable than NER for emails)
    email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    email_match = re.search(email_pattern, text)
    if email_match:
        data["email"] = email_match.group(0)

    # 3. Extract Skills (Using our custom EntityRuler)
    skills = []
    for ent in doc.ents:
        if ent.label_ == "SKILL":
            skills.append(ent.text)
    data["skills"] = list(set(skills)) # Remove duplicates

    # 4. Simple Education Extraction (Looking for keywords)
    # A real production system would use a trained model for this.
    edu_keywords = ["Bachelor", "Master", "B.Tech", "M.Tech", "PhD", "University", "College"]
    lines = text.split('\n')
    for line in lines:
        if any(keyword in line for keyword in edu_keywords):
            data["education"] = line.strip()
            break  # Assume the first match is the highest degree

    return data