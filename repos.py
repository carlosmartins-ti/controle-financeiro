import datetime
from database import get_connection

# ======================
# Utils
# ======================
def _now():
    return datetime.datetime.now().isoformat(timespec="seconds")

# ======================
# Default Categories
# ======================
DEFAULT_CATEGORIES = [
    "Aluguel","Condomínio","Água","Luz","Plano celular","Internet",
    "Supermercado","Restaurante","Delivery / iFood","Refeição trabalho",
    "TV / Streaming","Transporte","Cartão de crédito","Contas fixas","Lazer",
    "Saúde","Educação","Poupança","Roupas","Calçados","Cosméticos","Farmácia",
    "Academia","Barbeiro / Salão","Cinema","Viagem","Passeios","Jogos",
    "Bares / festas","Faculdade","Móveis","Outros","Imprevistos",
]

# ======================
# Categories
# ======================
def seed_default_categories(user_id: int):
    if user_id is None:
        return

    conn = get_connection()
    cur = conn.cursor()

    for name in DEFAULT_CATEGORIES:
        cur.execute(
            """
            INSERT INTO categories (user_id, name, created_at)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id, name) DO NOTHING
            """,
            (user_id, name, _now())
        )

    conn.commit()
    conn.close()

def list_categories(user_id: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT id, name FROM categories WHERE user_id = ? ORDER BY name",
        (user_id,)
    )
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
    cur.execute(
        "UPDATE payments SET category_id = NULL WHERE user_id = ? AND category_id = ?",
        (user_id, category_id)
    )
    cur.execute(
        "DELETE FROM categories WHERE user_id = ? AND id = ?",
        (user_id, category_id)
    )
    conn.commit()
    conn.close()

# ======================
# Payments (mantém o que você já tinha)
# ======================
def add_payment(*args, **kwargs):
    raise NotImplementedError("add_payment já existe no seu repos.py original")

def list_payments(*args, **kwargs):
    raise NotImplementedError("list_payments já existe no seu repos.py original")

def mark_paid(*args, **kwargs):
    raise NotImplementedError("mark_paid já existe no seu repos.py original")

def delete_payment(*args, **kwargs):
    raise NotImplementedError("delete_payment já existe no seu repos.py original")

def mark_credit_invoice_paid(*args, **kwargs):
    raise NotImplementedError("mark_credit_invoice_paid já existe no seu repos.py original")

def unmark_credit_invoice_paid(*args, **kwargs):
    raise NotImplementedError("unmark_credit_invoice_paid já existe no seu repos.py original")

def get_budget(*args, **kwargs):
    raise NotImplementedError("get_budget já existe no seu repos.py original")

def upsert_budget(*args, **kwargs):
    raise NotImplementedError("upsert_budget já existe no seu repos.py original")
