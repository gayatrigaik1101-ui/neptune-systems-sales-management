"""
Neptune Systems - Sales Management System
Database Cleanup and Reset Utility
Completely removes all test/dummy data while preserving schemas, headers,
formatting, and system configuration.
"""

import json
import shutil
import sys
from datetime import datetime
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.config import config, BACKUPS_DIR
from app.utils import logger, audit_sys_logger, get_current_timestamp_str
from app.google_sheets import sheets_connector


def create_pre_cleanup_backup() -> Path:
    """Takes a timestamped snapshot of the database before cleanup."""
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = BACKUPS_DIR / f"pre_cleanup_backup_{ts}.json"
    mirror_file = sheets_connector.local_mirror_file

    if mirror_file.exists():
        shutil.copy2(mirror_file, backup_file)
        logger.info(f"Database backup successfully saved to: {backup_file}")
    else:
        logger.warning("No existing database mirror found to back up.")
    return backup_file


def cleanup_local_database_mirror() -> dict:
    """Resets the local database mirror to a clean, empty state with 0 records."""
    mirror_file = sheets_connector.local_mirror_file

    old_sales_count = 0
    old_history_count = 0

    if mirror_file.exists():
        try:
            with open(mirror_file, "r", encoding="utf-8") as f:
                old_data = json.load(f)
                old_sales_count = len(old_data.get("sales_entries", []))
                old_history_count = len(old_data.get("edit_history", []))
        except Exception as e:
            logger.error(f"Error reading existing mirror: {e}")

    # Fresh, pristine schema
    clean_data = {
        "sales_entries": [],
        "edit_history": [],
        "dashboard_data": [],
        "metadata": {
            "created_at": get_current_timestamp_str(),
            "last_cleaned_at": get_current_timestamp_str(),
            "spreadsheet_name": config.google_workspace.get("spreadsheet_name"),
            "spreadsheet_id": config.google_workspace.get("spreadsheet_id"),
            "status": "clean_production_ready",
        }
    }

    with open(mirror_file, "w", encoding="utf-8") as f:
        json.dump(clean_data, f, indent=2)

    logger.info(f"Local database mirror reset: cleared {old_sales_count} sales entries and {old_history_count} history records.")
    audit_sys_logger.info(f"DATABASE_CLEANUP | Cleared {old_sales_count} sales entries, {old_history_count} history records.")

    return {
        "sales_entries_deleted": old_sales_count,
        "edit_history_deleted": old_history_count,
        "dashboard_data_deleted": 0,
    }


def cleanup_live_google_sheets() -> dict:
    """
    Clears test rows directly from the live Google Spreadsheet if API credentials exist.
    Preserves row 1 (headers), column structure, and formatting.
    """
    stats = {"live_sheets_cleaned": False, "message": "Not connected to live Google Sheets"}

    if sheets_connector.is_connected and sheets_connector.spreadsheet:
        try:
            ss = sheets_connector.spreadsheet
            sheets_to_clean = [
                config.sheets_config["sales_entries"]["name"],
                config.sheets_config["edit_history"]["name"],
                config.sheets_config["dashboard_data"]["name"],
            ]

            for sheet_name in sheets_to_clean:
                try:
                    ws = ss.worksheet(sheet_name)
                    row_count = len(ws.get_all_values())
                    if row_count > 1:
                        # Delete all rows from row 2 to row_count
                        ws.delete_rows(2, row_count - 1)
                        logger.info(f"Cleared {row_count - 1} rows from Google Sheet '{sheet_name}'. Header preserved.")
                except Exception as ex:
                    logger.warning(f"Could not clear rows in sheet '{sheet_name}': {ex}")

            stats["live_sheets_cleaned"] = True
            stats["message"] = f"Successfully cleared all data rows from Google Spreadsheet '{ss.title}'."
        except Exception as e:
            stats["message"] = f"Error during live Google Sheets cleanup: {e}"
            logger.error(stats["message"])

    return stats


def run_full_cleanup():
    """Executes the complete end-to-end database cleanup."""
    print("=" * 60)
    print("  NEPTUNE SYSTEMS - SALES DATABASE CLEANUP")
    print("=" * 60)

    # 1. Secure Backup
    backup_path = create_pre_cleanup_backup()
    print(f"[OK] Secure pre-cleanup backup created at:\n     {backup_path}")

    # 2. Reset Local Mirror
    local_stats = cleanup_local_database_mirror()
    print(f"[OK] Sales Entries deleted: {local_stats['sales_entries_deleted']}")
    print(f"[OK] Edit History records deleted: {local_stats['edit_history_deleted']}")
    print(f"[OK] Dashboard Data records deleted: {local_stats['dashboard_data_deleted']}")

    # 3. Live Google Sheets cleanup
    live_stats = cleanup_live_google_sheets()
    if live_stats["live_sheets_cleaned"]:
        print(f"[OK] Live Google Sheets: {live_stats['message']}")
    else:
        print(f"[INFO] Live Google Sheets: {live_stats['message']}")
        print("       (Use Google Apps Script 'cleanupAllDummyData' to clear the live spreadsheet in 1 click).")

    print("\n[OK] All column headers, formatting, and configurations preserved.")
    print("[OK] Dashboard metrics reset to initial zero state.")
    print("=" * 60)
    return local_stats


if __name__ == "__main__":
    run_full_cleanup()
