# Personal Expense Management System with LLM Integration

## Overview
A multi-user personal expense management system that supports CRUD operations through both a traditional web interface and natural language commands powered by a local LLM (Ollama) via LangChain.

## Tech Stack
- **Database:** PostgreSQL (via Docker)
- **Backend:** Python, SQLAlchemy, psycopg2
- **Frontend:** Streamlit
- **LLM:** Ollama (open-source, runs locally)
- **AI Orchestration:** LangChain

## Prerequisites
- Python 3.10+
- Docker Desktop (for PostgreSQL)
- Ollama installed and running (https://ollama.com)

## Setup Instructions

### Step 1: Start PostgreSQL in Docker
```bash
docker run -d --name expense_postgres -e POSTGRES_USER=expense_user -e POSTGRES_PASSWORD=yourpassword -e POSTGRES_DB=expense_db -p 5432:5432 -v expense_data:/var/lib/postgresql/data postgres:16
```

Verify it's running:
```bash
docker ps
```

### Step 2: Pull an Ollama Model
Make sure Ollama is running, then pull a model:
```bash
ollama pull llama3
```
If you use a different model, update the `OLLAMA_MODEL` variable in `llm_handler.py`.

### Step 3: Install Python Dependencies
```bash
pip install -r requirements.txt
```

### Step 4: Initialize the Database
```bash
python init_db.py
```

### Step 5: Run the Application
```bash
streamlit run app.py
```
The app will open in your browser at http://localhost:8501

## How to Use

1. **Register** a new account on the registration tab.
2. **Login** with your credentials.
3. Use the **Chat with AI** tab to manage expenses with natural language:
   - "Add a $50 grocery expense"
   - "Record salary income of $2000"
   - "Show all transactions this month"
   - "Delete transaction #3"
   - "What is my current balance?"
4. Use the **Manual Entry** tab to add transactions with a form.
5. Use the **Transaction History** tab to view, filter, update, and delete transactions.

## Configuration
- **Database connection:** Update `DATABASE_URL` in `db_operations.py` and `init_db.py`
- **LLM model:** Update `OLLAMA_MODEL` in `llm_handler.py`

## Project Structure
```
expense_app/
├── app.py              # Streamlit frontend (main entry point)
├── db_operations.py    # Database CRUD operations
├── llm_handler.py      # LangChain + Ollama integration
├── init_db.py          # Database table initialization
├── requirements.txt    # Python dependencies
└── README.md           # This file
```
