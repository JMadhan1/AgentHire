"""
routes/auth.py — Authentication blueprint (register, login, logout)
"""

import logging
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from models import db, User

logger = logging.getLogger(__name__)

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    """User registration endpoint."""

    # Redirect if already logged in
    if current_user.is_authenticated:
        return redirect(url_for("agent.dashboard"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        # Server-side validation
        errors = []
        if not email:
            errors.append("Email is required.")
        if "@" not in email or "." not in email:
            errors.append("Please enter a valid email address.")
        if not password:
            errors.append("Password is required.")
        if len(password) < 6:
            errors.append("Password must be at least 6 characters.")
        if password != confirm_password:
            errors.append("Passwords do not match.")

        if errors:
            for error in errors:
                flash(error, "error")
            return render_template("register.html", email=email)

        # Check if email already registered
        existing = User.query.filter_by(email=email).first()
        if existing:
            flash("An account with this email already exists. Please log in.", "error")
            return render_template("register.html", email=email)

        # Create user
        try:
            user = User(email=email)
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            logger.info(f"New user registered: {email}")
            flash("Account created! Please log in.", "success")
            return redirect(url_for("auth.login"))
        except Exception as e:
            db.session.rollback()
            logger.exception(f"Error creating user: {e}")
            flash("Something went wrong. Please try again.", "error")

    return render_template("register.html")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    """User login endpoint."""

    if current_user.is_authenticated:
        return redirect(url_for("agent.dashboard"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not email or not password:
            flash("Email and password are required.", "error")
            return render_template("login.html", email=email)

        user = User.query.filter_by(email=email).first()

        if not user or not user.check_password(password):
            flash("Invalid email or password.", "error")
            logger.warning(f"Failed login attempt for: {email}")
            return render_template("login.html", email=email)

        login_user(user, remember=True)
        logger.info(f"User logged in: {email}")

        # Redirect to original destination or dashboard
        next_page = request.args.get("next")
        if next_page and next_page.startswith("/"):
            return redirect(next_page)
        return redirect(url_for("agent.dashboard"))

    return render_template("login.html")


@auth_bp.route("/logout")
@login_required
def logout():
    """Log out the current user."""
    email = current_user.email
    logout_user()
    logger.info(f"User logged out: {email}")
    flash("You have been logged out.", "info")
    return redirect(url_for("auth.login"))
