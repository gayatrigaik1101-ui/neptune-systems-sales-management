# Neptune Systems – Sales Entry & Management System
### Google Workspace + Python Streamlit Business Automation Platform

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Streamlit](https://img.shields.io/badge/streamlit-1.45+-FF4B4B.svg)](https://streamlit.io)
[![Google Workspace](https://img.shields.io/badge/Google%20Workspace-Integrated-4285F4.svg)](https://workspace.google.com)
[![License](https://img.shields.io/badge/license-Proprietary-red.svg)]()

---

## 1. Project Overview & Architecture

The **Neptune Systems Sales Management System** is an enterprise sales relationship and lead management automation solution designed for Neptune Systems. It automates customer data collection from field sales representatives, maintains a single source of truth in Google Sheets, and provides a secure, role-restricted dashboard for authorized management (**Sagar Sir** and **Tushar Sir**) to review, search, update, and audit customer interactions in real time.

### End-to-End Architecture:
```text
  SALES TEAM (Field Representatives)
            │
            ▼
  GOOGLE FORM ("Neptune Systems – Customer & Sales Entry Form")
            │ (Automated Submission)
            ▼
  GOOGLE SHEETS CENTRAL DATABASE ("Neptune Systems – Sales Customer Database")
            │
      ┌─────┴───────────────────────────────────┐
      ▼                                         ▼
  Worksheet 1: "Sales Entries"             Worksheet 2: "Edit History"
      │ (Real-time Central Sync)                ▲ (Atomic Audit Trail)
      ▼                                         │
  PYTHON STREAMLIT DASHBOARD ───────────────────┘
      │
      ▼
  SECURE AUTHENTICATION (Bcrypt + Strict Email Allowlist)
      │
      ├───────────────────────┬───────────────────────┐
      ▼                       ▼                       ▼
  SAGAR SIR               TUSHAR SIR                ADMIN
  (sagar@neptunesystems)  (tushar@neptunesystems)   (mallikarjungokule@gmail.com)
      │                       │
      ▼                       ▼
  SEARCH / REVIEW / EDIT / DELETE CUSTOMER DETAILS
      │
      ▼
  OPTIMISTIC CONCURRENCY LOCK (Collision Detection)
      │
      ▼
  UPDATE ORIGINAL GOOGLE SHEETS ROW (In-Place, No Duplicates)
```

---

## 2. Key Features

- **Field Lead Ingestion**: 100% genuine Google Forms integration with strict regex validation (10-digit mobile number, formatted email, mandatory fields).
- **Central Google Sheets Database**: Structured into 3 dedicated worksheets:
  - `Sales Entries`: 11 standardized columns with unique ID (`NEP-YYYYMMDD-XXXX`), plain-text formatted mobile numbers, and timestamps.
  - `Edit History`: Tamper-evident field-level audit trail logging previous vs. new values, editor identity, and exact timestamp.
  - `Dashboard Data`: Aggregated metrics and cached reporting.
- **Optimistic Concurrency Protection**: Prevents simultaneous edit collisions between Sagar Sir and Tushar Sir by detecting timestamp divergence.
- **In-Place Row Updates**: Modifies the exact customer row; never creates duplicate records during edits.
- **Dual Edit Modes**: Support for rapid "Quick Edit Remark Only" or "Full Customer Record Edit".
- **Safe Customer Deletion**: Double-confirmed record deletion with automatic audit trail recording in `Edit History`.
- **Multi-Factor User Security**: Bcrypt hashed passwords, session timeout management, and strict verified email allowlists.

---

## 3. Technology Stack

- **Frontend & App Framework**: Streamlit 1.45+
- **Backend & Business Logic**: Python 3.10+
- **Database & Spreadsheets**: Google Sheets API v4, `gspread`, Google Apps Script
- **Form Automation**: Google Forms API, Google Apps Script
- **Security & Cryptography**: `bcrypt` (12 rounds), Python `hashlib`, Session State
- **Data Engineering**: `pandas`, `openpyxl`
- **Testing**: `pytest` (with session-level database isolation fixture)
- **Deployment**: Streamlit Community Cloud / Private Linux/Windows Server / Docker

---

## 4. Project Directory Structure

```text
Neptune_Systems_Sales_Management/
│
├── .streamlit/
│   └── config.toml              # Corporate theme configuration
│
├── app/
│   ├── __init__.py              # Python package marker
│   ├── main.py                  # Main Streamlit application entrypoint & auth gateway
│   ├── dashboard.py             # UI views, metric cards, tables, search & edit forms
│   ├── config.py                # Configuration loader & Streamlit secrets binding
│   ├── google_forms.py          # Form schemas & Apps Script automation generator
│   ├── google_sheets.py         # Google Sheets API connector & mirror engine
│   ├── authentication.py        # Bcrypt auth, session management & email allowlist
│   ├── validation.py            # Strict business rules validation engine
│   ├── record_manager.py        # Business logic, optimistic locking & search
│   ├── audit_logger.py          # Field-level diff generator & audit history
│   └── utils.py                 # ID generators, timestamp formatting & logging
│
├── config/
│   └── settings.json            # Central application settings & user definitions
│
├── credentials/
│   └── README.md                # Credentials security policy & setup guide
│
├── logs/
│   └── .gitkeep                 # Runtime logs directory (excluded from git)
│
├── backups/
│   └── .gitkeep                 # Backup mirror directory (excluded from git)
│
├── scripts/
│   ├── setup_neptune_workspace.gs # 1-Click Google Workspace Deployment Script
│   └── cleanup_database.py      # Automated database reset and cleanup utility
│
├── tests/
│   ├── __init__.py              # Python test package marker
│   ├── conftest.py              # Pytest isolation fixture
│   ├── test_validation.py       # Unit tests for input validation rules
│   ├── test_authentication.py   # Unit tests for passwords & user allowlist
│   ├── test_record_manager.py   # Tests for diffs, updates, deletion & conflicts
│   └── test_google_sheets.py    # Tests for schema consistency & row updates
│
├── .env.example                 # Environment variables template
├── .gitignore                   # Excludes credentials, logs, and venvs
├── requirements.txt             # Python dependencies
├── README.md                    # Project documentation
├── setup.py                     # Python package configuration
├── run.bat                      # Windows interactive menu runner
└── start_dashboard.bat          # 1-Click Streamlit dashboard launch script
```

---

## 5. Local Installation & Setup

### Prerequisites
- Python 3.10, 3.11, 3.12, or 3.13
- Git

### 1. Clone the Private Repository
```bash
git clone https://github.com/gayatrigaik1101-ui/neptune-systems-sales-management.git
cd neptune-systems-sales-management
```

### 2. Create and Activate Virtual Environment
```bash
# Windows
python -m venv .venv
.venv\Scripts\activate

# Linux / macOS
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Environment
Copy `.env.example` to `.env`:
```bash
copy .env.example .env
```
Update your Google Spreadsheet ID, Google Form URL, and authorized emails inside `.env`.

### 5. Launch Application
```bash
# Windows 1-click
start_dashboard.bat

# Or command line
python -m streamlit run app/main.py --server.port 8501
```
Open **`http://localhost:8501`** in your browser.

---

## 6. Google Workspace Integration Setup

The application is linked to Google account **`mallikarjungokule@gmail.com`**.

### 1-Click Automated Setup via Google Apps Script:
1. Open [https://script.google.com](https://script.google.com) under `mallikarjungokule@gmail.com`.
2. Create a **New project** named `Neptune Systems Automation`.
3. Paste the contents of [`scripts/setup_neptune_workspace.gs`](scripts/setup_neptune_workspace.gs) into the editor.
4. Select function **`setupNeptuneSystemsWorkspace`** and click **Run**.
5. Grant standard permissions.
6. The script creates the **Form** and **Spreadsheet**, configures worksheets, links them, and outputs:
   - **Google Form Published URL** (to share with sales team)
   - **Google Spreadsheet URL** (`Neptune Systems – Sales Customer Database`)
   - **Google Spreadsheet ID**

---

## 7. Streamlit Community Cloud Deployment

To deploy to [Streamlit Community Cloud](https://share.streamlit.io):

1. Go to **[https://share.streamlit.io](https://share.streamlit.io)** and sign in with GitHub account **`gayatrigaik1101-ui`**.
2. Click **"New app"**.
3. Select:
   - **Repository:** `gayatrigaik1101-ui/neptune-systems-sales-management`
   - **Branch:** `main`
   - **Main file path:** `app/main.py`
4. Click **"Advanced settings"** and navigate to **Secrets**.
5. Paste your environment secrets in TOML format:

```toml
# General Configuration
GOOGLE_ACCOUNT = "mallikarjungokule@gmail.com"
GOOGLE_SPREADSHEET_ID = "12uDlqhwf2moVgRCZvRnvpTYGa5O6OHAa_rWyME6ZF_4"
GOOGLE_SPREADSHEET_NAME = "Neptune Systems – Sales Customer Database"
GOOGLE_FORM_URL = "https://docs.google.com/forms/d/1yKen6MLCxqW1yEaibFI1oS06w8FK9R-k1JjQxEJm0MA/viewform"
GOOGLE_AUTH_MODE = "service_account"

# Authorized Users
SAGAR_SIR_EMAIL = "sagar@neptunesystems.com"
TUSHAR_SIR_EMAIL = "tushar@neptunesystems.com"
ADMIN_EMAIL = "mallikarjungokule@gmail.com"

# Google Cloud Service Account (for live Sheets API sync)
[gcp_service_account]
type = "service_account"
project_id = "your-gcp-project-id"
private_key_id = "your-private-key-id"
private_key = "-----BEGIN PRIVATE KEY-----\nMIIEvgIBA...\n-----END PRIVATE KEY-----\n"
client_email = "neptune-sales@your-gcp-project.iam.gserviceaccount.com"
client_id = "1234567890"
auth_uri = "https://accounts.google.com/o/oauth2/auth"
token_uri = "https://oauth2.googleapis.com/token"
```

6. Click **Deploy!**
7. Streamlit Cloud will build the container and provide your live HTTPS URL.

---

## 8. User Authentication & Default Credentials

| User | Username / Email | Role | Default Password |
|---|---|---|---|
| **Sagar Sir** | `sagar` or `sagar@neptunesystems.com` | Sales Manager | `Sagar@Neptune2026` |
| **Tushar Sir** | `tushar` or `tushar@neptunesystems.com` | Sales Manager | `Tushar@Neptune2026` |
| **Admin** | `mallikarjun` or `mallikarjungokule@gmail.com` | Administrator | `Admin@Neptune2026` |

> [!IMPORTANT]
> Passwords should be changed in production by generating a new Bcrypt hash via `AuthManager.hash_password("NewPassword")` and updating `config/settings.json` or Streamlit Secrets.

---

## 9. Automated Testing Suite

Execute the comprehensive test suite locally:
```bash
pytest tests/ -v
```

### Verified Test Cases:
| Module | Test Case | Status | Verified Functionality |
|---|---|---|---|
| `test_authentication.py` | `test_authenticate_sagar_sir` | ✅ PASS | Password verification & role assignment |
| `test_authentication.py` | `test_authenticate_tushar_sir` | ✅ PASS | Password verification & role assignment |
| `test_authentication.py` | `test_authenticate_by_email` | ✅ PASS | Login using registered email address |
| `test_authentication.py` | `test_reject_wrong_password` | ✅ PASS | Rejection of invalid credentials |
| `test_authentication.py` | `test_reject_unauthorized_user` | ✅ PASS | Rejection of unregistered users |
| `test_authentication.py` | `test_authorized_email_allowlist` | ✅ PASS | Strict email allowlist verification |
| `test_google_sheets.py` | `test_schema_column_definitions` | ✅ PASS | 11 sales columns & 8 history columns |
| `test_google_sheets.py` | `test_local_mirror_persistence` | ✅ PASS | Read/write local backup persistence |
| `test_google_sheets.py` | `test_update_row_preserves_entry_id`| ✅ PASS | In-place row update; preserves Entry ID |
| `test_record_manager.py` | `test_create_and_fetch_record` | ✅ PASS | Generates unique ID (`NEP-YYYYMMDD-XXXX`) |
| `test_record_manager.py` | `test_edit_only_remark` | ✅ PASS | Atomic update & history record creation |
| `test_record_manager.py` | `test_edit_multiple_fields_and_audit_history` | ✅ PASS | Multi-field diff tracking |
| `test_record_manager.py` | `test_concurrent_edit_conflict_detection` | ✅ PASS | Stale timestamp collision detection |
| `test_record_manager.py` | `test_delete_record_and_audit` | ✅ PASS | Safe deletion & audit entry logging |
| `test_validation.py` | `test_mobile_number_validation` | ✅ PASS | Rejects invalid phone lengths & non-digits |
| `test_validation.py` | `test_email_validation` | ✅ PASS | Validates email syntax; allows blank |
| `test_validation.py` | `test_mandatory_fields_rejection` | ✅ PASS | Rejects blank Company, Customer, Address |
| `test_validation.py` | `test_date_validation` | ✅ PASS | Normalizes DD-MM-YYYY format |
| `test_validation.py` | `test_full_record_validation` | ✅ PASS | Full record sanitization and validation |

**Results: 19 / 19 Tests Passed (100% Pass Rate)**

---

## 10. Troubleshooting Guide

| Issue | Root Cause | Solution |
|---|---|---|
| Dashboard shows "🟡 Local Mirror Active" | Google service account key not yet placed or sheet not shared | Add `[gcp_service_account]` into Streamlit Secrets or place `credentials/service_account.json` locally and share sheet with service account email. |
| "CONCURRENT EDIT CONFLICT" error when saving | Another user saved changes while your form was open | Click Cancel or refresh the customer record to review the newer information before updating. |
| Mobile number formatting dropped in Google Sheets | Sheets auto-converted to number | The system automatically prefixes with apostrophe (`'`) so numbers are stored as literal text `@`. |
| "Authentication Failed" for Sagar Sir or Tushar Sir | Incorrect password or email not in settings | Check `config/settings.json` or reset password using `AuthManager.hash_password()`. |
| Pytest modifies production data | Missing isolation fixture | `tests/conftest.py` automatically routes all test operations to an isolated temporary sandbox. |
