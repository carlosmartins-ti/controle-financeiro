import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import date, datetime

from database import init_db
from auth import authenticate, create_user, get_security_question, reset_password
import repos
from export_utils import export_excel_bytes, export_pdf_bytes


# -------------------- Setup --------------------
st.set_page_config(page_title="Controle Financeiro", page_icon="💳", layout="wide")
init_db()


def inject_css():
    try:
        with open("style.css", "r", encoding="utf-8") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
    except FileNotFoundError:
        pass


inject_css()

# ========================
# CONTROLE DE UI (ADMIN)
# ========================
def hide_share_only():
    st.markdown(
        """
        <style>
        button[title="Share"] {display:none !important;}
        a[title="View source"] {display:none !important;}
        a[title="Edit this app"] {display:none !important;}
        </style>
        """,
        unsafe_allow_html=True
    )


if st.session_state.get("username") != "carlos.martins":
    hide_share_only()


# -------------------- Session --------------------
if "user_id" not in st.session_state:
    st.session_state.user_id = None
if "username" not in st.session_state:
    st.session_state.username = None
if "edit_id" not in st.session_state:
    st.session_state.edit_id = None


MESES = [
    "Janeiro","Fevereiro","Março","Abril","Maio","Junho",
    "Julho","Agosto","Setembro","Outubro","Novembro","Dezembro"
]

CATEGORIA_CARTAO = "Cartão de crédito"


def fmt_brl(v):
    return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def parse_date_str(s):
    try:
        return datetime.fromisoformat(str(s)).date()
    except:
        try:
            return datetime.strptime(str(s), "%Y-%m-%d").date()
        except:
            return date.today()


# -------------------- Auth --------------------
def screen_auth():
    st.title("💳 Controle Financeiro")

    tab_login, tab_signup, tab_reset = st.tabs(
        ["Entrar", "Criar conta", "Recuperar senha"]
    )

    with tab_login:
        u = st.text_input("Usuário")
        p = st.text_input("Senha", type="password")
        if st.button("Entrar", use_container_width=True):
            uid = authenticate(u, p)
            if uid:
                st.session_state.user_id = uid
                st.session_state.username = u
                st.rerun()
            else:
                st.error("Usuário ou senha inválidos")

    with tab_signup:
        u = st.text_input("Novo usuário")
        p = st.text_input("Nova senha", type="password")
        q = st.selectbox(
            "Pergunta de segurança",
            [
                "Qual o nome do seu primeiro pet?",
                "Qual o nome da sua mãe?",
                "Qual sua cidade de nascimento?",
                "Qual seu filme favorito?",
            ]
        )
        a = st.text_input("Resposta")
        if st.button("Criar conta", type="primary", use_container_width=True):
            try:
                create_user(u, p, q, a)
                st.success("Conta criada! Faça login.")
            except Exception as e:
                st.error(str(e))

    with tab_reset:
        u = st.text_input("Usuário")
        q = get_security_question(u) if u else None
        if q:
            st.info(q)
            a = st.text_input("Resposta")
            np = st.text_input("Nova senha", type="password")
            if st.button("Redefinir senha", use_container_width=True):
                if reset_password(u, a, np):
                    st.success("Senha alterada")
                else:
                    st.error("Resposta incorreta")


# -------------------- Main app --------------------
def screen_app():
    with st.sidebar:
        st.markdown(f"**Usuário:** `{st.session_state.username}`")

        today = date.today()
        month_label = st.selectbox("Mês", MESES, index=today.month-1)
        year = st.selectbox("Ano", list(range(today.year-2, today.year+3)), index=2)
        month = MESES.index(month_label) + 1

        st.divider()

        # 🔴 AQUI ESTÁ A CORREÇÃO CRÍTICA
        page = st.radio(
            "Menu",
            ["📊 Dashboard", "🧾 Pagamentos", "🏷️ Categorias", "💰 Planejamento", "📤 Exportar"],
            key="menu_page"
        )

        st.divider()

        if st.button("Sair", use_container_width=True):
            st.session_state.user_id = None
            st.session_state.username = None
            st.session_state.edit_id = None
            st.rerun()

    rows = repos.list_payments(st.session_state.user_id, month, year)
    df = pd.DataFrame(
        rows,
        columns=["id","Descrição","Valor","Vencimento","Pago","Data pagamento","CategoriaID","Categoria"]
    )

    total = float(df["Valor"].sum()) if not df.empty else 0.0
    total_pago = float(df.loc[df["Pago"]==1, "Valor"].sum()) if not df.empty else 0.0
    total_aberto = total - total_pago

    overdue = 0.0
    if not df.empty:
        overdue = float(
            df[
                (df["Pago"] == 0)
                & (df["Vencimento"].apply(parse_date_str) < date.today())
            ]["Valor"].sum()
        )

    budget = repos.get_budget(st.session_state.user_id, month, year)
    income = float(budget["income"])
    saldo = income - total

    st.title("💳 Controle Financeiro")
    st.caption(f"Período: **{MESES[month-1]}/{year}**")

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Total do mês", fmt_brl(total))
    c2.metric("Pago", fmt_brl(total_pago))
    c3.metric("Em aberto", fmt_brl(total_aberto))
    c4.metric("Em atraso", fmt_brl(overdue))
    c5.metric("Saldo (renda - total)", fmt_brl(saldo))

    st.divider()
# ================= DASHBOARD =================
if page == "📊 Dashboard":
    st.subheader("📊 Dashboard")

    if df.empty:
        st.info("Sem dados para este mês/ano.")
    else:
        # normaliza categorias vazias
        df_dash = df.copy()
        df_dash["Categoria"] = df_dash["Categoria"].fillna("Sem categoria")
        df_dash["Status"] = df_dash["Pago"].map({0: "Em aberto", 1: "Pago"})

        col1, col2 = st.columns([2, 1])

        with col1:
            fig_cat = px.pie(
                df_dash,
                names="Categoria",
                values="Valor",
                title="Gastos por categoria"
            )
            st.plotly_chart(fig_cat, use_container_width=True)

        with col2:
            resumo_status = (
                df_dash.groupby("Status", as_index=False)["Valor"]
                .sum()
            )
            fig_status = px.bar(
                resumo_status,
                x="Status",
                y="Valor",
                title="Pago x Em aberto",
                text_auto=True
            )
            st.plotly_chart(fig_status, use_container_width=True)

        st.divider()

        resumo_cat = (
            df_dash.groupby("Categoria", as_index=False)["Valor"]
            .sum()
            .sort_values("Valor", ascending=False)
        )

        st.markdown("### 📌 Resumo por categoria")
        st.dataframe(
            resumo_cat,
            use_container_width=True,
            hide_index=True
        )

# -------------------- Router --------------------
if st.session_state.user_id is None:
    screen_auth()
else:
    screen_app()
