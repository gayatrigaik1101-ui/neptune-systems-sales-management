"""
Neptune Systems - Sales Management System
Main Streamlit Application Entrypoint
"""

import sys
from pathlib import Path

# Enable Windows native certificate store for SSL connections
try:
    import truststore
    truststore.inject_into_ssl()
except Exception:
    pass

# Add project root to sys.path to ensure module imports resolve cleanly
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st
from app.config import config
from app.authentication import (
    init_session_state,
    is_authenticated,
    login_user,
    auth_manager,
    get_current_user,
)
from app.dashboard import render_dashboard, apply_custom_css


def render_login_screen() -> None:
    """Renders the secure authentication portal for Neptune Systems."""
    apply_custom_css()

    st.markdown("<br><br>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 1.8, 1])

    with c2:
        st.markdown(
            """
            <div style="background: white; padding: 2.5rem; border-radius: 12px; box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05); border: 1px solid #E2E8F0; text-align: center;">
                <div style="margin-bottom: 1rem;">
                    <span style="font-size: 2.5rem;">💼</span>
                </div>
                <h2 style="color: #0F172A; margin: 0; font-weight: 700;">NEPTUNE SYSTEMS</h2>
                <p style="color: #64748B; font-size: 0.95rem; margin-top: 0.25rem;">
                    Sales Entry & Customer Management Portal
                </p>
                <div style="background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 8px; padding: 0.75rem; margin: 1.5rem 0; font-size: 0.85rem; color: #475569; text-align: left;">
                    🔒 <strong>Authorised Access Only</strong><br>
                    Editing access is strictly restricted to <strong>Sagar Sir</strong> and <strong>Tushar Sir</strong>. General sales team members record enquiries via the Google Form.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        with st.form("login_form"):
            st.markdown("##### **User Sign In**")
            username_or_email = st.text_input(
                "Username or Verified Email",
                placeholder="sagar / tushar / your-email@neptunesystems.com",
            )
            password = st.text_input(
                "Password",
                type="password",
                placeholder="Enter your secure password",
            )
            submit_btn = st.form_submit_button("Sign In to Sales Portal", type="primary", use_container_width=True)

            if submit_btn:
                if not username_or_email or not password:
                    st.error("Please enter both username/email and password.")
                else:
                    user = auth_manager.authenticate(username_or_email, password)
                    if user:
                        login_user(user)
                        st.success(f"Welcome back, {user.display_name}!")
                        st.rerun()
                    else:
                        st.error(
                            "Authentication failed: Invalid credentials or user email is not in the authorised allowlist."
                        )

        # Informational setup note
        with st.expander("ℹ️ Credentials & Account Notice"):
            st.caption(
                "Authorized accounts: **Sagar Sir** (`sagar@neptunesystems.com`) & **Tushar Sir** (`tushar@neptunesystems.com`). "
                "Default initial credentials can be reviewed in `config/settings.json` and credentials README."
            )


def main() -> None:
    """Application runner."""
    st.set_page_config(
        page_title="Neptune Systems – Sales Management",
        page_icon="💼",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    init_session_state()

    if is_authenticated():
        render_dashboard()
    else:
        render_login_screen()


if __name__ == "__main__":
    main()
