"""
Unit Tests for Data Validation & Integrity Engine
"""

import pytest
from app.validation import SalesDataValidator, ValidationResult


def test_mobile_number_validation():
    # Valid 10 digits
    ok, err, val = SalesDataValidator.validate_mobile_number("9876543210")
    assert ok is True
    assert val == "9876543210"

    # Reject 9-digit mobile number
    ok, err, val = SalesDataValidator.validate_mobile_number("987654321")
    assert ok is False
    assert "10 digits" in err

    # Reject 11-digit mobile number
    ok, err, val = SalesDataValidator.validate_mobile_number("98765432101")
    assert ok is False
    assert "10 digits" in err

    # Reject alphabetic characters
    ok, err, val = SalesDataValidator.validate_mobile_number("98765abc10")
    assert ok is False
    assert "Alphabetic characters are rejected" in err

    # Reject blank
    ok, err, val = SalesDataValidator.validate_mobile_number("")
    assert ok is False
    assert "mandatory" in err


def test_email_validation():
    # Accept valid email
    ok, err, val = SalesDataValidator.validate_email("sales@neptunesystems.com")
    assert ok is True
    assert val == "sales@neptunesystems.com"

    # Accept blank optional email
    ok, err, val = SalesDataValidator.validate_email("")
    assert ok is True
    assert val == ""

    # Accept None optional email
    ok, err, val = SalesDataValidator.validate_email(None)
    assert ok is True
    assert val == ""

    # Reject invalid email format
    ok, err, val = SalesDataValidator.validate_email("invalid-email-address")
    assert ok is False
    assert "Invalid email format" in err


def test_mandatory_fields_rejection():
    # Reject blank Company Name
    ok, err, val = SalesDataValidator.validate_company_name("   ")
    assert ok is False
    assert "Company Name is mandatory" in err

    # Reject blank Customer Name
    ok, err, val = SalesDataValidator.validate_customer_name("")
    assert ok is False
    assert "Customer Name is mandatory" in err

    # Reject blank Company Address
    ok, err, val = SalesDataValidator.validate_company_address("   ")
    assert ok is False
    assert "Company Address is mandatory" in err

    # Reject blank Remark
    ok, err, val = SalesDataValidator.validate_remark("")
    assert ok is False
    assert "Remark is mandatory" in err


def test_date_validation():
    # Valid DD-MM-YYYY
    ok, err, val = SalesDataValidator.validate_date("02-11-2026")
    assert ok is True
    assert val == "02-11-2026"

    # Valid slash format parsed to DD-MM-YYYY
    ok, err, val = SalesDataValidator.validate_date("02/11/2026")
    assert ok is True
    assert val == "02-11-2026"

    # Reject invalid date string
    ok, err, val = SalesDataValidator.validate_date("not-a-date")
    assert ok is False
    assert "Invalid date format" in err


def test_full_record_validation():
    valid_record = {
        "Date": "02-11-2026",
        "Company Name": "Apex Engineering Works",
        "Customer Name": "Rahul Patil",
        "Company Address": "Plot 42, Bhosari MIDC, Pune",
        "Mobile Number": "9822012345",
        "Email": "rahul@apexeng.in",
        "Remark": "Requires 5kW servo system quote by Friday.",
    }
    res: ValidationResult = SalesDataValidator.validate_record(valid_record)
    assert res.is_valid is True
    assert len(res.errors) == 0
    assert res.sanitized_data["Mobile Number"] == "9822012345"
    assert res.sanitized_data["Company Name"] == "Apex Engineering Works"

    # Full record with missing fields
    invalid_record = {
        "Date": "02-11-2026",
        "Company Name": "   ",
        "Customer Name": "",
        "Company Address": "Short",
        "Mobile Number": "12345",  # invalid length
        "Email": "bad-email",
        "Remark": "",
    }
    res2: ValidationResult = SalesDataValidator.validate_record(invalid_record)
    assert res2.is_valid is False
    assert "Company Name" in res2.errors
    assert "Customer Name" in res2.errors
    assert "Mobile Number" in res2.errors
    assert "Email" in res2.errors
    assert "Remark" in res2.errors
