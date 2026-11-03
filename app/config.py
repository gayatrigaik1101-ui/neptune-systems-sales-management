"""
Neptune Systems - Sales Management System
Configuration Module
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional
from dotenv import load_dotenv

# Base paths
APP_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = APP_DIR.parent
CONFIG_DIR = PROJECT_ROOT / "config"
CREDENTIALS_DIR = PROJECT_ROOT / "credentials"
LOGS_DIR = PROJECT_ROOT / "logs"
BACKUPS_DIR = PROJECT_ROOT / "backups"
SETTINGS_FILE = CONFIG_DIR / "settings.json"
ENV_FILE = PROJECT_ROOT / ".env"

# Ensure runtime directories exist
for directory in [CONFIG_DIR, CREDENTIALS_DIR, LOGS_DIR, BACKUPS_DIR]:
    directory.mkdir(parents=True, exist_ok=True)

# Load environment variables
if ENV_FILE.exists():
    load_dotenv(ENV_FILE)
else:
    load_dotenv()


class AppConfig:
    """Manages application configuration combining settings.json and environment variables."""

    _instance: Optional["AppConfig"] = None
    _settings: Dict[str, Any] = {}

    def __new__(cls) -> "AppConfig":
        if cls._instance is None:
            cls._instance = super(AppConfig, cls).__new__(cls)
            cls._instance.load()
        return cls._instance

    def load(self) -> None:
        """Loads settings from settings.json and environment overrides."""
        if SETTINGS_FILE.exists():
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                self._settings = json.load(f)
        else:
            self._settings = self._get_default_settings()
            self.save()

        # Apply environment overrides if set
        self._apply_env_overrides()

    def _apply_env_overrides(self) -> None:
        """Applies environment variable and Streamlit secrets overrides to configuration."""
        gw = self._settings.setdefault("google_workspace", {})
        if os.getenv("GOOGLE_ACCOUNT"):
            gw["account_email"] = os.getenv("GOOGLE_ACCOUNT")
        if os.getenv("GOOGLE_SPREADSHEET_ID"):
            gw["spreadsheet_id"] = os.getenv("GOOGLE_SPREADSHEET_ID")
        if os.getenv("GOOGLE_SPREADSHEET_NAME"):
            gw["spreadsheet_name"] = os.getenv("GOOGLE_SPREADSHEET_NAME")
        if os.getenv("GOOGLE_FORM_ID"):
            gw["form_id"] = os.getenv("GOOGLE_FORM_ID")
        if os.getenv("GOOGLE_FORM_URL"):
            gw["form_url"] = os.getenv("GOOGLE_FORM_URL")
        if os.getenv("GOOGLE_AUTH_MODE"):
            gw["auth_mode"] = os.getenv("GOOGLE_AUTH_MODE")
        if os.getenv("GOOGLE_CREDENTIALS_FILE"):
            gw["service_account_path"] = os.getenv("GOOGLE_CREDENTIALS_FILE")

        # Streamlit Cloud secrets support
        try:
            import streamlit as st
            if hasattr(st, "secrets"):
                if "GOOGLE_ACCOUNT" in st.secrets:
                    gw["account_email"] = str(st.secrets["GOOGLE_ACCOUNT"])
                if "GOOGLE_SPREADSHEET_ID" in st.secrets:
                    gw["spreadsheet_id"] = str(st.secrets["GOOGLE_SPREADSHEET_ID"])
                if "GOOGLE_SPREADSHEET_NAME" in st.secrets:
                    gw["spreadsheet_name"] = str(st.secrets["GOOGLE_SPREADSHEET_NAME"])
                if "GOOGLE_FORM_ID" in st.secrets:
                    gw["form_id"] = str(st.secrets["GOOGLE_FORM_ID"])
                if "GOOGLE_FORM_URL" in st.secrets:
                    gw["form_url"] = str(st.secrets["GOOGLE_FORM_URL"])
                if "GOOGLE_AUTH_MODE" in st.secrets:
                    gw["auth_mode"] = str(st.secrets["GOOGLE_AUTH_MODE"])
        except Exception:
            pass

    def _get_default_settings(self) -> Dict[str, Any]:
        """Provides fallback default settings."""
        return {
            "app": {
                "name": "Neptune Systems – Sales Management Dashboard",
                "version": "1.0.0",
                "organization": "Neptune Systems",
                "session_timeout_minutes": 120,
                "pagination_page_size": 25,
                "concurrency_protection": True,
            },
            "google_workspace": {
                "account_email": "mallikarjungokule@gmail.com",
                "spreadsheet_name": "Neptune Systems – Sales Customer Database",
                "spreadsheet_id": "",
                "form_name": "Neptune Systems – Customer & Sales Entry Form",
                "form_id": "",
                "form_url": "",
                "auth_mode": "service_account",
                "service_account_path": "credentials/service_account.json",
                "oauth_client_path": "credentials/client_secret.json",
                "oauth_token_path": "credentials/token.json",
            },
            "sheets": {
                "sales_entries": {
                    "name": "Sales Entries",
                    "columns": [
                        "Entry ID",
                        "Date",
                        "Company Name",
                        "Customer Name",
                        "Company Address",
                        "Mobile Number",
                        "Email",
                        "Remark",
                        "Created At",
                        "Last Updated",
                        "Updated By",
                    ],
                },
                "edit_history": {
                    "name": "Edit History",
                    "columns": [
                        "History ID",
                        "Entry ID",
                        "Company Name",
                        "Field Changed",
                        "Previous Value",
                        "New Value",
                        "Updated By",
                        "Update Date & Time",
                    ],
                },
                "dashboard_data": {"name": "Dashboard Data"},
            },
            "authorized_users": [],
            "validation": {
                "phone_digits_required": 10,
                "date_format": "%d-%m-%Y",
                "timestamp_format": "%d-%m-%Y %H:%M:%S",
                "mandatory_fields": [
                    "Date",
                    "Company Name",
                    "Customer Name",
                    "Company Address",
                    "Mobile Number",
                    "Remark",
                ],
                "optional_fields": ["Email"],
            },
        }

    def save(self) -> None:
        """Saves current settings back to settings.json."""
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(self._settings, f, indent=2)

    def get(self, key: str, default: Any = None) -> Any:
        """Retrieves a configuration key."""
        return self._settings.get(key, default)

    @property
    def google_workspace(self) -> Dict[str, Any]:
        return self._settings.get("google_workspace", {})

    @property
    def sheets_config(self) -> Dict[str, Any]:
        return self._settings.get("sheets", {})

    @property
    def sales_entries_columns(self) -> List[str]:
        return self.sheets_config.get("sales_entries", {}).get("columns", [])

    @property
    def edit_history_columns(self) -> List[str]:
        return self.sheets_config.get("edit_history", {}).get("columns", [])

    @property
    def authorized_users(self) -> List[Dict[str, Any]]:
        return self._settings.get("authorized_users", [])

    @property
    def validation_rules(self) -> Dict[str, Any]:
        return self._settings.get("validation", {})

    def resolve_path(self, relative_path: str) -> Path:
        """Resolves path relative to PROJECT_ROOT if not already absolute."""
        p = Path(relative_path)
        if p.is_absolute():
            return p
        return PROJECT_ROOT / relative_path

    def update_google_resource_ids(
        self,
        spreadsheet_id: Optional[str] = None,
        form_id: Optional[str] = None,
        form_url: Optional[str] = None,
    ) -> None:
        """Updates Google Spreadsheet and Form IDs."""
        gw = self._settings.setdefault("google_workspace", {})
        if spreadsheet_id:
            gw["spreadsheet_id"] = spreadsheet_id
        if form_id:
            gw["form_id"] = form_id
        if form_url:
            gw["form_url"] = form_url
        self.save()


# Singleton instance
config = AppConfig()
