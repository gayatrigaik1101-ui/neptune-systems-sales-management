"""
Neptune Systems - Sales Management System
Record Management & Business Logic Engine
"""

from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
import pandas as pd

from app.config import config
from app.utils import logger, clean_string, parse_date_string, get_current_date_str
from app.validation import SalesDataValidator, ValidationResult
from app.google_sheets import sheets_connector
from app.audit_logger import AuditLogger, AuditHistoryItem


class ConcurrentEditConflictError(Exception):
    """Raised when an edit is attempted on a record that has already been modified by another user."""
    pass


class RecordManager:
    """Orchestrates customer data retrieval, validation, updates, audit logging, and concurrency control."""

    def __init__(self) -> None:
        self.sheets = sheets_connector

    def get_all_records(self, sort_by_date: bool = True) -> List[Dict[str, Any]]:
        """Retrieves all sales records, optionally sorted by Date descending."""
        records = self.sheets.fetch_all_sales_entries()
        if not records:
            return []

        if sort_by_date:
            def sort_key(rec: Dict[str, Any]) -> datetime:
                d = parse_date_string(rec.get("Date", ""))
                return d or datetime.min

            return sorted(records, key=sort_key, reverse=True)
        return records

    def get_record_by_id(self, entry_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves a single record by its Entry ID."""
        res = self.sheets.fetch_sales_entry_by_id(entry_id)
        if res:
            return res[1]
        return None

    def search_records(
        self,
        entry_id: str = "",
        company_name: str = "",
        customer_name: str = "",
        mobile_number: str = "",
        date_str: str = "",
        general_query: str = "",
    ) -> List[Dict[str, Any]]:
        """
        Searches records using multi-criteria filtering:
        - Entry ID
        - Company Name
        - Customer Name
        - Mobile Number
        - Date
        - General query across all fields
        """
        all_records = self.get_all_records(sort_by_date=True)
        filtered = []

        q_id = clean_string(entry_id).upper()
        q_comp = clean_string(company_name).lower()
        q_cust = clean_string(customer_name).lower()
        q_mob = clean_string(mobile_number)
        q_date = clean_string(date_str)
        q_gen = clean_string(general_query).lower()

        for rec in all_records:
            r_id = clean_string(rec.get("Entry ID", "")).upper()
            r_comp = clean_string(rec.get("Company Name", "")).lower()
            r_cust = clean_string(rec.get("Customer Name", "")).lower()
            r_mob = clean_string(rec.get("Mobile Number", ""))
            r_date = clean_string(rec.get("Date", ""))
            r_remark = clean_string(rec.get("Remark", "")).lower()

            # Exact or partial match checks
            if q_id and q_id not in r_id:
                continue
            if q_comp and q_comp not in r_comp:
                continue
            if q_cust and q_cust not in r_cust:
                continue
            if q_mob and q_mob not in r_mob:
                continue
            if q_date and q_date != r_date:
                continue

            # General query across full record
            if q_gen:
                haystack = f"{r_id} {r_comp} {r_cust} {r_mob} {r_date} {r_remark}"
                if q_gen not in haystack:
                    continue

            filtered.append(rec)

        return filtered

    def create_record(self, data: Dict[str, Any], created_by: str = "Sales Team") -> Tuple[bool, str, Optional[str]]:
        """
        Validates and creates a new sales customer submission.
        Returns: (success_bool, message, entry_id)
        """
        validation: ValidationResult = SalesDataValidator.validate_record(data)
        if not validation.is_valid:
            return False, f"Validation Failed: {validation.error_summary()}", None

        try:
            entry_id = self.sheets.insert_sales_entry(validation.sanitized_data, created_by=created_by)
            return True, f"Successfully created customer entry with ID: {entry_id}", entry_id
        except Exception as e:
            logger.error(f"Error creating sales record: {e}")
            return False, f"Database error creating entry: {str(e)}", None

    def update_record(
        self,
        entry_id: str,
        updated_fields: Dict[str, Any],
        editor_identity: str,
        expected_last_updated: Optional[str] = None,
    ) -> Tuple[bool, str, List[AuditHistoryItem]]:
        """
        Updates an existing sales record with strict concurrency check and audit logging.
        CRITICAL RULES:
        1. Validates all updated fields.
        2. Detects concurrent edit conflicts.
        3. Prevents creating duplicate rows.
        4. Saves changes to the original Google Sheets row.
        5. Records every changed field in Edit History.
        Returns: (success_bool, message, list_of_audit_items)
        """
        # Fetch current existing record from database
        res = self.sheets.fetch_sales_entry_by_id(entry_id)
        if not res:
            return False, f"Record with Entry ID '{entry_id}' not found.", []

        row_idx, original_record = res

        # 1. OPTIMISTIC CONCURRENCY CHECK
        if config.get("app", {}).get("concurrency_protection", True) and expected_last_updated:
            db_last_updated = clean_string(original_record.get("Last Updated", ""))
            exp_last_updated = clean_string(expected_last_updated)
            if db_last_updated and exp_last_updated and db_last_updated != exp_last_updated:
                err_msg = (
                    f"CONCURRENT EDIT CONFLICT: This record was modified by another user at "
                    f"'{db_last_updated}' after you loaded it (loaded at '{exp_last_updated}'). "
                    f"To prevent overwriting newer information, please refresh the record and review."
                )
                logger.warning(f"Conflict on {entry_id}: DB '{db_last_updated}' vs Expected '{exp_last_updated}'")
                raise ConcurrentEditConflictError(err_msg)

        # 2. VALIDATE ALL CHANGED FIELDS
        merged_for_validation = dict(original_record)
        merged_for_validation.update(updated_fields)

        validation: ValidationResult = SalesDataValidator.validate_record(merged_for_validation)
        if not validation.is_valid:
            return False, f"Validation Failed: {validation.error_summary()}", []

        # 3. GENERATE AUDIT DIFF
        company_name = clean_string(original_record.get("Company Name", ""))
        audit_items = AuditLogger.generate_diff(
            entry_id=entry_id,
            company_name=company_name,
            original_record=original_record,
            updated_fields=validation.sanitized_data,
            editor_identity=editor_identity,
        )

        if not audit_items:
            return True, "No field values were modified. Record remains unchanged.", []

        # 4. UPDATE EXISTING ROW IN GOOGLE SHEETS
        success = self.sheets.update_sales_entry(
            entry_id=entry_id,
            updated_fields=validation.sanitized_data,
            editor_user_identity=editor_identity,
        )

        if not success:
            return False, "Failed to update row in Google Sheets database.", []

        # 5. APPEND AUDIT HISTORY RECORDS
        self.sheets.append_edit_history_records(audit_items)

        logger.info(
            f"Successfully updated entry {entry_id} with {len(audit_items)} changes by {editor_identity}."
        )
        return True, f"Successfully updated record {entry_id} ({len(audit_items)} field(s) changed).", audit_items

    def delete_record(self, entry_id: str, deleted_by: str) -> Tuple[bool, str]:
        """
        Deletes a sales record by Entry ID.
        Verifies record exists, removes it from Worksheet 1,
        and logs a permanent deletion audit entry in Worksheet 2.
        """
        rec = self.get_record_by_id(entry_id)
        if not rec:
            return False, f"Record with Entry ID '{entry_id}' not found."

        success = self.sheets.delete_sales_entry(entry_id=entry_id, deleted_by=deleted_by)
        if success:
            logger.info(f"Record {entry_id} deleted by {deleted_by}.")
            return True, f"Record {entry_id} has been permanently deleted and logged in Edit History."
        return False, f"Failed to delete record {entry_id} from database."

    def get_edit_history(
        self,
        updated_by: str = "",
        company_name: str = "",
        entry_id: str = "",
        update_date: str = "",
    ) -> List[Dict[str, Any]]:
        """
        Retrieves audit history with optional filters:
        - Updated By
        - Company Name
        - Entry ID
        - Update Date
        """
        all_history = self.sheets.fetch_all_edit_history()
        if not all_history:
            return []

        filtered = []
        q_user = clean_string(updated_by).lower()
        q_comp = clean_string(company_name).lower()
        q_id = clean_string(entry_id).upper()
        q_date = clean_string(update_date)

        for item in all_history:
            h_user = clean_string(item.get("Updated By", "")).lower()
            h_comp = clean_string(item.get("Company Name", "")).lower()
            h_id = clean_string(item.get("Entry ID", "")).upper()
            h_ts = clean_string(item.get("Update Date & Time", ""))

            if q_user and q_user not in h_user:
                continue
            if q_comp and q_comp not in h_comp:
                continue
            if q_id and q_id not in h_id:
                continue
            if q_date and q_date not in h_ts:
                continue

            filtered.append(item)

        # Reverse to show newest edits first
        return list(reversed(filtered))

    def get_overview_metrics(self) -> Dict[str, Any]:
        """
        Calculates key dashboard metrics:
        - Total Customer Entries
        - Total Companies (unique)
        - Entries Added Today
        - Entries Updated Today
        - Records Requiring Follow-up
        """
        records = self.get_all_records(sort_by_date=False)
        today_str = get_current_date_str("%d-%m-%Y")

        total_entries = len(records)
        unique_companies = len(set(clean_string(r.get("Company Name", "")).lower() for r in records if r.get("Company Name")))

        added_today = 0
        updated_today = 0
        followup_count = 0

        followup_keywords = ["follow-up", "followup", "call back", "quote", "pending", "requirement", "demo", "interested"]

        for r in records:
            created_at = clean_string(r.get("Created At", ""))
            last_updated = clean_string(r.get("Last Updated", ""))
            date_field = clean_string(r.get("Date", ""))
            remark = clean_string(r.get("Remark", "")).lower()

            if today_str in created_at or today_str in date_field:
                added_today += 1

            if today_str in last_updated and last_updated != created_at:
                updated_today += 1

            if any(kw in remark for kw in followup_keywords):
                followup_count += 1

        return {
            "total_entries": total_entries,
            "total_companies": unique_companies,
            "entries_added_today": added_today,
            "entries_updated_today": updated_today,
            "requiring_followup": followup_count,
        }


# Global record manager instance
record_manager = RecordManager()
