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
div[data-testid="stTextInput"] input,
div[data-testid="stTextArea"] textarea {
    background-color: rgba(255,255,255,0.08) !important;
    color: var(--text-color) !important;
    border-radius: 6px !important;
    border: 1px solid rgba(255,255,255,0.15) !important;
    font-size: 16px !important;
}
div[data-testid="stPasswordInput"] input {
    padding-right: 48px !important;
}
div[data-testid="stPasswordInput"] button {
    position: absolute !important;
    right: 10px !important;
    top: 6px !important;
}
.auth-box {
    background-color: rgba(255,255,255,0.08) !important;
    border-left: 5px solid #4f8bf9;
    border-radius: 8px;
    padding: 12px;
    margin-bottom: 16px;
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

    st.markdown("""
    <div class="auth-box">
    🔐 <b>Autenticação e autoria do projeto</b><br>
    Aplicação desenvolvida por <b>Carlos Martins</b><br>
    📧 <a href="mailto:cr954479@gmail.com">cr954479@gmail.com</a>
    </div>
    """, unsafe_allow_html=True)

    t1, t2, t3 = st.tabs(["Entrar", "Criar conta", "Recuperar senha"])

    with t1:
        u = st.text_input("Usuário")
        p = st.text_input("Senha", type="password")
        if st.button("Entrar"):
            uid = authenticate(u, p)
            if uid:
                st.session_state.user_id = uid
                st.session_state.username = u.lower().strip()
                repos.ensure_default_categories(uid)
                st.rerun()

    with t2:
        u = st.text_input("Novo usuário")
        p = st.text_input("Nova senha", type="password")
        q = st.selectbox("Pergunta", [
            "Nome do primeiro pet?",
            "Nome da mãe?",
            "Cidade de nascimento?"
        ])
        a = st.text_input("Resposta")
        if st.button("Criar conta"):
            create_user(u, p, q, a)
            st.success("Conta criada")

    with t3:
        u = st.text_input("Usuário")
        q = get_security_question(u) if u else None
        if q:
            st.info(q)
            a = st.text_input("Resposta")
            np = st.text_input("Nova senha", type="password")
            if st.button("Redefinir"):
                reset_password(u, a, np)
                st.success("Senha alterada")

# ==================== APP ====================
def screen_app():
    with st.sidebar:
        st.markdown(f"**Usuário:** {st.session_state.username}")
        today = date.today()
        month_label = st.selectbox("Mês", MESES, index=today.month-1)
        year = st.selectbox("Ano", list(range(today.year-2, today.year+3)))
        month = MESES.index(month_label)+1

        page = st.radio("Menu", [
            "📊 Dashboard", "🧾 Despesas", "🏷️ Categorias", "💰 Planejamento"
        ])

        if st.button("Sair"):
            st.session_state.user_id = None
            st.rerun()

    rows = repos.list_payments(st.session_state.user_id, month, year)
    df = pd.DataFrame(rows, columns=[
        "id","descricao","valor","vencimento","pago","data_pagamento",
        "categoria_id","categoria","is_credit","installments",
        "installment_index","credit_group"
    ])

    st.title("💳 Controle Financeiro")

    # ================= DASHBOARD =================
    if page == "📊 Dashboard":
        if not df.empty:
            df["categoria"] = df["categoria"].fillna("Sem categoria")
            fig = px.pie(df, names="categoria", values="valor")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Nenhum dado para exibir")

    # ================= DESPESAS =================
    elif page == "🧾 Despesas":
        st.subheader("🧾 Despesas")

        for r in rows:
            pid, desc, amount, due, paid = r[0], r[1], r[2], r[3], r[4]
            a,b,c,d,e = st.columns([4,1.2,1.5,1.2,1])
            a.write(desc)
            b.write(fmt_brl(amount))
            c.write(fmt_date_br(due))
            d.write("✅" if paid else "🕓")

            if not paid:
                if e.button("Pagar", key=f"p{pid}"):
                    repos.mark_paid(st.session_state.user_id, pid, True)
                    st.rerun()
            else:
                if e.button("Desfazer", key=f"u{pid}"):
                    repos.mark_paid(st.session_state.user_id, pid, False)
                    st.rerun()

    # ================= CATEGORIAS =================
    elif page == "🏷️ Categorias":
        new = st.text_input("Nova categoria")
        if st.button("Adicionar"):
            repos.create_category(st.session_state.user_id, new)
            st.rerun()

        for cid, name in repos.list_categories(st.session_state.user_id):
            st.write(name)

    # ================= PLANEJAMENTO =================
    elif page == "💰 Planejamento":
        budget = repos.get_budget(st.session_state.user_id, month, year)
        renda = st.number_input("Renda", value=float(budget["income"]))
        meta = st.number_input("Meta", value=float(budget["expense_goal"]))
        if st.button("Salvar"):
            repos.upsert_budget(st.session_state.user_id, month, year, renda, meta)
            st.success("Planejamento salvo")

# ==================== ROUTER ====================
if st.session_state.user_id is None:
    screen_auth()
else:
    screen_app()
