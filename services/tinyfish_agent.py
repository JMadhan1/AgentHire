"""
services/tinyfish_agent.py — TinyFish Web Agent API integration

Handles all communication with the TinyFish autonomous browser agent API.
The agent navigates real career portals and fills out job applications.
"""

import base64
import json
import logging
import requests
from typing import Generator, Dict, Any, Optional

logger = logging.getLogger(__name__)


class TinyFishAgent:
    """
    Client for the TinyFish Web Agent API.

    The API streams real-time events via Server-Sent Events (SSE) as the
    browser agent navigates pages and fills out forms.
    """

    BASE_URL = "https://agent.tinyfish.ai/v1/automation/run-sse"

    def __init__(self, api_key: str):
        self.api_key = api_key

    def build_goal_prompt(self, profile, job_url: str, base_url: str = "", resume_path: Optional[str] = None, resume_public_url: Optional[str] = None) -> str:
        """
        Build a detailed natural language goal for the TinyFish agent.
        This prompt is the most critical part — quality determines success rate.
        """

        # Priority: explicit public URL > resume_path > profile.resume_path
        if resume_public_url:
            resume_url = resume_public_url
        else:
            final_resume = resume_path or (profile.resume_path if profile else None)
            resume_url = f"{base_url.rstrip('/')}/static/uploads/{final_resume}" if base_url and final_resume else None

        # Determine the resume instruction
        if resume_url:
            resume_instruction = f"""CRITICAL — RESUME UPLOAD REQUIRED:
The resume PDF is attached to this task as "{resume_url.split('/')[-1] if resume_url else 'resume.pdf'}".
Steps to upload it:
1. Scroll the full page to find any area labelled 'Resume', 'CV', 'Attach file', 'Upload', or a drag-and-drop zone.
2. Try each method below IN ORDER until one succeeds:
   METHOD A — Direct file input:
     - Find the <input type="file"> element (it may be hidden with display:none or opacity:0).
     - Use page.setInputFiles() or equivalent to attach the resume file directly to that input.
     - This works even on hidden inputs — do NOT skip hidden inputs.
   METHOD B — Reveal and click:
     - Run JS: document.querySelectorAll('input[type="file"]').forEach(el => el.style.display='block')
     - Then click the now-visible input and select the file.
   METHOD C — Drop zone simulation:
     - Find the drag-and-drop container element.
     - Use the DataTransfer API via JS to simulate dropping the file onto it.
3. After any successful upload, confirm the filename appears in the UI.
4. NEVER skip this step. If all methods fail, report exactly which element you found and why it failed."""
        else:
            resume_instruction = "If there is a resume upload field, mark it as 'skipped' in your report as no resume was provided for this run."

        # Build skills string
        skills_str = profile.skills if profile.skills else "Not specified"
        experience_str = f"{profile.experience_years} years" if profile.experience_years else "Not specified"
        location_str = profile.location if profile.location else "Not specified"
        linkedin_str = profile.linkedin_url if profile.linkedin_url else "Not provided"
        portfolio_str = profile.portfolio_url if profile.portfolio_url else "Not provided"
        current_title_str = profile.current_title if profile.current_title else "Professional"
        desired_role_str = profile.desired_role if profile.desired_role else "Open to opportunities"

        goal = f"""You are an autonomous AI job application agent. Your objective is to successfully apply to a job role. Complete EVERY mandatory field including screening questions and the resume upload.

CANDIDATE PROFILE:
- Name: {profile.full_name}
- Email: {profile.email_contact}
- Phone: {profile.phone}
- Location: {location_str}
- Title: {current_title_str}
- Exp: {experience_str}
- Skills: {skills_str}
- LinkedIn: {linkedin_str}
- Portfolio: {portfolio_str}

TARGET JOB: {job_url}

EXECUTION PLAN:

1. Navigate to the job URL and click the primary "Apply" button.

2. STANDARD FIELDS:
   - Fill every visible text input using the candidate data above.
   - Split "{profile.full_name}" into First / Last name fields as needed.
   - Use "{profile.email_contact}" for all email fields.
   - If a Cover Letter field is present, write 2-3 sentences about the candidate's interest using their skills: {skills_str}.

3. SCREENING / DROPDOWN QUESTIONS — CRITICAL:
   Many job forms use CUSTOM dropdown or radio components (not native <select>) that may lack standard attributes.
   For EVERY screening question on the page, follow this process:
   a. Read the question label text carefully.
   b. If it is a NATIVE <select>, use it directly.
   c. If it is a CUSTOM component (div/button-based dropdown, styled radio group, etc.):
      - Click the component to open it.
      - Wait for the options list to appear in the DOM.
      - Click the correct option text directly.
      - If clicking by UUID/ID fails, use JavaScript: find the element by its visible text using document.evaluate() or querySelectorAll, then dispatch a click event.
   d. Answers to common screening questions:
      - Work Authorization / Right to work: YES / Authorized
      - Visa Sponsorship required: NO
      - Are you 18+: YES
      - Willing to relocate: YES (if asked)
      - Any Yes/No about interest in the role: YES

4. {resume_instruction}

5. NAVIGATION:
   - After completing each section, click "Next", "Continue", or "Save & Continue".
   - Dismiss any cookie banners or popups that appear.
   - If a step shows validation errors, fix them before proceeding.

6. SUBMISSION:
   - Click the final "Submit Application" or "Submit" button.
   - Wait for a confirmation page or success message.

RULES:
- NEVER skip a mandatory field — fix validation errors before moving on.
- For any custom UI component you cannot interact with normally, use JavaScript via page.evaluate() to set its value or trigger the click.
- If you hit a CAPTCHA or mandatory login wall, report it as a BLOCKER immediately.
- Do not fabricate data not in the profile. Leave optional unknown fields blank.

REPORTING:
Return your final result as JSON:
{{
    "status": "submitted" | "failed" | "blocked",
    "company": "Company Name",
    "role": "Job Title",
    "resume_uploaded": true/false,
    "steps": ["brief list of what you did"],
    "blockers": "details of any issues",
    "confirmation": "success message text"
}}"""

        return goal

    def apply_to_job(
        self,
        job_url: str,
        profile,
        base_url: str = "",
        resume_path: Optional[str] = None,
        resume_public_url: Optional[str] = None,
        resume_bytes: Optional[bytes] = None,
        resume_filename: str = "resume.pdf",
    ) -> Generator[Dict[str, Any], None, None]:
        """
        Stream job application events from TinyFish API.
        resume_bytes: raw PDF bytes passed directly to the agent (no external hosting needed).
        """

        goal = self.build_goal_prompt(profile, job_url, base_url, resume_path=resume_path, resume_public_url=resume_public_url)
        logger.info(f"Starting TinyFish agent for URL: {job_url}")

        headers = {
            "X-API-Key": self.api_key,
            "Content-Type": "application/json",
            "Accept": "text/event-stream",
        }

        payload: Dict[str, Any] = {
            "url": job_url,
            "goal": goal,
            "browser_profile": "stealth",
        }

        # Attach the resume file directly so the agent has it locally — no external URL needed.
        if resume_bytes:
            payload["files"] = [
                {
                    "name": resume_filename,
                    "content": base64.b64encode(resume_bytes).decode("utf-8"),
                    "content_type": "application/pdf",
                }
            ]
            logger.info(f"Resume attached to payload: {resume_filename} ({len(resume_bytes)} bytes)")

        try:
            response = requests.post(
                self.BASE_URL,
                headers=headers,
                json=payload,
                stream=True,
                timeout=600,  # 10-minute timeout for complex forms
            )

            if not response.ok:
                error_body = ""
                try:
                    error_body = response.text[:500]
                except Exception:
                    pass
                logger.error(
                    f"TinyFish API error {response.status_code}: {error_body}"
                )
                yield {
                    "type": "ERROR",
                    "error": f"TinyFish API returned HTTP {response.status_code}: {error_body}",
                    "status": response.status_code,
                }
                return

            # Parse SSE stream line by line
            buffer = ""
            for raw_line in response.iter_lines(decode_unicode=True):
                if raw_line is None:
                    continue

                line = raw_line.strip()

                # SSE data line
                if line.startswith("data:"):
                    data_str = line[5:].strip()
                    if data_str == "[DONE]":
                        logger.info("TinyFish stream complete")
                        break
                    try:
                        event_data = json.loads(data_str)
                        logger.debug(f"SSE event: {event_data.get('type', 'unknown')}")
                        yield event_data
                    except json.JSONDecodeError:
                        # Non-JSON data line — yield as raw text event
                        yield {"type": "LOG", "message": data_str}

                # SSE event type line (e.g., "event: COMPLETE")
                elif line.startswith("event:"):
                    event_type = line[6:].strip()
                    logger.debug(f"SSE event type: {event_type}")

                # Empty line — SSE event boundary
                elif line == "":
                    continue

        except requests.exceptions.Timeout:
            logger.error(f"TinyFish API timeout for URL: {job_url}")
            yield {
                "type": "ERROR",
                "error": "TinyFish agent timed out after 5 minutes. The career portal may be slow or unresponsive.",
            }

        except requests.exceptions.ConnectionError as e:
            logger.error(f"TinyFish API connection error: {e}")
            yield {
                "type": "ERROR",
                "error": f"Could not connect to TinyFish API: {str(e)}",
            }

        except Exception as e:
            logger.exception(f"Unexpected error in TinyFish agent: {e}")
            yield {
                "type": "ERROR",
                "error": f"Unexpected error: {str(e)}",
            }
