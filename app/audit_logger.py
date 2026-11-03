"""
Neptune Systems - Sales Management System
Audit Logging & Modification History Engine
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional
from app.utils import generate_history_id, get_current_timestamp_str, audit_sys_logger, clean_string


@dataclass
class AuditHistoryItem:
    """Represents a single atomic field change in the Edit History worksheet."""
    history_id: str
    entry_id: str
    company_name: str
    field_changed: str
    previous_value: str
    new_value: str
    updated_by: str
    update_date_time: str

    def to_row(self) -> List[str]:
        """Converts item into a list matching Edit History worksheet columns."""
        return [
            self.history_id,
            self.entry_id,
            self.company_name,
            self.field_changed,
            self.previous_value,
            self.new_value,
            self.updated_by,
            self.update_date_time,
        ]

    def to_dict(self) -> Dict[str, str]:
        """Converts item into a dictionary for API/JSON handling."""
        return {
            "History ID": self.history_id,
            "Entry ID": self.entry_id,
            "Company Name": self.company_name,
            "Field Changed": self.field_changed,
            "Previous Value": self.previous_value,
            "New Value": self.new_value,
            "Updated By": self.updated_by,
            "Update Date & Time": self.update_date_time,
        }


class AuditLogger:
    """Creates, formats, and tracks field-level modification records for Neptune Systems."""

    @classmethod
    def generate_diff(
        cls,
        entry_id: str,
        company_name: str,
        original_record: Dict[str, Any],
        updated_fields: Dict[str, Any],
        editor_identity: str,
    ) -> List[AuditHistoryItem]:
        """
        Compares original record with updated fields to generate individual AuditHistoryItems.
        Only fields whose values have actually changed produce a history item.
        """
        changes: List[AuditHistoryItem] = []
        now_str = get_current_timestamp_str()

        # Exclude metadata fields from field change tracking
        ignored_fields = {"Entry ID", "Created At", "Last Updated", "Updated By"}

        for field_name, new_val in updated_fields.items():
            if field_name in ignored_fields:
                continue

            old_val_cleaned = clean_string(original_record.get(field_name, ""))
            new_val_cleaned = clean_string(new_val)

            # Check if there is an actual modification
            if old_val_cleaned != new_val_cleaned:
                hist_id = generate_history_id()
                item = AuditHistoryItem(
                    history_id=hist_id,
                    entry_id=clean_string(entry_id),
                    company_name=clean_string(company_name),
                    field_changed=field_name,
                    previous_value=old_val_cleaned,
                    new_value=new_val_cleaned,
                    updated_by=clean_string(editor_identity),
                    update_date_time=now_str,
                )
                changes.append(item)

                # Log to system audit log
                audit_sys_logger.info(
                    f"RECORD_MODIFIED | Entry: {entry_id} | Field: {field_name} | "
                    f"Old: '{old_val_cleaned}' -> New: '{new_val_cleaned}' | By: {editor_identity}"
                )

        return changes

    @classmethod
    def log_system_event(cls, event_type: str, details: str, user_identity: Optional[str] = None) -> None:
        """Logs general security and system events to the local rotating audit file."""
        user_str = user_identity or "SYSTEM"
        audit_sys_logger.info(f"{event_type.upper()} | User: {user_str} | Details: {details}")
