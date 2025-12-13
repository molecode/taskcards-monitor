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


# HTML email template
EMAIL_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
        }
        h1 {
            color: #2c3e50;
            border-bottom: 3px solid #3498db;
            padding-bottom: 10px;
        }
        h2 {
            color: #34495e;
            margin-top: 30px;
            margin-bottom: 15px;
        }
        .board-info {
            background-color: #f8f9fa;
            border-left: 4px solid #3498db;
            padding: 15px;
            margin: 20px 0;
        }
        .changes-section {
            margin: 25px 0;
        }
        .card-list {
            list-style: none;
            padding: 0;
        }
        .card-item {
            background: #fff;
            border: 1px solid #e1e4e8;
            border-radius: 6px;
            padding: 12px 15px;
            margin: 8px 0;
            box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        }
        .card-item.added {
            border-left: 4px solid #27ae60;
            background-color: #f0fdf4;
        }
        .card-item.removed {
            border-left: 4px solid #e74c3c;
            background-color: #fef2f2;
        }
        .card-item.changed {
            border-left: 4px solid #f39c12;
            background-color: #fffbeb;
        }
        .card-title {
            font-weight: 600;
            color: #1a202c;
            margin-bottom: 5px;
        }
        .card-description {
            color: #666;
            font-size: 14px;
            margin-top: 5px;
        }
        .change-detail {
            font-size: 13px;
            color: #666;
            font-style: italic;
        }
        .no-changes {
            color: #666;
            font-style: italic;
            padding: 10px;
        }
        .footer {
            margin-top: 40px;
            padding-top: 20px;
            border-top: 1px solid #e1e4e8;
            font-size: 12px;
            color: #999;
        }
        .summary {
            background-color: #eef2ff;
            border-radius: 6px;
            padding: 15px;
            margin: 20px 0;
        }
        .summary strong {
            color: #3730a3;
        }
    </style>
</head>
<body>
    <h1>📋 {{ board_name }}</h1>

    <div class="board-info">
        <strong>Board ID:</strong> {{ board_id }}<br>
        <strong>Board Name:</strong> {{ board_name }}<br>
        <strong>Checked at:</strong> {{ timestamp }}
    </div>

    <div class="summary">
        <strong>Summary:</strong>
        {{ added_count }} added, {{ removed_count }} removed, {{ changed_count }} changed
    </div>

    {% if added_cards %}
    <div class="changes-section">
        <h2>✅ Added Cards ({{ added_cards|length }})</h2>
        <ul class="card-list">
            {% for card in added_cards %}
            <li class="card-item added">
                <div class="card-title">{{ card.title }}</div>
                {% if card.description %}
                <div class="card-description">{{ card.description }}</div>
                {% endif %}
            </li>
            {% endfor %}
        </ul>
    </div>
    {% endif %}

    {% if removed_cards %}
    <div class="changes-section">
        <h2>❌ Removed Cards ({{ removed_cards|length }})</h2>
        <ul class="card-list">
            {% for card in removed_cards %}
            <li class="card-item removed">
                <div class="card-title">{{ card.title }}</div>
                {% if card.description %}
                <div class="card-description">{{ card.description }}</div>
                {% endif %}
            </li>
            {% endfor %}
        </ul>
    </div>
    {% endif %}

    {% if changed_cards %}
    <div class="changes-section">
        <h2>📝 Changed Cards ({{ changed_cards|length }})</h2>
        <ul class="card-list">
            {% for card in changed_cards %}
            <li class="card-item changed">
                <div class="card-title">{{ card.new_title or card.title }}</div>
                {% if card.title_changed %}
                <div class="change-detail">
                    Title: "{{ card.old_title }}" → "{{ card.new_title }}"
                </div>
                {% endif %}
                {% if card.description_changed %}
                <div class="change-detail">
                    Description changed
                </div>
                {% endif %}
            </li>
            {% endfor %}
        </ul>
    </div>
    {% endif %}

    {% if not added_cards and not removed_cards and not changed_cards %}
    <div class="no-changes">No changes detected.</div>
    {% endif %}

    <div class="footer">
        <p>This email was sent by <strong>taskcards-monitor</strong>, an open source TaskCards monitoring tool.</p>
        <p>
            🔗 <a href="https://github.com/molecode/taskcards-monitor" style="color: #3498db;">GitHub Repository</a> |
            🐛 <a href="https://github.com/molecode/taskcards-monitor/issues" style="color: #3498db;">Issue Tracker</a>
        </p>
        <p style="margin-top: 10px; font-size: 11px;">Board: {{ board_name }} ({{ board_id }})</p>
    </div>
</body>
</html>
"""


class EmailNotifier:
    """Send email notifications about board changes."""

    def __init__(self, config: EmailConfig):
        """Initialize email notifier with configuration.

        Args:
            config: EmailConfig instance with SMTP and email settings
        """
        self.config = config
        self.template = Template(EMAIL_TEMPLATE)

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
        msg["To"] = ", ".join(self.config.to_emails)

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
