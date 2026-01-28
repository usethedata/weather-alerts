"""
Tests for the EmailAction class.

These tests focus on the template substitution logic, which doesn't require
actually sending emails. We use "mocking" to replace the SMTP connection
with a fake that records what would have been sent.

=== MOCKING EXPLAINED ===

When testing code that has external dependencies (network, files, databases),
we "mock" those dependencies - replace them with fake versions that:
1. Don't actually connect to external services
2. Let us verify our code called them correctly
3. Let us simulate different responses (success, failure, etc.)

The @patch decorator replaces a class/function with a "Mock" object during the test.
After the test, the original is restored automatically.
"""

import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from actions.email import EmailAction


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def email_config():
    """Sample email configuration for testing."""
    return {
        'smtp_host': 'smtp.example.com',
        'smtp_port': 465,
        'use_ssl': True,
        'username': 'test@example.com',
        'password': 'testpassword',
        'from_address': 'alerts@example.com',
        'to_addresses': ['recipient@example.com']
    }


@pytest.fixture
def email_action(email_config):
    """Create an EmailAction instance for testing."""
    return EmailAction(email_config)


# =============================================================================
# TESTS FOR template substitution
# =============================================================================

class TestTemplateSubstitution:
    """
    Tests for the _substitute_template method.

    This is "pure" logic - no external dependencies - so it's easy to test directly.
    """

    def test_simple_substitution(self, email_action):
        """Test basic variable substitution."""
        template = "The temperature is {temperature}°F"
        context = {'temperature': 28}

        result = email_action._substitute_template(template, context)

        assert result == "The temperature is 28°F"

    def test_multiple_substitutions(self, email_action):
        """Test multiple variables in one template."""
        template = "High: {temp_max}°F, Low: {temp_min}°F on {date}"
        context = {
            'temp_max': 45,
            'temp_min': 28,
            'date': '2024-01-15'
        }

        result = email_action._substitute_template(template, context)

        assert result == "High: 45°F, Low: 28°F on 2024-01-15"

    def test_no_substitutions_needed(self, email_action):
        """Test template with no placeholders."""
        template = "This is a plain message with no variables."
        context = {'unused': 'value'}

        result = email_action._substitute_template(template, context)

        assert result == "This is a plain message with no variables."

    def test_empty_context(self, email_action):
        """Test template substitution with empty context."""
        template = "Temperature: {temperature}°F"
        context = {}

        result = email_action._substitute_template(template, context)

        # Placeholder remains since no value provided
        assert result == "Temperature: {temperature}°F"

    def test_multiline_template(self, email_action):
        """Test substitution in multiline templates (like email bodies)."""
        template = """Weather Alert!

Forecasted low: {temperature_min}°F
Date: {forecast_date}

Please take action."""

        context = {
            'temperature_min': 28,
            'forecast_date': '2024-01-15'
        }

        result = email_action._substitute_template(template, context)

        expected = """Weather Alert!

Forecasted low: 28°F
Date: 2024-01-15

Please take action."""

        assert result == expected

    def test_repeated_placeholder(self, email_action):
        """Test that the same placeholder can appear multiple times."""
        template = "Min temp is {temp}°F. Again, it's {temp}°F."
        context = {'temp': 28}

        result = email_action._substitute_template(template, context)

        assert result == "Min temp is 28°F. Again, it's 28°F."


# =============================================================================
# TESTS FOR email sending (with mocked SMTP)
# =============================================================================

class TestEmailSending:
    """
    Tests for the send() method.

    These tests mock the SMTP connection to verify:
    1. We connect with correct settings
    2. We send the right message content
    3. We handle errors gracefully
    """

    @patch('actions.email.smtplib.SMTP_SSL')
    def test_send_email_success(self, mock_smtp_class, email_action):
        """
        Test successful email sending.

        @patch replaces smtplib.SMTP_SSL with a mock. The mock is passed
        as the first parameter (mock_smtp_class) after 'self'.
        """
        # Arrange: Set up the mock SMTP server
        mock_server = MagicMock()
        mock_smtp_class.return_value = mock_server

        # Act: Send an email
        email_action.send(
            subject="Test Alert",
            body="This is a test.",
            context={}
        )

        # Assert: Verify SMTP was used correctly
        mock_smtp_class.assert_called_once_with(
            'smtp.example.com',
            465,
            timeout=10
        )
        mock_server.login.assert_called_once_with('test@example.com', 'testpassword')
        mock_server.send_message.assert_called_once()
        mock_server.quit.assert_called_once()

    @patch('actions.email.smtplib.SMTP_SSL')
    def test_send_email_with_context(self, mock_smtp_class, email_action):
        """Test that context variables are substituted in subject and body."""
        mock_server = MagicMock()
        mock_smtp_class.return_value = mock_server

        email_action.send(
            subject="Alert: {temperature} degrees",
            body="The temperature will be {temperature} degrees on {date}.",
            context={'temperature': 28, 'date': '2024-01-15'}
        )

        # Get the message that was sent
        sent_message = mock_server.send_message.call_args[0][0]

        assert sent_message['Subject'] == "Alert: 28 degrees"
        # The body is in the message payload (first part of multipart message)
        body_part = sent_message.get_payload(0).get_payload()
        assert "28 degrees" in body_part
        assert "2024-01-15" in body_part

    @patch('actions.email.smtplib.SMTP_SSL')
    def test_send_email_handles_smtp_error(self, mock_smtp_class, email_action, capsys):
        """
        Test that SMTP errors are handled gracefully.

        capsys is a pytest fixture that captures stdout/stderr,
        letting us verify error messages were printed.
        """
        import smtplib

        # Make the mock raise an SMTP error
        mock_smtp_class.side_effect = smtplib.SMTPException("Connection failed")

        # Should not raise an exception
        email_action.send(
            subject="Test",
            body="Test body",
            context={}
        )

        # Verify error was printed
        captured = capsys.readouterr()
        assert "Error sending email" in captured.out

    @patch('actions.email.smtplib.SMTP')
    def test_send_email_non_ssl(self, mock_smtp_class, email_config):
        """Test sending email without SSL (using STARTTLS)."""
        # Modify config to not use SSL
        email_config['use_ssl'] = False
        email_action = EmailAction(email_config)

        mock_server = MagicMock()
        mock_smtp_class.return_value = mock_server

        email_action.send(
            subject="Test",
            body="Test body",
            context={}
        )

        # Should use SMTP (not SMTP_SSL) and call starttls
        mock_smtp_class.assert_called_once()
        mock_server.starttls.assert_called_once()

    @patch('actions.email.smtplib.SMTP_SSL')
    def test_send_email_multiple_recipients(self, mock_smtp_class, email_config):
        """Test sending to multiple recipients."""
        email_config['to_addresses'] = ['one@example.com', 'two@example.com']
        email_action = EmailAction(email_config)

        mock_server = MagicMock()
        mock_smtp_class.return_value = mock_server

        email_action.send(
            subject="Test",
            body="Test body",
            context={}
        )

        sent_message = mock_server.send_message.call_args[0][0]
        assert sent_message['To'] == 'one@example.com, two@example.com'
