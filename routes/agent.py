"""
routes/agent.py — Agent application blueprint (apply, stream SSE, dashboard, detail)
"""

import json
import logging
import os
import requests
from datetime import datetime, timedelta
from urllib.parse import urlparse
from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    jsonify,
    Response,
    current_app,
    stream_with_context,
    send_from_directory
)
from flask_login import login_required, current_user
from models import db, Profile, Application
from services.tinyfish_agent import TinyFishAgent
from services.email_service import send_application_notification

logger = logging.getLogger(__name__)

agent_bp = Blueprint("agent", __name__)


def _upload_resume_to_public_host(resume_path: str, upload_folder: str):
    """
    Upload a local resume file to a public host and return the URL.
    Tries multiple services in order: file.io, then transfer.sh.
    Used when running on localhost so the cloud TinyFish agent can access it.
    Returns the public URL string, or None if all uploads fail.
    """
    file_path = os.path.join(upload_folder, resume_path)
    if not os.path.isfile(file_path):
        logger.warning(f"Resume file not found on disk: {file_path}")
        return None

    filename = os.path.basename(resume_path)
    with open(file_path, "rb") as f:
        file_bytes = f.read()

    # 1. Try file.io (simple multipart upload, returns JSON with link)
    try:
        resp = requests.post(
            "https://file.io/?expires=1d",
            files={"file": (filename, file_bytes, "application/pdf")},
            timeout=30,
        )
        if resp.ok:
            data = resp.json()
            public_url = data.get("link") or data.get("url")
            if public_url:
                logger.info(f"Resume uploaded to file.io: {public_url}")
                return public_url
        logger.warning(f"file.io upload failed ({resp.status_code}): {resp.text[:200]}")
    except Exception as e:
        logger.warning(f"file.io upload error: {e}")

    # 2. Fallback: transfer.sh
    try:
        resp = requests.put(
            f"https://transfer.sh/{filename}",
            data=file_bytes,
            headers={"Content-Type": "application/pdf", "Max-Downloads": "50", "Max-Days": "1"},
            timeout=30,
        )
        if resp.ok:
            public_url = resp.text.strip()
            logger.info(f"Resume uploaded to transfer.sh: {public_url}")
            return public_url
        logger.warning(f"transfer.sh upload failed ({resp.status_code}): {resp.text[:200]}")
    except Exception as e:
        logger.warning(f"transfer.sh upload error: {e}")

    logger.warning("All resume upload attempts failed. TinyFish agent may not be able to attach the resume.")
    return None

MAX_URLS_PER_REQUEST = 5
RATE_LIMIT_COUNT = 10        # max applications
RATE_LIMIT_WINDOW = 3600     # per hour in seconds


@agent_bp.route("/static/uploads/<path:filename>")
def serve_upload(filename):
    """Serve uploaded resume files (needed for AI agent access)."""
    return send_from_directory(current_app.config["UPLOAD_FOLDER"], filename)


def is_valid_url(url: str) -> bool:
    """Basic URL validation."""
    try:
        result = urlparse(url)
        return all([result.scheme in ("http", "https"), result.netloc])
    except Exception:
        return False


def check_rate_limit(user_id: int) -> bool:
    """Return True if user is within rate limits, False if exceeded."""
    window_start = datetime.utcnow() - timedelta(seconds=RATE_LIMIT_WINDOW)
    recent_count = Application.query.filter(
        Application.user_id == user_id,
        Application.created_at >= window_start,
    ).count()
    return recent_count < RATE_LIMIT_COUNT


# ── Routes ─────────────────────────────────────────────────────────────────────

@agent_bp.route("/")
def index():
    """Landing page."""
    return render_template("index.html")


@agent_bp.route("/dashboard")
@login_required
def dashboard():
    """Application dashboard — shows all user applications."""
    applications = (
        Application.query.filter_by(user_id=current_user.id)
        .order_by(Application.created_at.desc())
        .all()
    )

    total       = len(applications)
    submitted   = sum(1 for a in applications if a.status == "submitted")
    in_progress = sum(1 for a in applications if a.status == "in_progress")
    week_start  = datetime.utcnow() - timedelta(days=7)
    this_week   = sum(1 for a in applications if a.created_at >= week_start)
    success_rate = round((submitted / total) * 100) if total > 0 else 0

    return render_template(
        "dashboard.html",
        applications=applications,
        stats={
            "total":        total,
            "submitted":    submitted,
            "in_progress":  in_progress,
            "this_week":    this_week,
            "success_rate": success_rate,
        },
    )


@agent_bp.route("/apply", methods=["GET"])
@login_required
def apply_page():
    """Render the apply page (GET)."""
    profile = Profile.query.filter_by(user_id=current_user.id).first()
    if not profile or not profile.is_complete:
        flash("Please complete your profile (name, email, phone) before applying.", "error")
        return redirect(url_for("profile.view_profile"))
    return render_template("apply.html", profile=profile)


