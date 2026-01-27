import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import date, datetime

from database import init_db
from auth import authenticate, create_user, get_security_question, reset_password
import repos

# ==================== CONFIG ====================
st.set_page_config(
    page_title="Controle Financeiro",
    page_icon="💳",
    layout="wide"
)

init_db()

# ==================== CSS GLOBAL ====================
st.markdown("""
<style>

/* INPUTS */
div[data-testid="stTextInput"] input,
div[data-testid="stTextArea"] textarea {
    background-color: rgba(255,255,255,0.08) !important;
    color: var(--text-color) !important;
    border-radius: 6px !important;
    border: 1px solid rgba(255,255,255,0.15) !important;
    font-size: 16px !important;
}

/* PLACEHOLDER */
div[data-testid="stTextInput"] input::placeholder {
    color: rgba(180,180,180,0.9) !important;
}

/* PASSWORD */
div[data-testid="stPasswordInput"] {
    position: relative;
}

div[data-testid="stPasswordInput"] input {
    padding-right: 48px !important;
    height: 42px !important;
}

div[data-testid="stPasswordInput"] button {
    position: absolute !important;
    right: 10px !important;
    top: 6px !important;
    height: 30px !important;
    width: 30px !important;
    background: transparent !important;
}

/* AUTH BOX */
.auth-box {
    background-color: rgba(255,255,255,0.08) !important;
    border-left: 5px solid #4f8bf9;
    border-radius: 8px;
    padding: 12px;
    margin-bottom: 16px;
}

/* MOBILE */
@media (max-width: 768px) {
    h1 { font-size: 1.4rem !important; }
    button { width: 100%; }
}

</style>
""", unsafe_allow_html=True)

# ==================== CONSTANTES ====================
MESES = [
    "Janeiro","Fevereiro","Março","Abril","Maio","Junho",
    "Julho","Agosto","Setembro","Outubro","Novembro","Dezembro"
]

# ==================== FORMATADORES ====================
def fmt_brl(v):
    return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def fmt_date_br(d):
    try:
        return datetime.strptime(str(d), "%Y-%m-%d").strftime("%d/%m/%Y")
    except:
        return str(d)

# ==================== SESSION ====================
for k in ["user_id", "username"]:
    if k not in st.session_state:
        st.session_state[k] = None

# ==================== AUTH ====================
def screen_auth():
    st.title("💳 Controle Financeiro")

    st.markdown(
        """
        <div class="auth-box">
        🔐 <b>Autenticação e autoria do projeto</b><br>
        Aplicação desenvolvida por <b>Carlos Martins</b><br>
        📧 <a href="mailto:cr954479@gmail.com">cr954479@gmail.com</a>
        </div>
        """,
        unsafe_allow_html=True
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
                repos.ensure_default_categories(uid)
                st.rerun()
            else:
                st.error("Usuário ou senha inválidos.")

    with t2:
        u = st.text_input("Novo usuário")
        p = st.text_input("Nova senha", type="password")
        q = st.selectbox("Pergunta de segurança", [
            "Qual o nome do seu primeiro pet?",
            "Qual o nome da sua mãe?",
            "Qual sua cidade de nascimento?",
            "Qual seu filme favorito?"
        ])
        a = st.text_input("Resposta")

        if st.button("Criar conta"):
            create_user(u, p, q, a)
            st.success("Conta criada!")

    with t3:
        u = st.text_input("Usuário")
        q = get_security_question(u) if u else None
        if q:
            st.info(q)
            a = st.text_input("Resposta")
            np = st.text_input("Nova senha", type="password")
            if st.button("Redefinir"):
                if reset_password(u, a, np):
                    st.success("Senha alterada!")

# ==================== APP ====================
def screen_app():
    with st.sidebar:
        st.markdown(f"**Usuário:** `{st.session_state.username}`")

        today = date.today()
        month_label = st.selectbox("Mês", MESES, index=today.month - 1)
        year = st.selectbox("Ano", list(range(today.year-2, today.year+3)))
        month = MESES.index(month_label) + 1

        page = st.radio("Menu", [
            "📊 Dashboard", "🧾 Despesas", "🏷️ Categorias", "💰 Planejamento"
        ])

        if st.button("Sair"):
            st.session_state.user_id = None
            st.session_state.username = None
            st.rerun()

    rows = repos.list_payments(st.session_state.user_id, month, year)

    # ================= DESPESAS =================
    if page == "🧾 Despesas":
        st.subheader("🧾 Despesas")

        # >>>>>>>>>>> FATURA DO CARTÃO (ADICIONADO)
        credit_rows = [r for r in rows if r[7] and "cart" in r[7].lower()]
        if credit_rows:
            open_credit = [r for r in credit_rows if r[4] == 0]
            paid_credit = [r for r in credit_rows if r[4] == 1]

            total_fatura = sum(float(r[2]) for r in open_credit)

            st.subheader("💳 Fatura do cartão")
            c1, c2 = st.columns([3,1])
            c1.metric("Total da fatura", fmt_brl(total_fatura))

            if open_credit:
                if c2.button("💰 Pagar fatura do cartão"):
                    repos.mark_credit_invoice_paid(
                        st.session_state.user_id, month, year
                    )
                    st.rerun()
            elif paid_credit:
                if c2.button("🔄 Desfazer pagamento da fatura"):
                    repos.unmark_credit_invoice_paid(
                        st.session_state.user_id, month, year
                    )
                    st.rerun()

            st.divider()
        # <<<<<<<<<< FATURA DO CARTÃO

        for r in rows:
            pid, desc, amount, due, paid = r[0], r[1], r[2], r[3], r[4]
            cat = r[7]

            a,b,c,d,e = st.columns([4,1.2,1.5,1.2,1])
            a.write(f"**{desc}**" + (f"  \n🏷️ {cat}" if cat else ""))
            b.write(fmt_brl(amount))
            c.write(fmt_date_br(due))
            d.write("✅ Paga" if paid else "🕓 Aberta")

            if not paid:
                if e.button("Pagar", key=f"pay_{pid}"):
                    repos.mark_paid(st.session_state.user_id, pid, True)
                    st.rerun()
            else:
                if e.button("Desfazer", key=f"unpay_{pid}"):
                    repos.mark_paid(st.session_state.user_id, pid, False)
                    st.rerun()

# ==================== ROUTER ====================
if st.session_state.user_id is None:
    screen_auth()
else:
    screen_app()
