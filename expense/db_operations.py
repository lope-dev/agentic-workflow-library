"""
db_operations.py - All CRUD database operations for the expense management system.
"""

from sqlalchemy import create_engine, text
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash

DATABASE_URL = "postgresql://expense_user:rodo4194@localhost:5432/expense_db"
engine = create_engine(DATABASE_URL)


# ============================================================
# USER OPERATIONS
# ============================================================

def register_user(username: str, password: str) -> dict:
    """Register a new user. Returns dict with success status and message."""
    hashed_password = generate_password_hash(password)
    try:
        with engine.connect() as conn:
            conn.execute(
                text("INSERT INTO Users (username, password, balance) VALUES (:username, :password, 0.00)"),
                {"username": username, "password": hashed_password}
            )
            conn.commit()
            return {"success": True, "message": f"User '{username}' registered successfully!"}
    except Exception as e:
        if "unique" in str(e).lower():
            return {"success": False, "message": "Username already exists."}
        return {"success": False, "message": str(e)}


def login_user(username: str, password: str) -> dict:
    """Authenticate a user. Returns dict with user info if successful."""
    with engine.connect() as conn:
        result = conn.execute(
            text("SELECT user_id, username, password, balance FROM Users WHERE username = :username"),
            {"username": username}
        ).fetchone()

        if result is None:
            return {"success": False, "message": "User not found."}

        if not check_password_hash(result[2], password):
            return {"success": False, "message": "Incorrect password."}

        # Update last_login
        conn.execute(
            text("UPDATE Users SET last_login = :now WHERE user_id = :uid"),
            {"now": datetime.now(), "uid": result[0]}
        )
        conn.commit()

        return {
            "success": True,
            "user_id": result[0],
            "username": result[1],
            "balance": float(result[3])
        }


def get_balance(user_id: int) -> float:
    """Get the current balance for a user."""
    with engine.connect() as conn:
        result = conn.execute(
            text("SELECT balance FROM Users WHERE user_id = :uid"),
            {"uid": user_id}
        ).fetchone()
        return float(result[0]) if result else 0.00


# ============================================================
# TRANSACTION OPERATIONS
# ============================================================

def add_transaction(user_id: int, trans_type: str, category: str, amount: float, description: str = "") -> dict:
    """Add a new transaction and update the user's balance."""
    trans_type = trans_type.upper()
    if trans_type not in ("DEBIT", "CREDIT"):
        return {"success": False, "message": "Type must be DEBIT or CREDIT."}

    now = datetime.now()
    try:
        with engine.connect() as conn:
            # Insert transaction
            conn.execute(
                text("""
                    INSERT INTO Transactions (user_id, type, category, amount, description, transaction_date, last_update)
                    VALUES (:uid, :type, :category, :amount, :desc, :now, :now)
                """),
                {"uid": user_id, "type": trans_type, "category": category,
                 "amount": amount, "desc": description, "now": now}
            )

            # Update balance
            if trans_type == "CREDIT":
                conn.execute(
                    text("UPDATE Users SET balance = balance + :amount WHERE user_id = :uid"),
                    {"amount": amount, "uid": user_id}
                )
            else:
                conn.execute(
                    text("UPDATE Users SET balance = balance - :amount WHERE user_id = :uid"),
                    {"amount": amount, "uid": user_id}
                )

            conn.commit()
            new_balance = get_balance(user_id)
            return {
                "success": True,
                "message": f"{'Expense' if trans_type == 'DEBIT' else 'Income'} of ${amount:.2f} ({category}) added. New balance: ${new_balance:.2f}"
            }
    except Exception as e:
        return {"success": False, "message": str(e)}


def get_all_transactions(user_id: int) -> list:
    """Get all transactions for a user."""
    with engine.connect() as conn:
        results = conn.execute(
            text("""
                SELECT transaction_id, type, category, amount, description, transaction_date
                FROM Transactions
                WHERE user_id = :uid
                ORDER BY transaction_date DESC
            """),
            {"uid": user_id}
        ).fetchall()

        return [
            {
                "transaction_id": r[0], "type": r[1], "category": r[2],
                "amount": float(r[3]), "description": r[4],
                "transaction_date": r[5].strftime("%Y-%m-%d %H:%M") if r[5] else ""
            }
            for r in results
        ]


def get_transactions_by_date_range(user_id: int, start_date: str, end_date: str) -> list:
    """Get transactions within a date range."""
    with engine.connect() as conn:
        results = conn.execute(
            text("""
                SELECT transaction_id, type, category, amount, description, transaction_date
                FROM Transactions
                WHERE user_id = :uid AND transaction_date BETWEEN :start AND :end
                ORDER BY transaction_date DESC
            """),
            {"uid": user_id, "start": start_date, "end": end_date}
        ).fetchall()

        return [
            {
                "transaction_id": r[0], "type": r[1], "category": r[2],
                "amount": float(r[3]), "description": r[4],
                "transaction_date": r[5].strftime("%Y-%m-%d %H:%M") if r[5] else ""
            }
            for r in results
        ]


def get_transactions_by_category(user_id: int, category: str) -> list:
    """Get transactions filtered by category."""
    with engine.connect() as conn:
        results = conn.execute(
            text("""
                SELECT transaction_id, type, category, amount, description, transaction_date
                FROM Transactions
                WHERE user_id = :uid AND LOWER(category) = LOWER(:cat)
                ORDER BY transaction_date DESC
            """),
            {"uid": user_id, "cat": category}
        ).fetchall()

        return [
            {
                "transaction_id": r[0], "type": r[1], "category": r[2],
                "amount": float(r[3]), "description": r[4],
                "transaction_date": r[5].strftime("%Y-%m-%d %H:%M") if r[5] else ""
            }
            for r in results
        ]


