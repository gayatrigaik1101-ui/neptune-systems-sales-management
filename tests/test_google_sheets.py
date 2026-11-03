"""
Unit Tests for Google Sheets Connector and Schema Integrity
"""

import pytest
from app.config import config
from app.google_sheets import sheets_connector


def test_schema_column_definitions():
    sales_cols = config.sales_entries_columns
    expected_sales_cols = [
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
    ]
    assert sales_cols == expected_sales_cols

    history_cols = config.edit_history_columns
    expected_history_cols = [
        "History ID",
        "Entry ID",
        "Company Name",
        "Field Changed",
        "Previous Value",
        "New Value",
        "Updated By",
        "Update Date & Time",
    ]
    assert history_cols == expected_history_cols


def test_local_mirror_persistence():
    # Insert entry into sheets connector
    data = {
        "Date": "02-11-2026",
        "Company Name": "Neptune Systems Test Lab",
        "Customer Name": "Testing Engineer",
        "Company Address": "Neptune Systems HQ",
        "Mobile Number": "9988776655",
        "Email": "test@neptune.com",
        "Remark": "Automated integration test entry.",
    }
    entry_id = sheets_connector.insert_sales_entry(data, created_by="Test Suite")
    assert entry_id is not None

    # Fetch
    res = sheets_connector.fetch_sales_entry_by_id(entry_id)
    assert res is not None
    row_idx, rec = res
    assert rec["Company Name"] == "Neptune Systems Test Lab"
    assert rec["Mobile Number"] == "9988776655"


def test_update_row_preserves_entry_id():
    # Insert
    data = {
        "Date": "02-11-2026",
        "Company Name": "Row Update Verification Corp",
        "Customer Name": "John Doe",
        "Company Address": "Pune IT Park",
        "Mobile Number": "9876543210",
        "Email": "john@rowupdate.com",
        "Remark": "Original remark",
    }
    entry_id = sheets_connector.insert_sales_entry(data, created_by="Test Runner")

    # Update
    updated_fields = {"Remark": "Updated remark text"}
    ok = sheets_connector.update_sales_entry(
        entry_id=entry_id,
        updated_fields=updated_fields,
        editor_user_identity="Sagar Sir",
    )
    assert ok is True

    # Retrieve and verify
    res = sheets_connector.fetch_sales_entry_by_id(entry_id)
    assert res is not None
    _, rec = res
    assert rec["Entry ID"] == entry_id
    assert rec["Remark"] == "Updated remark text"
    assert rec["Updated By"] == "Sagar Sir"
