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
for k in ["user_id", "username"]:
    if k not in st.session_state:
        st.session_state[k] = None

# ================= AUTH =================
def screen_auth():
    st.title("💳 Controle Financeiro")

    components.html(
        """
        <div style="background: linear-gradient(135deg,#1f2937,#111827);
                    border-radius:12px;padding:16px;margin:14px 0;color:#e5e7eb;">
            <strong>🔐 Autenticação e autoria do projeto</strong><br><br>
            Aplicação desenvolvida por <strong>Carlos Martins</strong><br>
            📧 <a href="mailto:cr954479@gmail.com" style="color:#60a5fa">cr954479@gmail.com</a>
        </div>
        """,
        height=150
    )

    t1, t2, t3 = st.tabs(["Entrar", "Criar conta", "Recuperar senha"])

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
def screen_app():
    with st.sidebar:
        st.markdown(f"**Usuário:** `{st.session_state.username}`")

        today = date.today()
        month_label = st.selectbox("Mês", MESES, index=today.month - 1)
        year = st.selectbox("Ano", list(range(today.year - 2, today.year + 3)), index=2)
        month = MESES.index(month_label) + 1

        page = st.radio(
            "Menu",
            ["📊 Dashboard", "🧾 Despesas", "🏷️ Categorias", "💰 Planejamento"]
        )

        if st.button("Sair"):
            st.session_state.user_id = None
            st.session_state.username = None
            st.rerun()

    rows = repos.list_payments(st.session_state.user_id, month, year)
    df = pd.DataFrame(rows, columns=[
        "id","Descrição","Valor","Vencimento","Pago","DataPg",
        "CategoriaID","Categoria","is_credit","installments",
        "installment_index","credit_group"
    ])

    st.title("💳 Controle Financeiro")
    st.caption(f"{month_label}/{year}")

    # ================= DESPESAS =================
    if page == "🧾 Despesas":
        st.subheader("🧾 Despesas")

        cats = repos.list_categories(st.session_state.user_id)
        cat_map = {n:c for c,n in cats}
        cat_names = ["(Sem categoria)"] + list(cat_map.keys())

        with st.expander("➕ Adicionar despesa", expanded=True):
            with st.form("add"):
                desc = st.text_input("Descrição")
                val = st.number_input("Valor", min_value=0.0)
                venc = st.date_input("Vencimento", date.today())
                cat = st.selectbox("Categoria", cat_names)
                ok = st.form_submit_button("Adicionar")

            if ok:
                repos.add_payment(
                    st.session_state.user_id,
                    desc, val, str(venc),
                    month, year,
                    None if cat=="(Sem categoria)" else cat_map[cat],
                    0, 1
                )
                st.rerun()

        if not df.empty:
            cartao_id = next((cid for cid,n in cats if n.lower()=="cartão de crédito"), None)

            if cartao_id:
                total_fatura = df[df["CategoriaID"]==cartao_id]["Valor"].sum()
                st.metric("💳 Total da fatura", fmt_brl(total_fatura))

            for r in rows:
                pid, desc, val, due, paid, _, _, cat, *_ = r
                a,b,c,d,e = st.columns([4,1.2,1.8,1.2,1])
                a.write(desc)
                b.write(fmt_brl(val))
                c.write(format_date_br(due))
                d.write("✅" if paid else "🕓")
                if e.button("Excluir", key=f"del{pid}"):
                    repos.delete_payment(st.session_state.user_id, pid)
                    st.rerun()

# ================= ROUTER =================
if st.session_state.user_id is None:
    screen_auth()
else:
    screen_app()