@agent_bp.route("/apply", methods=["POST"])
@login_required
def apply_submit():
    """
    Accept job URLs and create Application records.
    Returns JSON: { application_ids: [id, ...] }
    """
    profile = Profile.query.filter_by(user_id=current_user.id).first()
    data     = request.get_json(silent=True) or {}
    job_urls = data.get("job_urls", [])

    if not job_urls or not isinstance(job_urls, list):
        return jsonify({"error": "Please provide at least one job URL."}), 400

    if len(job_urls) > MAX_URLS_PER_REQUEST:
        return jsonify({"error": f"Maximum {MAX_URLS_PER_REQUEST} URLs per request."}), 400

    valid_urls = []
    for url in job_urls:
        url = url.strip()
        if not url:
            continue
        if not is_valid_url(url):
            return jsonify({"error": f"Invalid URL: {url}"}), 400
        valid_urls.append(url)

    if not valid_urls:
        return jsonify({"error": "No valid URLs provided."}), 400

    if not check_rate_limit(current_user.id):
        return jsonify({"error": "Rate limit exceeded. Max 10 applications per hour."}), 429

    application_ids = []
    try:
        for url in valid_urls:
            app_record = Application(
                user_id=current_user.id,
                job_url=url,
                status=Application.STATUS_PENDING,
                resume_path=profile.resume_path  # Snapshot the resume used for this batch
            )
            db.session.add(app_record)
            db.session.flush()
            application_ids.append(app_record.id)
        db.session.commit()
        logger.info(f"Created {len(application_ids)} applications for user_id={current_user.id}")
    except Exception as e:
        db.session.rollback()
        logger.exception(f"Error creating applications: {e}")
        return jsonify({"error": "Failed to create applications."}), 500

    return jsonify({"application_ids": application_ids})


