"""
services/resume_parser.py — PDF Resume Parser

Extracts text from a PDF resume and parses structured profile fields using
regular expressions and heuristics. No external AI API required.

Returns a dict matching the Profile model fields.
"""

import io
import re
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# ── Try importing pypdf ────────────────────────────────────────────────────────
try:
    from pypdf import PdfReader
    PYPDF_AVAILABLE = True
except ImportError:
    PYPDF_AVAILABLE = False
    logger.warning("pypdf not installed — resume parsing disabled. Run: pip install pypdf")


# ── Regex patterns ─────────────────────────────────────────────────────────────

# Email
EMAIL_RE = re.compile(
    r'\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b'
)

# Phone — handles +1 (555) 123-4567, 555.123.4567, +44 7700 900123, etc.
PHONE_RE = re.compile(
    r'(?:(?:\+|00)[1-9]\d{0,2}[\s\-.]?)?'        # country code
    r'(?:\(?\d{1,4}\)?[\s\-.]?)?'                  # area code
    r'\d{3,4}[\s\-.]?\d{3,4}[\s\-.]?\d{0,4}'      # number
)

# LinkedIn
LINKEDIN_RE = re.compile(
    r'(?:https?://)?(?:www\.)?linkedin\.com/in/[A-Za-z0-9_\-]+/?',
    re.IGNORECASE
)

# GitHub
GITHUB_RE = re.compile(
    r'(?:https?://)?(?:www\.)?github\.com/[A-Za-z0-9_\-]+/?',
    re.IGNORECASE
)

# Personal website / portfolio (not linkedin, github, etc.)
WEBSITE_RE = re.compile(
    r'https?://(?!(?:www\.)?(?:linkedin|github|twitter|facebook|instagram)\.)(?:[A-Za-z0-9\-]+\.)+[A-Za-z]{2,}(?:/[^\s]*)?',
    re.IGNORECASE
)

# Years of experience — "5 years", "5+ years", "over 5 years"
EXPERIENCE_RE = re.compile(
    r'(\d+)\+?\s*(?:years?|yrs?)\s*(?:of\s+)?(?:experience|exp\.?)?',
    re.IGNORECASE
)

# Location — "City, State" or "City, Country"
LOCATION_RE = re.compile(
    r'\b([A-Z][a-z]+(?:\s[A-Z][a-z]+)*),\s*'
    r'([A-Z]{2}|[A-Z][a-z]+(?:\s[A-Z][a-z]+)*)\b'
)

# Section headers used in resumes
SECTION_HEADERS = {
    'skills':      re.compile(r'^(?:technical\s+)?skills?|competencies|technologies|tools?|stack', re.IGNORECASE),
    'experience':  re.compile(r'^(?:work\s+)?experience|employment|career|history|positions?', re.IGNORECASE),
    'education':   re.compile(r'^education|academic|qualifications?|degrees?', re.IGNORECASE),
    'summary':     re.compile(r'^(?:professional\s+)?summary|profile|objective|about(?:\s+me)?', re.IGNORECASE),
}

