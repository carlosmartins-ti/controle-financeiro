import sqlite3

DB_PATH = "database.db"

def get_connection():
    return sqlite3.connect(DB_PATH, check_same_thread=False)

# -------------------- MIGRAÇÃO --------------------
def migrate_payments_credit_fields():
    conn = get_connection()
    cur = conn.cursor()

    # colunas novas necessárias para cartão de crédito
    cols = {
        "is_credit": "INTEGER NOT NULL DEFAULT 0",
        "installments": "INTEGER NOT NULL DEFAULT 1",
        "installment_index": "INTEGER NOT NULL DEFAULT 1",
        "credit_group": "INTEGER"
    }

    # verifica colunas existentes
    cur.execute("PRAGMA table_info(payments)")
    existing_cols = [c[1] for c in cur.fetchall()]

    # adiciona somente se não existir
    for col, ddl in cols.items():
        if col not in existing_cols:
            cur.execute(f"ALTER TABLE payments ADD COLUMN {col} {ddl}")

    conn.commit()
    conn.close()

# -------------------- INIT DB --------------------
def init_db():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        security_question TEXT NOT NULL,
        security_answer_hash TEXT NOT NULL,
        created_at TEXT NOT NULL
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS categories (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        created_at TEXT NOT NULL,
        UNIQUE(user_id, name),
        FOREIGN KEY(user_id) REFERENCES users(id)
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS payments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        description TEXT NOT NULL,
        category_id INTEGER,
        amount REAL NOT NULL,
        due_date TEXT NOT NULL,
        month INTEGER NOT NULL,
        year INTEGER NOT NULL,
        paid INTEGER NOT NULL DEFAULT 0,
        paid_date TEXT,
        created_at TEXT NOT NULL,
        FOREIGN KEY(user_id) REFERENCES users(id),
        FOREIGN KEY(category_id) REFERENCES categories(id)
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS budgets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        month INTEGER NOT NULL,
        year INTEGER NOT NULL,
        income REAL NOT NULL DEFAULT 0,
        expense_goal REAL NOT NULL DEFAULT 0,
        created_at TEXT NOT NULL,
        UNIQUE(user_id, month, year),
        FOREIGN KEY(user_id) REFERENCES users(id)
    )
    """)

    conn.commit()
    conn.close()

    # 🔥 MIGRAÇÃO AQUI (não apaga dados)
    migrate_payments_credit_fields()
