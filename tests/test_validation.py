"""
Unit Tests for Data Validation & Integrity Engine
Validates that fields are optional and accept submissions without compulsory restrictions.
"""

import pytest
from app.validation import SalesDataValidator, ValidationResult


def test_mobile_number_validation():
    # Valid 10 digits
    ok, err, val = SalesDataValidator.validate_mobile_number("9876543210")
    assert ok is True
    assert val == "9876543210"

    # Accept blank mobile number (non-compulsory)
    ok, err, val = SalesDataValidator.validate_mobile_number("")
    assert ok is True
    assert val == ""


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


def test_optional_fields_acceptance():
    # Accept blank Company Name
    ok, err, val = SalesDataValidator.validate_company_name("   ")
    assert ok is True
    assert val == ""

    # Accept blank Customer Name
    ok, err, val = SalesDataValidator.validate_customer_name("")
    assert ok is True
    assert val == ""

    # Accept blank Company Address
    ok, err, val = SalesDataValidator.validate_company_address("   ")
    assert ok is True
    assert val == ""

    # Accept blank Remark
    ok, err, val = SalesDataValidator.validate_remark("")
    assert ok is True
    assert val == ""


def test_date_validation():
    # Valid DD-MM-YYYY
    ok, err, val = SalesDataValidator.validate_date("02-11-2026")
    assert ok is True
    assert val == "02-11-2026"

    # Valid slash format parsed to DD-MM-YYYY
    ok, err, val = SalesDataValidator.validate_date("02/11/2026")
    assert ok is True
    assert val == "02-11-2026"

    # Blank date defaults to current date
    ok, err, val = SalesDataValidator.validate_date("")
    assert ok is True
    assert val != ""


def test_full_record_validation():
    # Full record with all fields
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

    # Record with blank optional fields is also valid (non-compulsory)
    minimal_record = {
        "Date": "02-11-2026",
        "Company Name": "",
        "Customer Name": "",
        "Company Address": "",
        "Mobile Number": "",
        "Email": "",
        "Remark": "",
        "Status": "Interested",
        "Remark 1": "Follow-up Required",
        "Remark 2": "Customer requested callback tomorrow.",
    }
    res2: ValidationResult = SalesDataValidator.validate_record(minimal_record)
    assert res2.is_valid is True
    assert len(res2.errors) == 0
    assert res2.sanitized_data["Status"] == "Interested"
    assert res2.sanitized_data["Remark 1"] == "Follow-up Required"
    assert res2.sanitized_data["Remark 2"] == "Customer requested callback tomorrow."


def test_status_validation():
    for valid_status in ["Interested", "Not Interested", "Genuine", "interested", "genuine"]:
        ok, err, val = SalesDataValidator.validate_status(valid_status)
        assert ok is True
        assert val in ["Interested", "Not Interested", "Genuine"]

    # Blank status is accepted
    ok, err, val = SalesDataValidator.validate_status("")
    assert ok is True
    assert val == ""


def test_remark_1_validation():
    for valid_rem in ["Contacted", "Follow-up Required", "Quotation Sent", "Unknown"]:
        ok, err, val = SalesDataValidator.validate_remark_1(valid_rem)
        assert ok is True
        assert val != ""

    # Blank remark 1 is accepted
    ok, err, val = SalesDataValidator.validate_remark_1("")
    assert ok is True
    assert val == ""


def test_remark_2_manual_entry():
    custom_note = "Detailed discussion regarding hydraulic fixture package. Follow up on Tuesday."
    ok, err, val = SalesDataValidator.validate_remark_2(custom_note)
    assert ok is True
    assert val == custom_note

    # Blank remark 2 is accepted
    ok, err, val = SalesDataValidator.validate_remark_2("")
    assert ok is True
    assert val == ""
