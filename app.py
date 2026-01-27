import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import date, datetime

from database import init_db
from auth import authenticate, create_user, get_security_question, reset_password
import repos
from export_utils import export_excel_bytes, export_pdf_bytes

# ================= CONFIG =================
st.set_page_config(page_title="Controle Financeiro", page_icon="💳", layout="wide")
init_db()

CATEGORIA_CARTAO = "Cartão de crédito"

MESES = [
    "Janeiro","Fevereiro","Março","Abril","Maio","Junho",
    "Julho","Agosto","Agosto","Setembro","Outubro","Novembro","Dezembro"
]

# ================= CSS =================
def inject_css():
    try:
        with open("style.css", "r", encoding="utf-8") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
    except:
        pass

inject_css()

# ================= UI CONTROL =================
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

# ================= SESSION =================
if "user_id" not in st.session_state:
    st.session_state.user_id = None
if "username" not in st.session_state:
    st.session_state.username = None
if "edit_id" not in st.session_state:
    st.session_state.edit_id = None

# ================= HELPERS =================
def fmt(v):
    return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def parse_date(d):
    try:
        return datetime.fromisoformat(str(d)).date()
    except:
        return datetime.strptime(str(d), "%Y-%m-%d").date()

# ================= AUTH =================
def screen_auth():
    st.title("💳 Controle Financeiro")

    tab1, tab2, tab3 = st.tabs(["Entrar", "Criar conta", "Recuperar senha"])

    with tab1:
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

    with tab2:
        u = st.text_input("Novo usuário")
        p = st.text_input("Nova senha", type="password")
        q = st.selectbox(
            "Pergunta de segurança",
            ["Nome do primeiro pet?","Nome da mãe?","Cidade onde nasceu?","Filme favorito?"]
        )
        a = st.text_input("Resposta")
        if st.button("Criar conta", type="primary", use_container_width=True):
            try:
                create_user(u, p, q, a)
                st.success("Conta criada! Faça login.")
            except Exception as e:
                st.error(str(e))

    with tab3:
        u = st.text_input("Usuário")
        q = get_security_question(u) if u else None
        if q:
            st.info(q)
            a = st.text_input("Resposta")
            np = st.text_input("Nova senha", type="password")
            if st.button("Redefinir senha", use_container_width=True):
                if reset_password(u, a, np):
                    st.success("Senha alterada!")
                else:
                    st.error("Resposta incorreta")

