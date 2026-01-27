import sqlite3
import pandas as pd
from datetime import datetime

from database import get_connection

def _now():
    return datetime.now().isoformat(timespec="seconds")

# -------------------- Categorias --------------------
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
    cur.execute("INSERT INTO categories (user_id, name, created_at) VALUES (?, ?, ?)", (user_id, name, _now()))
    conn.commit()
    conn.close()

def delete_category(user_id: int, category_id: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE payments SET category_id = NULL WHERE user_id = ? AND category_id = ?", (user_id, category_id))
    cur.execute("DELETE FROM categories WHERE user_id = ? AND id = ?", (user_id, category_id))
    conn.commit()
    conn.close()

def _get_category_id_by_name(conn, user_id: int, name: str):
    cur = conn.cursor()
    cur.execute("SELECT id FROM categories WHERE user_id = ? AND name = ? LIMIT 1", (user_id, name))
    r = cur.fetchone()
    return int(r[0]) if r else None

# -------------------- Pagamentos --------------------
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

def add_installments(user_id: int, description: str, total_amount: float, installments: int, first_due_date: str,
                     start_month: int, start_year: int, category_id=None):
    description = (description or "").strip()
    if not description:
        raise ValueError("Descrição é obrigatória.")
    if total_amount is None or float(total_amount) <= 0:
        raise ValueError("Valor deve ser maior que zero.")
    if int(installments) < 2:
        raise ValueError("Parcelas deve ser >= 2 para parcelamento.")

    total_amount = float(total_amount)
    installments = int(installments)

    # divide e ajusta centavos no final para fechar exatamente
    base = round(total_amount / installments, 2)
    valores = [base] * installments
    diff = round(total_amount - sum(valores), 2)
    valores[-1] = round(valores[-1] + diff, 2)

    due_day = None
    try:
        due_day = datetime.fromisoformat(str(first_due_date)).day
    except:
        try:
            due_day = int(str(first_due_date).split("-")[-1])
        except:
            due_day = 1

    for i in range(installments):
        m = start_month + i
        y = start_year
        while m > 12:
            m -= 12
            y += 1

        desc_i = f"{description} ({i+1}/{installments})"
        due_i = f"{y:04d}-{m:02d}-{min(due_day, 28):02d}"  # evita datas inválidas

        add_payment(user_id, desc_i, float(valores[i]), due_i, m, y, category_id)

def list_payments(user_id: int, month: int, year: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """SELECT p.id, p.description, p.amount, p.due_date, p.paid, p.paid_date,
                  p.category_id, c.name
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

def delete_payment(user_id: int, payment_id: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM payments WHERE user_id = ? AND id = ?", (user_id, payment_id))
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

def set_paid_for_category_month(user_id: int, month: int, year: int, category_name: str, paid: bool):
    conn = get_connection()
    cat_id = _get_category_id_by_name(conn, user_id, category_name)
    if cat_id is None:
        conn.close()
        return

    cur = conn.cursor()
    if paid:
        cur.execute(
            """UPDATE payments
               SET paid = 1, paid_date = ?
               WHERE user_id = ? AND month = ? AND year = ? AND category_id = ?""",
            (_now(), user_id, int(month), int(year), cat_id)
        )
    else:
        cur.execute(
            """UPDATE payments
               SET paid = 0, paid_date = NULL
               WHERE user_id = ? AND month = ? AND year = ? AND category_id = ?""",
            (user_id, int(month), int(year), cat_id)
        )
    conn.commit()
    conn.close()

def payments_dataframe(user_id: int, month: int, year: int) -> pd.DataFrame:
    rows = list_payments(user_id, month, year)
    df = pd.DataFrame(rows, columns=["ID", "Descrição", "Valor", "Vencimento", "Pago", "Data pagamento", "CategoriaID", "Categoria"])
    if not df.empty:
        df["Pago"] = df["Pago"].map({0: "Não", 1: "Sim"})
        df = df.drop(columns=["CategoriaID"])
    return df

# -------------------- Planejamento (budgets) --------------------
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
