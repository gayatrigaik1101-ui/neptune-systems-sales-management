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
from app.utils import logger, clean_string, get_current_timestamp_str, generate_entry_id, generate_record_id
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
        Worksheet 1: Sales Entries (14 columns including Sr. No., Status, Remark 1, Remark 2, Record ID)
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
                ws.freeze(rows=1)
            else:
                ws = existing_sheets[title]
                first_row = ws.row_values(1)
                if not first_row:
                    ws.append_row(headers)
                    ws.freeze(rows=1)
                elif title == config.sheets_config["sales_entries"]["name"]:
                    # Check if schema migration is required
                    if first_row != headers:
                        self.upgrade_sales_entries_schema(ws)
                elif title == config.sheets_config["edit_history"]["name"]:
                    if first_row != headers and len(first_row) == len(headers):
                        ws.update("A1", [headers])

    def upgrade_sales_entries_schema(self, ws: Any) -> None:
        """
        Migrates existing Sales Entries worksheet to the updated schema:
        ['Sr. No.', 'Date', 'Company Name', 'Customer Name', 'Company Address',
         'Mobile Number', 'Email', 'Status', 'Remark 1', 'Remark 2',
         'Created At', 'Last Updated', 'Updated By', 'Record ID']
        Preserves all genuine existing records, backfilling Sr. No., Status, Remark 1, Remark 2, and Record ID.
        """
        try:
            old_rows = ws.get_all_values()
            if not old_rows:
                ws.append_row(config.sales_entries_columns)
                ws.freeze(rows=1)
                return

            old_headers = [h.strip() for h in old_rows[0]]
            if old_headers == config.sales_entries_columns:
                return

            logger.info("Migrating Google Sheets 'Sales Entries' to updated schema...")
            data_rows = old_rows[1:]
            header_map = {h: idx for idx, h in enumerate(old_headers)}

            new_rows = []
            for sr_idx, row in enumerate(data_rows, 1):
                def get_val(col_name: str) -> str:
                    idx = header_map.get(col_name)
                    if idx is not None and idx < len(row):
                        return clean_string(row[idx])
                    return ""

                old_id = get_val("Record ID") or get_val("Entry ID") or generate_record_id("NEP")
                old_remark = get_val("Remark")
                status_val = get_val("Status") or "Genuine"
                remark_1_val = get_val("Remark 1") or "Contacted"
                remark_2_val = get_val("Remark 2") or old_remark

                row_dict = {
                    "Sr. No.": sr_idx,
                    "Date": get_val("Date"),
                    "Company Name": get_val("Company Name"),
                    "Customer Name": get_val("Customer Name"),
                    "Company Address": get_val("Company Address"),
                    "Mobile Number": f"'{get_val('Mobile Number')}",
                    "Email": get_val("Email"),
                    "Status": status_val,
                    "Remark 1": remark_1_val,
                    "Remark 2": remark_2_val,
                    "Created At": get_val("Created At"),
                    "Last Updated": get_val("Last Updated"),
                    "Updated By": get_val("Updated By"),
                    "Record ID": old_id,
                }
                new_rows.append([row_dict.get(c, "") for c in config.sales_entries_columns])

            ws.clear()
            all_content = [config.sales_entries_columns] + new_rows
            ws.update("A1", all_content, value_input_option="USER_ENTERED")
            ws.freeze(rows=1)
            logger.info(f"Successfully migrated {len(new_rows)} rows to updated Google Sheets schema.")
        except Exception as e:
            logger.error(f"Failed to migrate Google Sheets schema: {e}")

    # =========================================================================
    # SALES ENTRIES OPERATIONS (WORKSHEET 1)
    # =========================================================================

    def fetch_all_sales_entries(self) -> List[Dict[str, Any]]:
        """
        Fetches all customer sales records from Worksheet 1: 'Sales Entries'.
        Ensures Sr. No. is sequential and Record ID is guaranteed for each entry.
        """
        raw_records: List[Dict[str, Any]] = []
        if self.is_connected and self.spreadsheet:
            try:
                sheet_name = config.sheets_config["sales_entries"]["name"]
                ws = self.spreadsheet.worksheet(sheet_name)
                raw_records = ws.get_all_records(default_blank="")
            except Exception as e:
                logger.error(f"Error reading live Google Sheets: {e}. Falling back to local mirror.")

        if not raw_records:
            raw_records = self._read_from_local_mirror("sales_entries")

        # Normalize records with sequential Sr. No. and guaranteed Record ID
        normalized_records = []
        for idx, r in enumerate(raw_records, 1):
            rec = dict(r)
            rec_id = clean_string(rec.get("Record ID") or rec.get("Entry ID") or f"NEP-REC-{idx:04d}")
            rec["Record ID"] = rec_id
            rec["Entry ID"] = rec_id  # preserve compatibility
            rec["Sr. No."] = idx

            # Normalize Status & Remarks
            rec["Status"] = clean_string(rec.get("Status", ""))
            rec["Remark 1"] = clean_string(rec.get("Remark 1", ""))
            rec["Remark 2"] = clean_string(rec.get("Remark 2", "") or rec.get("Remark", ""))
            rec["Remark"] = rec["Remark 2"] or rec["Remark 1"]

            normalized_records.append(rec)

        # Sync normalized copy to local mirror
        self._save_to_local_mirror("sales_entries", normalized_records)
        return normalized_records

    def fetch_sales_entry_by_id(self, target_id: str) -> Optional[Tuple[int, Dict[str, Any]]]:
        """
        Retrieves a single sales entry by its Record ID, Entry ID, or Sr. No.
        Returns tuple of (1-based row index in sheet, record dictionary) or None.
        """
        clean_target = clean_string(target_id).upper()
        if not clean_target:
            return None

        entries = self.fetch_all_sales_entries()
        for idx, entry in enumerate(entries):
            r_id = clean_string(entry.get("Record ID", "")).upper()
            e_id = clean_string(entry.get("Entry ID", "")).upper()
            sr_str = str(entry.get("Sr. No.", ""))

            if clean_target in (r_id, e_id, sr_str):
                return (idx + 2, entry)

        return None

    def insert_sales_entry(self, data: Dict[str, Any], created_by: str = "Sales Team") -> str:
        """
        Inserts a new sales customer submission into Worksheet 1 ('Sales Entries').
        Automatically assigns next sequential Sr. No., permanent Record ID, timestamp, and sets Updated By.
        """
        existing = self.fetch_all_sales_entries()
        sr_no = len(existing) + 1
        record_id = clean_string(data.get("Record ID") or data.get("Entry ID") or generate_record_id("NEP"))
        now_ts = get_current_timestamp_str()
        columns = config.sales_entries_columns

        row_dict = {
            "Sr. No.": sr_no,
            "Date": clean_string(data.get("Date", "")),
            "Company Name": clean_string(data.get("Company Name", "")),
            "Customer Name": clean_string(data.get("Customer Name", "")),
            "Company Address": clean_string(data.get("Company Address", "")),
            "Mobile Number": f"'{clean_string(data.get('Mobile Number', ''))}",
            "Email": clean_string(data.get("Email", "")),
            "Status": clean_string(data.get("Status", "")),
            "Remark 1": clean_string(data.get("Remark 1", "")),
            "Remark 2": clean_string(data.get("Remark 2", "") or data.get("Remark", "")),
            "Created At": data.get("Created At") or now_ts,
            "Last Updated": now_ts,
            "Updated By": created_by,
            "Record ID": record_id,
        }

        row_values = [row_dict.get(col, "") for col in columns]

        if self.is_connected and self.spreadsheet:
            try:
                sheet_name = config.sheets_config["sales_entries"]["name"]
                ws = self.spreadsheet.worksheet(sheet_name)
                ws.append_row(row_values, value_input_option="USER_ENTERED")
                logger.info(f"Appended new sales entry {record_id} (Sr. No. {sr_no}) to Google Sheets row.")
            except Exception as e:
                logger.error(f"Failed to append to Google Sheets: {e}. Writing to local mirror.")

        # Persist to local mirror (without apostrophe prefix)
        clean_row = dict(row_dict)
        clean_row["Mobile Number"] = clean_string(data.get("Mobile Number", ""))
        clean_row["Entry ID"] = record_id
        clean_row["Remark"] = clean_row["Remark 2"] or clean_row["Remark 1"]
        self._append_to_local_mirror("sales_entries", clean_row)
        return record_id

    def update_sales_entry(
        self,
        record_id: Optional[str] = None,
        updated_fields: Optional[Dict[str, Any]] = None,
        editor_user_identity: str = "",
        entry_id: Optional[str] = None,
    ) -> bool:
        """
        Updates an existing customer row in Worksheet 1: 'Sales Entries'.
        Targets the record by its permanent Record ID (or legacy Entry ID).
        Preserves Sr. No., Record ID, Created At.
        """
        target_raw = record_id or entry_id or ""
        target = clean_string(target_raw).upper()
        if not target:
            return False
        if updated_fields is None:
            updated_fields = {}
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
                    r_id = clean_string(r.get("Record ID", "")).upper()
                    e_id = clean_string(r.get("Entry ID", "")).upper()
                    if target in (r_id, e_id):
                        target_row_idx = idx + 2
                        existing_entry = r
                        break

                if not target_row_idx or not existing_entry:
                    logger.error(f"Cannot update: Record ID '{record_id}' not found in Google Sheets.")
                    return False

                # Merge changes
                merged = dict(existing_entry)
                for k, v in updated_fields.items():
                    if k in columns and k not in {"Sr. No.", "Record ID", "Entry ID", "Created At"}:
                        merged[k] = clean_string(v)

                if "Remark" in updated_fields and "Remark 2" not in updated_fields:
                    merged["Remark 2"] = clean_string(updated_fields["Remark"])

                merged["Last Updated"] = now_ts
                merged["Updated By"] = clean_string(editor_user_identity)

                if "Mobile Number" in merged:
                    merged["Mobile Number"] = f"'{clean_string(merged['Mobile Number'])}"

                new_row_values = [merged.get(col, "") for col in columns]

                col_end_letter = chr(ord('A') + len(columns) - 1)
                cell_range = f"A{target_row_idx}:{col_end_letter}{target_row_idx}"
                ws.update(values=[new_row_values], range_name=cell_range, value_input_option="USER_ENTERED")
                logger.info(f"Successfully updated row {target_row_idx} ({record_id}) in Google Sheets.")

            except Exception as e:
                logger.error(f"Live Google Sheets update failed: {e}. Falling back to mirror.")
                return False

        # Update Local Mirror
        mirror_entries = self._read_from_local_mirror("sales_entries")
        found = False
        for entry in mirror_entries:
            r_id = clean_string(entry.get("Record ID", "")).upper()
            e_id = clean_string(entry.get("Entry ID", "")).upper()
            if target in (r_id, e_id):
                for k, v in updated_fields.items():
                    if k not in {"Sr. No.", "Record ID", "Entry ID", "Created At"}:
                        entry[k] = clean_string(v)
                if "Remark" in updated_fields and "Remark 2" not in updated_fields:
                    entry["Remark 2"] = clean_string(updated_fields["Remark"])
                entry["Last Updated"] = now_ts
                entry["Updated By"] = clean_string(editor_user_identity)
                entry["Remark"] = entry.get("Remark 2", "") or entry.get("Remark 1", "")
                found = True
                break

        if found:
            self._save_to_local_mirror("sales_entries", mirror_entries)
            return True

        return False

    def delete_sales_entry(
        self,
        record_id: Optional[str] = None,
        deleted_by: str = "Admin",
        entry_id: Optional[str] = None,
    ) -> bool:
        """
        Deletes a customer record from Worksheet 1 ('Sales Entries').
        Recalculates sequential Sr. No. for all remaining records.
        Automatically appends a deletion record to Worksheet 2 ('Edit History').
        """
        target_raw = record_id or entry_id or ""
        target = clean_string(target_raw).upper()
        if not target:
            return False
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
                    r_id = clean_string(r.get("Record ID", "")).upper()
                    e_id = clean_string(r.get("Entry ID", "")).upper()
                    if target in (r_id, e_id):
                        target_row_idx = idx + 2
                        deleted_company = clean_string(r.get("Company Name", ""))
                        break

                if target_row_idx:
                    ws.delete_rows(target_row_idx)
                    logger.info(f"Deleted row {target_row_idx} ({record_id}) from Google Sheets.")

                    # Recalculate Sr. No. for remaining rows in Google Sheets
                    remaining_count = len(records) - 1
                    if remaining_count > 0:
                        sr_vals = [[i] for i in range(1, remaining_count + 1)]
                        ws.update(values=sr_vals, range_name=f"A2:A{remaining_count + 1}", value_input_option="USER_ENTERED")
                        logger.info("Recalculated sequential Sr. No. in Google Sheets.")
            except Exception as e:
                logger.error(f"Live Google Sheets deletion failed: {e}")

        # Delete from Local Mirror & recalculate Sr. No.
        mirror_entries = self._read_from_local_mirror("sales_entries")
        new_entries = []
        found = False
        for entry in mirror_entries:
            r_id = clean_string(entry.get("Record ID", "")).upper()
            e_id = clean_string(entry.get("Entry ID", "")).upper()
            if target in (r_id, e_id):
                found = True
                if not deleted_company:
                    deleted_company = clean_string(entry.get("Company Name", ""))
            else:
                new_entries.append(entry)

        if found:
            # Re-index Sr. No. sequentially
            for i, entry in enumerate(new_entries, 1):
                entry["Sr. No."] = i

            self._save_to_local_mirror("sales_entries", new_entries)

            # Record deletion in audit history
            from app.utils import generate_history_id
            deletion_audit = AuditHistoryItem(
                history_id=generate_history_id(),
                entry_id=record_id,
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
