# app.py
import os
from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
from parser_utils import extract_text, parse_resume

app = Flask(__name__)

# CONFIGURATION
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///resume.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

db = SQLAlchemy(app)

# DATABASE MODEL
class Candidate(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    email = db.Column(db.String(100))
    skills = db.Column(db.JSON)  # Storing skills as a JSON list
    education = db.Column(db.Text)
    filename = db.Column(db.String(100))

# Initialize DB
with app.app_context():
    db.create_all()

# ROUTES
@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        if 'resume' not in request.files:
            return redirect(request.url)
        
        file = request.files['resume']
        if file.filename == '':
            return redirect(request.url)

        if file:
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)

            # 1. Extract Text
            text = extract_text(filepath, filename)
            
            # 2. Parse Info
            data = parse_resume(text)

            # 3. Save to DB
            new_candidate = Candidate(
                name=data.get('name'),
                email=data.get('email'),
                skills=data.get('skills'),
                education=data.get('education'),
                filename=filename
            )
            db.session.add(new_candidate)
            db.session.commit()

            return redirect(url_for('index'))

    # Fetch all candidates for display
    candidates = Candidate.query.all()
    return render_template('index.html', candidates=candidates)

@app.route('/search')
def search():
    query = request.args.get('q')
    if query:
        # Search for candidates who have the skill in their JSON list
        # Note: This uses JSON containment operator (@>) for PostgreSQL
        results = Candidate.query.filter(Candidate.skills.cast(db.String).ilike(f"%{query}%")).all()
    else:
        results = []
    return render_template('results.html', results=results, query=query)

if __name__ == '__main__':
    app.run(debug=True)