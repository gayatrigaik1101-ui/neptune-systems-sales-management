"""
Unit Tests for Authentication & Authorization Allowlist
"""

import pytest
from app.authentication import AuthManager, User


def test_authenticate_sagar_sir():
    auth = AuthManager()
    user = auth.authenticate("sagar", "Sagar@Neptune2026")
    assert user is not None
    assert user.username == "sagar"
    assert user.display_name == "Sagar Sir"
    assert user.role == "sales_manager"
    assert user.email == "sagar@neptunesystems.com"


def test_authenticate_tushar_sir():
    auth = AuthManager()
    user = auth.authenticate("tushar", "Tushar@Neptune2026")
    assert user is not None
    assert user.username == "tushar"
    assert user.display_name == "Tushar Sir"
    assert user.role == "sales_manager"
    assert user.email == "tushar@neptunesystems.com"


def test_authenticate_by_email():
    auth = AuthManager()
    user = auth.authenticate("sagar@neptunesystems.com", "Sagar@Neptune2026")
    assert user is not None
    assert user.display_name == "Sagar Sir"


def test_reject_wrong_password():
    auth = AuthManager()
    user = auth.authenticate("sagar", "WrongPassword123")
    assert user is None


def test_reject_unauthorized_user():
    auth = AuthManager()
    user = auth.authenticate("intruder", "SomePassword123")
    assert user is None


def test_authorized_email_allowlist():
    auth = AuthManager()
    assert auth.is_email_authorized("sagar@neptunesystems.com") is True
    assert auth.is_email_authorized("tushar@neptunesystems.com") is True
    assert auth.is_email_authorized("unknown@external.com") is False
    assert auth.is_email_authorized("") is False