@agent_bp.route("/apply/stream/<int:application_id>")
@login_required
def stream_application(application_id: int):
    """
    SSE endpoint — proxies TinyFish agent events to the browser in real time.

    Real TinyFish event types:
      STARTED → agent launched
      STREAMING_URL → live browser preview URL
      HEARTBEAT → keep-alive
      PROGRESS → step description
      COMPLETED → agent finished (resultJson contains outcome)
      ERROR → agent error
    """
    app_record = Application.query.filter_by(
        id=application_id, user_id=current_user.id
    ).first()

    if not app_record:
        def _not_found():
            yield 'data: {"type":"ERROR","error":"Application not found."}\n\n'
        return Response(stream_with_context(_not_found()), mimetype="text/event-stream")

    api_key = current_app.config.get("TINYFISH_API_KEY", "")
    if not api_key or api_key.startswith("your_"):
        def _no_key():
            yield 'data: {"type":"ERROR","error":"TinyFish API key not configured."}\n\n'
        app_record.status = Application.STATUS_FAILED
        app_record.error_msg = "TinyFish API key not configured."
        db.session.commit()
        return Response(stream_with_context(_no_key()), mimetype="text/event-stream")

    profile = Profile.query.filter_by(user_id=current_user.id).first()
    if not profile or not profile.is_complete:
        def _no_profile():
            yield 'data: {"type":"ERROR","error":"Profile incomplete."}\n\n'
        return Response(stream_with_context(_no_profile()), mimetype="text/event-stream")

    def generate():
        app_record.status = Application.STATUS_IN_PROGRESS
        db.session.commit()

        agent     = TinyFishAgent(api_key=api_key)
        log_lines = []
        completed = False
        base_url = request.url_root

        # Load resume bytes — prefer DB copy (works on Vercel), fall back to disk.
        resume_bytes = None
        resume_filename = "resume.pdf"
        if profile.resume_data:
            resume_bytes = bytes(profile.resume_data)
            resume_filename = os.path.basename(app_record.resume_path or profile.resume_path or "resume.pdf")
            logger.info(f"Resume loaded from DB: {resume_filename} ({len(resume_bytes)} bytes)")
        elif app_record.resume_path:
            resume_file_path = os.path.join(current_app.config["UPLOAD_FOLDER"], app_record.resume_path)
            if os.path.isfile(resume_file_path):
                with open(resume_file_path, "rb") as f:
                    resume_bytes = f.read()
                resume_filename = os.path.basename(app_record.resume_path)
                logger.info(f"Resume loaded from disk: {resume_filename} ({len(resume_bytes)} bytes)")
            else:
                logger.warning(f"Resume not in DB or disk: {resume_file_path}")

        try:
            for event in agent.apply_to_job(
                app_record.job_url,
                profile,
                base_url=base_url,
                resume_path=app_record.resume_path,
                resume_bytes=resume_bytes,
                resume_filename=resume_filename,
            ):
                event_json = json.dumps(event)
                log_lines.append(event_json)
                yield f"data: {event_json}\n\n"

                event_type = (event.get("type") or "").upper()

                # ── COMPLETED / COMPLETE ──────────────────────────────────────
                if event_type in ("COMPLETED", "COMPLETE"):
                    completed = True

                    raw = (
                        event.get("resultJson")
                        or event.get("result")
                        or event.get("output")
                        or {}
                    )
                    if isinstance(raw, str):
                        try: result = json.loads(raw)
                        except Exception: result = {}
                    else:
                        result = raw if isinstance(raw, dict) else {}

                    agent_status = (
                        result.get("status") or event.get("status") or "submitted"
                    ).lower()

                    if agent_status in ("submitted", "completed", "success", "done"):
                        app_record.status = Application.STATUS_SUBMITTED
                        app_record.error_msg = result.get("confirmation") or result.get("reason") or "Application submitted successfully."
                    else:
                        app_record.status = Application.STATUS_FAILED
                        app_record.error_msg = (
                            result.get("blockers") or result.get("reason") or result.get("message") or "Not confirmed."
                        )

                    app_record.company      = result.get("company") or event.get("company") or ""
                    app_record.role_title   = result.get("role")    or event.get("role")    or ""
                    app_record.completed_at = datetime.utcnow()
                    app_record.agent_log    = "\n".join(log_lines)
                    db.session.commit()
                    logger.info(f"Application {application_id} → {app_record.status} ({app_record.error_msg})")

                    # ── Send Email Notification ──────────────────────────────────
                    try:
                        send_application_notification(
                            to_email=profile.email_contact or current_user.email,
                            company=app_record.company,
                            role=app_record.role_title,
                            status=app_record.status,
                            confirmation=app_record.error_msg if app_record.status == 'failed' else result.get('confirmation')
                        )
                    except Exception as email_err:
                        logger.error(f"Failed to trigger email notification: {email_err}")

                # ── ERROR ─────────────────────────────────────────────────────
                elif event_type == "ERROR":
                    completed = True
                    app_record.status      = Application.STATUS_FAILED
                    app_record.error_msg   = event.get("error") or event.get("message") or "Agent error."
                    app_record.completed_at = datetime.utcnow()
                    app_record.agent_log   = "\n".join(log_lines)
                    db.session.commit()

                    # Send error notification
                    try:
                        send_application_notification(
                            to_email=profile.email_contact or current_user.email,
                            company=app_record.company or "Unknown",
                            role=app_record.role_title or "Position",
                            status="failed",
                            confirmation=app_record.error_msg
                        )
                    except Exception as email_err:
                        logger.error(f"Failed to trigger error email notification: {email_err}")

        except Exception as e:
            logger.exception(f"Stream error for application {application_id}: {e}")
            yield f'data: {{"type":"ERROR","error":{json.dumps(str(e))}}}\n\n'
            app_record.status      = Application.STATUS_FAILED
            app_record.error_msg   = str(e)
            app_record.completed_at = datetime.utcnow()
            app_record.agent_log   = "\n".join(log_lines)
            db.session.commit()

        finally:
            if not completed:
                # If we have some log lines, maybe we can figure out what happened
                last_event = {}
                if log_lines:
                    try: last_event = json.loads(log_lines[-1])
                    except: pass
                
                app_record.status      = Application.STATUS_FAILED
                app_record.error_msg   = f"Agent stream ended unexpectedly. Last event: {last_event.get('type', 'None')}"
                app_record.completed_at = datetime.utcnow()
                app_record.agent_log   = "\n".join(log_lines)
                db.session.commit()
                logger.warning(f"Application {application_id} ended without completion: {app_record.error_msg}")
                yield f'data: {{"type":"ERROR","error":"Agent stream ended unexpectedly."}}\n\n'

    resp = Response(stream_with_context(generate()), mimetype="text/event-stream")
    resp.headers["Cache-Control"]    = "no-cache"
    resp.headers["Connection"]       = "keep-alive"
    resp.headers["X-Accel-Buffering"] = "no"
    return resp


@agent_bp.route("/application/<int:app_id>")
@login_required
def application_detail(app_id: int):
    """Show detailed view for a single application."""
    app_record = Application.query.filter_by(
        id=app_id, user_id=current_user.id
    ).first_or_404()
    return render_template("application.html", application=app_record)


@agent_bp.route("/application/<int:app_id>/reapply", methods=["POST"])
@login_required
def reapply(app_id: int):
    """Create a new application for the same URL (re-apply)."""
    original = Application.query.filter_by(
        id=app_id, user_id=current_user.id
    ).first_or_404()

    if not check_rate_limit(current_user.id):
        flash("Rate limit exceeded. Try again later.", "error")
        return redirect(url_for("agent.application_detail", app_id=app_id))

    new_app = Application(
        user_id=current_user.id,
        job_url=original.job_url,
        status=Application.STATUS_PENDING,
    )
    db.session.add(new_app)
    db.session.commit()
    logger.info(f"Re-apply created: application_id={new_app.id} for url={original.job_url}")
    flash("New application created. Go to Apply page to launch it.", "success")
    return redirect(url_for("agent.apply_page"))
