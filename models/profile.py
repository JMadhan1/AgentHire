"""
models/profile.py — User profile model storing all candidate information
"""

from datetime import datetime
from . import db


class Profile(db.Model):
    """
    Candidate profile model.
    Stores all information the AI agent needs to fill job applications.
    """

    __tablename__ = "profiles"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), unique=True, nullable=False)

    # Personal info
    full_name = db.Column(db.String(200), nullable=True)
    email_contact = db.Column(db.String(255), nullable=True)
    phone = db.Column(db.String(50), nullable=True)
    location = db.Column(db.String(200), nullable=True)

    # Professional info
    current_title = db.Column(db.String(200), nullable=True)
    experience_years = db.Column(db.Integer, nullable=True)
    desired_role = db.Column(db.String(200), nullable=True)
    skills = db.Column(db.Text, nullable=True)  # comma-separated
    salary_range = db.Column(db.String(100), nullable=True)

    # Online presence
    linkedin_url = db.Column(db.String(500), nullable=True)
    portfolio_url = db.Column(db.String(500), nullable=True)

    # Documents
    resume_path = db.Column(db.String(500), nullable=True)       # original filename (display only)
    resume_data = db.Column(db.LargeBinary, nullable=True)       # raw PDF bytes stored in DB
    cover_letter_template = db.Column(db.Text, nullable=True)

    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    @property
    def is_complete(self) -> bool:
        """Check if the minimum required fields are filled to apply for jobs."""
        required = [self.full_name, self.email_contact, self.phone]
        return all(field and field.strip() for field in required)

    @property
    def completeness_percentage(self) -> int:
        """Return profile completeness as a percentage (0-100)."""
        fields = [
            self.full_name,
            self.email_contact,
            self.phone,
            self.location,
            self.current_title,
            self.experience_years,
            self.desired_role,
            self.skills,
            self.linkedin_url,
            self.resume_path,
            self.cover_letter_template,
        ]
        filled = sum(1 for f in fields if f)
        return int((filled / len(fields)) * 100)

    def __repr__(self) -> str:
        return f"<Profile user_id={self.user_id} name={self.full_name}>"
