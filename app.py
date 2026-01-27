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

# ==================== CSS GLOBAL (MOBILE + DARK/LIGHT) ====================
st.markdown("""
<style>

/* ===============================
   INPUTS (TEXT / TEXTAREA)
   =============================== */
div[data-testid="stTextInput"] input,
div[data-testid="stTextArea"] textarea {
    background-color: rgba(255,255,255,0.08) !important;
    color: var(--text-color) !important;
    border-radius: 6px !important;
    border: 1px solid rgba(255,255,255,0.15) !important;
    font-size: 16px !important;
}

/* Placeholder */
div[data-testid="stTextInput"] input::placeholder,
div[data-testid="stTextArea"] textarea::placeholder {
    color: rgba(180,180,180,0.9) !important;
}

/* ===============================
   PASSWORD INPUT (CORRIGIDO)
   =============================== */
div[data-testid="stPasswordInput"] {
    position: relative;
}

div[data-testid="stPasswordInput"] input {
    background-color: rgba(255,255,255,0.08) !important;
    color: var(--text-color) !important;
    padding-right: 48px !important;
    height: 42px !important;
    line-height: 42px !important;
    font-size: 16px !important;
}

/* ÍCONE DO OLHO — FIX MOBILE */
div[data-testid="stPasswordInput"] button {
    position: absolute !important;
    right: 10px !important;
    top: 6px !important;
    height: 30px !important;
    width: 30px !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    background: transparent !important;
}

/* ===============================
   BOX DE AUTENTICAÇÃO
   =============================== */
.auth-box {
    background-color: rgba(255,255,255,0.08) !important;
    color: var(--text-color) !important;
    border-left: 5px solid #4f8bf9;
    border-radius: 8px;
    padding: 12px;
    margin-bottom: 16px;
    font-size: 14px;
}

/* ===============================
   MOBILE
   =============================== */
@media (max-width: 768px) {
    h1 {
        font-size: 1.4rem !important;
    }

    button {
        width: 100%;
    }
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
    if not d:
        return ""
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
    st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)

    st.markdown(
        """
        <div class="auth-box">
        🔐 <b>Autenticação e autoria do projeto</b><br>
        Aplicação desenvolvida por <b>Carlos Martins</b>.<br>
        Para dúvidas, sugestões ou suporte técnico:<br>
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
                repos.ensure_default_categories(uid)
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
            create_user(u, p, q, a)
            st.success("Conta criada! Faça login.")

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

# ==================== APP ====================
def screen_app():
    with st.sidebar:
        st.markdown(f"**Usuário:** `{st.session_state.username}`")

        today = date.today()
        month_label = st.selectbox("Mês", MESES, index=today.month - 1)
        year = st.selectbox("Ano", list(range(today.year - 2, today.year + 3)))
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
        "id","descricao","valor","vencimento","pago","data_pagamento",
        "categoria_id","categoria","is_credit","installments",
        "installment_index","credit_group"
    ])

    total = df["valor"].sum() if not df.empty else 0
    pago = df[df["pago"] == 1]["valor"].sum() if not df.empty else 0
    aberto = total - pago

    budget = repos.get_budget(st.session_state.user_id, month, year)
    saldo = budget["income"] - total

    st.title("💳 Controle Financeiro")
    st.caption(f"Período: **{month_label}/{year}**")

    c1,c2,c3,c4 = st.columns(4)
    c1.metric("Total", fmt_brl(total))
    c2.metric("Pago", fmt_brl(pago))
    c3.metric("Em aberto", fmt_brl(aberto))
    c4.metric("Saldo", fmt_brl(saldo))

    st.divider()

    # ================= DESPESAS =================
    if page == "🧾 Despesas":
        st.subheader("🧾 Despesas")

        cats = repos.list_categories(st.session_state.user_id)
        cat_map = {name: cid for cid, name in cats}
        cat_names = ["(Sem categoria)"] + list(cat_map.keys())

        with st.expander("➕ Adicionar despesa", expanded=True):
            desc = st.text_input("Descrição")
            val = st.number_input("Valor (R$)", min_value=0.0)
            venc = st.date_input("Vencimento", format="DD/MM/YYYY")
            cat_name = st.selectbox("Categoria", cat_names)
            parcelas = st.number_input("Parcelas", min_value=1, value=1)

            if st.button("Adicionar"):
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
                st.rerun()

        st.divider()

        for r in rows:
            pid, desc, amount, due, paid = r[0], r[1], r[2], r[3], r[4]
            cat_name = r[7]

            a,b,c,d,e = st.columns([4,1.2,1.5,1.2,1])
            a.write(f"**{desc}**" + (f"  \n🏷️ {cat_name}" if cat_name else ""))
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
