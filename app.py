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

# -------------------- UI CONTROL --------------------
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
for k in ["user_id", "username", "edit_id"]:
    if k not in st.session_state:
        st.session_state[k] = None

MESES = [
    "Janeiro","Fevereiro","Março","Abril","Maio","Junho",
    "Julho","Agosto","Setembro","Outubro","Novembro","Dezembro"
]

def fmt(v):
    return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def parse_date(s):
    try:
        return datetime.fromisoformat(str(s)).date()
    except:
        return date.today()

# -------------------- Auth --------------------
def screen_auth():
    st.title("💳 Controle Financeiro")

    t1, t2, t3 = st.tabs(["Entrar", "Criar conta", "Recuperar senha"])

    with t1:
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

    with t2:
        u = st.text_input("Novo usuário")
        p = st.text_input("Nova senha", type="password")
        q = st.selectbox(
            "Pergunta de segurança",
            [
                "Nome do primeiro pet?",
                "Nome da mãe?",
                "Cidade onde nasceu?",
                "Filme favorito?"
            ]
        )
        a = st.text_input("Resposta")
        if st.button("Criar conta", type="primary", use_container_width=True):
            create_user(u, p, q, a)
            st.success("Conta criada")

    with t3:
        u = st.text_input("Usuário")
        q = get_security_question(u) if u else None
        if q:
            st.info(q)
            a = st.text_input("Resposta")
            np = st.text_input("Nova senha", type="password")
            if st.button("Redefinir senha"):
                if reset_password(u, a, np):
                    st.success("Senha alterada")
                else:
                    st.error("Resposta incorreta")

# -------------------- App --------------------
def screen_app():
    with st.sidebar:
        st.markdown(f"**Usuário:** `{st.session_state.username}`")

        today = date.today()
        mes_nome = st.selectbox("Mês", MESES, index=today.month-1)
        ano = st.selectbox("Ano", list(range(today.year-2, today.year+3)), index=2)
        mes = MESES.index(mes_nome) + 1

        st.divider()

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

    # -------- Dados base --------
    rows = repos.list_payments(st.session_state.user_id, mes, ano)
    df = pd.DataFrame(
        rows,
        columns=["id","Descrição","Valor","Vencimento","Pago","Data pagamento","CategoriaID","Categoria"]
    )

    total = df["Valor"].sum() if not df.empty else 0
    pago = df[df["Pago"] == 1]["Valor"].sum() if not df.empty else 0
    aberto = total - pago

    atraso = 0.0
    if not df.empty:
        atraso = df[
            (df["Pago"] == 0) &
            (df["Vencimento"].apply(parse_date) < date.today())
        ]["Valor"].sum()

    budget = repos.get_budget(st.session_state.user_id, mes, ano)
    renda = float(budget["income"])
    saldo = renda - total

    st.title("💳 Controle Financeiro")
    st.caption(f"Período: **{mes_nome}/{ano}**")

    c1,c2,c3,c4,c5 = st.columns(5)
    c1.metric("Total do mês", fmt(total))
    c2.metric("Pago", fmt(pago))
    c3.metric("Em aberto", fmt(aberto))
    c4.metric("Em atraso", fmt(atraso))
    c5.metric("Saldo (renda - total)", fmt(saldo))

    st.divider()

    # ================= DASHBOARD =================
    if page == "📊 Dashboard":
        st.subheader("📊 Dashboard")

        if df.empty:
            st.info("Sem dados para este período.")
        else:
            df_d = df.copy()
            df_d["Categoria"] = df_d["Categoria"].fillna("Sem categoria")
            df_d["Status"] = df_d["Pago"].map({0: "Em aberto", 1: "Pago"})

            col1, col2 = st.columns([2,1])

            with col1:
                fig1 = px.pie(
                    df_d,
                    names="Categoria",
                    values="Valor",
                    title="Gastos por categoria"
                )
                st.plotly_chart(fig1, use_container_width=True)

            with col2:
                resumo = df_d.groupby("Status", as_index=False)["Valor"].sum()
                fig2 = px.bar(
                    resumo,
                    x="Status",
                    y="Valor",
                    title="Pago x Em aberto",
                    text_auto=True
                )
                st.plotly_chart(fig2, use_container_width=True)

            st.divider()
            resumo_cat = (
                df_d.groupby("Categoria", as_index=False)["Valor"]
                .sum()
                .sort_values("Valor", ascending=False)
            )
            st.dataframe(resumo_cat, use_container_width=True, hide_index=True)

    # ================= PAGAMENTOS =================
with st.expander("➕ Adicionar pagamento", expanded=True):
    a1, a2, a3, a4, a5 = st.columns([3,1,1.3,2,1])

    desc = a1.text_input("Descrição")
    val = a2.number_input("Valor (R$)", min_value=0.0, step=10.0)
    venc = a3.date_input("Vencimento")
    cat_name = a4.selectbox("Categoria", cat_names)
    parcelas = a5.number_input("Parcelas", min_value=1, step=1, value=1)

    if st.button("Adicionar", type="primary"):
        cid = None if cat_name == "(Sem categoria)" else cat_map[cat_name]
        is_credit = 1 if parcelas > 1 else 0
        repos.add_payment(
            st.session_state.user_id,
            desc,
            val,
            str(venc),
            month,
            year,
            cid,
            is_credit=is_credit,
            installments=parcelas
        )
        st.success("Pagamento adicionado.")
        st.rerun()

    # ================= CATEGORIAS =================
    elif page == "🏷️ Categorias":
        st.subheader("🏷️ Categorias")
        new_cat = st.text_input("Nova categoria")
        if st.button("Adicionar"):
            repos.create_category(st.session_state.user_id, new_cat)
            st.rerun()
        for cid, name in repos.list_categories(st.session_state.user_id):
            a,b = st.columns([4,1])
            a.write(name)
            if b.button("Excluir", key=f"c_{cid}"):
                repos.delete_category(st.session_state.user_id, cid)
                st.rerun()

    # ================= PLANEJAMENTO =================
    elif page == "💰 Planejamento":
        st.subheader("💰 Planejamento")
        renda_v = st.number_input("Renda", value=float(renda))
        meta_v = st.number_input("Meta de gastos", value=float(budget["expense_goal"]))
        if st.button("Salvar"):
            repos.upsert_budget(st.session_state.user_id, mes, ano, renda_v, meta_v)
            st.success("Planejamento salvo")

    # ================= EXPORTAR =================
    elif page == "📤 Exportar":
        st.subheader("📤 Exportar")
        st.download_button(
            "📊 Excel",
            export_excel_bytes(df),
            file_name="pagamentos.xlsx"
        )

# -------------------- Router --------------------
if st.session_state.user_id is None:
    screen_auth()
else:
    screen_app()
