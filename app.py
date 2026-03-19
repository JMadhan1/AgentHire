"""
app.py — Flask application factory and entry point for AgentHire
"""

import logging
import os
from flask import Flask, render_template
from flask_login import LoginManager
from config import Config
from models import db, User


# ─── Logging Setup ────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("agenthire.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)


# ─── App Factory ──────────────────────────────────────────────────────────────

def create_app(config_class=Config) -> Flask:
    """Create and configure the Flask application."""

    app = Flask(__name__)
    app.config.from_object(config_class)

    # ── Extensions ──────────────────────────────────────────────────────────
    db.init_app(app)

    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    login_manager.login_message = "Please log in to access this page."
    login_manager.login_message_category = "info"

    @login_manager.user_loader
    def load_user(user_id: str):
        return User.query.get(int(user_id))

    # ── Blueprints ───────────────────────────────────────────────────────────
    from routes.auth import auth_bp
    from routes.profile import profile_bp
    from routes.agent import agent_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(profile_bp)
    app.register_blueprint(agent_bp)

    # ── Error Handlers ───────────────────────────────────────────────────────

    @app.errorhandler(404)
    def not_found(e):
        return render_template("errors/404.html"), 404

    @app.errorhandler(500)
    def server_error(e):
        logger.error(f"500 error: {e}")
        return render_template("errors/500.html"), 500

    @app.errorhandler(413)
    def request_too_large(e):
        from flask import flash, redirect, url_for
        flash("File too large. Maximum size is 16MB.", "error")
        return redirect(url_for("profile.view_profile"))

    # ── Database Init ────────────────────────────────────────────────────────
    with app.app_context():
        db.create_all()
        logger.info("Database tables created/verified.")

    logger.info("AgentHire application created successfully.")
    return app


# ─── Entry Point ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    app = create_app()
    logger.info("Starting AgentHire development server...")
    app.run(debug=True, host="0.0.0.0", port=5001)
