"""
Neptune Systems - Sales Management System
Streamlit Dashboard Views & Navigation Engine
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
import pandas as pd
import streamlit as st

from app.config import config
from app.utils import clean_string, get_current_date_str
from app.validation import SalesDataValidator, ValidationResult
from app.authentication import get_current_user, logout_user, auth_manager
from app.record_manager import record_manager, ConcurrentEditConflictError
from app.google_sheets import sheets_connector
from app.audit_logger import AuditLogger


def apply_custom_css() -> None:
    """Applies modern Neptune Systems corporate styling."""
    st.markdown(
        """
        <style>
        /* Main background and fonts */
        .main {
            background-color: #F8FAFC;
        }
        /* Top header brand styling */
        .neptune-brand-header {
            background: linear-gradient(135deg, #0F172A 0%, #1E3A8A 50%, #0369A1 100%);
            color: white;
            padding: 1.5rem 2rem;
            border-radius: 12px;
            margin-bottom: 1.5rem;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
        }
        .neptune-brand-header h1 {
            color: #FFFFFF;
            font-size: 1.8rem;
            font-weight: 700;
            margin: 0;
            padding: 0;
            letter-spacing: -0.5px;
        }
        .neptune-brand-header p {
            color: #BAE6FD;
            font-size: 0.95rem;
            margin: 0.25rem 0 0 0;
        }

        /* Metric card styling */
        .metric-card {
            background: #FFFFFF;
            border-radius: 10px;
            padding: 1.25rem;
            border: 1px solid #E2E8F0;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.04);
            text-align: center;
        }
        .metric-card-title {
            color: #64748B;
            font-size: 0.85rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 0.5rem;
        }
        .metric-card-value {
            color: #0F172A;
            font-size: 2rem;
            font-weight: 700;
            margin: 0;
        }

        /* Custom diff preview styling */
        .diff-container {
            background: #F1F5F9;
            border-left: 4px solid #0284C7;
            padding: 1rem;
            border-radius: 6px;
            margin: 1rem 0;
        }
        .diff-old {
            color: #DC2626;
            text-decoration: line-through;
            background: #FEE2E2;
            padding: 2px 6px;
            border-radius: 4px;
        }
        .diff-new {
            color: #16A34A;
            font-weight: 600;
            background: #DCFCE7;
            padding: 2px 6px;
            border-radius: 4px;
        }

        /* Status badges */
        .badge-live {
            background-color: #DCFCE7;
            color: #15803D;
            padding: 4px 10px;
            border-radius: 9999px;
            font-weight: 600;
            font-size: 0.8rem;
            display: inline-block;
        }
        .badge-mirror {
            background-color: #FEF3C7;
            color: #B45309;
            padding: 4px 10px;
            border-radius: 9999px;
            font-weight: 600;
            font-size: 0.8rem;
            display: inline-block;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_header(current_user: Any) -> None:
    """Renders Neptune Systems top bar with connection status."""
    conn_badge = (
        '<span class="badge-live">🟢 Live Google Sheets</span>'
        if sheets_connector.is_connected
        else '<span class="badge-mirror">🟡 Local Mirror Active</span>'
    )

    st.markdown(
        f"""
        <div class="neptune-brand-header">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <div>
                    <h1>NEPTUNE SYSTEMS</h1>
                    <p>Sales Entry & Customer Relationship Management Portal</p>
                </div>
                <div style="text-align: right;">
                    {conn_badge}<br>
                    <span style="font-size: 0.85rem; color: #E0F2FE;">
                        User: <strong>{current_user.display_name}</strong> ({current_user.email})
                    </span>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_sidebar(current_user: Any) -> str:
    """Renders navigation sidebar and user controls."""
    with st.sidebar:
        st.image(
            "https://img.icons8.com/fluency/96/commercial.png",
            width=64,
        )
        st.markdown(f"### **{current_user.display_name}**")
        st.caption(f"Role: {current_user.role.replace('_', ' ').title()}")
        st.caption(f"Email: {current_user.email}")
        st.divider()

        nav_options = [
            "📊 Overview",
            "📋 All Sales Entries",
            "🔍 Search Customer",
            "✏️ Edit Customer Details",
            "📜 Edit History",
            "⚙️ Google Setup Guide",
        ]

        # Check if selected from another action
        default_index = 0
        active_nav = st.session_state.get("active_nav", "Overview")
        for i, opt in enumerate(nav_options):
            if active_nav in opt:
                default_index = i
                break

        selected_page = st.radio("Navigation", nav_options, index=default_index)

        st.divider()

        # Database sync status
        st.markdown("**Database Status**")
        if sheets_connector.is_connected:
            st.success(f"Connected: {sheets_connector.connection_mode}")
        else:
            st.warning("Mirror Mode (Pending Google Auth)")
            st.caption("See 'Google Setup Guide' to link your Google Spreadsheet.")

        if st.button("🔄 Sync with Google Sheets", use_container_width=True):
            sheets_connector.connect()
            st.rerun()

        st.divider()
        if st.button("🚪 Logout", use_container_width=True, type="secondary"):
            logout_user()
            st.rerun()

        return selected_page


# =============================================================================
# VIEW 1: OVERVIEW
# =============================================================================

def view_overview() -> None:
    """Renders business metrics and overview cards."""
    st.subheader("Executive Sales Overview")

    metrics = record_manager.get_overview_metrics()

    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-card-title">Total Entries</div>
                <div class="metric-card-value">{metrics['total_entries']}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with c2:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-card-title">Total Companies</div>
                <div class="metric-card-value" style="color: #0369A1;">{metrics['total_companies']}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with c3:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-card-title">Added Today</div>
                <div class="metric-card-value" style="color: #15803D;">{metrics['entries_added_today']}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with c4:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-card-title">Updated Today</div>
                <div class="metric-card-value" style="color: #7C3AED;">{metrics['entries_updated_today']}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with c5:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-card-title">Follow-ups Due</div>
                <div class="metric-card-value" style="color: #B45309;">{metrics['requiring_followup']}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("<br>", unsafe_allow_html=True)

    # Recent entries overview
    all_records = record_manager.get_all_records(sort_by_date=True)
    if all_records:
        st.markdown("#### **Recent Customer Entries**")
        df = pd.DataFrame(all_records)
        display_cols = [
            col for col in [
                "Entry ID", "Date", "Company Name", "Customer Name",
                "Mobile Number", "Remark", "Last Updated", "Updated By"
            ] if col in df.columns
        ]
        st.dataframe(df[display_cols].head(10), use_container_width=True, hide_index=True)
    else:
        st.info("No customer entries recorded yet. Use the Google Form or Add New Entry below to record leads.")

    # Quick Sales Entry Form for testing/direct entry
    with st.expander("➕ Direct Customer Entry (Sales Representative Form)"):
        with st.form("direct_entry_form"):
            fc1, fc2 = st.columns(2)
            with fc1:
                e_date = st.date_input("Date *", value=datetime.now())
                e_comp = st.text_input("Company Name *")
                e_cust = st.text_input("Customer Name *")
                e_addr = st.text_area("Company Address *")
            with fc2:
                e_mobile = st.text_input("Mobile Number * (10 digits)", max_chars=10)
                e_email = st.text_input("Email (Optional)")
                e_remark = st.text_area("Remark *", help="Enquiries, notes, follow-up actions")

            submitted = st.form_submit_button("Submit Customer Record", type="primary")
            if submitted:
                payload = {
                    "Date": e_date.strftime("%d-%m-%Y"),
                    "Company Name": e_comp,
                    "Customer Name": e_cust,
                    "Company Address": e_addr,
                    "Mobile Number": e_mobile,
                    "Email": e_email,
                    "Remark": e_remark,
                }
                success, msg, entry_id = record_manager.create_record(payload, created_by="Dashboard Form")
                if success:
                    st.success(f"{msg}")
                    st.rerun()
                else:
                    st.error(msg)


# =============================================================================
# VIEW 2: ALL SALES ENTRIES
# =============================================================================

def view_all_entries() -> None:
    """Renders table of all sales records with filters, search, and pagination."""
    st.subheader("All Customer Sales Entries")

    all_records = record_manager.get_all_records(sort_by_date=True)

    c1, c2, c3 = st.columns([3, 1, 1])
    with c1:
        search_query = st.text_input("🔍 Quick search by Company, Customer, Phone, or ID...", "")
    with c2:
        sort_choice = st.selectbox("Sort By", ["Newest Date First", "Oldest Date First", "Company A-Z"])
    with c3:
        page_size = st.selectbox("Rows per page", [10, 25, 50, 100], index=1)

    if not all_records:
        st.info("The sales database is currently empty.")
        return

    # Filter records
    filtered = all_records
    if search_query:
        filtered = record_manager.search_records(general_query=search_query)

    if sort_choice == "Oldest Date First":
        filtered = list(reversed(filtered))
    elif sort_choice == "Company A-Z":
        filtered = sorted(filtered, key=lambda x: clean_string(x.get("Company Name", "")).lower())

    st.caption(f"Showing {len(filtered)} matching records out of {len(all_records)} total.")

    df = pd.DataFrame(filtered)
    columns_order = config.sales_entries_columns
    available_cols = [c for c in columns_order if c in df.columns]

    # Pagination logic
    total_pages = max(1, (len(filtered) - 1) // page_size + 1)
    if total_pages > 1:
        page_num = st.number_input("Page", min_value=1, max_value=total_pages, value=1)
    else:
        page_num = 1

    start_idx = (page_num - 1) * page_size
    end_idx = start_idx + page_size
    page_records = filtered[start_idx:end_idx]

    # Display table
    page_df = pd.DataFrame(page_records)
    if not page_df.empty:
        st.dataframe(page_df[available_cols], use_container_width=True, hide_index=True)

    # Action selector to edit
    st.divider()
    st.markdown("#### **Select Record to Edit**")
    entry_id_list = [r.get("Entry ID") for r in page_records if r.get("Entry ID")]
    if entry_id_list:
        ec1, ec2 = st.columns([3, 1])
        with ec1:
            chosen_id = st.selectbox("Choose Entry ID to edit:", entry_id_list)
        with ec2:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("✏️ Edit Selected Record", type="primary"):
                st.session_state["selected_entry_id"] = chosen_id
                st.session_state["active_nav"] = "Edit Customer Details"
                st.rerun()


# =============================================================================
# VIEW 3: SEARCH CUSTOMER
# =============================================================================

def view_search() -> None:
    """Renders comprehensive search interface."""
    st.subheader("Search Customer Records")

    with st.container():
        sc1, sc2, sc3 = st.columns(3)
        with sc1:
            q_id = st.text_input("Entry ID", placeholder="e.g. NEP-20261102-...")
            q_comp = st.text_input("Company Name", placeholder="e.g. Apex Engineering")
        with sc2:
            q_cust = st.text_input("Customer Name", placeholder="e.g. Rahul Patil")
            q_mob = st.text_input("Mobile Number", placeholder="e.g. 9822012345")
        with sc3:
            q_date = st.text_input("Date (DD-MM-YYYY)", placeholder="e.g. 02-11-2026")
            st.markdown("<br>", unsafe_allow_html=True)
            search_clicked = st.button("🔍 Search Database", type="primary", use_container_width=True)

    results = record_manager.search_records(
        entry_id=q_id,
        company_name=q_comp,
        customer_name=q_cust,
        mobile_number=q_mob,
        date_str=q_date,
    )

    st.divider()
    st.markdown(f"#### Results ({len(results)} found)")

    if not results:
        st.warning("No records matched your search criteria.")
        return

    for rec in results:
        with st.expander(f"🏢 **{rec.get('Company Name')}** | {rec.get('Customer Name')} (ID: {rec.get('Entry ID')})"):
            c1, c2 = st.columns(2)
            with c1:
                st.write(f"**Date:** {rec.get('Date')}")
                st.write(f"**Mobile Number:** {rec.get('Mobile Number')}")
                st.write(f"**Email:** {rec.get('Email') or 'None'}")
                st.write(f"**Company Address:** {rec.get('Company Address')}")
            with c2:
                st.write(f"**Remark:** {rec.get('Remark')}")
                st.write(f"**Created At:** {rec.get('Created At')}")
                st.write(f"**Last Updated:** {rec.get('Last Updated')}")
                st.write(f"**Updated By:** {rec.get('Updated By')}")

            if st.button(f"✏️ Edit Record {rec.get('Entry ID')}", key=f"btn_edit_{rec.get('Entry ID')}"):
                st.session_state["selected_entry_id"] = rec.get("Entry ID")
                st.session_state["active_nav"] = "Edit Customer Details"
                st.rerun()


# =============================================================================
# VIEW 4: EDIT CUSTOMER DETAILS (CRITICAL COMPONENT)
# =============================================================================

def view_edit_customer(current_user: Any) -> None:
    """
    Renders record editing interface with:
    - Quick Remark Only edit vs Full Field edit
    - Field validation
    - Concurrency conflict detection (optimistic locking)
    - Pre-save diff preview
    - Row-level update to original Google Sheets row
    - Complete audit trail logging
    """
    st.subheader("Edit Customer Details")

    all_records = record_manager.get_all_records(sort_by_date=True)
    if not all_records:
        st.info("No records available to edit.")
        return

    record_options = {
        f"{r.get('Entry ID')} - {r.get('Company Name')} ({r.get('Customer Name')})": r.get('Entry ID')
        for r in all_records if r.get('Entry ID')
    }

    # Pre-select ID if transferred from another view
    selected_id = st.session_state.get("selected_entry_id")
    default_idx = 0
    if selected_id:
        for idx, (label, eid) in enumerate(record_options.items()):
            if eid == selected_id:
                default_idx = idx
                break

    selected_label = st.selectbox(
        "Select Customer Record to Edit:",
        list(record_options.keys()),
        index=default_idx
    )
    chosen_id = record_options[selected_label]

    # Fetch fresh record from backend
    record = record_manager.get_record_by_id(chosen_id)
    if not record:
        st.error(f"Record with ID '{chosen_id}' not found.")
        return

    # Track expected last updated timestamp for optimistic locking
    expected_last_updated = clean_string(record.get("Last Updated", ""))

    st.markdown(
        f"""
        <div style="background: #EFF6FF; border: 1px solid #BFDBFE; padding: 0.75rem 1rem; border-radius: 8px; margin-bottom: 1rem;">
            <strong>Entry ID:</strong> <code>{record.get('Entry ID')}</code> &nbsp;|&nbsp;
            <strong>Created:</strong> {record.get('Created At')} &nbsp;|&nbsp;
            <strong>Last Updated:</strong> {record.get('Last Updated')} &nbsp;|&nbsp;
            <strong>Last Updated By:</strong> {record.get('Updated By')}
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Edit mode option
    edit_mode = st.radio(
        "Edit Scope:",
        ["Quick Edit Remark Only", "Full Customer Record Edit"],
        horizontal=True
    )

    with st.form("edit_customer_form"):
        updated_payload: Dict[str, Any] = {}

        if edit_mode == "Quick Edit Remark Only":
            st.info(f"Editing Remark for **{record.get('Company Name')}** ({record.get('Customer Name')})")
            new_remark = st.text_area("Remark *", value=record.get("Remark", ""), height=150)
            updated_payload["Remark"] = new_remark
        else:
            c1, c2 = st.columns(2)
            with c1:
                new_date = st.text_input("Date (DD-MM-YYYY) *", value=record.get("Date", ""))
                new_company = st.text_input("Company Name *", value=record.get("Company Name", ""))
                new_customer = st.text_input("Customer Name *", value=record.get("Customer Name", ""))
                new_address = st.text_area("Company Address *", value=record.get("Company Address", ""), height=100)
            with c2:
                new_mobile = st.text_input("Mobile Number (10 digits) *", value=str(record.get("Mobile Number", "")), max_chars=10)
                new_email = st.text_input("Email", value=record.get("Email", ""))
                new_remark = st.text_area("Remark *", value=record.get("Remark", ""), height=100)

            updated_payload = {
                "Date": new_date,
                "Company Name": new_company,
                "Customer Name": new_customer,
                "Company Address": new_address,
                "Mobile Number": new_mobile,
                "Email": new_email,
                "Remark": new_remark,
            }

        btn_c1, btn_c2 = st.columns([1, 1])
        with btn_c1:
            save_clicked = st.form_submit_button("💾 Save Changes to Google Sheets", type="primary", use_container_width=True)
        with btn_c2:
            cancel_clicked = st.form_submit_button("❌ Cancel / Reset", type="secondary", use_container_width=True)

    if cancel_clicked:
        st.session_state["selected_entry_id"] = None
        st.info("Edit cancelled. Form reset.")
        st.rerun()

    if save_clicked:
        # Pre-validate before attempting save
        editor_identity = f"{current_user.display_name} ({current_user.email})"

        try:
            with st.spinner("Saving changes and updating Google Sheets database..."):
                success, msg, changes = record_manager.update_record(
                    entry_id=chosen_id,
                    updated_fields=updated_payload,
                    editor_identity=editor_identity,
                    expected_last_updated=expected_last_updated,
                )

            if success:
                st.success(f"✅ {msg}")
                if changes:
                    st.markdown("#### **Summary of Changes Recorded in Edit History:**")
                    diff_data = [
                        {
                            "Field": item.field_changed,
                            "Previous Value": item.previous_value,
                            "New Value": item.new_value,
                            "Editor": item.updated_by,
                            "Timestamp": item.update_date_time,
                        }
                        for item in changes
                    ]
                    st.table(pd.DataFrame(diff_data))
                # Clear selected entry so user can choose another
                st.session_state["selected_entry_id"] = None
            else:
                st.error(f"❌ {msg}")

        except ConcurrentEditConflictError as ce:
            st.error(f"⚠️ {str(ce)}")
            st.warning("Please reload the record to see the latest modifications before submitting your changes.")
        except Exception as ex:
            st.error(f"An unexpected error occurred while saving: {str(ex)}")

    # Delete Record Section (Danger Zone)
    st.divider()
    with st.expander("🗑️ Delete Customer Record (Danger Zone)"):
        st.warning(f"Deleting record **{chosen_id}** ({record.get('Company Name')}) will permanently remove it from the active Sales Entries. A permanent audit log will be preserved in Edit History.")
        confirm_delete = st.checkbox(f"I confirm I want to permanently delete record {chosen_id}", key=f"confirm_del_{chosen_id}")
        if st.button("🚨 Delete Record Permanently", type="secondary", disabled=not confirm_delete):
            editor_identity = f"{current_user.display_name} ({current_user.email})"
            del_ok, del_msg = record_manager.delete_record(chosen_id, deleted_by=editor_identity)
            if del_ok:
                st.success(del_msg)
                st.session_state["selected_entry_id"] = None
                st.rerun()
            else:
                st.error(del_msg)


# =============================================================================
# VIEW 5: EDIT HISTORY
# =============================================================================

def view_edit_history() -> None:
    """Renders modification history log with filtering options."""
    st.subheader("Central Audit & Edit History")
    st.caption("Complete, tamper-evident log of every modification made to customer records.")

    all_history = record_manager.get_edit_history()

    # Filters
    fc1, fc2, fc3, fc4 = st.columns(4)
    with fc1:
        f_user = st.text_input("Filter by Updated By", placeholder="e.g. Sagar Sir")
    with fc2:
        f_comp = st.text_input("Filter by Company", placeholder="e.g. Precision")
    with fc3:
        f_id = st.text_input("Filter by Entry ID", placeholder="e.g. NEP-")
    with fc4:
        f_date = st.text_input("Filter by Date", placeholder="e.g. 02-11-2026")

    filtered_history = record_manager.get_edit_history(
        updated_by=f_user,
        company_name=f_comp,
        entry_id=f_id,
        update_date=f_date,
    )

    st.markdown(f"**Found {len(filtered_history)} modification events**")

    if not filtered_history:
        st.info("No edit history records match your filters.")
        return

    df_hist = pd.DataFrame(filtered_history)
    cols = config.edit_history_columns
    display_cols = [c for c in cols if c in df_hist.columns]

    st.dataframe(df_hist[display_cols], use_container_width=True, hide_index=True)

    # Download button
    csv_data = df_hist[display_cols].to_csv(index=False).encode("utf-8")
    st.download_button(
        label="📥 Export Edit History to CSV",
        data=csv_data,
        file_name=f"neptune_edit_history_{get_current_date_str()}.csv",
        mime="text/csv",
    )


# =============================================================================
# VIEW 6: GOOGLE SETUP GUIDE
# =============================================================================

def view_google_setup() -> None:
    """Renders instructions and 1-click tools for Google Workspace setup."""
    st.subheader("Google Workspace Setup & Authorization Guide")

    st.markdown(
        f"""
        This system is designed to integrate seamlessly with Google account:
        **`{config.google_workspace.get('account_email', 'mallikarjungokule@gmail.com')}`**

        ### Quick 1-Minute Automated Setup via Google Apps Script (Recommended):
        We have generated a zero-dependency Google Apps Script file:
        `scripts/setup_neptune_workspace.gs`

        #### Steps to run in Google Account `mallikarjungokule@gmail.com`:
        1. Open your browser and go to [https://script.google.com](https://script.google.com)
        2. Click **New Project** and name it `Neptune Systems Sales Automation`.
        3. Copy the script below, paste it into the editor replacing existing text, and click **Save**.
        4. Select function **`setupNeptuneSystemsWorkspace`** from the dropdown and click **Run**.
        5. Grant the standard Google permissions.
        6. That's it! It will automatically create:
           - The Google Form: **`Neptune Systems – Customer & Sales Entry Form`**
           - The Google Spreadsheet: **`Neptune Systems – Sales Customer Database`**
           - Worksheets: **`Sales Entries`**, **`Edit History`**, **`Dashboard Data`**
           - Link them with automatic `onFormSubmit` unique Entry ID generation!
        """
    )

    from app.google_forms import GoogleFormsManager
    gas_code = GoogleFormsManager.generate_apps_script_code()

    with st.expander("📄 Click to View / Copy Google Apps Script Code"):
        st.code(gas_code, language="javascript")

    st.divider()

    st.markdown("### Update Dashboard Configuration")
    with st.form("update_sheet_ids_form"):
        curr_ss_id = st.text_input(
            "Google Spreadsheet ID",
            value=config.google_workspace.get("spreadsheet_id", ""),
            help="Found in your Google Sheet URL between /d/ and /edit",
        )
        curr_form_url = st.text_input(
            "Google Form Published URL",
            value=config.google_workspace.get("form_url", ""),
            help="The link you share with the sales team to submit records",
        )
        save_btn = st.form_submit_button("Save Google Resource Details")
        if save_btn:
            config.update_google_resource_ids(
                spreadsheet_id=curr_ss_id.strip(),
                form_url=curr_form_url.strip(),
            )
            st.success("Configuration updated! Re-connecting to Google Sheets...")
            sheets_connector.connect()
            st.rerun()


# =============================================================================
# MAIN DASHBOARD RENDERER
# =============================================================================

def render_dashboard() -> None:
    """Entry point for authenticated Streamlit dashboard."""
    apply_custom_css()
    current_user = get_current_user()

    if not current_user:
        st.error("Access denied. Please log in.")
        return

    render_header(current_user)
    selected_page = render_sidebar(current_user)

    if "Overview" in selected_page:
        view_overview()
    elif "All Sales Entries" in selected_page:
        view_all_entries()
    elif "Search Customer" in selected_page:
        view_search()
    elif "Edit Customer Details" in selected_page:
        view_edit_customer(current_user)
    elif "Edit History" in selected_page:
        view_edit_history()
    elif "Google Setup Guide" in selected_page:
        view_google_setup()
