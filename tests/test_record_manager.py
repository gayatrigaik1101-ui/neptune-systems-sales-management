"""
Unit Tests for Record Manager, Concurrency Control, and Auditing
"""

import pytest
from app.record_manager import RecordManager, ConcurrentEditConflictError
from app.audit_logger import AuditLogger


@pytest.fixture
def manager():
    return RecordManager()


def test_create_and_fetch_record(manager):
    data = {
        "Date": "02-11-2026",
        "Company Name": "Omega Automation Ltd",
        "Customer Name": "Suresh Deshmukh",
        "Company Address": "Sector 10, Chakan Industrial Area, Pune",
        "Mobile Number": "9922334455",
        "Email": "suresh@omegaauto.com",
        "Remark": "Interested in pneumatic controls package.",
    }
    success, msg, entry_id = manager.create_record(data, created_by="Sales Team")
    assert success is True
    assert entry_id is not None
    assert entry_id.startswith("NEP-")

    # Fetch by ID
    rec = manager.get_record_by_id(entry_id)
    assert rec is not None
    assert rec["Company Name"] == "Omega Automation Ltd"
    assert rec["Mobile Number"] == "9922334455"


def test_edit_only_remark(manager):
    # Setup initial record
    data = {
        "Date": "02-11-2026",
        "Company Name": "Precision Gears Pvt Ltd",
        "Customer Name": "Nitin Kulkarni",
        "Company Address": "MIDC Bhosari Pune",
        "Mobile Number": "9811223344",
        "Email": "nitin@precisiongears.com",
        "Remark": "Initial enquiry sent.",
    }
    _, _, entry_id = manager.create_record(data, created_by="Sales Team")
    rec = manager.get_record_by_id(entry_id)
    initial_last_updated = rec["Last Updated"]

    # Edit only Remark
    updated = {"Remark": "Follow-up meeting scheduled for Thursday 2 PM."}
    success, msg, changes = manager.update_record(
        entry_id=entry_id,
        updated_fields=updated,
        editor_identity="Sagar Sir (sagar@neptunesystems.com)",
        expected_last_updated=initial_last_updated,
    )
    assert success is True
    assert len(changes) == 1
    assert changes[0].field_changed == "Remark"
    assert changes[0].previous_value == "Initial enquiry sent."
    assert changes[0].new_value == "Follow-up meeting scheduled for Thursday 2 PM."
    assert changes[0].updated_by == "Sagar Sir (sagar@neptunesystems.com)"

    # Verify original row updated and no duplicate created
    updated_rec = manager.get_record_by_id(entry_id)
    assert updated_rec["Remark"] == "Follow-up meeting scheduled for Thursday 2 PM."
    assert updated_rec["Updated By"] == "Sagar Sir (sagar@neptunesystems.com)"


def test_edit_multiple_fields_and_audit_history(manager):
    data = {
        "Date": "02-11-2026",
        "Company Name": "Kirloskar Brothers Subcontractor",
        "Customer Name": "Amit Rao",
        "Company Address": "Khadki, Pune",
        "Mobile Number": "9766554433",
        "Email": "amit@kirloskar.example",
        "Remark": "Initial demo request.",
    }
    _, _, entry_id = manager.create_record(data, created_by="Sales Team")
    rec = manager.get_record_by_id(entry_id)

    # Edit multiple fields: Customer Name and Mobile Number
    updates = {
        "Customer Name": "Amit R. Rao (Senior VP)",
        "Mobile Number": "9822331100",
        "Remark": "Initial demo completed successfully.",
    }
    success, msg, changes = manager.update_record(
        entry_id=entry_id,
        updated_fields=updates,
        editor_identity="Tushar Sir (tushar@neptunesystems.com)",
        expected_last_updated=rec["Last Updated"],
    )
    assert success is True
    assert len(changes) == 3

    # Check edit history includes these records
    history = manager.get_edit_history(entry_id=entry_id)
    assert len(history) >= 3
    fields_changed = {h["Field Changed"] for h in history}
    assert "Customer Name" in fields_changed
    assert "Mobile Number" in fields_changed
    assert "Remark" in fields_changed


def test_concurrent_edit_conflict_detection(manager):
    import time
    data = {
        "Date": "02-11-2026",
        "Company Name": "Tata Autocomp Vendor",
        "Customer Name": "Vikram Shinde",
        "Company Address": "Talegaon MIDC",
        "Mobile Number": "9850123456",
        "Email": "vikram@tataauto.example",
        "Remark": "Waiting for pricing approval.",
    }
    _, _, entry_id = manager.create_record(data)
    rec = manager.get_record_by_id(entry_id)
    original_timestamp = rec["Last Updated"]

    # Sleep 1.1 seconds so User 1's update has a strictly newer timestamp than original_timestamp
    time.sleep(1.1)

    # User 1 updates record
    manager.update_record(
        entry_id=entry_id,
        updated_fields={"Remark": "Discount of 5% approved by Sagar Sir."},
        editor_identity="Sagar Sir",
        expected_last_updated=original_timestamp,
    )

    # User 2 tries to update using the stale original_timestamp
    with pytest.raises(ConcurrentEditConflictError) as exc_info:
        manager.update_record(
            entry_id=entry_id,
            updated_fields={"Remark": "Discount of 10% requested by client."},
            editor_identity="Tushar Sir",
            expected_last_updated=original_timestamp,  # STALE TIMESTAMP!
        )
    assert "CONCURRENT EDIT CONFLICT" in str(exc_info.value)


def test_delete_record_and_audit(manager):
    data = {
        "Date": "02-11-2026",
        "Company Name": "Delete Target Industries",
        "Customer Name": "Ramesh Pawar",
        "Company Address": "Hadapsar Industrial Estate",
        "Mobile Number": "9822998877",
        "Email": "ramesh@deletetarget.com",
        "Remark": "Lead entered by error.",
    }
    _, _, entry_id = manager.create_record(data)
    assert manager.get_record_by_id(entry_id) is not None

    # Delete record
    success, msg = manager.delete_record(entry_id, deleted_by="Sagar Sir")
    assert success is True
    assert "permanently deleted" in msg

    # Verify record is no longer retrieved
    assert manager.get_record_by_id(entry_id) is None

    # Verify audit history records deletion
    history = manager.get_edit_history(entry_id=entry_id)
    assert len(history) >= 1
    assert any(h["Field Changed"] == "RECORD_STATUS" and h["New Value"] == "DELETED" for h in history)
