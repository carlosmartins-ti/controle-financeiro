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
            ["📊 Dashboard", "🧾 Despesas", "💳 Cartão", "🏷️ Categorias", "💰 Planejamento"]
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

    # ================= DASHBOARD =================
    if page == "📊 Dashboard":
        if not df.empty:
            df2 = df.copy()
            df2["categoria"] = df2["categoria"].fillna("Sem categoria")
            fig = px.pie(df2, names="categoria", values="valor")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Nenhuma despesa cadastrada.")

    # ================= DESPESAS =================
    elif page == "🧾 Despesas":
        despesas = df[df["is_credit"] == 0]

        for _, r in despesas.iterrows():
            a,b,c,d,e = st.columns([4,1.2,1.5,1.2,1])
            a.write(f"**{r.descricao}**")
            b.write(fmt_brl(r.valor))
            c.write(fmt_date_br(r.vencimento))
            d.write("✅ Paga" if r.pago else "🕓 Aberta")

            if not r.pago:
                if e.button("Pagar", key=f"pay_{r.id}"):
                    repos.mark_paid(st.session_state.user_id, r.id, True)
                    st.rerun()
            else:
                if e.button("Desfazer", key=f"unpay_{r.id}"):
                    repos.mark_paid(st.session_state.user_id, r.id, False)
                    st.rerun()

    # ================= CARTÃO =================
    elif page == "💳 Cartão":
        cartao = df[df["is_credit"] == 1]

        if cartao.empty:
            st.info("Nenhuma compra no cartão.")
        else:
            for group, g in cartao.groupby("credit_group"):
                total_fatura = g["valor"].sum()
                pago_fatura = g[g["pago"] == 1]["valor"].sum()

                st.markdown(f"""
                **Fatura:** {group}  
                Total: {fmt_brl(total_fatura)}  
                Pago: {fmt_brl(pago_fatura)}
                """)

                col1, col2 = st.columns(2)
                if col1.button("Marcar fatura como paga", key=f"payg_{group}"):
                    for pid in g["id"]:
                        repos.mark_paid(st.session_state.user_id, pid, True)
                    st.rerun()

                if col2.button("Desfazer fatura", key=f"ung_{group}"):
                    for pid in g["id"]:
                        repos.mark_paid(st.session_state.user_id, pid, False)
                    st.rerun()

                st.divider()

    # ================= CATEGORIAS =================
    elif page == "🏷️ Categorias":
        new = st.text_input("Nova categoria")
        if st.button("Adicionar"):
            repos.create_category(st.session_state.user_id, new)
            st.rerun()

        for cid, name in repos.list_categories(st.session_state.user_id):
            a,b = st.columns([4,1])
            a.write(name)
            if b.button("Excluir", key=f"cat_{cid}"):
                repos.delete_category(st.session_state.user_id, cid)
                st.rerun()

    # ================= PLANEJAMENTO =================
    elif page == "💰 Planejamento":
        renda = st.number_input("Renda mensal", value=float(budget["income"]))
        meta = st.number_input("Meta de gastos", value=float(budget["expense_goal"]))

        if st.button("Salvar planejamento"):
            repos.upsert_budget(st.session_state.user_id, month, year, renda, meta)
            st.success("Planejamento salvo!")

# ==================== ROUTER ====================
if st.session_state.user_id is None:
    screen_auth()
else:
    screen_app()
