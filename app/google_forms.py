"""
Neptune Systems - Sales Management System
Google Forms Integration & Generation Engine
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.config import config, PROJECT_ROOT
from app.utils import logger

# Google Forms API Scopes
FORMS_SCOPES = [
    "https://www.googleapis.com/auth/forms.body",
    "https://www.googleapis.com/auth/drive",
]

class GoogleFormsManager:
    """Manages Google Form configuration, API automation, and Google Apps Script generation."""

    FORM_TITLE = "Neptune Systems – Customer & Sales Entry Form"
    FORM_DESCRIPTION = (
        "Use this form to record new customer enquiries and sales interactions. "
        "Enter accurate customer and company information to maintain a centralised sales database."
    )

    FORM_FIELDS = [
        {
            "index": 1,
            "title": "Date",
            "type": "DATE",
            "required": True,
            "description": "Date of customer interaction or entry (DD-MM-YYYY in spreadsheet).",
        },
        {
            "index": 2,
            "title": "Company Name",
            "type": "TEXT",
            "required": True,
            "description": "Registered company or business enterprise name.",
        },
        {
            "index": 3,
            "title": "Customer Name",
            "type": "TEXT",
            "required": True,
            "description": "Full name of the contact person or decision maker.",
        },
        {
            "index": 4,
            "title": "Company Address",
            "type": "PARAGRAPH",
            "required": True,
            "description": "Complete office / workshop / delivery address.",
        },
        {
            "index": 5,
            "title": "Mobile Number",
            "type": "TEXT",
            "required": True,
            "description": "10-digit mobile number (e.g. 9876543210). Numeric only.",
            "regex_validation": r"^[0-9]{10}$",
            "error_message": "Please enter a valid 10-digit numeric mobile number without country code or spaces.",
        },
        {
            "index": 6,
            "title": "Email",
            "type": "TEXT",
            "required": False,
            "description": "Official email address (Optional).",
            "regex_validation": r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$",
            "error_message": "Please enter a valid email address format (e.g. contact@example.com).",
        },
        {
            "index": 7,
            "title": "Remark",
            "type": "PARAGRAPH",
            "required": True,
            "description": "Detailed customer interaction notes, requirements, enquiries, follow-up discussions, and sales updates.",
        },
    ]

    @classmethod
    def generate_apps_script_code(cls) -> str:
        """
        Generates production-ready Google Apps Script (GAS) code.
        When executed in Google account mallikarjungokule@gmail.com at https://script.google.com:
        1. Creates 'Neptune Systems – Sales Customer Database' Google Spreadsheet.
        2. Configures worksheets 'Sales Entries', 'Edit History', 'Dashboard Data'.
        3. Creates 'Neptune Systems – Customer & Sales Entry Form'.
        4. Configures all 7 fields with exact types, mandatory flags, and regex validations.
        5. Links Form responses directly to the spreadsheet.
        6. Sets up onFormSubmit trigger to assign unique Entry ID (NEP-YYYYMMDD-XXXX),
           format Mobile Numbers as plain text, set timestamps, and preserve previous submissions.
        7. Logs the live Google Form URL and Google Spreadsheet URL.
        """
        script = f"""/**
 * NEPTUNE SYSTEMS - GOOGLE WORKSPACE AUTOMATION SCRIPT
 * Account: mallikarjungokule@gmail.com
 *
 * This script creates:
 * 1. Google Form: '{cls.FORM_TITLE}'
 * 2. Google Spreadsheet: 'Neptune Systems – Sales Customer Database'
 * 3. Worksheets: 'Sales Entries', 'Edit History', 'Dashboard Data'
 * 4. Links Form to Spreadsheet with unique Entry ID generator trigger
 */

