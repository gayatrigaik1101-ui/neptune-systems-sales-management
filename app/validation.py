"""
Neptune Systems - Sales Management System
Data Validation and Integrity Engine
"""

import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from app.utils import clean_string, sanitize_phone_number, parse_date_string


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
        Mandatory: YES
        Must be a valid date, normalized to DD-MM-YYYY format.
        """
        cleaned = clean_string(value)
        if not cleaned:
            return False, "Date is mandatory.", None

        parsed = parse_date_string(cleaned)
        if not parsed:
            return False, "Invalid date format. Expected DD-MM-YYYY (e.g. 02-11-2026).", None

        normalized = parsed.strftime("%d-%m-%Y")
        return True, None, normalized

    @classmethod
    def validate_company_name(cls, value: Any) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Validates Company Name field.
        Mandatory: YES. Reject empty or whitespace-only values.
        """
        cleaned = clean_string(value)
        if not cleaned:
            return False, "Company Name is mandatory and cannot be blank or whitespace only.", None
        if len(cleaned) < 2:
            return False, "Company Name must be at least 2 characters.", None
        return True, None, cleaned

    @classmethod
    def validate_customer_name(cls, value: Any) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Validates Customer Name field.
        Mandatory: YES. Reject empty values.
        """
        cleaned = clean_string(value)
        if not cleaned:
            return False, "Customer Name is mandatory and cannot be blank.", None
        if len(cleaned) < 2:
            return False, "Customer Name must be at least 2 characters.", None
        return True, None, cleaned

    @classmethod
    def validate_company_address(cls, value: Any) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Validates Company Address field.
        Mandatory: YES. Allow complete addresses.
        """
        cleaned = clean_string(value)
        if not cleaned:
            return False, "Company Address is mandatory and cannot be blank.", None
        if len(cleaned) < 5:
            return False, "Company Address must contain at least 5 characters.", None
        return True, None, cleaned

    @classmethod
    def validate_mobile_number(cls, value: Any) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Validates Mobile Number field.
        Mandatory: YES. Must contain exactly 10 numeric digits.
        Reject alphabetic characters, symbols, and invalid lengths.
        """
        raw_str = clean_string(value)
        if not raw_str:
            return False, "Mobile Number is mandatory.", None

        # Check if contains letters or forbidden symbols
        if re.search(r"[a-zA-Z]", raw_str):
            return False, "Mobile Number must contain only digits. Alphabetic characters are rejected.", None

        digits = sanitize_phone_number(raw_str)
        if len(digits) != 10:
            return (
                False,
                f"Mobile Number must contain exactly 10 digits. Provided input contains {len(digits)} digits.",
                None
            )

        # Standard mobile number sanity check (must start with 6, 7, 8, or 9 for Indian mobile numbers)
        if not re.match(r"^[6-9]\d{9}$", digits):
            # We still accept it if 10 digits, but warn if clearly non-standard
            pass

        return True, None, digits

    @classmethod
    def validate_email(cls, value: Any) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Validates Email field.
        Mandatory: NO.
        Allow blank values. If entered, validate email format.
        """
        cleaned = clean_string(value)
        if not cleaned:
            return True, None, ""

        if not cls.EMAIL_REGEX.match(cleaned):
            return False, f"Invalid email format: '{cleaned}'. Please provide a valid email or leave blank.", None

        return True, None, cleaned.lower()

    @classmethod
    def validate_remark(cls, value: Any) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Validates Remark field.
        Mandatory: YES.
        Allow detailed customer interaction notes, requirements, enquiries, follow-up discussions.
        """
        cleaned = clean_string(value)
        if not cleaned:
            return False, "Remark is mandatory. Enter interaction notes, requirements, or follow-up details.", None
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

        # 7. Remark
        ok, err, val = cls.validate_remark(data.get("Remark"))
        if not ok and err:
            errors["Remark"] = err
        else:
            sanitized["Remark"] = val

        # Preserve metadata if present
        for meta_field in ["Entry ID", "Created At", "Last Updated", "Updated By"]:
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
        }
        validator = mapping.get(field_name)
        if not validator:
            # Unrestricted field
            return True, None, clean_string(value)
        return validator(value)
