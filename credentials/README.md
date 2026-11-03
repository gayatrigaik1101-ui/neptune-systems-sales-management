# Neptune Systems - Credentials & Authentication Guide

This directory holds security credentials required to connect the Neptune Systems Sales Dashboard to Google Workspace (Google Forms and Google Sheets).

## ⚠️ Security Policy
1. **NEVER commit credential files (`*.json`) to version control / Git.**
2. **NEVER share private key files publicly or in chat.**
3. **NEVER ask for or use raw Gmail passwords.** Google Workspace APIs use OAuth 2.0 and Service Accounts.

---

## Supported Authentication Modes

### Option 1: Service Account (Recommended for Deployed Streamlit Apps)
A Google Cloud Service Account allows the dashboard to read/write to Google Sheets continuously without expiring tokens.

#### Steps:
1. Go to [Google Cloud Console](https://console.cloud.google.com/) while logged into `mallikarjungokule@gmail.com`.
2. Create or select a project (e.g., `Neptune-Systems-Sales`).
3. Enable **Google Sheets API**, **Google Drive API**, and **Google Forms API** under **APIs & Services > Library**.
4. Go to **APIs & Services > Credentials > Create Credentials > Service Account**.
   - Name: `neptune-sales-service-account`
   - Role: `Editor`
5. Click the created service account, go to the **Keys** tab, click **Add Key > Create new key > JSON**.
6. Download the key and save it as:
   `credentials/service_account.json`
7. **Crucial Step:** Open the Google Spreadsheet (`Neptune Systems – Sales Customer Database`) and share it with the service account email (e.g. `neptune-sales-service-account@<project-id>.iam.gserviceaccount.com`) as an **Editor**.

---

### Option 2: OAuth 2.0 Client ID (For Desktop / Direct User Authorization)
If you prefer running as your personal Google user account:
1. Go to **APIs & Services > Credentials > Create Credentials > OAuth client ID**.
2. Application type: **Desktop App**.
3. Name: `Neptune Systems Sales Client`.
4. Download the JSON and save it as:
   `credentials/client_secret.json`
5. When the application first runs, it will launch a browser window asking `mallikarjungokule@gmail.com` to authorize access. It will automatically save `credentials/token.json` for subsequent silent logins.

---

### Authorized Editing Users
Only **Sagar Sir** and **Tushar Sir** are authorized to access and modify records in the Streamlit Sales Dashboard.
User logins are securely authenticated against hashed passwords and email allowlists configured in `config/settings.json`.
