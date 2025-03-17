# models.py
from database import db


class Resume(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(255), nullable=False)
    uploaded_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    score = db.Column(db.Integer, nullable=True)
    summary = db.Column(db.Text, nullable=True)
    job_id = db.Column(db.Integer, db.ForeignKey('job.id'), nullable=False)
    user = db.relationship("User", backref=db.backref("resumes", lazy=True))

class Job(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=False)
    company = db.Column(db.String(255), nullable=False)
    location = db.Column(db.String(255), nullable=False)
    posted_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    admin_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)

    admin = db.relationship("User", backref=db.backref("jobs", lazy=True))

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), unique=True, nullable=False)
    role = db.Column(db.String(50), nullable=False)  # 'recruiter' or 'job_seeker'

    def __init__(self, email, role):
        self.email = email
        self.role = role