# Known tech skills for extraction from body text
TECH_SKILLS_VOCAB = {
    # Languages
    'Python', 'JavaScript', 'TypeScript', 'Java', 'C++', 'C#', 'C', 'Go', 'Rust',
    'Ruby', 'PHP', 'Swift', 'Kotlin', 'Scala', 'R', 'MATLAB', 'Perl', 'Shell',
    'Bash', 'SQL', 'HTML', 'CSS', 'HTML5', 'CSS3', 'Dart', 'Elixir', 'Haskell',
    # Frontend
    'React', 'Vue', 'Angular', 'Next.js', 'Nuxt.js', 'Svelte', 'Redux',
    'Webpack', 'Vite', 'Tailwind', 'Bootstrap', 'jQuery', 'GraphQL',
    # Backend
    'Node.js', 'Express', 'Django', 'Flask', 'FastAPI', 'Spring', 'Rails',
    'Laravel', 'NestJS', 'Gin', 'Echo', 'Fiber', 'gRPC', 'REST', 'API',
    # Cloud & DevOps
    'AWS', 'Azure', 'GCP', 'Docker', 'Kubernetes', 'Terraform', 'Ansible',
    'Jenkins', 'GitHub Actions', 'CircleCI', 'TravisCI', 'CI/CD', 'Helm',
    'ArgoCD', 'Prometheus', 'Grafana', 'Datadog', 'Nginx', 'Apache',
    # Databases
    'PostgreSQL', 'MySQL', 'MongoDB', 'Redis', 'SQLite', 'Cassandra',
    'DynamoDB', 'Elasticsearch', 'Neo4j', 'InfluxDB', 'Firestore', 'Supabase',
    # AI/ML
    'TensorFlow', 'PyTorch', 'Keras', 'scikit-learn', 'pandas', 'NumPy',
    'OpenCV', 'Hugging Face', 'LangChain', 'LLM', 'RAG', 'BERT', 'GPT',
    # Mobile
    'iOS', 'Android', 'React Native', 'Flutter', 'SwiftUI', 'Jetpack Compose',
    # Data
    'Spark', 'Kafka', 'Airflow', 'dbt', 'Snowflake', 'BigQuery', 'Tableau',
    'Power BI', 'Looker', 'Databricks',
    # Testing
    'Jest', 'Pytest', 'Cypress', 'Selenium', 'JUnit', 'Mocha', 'Jasmine',
    # Misc
    'Git', 'Linux', 'Unix', 'Agile', 'Scrum', 'Jira', 'Figma', 'Microservices',
    'Serverless', 'WebSockets', 'OAuth', 'JWT', 'GraphQL',
}

# Common job titles — used to detect current title
TITLE_KEYWORDS = [
    'Engineer', 'Developer', 'Architect', 'Manager', 'Director', 'Lead',
    'Senior', 'Junior', 'Staff', 'Principal', 'VP', 'CTO', 'CEO', 'COO',
    'Analyst', 'Designer', 'Scientist', 'Researcher', 'Consultant',
    'Specialist', 'Administrator', 'Coordinator', 'Intern', 'Associate',
    'Head of', 'Chief', 'Officer', 'President', 'Founder', 'Co-founder',
]

TITLE_RE = re.compile(
    r'(?:' + '|'.join(re.escape(t) for t in TITLE_KEYWORDS) + r')'
    r'(?:\s+(?:Engineer|Developer|Architect|Manager|Designer|Scientist|Analyst|Lead|Officer|Director))*',
    re.IGNORECASE
)


# ── Main Parser Class ──────────────────────────────────────────────────────────

