"""Tests for the email notifier module."""

from unittest.mock import MagicMock, patch

import pytest
import yaml

from taskcards_monitor.changes import CardAdded, ChangeSet
from taskcards_monitor.email_notifier import EmailConfig, EmailNotifier


def write_config(tmp_path, config: dict):
    """Write a YAML config file and return its path."""
    config_path = tmp_path / "email.yaml"
    config_path.write_text(yaml.safe_dump(config))
    return config_path


@pytest.fixture
def full_config(tmp_path):
    """A complete email configuration file."""
    return write_config(
        tmp_path,
        {
            "smtp": {
                "host": "smtp.example.com",
                "port": 465,
                "use_tls": True,
                "username": "user",
                "password": "pass",
            },
            "email": {
                "from": "monitor@example.com",
                "from_name": "Monitor",
                "to": ["a@example.com", "b@example.com"],
                "subject": "Changes on {{ board_name }}",
            },
        },
    )


@pytest.fixture
def minimal_config(tmp_path):
    """A minimal email configuration relying on defaults."""
    return write_config(
        tmp_path,
        {
            "email": {
                "from": "monitor@example.com",
                "to": ["a@example.com"],
            }
        },
    )


class TestEmailConfig:
    """Tests for EmailConfig class."""

    def test_load_full_config(self, full_config):
        """All settings are read from the YAML file."""
        config = EmailConfig(full_config)

        assert config.smtp_host == "smtp.example.com"
        assert config.smtp_port == 465
        assert config.use_tls is True
        assert config.username == "user"
        assert config.password == "pass"
        assert config.from_email == "monitor@example.com"
        assert config.from_name == "Monitor"
        assert config.to_emails == ["a@example.com", "b@example.com"]
        assert config.subject == "Changes on {{ board_name }}"

    def test_defaults(self, minimal_config):
        """Missing optional settings fall back to defaults."""
        config = EmailConfig(minimal_config)

        assert config.smtp_host == "localhost"
        assert config.smtp_port == 587
        assert config.use_tls is True
        assert config.username is None
        assert config.password is None
        assert config.from_name == "TaskCards Monitor"
        assert config.subject == "TaskCards Board Changes Detected"

    def test_missing_file(self, tmp_path):
        """A missing config file raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError, match="Email config file not found"):
            EmailConfig(tmp_path / "does-not-exist.yaml")

    def test_missing_from_address(self, tmp_path):
        """A config without 'from' address raises ValueError."""
        config_path = write_config(tmp_path, {"email": {"to": ["a@example.com"]}})

        with pytest.raises(ValueError, match="'from' address is required"):
            EmailConfig(config_path)

    def test_missing_to_addresses(self, tmp_path):
        """A config without 'to' addresses raises ValueError."""
        config_path = write_config(tmp_path, {"email": {"from": "monitor@example.com"}})

        with pytest.raises(ValueError, match="'to' email address is required"):
            EmailConfig(config_path)


class TestEmailNotifier:
    """Tests for EmailNotifier class."""

    @pytest.fixture
    def changeset(self):
        """A ChangeSet with one added card."""
        return ChangeSet(
            is_first_run=False,
            cards_added=[
                CardAdded(
                    id="card1",
                    title="New Task",
                    description="Description",
                    link="",
                    column="To Do",
                    attachments=[],
                )
            ],
            cards_removed=[],
            cards_modified=[],
        )

    def test_init_loads_template(self, full_config):
        """Notifier loads config and email template on init."""
        notifier = EmailNotifier(full_config)

        assert notifier.config.from_email == "monitor@example.com"
        assert notifier.template is not None

    def test_notify_changes_first_run(self, full_config, changeset):
        """No email is sent on first run."""
        notifier = EmailNotifier(full_config)
        changeset.is_first_run = True

        with patch.object(notifier, "send_notification") as mock_send:
            sent = notifier.notify_changes("board123", "Board", "2026-01-01", changeset)

        assert sent is False
        mock_send.assert_not_called()

    def test_notify_changes_no_changes(self, full_config):
        """No email is sent when there are no changes."""
        notifier = EmailNotifier(full_config)
        changes = ChangeSet(is_first_run=False)

        with patch.object(notifier, "send_notification") as mock_send:
            sent = notifier.notify_changes("board123", "Board", "2026-01-01", changes)

        assert sent is False
        mock_send.assert_not_called()

    def test_notify_changes_sends_email(self, full_config, changeset):
        """Email is sent when changes are detected."""
        notifier = EmailNotifier(full_config)

        with patch.object(notifier, "send_notification") as mock_send:
            sent = notifier.notify_changes(
                "board123", "Board", "2026-01-01", changeset, token="tok"
            )

        assert sent is True
        mock_send.assert_called_once_with(
            board_id="board123",
            board_name="Board",
            timestamp="2026-01-01",
            added_cards=changeset.cards_added,
            removed_cards=[],
            changed_cards=[],
            token="tok",
        )

    def test_send_notification_builds_message(self, full_config, changeset):
        """send_notification renders subject/body and sends the message."""
        notifier = EmailNotifier(full_config)

        with patch.object(notifier, "_send_email") as mock_send:
            notifier.send_notification(
                board_id="board123",
                board_name="My Board",
                timestamp="2026-01-01",
                added_cards=changeset.cards_added,
                removed_cards=[],
                changed_cards=[],
                token="tok",
            )

        mock_send.assert_called_once()
        msg = mock_send.call_args[0][0]
        assert msg["Subject"] == "Changes on My Board"
        assert msg["From"] == "Monitor <monitor@example.com>"
        assert msg["To"] == "monitor@example.com"
        assert msg["Bcc"] == "a@example.com, b@example.com"
        html = msg.get_payload()[0].get_payload(decode=True).decode()
        assert "board123" in html

    def test_send_notification_board_name_fallback(self, minimal_config):
        """Board id is used when no board name is available."""
        notifier = EmailNotifier(minimal_config)

        with patch.object(notifier, "_send_email") as mock_send:
            notifier.send_notification(
                board_id="board123",
                board_name=None,
                timestamp="2026-01-01",
                added_cards=[],
                removed_cards=[],
                changed_cards=[],
            )

        msg = mock_send.call_args[0][0]
        assert msg["Subject"] == "TaskCards Board Changes Detected"

    @patch("taskcards_monitor.email_notifier.smtplib.SMTP")
    def test_send_email_with_tls_and_login(self, mock_smtp_class, full_config):
        """SMTP send uses TLS and login when configured."""
        notifier = EmailNotifier(full_config)
        server = MagicMock()
        mock_smtp_class.return_value.__enter__.return_value = server

        msg = MagicMock()
        notifier._send_email(msg)

        mock_smtp_class.assert_called_once_with("smtp.example.com", 465)
        server.starttls.assert_called_once()
        server.login.assert_called_once_with("user", "pass")
        server.send_message.assert_called_once_with(msg)

    @patch("taskcards_monitor.email_notifier.smtplib.SMTP")
    def test_send_email_without_login(self, mock_smtp_class, tmp_path):
        """SMTP send skips TLS and login when not configured."""
        config_path = write_config(
            tmp_path,
            {
                "smtp": {"use_tls": False},
                "email": {"from": "monitor@example.com", "to": ["a@example.com"]},
            },
        )
        notifier = EmailNotifier(config_path)
        server = MagicMock()
        mock_smtp_class.return_value.__enter__.return_value = server

        msg = MagicMock()
        notifier._send_email(msg)

        server.starttls.assert_not_called()
        server.login.assert_not_called()
        server.send_message.assert_called_once_with(msg)
