import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import date, datetime
import streamlit.components.v1 as components

from database import init_db
from auth import authenticate, create_user, get_security_question, reset_password
import repos

# ================= SETUP =================
st.set_page_config(
    page_title="Controle Financeiro",
    page_icon="💳",
    layout="wide"
)

with open("style.css", "r", encoding="utf-8") as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

init_db()

ADMIN_USERNAME = "carlos.martins"

MESES = [
    "Janeiro","Fevereiro","Março","Abril","Maio","Junho",
    "Julho","Agosto","Setembro","Outubro","Novembro","Dezembro"
]

# ================= UTILS =================
def fmt_brl(v):
    return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def format_date_br(s):
    if not s:
        return ""
    try:
        return datetime.fromisoformat(str(s)).strftime("%d/%m/%Y")
    except:
        return str(s)

def is_admin():
    return st.session_state.username == ADMIN_USERNAME

# ================= SESSION =================
for k in ["user_id", "username", "edit_id"]:
    if k not in st.session_state:
        st.session_state[k] = None

# ================= AUTH =================
def screen_auth():
    st.title("💳 Controle Financeiro")

    components.html(
        """
        <div style="background:linear-gradient(135deg,#1f2937,#111827);
                    border-radius:12px;padding:16px;margin:14px 0;
                    color:#e5e7eb;box-shadow:0 6px 18px rgba(0,0,0,.45);
                    font-family:system-ui;">
            <strong>🔐 Autenticação e autoria do projeto</strong><br>
            Aplicação desenvolvida por <b>Carlos Martins</b><br>
            📧 <a href="mailto:cr954479@gmail.com" style="color:#60a5fa">
                cr954479@gmail.com
            </a>
        </div>
        """,
        height=150
    )

    t1, t2, t3 = st.tabs(["Entrar", "Criar conta", "Recuperar senha"])

    with t1:
        u = st.text_input("Usuário", key="login_user")
        p = st.text_input("Senha", type="password", key="login_pass")
        if st.button("Entrar"):
            uid = authenticate(u, p)
            if uid:
                st.session_state.user_id = uid
                st.session_state.username = u.strip().lower()
                st.rerun()
            else:
                st.error("Usuário ou senha inválidos.")

    with t2:
        u = st.text_input("Novo usuário")
        p = st.text_input("Nova senha", type="password")
        q = st.selectbox(
            "Pergunta de segurança",
            [
                "Qual o nome do seu primeiro pet?",
                "Qual o nome da sua mãe?",
                "Qual sua cidade de nascimento?",
                "Qual seu filme favorito?"
            ]
        )
        a = st.text_input("Resposta")
        if st.button("Criar conta"):
            create_user(u, p, q, a)
            uid = authenticate(u, p)
            st.session_state.user_id = uid
            st.session_state.username = u.strip().lower()
            repos.seed_default_categories(uid)
            st.success("Conta criada com sucesso.")
            st.rerun()

    with t3:
        u = st.text_input("Usuário")
        q = get_security_question(u) if u else None
        if q:
            st.info(q)
            a = st.text_input("Resposta")
            np = st.text_input("Nova senha", type="password")
            if st.button("Redefinir senha"):
                if reset_password(u, a, np):
                    st.success("Senha alterada!")
                else:
                    st.error("Resposta incorreta.")

# ================= APP =================
def screen_app():
    with st.sidebar:
        today = date.today()
        month_label = st.selectbox("Mês", MESES, index=today.month - 1)
        year = st.selectbox("Ano", list(range(today.year - 2, today.year + 3)), index=2)
        month = MESES.index(month_label) + 1
        page = st.radio("Menu", ["📊 Dashboard", "🧾 Despesas", "🏷️ Categorias", "💰 Planejamento"])

    repos.seed_default_categories(st.session_state.user_id)
    rows = repos.list_payments(st.session_state.user_id, month, year)

    df = pd.DataFrame(rows, columns=[
        "id","Descrição","Valor","Vencimento","Pago","Data pagamento",
        "CategoriaID","Categoria","is_credit","installments",
        "installment_index","credit_group"
    ])

    if page == "🧾 Despesas":
        cats = repos.list_categories(st.session_state.user_id)
        cat_map = {name: cid for cid, name in cats}
        cat_names = ["(Sem categoria)"] + list(cat_map.keys())

        for r in rows:
            pid, desc, amount, due, paid, _, _, cat_name, *_ = r

            st.write(desc, fmt_brl(amount), format_date_br(due))

            if st.button("✏️ Editar", key=f"edit_{pid}"):
                st.session_state.edit_id = pid

            if st.session_state.edit_id == pid:
                with st.form(f"edit_form_{pid}"):
                    n_desc = st.text_input("Descrição", value=desc)
                    n_val = st.number_input("Valor", value=float(amount))
                    n_venc = st.date_input(
                        "Vencimento",
                        value=datetime.fromisoformat(due).date()
                    )

                    current_cat = cat_name if cat_name in cat_map else "(Sem categoria)"
                    n_cat = st.selectbox(
                        "Categoria",
                        cat_names,
                        index=cat_names.index(current_cat)
                    )

                    salvar = st.form_submit_button("Salvar")
                    cancelar = st.form_submit_button("Cancelar")

                    if salvar:
                        cid = None if n_cat == "(Sem categoria)" else cat_map[n_cat]
                        repos.update_payment(
                            st.session_state.user_id,
                            pid,
                            n_desc,
                            n_val,
                            str(n_venc),
                            cid
                        )
                        st.session_state.edit_id = None
                        st.rerun()

                    if cancelar:
                        st.session_state.edit_id = None
                        st.rerun()

# ================= ROUTER =================
if st.session_state.user_id is None:
    screen_auth()
else:
    screen_app()
