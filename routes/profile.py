"""
routes/profile.py — Profile management blueprint (view, update, resume upload)
"""

import os
import logging
from datetime import datetime
from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    jsonify,
    current_app,
)
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from models import db, Profile

logger = logging.getLogger(__name__)

profile_bp = Blueprint("profile", __name__)

ALLOWED_EXTENSIONS = {"pdf"}


def allowed_file(filename: str) -> bool:
    """Check if the uploaded file has an allowed extension."""
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def validate_pdf_signature(file_stream) -> bool:
    """Verify the file starts with the PDF magic bytes."""
    header = file_stream.read(4)
    file_stream.seek(0)
    return header == b"%PDF"


@profile_bp.route("/profile", methods=["GET", "POST"])
@login_required
def view_profile():
    """View and update the user's candidate profile."""

    # Load or create profile
    profile = Profile.query.filter_by(user_id=current_user.id).first()
    if not profile:
        profile = Profile(user_id=current_user.id)

    if request.method == "POST":
        # Read all form fields
        profile.full_name = request.form.get("full_name", "").strip()
        profile.email_contact = request.form.get("email_contact", "").strip()
        profile.phone = request.form.get("phone", "").strip()
        profile.location = request.form.get("location", "").strip()
        profile.current_title = request.form.get("current_title", "").strip()
        profile.desired_role = request.form.get("desired_role", "").strip()
        profile.skills = request.form.get("skills", "").strip()
        profile.salary_range = request.form.get("salary_range", "").strip()
        profile.linkedin_url = request.form.get("linkedin_url", "").strip()
        profile.portfolio_url = request.form.get("portfolio_url", "").strip()
        profile.cover_letter_template = request.form.get("cover_letter_template", "").strip()

        # Parse experience years
        exp_str = request.form.get("experience_years", "").strip()
        if exp_str.isdigit():
            profile.experience_years = int(exp_str)
        elif exp_str == "":
            profile.experience_years = None

        # Validate required fields
        errors = []
        if not profile.full_name:
            errors.append("Full name is required.")
        if not profile.email_contact:
            errors.append("Contact email is required.")
        if not profile.phone:
            errors.append("Phone number is required.")

        if errors:
            for error in errors:
                flash(error, "error")
            db.session.add(profile)
            return render_template("profile.html", profile=profile)

        try:
            profile.updated_at = datetime.utcnow()
            db.session.add(profile)
            db.session.commit()
            logger.info(f"Profile updated for user_id={current_user.id}")
            flash("Profile saved successfully!", "success")
        except Exception as e:
            db.session.rollback()
            logger.exception(f"Error saving profile: {e}")
            flash("Failed to save profile. Please try again.", "error")

        return redirect(url_for("profile.view_profile"))

    return render_template("profile.html", profile=profile)


@profile_bp.route("/profile/resume", methods=["POST"])
@login_required
def upload_resume():
    """
    Handle resume PDF upload via AJAX.

    After saving the file, parses it with resume_parser and returns
    extracted profile fields so the frontend can auto-fill the form.
    """

    if "resume" not in request.files:
        return jsonify({"success": False, "error": "No file provided."}), 400

    file = request.files["resume"]

    if file.filename == "":
        return jsonify({"success": False, "error": "No file selected."}), 400

    if not allowed_file(file.filename):
        return jsonify({"success": False, "error": "Only PDF files are allowed."}), 400

    # Validate actual PDF content (not just extension)
    if not validate_pdf_signature(file.stream):
        return jsonify({"success": False, "error": "Invalid file. Please upload a real PDF."}), 400

    # Read all bytes now — needed for both saving and parsing
    pdf_bytes = file.read()

    # Build safe filename
    original_name = secure_filename(file.filename)
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    filename = f"{current_user.id}_{timestamp}_{original_name}"

    upload_folder = current_app.config["UPLOAD_FOLDER"]
    os.makedirs(upload_folder, exist_ok=True)
    save_path = os.path.join(upload_folder, filename)

    try:
        with open(save_path, "wb") as f:
            f.write(pdf_bytes)
    except Exception as e:
        logger.exception(f"Error saving resume file: {e}")
        return jsonify({"success": False, "error": "Failed to save file."}), 500

    # ── Parse resume for auto-fill ───────────────────────────────────────────
    parsed_fields = {}
    parse_error = None
    try:
        from services.resume_parser import parse_resume_bytes
        parsed_fields = parse_resume_bytes(pdf_bytes)
        logger.info(
            f"Resume parsed for user_id={current_user.id}: "
            f"{list(parsed_fields.keys())}"
        )
    except Exception as e:
        parse_error = str(e)
        logger.warning(f"Resume parsing failed for user_id={current_user.id}: {e}")

    # ── Save resume path + auto-fill blank profile fields ────────────────────
    profile = Profile.query.filter_by(user_id=current_user.id).first()
    if not profile:
        profile = Profile(user_id=current_user.id)

    profile.resume_path = filename
    profile.updated_at = datetime.utcnow()

    # Only fill DB fields that are currently blank (don't clobber existing data)
    if parsed_fields:
        _fill_if_blank(profile, "full_name",             parsed_fields)
        _fill_if_blank(profile, "email_contact",         parsed_fields)
        _fill_if_blank(profile, "phone",                 parsed_fields)
        _fill_if_blank(profile, "location",              parsed_fields)
        _fill_if_blank(profile, "linkedin_url",          parsed_fields)
        _fill_if_blank(profile, "portfolio_url",         parsed_fields)
        _fill_if_blank(profile, "current_title",         parsed_fields)
        _fill_if_blank(profile, "skills",                parsed_fields)
        _fill_if_blank(profile, "cover_letter_template", parsed_fields)
        if not profile.experience_years and parsed_fields.get("experience_years"):
            profile.experience_years = parsed_fields["experience_years"]

    try:
        db.session.add(profile)
        db.session.commit()
        logger.info(f"Resume saved for user_id={current_user.id}: {filename}")
    except Exception as e:
        db.session.rollback()
        logger.exception(f"Error saving profile after resume upload: {e}")
        return jsonify({"success": False, "error": "File saved but DB update failed."}), 500

    return jsonify({
        "success": True,
        "filename": original_name,
        "parsed": parsed_fields,
        "parse_error": parse_error,
        "fields_found": list(parsed_fields.keys()),
    })


def _fill_if_blank(profile, field: str, data: dict) -> None:
    """Set profile.field from data only if the field is currently empty."""
    if not getattr(profile, field, None) and data.get(field):
        setattr(profile, field, data[field])
