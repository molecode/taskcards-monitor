"""Email notification module for TaskCards monitor."""

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Any

import yaml
from jinja2 import Template


class EmailConfig:
    """Email configuration from YAML file."""

    def __init__(self, config_path: Path | str):
        """Load email configuration from YAML file.

        Args:
            config_path: Path to the YAML configuration file
        """
        config_path = Path(config_path)
        if not config_path.exists():
            raise FileNotFoundError(f"Email config file not found: {config_path}")

        with open(config_path) as f:
            config = yaml.safe_load(f)

        # SMTP settings
        smtp = config.get("smtp", {})
        self.smtp_host = smtp.get("host", "localhost")
        self.smtp_port = smtp.get("port", 587)
        self.use_tls = smtp.get("use_tls", True)
        self.username = smtp.get("username")
        self.password = smtp.get("password")

        # Email settings
        email = config.get("email", {})
        self.from_email = email.get("from")
        self.from_name = email.get("from_name", "TaskCards Monitor")
        self.to_emails = email.get("to", [])
        self.subject = email.get("subject", "TaskCards Board Changes Detected")

        # Validate required fields
        if not self.from_email:
            raise ValueError("Email 'from' address is required in config")
        if not self.to_emails:
            raise ValueError("At least one 'to' email address is required in config")


class EmailNotifier:
    """Send email notifications about board changes."""

    def __init__(self, config_path: Path | str):
        """Initialize email notifier with configuration.

        Args:
            config_path: Path to the YAML configuration file
        """
        # Load email configuration
        self.config = EmailConfig(config_path)

        # Load email template from file
        template_path = Path(__file__).parent / "email_template.html"
        with open(template_path) as f:
            template_content = f.read()
        self.template = Template(template_content)

    def notify_changes(
        self,
        board_id: str,
        board_name: str | None,
        timestamp: str,
        changes: dict[str, Any],
    ) -> bool:
        """Send email notification if there are changes (not on first run).

        Args:
            board_id: The board identifier
            board_name: The board name (optional)
            timestamp: Timestamp of the check
            changes: Changes dictionary from BoardMonitor.detect_changes()

        Returns:
            True if email was sent, False otherwise
        """
        # Don't send email on first run
        if changes["is_first_run"]:
            return False

        # Check if there are any changes
        has_changes = changes["cards_added"] or changes["cards_removed"] or changes["cards_changed"]

        if not has_changes:
            return False

        # Send the notification
        self.send_notification(
            board_id=board_id,
            board_name=board_name,
            timestamp=timestamp,
            added_cards=changes["cards_added"],
            removed_cards=changes["cards_removed"],
            changed_cards=changes["cards_changed"],
        )

        return True

    def send_notification(
        self,
        board_id: str,
        board_name: str | None,
        timestamp: str,
        added_cards: list[dict[str, Any]],
        removed_cards: list[dict[str, Any]],
        changed_cards: list[dict[str, Any]],
    ) -> None:
        """Send email notification about board changes.

        Args:
            board_id: The board identifier
            board_name: The board name (optional)
            timestamp: Timestamp of the check
            added_cards: List of added cards
            removed_cards: List of removed cards
            changed_cards: List of changed cards
        """
        # Prepare template context
        context = {
            "board_id": board_id,
            "board_name": board_name or board_id,
            "timestamp": timestamp,
            "added_cards": added_cards,
            "removed_cards": removed_cards,
            "changed_cards": changed_cards,
            "added_count": len(added_cards),
            "removed_count": len(removed_cards),
            "changed_count": len(changed_cards),
        }

        # Render subject with Jinja2 variables
        subject_template = Template(self.config.subject)
        subject = subject_template.render(**context)

        # Generate HTML content
        html_content = self.template.render(**context)

        # Create message
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = (
            f"{self.config.from_name} <{self.config.from_email}>"
            if self.config.from_name
            else self.config.from_email
        )
        # Use Bcc to hide recipients from each other
        msg["To"] = self.config.from_email
        msg["Bcc"] = ", ".join(self.config.to_emails)

        # Attach HTML content
        html_part = MIMEText(html_content, "html")
        msg.attach(html_part)

        # Send email
        self._send_email(msg)

    def _send_email(self, msg: MIMEMultipart) -> None:
        """Send email via SMTP.

        Args:
            msg: The email message to send
        """
        with smtplib.SMTP(self.config.smtp_host, self.config.smtp_port) as server:
            if self.config.use_tls:
                server.starttls()

            if self.config.username and self.config.password:
                server.login(self.config.username, self.config.password)

            server.send_message(msg)