# ================= APP =================
def screen_app():
    today = date.today()

    with st.sidebar:
        st.markdown(f"👤 **{st.session_state.username}**")
        mes_nome = st.selectbox("Mês", MESES, index=today.month-1)
        ano = st.selectbox("Ano", list(range(today.year-2, today.year+3)), index=2)
        mes = MESES.index(mes_nome) + 1

        page = st.radio(
            "Menu",
            ["🧾 Pagamentos", "🏷️ Categorias", "💰 Planejamento", "📊 Dashboard", "📤 Exportar"]
        )

        if st.button("Sair"):
            st.session_state.user_id = None
            st.session_state.username = None
            st.session_state.edit_id = None
            st.rerun()

    rows = repos.list_payments(st.session_state.user_id, mes, ano)

    df_raw = pd.DataFrame(
        rows,
        columns=["id","Descrição","Valor","Vencimento","Pago","Categoria"]
    )

    # ---------- CONSOLIDA CARTÃO ----------
    df_cartao = df_raw[df_raw["Categoria"] == CATEGORIA_CARTAO]
    df_outros = df_raw[df_raw["Categoria"] != CATEGORIA_CARTAO]

    if not df_cartao.empty:
        fatura = {
            "id": -1,
            "Descrição": f"💳 Fatura Cartão ({mes_nome}/{ano})",
            "Valor": df_cartao["Valor"].sum(),
            "Vencimento": df_cartao["Vencimento"].max(),
            "Pago": 1 if df_cartao["Pago"].all() else 0,
            "Categoria": CATEGORIA_CARTAO
        }
        df = pd.concat([df_outros, pd.DataFrame([fatura])], ignore_index=True)
    else:
        df = df_raw.copy()

    st.title(f"{mes_nome}/{ano}")

    total = df_raw["Valor"].sum() if not df_raw.empty else 0
    pago = df_raw[df_raw["Pago"] == 1]["Valor"].sum() if not df_raw.empty else 0

    c1, c2, c3 = st.columns(3)
    c1.metric("Total", fmt(total))
    c2.metric("Pago", fmt(pago))
    c3.metric("Em aberto", fmt(total - pago))

    st.divider()

    # ================= PAGAMENTOS =================
    if page == "🧾 Pagamentos":
        st.subheader("🧾 Pagamentos")

        cats = repos.list_categories(st.session_state.user_id)
        cat_map = {name: cid for cid, name in cats}
        cat_names = list(cat_map.keys())

        with st.expander("➕ Novo pagamento", expanded=True):
            d = st.text_input("Descrição")
            v = st.number_input("Valor", min_value=0.0)
            c = st.selectbox("Categoria", cat_names)
            parcelado = st.checkbox("Parcelado?")
            parcelas = st.number_input("Qtd parcelas", min_value=1, value=1)
            ven = st.date_input("Vencimento")

            if st.button("Salvar", type="primary"):
                if parcelado and parcelas > 1:
                    repos.add_installments(
                        st.session_state.user_id,
                        d,
                        v,
                        parcelas,
                        mes,
                        ano,
                        cat_map[c]
                    )
                else:
                    repos.add_payment(
                        st.session_state.user_id,
                        d,
                        v,
                        str(ven),
                        mes,
                        ano,
                        cat_map[c]
                    )
                st.rerun()

        for _, row in df.iterrows():
            a,b,c,d,e = st.columns([4,1.5,1.5,1.5,1.5])
            a.write(f"**{row['Descrição']}**")
            b.write(fmt(row["Valor"]))
            c.write("✅ Pago" if row["Pago"] else "🕓 Aberto")

            if row["id"] == -1:
                if not row["Pago"]:
                    if d.button("Pagar fatura", key="pay_fatura"):
                        repos.mark_fatura_cartao(
                            st.session_state.user_id,
                            mes,
                            ano,
                            CATEGORIA_CARTAO
                        )
                        st.rerun()
            else:
                if not row["Pago"]:
                    if d.button("Pagar", key=f"pay_{row['id']}"):
                        repos.mark_paid(st.session_state.user_id, row["id"], True)
                        st.rerun()

                if e.button("Excluir", key=f"del_{row['id']}"):
                    repos.delete_payment(st.session_state.user_id, row["id"])
                    st.rerun()

    # ================= CATEGORIAS =================
    elif page == "🏷️ Categorias":
        st.subheader("🏷️ Categorias")
        new_cat = st.text_input("Nova categoria")
        if st.button("Adicionar"):
            repos.create_category(st.session_state.user_id, new_cat)
            st.rerun()

        cats = repos.list_categories(st.session_state.user_id)
        for cid, name in cats:
            a,b = st.columns([4,1])
            a.write(name)
            if b.button("Excluir", key=f"cat_{cid}"):
                repos.delete_category(st.session_state.user_id, cid)
                st.rerun()

    # ================= PLANEJAMENTO =================
    elif page == "💰 Planejamento":
        budget = repos.get_budget(st.session_state.user_id, mes, ano)
        renda = st.number_input("Renda do mês", value=float(budget["income"]))
        meta = st.number_input("Meta de gastos", value=float(budget["expense_goal"]))

        if st.button("Salvar planejamento", type="primary"):
            repos.upsert_budget(st.session_state.user_id, mes, ano, renda, meta)
            st.success("Planejamento salvo")

        gasto = total
        sobra = renda - gasto

        st.metric("Gasto do mês", fmt(gasto))
        st.metric("Sobra", fmt(sobra))

    # ================= DASHBOARD =================
    elif page == "📊 Dashboard" and not df_raw.empty:
        fig = px.pie(df_raw, names="Categoria", values="Valor", title="Gastos por categoria")
        st.plotly_chart(fig, use_container_width=True)

    # ================= EXPORT =================
    elif page == "📤 Exportar":
        df_exp = df_raw.copy()
        df_exp["Pago"] = df_exp["Pago"].map({0:"Não",1:"Sim"})
        st.dataframe(df_exp, use_container_width=True)

        st.download_button(
            "📊 Exportar Excel",
            export_excel_bytes(df_exp),
            file_name="pagamentos.xlsx"
        )

# ================= ROUTER =================
if st.session_state.user_id is None:
    screen_auth()
else:
    screen_app()
