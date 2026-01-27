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
def add_payment(user_id, description, amount, due_date, month, year, category_id=None, parent_id=None):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """INSERT INTO payments
           (user_id, description, category_id, amount, due_date, month, year, paid, parent_id, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, 0, ?, ?)""",
        (user_id, description, category_id, amount, due_date, month, year, parent_id, _now())
    )
    conn.commit()
    conn.close()

def list_payments(user_id, month, year):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """SELECT id, description, amount, due_date, paid, category_id
           FROM payments
           WHERE user_id = ? AND month = ? AND year = ?""",
        (user_id, month, year)
    )
    rows = cur.fetchall()
    conn.close()
    return rows

def mark_month_paid_by_category(user_id, month, year, category_name):
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
        (user_id, month, year, user_id, category_name)
    )
    conn.commit()
    conn.close()

# ===================== PARCELAMENTO =====================
def create_installments(user_id, description, total_amount, installments, start_month, start_year, category_id):
    parcela_valor = round(total_amount / installments, 2)
    current_month = start_month
    current_year = start_year

    conn = get_connection()
    cur = conn.cursor()

    # cria pagamento pai
    cur.execute(
        """INSERT INTO payments
           (user_id, description, category_id, amount, due_date, month, year, paid, parent_id, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, 0, NULL, ?)""",
        (user_id, description + " (1/{} )".format(installments),
         category_id, parcela_valor, "01", current_month, current_year, _now())
    )
    parent_id = cur.lastrowid

    for i in range(installments):
        mes = start_month + i
        ano = start_year
        while mes > 12:
            mes -= 12
            ano += 1

        desc = f"{description} ({i+1}/{installments})"
        cur.execute(
            """INSERT INTO payments
               (user_id, description, category_id, amount, due_date, month, year, paid, parent_id, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, 0, ?, ?)""",
            (user_id, desc, category_id, parcela_valor, "01", mes, ano, parent_id, _now())
        )

    conn.commit()
    conn.close()
