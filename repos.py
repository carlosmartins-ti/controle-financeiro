import datetime
import pandas as pd
from database import get_connection

def _now():
    return datetime.datetime.now().isoformat(timespec="seconds")

# -------------------- Categories --------------------
def list_categories(user_id: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, name FROM categories WHERE user_id = ? ORDER BY name", (user_id,))
    rows = cur.fetchall()
    conn.close()
    return rows

def create_category(user_id: int, name: str):
    name = (name or "").strip()
    if not name:
        raise ValueError("Nome da categoria é obrigatório.")
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO categories (user_id, name, created_at) VALUES (?, ?, ?)",
        (user_id, name, _now())
    )
    conn.commit()
    conn.close()

def delete_category(user_id: int, category_id: int):
    conn = get_connection()
    cur = conn.cursor()
    # desvincula pagamentos antes de deletar
    cur.execute("UPDATE payments SET category_id = NULL WHERE user_id = ? AND category_id = ?", (user_id, category_id))
    cur.execute("DELETE FROM categories WHERE user_id = ? AND id = ?", (user_id, category_id))
    conn.commit()
    conn.close()

# -------------------- Payments --------------------
def add_payment(user_id: int, description: str, amount: float, due_date: str, month: int, year: int, category_id=None):
    description = (description or "").strip()
    if not description:
        raise ValueError("Descrição é obrigatória.")
    if amount is None or float(amount) <= 0:
        raise ValueError("Valor deve ser maior que zero.")
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """INSERT INTO payments
            (user_id, description, category_id, amount, due_date, month, year, paid, paid_date, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, 0, NULL, ?)""",
        (user_id, description, category_id, float(amount), due_date, int(month), int(year), _now())
    )
    conn.commit()
    conn.close()

def list_payments(user_id: int, month: int, year: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """SELECT p.id, p.description, p.amount, p.due_date, p.paid, p.paid_date,
                  p.category_id, c.name as category
           FROM payments p
           LEFT JOIN categories c ON c.id = p.category_id
           WHERE p.user_id = ? AND p.month = ? AND p.year = ?
           ORDER BY p.paid ASC, p.due_date ASC, p.id DESC""",
        (user_id, int(month), int(year))
    )
    rows = cur.fetchall()
    conn.close()
    return rows

def update_payment(user_id: int, payment_id: int, description: str, amount: float, due_date: str, category_id=None):
    description = (description or "").strip()
    if not description:
        raise ValueError("Descrição é obrigatória.")
    if amount is None or float(amount) <= 0:
        raise ValueError("Valor deve ser maior que zero.")
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """UPDATE payments
           SET description = ?, amount = ?, due_date = ?, category_id = ?
           WHERE user_id = ? AND id = ?""",
        (description, float(amount), due_date, category_id, user_id, payment_id)
    )
    conn.commit()
    conn.close()

def mark_paid(user_id: int, payment_id: int, paid: bool):
    conn = get_connection()
    cur = conn.cursor()
    if paid:
        cur.execute(
            "UPDATE payments SET paid = 1, paid_date = ? WHERE user_id = ? AND id = ?",
            (_now(), user_id, payment_id)
        )
    else:
        cur.execute(
            "UPDATE payments SET paid = 0, paid_date = NULL WHERE user_id = ? AND id = ?",
            (user_id, payment_id)
        )
    conn.commit()
    conn.close()

def delete_payment(user_id: int, payment_id: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM payments WHERE user_id = ? AND id = ?", (user_id, payment_id))
    conn.commit()
    conn.close()

def payments_dataframe(user_id: int, month: int, year: int) -> pd.DataFrame:
    rows = list_payments(user_id, month, year)
    df = pd.DataFrame(rows, columns=["ID", "Descrição", "Valor", "Vencimento", "Pago", "Data pagamento", "CategoriaID", "Categoria"])
    if not df.empty:
        df["Pago"] = df["Pago"].map({0: "Não", 1: "Sim"})
        df = df.drop(columns=["CategoriaID"])
    return df

# -------------------- Budgets / Planning --------------------
def get_budget(user_id: int, month: int, year: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT income, expense_goal FROM budgets WHERE user_id = ? AND month = ? AND year = ?",
        (user_id, int(month), int(year))
    )
    row = cur.fetchone()
    conn.close()
    if row:
        return {"income": float(row[0]), "expense_goal": float(row[1])}
    return {"income": 0.0, "expense_goal": 0.0}

def upsert_budget(user_id: int, month: int, year: int, income: float, expense_goal: float):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """INSERT INTO budgets (user_id, month, year, income, expense_goal, created_at)
           VALUES (?, ?, ?, ?, ?, ?)
           ON CONFLICT(user_id, month, year)
           DO UPDATE SET income = excluded.income, expense_goal = excluded.expense_goal""",
        (user_id, int(month), int(year), float(income or 0), float(expense_goal or 0), _now())
    )
    conn.commit()
    conn.close()
