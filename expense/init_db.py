"""
init_db.py - Initialize the PostgreSQL database tables.
Run this once before starting the app.
"""

from sqlalchemy import create_engine, text

DATABASE_URL = "postgresql://expense_user:rodo4194@localhost:5432/expense_db"


def init_database():
    engine = create_engine(DATABASE_URL)

    with engine.connect() as conn:
        # Create Users table
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS Users (
                user_id SERIAL PRIMARY KEY,
                username VARCHAR(50) UNIQUE NOT NULL,
                password VARCHAR(255) NOT NULL,
                balance DECIMAL(12,2) DEFAULT 0.00,
                last_login TIMESTAMP
            );
        """))

        # Create Transactions table
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS Transactions (
                transaction_id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                type VARCHAR(10) CHECK(type IN ('DEBIT','CREDIT')),
                category VARCHAR(50),
                amount DECIMAL(12,2) NOT NULL,
                description TEXT,
                transaction_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_update TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES Users(user_id)
            );
        """))

        conn.commit()
        print("Database tables created successfully!")


if __name__ == "__main__":
    init_database()
