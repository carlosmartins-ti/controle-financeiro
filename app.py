import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import date, datetime

from database import init_db
from auth import authenticate, create_user, get_security_question, reset_password
import repos

# ================= SETUP =================
st.set_page_config(
    page_title="Controle Financeiro",
    page_icon="💳",
    layout="wide"
)

# 🔥 CSS (OBRIGATÓRIO PARA MOBILE)
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

def status_vencimento(due_date, paid):
    if paid:
        return "", ""
    try:
        d = datetime.fromisoformat(str(due_date)).date()
    except:
        return "", ""
    today = date.today()
    if d < today:
        return "🔴 VENCIDA", "#ff4d4d"
    if d == today:
        return "🟡 VENCE HOJE", "#ffcc00"
    return "", ""

def is_admin():
    return st.session_state.username == ADMIN_USERNAME

# ================= SESSION =================
for k in ["user_id", "username"]:
    if k not in st.session_state:
        st.session_state[k] = None

# ================= AUTH =================
def screen_auth():
    st.title("💳 Controle Financeiro")

    st.markdown(
    """
    <div class="auth-box">
        🔐 <b>Autenticação e autoria do projeto</b><br>
        Aplicação desenvolvida por <b>Carlos Martins</b>.<br>
        📧 <a href="mailto:cr954479@gmail.com">cr954479@gmail.com</a>
    </div>
    """,
    unsafe_allow_html=True
)

    t1, t2, t3 = st.tabs(["Entrar", "Criar conta", "Recuperar senha"])

    # ---------- LOGIN ----------
    with t1:
        u = st.text_input("Usuário", key="login_user")
        p = st.text_input("Senha", type="password", key="login_pass")

        if st.button("Entrar", key="btn_login"):
            uid = authenticate(u, p)
            if uid:
                st.session_state.user_id = uid
                st.session_state.username = u.strip().lower()
                st.rerun()
            else:
                st.error("Usuário ou senha inválidos.")

    # ---------- CADASTRO ----------
    with t2:
        u = st.text_input("Novo usuário", key="signup_user")
        p = st.text_input("Nova senha", type="password", key="signup_pass")
        q = st.selectbox(
            "Pergunta de segurança",
            [
                "Qual o nome do seu primeiro pet?",
                "Qual o nome da sua mãe?",
                "Qual sua cidade de nascimento?",
                "Qual seu filme favorito?"
            ],
            key="signup_q"
        )
        a = st.text_input("Resposta", key="signup_a")

        if st.button("Criar conta", key="btn_signup"):
            try:
                create_user(u, p, q, a)

                uid = authenticate(u, p)
                st.session_state.user_id = uid
                st.session_state.username = u.strip().lower()

                repos.seed_default_categories(uid)

                st.success("Conta criada com sucesso.")
                st.rerun()

            except ValueError as e:
                st.error(str(e))

    # ---------- RECUPERAR SENHA ----------
    with t3:
        u = st.text_input("Usuário", key="reset_user")
        q = get_security_question(u) if u else None

        if q:
            st.info(q)
            a = st.text_input("Resposta", key="reset_a")
            np = st.text_input("Nova senha", type="password", key="reset_np")

            if st.button("Redefinir senha", key="btn_reset"):
                if reset_password(u, a, np):
                    st.success("Senha alterada!")
                else:
                    st.error("Resposta incorreta.")


# ================= APP =================
with st.expander("➕ Adicionar despesa", expanded=True):
    with st.form("form_add_despesa", clear_on_submit=True):

        a1, a2, a3, a4, a5 = st.columns([3, 1, 1.3, 2, 1])

        desc = a1.text_input("Descrição")
        val = a2.number_input("Valor (R$)", min_value=0.0, step=10.0)
        venc = a3.date_input(
            "Vencimento",
            value=date.today(),
            format="DD/MM/YYYY"
        )
        cat_name = a4.selectbox("Categoria", cat_names)
        parcelas = a5.number_input("Parcelas", min_value=1, step=1, value=1)

        submitted = st.form_submit_button("Adicionar")

    if submitted:
        if not desc or val <= 0:
            st.error("Preencha a descrição e um valor válido.")
        else:
            cid = None if cat_name == "(Sem categoria)" else cat_map[cat_name]

            repos.add_payment(
                st.session_state.user_id,
                desc,
                val,
                str(venc),
                month,
                year,
                cid,
                is_credit=1 if parcelas > 1 else 0,
                installments=parcelas
            )

            st.success("Despesa adicionada com sucesso!")
            st.rerun()


# ================= ROUTER =================
if st.session_state.user_id is None:
    screen_auth()
else:
    screen_app()
