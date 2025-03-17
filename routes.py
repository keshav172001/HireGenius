# routes.py
from flask import Blueprint, redirect, url_for, jsonify
from database import db
from models import User,Resume,Job
from auth import oidc
import os
from flask import request, flash,session
from config import Config
from werkzeug.utils import secure_filename
from sqlalchemy import desc
import uuid
from flask import render_template,send_file
from celery_app import score_resume

routes = Blueprint("routes", __name__)

from functools import wraps
from flask import abort

def role_required(required_role):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not oidc.user_loggedin:
                return redirect(url_for("login"))
            
            user_email = oidc.user_getfield("email")
            user = User.query.filter_by(email=user_email).first()

            if not user or user.role != required_role:
                abort(403)  # Forbidden

            return f(*args, **kwargs)
        return decorated_function
    return decorator

@routes.route("/")
def home():
    if oidc.user_loggedin:
        user_email = oidc.user_getfield("email")
        user = User.query.filter_by(email=user_email).first()
        if not user:
            return redirect(url_for("routes.choose_role"))
        
        session["user_id"] = user.id
        session["role"] = user.role

        return render_template("index.html", user=user)
    
    return render_template("login.html")

@routes.route("/choose-role")
@oidc.require_login
def choose_role():
    user_email = oidc.user_getfield("email")
    existing_user = User.query.filter_by(email=user_email).first()

    if not existing_user:
        role = "job_seeker"  # Default role
        new_user = User(email=user_email, role=role)
        db.session.add(new_user)
        db.session.commit()

    return redirect(url_for("routes.home"))

@routes.route("/dashboard", methods=["GET"])
@oidc.require_login
def dashboard():
    if oidc.user_loggedin:
        user_email = oidc.user_getfield("email")
        user = User.query.filter_by(email=user_email).first()
    if user.role == "recruiter":
        jobs = Job.query.filter_by(admin_id=user.id).order_by(desc(Job.posted_at)).all()  # Only recruiter’s jobs
    else:
        jobs = (
        db.session.query(Job)
        .outerjoin(Resume, (Job.id == Resume.job_id) & (Resume.user_id == session["user_id"]))
        .filter(Resume.id.is_(None))  # Exclude jobs where a resume entry exists for this user
        .order_by(desc(Job.posted_at))
        .all()
        ) # Job seekers see all jobs
    
    return render_template("dashboard.html", jobs=jobs,current_user=user)


ALLOWED_EXTENSIONS = {"pdf", "docx"}

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

@routes.route("/upload_resume/<int:job_id>", methods=["POST", "GET"])
def upload_resume(job_id):
    if request.method == "GET":
        if(Resume.query.filter_by(user_id=session["user_id"], job_id = job_id).first() is not None):
            return render_template("upload_resume.html", job_id=job_id, message="You Have Already Applied for this Job.", status="success")
        return render_template("upload_resume.html", job_id=job_id)

    job = Job.query.get(job_id)
    
    if not job:
        return render_template("upload_resume.html", job_id=job_id, message="Job not found!", status="error")

    if "file" not in request.files:
        return render_template("upload_resume.html", job_id=job_id, message="No file uploaded.", status="error")

    file = request.files["file"]
    print("entered")
    if file.filename == "":
        return render_template("upload_resume.html", job_id=job_id, message="No file selected.", status="error")

    if not allowed_file(file.filename):
        return render_template("upload_resume.html", job_id=job_id, message="Invalid file type. Only PDF and DOCX allowed.", status="error")

    try:
        # Generate a unique filename
        filename = secure_filename(file.filename.split(".")[0] + str(uuid.uuid4().hex) + ".pdf")
        filepath = os.path.join(Config.UPLOAD_FOLDER, filename)
        file.save(filepath)

        # Store resume in database
        resume = Resume(user_id=session["user_id"], filename=filename, file_path=filepath, job_id=job_id)
        db.session.add(resume)
        db.session.commit()

        job_data: Job = db.session.query(Job).filter(Job.id == job_id).first()

        score_resume.apply_async((resume.id, job_data.description ,  resume.file_path), countdown=10)
        return render_template("upload_resume.html", job_id=job_id, message="Resume uploaded successfully!", status="success")
    except Exception as e:
        print("error :", e)
        return render_template("upload_resume.html", job_id=job_id, message=f"An error occurred: {str(e)}", status="error")

@routes.route("/view_resumes/<int:job_id>")
def view_resumes(job_id):
    job = Job.query.get(job_id)
    if not job or job.admin_id != session["user_id"]:
        return "Unauthorized", 403

    resumes = (
        db.session.query(Resume)
        .join(User, Resume.user_id == User.id)  # Join with the User table
        .filter(Resume.job_id == job_id)       # Filter by job_id
        .add_columns(User.email)               # Include the email column from the User table
        .order_by(Resume.score.desc())         # Order by score in descending order
        .all()                                 # Fetch all results
    )

    return render_template("view_resumes.html", job=job, resumes=resumes)

@routes.route("/applied_jobs")
@role_required("job_seeker")
def applied_jobs():

    user_id = session["user_id"]

    # Fetch jobs where the user has already applied (exists in Resume table)
    applied_jobs = (
        db.session.query(Job)
        .join(Resume, Job.id == Resume.job_id)
        .filter(Resume.user_id == user_id)
        .all()
    )

    return render_template("applied_jobs.html", jobs=applied_jobs)


@routes.route("/post_job", methods=["POST","GET"])
@role_required("recruiter")
def post_job():
    if(request.method == "GET"):
        return render_template("postjob.html") 
    title = request.form.get("title")
    description = request.form.get("description")
    company = request.form.get("company")
    location = request.form.get("location")

    if not title or not description or not company or not location:
        return "All fields are required!", 400

    job = Job(title=title, description=description, company=company, location=location, admin_id=session["user_id"])
    db.session.add(job)
    db.session.commit()

    return redirect(url_for("routes.dashboard"))

@routes.route("/download_resume/<int:resume_id>")
def download_resume(resume_id):
    resume = Resume.query.get(resume_id)
    
    if not resume:
        abort(404, "Resume not found.")
    
    job = Job.query.get(resume.job_id)

    # Ensure only the job poster (admin) can download
    if not job or job.admin_id != session["user_id"]:
        abort(403, "Unauthorized")

    # Serve the resume file
    return send_file(resume.file_path, as_attachment=True)

@routes.route("/logout")
def logout():
    # Step 1: Clear the Flask session
    session.clear()

    # Step 2: Get the current ID token (if available)
    id_token = oidc.get_access_token()  # Or use oidc.get_refresh_token() if needed

    # Step 3: Define the OIDC provider's logout endpoint
    oidc_logout_url = "https://dev-12637801.okta.com/protocol/openid-connect/logout"

    # Step 4: Define the post-logout redirect URI (your home screen)
    post_logout_redirect_uri = request.url_root.rstrip("/") + url_for("routes.home")

    # Step 5: Construct the logout URL with required parameters
    logout_params = {
        "post_logout_redirect_uri": post_logout_redirect_uri,
        "id_token_hint": id_token,  # Pass the ID token to invalidate it
    }

    full_logout_url = f"{oidc_logout_url}?{'&'.join(f'{k}={v}' for k, v in logout_params.items())}"

    # Step 6: Redirect the user to the OIDC logout endpoint
    return redirect(full_logout_url)
    # return redirect(url_for("routes.home"))
