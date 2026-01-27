import datetime
import pandas as pd
from database import get_connection

def _now():
    return datetime.datetime.now().isoformat(timespec="seconds")

# ===================== CATEGORIAS =====================
def list_categories(user_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, name FROM categories WHERE user_id = ?", (user_id,))
    rows = cur.fetchall()
    conn.close()
    return rows

# ===================== PAGAMENTOS =====================
def add_payment(user_id, description, amount, due_date, month, year, category_id=None):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """INSERT INTO payments
           (user_id, description, category_id, amount, due_date, month, year, paid, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, 0, ?)""",
        (user_id, description, category_id, amount, due_date, month, year, _now())
    )
    conn.commit()
    conn.close()

def add_installments(user_id, description, total_amount, installments, start_month, start_year, category_id):
    parcela = round(total_amount / installments, 2)

    conn = get_connection()
    cur = conn.cursor()

    for i in range(installments):
        mes = start_month + i
        ano = start_year
        while mes > 12:
            mes -= 12
            ano += 1

        desc = f"{description} ({i+1}/{installments})"
        cur.execute(
            """INSERT INTO payments
               (user_id, description, category_id, amount, due_date, month, year, paid, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, 0, ?)""",
            (user_id, desc, category_id, parcela, "01", mes, ano, _now())
        )

    conn.commit()
    conn.close()

def list_payments(user_id, month, year):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """SELECT p.id, p.description, p.amount, p.due_date, p.paid, c.name
           FROM payments p
           LEFT JOIN categories c ON c.id = p.category_id
           WHERE p.user_id = ? AND p.month = ? AND p.year = ?
           ORDER BY p.paid ASC, p.due_date ASC, p.id DESC""",
        (user_id, month, year)
    )
    rows = cur.fetchall()
    conn.close()
    return rows

def mark_fatura_cartao(user_id, month, year, categoria_nome):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """UPDATE payments
           SET paid = 1
           WHERE user_id = ? AND month = ? AND year = ?
             AND category_id = (
                SELECT id FROM categories
                WHERE user_id = ? AND name = ?
             )""",
        (user_id, month, year, user_id, categoria_nome)
    )
    conn.commit()
    conn.close()
