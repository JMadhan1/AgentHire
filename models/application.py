"""
models/application.py — Job application tracking model
"""

from datetime import datetime
from . import db


class Application(db.Model):
    """
    Job application record.
    Tracks every application submitted by the AI agent.
    """

    __tablename__ = "applications"

    # Valid status values
    STATUS_PENDING = "pending"
    STATUS_IN_PROGRESS = "in_progress"
    STATUS_SUBMITTED = "submitted"
    STATUS_FAILED = "failed"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    # Job info (URL is required; company + role filled by agent)
    job_url = db.Column(db.String(1000), nullable=False)
    company = db.Column(db.String(300), nullable=True)
    role_title = db.Column(db.String(300), nullable=True)
    resume_path = db.Column(db.String(500), nullable=True)  # Path to the resume used for this app

    # Status tracking
    status = db.Column(db.String(50), default=STATUS_PENDING, nullable=False)
    agent_log = db.Column(db.Text, nullable=True)        # Full SSE log from TinyFish
    error_msg = db.Column(db.Text, nullable=True)        # Error message if failed

    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime, nullable=True)

    def append_log(self, line: str) -> None:
        """Append a line to the agent log."""
        if self.agent_log:
            self.agent_log += "\n" + line
        else:
            self.agent_log = line

    def __repr__(self) -> str:
        return f"<Application id={self.id} status={self.status} url={self.job_url[:50]}>"
