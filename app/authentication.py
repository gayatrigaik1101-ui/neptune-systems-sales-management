"""
Neptune Systems - Sales Management System
Authentication & Session Management Module
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
import os
from typing import Any, Dict, List, Optional
import bcrypt
import streamlit as st

from app.config import config
from app.utils import logger, audit_sys_logger


@dataclass
class User:
    """Represents an authenticated user in Neptune Systems."""
    username: str
    display_name: str
    email: str
    role: str
    password_hash: str
    is_active: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "username": self.username,
            "display_name": self.display_name,
            "email": self.email,
            "role": self.role,
            "password_hash": self.password_hash,
            "is_active": self.is_active,
        }


class AuthManager:
    """Manages user authentication, password verification, and authorization allowlists."""

    def __init__(self) -> None:
        self._users: Dict[str, User] = {}
        self._load_users()

    def _load_users(self) -> None:
        """Loads users from settings and environment overrides."""
        raw_users = config.authorized_users
        for u in raw_users:
            user = User(
                username=u.get("username", "").lower(),
                display_name=u.get("display_name", ""),
                email=u.get("email", "").lower(),
                role=u.get("role", "viewer"),
                password_hash=u.get("password_hash", ""),
                is_active=u.get("is_active", True),
            )
            # Index by username and email
            self._users[user.username] = user
            if user.email:
                self._users[user.email] = user

        # Apply environment overrides for Sagar Sir and Tushar Sir emails if provided
        sagar_env_email = os.getenv("SAGAR_SIR_EMAIL")
        if sagar_env_email and "sagar" in self._users:
            self._users["sagar"].email = sagar_env_email.lower()
            self._users[sagar_env_email.lower()] = self._users["sagar"]

        tushar_env_email = os.getenv("TUSHAR_SIR_EMAIL")
        if tushar_env_email and "tushar" in self._users:
            self._users["tushar"].email = tushar_env_email.lower()
            self._users[tushar_env_email.lower()] = self._users["tushar"]

    @property
    def authorized_emails(self) -> List[str]:
        """Returns the list of authorized emails."""
        return list(set(u.email for u in self._users.values() if u.is_active and u.email))

    def is_email_authorized(self, email: str) -> bool:
        """Verifies if an email is in the authorized allowlist."""
        if not email:
            return False
        return email.strip().lower() in self.authorized_emails

    @staticmethod
    def hash_password(plain_password: str) -> str:
        """Hashes a plaintext password using bcrypt."""
        salt = bcrypt.gensalt(rounds=12)
        return bcrypt.hashpw(plain_password.encode("utf-8"), salt).decode("utf-8")

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verifies a plaintext password against a bcrypt hash."""
        if not plain_password or not hashed_password:
            return False
        try:
            return bcrypt.checkpw(
                plain_password.encode("utf-8"), hashed_password.encode("utf-8")
            )
        except Exception as e:
            logger.error(f"Password verification error: {e}")
            return False

    def authenticate(self, username_or_email: str, password: str) -> Optional[User]:
        """
        Authenticates a user by username or email and plaintext password.
        Validates against both password hash and the authorized allowlist.
        """
        identifier = username_or_email.strip().lower()
        user = self._users.get(identifier)

        if not user:
            logger.warning(f"Failed login attempt for unknown user: '{identifier}'")
            return None

        if not user.is_active:
            logger.warning(f"Login attempt for inactive user: '{identifier}'")
            return None

        # Verify email allowlist strictly
        if not self.is_email_authorized(user.email):
            logger.warning(f"User '{identifier}' rejected: Email '{user.email}' not in authorized allowlist.")
            return None

        # Verify password hash
        if not self.verify_password(password, user.password_hash):
            logger.warning(f"Failed login attempt for user: '{identifier}' (invalid password)")
            return None

        logger.info(f"User authenticated successfully: {user.display_name} ({user.email})")
        audit_sys_logger.info(f"AUTH_SUCCESS | User: {user.display_name} | Email: {user.email} | Role: {user.role}")
        return user

    def update_user_email(self, username: str, new_email: str) -> bool:
        """Updates an authorized user's email address."""
        u = self._users.get(username.lower())
        if not u:
            return False
        old_email = u.email
        u.email = new_email.strip().lower()

        # Update in settings.json
        raw_users = config.authorized_users
        for entry in raw_users:
            if entry.get("username", "").lower() == username.lower():
                entry["email"] = u.email
        config.save()

        # Update lookup dictionary
        if old_email in self._users:
            del self._users[old_email]
        self._users[u.email] = u
        logger.info(f"Updated email for user '{username}' to '{new_email}'")
        return True


# Global auth manager instance
auth_manager = AuthManager()


# Streamlit Session Helpers
def init_session_state() -> None:
    """Initializes Streamlit session state keys if not already set."""
    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False
    if "user" not in st.session_state:
        st.session_state["user"] = None
    if "login_timestamp" not in st.session_state:
        st.session_state["login_timestamp"] = None
    if "active_nav" not in st.session_state:
        st.session_state["active_nav"] = "Overview"
    if "selected_entry_id" not in st.session_state:
        st.session_state["selected_entry_id"] = None


def is_authenticated() -> bool:
    """Checks whether the current session is authenticated and not expired."""
    if not st.session_state.get("authenticated", False):
        return False

    login_ts = st.session_state.get("login_timestamp")
    if not login_ts:
        return False

    timeout_minutes = config.get("app", {}).get("session_timeout_minutes", 120)
    if datetime.now() - login_ts > timedelta(minutes=timeout_minutes):
        logout_user()
        st.warning("Session has expired due to inactivity. Please log in again.")
        return False

    return True


def get_current_user() -> Optional[User]:
    """Retrieves the User object of the currently logged in user."""
    return st.session_state.get("user")


def login_user(user: User) -> None:
    """Sets session state for logged in user."""
    st.session_state["authenticated"] = True
    st.session_state["user"] = user
    st.session_state["login_timestamp"] = datetime.now()
    st.session_state["active_nav"] = "Overview"


def logout_user() -> None:
    """Clears authentication session state."""
    user = st.session_state.get("user")
    if user:
        audit_sys_logger.info(f"AUTH_LOGOUT | User: {user.display_name} | Email: {user.email}")
    st.session_state["authenticated"] = False
    st.session_state["user"] = None
    st.session_state["login_timestamp"] = None
    st.session_state["selected_entry_id"] = None