function setupNeptuneSystemsWorkspace() {{
  Logger.log("=== Starting Neptune Systems Google Workspace Setup ===");

  // 1. CREATE CENTRAL GOOGLE SPREADSHEET
  const spreadsheetName = "Neptune Systems – Sales Customer Database";
  const ss = SpreadsheetApp.create(spreadsheetName);
  const ssId = ss.getId();
  const ssUrl = ss.getUrl();
  Logger.log("Created Spreadsheet: " + ssUrl);

  // Configure Worksheet 1: Sales Entries
  let salesSheet = ss.getSheetByName("Sheet1");
  if (!salesSheet) {{
    salesSheet = ss.insertSheet("Sales Entries");
  }} else {{
    salesSheet.setName("Sales Entries");
  }}

  const salesHeaders = [
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
    "Updated By"
  ];
  salesSheet.appendRow(salesHeaders);
  salesSheet.setFrozenRows(1);
  salesSheet.getRange(1, 1, 1, salesHeaders.length)
    .setFontWeight("bold")
    .setBackground("#1F4E78")
    .setFontColor("#FFFFFF");
  
  // Format column F (Mobile Number) as Plain Text
  salesSheet.getRange("F:F").setNumberFormat("@");

  // Configure Worksheet 2: Edit History
  const historySheet = ss.insertSheet("Edit History");
  const historyHeaders = [
    "History ID",
    "Entry ID",
    "Company Name",
    "Field Changed",
    "Previous Value",
    "New Value",
    "Updated By",
    "Update Date & Time"
  ];
  historySheet.appendRow(historyHeaders);
  historySheet.setFrozenRows(1);
  historySheet.getRange(1, 1, 1, historyHeaders.length)
    .setFontWeight("bold")
    .setBackground("#2E75B6")
    .setFontColor("#FFFFFF");

  // Configure Worksheet 3: Dashboard Data
  const dashSheet = ss.insertSheet("Dashboard Data");
  dashSheet.appendRow(["Metric Key", "Metric Value", "Last Computed"]);
  dashSheet.setFrozenRows(1);
  dashSheet.getRange(1, 1, 1, 3)
    .setFontWeight("bold")
    .setBackground("#5B9BD5")
    .setFontColor("#FFFFFF");

  // 2. CREATE GOOGLE FORM
  const formTitle = "{cls.FORM_TITLE}";
  const form = FormApp.create(formTitle);
  form.setDescription("{cls.FORM_DESCRIPTION}");
  form.setAllowResponseEdits(false);
  form.setCollectEmail(false);
  form.setProgressBar(true);

  // Field 1: Date (Mandatory)
  const dateItem = form.addDateItem();
  dateItem.setTitle("Date")
    .setHelpText("Date of customer interaction or entry (DD-MM-YYYY).")
    .setRequired(true);

  // Field 2: Company Name (Mandatory)
  const compItem = form.addTextItem();
  compItem.setTitle("Company Name")
    .setHelpText("Registered company or enterprise name.")
    .setRequired(true);

  // Field 3: Customer Name (Mandatory)
  const custItem = form.addTextItem();
  custItem.setTitle("Customer Name")
    .setHelpText("Full name of the contact person or decision maker.")
    .setRequired(true);

  // Field 4: Company Address (Mandatory, Paragraph)
  const addrItem = form.addParagraphTextItem();
  addrItem.setTitle("Company Address")
    .setHelpText("Complete office or workshop address.")
    .setRequired(true);

  // Field 5: Mobile Number (Mandatory, 10 Digits Validation)
  const mobileItem = form.addTextItem();
  const mobileValidation = FormApp.createTextValidation()
    .requireTextMatchesPattern("^[0-9]{{10}}$")
    .setHelpText("Must contain exactly 10 numeric digits without spaces or country code.")
    .build();
  mobileItem.setTitle("Mobile Number")
    .setHelpText("10-digit mobile number (e.g. 9876543210).")
    .setRequired(true)
    .setValidation(mobileValidation);

  // Field 6: Email (Optional, Email Validation)
  const emailItem = form.addTextItem();
  const emailValidation = FormApp.createTextValidation()
    .requireTextIsEmail()
    .setHelpText("Must be a valid email format (e.g. info@company.com).")
    .build();
  emailItem.setTitle("Email")
    .setHelpText("Official email address (Optional).")
    .setRequired(false)
    .setValidation(emailValidation);

  // Field 7: Remark (Mandatory, Paragraph)
  const remarkItem = form.addParagraphTextItem();
  remarkItem.setTitle("Remark")
    .setHelpText("Detailed customer interaction notes, requirements, enquiries, and follow-up discussions.")
    .setRequired(true);

  // 3. LINK FORM TO SPREADSHEET
  form.setDestination(FormApp.DestinationType.SPREADSHEET, ssId);

  // 4. INSTALL ON-FORM-SUBMIT TRIGGER TO SYNC FORM RESPONSES TO SALES ENTRIES WITH UNIQUE ENTRY ID
  ScriptApp.newTrigger("handleNeptuneFormSubmit")
    .forSpreadsheet(ss)
    .onFormSubmit()
    .create();

  const publishedUrl = form.getPublishedUrl();
  const editUrl = form.getEditUrl();

  Logger.log("=================================================");
  Logger.log("SUCCESS! NEPTUNE SYSTEMS WORKSPACE CONFIGURED");
  Logger.log("Form Published (Share with Sales Team): " + publishedUrl);
  Logger.log("Form Editor URL: " + editUrl);
  Logger.log("Spreadsheet URL: " + ssUrl);
  Logger.log("Spreadsheet ID: " + ssId);
  Logger.log("=================================================");

  return {{
    spreadsheetId: ssId,
    spreadsheetUrl: ssUrl,
    formPublishedUrl: publishedUrl,
    formEditUrl: editUrl
  }};
}}

/**
 * Handles Form submissions: Formats dates, assigns unique Entry ID,
 * and records into 'Sales Entries' worksheet.
 */
