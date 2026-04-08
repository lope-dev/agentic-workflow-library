"""
app.py - Streamlit frontend for the Personal Expense Management System.
Run with: streamlit run app.py
"""

import streamlit as st
import db_operations as db
import llm_handler as llm
from datetime import datetime

# ============================================================
# PAGE CONFIG
# ============================================================
st.set_page_config(page_title="Expense Manager", page_icon="💰", layout="wide")

# ============================================================
# SESSION STATE INITIALIZATION
# ============================================================
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "user_id" not in st.session_state:
    st.session_state.user_id = None
if "username" not in st.session_state:
    st.session_state.username = ""
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []


# ============================================================
# LOGIN / REGISTER PAGE
# ============================================================
def show_auth_page():
    st.title("💰 Personal Expense Manager")
    st.subheader("Login or Register to get started")

    tab_login, tab_register = st.tabs(["Login", "Register"])

    with tab_login:
        with st.form("login_form"):
            username = st.text_input("Username", key="login_user")
            password = st.text_input("Password", type="password", key="login_pass")
            submitted = st.form_submit_button("Login")

            if submitted:
                if not username or not password:
                    st.error("Please enter both username and password.")
                else:
                    result = db.login_user(username, password)
                    if result["success"]:
                        st.session_state.logged_in = True
                        st.session_state.user_id = result["user_id"]
                        st.session_state.username = result["username"]
                        st.session_state.chat_history = []
                        st.rerun()
                    else:
                        st.error(result["message"])

    with tab_register:
        with st.form("register_form"):
            new_username = st.text_input("Choose a Username", key="reg_user")
            new_password = st.text_input("Choose a Password", type="password", key="reg_pass")
            confirm_password = st.text_input("Confirm Password", type="password", key="reg_confirm")
            submitted = st.form_submit_button("Register")

            if submitted:
                if not new_username or not new_password:
                    st.error("Please fill in all fields.")
                elif new_password != confirm_password:
                    st.error("Passwords do not match.")
                elif len(new_password) < 4:
                    st.error("Password must be at least 4 characters.")
                else:
                    result = db.register_user(new_username, new_password)
                    if result["success"]:
                        st.success(result["message"] + " You can now log in.")
                    else:
                        st.error(result["message"])