def get_monthly_summary(user_id: int, year: int = None, month: int = None) -> dict:
    """Get monthly summary: total income, total expenses, net balance."""
    if year is None:
        year = datetime.now().year
    if month is None:
        month = datetime.now().month

    with engine.connect() as conn:
        result = conn.execute(
            text("""
                SELECT
                    COALESCE(SUM(CASE WHEN type = 'CREDIT' THEN amount ELSE 0 END), 0) as total_income,
                    COALESCE(SUM(CASE WHEN type = 'DEBIT' THEN amount ELSE 0 END), 0) as total_expense
                FROM Transactions
                WHERE user_id = :uid
                  AND EXTRACT(YEAR FROM transaction_date) = :year
                  AND EXTRACT(MONTH FROM transaction_date) = :month
            """),
            {"uid": user_id, "year": year, "month": month}
        ).fetchone()

        total_income = float(result[0])
        total_expense = float(result[1])

        return {
            "year": year,
            "month": month,
            "total_income": total_income,
            "total_expense": total_expense,
            "net": total_income - total_expense
        }


def update_transaction(transaction_id: int, user_id: int, new_type: str = None,
                       new_category: str = None, new_amount: float = None,
                       new_description: str = None) -> dict:
    """Update a transaction and adjust balance accordingly."""
    try:
        with engine.connect() as conn:
            # Get original transaction
            original = conn.execute(
                text("""
                    SELECT type, amount FROM Transactions
                    WHERE transaction_id = :tid AND user_id = :uid
                """),
                {"tid": transaction_id, "uid": user_id}
            ).fetchone()

            if original is None:
                return {"success": False, "message": "Transaction not found."}

            old_type = original[0]
            old_amount = float(original[1])

            # Reverse the old transaction's effect on balance
            if old_type == "CREDIT":
                conn.execute(
                    text("UPDATE Users SET balance = balance - :amount WHERE user_id = :uid"),
                    {"amount": old_amount, "uid": user_id}
                )
            else:
                conn.execute(
                    text("UPDATE Users SET balance = balance + :amount WHERE user_id = :uid"),
                    {"amount": old_amount, "uid": user_id}
                )

            # Apply updates
            updated_type = new_type.upper() if new_type else old_type
            updated_amount = new_amount if new_amount is not None else old_amount
            updated_category = new_category
            updated_description = new_description

            # Build update query dynamically
            updates = ["last_update = :now"]
            params = {"tid": transaction_id, "uid": user_id, "now": datetime.now()}

            if new_type:
                updates.append("type = :new_type")
                params["new_type"] = updated_type
            if new_category:
                updates.append("category = :new_cat")
                params["new_cat"] = updated_category
            if new_amount is not None:
                updates.append("amount = :new_amount")
                params["new_amount"] = updated_amount
            if new_description is not None:
                updates.append("description = :new_desc")
                params["new_desc"] = updated_description

            conn.execute(
                text(f"UPDATE Transactions SET {', '.join(updates)} WHERE transaction_id = :tid AND user_id = :uid"),
                params
            )

            # Apply the new transaction's effect on balance
            if updated_type == "CREDIT":
                conn.execute(
                    text("UPDATE Users SET balance = balance + :amount WHERE user_id = :uid"),
                    {"amount": updated_amount, "uid": user_id}
                )
            else:
                conn.execute(
                    text("UPDATE Users SET balance = balance - :amount WHERE user_id = :uid"),
                    {"amount": updated_amount, "uid": user_id}
                )

            conn.commit()
            new_balance = get_balance(user_id)
            return {"success": True, "message": f"Transaction #{transaction_id} updated. New balance: ${new_balance:.2f}"}
    except Exception as e:
        return {"success": False, "message": str(e)}


def delete_transaction(transaction_id: int, user_id: int) -> dict:
    """Delete a transaction and adjust balance."""
    try:
        with engine.connect() as conn:
            # Get transaction details first
            original = conn.execute(
                text("SELECT type, amount FROM Transactions WHERE transaction_id = :tid AND user_id = :uid"),
                {"tid": transaction_id, "uid": user_id}
            ).fetchone()

            if original is None:
                return {"success": False, "message": "Transaction not found."}

            old_type = original[0]
            old_amount = float(original[1])

            # Delete transaction
            conn.execute(
                text("DELETE FROM Transactions WHERE transaction_id = :tid AND user_id = :uid"),
                {"tid": transaction_id, "uid": user_id}
            )

            # Reverse balance effect
            if old_type == "CREDIT":
                conn.execute(
                    text("UPDATE Users SET balance = balance - :amount WHERE user_id = :uid"),
                    {"amount": old_amount, "uid": user_id}
                )
            else:
                conn.execute(
                    text("UPDATE Users SET balance = balance + :amount WHERE user_id = :uid"),
                    {"amount": old_amount, "uid": user_id}
                )

            conn.commit()
            new_balance = get_balance(user_id)
            return {"success": True, "message": f"Transaction #{transaction_id} deleted. New balance: ${new_balance:.2f}"}
    except Exception as e:
        return {"success": False, "message": str(e)}
