"""
Migrates Neptune Systems Google Spreadsheet to the updated schema:
Columns: ['Sr. No.', 'Date', 'Company Name', 'Customer Name', 'Company Address',
          'Mobile Number', 'Email', 'Status', 'Remark 1', 'Remark 2',
          'Created At', 'Last Updated', 'Updated By', 'Record ID']
"""

import sys
from app.config import config
from app.google_sheets import sheets_connector
from app.utils import logger, STATUS_OPTIONS, REMARK_1_OPTIONS

def migrate():
    print("Connecting to Google Sheets...")
    if not sheets_connector.is_connected or not sheets_connector.spreadsheet:
        print("Error: Could not connect to Google Spreadsheet!")
        sys.exit(1)

    ss = sheets_connector.spreadsheet
    print(f"Connected to Spreadsheet: '{ss.title}'")

    ws = ss.worksheet(config.sheets_config["sales_entries"]["name"])
    print("Running upgrade_sales_entries_schema on 'Sales Entries'...")
    sheets_connector.upgrade_sales_entries_schema(ws)

    # Apply Data Validation dropdowns for Status (col H = 8) and Remark 1 (col I = 9) in Google Sheets
    try:
        from gspread.utils import a1_to_rowcol
        print("Setting data validation rules in Google Sheets for Status and Remark 1...")
        sheet_id = ws.id
        requests = [
            # Dropdown for Status: Column H (col 8, index 7)
            {
                "setDataValidation": {
                    "range": {
                        "sheetId": sheet_id,
                        "startRowIndex": 1,
                        "startColumnIndex": 7,
                        "endColumnIndex": 8,
                    },
                    "rule": {
                        "condition": {
                            "type": "ONE_OF_LIST",
                            "values": [{"userEnteredValue": opt} for opt in STATUS_OPTIONS],
                        },
                        "showCustomUi": True,
                        "strict": False,
                    },
                }
            },
            # Dropdown for Remark 1: Column I (col 9, index 8)
            {
                "setDataValidation": {
                    "range": {
                        "sheetId": sheet_id,
                        "startRowIndex": 1,
                        "startColumnIndex": 8,
                        "endColumnIndex": 9,
                    },
                    "rule": {
                        "condition": {
                            "type": "ONE_OF_LIST",
                            "values": [{"userEnteredValue": opt} for opt in REMARK_1_OPTIONS],
                        },
                        "showCustomUi": True,
                        "strict": False,
                    },
                }
            },
        ]
        ss.batch_update({"requests": requests})
        print("Data validation rules applied successfully!")
    except Exception as e:
        print(f"Note: Could not set Google Sheets native validation (non-blocking): {e}")

    # Verify rows
    updated_records = ws.get_all_records(default_blank="")
    print(f"Migration complete! Total rows in Google Sheets: {len(updated_records)}")
    if updated_records:
        print("Sample row 1:")
        print(updated_records[0])

if __name__ == "__main__":
    migrate()
