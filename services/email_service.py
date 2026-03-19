
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask import current_app

logger = logging.getLogger(__name__)

def send_application_notification(to_email, company, role, status, confirmation=None):
    """
    Send an email notification to the user about their application status.
    """
    smtp_server = current_app.config.get("SMTP_SERVER")
    smtp_port = current_app.config.get("SMTP_PORT")
    smtp_user = current_app.config.get("SMTP_USER")
    smtp_password = current_app.config.get("SMTP_PASSWORD")

    if not all([smtp_server, smtp_port, smtp_user, smtp_password]):
        logger.warning("Email settings not fully configured. Skipping email notification.")
        return False

    subject = f"Job Application Update: {role} at {company}"
    
    if status == "submitted":
        status_text = "SUCCESSFULLY SUBMITTED"
        message_body = f"""
        Hello,

        Your AI agent has successfully submitted your application for:
        
        Company: {company}
        Position: {role}
        Status: {status_text}
        
        Confirmation Details: {confirmation or 'Application confirmed by agent.'}

        Log in to your AgentHire dashboard to see the full activity log.

        Best regards,
        AgentHire Team
        """
    else:
        status_text = "FAILED"
        message_body = f"""
        Hello,

        There was an issue with your AI agent application for:
        
        Company: {company}
        Position: {role}
        Status: {status_text}
        
        Reason: {confirmation or 'The agent encountered a blocker or error.'}

        You can review the full log and try re-applying from your dashboard.

        Best regards,
        AgentHire Team
        """

    try:
        msg = MIMEMultipart()
        msg['From'] = smtp_user
        msg['To'] = to_email
        msg['Subject'] = subject
        msg.attach(MIMEText(message_body, 'plain'))

        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.send_message(msg)
        
        logger.info(f"Notification email sent to {to_email} for {company}")
        return True
    except Exception as e:
        logger.exception(f"Failed to send email to {to_email}: {e}")
        return False
