"""
Neptune Systems - Sales Management System
Data Validation and Integrity Engine
"""

import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from app.utils import (
    clean_string,
    sanitize_phone_number,
    parse_date_string,
    STATUS_OPTIONS,
    REMARK_1_OPTIONS,
)


@dataclass
class ValidationResult:
    """Encapsulates the outcome of data validation."""
    is_valid: bool
    errors: Dict[str, str] = field(default_factory=dict)
    sanitized_data: Dict[str, Any] = field(default_factory=dict)

    def error_summary(self) -> str:
        """Returns readable summary of all validation errors."""
        if self.is_valid:
            return "Validation successful."
        return "; ".join([f"{k}: {v}" for k, v in self.errors.items()])


class SalesDataValidator:
    """Validates Neptune Systems customer and sales entry records."""

    EMAIL_REGEX = re.compile(
        r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+(?:\.[a-zA-Z0-9-]+)+$"
    )

    @classmethod
    def validate_date(cls, value: Any) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Validates Date field.
        Optional: If not provided, defaults to current date.
        """
        cleaned = clean_string(value)
        if not cleaned:
            from app.utils import get_current_date_str
            return True, None, get_current_date_str()

        parsed = parse_date_string(cleaned)
        if not parsed:
            # If parsing fails, preserve raw string or today's date
            return True, None, cleaned

        normalized = parsed.strftime("%d-%m-%Y")
        return True, None, normalized

    @classmethod
    def validate_company_name(cls, value: Any) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Validates Company Name field.
        Optional: Allowed to be blank.
        """
        cleaned = clean_string(value)
        return True, None, cleaned

    @classmethod
    def validate_customer_name(cls, value: Any) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Validates Customer Name field.
        Optional: Allowed to be blank.
        """
        cleaned = clean_string(value)
        return True, None, cleaned

    @classmethod
    def validate_company_address(cls, value: Any) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Validates Company Address field.
        Optional: Allowed to be blank.
        """
        cleaned = clean_string(value)
        return True, None, cleaned

    @classmethod
    def validate_mobile_number(cls, value: Any) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Validates Mobile Number field.
        Optional: Allowed to be blank.
        If entered, cleans digits.
        """
        raw_str = clean_string(value)
        if not raw_str:
            return True, None, ""

        digits = sanitize_phone_number(raw_str)
        return True, None, digits if digits else raw_str

    @classmethod
    def validate_email(cls, value: Any) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Validates Email field.
        Optional: Allowed to be blank.
        """
        cleaned = clean_string(value)
        if not cleaned:
            return True, None, ""

        return True, None, cleaned.lower()

    @classmethod
    def validate_remark(cls, value: Any) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Validates Remark field (legacy/fallback).
        Optional: Allowed to be blank.
        """
        cleaned = clean_string(value)
        return True, None, cleaned

    @classmethod
    def validate_status(cls, value: Any) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Validates Status field.
        Options: Interested, Not Interested, Genuine.
        Optional: Allowed to be blank or any valid Status.
        """
        cleaned = clean_string(value)
        if not cleaned:
            return True, None, ""

        # Match case-insensitively to canonical options
        for opt in STATUS_OPTIONS:
            if cleaned.lower() == opt.lower():
                return True, None, opt

        return True, None, cleaned

    @classmethod
    def validate_remark_1(cls, value: Any) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Validates Remark 1 dropdown field.
        Optional: Allowed to be blank or any valid Remark 1 option.
        """
        cleaned = clean_string(value)
        if not cleaned:
            return True, None, ""

        for opt in REMARK_1_OPTIONS:
            if cleaned.lower() == opt.lower():
                return True, None, opt

        return True, None, cleaned

    @classmethod
    def validate_remark_2(cls, value: Any) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Validates Remark 2 manual free-text entry field.
        Optional: Allowed to be blank or free-form text.
        """
        cleaned = clean_string(value)
        return True, None, cleaned

    @classmethod
    def validate_record(cls, data: Dict[str, Any]) -> ValidationResult:
        """
        Validates a full customer entry dictionary against all business rules.
        Returns a ValidationResult object with errors and sanitized data.
        """
        errors: Dict[str, str] = {}
        sanitized: Dict[str, Any] = {}

        # 1. Date
        ok, err, val = cls.validate_date(data.get("Date"))
        if not ok and err:
            errors["Date"] = err
        else:
            sanitized["Date"] = val

        # 2. Company Name
        ok, err, val = cls.validate_company_name(data.get("Company Name"))
        if not ok and err:
            errors["Company Name"] = err
        else:
            sanitized["Company Name"] = val

        # 3. Customer Name
        ok, err, val = cls.validate_customer_name(data.get("Customer Name"))
        if not ok and err:
            errors["Customer Name"] = err
        else:
            sanitized["Customer Name"] = val

        # 4. Company Address
        ok, err, val = cls.validate_company_address(data.get("Company Address"))
        if not ok and err:
            errors["Company Address"] = err
        else:
            sanitized["Company Address"] = val

        # 5. Mobile Number
        ok, err, val = cls.validate_mobile_number(data.get("Mobile Number"))
        if not ok and err:
            errors["Mobile Number"] = err
        else:
            sanitized["Mobile Number"] = val

        # 6. Email
        ok, err, val = cls.validate_email(data.get("Email"))
        if not ok and err:
            errors["Email"] = err
        else:
            sanitized["Email"] = val

        # 7. Status
        ok, err, val = cls.validate_status(data.get("Status"))
        if not ok and err:
            errors["Status"] = err
        else:
            sanitized["Status"] = val

        # 8. Remark 1 (Dropdown)
        ok, err, val = cls.validate_remark_1(data.get("Remark 1"))
        if not ok and err:
            errors["Remark 1"] = err
        else:
            sanitized["Remark 1"] = val

        # 9. Remark 2 (Manual Entry)
        # Fall back to legacy Remark if Remark 2 is empty but Remark is provided
        raw_remark_2 = data.get("Remark 2")
        if not raw_remark_2 and data.get("Remark"):
            raw_remark_2 = data.get("Remark")
        ok, err, val = cls.validate_remark_2(raw_remark_2)
        if not ok and err:
            errors["Remark 2"] = err
        else:
            sanitized["Remark 2"] = val

        # Keep legacy Remark in sync if needed
        sanitized["Remark"] = sanitized["Remark 2"] or sanitized["Remark 1"]

        # Preserve metadata and identifiers if present
        for meta_field in ["Sr. No.", "Record ID", "Entry ID", "Created At", "Last Updated", "Updated By"]:
            if meta_field in data:
                sanitized[meta_field] = clean_string(data[meta_field])

        return ValidationResult(
            is_valid=(len(errors) == 0),
            errors=errors,
            sanitized_data=sanitized
        )

    @classmethod
    def validate_single_field(cls, field_name: str, value: Any) -> Tuple[bool, Optional[str], Optional[str]]:
        """Validates any individual field by name."""
        mapping = {
            "Date": cls.validate_date,
            "Company Name": cls.validate_company_name,
            "Customer Name": cls.validate_customer_name,
            "Company Address": cls.validate_company_address,
            "Mobile Number": cls.validate_mobile_number,
            "Email": cls.validate_email,
            "Remark": cls.validate_remark,
            "Status": cls.validate_status,
            "Remark 1": cls.validate_remark_1,
            "Remark 2": cls.validate_remark_2,
        }
        validator = mapping.get(field_name)
        if not validator:
            # Unrestricted field
            return True, None, clean_string(value)
        return validator(value)
