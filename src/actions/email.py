"""Email action for sending weather alerts."""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, Any, List


class EmailAction:
    """Send email alerts using SMTP."""

    def __init__(self, email_config: Dict[str, Any]):
        """Initialize email action.

        Args:
            email_config: Email configuration including SMTP settings
        """
        self.smtp_host = email_config['smtp_host']
        self.smtp_port = email_config['smtp_port']
        self.use_ssl = email_config.get('use_ssl', True)
        self.username = email_config['username']
        self.password = email_config['password']
        self.from_address = email_config['from_address']
        self.to_addresses = email_config['to_addresses']

    def send(self, subject: str, body: str, context: Dict[str, Any] = None):
        """Send an email alert.

        Args:
            subject: Email subject (supports template variables)
            body: Email body (supports template variables)
            context: Context dict for template variable substitution
        """
        if context is None:
            context = {}

        # Substitute template variables
        subject = self._substitute_template(subject, context)
        body = self._substitute_template(body, context)

        # Create message
        msg = MIMEMultipart()
        msg['From'] = self.from_address
        msg['To'] = ', '.join(self.to_addresses)
        msg['Subject'] = subject

        msg.attach(MIMEText(body, 'plain'))

        # Send email
        try:
            if self.use_ssl:
                server = smtplib.SMTP_SSL(self.smtp_host, self.smtp_port, timeout=10)
            else:
                server = smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=10)
                server.starttls()

            server.login(self.username, self.password)
            server.send_message(msg)
            server.quit()

            print(f"  Email sent successfully to {', '.join(self.to_addresses)}")

        except smtplib.SMTPException as e:
            print(f"  Error sending email: {e}")
        except Exception as e:
            print(f"  Unexpected error sending email: {e}")

    def _substitute_template(self, template: str, context: Dict[str, Any]) -> str:
        """Substitute template variables with context values.

        Args:
            template: Template string with {variable} placeholders
            context: Context dict with values

        Returns:
            Substituted string
        """
        result = template
        for key, value in context.items():
            placeholder = f"{{{key}}}"
            result = result.replace(placeholder, str(value))
        return result