class ResumeParser:
    """
    Extracts structured profile data from a PDF resume.

    Usage:
        parser = ResumeParser(pdf_file_path_or_bytes)
        data = parser.parse()
    """

    def __init__(self, source):
        """
        Args:
            source: str path to PDF, bytes object, or file-like object.
        """
        self.source = source
        self.raw_text = ""
        self.lines = []

    def extract_text(self) -> str:
        """Extract all text from the PDF."""
        if not PYPDF_AVAILABLE:
            raise RuntimeError("pypdf is not installed. Run: pip install pypdf")

        try:
            if isinstance(self.source, (str, Path)):
                reader = PdfReader(str(self.source))
            elif isinstance(self.source, bytes):
                reader = PdfReader(io.BytesIO(self.source))
            else:
                reader = PdfReader(self.source)

            pages_text = []
            for page in reader.pages:
                text = page.extract_text() or ""
                pages_text.append(text)

            self.raw_text = "\n".join(pages_text)
            self.lines = [l.strip() for l in self.raw_text.splitlines() if l.strip()]
            logger.info(f"Extracted {len(self.raw_text)} chars from {len(reader.pages)} PDF page(s)")
            return self.raw_text

        except Exception as e:
            logger.exception(f"PDF text extraction failed: {e}")
            raise

    def parse(self) -> dict:
        """
        Parse resume text into a structured profile dict.

        Returns:
            dict with keys matching Profile model fields.
        """
        if not self.raw_text:
            self.extract_text()

        result = {
            "full_name":             self._extract_name(),
            "email_contact":         self._extract_email(),
            "phone":                 self._extract_phone(),
            "location":              self._extract_location(),
            "linkedin_url":          self._extract_linkedin(),
            "portfolio_url":         self._extract_portfolio(),
            "current_title":         self._extract_title(),
            "experience_years":      self._extract_experience_years(),
            "skills":                self._extract_skills(),
            "desired_role":          None,   # hard to infer reliably
            "salary_range":          None,
            "cover_letter_template": self._build_cover_letter(),
        }

        # Remove None/empty values
        result = {k: v for k, v in result.items() if v}
        logger.info(f"Resume parsed: {list(result.keys())}")
        return result

    # ── Field extractors ───────────────────────────────────────────────────

    def _extract_email(self) -> Optional[str]:
        match = EMAIL_RE.search(self.raw_text)
        return match.group(0).lower() if match else None

    def _extract_phone(self) -> Optional[str]:
        # Exclude months and years (4-digit numbers that look like years)
        for match in PHONE_RE.finditer(self.raw_text):
            candidate = match.group(0).strip()
            digits = re.sub(r'\D', '', candidate)
            if 7 <= len(digits) <= 15:  # valid phone length
                return candidate
        return None

    def _extract_linkedin(self) -> Optional[str]:
        match = LINKEDIN_RE.search(self.raw_text)
        if not match:
            return None
        url = match.group(0)
        if not url.startswith('http'):
            url = 'https://' + url
        return url.rstrip('/')

    def _extract_portfolio(self) -> Optional[str]:
        # Prefer github over generic website
        github = GITHUB_RE.search(self.raw_text)
        if github:
            url = github.group(0)
            if not url.startswith('http'):
                url = 'https://' + url
            return url.rstrip('/')

        # Generic website (not linkedin/github)
        website = WEBSITE_RE.search(self.raw_text)
        if website:
            return website.group(0).rstrip('/')
        return None

    def _extract_name(self) -> Optional[str]:
        """
        The candidate name is almost always on the first 1-3 lines of a resume.
        We look for a line that:
        - Has 2-4 words
        - Each word starts with a capital letter
        - Contains no numbers or special chars beyond hyphens/apostrophes
        - Is NOT an email or URL
        """
        name_re = re.compile(
            r"^[A-Z][a-z'\-]+(?:\s+[A-Z][a-z'\-]+){1,3}$"
        )
        for line in self.lines[:10]:  # check first 10 lines only
            line = line.strip()
            # Skip lines with email, numbers, or common resume section headers
            if EMAIL_RE.search(line):
                continue
            if re.search(r'\d', line):
                continue
            if any(line.lower().startswith(h) for h in [
                'summary', 'experience', 'education', 'skills', 'objective',
                'profile', 'contact', 'curriculum', 'resume', 'cv'
            ]):
                continue
            if name_re.match(line):
                return line
        return None

    def _extract_location(self) -> Optional[str]:
        """Extract city, state/country from resume."""
        # Check first 20 lines for address-like patterns
        for line in self.lines[:20]:
            match = LOCATION_RE.search(line)
            if match:
                # Reject if the match looks like a skill or tech term
                loc = match.group(0)
                if not any(skill.lower() in loc.lower() for skill in TECH_SKILLS_VOCAB):
                    return loc
        return None

    def _extract_title(self) -> Optional[str]:
        """
        Find the most likely current/recent job title.
        Usually appears near the top (first 20 lines) or after the name.
        """
        # Check early lines first (summary section often has title)
        for line in self.lines[:20]:
            match = TITLE_RE.search(line)
            if match:
                # Grab the matched segment and up to 5 surrounding words
                start = max(0, match.start() - 20)
                candidate = line[start:match.end() + 20].strip()
                # Clean up — remove trailing punctuation
                candidate = re.sub(r'[|•·,;]+$', '', candidate).strip()
                if 3 <= len(candidate) <= 80:
                    return candidate
        return None

    def _extract_experience_years(self) -> Optional[int]:
        """Extract total years of experience from text."""
        matches = list(EXPERIENCE_RE.finditer(self.raw_text))
        if not matches:
            return None

        # Return the largest number found (most likely total experience)
        years = [int(m.group(1)) for m in matches]
        best = max(y for y in years if 0 < y <= 50)
        return best if best else None

    def _extract_skills(self) -> Optional[str]:
        """
        Extract skills by:
        1. Finding a 'Skills' section and pulling lines from it
        2. Scanning the whole document for known tech vocabulary
        """
        extracted_skills = set()

        # Method 1: Find skills section
        in_skills_section = False
        skills_lines = []
        for line in self.lines:
            # Check if this line is a skills section header
            if SECTION_HEADERS['skills'].match(line) and len(line) < 60:
                in_skills_section = True
                continue
            # Stop at next section header
            if in_skills_section:
                is_new_section = any(
                    pat.match(line) and len(line) < 60
                    for key, pat in SECTION_HEADERS.items()
                )
                if is_new_section:
                    break
                skills_lines.append(line)

        # Parse skills lines — split by commas, bullets, pipes, newlines
        for line in skills_lines:
            parts = re.split(r'[,|•·\n]', line)
            for part in parts:
                part = part.strip().strip('·•-–').strip()
                if 2 <= len(part) <= 40 and not re.search(r'\d{4}', part):
                    extracted_skills.add(part)

        # Method 2: Scan for known tech vocab anywhere in the document
        for skill in TECH_SKILLS_VOCAB:
            # Use word boundary matching
            pattern = r'(?<![A-Za-z])' + re.escape(skill) + r'(?![A-Za-z])'
            if re.search(pattern, self.raw_text, re.IGNORECASE):
                extracted_skills.add(skill)

        if not extracted_skills:
            return None

        # Sort: known tech skills first, then others
        known = sorted([s for s in extracted_skills if s in TECH_SKILLS_VOCAB])
        other = sorted([s for s in extracted_skills if s not in TECH_SKILLS_VOCAB])

        all_skills = known + other
        return ', '.join(all_skills[:30])  # cap at 30 skills

    def _build_cover_letter(self) -> Optional[str]:
        """
        Build a default cover letter template using extracted data.
        """
        email = self._extract_email() or '{email}'
        name = self._extract_name() or 'I'
        title = self._extract_title() or 'professional'
        skills_raw = self._extract_skills()
        top_skills = ', '.join(skills_raw.split(', ')[:4]) if skills_raw else 'my technical skills'
        yoe = self._extract_experience_years()
        exp_str = f"{yoe} years of experience" if yoe else "extensive experience"

        return (
            f"I am excited to apply for this position. With {exp_str} as a {title}, "
            f"I bring strong expertise in {top_skills}. "
            f"I am confident I can make an immediate and meaningful impact on your team. "
            f"I would welcome the opportunity to discuss how my background aligns with your needs. "
            f"Please feel free to reach me at {email}."
        )


# ── Convenience function ───────────────────────────────────────────────────────

def parse_resume_file(file_path: str) -> dict:
    """
    Parse a resume PDF from a file path.
    Returns dict of parsed profile fields.
    """
    parser = ResumeParser(file_path)
    return parser.parse()


def parse_resume_bytes(pdf_bytes: bytes) -> dict:
    """
    Parse a resume PDF from raw bytes.
    Returns dict of parsed profile fields.
    """
    parser = ResumeParser(pdf_bytes)
    return parser.parse()
