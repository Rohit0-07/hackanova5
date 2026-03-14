import os
import sys
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add the backend directory to the Python path
backend_path = Path(__file__).parent.parent / "backend"
sys.path.append(str(backend_path))

from app.services import email_service

# Mock data
SESSION_ID = "test-session-123"
TEST_EMAIL = "rohit15072005@gmail.com"
TEST_QUERY = "Neural Radiance Fields"
TEST_COUNT = 5


@pytest.fixture(autouse=True)
def clean_subscriptions():
    """Ensure subscriptions are empty before each test."""
    email_service.unregister_email(SESSION_ID)
    yield
    email_service.unregister_email(SESSION_ID)


def test_subscription_management():
    """Test registering, retrieving, and unregistering email subscriptions."""
    # Initially no email
    assert email_service.get_email_for_session(SESSION_ID) is None

    # Register
    email_service.register_email(SESSION_ID, TEST_EMAIL)
    assert email_service.get_email_for_session(SESSION_ID) == TEST_EMAIL

    # Unregister
    email_service.unregister_email(SESSION_ID)
    assert email_service.get_email_for_session(SESSION_ID) is None


@patch("resend.Emails.send")
def test_send_via_resend_logic(mock_resend):
    """Verify that if RESEND_API_KEY is set, it calls resend.Emails.send."""
    with patch("app.services.email_service.RESEND_API_KEY", "re_test_key"):
        # Set up subscription
        email_service.register_email(SESSION_ID, TEST_EMAIL)

        # Mock success response
        mock_resend.return_value = {"id": "resend-id-123"}

        # Act
        result = email_service.send_completion_email(SESSION_ID, TEST_QUERY, TEST_COUNT)

        # Assert
        assert result is True
        mock_resend.assert_called_once()
        # Verify it unregistered after sending
        assert email_service.get_email_for_session(SESSION_ID) is None


@patch("smtplib.SMTP")
def test_send_via_smtp_fallback(mock_smtp):
    """Verify SMTP fallback when Resend is unavailable."""
    # Ensure Resend is NOT configured
    with patch("app.services.email_service.RESEND_API_KEY", ""):
        # Mock SMTP credentials
        with (
            patch("app.services.email_service.SMTP_HOST", "smtp.test.com"),
            patch("app.services.email_service.SENDER_EMAIL", "sender@test.com"),
            patch("app.services.email_service.SENDER_PASS", "pass"),
        ):
            email_service.register_email(SESSION_ID, TEST_EMAIL)

            # Mock SMTP instance
            instance = mock_smtp.return_value.__enter__.return_value

            # Act
            result = email_service.send_completion_email(
                SESSION_ID, TEST_QUERY, TEST_COUNT
            )

            # Assert
            assert result is True
            instance.login.assert_called_once_with("sender@test.com", "pass")
            instance.sendmail.assert_called_once()
            assert email_service.get_email_for_session(SESSION_ID) is None


def test_no_provider_configured():
    """Verify it returns False if no email provider is configured."""
    with (
        patch("app.services.email_service.RESEND_API_KEY", ""),
        patch("app.services.email_service.SMTP_HOST", ""),
    ):
        email_service.register_email(SESSION_ID, TEST_EMAIL)
        result = email_service.send_completion_email(SESSION_ID, TEST_QUERY, TEST_COUNT)

        assert result is False
        # Should stay registered since it wasn't "sent"
        assert email_service.get_email_for_session(SESSION_ID) == TEST_EMAIL