# ============================================================
# MAIN DASHBOARD
# ============================================================
def show_dashboard():
    # -- Sidebar --
    with st.sidebar:
        st.title(f"Welcome, {st.session_state.username}!")
        balance = db.get_balance(st.session_state.user_id)
        st.metric("Current Balance", f"${balance:.2f}")

        st.divider()
        if st.button("Logout", use_container_width=True):
            st.session_state.logged_in = False
            st.session_state.user_id = None
            st.session_state.username = ""
            st.session_state.chat_history = []
            st.rerun()

    # -- Main content tabs --
    tab_chat, tab_manual, tab_history = st.tabs([
        "💬 Chat with AI", "📝 Manual Entry", "📊 Transaction History"
    ])

    # ---- TAB 1: CHAT WITH AI ----
    with tab_chat:
        st.subheader("Chat with your AI Financial Assistant")
        st.caption("Try: 'Add a $50 grocery expense', 'Show my balance', 'Delete transaction #3'")

        # Display chat history
        for msg in st.session_state.chat_history:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

        # Chat input
        user_input = st.chat_input("Type your request...")
        if user_input:
            # Add user message to history
            st.session_state.chat_history.append({"role": "user", "content": user_input})
            with st.chat_message("user"):
                st.markdown(user_input)

            # Process with LLM
            with st.chat_message("assistant"):
                with st.spinner("Thinking..."):
                    response = llm.handle_user_message(st.session_state.user_id, user_input)
                st.markdown(response)

            st.session_state.chat_history.append({"role": "assistant", "content": response})
            st.rerun()

    # ---- TAB 2: MANUAL ENTRY ----
    with tab_manual:
        st.subheader("Add Transaction Manually")

        col1, col2 = st.columns(2)

        with col1:
            with st.form("add_transaction_form"):
                trans_type = st.selectbox("Type", ["DEBIT (Expense)", "CREDIT (Income)"])
                category = st.selectbox("Category", [
                    "Groceries", "Food", "Transport", "Salary", "Rent",
                    "Utilities", "Entertainment", "Shopping", "Healthcare",
                    "Education", "Freelance", "Other"
                ])
                amount = st.number_input("Amount ($)", min_value=0.01, step=0.01, format="%.2f")
                description = st.text_input("Description (optional)")
                submitted = st.form_submit_button("Add Transaction", use_container_width=True)

                if submitted:
                    t_type = "DEBIT" if "DEBIT" in trans_type else "CREDIT"
                    result = db.add_transaction(
                        st.session_state.user_id, t_type, category, amount, description
                    )
                    if result["success"]:
                        st.success(result["message"])
                        st.rerun()
                    else:
                        st.error(result["message"])

        with col2:
            st.subheader("Monthly Summary")
            now = datetime.now()
            summary = db.get_monthly_summary(st.session_state.user_id, now.year, now.month)
            st.metric("Total Income", f"${summary['total_income']:.2f}")
            st.metric("Total Expenses", f"${summary['total_expense']:.2f}")
            st.metric("Net This Month", f"${summary['net']:.2f}",
                      delta=f"${summary['net']:.2f}")

    # ---- TAB 3: TRANSACTION HISTORY ----
    with tab_history:
        st.subheader("All Transactions")

        # Filters
        col1, col2, col3 = st.columns(3)
        with col1:
            filter_type = st.selectbox("Filter by", ["All", "By Category", "By Date Range"])
        with col2:
            if filter_type == "By Category":
                filter_category = st.text_input("Category")
        with col3:
            if filter_type == "By Date Range":
                date_range = st.date_input("Date range", value=[], max_value=datetime.now())

        # Fetch transactions
        if filter_type == "All":
            transactions = db.get_all_transactions(st.session_state.user_id)
        elif filter_type == "By Category":
            transactions = db.get_transactions_by_category(
                st.session_state.user_id, filter_category if 'filter_category' in dir() else ""
            )
        elif filter_type == "By Date Range":
            if 'date_range' in dir() and len(date_range) == 2:
                transactions = db.get_transactions_by_date_range(
                    st.session_state.user_id,
                    date_range[0].strftime("%Y-%m-%d"),
                    date_range[1].strftime("%Y-%m-%d 23:59:59")
                )
            else:
                transactions = db.get_all_transactions(st.session_state.user_id)
        else:
            transactions = []

        # Display as table
        if transactions:
            st.dataframe(
                transactions,
                column_config={
                    "transaction_id": "ID",
                    "type": "Type",
                    "category": "Category",
                    "amount": st.column_config.NumberColumn("Amount", format="$%.2f"),
                    "description": "Description",
                    "transaction_date": "Date"
                },
                use_container_width=True,
                hide_index=True
            )

            # Delete / Update section
            st.divider()
            st.subheader("Manage Transactions")

            col_del, col_upd = st.columns(2)

            with col_del:
                with st.form("delete_form"):
                    del_id = st.number_input("Transaction ID to delete", min_value=1, step=1)
                    if st.form_submit_button("Delete Transaction", use_container_width=True):
                        result = db.delete_transaction(int(del_id), st.session_state.user_id)
                        if result["success"]:
                            st.success(result["message"])
                            st.rerun()
                        else:
                            st.error(result["message"])

            with col_upd:
                with st.form("update_form"):
                    upd_id = st.number_input("Transaction ID to update", min_value=1, step=1)
                    upd_type = st.selectbox("New Type (leave as-is if unchanged)",
                                           ["No change", "DEBIT", "CREDIT"])
                    upd_category = st.text_input("New Category (leave empty if unchanged)")
                    upd_amount = st.number_input("New Amount (0 = no change)", min_value=0.0, step=0.01)
                    upd_desc = st.text_input("New Description (leave empty if unchanged)")

                    if st.form_submit_button("Update Transaction", use_container_width=True):
                        result = db.update_transaction(
                            transaction_id=int(upd_id),
                            user_id=st.session_state.user_id,
                            new_type=upd_type if upd_type != "No change" else None,
                            new_category=upd_category if upd_category else None,
                            new_amount=upd_amount if upd_amount > 0 else None,
                            new_description=upd_desc if upd_desc else None
                        )
                        if result["success"]:
                            st.success(result["message"])
                            st.rerun()
                        else:
                            st.error(result["message"])
        else:
            st.info("No transactions found. Add your first transaction!")


# ============================================================
# MAIN APP ROUTER
# ============================================================
if st.session_state.logged_in:
    show_dashboard()
else:
    show_auth_page()
