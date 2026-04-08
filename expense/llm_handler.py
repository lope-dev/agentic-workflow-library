"""
llm_handler.py - LangChain + Ollama integration for natural language CRUD operations.
Parses user messages into structured operations and executes them.
"""

import json
import re
from datetime import datetime, timedelta
from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage, SystemMessage
import db_operations as db

# Change this to whatever model you have pulled in Ollama
OLLAMA_MODEL = "llama3"

llm = ChatOllama(model=OLLAMA_MODEL, temperature=0)

SYSTEM_PROMPT = """You are a helpful financial assistant that parses user requests into structured JSON commands.
You must respond ONLY with a valid JSON object, no extra text, no markdown, no explanation.

The user has a personal expense management system. Based on their message, determine the operation and return JSON.

Available operations:

1. ADD a transaction:
{"operation": "ADD", "type": "DEBIT" or "CREDIT", "category": "<category>", "amount": <number>, "description": "<description>"}
- DEBIT = expense (money going out)
- CREDIT = income (money coming in)
- Common categories: Groceries, Food, Transport, Salary, Rent, Utilities, Entertainment, Shopping, Healthcare, Education, Other

2. VIEW transactions:
{"operation": "VIEW", "filter": "all"}
{"operation": "VIEW", "filter": "category", "category": "<category>"}
{"operation": "VIEW", "filter": "date_range", "start_date": "YYYY-MM-DD", "end_date": "YYYY-MM-DD"}
{"operation": "VIEW", "filter": "this_month"}

3. GET balance:
{"operation": "BALANCE"}

4. GET monthly summary:
{"operation": "SUMMARY", "year": <year>, "month": <month>}
- If no year/month specified, use current month.

5. UPDATE a transaction:
{"operation": "UPDATE", "transaction_id": <id>, "updates": {"type": "...", "category": "...", "amount": ..., "description": "..."}}
- Only include fields that need to change.

6. DELETE a transaction:
{"operation": "DELETE", "transaction_id": <id>}

Today's date is: """ + datetime.now().strftime("%Y-%m-%d") + """

Important rules:
- "yesterday" means """ + (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d") + """
- Expenses like groceries, coffee, food, rent, bills = DEBIT
- Income like salary, payment received, freelance = CREDIT
- Always respond with ONLY valid JSON, nothing else.
"""


def parse_user_message(message: str) -> dict:
    """Send user message to Ollama via LangChain and parse the JSON response."""
    try:
        messages = [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=message)
        ]

        response = llm.invoke(messages)
        response_text = response.content.strip()

        # Try to extract JSON from the response
        # Sometimes the LLM wraps it in markdown code blocks
        json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
        if json_match:
            parsed = json.loads(json_match.group())
            return {"success": True, "data": parsed}
        else:
            return {"success": False, "message": "Could not parse LLM response."}

    except json.JSONDecodeError:
        return {"success": False, "message": "LLM returned invalid JSON."}
    except Exception as e:
        return {"success": False, "message": f"LLM error: {str(e)}"}


def execute_operation(user_id: int, parsed: dict) -> str:
    """Execute a parsed operation and return a human-readable result."""
    operation = parsed.get("operation", "").upper()

    try:
        # ---- ADD ----
        if operation == "ADD":
            result = db.add_transaction(
                user_id=user_id,
                trans_type=parsed.get("type", "DEBIT"),
                category=parsed.get("category", "Other"),
                amount=float(parsed.get("amount", 0)),
                description=parsed.get("description", "")
            )
            return result["message"]

        # ---- VIEW ----
        elif operation == "VIEW":
            filter_type = parsed.get("filter", "all")

            if filter_type == "all":
                transactions = db.get_all_transactions(user_id)
            elif filter_type == "category":
                transactions = db.get_transactions_by_category(user_id, parsed.get("category", ""))
            elif filter_type == "date_range":
                transactions = db.get_transactions_by_date_range(
                    user_id, parsed.get("start_date", ""), parsed.get("end_date", "")
                )
            elif filter_type == "this_month":
                now = datetime.now()
                start = now.replace(day=1).strftime("%Y-%m-%d")
                end = now.strftime("%Y-%m-%d")
                transactions = db.get_transactions_by_date_range(user_id, start, end)
            else:
                transactions = db.get_all_transactions(user_id)

            if not transactions:
                return "No transactions found."

            lines = ["Here are your transactions:\n"]
            for t in transactions:
                sign = "+" if t["type"] == "CREDIT" else "-"
                lines.append(
                    f"  #{t['transaction_id']} | {t['transaction_date']} | {t['type']} | "
                    f"{t['category']} | {sign}${t['amount']:.2f} | {t['description']}"
                )
            return "\n".join(lines)

        # ---- BALANCE ----
        elif operation == "BALANCE":
            balance = db.get_balance(user_id)
            return f"Your current balance is: ${balance:.2f}"

        # ---- SUMMARY ----
        elif operation == "SUMMARY":
            year = parsed.get("year")
            month = parsed.get("month")
            summary = db.get_monthly_summary(user_id, year, month)
            return (
                f"Monthly Summary ({summary['month']}/{summary['year']}):\n"
                f"  Total Income:  ${summary['total_income']:.2f}\n"
                f"  Total Expense: ${summary['total_expense']:.2f}\n"
                f"  Net:           ${summary['net']:.2f}"
            )

        # ---- UPDATE ----
        elif operation == "UPDATE":
            tid = parsed.get("transaction_id")
            if not tid:
                return "Please specify which transaction to update (by ID)."
            updates = parsed.get("updates", {})
            result = db.update_transaction(
                transaction_id=int(tid),
                user_id=user_id,
                new_type=updates.get("type"),
                new_category=updates.get("category"),
                new_amount=float(updates["amount"]) if "amount" in updates else None,
                new_description=updates.get("description")
            )
            return result["message"]

        # ---- DELETE ----
        elif operation == "DELETE":
            tid = parsed.get("transaction_id")
            if not tid:
                return "Please specify which transaction to delete (by ID)."
            result = db.delete_transaction(int(tid), user_id)
            return result["message"]

        else:
            return "I'm not sure what you'd like to do. Try something like 'Add a $50 grocery expense' or 'Show my balance'."

    except Exception as e:
        return f"Error executing operation: {str(e)}"


def handle_user_message(user_id: int, message: str) -> str:
    """Main entry point: takes a natural language message, parses it, executes it, returns result."""
    parsed_result = parse_user_message(message)

    if not parsed_result["success"]:
        return f"Sorry, I couldn't understand that. {parsed_result['message']}\nTry something like:\n  - 'Add a $50 grocery expense'\n  - 'Show all transactions'\n  - 'What is my balance?'"

    return execute_operation(user_id, parsed_result["data"])
