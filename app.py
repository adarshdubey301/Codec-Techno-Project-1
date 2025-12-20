import os
import re
import pdfplumber
import spacy
from flask import Flask, render_template_string, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from spacy.matcher import Matcher, PhraseMatcher

# 1. INITIALIZATION
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///resumes.db'
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Load NLP Model
nlp = spacy.load("en_core_web_sm")

# 2. DATABASE MODEL
class Candidate(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    email = db.Column(db.String(100))
    skills = db.Column(db.String(500))

# 3. ANALYZER LOGIC
def perfect_analyzer(file_path):
    text = ""
    first_page_text = ""
    with pdfplumber.open(file_path) as pdf:
        first_page_text = pdf.pages[0].extract_text() or ""
        for page in pdf.pages:
            text += page.extract_text() or ""

    doc = nlp(text)
    header_doc = nlp(first_page_text[:500])

    # Email Extraction
    email_regex = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    email_match = re.search(email_regex, text)
    email = email_match.group(0) if email_match else "Not Found"

    # Name Extraction
    name = "Unknown Name"
    matcher = Matcher(nlp.vocab)
    name_patterns = [[{'POS': 'PROPN'}, {'POS': 'PROPN'}]]
    matcher.add("NAME", name_patterns)
    matches = matcher(header_doc)
    if matches:
        name = header_doc[matches[0][1]:matches[0][2]].text
    else:
        for ent in header_doc.ents:
            if ent.label_ == "PERSON":
                name = ent.text
                break

    # Skill Extraction
    skill_list = ["Python", "Java", "SQL", "Flask", "React", "AWS", "Machine Learning"]
    skill_matcher = PhraseMatcher(nlp.vocab)
    patterns = [nlp.make_doc(s) for s in skill_list]
    skill_matcher.add("SKILL_LIST", patterns)
    found_skills = list(set([doc[start:end].text for _, start, end in skill_matcher(doc)]))
    
    return name, email, ", ".join(found_skills)

# 4. INTERFACE (Updated with Remover Buttons)
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>Perfect Resume Parser</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
</head>
<body class="bg-light">
    <div class="container py-5">
        <h2 class="text-center mb-4">🎯 Perfect Resume Analyzer</h2>
        
        <div class="card p-4 shadow-sm mb-4">
            <form method="POST" action="/upload" enctype="multipart/form-data" class="row g-3">
                <div class="col-md-9"><input type="file" name="resume" class="form-control" required></div>
                <div class="col-md-3"><button type="submit" class="btn btn-primary w-100">Upload & Parse</button></div>
            </form>
        </div>

        <div class="table-responsive bg-white rounded shadow-sm mb-4">
            <table class="table table-hover align-middle mb-0">
                <thead class="table-dark">
                    <tr>
                        <th>Name</th>
                        <th>Email</th>
                        <th>Skills</th>
                        <th class="text-center">Action</th>
                    </tr>
                </thead>
                <tbody>
                    {% for c in candidates %}
                    <tr>
                        <td><strong>{{ c.name }}</strong></td>
                        <td><code>{{ c.email }}</code></td>
                        <td>{{ c.skills }}</td>
                        <td class="text-center">
                            <a href="{{ url_for('delete_candidate', id=c.id) }}" class="btn btn-outline-danger btn-sm">
                                <i class="fas fa-trash"></i>
                            </a>
                        </td>
                    </tr>
                    {% endfor %}
                    {% if not candidates %}
                    <tr><td colspan="4" class="text-center py-4 text-muted">No resumes processed yet.</td></tr>
                    {% endif %}
                </tbody>
            </table>
        </div>

        {% if candidates %}
        <div class="d-flex justify-content-center">
            <form method="POST" action="/clear_all">
                <button type="submit" class="btn btn-danger px-5 shadow-sm" onclick="return confirm('Are you sure you want to delete all data?')">
                    <i class="fas fa-eraser me-2"></i> Remove All Data
                </button>
            </form>
        </div>
        {% endif %}
    </div>
</body>
</html>
'''

# 5. ROUTES (Includes Delete and Clear All)
@app.route('/')
def home():
    return render_template_string(HTML_TEMPLATE, candidates=Candidate.query.all())

@app.route('/upload', methods=['POST'])
def upload():
    file = request.files['resume']
    if file:
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
        file.save(file_path)
        name, email, skills = perfect_analyzer(file_path)
        db.session.add(Candidate(name=name, email=email, skills=skills))
        db.session.commit()
    return redirect(url_for('home'))

@app.route('/delete/<int:id>')
def delete_candidate(id):
    candidate = Candidate.query.get(id)
    if candidate:
        db.session.delete(candidate)
        db.session.commit()
    return redirect(url_for('home'))

@app.route('/clear_all', methods=['POST'])
def clear_all():
    db.session.query(Candidate).delete()
    db.session.commit()
    # Also clean up the uploads folder
    for f in os.listdir(app.config['UPLOAD_FOLDER']):
        os.remove(os.path.join(app.config['UPLOAD_FOLDER'], f))
    return redirect(url_for('home'))

if __name__ == '__main__':
    if not os.path.exists('uploads'): os.makedirs('uploads')
    with app.app_context(): db.create_all()
    app.run(port=5000, debug=True)