function handleNeptuneFormSubmit(e) {{
  if (!e || !e.values) return;
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const salesSheet = ss.getSheetByName("Sales Entries");
  if (!salesSheet) return;

  const timestamp = e.values[0]; // Submission timestamp
  const dateVal = e.values[1];
  const companyName = e.values[2];
  const customerName = e.values[3];
  const address = e.values[4];
  const mobile = "'" + e.values[5]; // Store as plain text
  const email = e.values[6] || "";
  const remark = e.values[7];

  // Format Date to DD-MM-YYYY
  let formattedDate = dateVal;
  try {{
    const d = new Date(dateVal);
    if (!isNaN(d.getTime())) {{
      const day = ("0" + d.getDate()).slice(-2);
      const month = ("0" + (d.getMonth() + 1)).slice(-2);
      const year = d.getFullYear();
      formattedDate = day + "-" + month + "-" + year;
    }}
  }} catch(err) {{
    formattedDate = dateVal;
  }}

  // Format Created At
  const now = new Date();
  const day = ("0" + now.getDate()).slice(-2);
  const month = ("0" + now.getMonth() + 1).slice(-2);
  const year = now.getFullYear();
  const timeStr = now.toTimeString().split(' ')[0];
  const nowFormatted = day + "-" + month + "-" + year + " " + timeStr;

  // Generate Unique Entry ID: NEP-YYYYMMDD-XXXX
  const datePart = "" + year + month + day;
  const randSuffix = Math.random().toString(36).substring(2, 6).toUpperCase();
  const entryId = "NEP-" + datePart + "-" + randSuffix;

  // Append new row to 'Sales Entries'
  salesSheet.appendRow([
    entryId,
    formattedDate,
    companyName,
    customerName,
    address,
    mobile,
    email,
    remark,
    nowFormatted,
    nowFormatted,
    "Sales Form Submission"
  ]);

  Logger.log("Form submission processed: " + entryId + " for company " + companyName);
}}

/**
 * CLEANS UP ALL DUMMY AND TEST DATA FROM GOOGLE SHEETS
 * Preserves:
 * - Row 1 Header text, colors, font styling, and frozen rows
 * - Plain text column format on Mobile Number (@)
 * - onFormSubmit triggers
 * - Google Form structure and validations
 * 
 * Clears:
 * - All data rows from row 2 downwards in 'Sales Entries'
 * - All data rows from row 2 downwards in 'Edit History'
 * - All data rows from row 2 downwards in 'Dashboard Data'
 * - All test rows from row 2 downwards in 'Form Responses 1' (if present)
 */
function cleanupAllDummyData() {{
  Logger.log("=== Starting Neptune Systems Dummy Data Cleanup ===");
  
  const ssId = "12uDlqhwf2moVgRCZvRnvpTYGa5O6OHAa_rWyME6ZF_4";
  let ss;
  try {{
    ss = SpreadsheetApp.openById(ssId);
  }} catch(e) {{
    ss = SpreadsheetApp.getActiveSpreadsheet();
  }}
  
  if (!ss) {{
    Logger.log("ERROR: Could not open spreadsheet with ID: " + ssId);
    return;
  }}
  
  Logger.log("Connected to Spreadsheet: " + ss.getName());
  
  const sheetsToClean = ["Sales Entries", "Edit History", "Dashboard Data", "Form Responses 1"];
  let totalRowsDeleted = 0;
  
  sheetsToClean.forEach(function(sheetName) {{
    const ws = ss.getSheetByName(sheetName);
    if (!ws) {{
      Logger.log("Sheet '" + sheetName + "' not found, skipping.");
      return;
    }}
    
    const lastRow = ws.getLastRow();
    if (lastRow > 1) {{
      const rowsToDelete = lastRow - 1;
      ws.deleteRows(2, rowsToDelete);
      totalRowsDeleted += rowsToDelete;
      Logger.log("SUCCESS: Cleared " + rowsToDelete + " dummy rows from '" + sheetName + "'. Header preserved.");
    }} else {{
      Logger.log("Sheet '" + sheetName + "' is already clean (only header exists).");
    }}
  }});
  
  Logger.log("=================================================");
  Logger.log("CLEANUP COMPLETE: " + totalRowsDeleted + " total dummy rows deleted.");
  Logger.log("The spreadsheet is clean and ready for live customer entries!");
  Logger.log("=================================================");
}}
"""
        return script

    @classmethod
    def save_apps_script_file(cls) -> Path:
        """Saves generated Apps Script to scripts/setup_neptune_workspace.gs."""
        scripts_dir = PROJECT_ROOT / "scripts"
        scripts_dir.mkdir(parents=True, exist_ok=True)
        file_path = scripts_dir / "setup_neptune_workspace.gs"
        content = cls.generate_apps_script_code()
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        logger.info(f"Saved Google Apps Script to: {file_path}")
        return file_path
