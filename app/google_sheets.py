"""
Neptune Systems - Sales Management System
Google Sheets Central Database Connector
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import pandas as pd

from app.config import config, CREDENTIALS_DIR, BACKUPS_DIR
from app.utils import logger, clean_string, get_current_timestamp_str, generate_entry_id
from app.audit_logger import AuditHistoryItem

# Optional Google libraries import
try:
    import truststore
    truststore.inject_into_ssl()
except Exception:
    pass

try:
    import gspread
    from google.oauth2.service_account import Credentials as ServiceAccountCredentials
    from google.oauth2.credentials import Credentials as UserOAuthCredentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    GOOGLE_LIBS_AVAILABLE = True
except ImportError:
    GOOGLE_LIBS_AVAILABLE = False


# Google Sheets API Scopes
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]


class GoogleSheetsConnector:
    """
    Manages connections and CRUD operations for the central Google Spreadsheet:
    'Neptune Systems – Sales Customer Database'
    """

    def __init__(self) -> None:
        self.client: Optional[Any] = None
        self.spreadsheet: Optional[Any] = None
        self.is_connected: bool = False
        self.connection_mode: str = "disconnected"
        self.connection_message: str = "Not initialized"
        self.local_mirror_file = BACKUPS_DIR / "local_sales_database_mirror.json"
        self._init_local_mirror()
        self.connect()

    def _init_local_mirror(self) -> None:
        """Initializes local JSON mirror for offline development and backup persistence."""
        if not self.local_mirror_file.exists():
            initial_data = {
                "sales_entries": [],
                "edit_history": [],
                "metadata": {
                    "created_at": get_current_timestamp_str(),
                    "spreadsheet_name": config.google_workspace.get("spreadsheet_name"),
                }
            }
            with open(self.local_mirror_file, "w", encoding="utf-8") as f:
                json.dump(initial_data, f, indent=2)

    def connect(self) -> bool:
        """
        Attempts connection to Google Sheets using either Service Account or OAuth 2.0.
        Falls back cleanly to Local Persistent Mirror if credentials are not yet configured.
        """
        if not GOOGLE_LIBS_AVAILABLE:
            self.connection_mode = "local_mirror"
            self.connection_message = "Google API libraries not installed. Operating in Local Mirror mode."
            logger.warning(self.connection_message)
            return False

        gw_config = config.google_workspace
        auth_mode = gw_config.get("auth_mode", "service_account")
        sa_path = config.resolve_path(gw_config.get("service_account_path", "credentials/service_account.json"))
        oauth_client_path = config.resolve_path(gw_config.get("oauth_client_path", "credentials/client_secret.json"))
        oauth_token_path = config.resolve_path(gw_config.get("oauth_token_path", "credentials/token.json"))
        spreadsheet_name = gw_config.get("spreadsheet_name", "Neptune Systems – Sales Customer Database")
        spreadsheet_id = gw_config.get("spreadsheet_id", "").strip()

        # Robust check for double .json extension on Windows or any service account key in credentials
        if not sa_path.exists():
            for candidate in [CREDENTIALS_DIR / "service_account.json.json", *CREDENTIALS_DIR.glob("*.json*")]:
                if candidate.is_file() and candidate.name != "README.md":
                    try:
                        with open(candidate, "r", encoding="utf-8") as jf:
                            key_data = json.load(jf)
                            if key_data.get("type") == "service_account":
                                sa_path = candidate
                                break
                    except Exception:
                        continue

        try:
            # 1. Try Service Account Authentication (File or Streamlit Secrets)
            if auth_mode == "service_account" and sa_path.exists():
                logger.info(f"Authenticating via Google Service Account key at: {sa_path}")
                credentials = ServiceAccountCredentials.from_service_account_file(
                    str(sa_path), scopes=SCOPES
                )
                self.client = gspread.authorize(credentials)
                self.connection_mode = "service_account (file)"
            else:
                # Check for Streamlit Community Cloud secrets: st.secrets["gcp_service_account"]
                try:
                    import streamlit as st
                    if hasattr(st, "secrets") and "gcp_service_account" in st.secrets:
                        logger.info("Authenticating via Google Service Account in st.secrets")
                        sa_info = dict(st.secrets["gcp_service_account"])
                        credentials = ServiceAccountCredentials.from_service_account_info(
                            sa_info, scopes=SCOPES
                        )
                        self.client = gspread.authorize(credentials)
                        self.connection_mode = "service_account (st.secrets)"
                except Exception as se:
                    logger.debug(f"st.secrets check: {se}")

            # 2. Try User OAuth 2.0 Token Authentication (if client not authorized)
            if not self.client and (oauth_token_path.exists() or oauth_client_path.exists()):
                logger.info("Authenticating via Google OAuth 2.0 Client flow")
                creds = None
                if oauth_token_path.exists():
                    creds = UserOAuthCredentials.from_authorized_user_file(str(oauth_token_path), SCOPES)
                if not creds or not creds.valid:
                    if creds and creds.expired and creds.refresh_token:
                        creds.refresh(Request())
                    elif oauth_client_path.exists():
                        # Desktop OAuth flow
                        flow = InstalledAppFlow.from_client_secrets_file(str(oauth_client_path), SCOPES)
                        creds = flow.run_local_server(port=0)
                    if creds:
                        with open(oauth_token_path, "w", encoding="utf-8") as token_file:
                            token_file.write(creds.to_json())

                if creds and creds.valid:
                    self.client = gspread.authorize(creds)
                    self.connection_mode = "oauth"

            # Check if client was authorized
            if self.client:
                # Open by ID or Name
                if spreadsheet_id:
                    self.spreadsheet = self.client.open_by_key(spreadsheet_id)
                else:
                    self.spreadsheet = self.client.open(spreadsheet_name)

                self.is_connected = True
                self.connection_message = f"Connected to Google Spreadsheet: '{self.spreadsheet.title}' ({self.connection_mode})"
                logger.info(self.connection_message)
                self.ensure_worksheets_structure()
                return True

        except Exception as e:
            logger.warning(f"Google Sheets connection attempt could not reach remote sheet: {e}")
            self.connection_message = f"Live Google connection pending: {str(e)}"

        # Fallback to local mirror
        self.is_connected = False
        self.connection_mode = "local_mirror"
        if "Google connection pending" not in self.connection_message:
            self.connection_message = "Operating in Local Mirror Mode (Awaiting Google Workspace credentials setup)."
        logger.info(self.connection_message)
        return False

    def ensure_worksheets_structure(self) -> None:
        """
        Ensures all 3 required worksheets exist with exact column headers and formatting:
        Worksheet 1: Sales Entries
        Worksheet 2: Edit History
        Worksheet 3: Dashboard Data
        """
        if not self.spreadsheet:
            return

        expected_sheets = {
            config.sheets_config["sales_entries"]["name"]: config.sales_entries_columns,
            config.sheets_config["edit_history"]["name"]: config.edit_history_columns,
            config.sheets_config["dashboard_data"]["name"]: ["Key Metric", "Value", "Last Computed"],
        }

        existing_sheets = {ws.title: ws for ws in self.spreadsheet.worksheets()}

        for title, headers in expected_sheets.items():
            if title not in existing_sheets:
                logger.info(f"Creating missing worksheet in Google Sheets: '{title}'")
                ws = self.spreadsheet.add_worksheet(title=title, rows=1000, cols=len(headers) + 2)
                ws.append_row(headers)
                # Freeze top row
                ws.freeze(rows=1)
            else:
                ws = existing_sheets[title]
                first_row = ws.row_values(1)
                if not first_row:
                    ws.append_row(headers)
                    ws.freeze(rows=1)

    # =========================================================================
    # SALES ENTRIES OPERATIONS (WORKSHEET 1)
    # =========================================================================

    def fetch_all_sales_entries(self) -> List[Dict[str, Any]]:
        """
        Fetches all customer sales records from Worksheet 1: 'Sales Entries'.
        Returns a list of dictionaries with column names as keys.
        """
        if self.is_connected and self.spreadsheet:
            try:
                sheet_name = config.sheets_config["sales_entries"]["name"]
                ws = self.spreadsheet.worksheet(sheet_name)
                records = ws.get_all_records(default_blank="")
                # Sync to local backup mirror for redundancy
                self._save_to_local_mirror("sales_entries", records)
                return records
            except Exception as e:
                logger.error(f"Error reading live Google Sheets: {e}. Falling back to local mirror.")

        # Read from local mirror
        return self._read_from_local_mirror("sales_entries")

    def fetch_sales_entry_by_id(self, entry_id: str) -> Optional[Tuple[int, Dict[str, Any]]]:
        """
        Retrieves a single sales entry by its unique Entry ID.
        Returns tuple of (1-based row index in sheet, record dictionary) or None.
        """
        target_id = clean_string(entry_id).upper()
        if not target_id:
            return None

        entries = self.fetch_all_sales_entries()
        for idx, entry in enumerate(entries):
            # Row index in Google Sheets: +2 (+1 for 0-index, +1 for header row)
            if clean_string(entry.get("Entry ID", "")).upper() == target_id:
                return (idx + 2, entry)

        return None

    def insert_sales_entry(self, data: Dict[str, Any], created_by: str = "Sales Team") -> str:
        """
        Inserts a new sales customer submission into Worksheet 1 ('Sales Entries').
        Automatically assigns a unique Entry ID, timestamp, and sets Updated By.
        Never overwrites existing entries.
        Returns the generated Entry ID.
        """
        entry_id = data.get("Entry ID") or generate_entry_id("NEP")
        now_ts = get_current_timestamp_str()

        # Build row according to exact column schema
        columns = config.sales_entries_columns
        row_dict = {
            "Entry ID": entry_id,
            "Date": clean_string(data.get("Date", "")),
            "Company Name": clean_string(data.get("Company Name", "")),
            "Customer Name": clean_string(data.get("Customer Name", "")),
            "Company Address": clean_string(data.get("Company Address", "")),
            "Mobile Number": f"'{clean_string(data.get('Mobile Number', ''))}",  # Prefix with ' to force plain text in Sheets
            "Email": clean_string(data.get("Email", "")),
            "Remark": clean_string(data.get("Remark", "")),
            "Created At": data.get("Created At") or now_ts,
            "Last Updated": now_ts,
            "Updated By": created_by,
        }

        # Value list in column order
        row_values = [row_dict.get(col, "") for col in columns]

        if self.is_connected and self.spreadsheet:
            try:
                sheet_name = config.sheets_config["sales_entries"]["name"]
                ws = self.spreadsheet.worksheet(sheet_name)
                # Append row safely (never overwriting previous entries)
                ws.append_row(row_values, value_input_option="USER_ENTERED")
                logger.info(f"Appended new sales entry {entry_id} to Google Sheets row.")
            except Exception as e:
                logger.error(f"Failed to append to Google Sheets: {e}. Writing to local mirror.")

        # Persist to local mirror (without apostrophe prefix in clean dict)
        clean_row = dict(row_dict)
        clean_row["Mobile Number"] = clean_string(data.get("Mobile Number", ""))
        self._append_to_local_mirror("sales_entries", clean_row)
        return entry_id

    def update_sales_entry(
        self,
        entry_id: str,
        updated_fields: Dict[str, Any],
        editor_user_identity: str,
    ) -> bool:
        """
        Updates an existing customer row in Worksheet 1: 'Sales Entries'.
        CRITICAL BUSINESS LOGIC:
        - Locates the EXACT existing row.
        - NEVER creates a new customer row during an edit.
        - Automatically updates 'Last Updated' timestamp.
        - Records the verified editor's identity in 'Updated By'.
        - Preserves all unchanged fields.
        """
        target_id = clean_string(entry_id).upper()
        now_ts = get_current_timestamp_str()
        columns = config.sales_entries_columns

        # Live Google Sheets Update
        if self.is_connected and self.spreadsheet:
            try:
                sheet_name = config.sheets_config["sales_entries"]["name"]
                ws = self.spreadsheet.worksheet(sheet_name)
                records = ws.get_all_records(default_blank="")

                target_row_idx = None
                existing_entry = None
                for idx, r in enumerate(records):
                    if clean_string(r.get("Entry ID", "")).upper() == target_id:
                        target_row_idx = idx + 2  # 1-based, plus header row
                        existing_entry = r
                        break

                if not target_row_idx or not existing_entry:
                    logger.error(f"Cannot update: Entry ID '{entry_id}' not found in Google Sheets.")
                    return False

                # Merge changes
                merged = dict(existing_entry)
                for k, v in updated_fields.items():
                    if k in columns and k not in {"Entry ID", "Created At"}:
                        merged[k] = clean_string(v)

                merged["Last Updated"] = now_ts
                merged["Updated By"] = clean_string(editor_user_identity)

                # Format mobile number as text if changed
                if "Mobile Number" in merged:
                    merged["Mobile Number"] = f"'{clean_string(merged['Mobile Number'])}"

                new_row_values = [merged.get(col, "") for col in columns]

                # Update the EXACT row range (e.g. A2:K2)
                col_end_letter = chr(ord('A') + len(columns) - 1)
                cell_range = f"A{target_row_idx}:{col_end_letter}{target_row_idx}"
                ws.update(cell_range, [new_row_values], value_input_option="USER_ENTERED")
                logger.info(f"Successfully updated row {target_row_idx} ({entry_id}) in Google Sheets.")

            except Exception as e:
                logger.error(f"Live Google Sheets update failed: {e}. Falling back to mirror.")
                return False

        # Update Local Mirror as well
        mirror_entries = self._read_from_local_mirror("sales_entries")
        found = False
        for entry in mirror_entries:
            if clean_string(entry.get("Entry ID", "")).upper() == target_id:
                for k, v in updated_fields.items():
                    if k not in {"Entry ID", "Created At"}:
                        entry[k] = clean_string(v)
                entry["Last Updated"] = now_ts
                entry["Updated By"] = clean_string(editor_user_identity)
                found = True
                break

        if found:
            self._save_to_local_mirror("sales_entries", mirror_entries)
            return True

        return False

    def delete_sales_entry(self, entry_id: str, deleted_by: str = "Admin") -> bool:
        """
        Deletes a customer record from Worksheet 1 ('Sales Entries').
        Automatically appends a deletion record to Worksheet 2 ('Edit History')
        to maintain an unbroken audit trail.
        """
        target_id = clean_string(entry_id).upper()
        now_ts = get_current_timestamp_str()
        deleted_company = ""

        # Live Google Sheets Deletion
        if self.is_connected and self.spreadsheet:
            try:
                sheet_name = config.sheets_config["sales_entries"]["name"]
                ws = self.spreadsheet.worksheet(sheet_name)
                records = ws.get_all_records(default_blank="")

                target_row_idx = None
                for idx, r in enumerate(records):
                    if clean_string(r.get("Entry ID", "")).upper() == target_id:
                        target_row_idx = idx + 2
                        deleted_company = clean_string(r.get("Company Name", ""))
                        break

                if target_row_idx:
                    ws.delete_rows(target_row_idx)
                    logger.info(f"Deleted row {target_row_idx} ({entry_id}) from Google Sheets.")
            except Exception as e:
                logger.error(f"Live Google Sheets deletion failed: {e}")

        # Delete from Local Mirror
        mirror_entries = self._read_from_local_mirror("sales_entries")
        new_entries = []
        found = False
        for entry in mirror_entries:
            if clean_string(entry.get("Entry ID", "")).upper() == target_id:
                found = True
                if not deleted_company:
                    deleted_company = clean_string(entry.get("Company Name", ""))
            else:
                new_entries.append(entry)

        if found:
            self._save_to_local_mirror("sales_entries", new_entries)

            # Record deletion in audit history
            from app.utils import generate_history_id
            deletion_audit = AuditHistoryItem(
                history_id=generate_history_id(),
                entry_id=entry_id,
                company_name=deleted_company,
                field_changed="RECORD_STATUS",
                previous_value="ACTIVE",
                new_value="DELETED",
                updated_by=clean_string(deleted_by),
                update_date_time=now_ts,
            )
            self.append_edit_history_records([deletion_audit])
            return True

        return False

    # =========================================================================
    # EDIT HISTORY OPERATIONS (WORKSHEET 2)
    # =========================================================================

    def fetch_all_edit_history(self) -> List[Dict[str, Any]]:
        """
        Fetches the complete modification audit history from Worksheet 2: 'Edit History'.
        Returns list of history record dictionaries.
        """
        if self.is_connected and self.spreadsheet:
            try:
                sheet_name = config.sheets_config["edit_history"]["name"]
                ws = self.spreadsheet.worksheet(sheet_name)
                records = ws.get_all_records(default_blank="")
                self._save_to_local_mirror("edit_history", records)
                return records
            except Exception as e:
                logger.error(f"Error reading Edit History from Google Sheets: {e}")

        return self._read_from_local_mirror("edit_history")

    def append_edit_history_records(self, history_items: List[AuditHistoryItem]) -> bool:
        """
        Appends modification audit records to Worksheet 2: 'Edit History'.
        Never overwrites or deletes previous audit-history records.
        """
        if not history_items:
            return True

        rows_to_append = [item.to_row() for item in history_items]
        dicts_to_append = [item.to_dict() for item in history_items]

        if self.is_connected and self.spreadsheet:
            try:
                sheet_name = config.sheets_config["edit_history"]["name"]
                ws = self.spreadsheet.worksheet(sheet_name)
                ws.append_rows(rows_to_append, value_input_option="USER_ENTERED")
                logger.info(f"Appended {len(rows_to_append)} audit history entries to Google Sheets.")
            except Exception as e:
                logger.error(f"Failed to append to Google Sheets Edit History: {e}")

        # Always update local mirror
        existing = self._read_from_local_mirror("edit_history")
        existing.extend(dicts_to_append)
        self._save_to_local_mirror("edit_history", existing)
        return True

    # =========================================================================
    # LOCAL MIRROR HELPERS
    # =========================================================================

    def _read_from_local_mirror(self, section: str) -> List[Dict[str, Any]]:
        """Reads section from local mirror JSON file."""
        if not self.local_mirror_file.exists():
            return []
        try:
            with open(self.local_mirror_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data.get(section, [])
        except Exception as e:
            logger.error(f"Error reading local mirror {section}: {e}")
            return []

    def _save_to_local_mirror(self, section: str, records: List[Dict[str, Any]]) -> None:
        """Saves section to local mirror JSON file."""
        try:
            data = {}
            if self.local_mirror_file.exists():
                with open(self.local_mirror_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
            data[section] = records
            with open(self.local_mirror_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving to local mirror {section}: {e}")

    def _append_to_local_mirror(self, section: str, record: Dict[str, Any]) -> None:
        """Appends a single record to local mirror."""
        items = self._read_from_local_mirror(section)
        items.append(record)
        self._save_to_local_mirror(section, items)


# Global sheets connector instance
sheets_connector = GoogleSheetsConnector()
