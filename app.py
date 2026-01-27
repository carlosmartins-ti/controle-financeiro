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

# -------------------- Utils --------------------
MESES = [
    "Janeiro","Fevereiro","Março","Abril","Maio","Junho",
    "Julho","Agosto","Setembro","Outubro","Novembro","Dezembro"
]

def fmt_brl(v):
    return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def parse_date_str(s):
    try:
        return datetime.fromisoformat(str(s)).date()
    except:
        return datetime.strptime(str(s), "%Y-%m-%d").date()

# -------------------- Session --------------------
for k in ["user_id", "username"]:
    if k not in st.session_state:
        st.session_state[k] = None

# -------------------- AUTH --------------------
def screen_auth():
    st.title("💳 Controle Financeiro")
    st.caption("Cada usuário acessa apenas seus próprios dados.")

    tab_login, tab_signup, tab_reset = st.tabs(
        ["Entrar", "Criar conta", "Recuperar senha"]
    )

    with tab_login:
        u = st.text_input("Usuário", key="login_user")
        p = st.text_input("Senha", type="password", key="login_pass")

        if st.button("Entrar", key="btn_login", use_container_width=True):
            uid = authenticate(u, p)
            if uid:
                st.session_state.user_id = uid
                st.session_state.username = u
                st.rerun()
            else:
                st.error("Usuário ou senha inválidos.")

    with tab_signup:
        u = st.text_input("Novo usuário", key="signup_user")
        p = st.text_input("Nova senha", type="password", key="signup_pass")

        q = st.selectbox(
            "Pergunta de segurança",
            [
                "Qual o nome do seu primeiro pet?",
                "Qual o nome da sua mãe?",
                "Qual sua cidade de nascimento?",
                "Qual seu filme favorito?",
            ],
            key="signup_question"
        )

        a = st.text_input("Resposta de segurança", key="signup_answer")

        if st.button("Criar conta", type="primary", key="btn_signup", use_container_width=True):
            try:
                create_user(u, p, q, a)
                st.success("Conta criada! Faça login.")
            except Exception as e:
                st.error(str(e))

    with tab_reset:
        u = st.text_input("Usuário", key="reset_user")
        q = get_security_question(u) if u else None

        if q:
            st.info(q)
            a = st.text_input("Resposta", key="reset_answer")
            np = st.text_input("Nova senha", type="password", key="reset_newpass")

            if st.button("Redefinir senha", key="btn_reset", use_container_width=True):
                if reset_password(u, a, np):
                    st.success("Senha alterada!")
                else:
                    st.error("Resposta incorreta.")
        else:
            st.caption("Digite um usuário existente.")

# -------------------- APP --------------------
def screen_app():
    with st.sidebar:
        st.markdown(f"**Usuário:** `{st.session_state.username}`")

        today = date.today()
        month_label = st.selectbox("Mês", MESES, index=today.month-1)
        year = st.selectbox("Ano", list(range(today.year-2, today.year+3)), index=2)
        month = MESES.index(month_label) + 1

        st.divider()
        page = st.radio(
            "Menu",
            ["📊 Dashboard", "🧾 Despesas", "🏷️ Categorias", "💰 Planejamento", "📤 Exportar"],
            key="menu"
        )
        st.divider()

        if st.button("Sair", use_container_width=True):
            st.session_state.user_id = None
            st.session_state.username = None
            st.rerun()

    # -------- Load data --------
    rows = repos.list_payments(st.session_state.user_id, month, year)
    df = pd.DataFrame(
        rows,
        columns=[
            "id","Descrição","Valor","Vencimento","Pago","Data pagamento",
            "CategoriaID","Categoria","is_credit","installments","installment_index","credit_group"
        ]
    )

    total = df["Valor"].sum() if not df.empty else 0
    pago = df[df["Pago"] == 1]["Valor"].sum() if not df.empty else 0
    aberto = total - pago

    atraso = 0.0
    if not df.empty:
        atraso = df[
            (df["Pago"] == 0) &
            (df["Vencimento"].apply(parse_date_str) < date.today())
        ]["Valor"].sum()

    budget = repos.get_budget(st.session_state.user_id, month, year)
    renda = float(budget["income"])
    saldo = renda - total

    st.title("💳 Controle Financeiro")
    st.caption(f"Período: **{month_label}/{year}**")

    c1,c2,c3,c4,c5 = st.columns(5)
    c1.metric("Total do mês", fmt_brl(total))
    c2.metric("Pago", fmt_brl(pago))
    c3.metric("Em aberto", fmt_brl(aberto))
    c4.metric("Em atraso", fmt_brl(atraso))
    c5.metric("Saldo", fmt_brl(saldo))

    st.divider()

    # ================= DESPESAS =================
    if page == "🧾 Despesas":
        st.subheader("🧾 Despesas")

        cats = repos.list_categories(st.session_state.user_id)
        cat_map = {name: cid for cid, name in cats}
        cat_names = ["(Sem categoria)"] + list(cat_map.keys())

        # ---- Add expense ----
        with st.expander("➕ Adicionar despesa", expanded=True):
            a1,a2,a3,a4,a5 = st.columns([3,1,1.3,2,1])

            desc = a1.text_input("Descrição", key="add_desc")
            val = a2.number_input("Valor (R$)", min_value=0.0, step=10.0, key="add_val")
            venc = a3.date_input("Vencimento", key="add_due")
            cat_name = a4.selectbox("Categoria", cat_names, key="add_cat")
            parcelas = a5.number_input("Parcelas", min_value=1, step=1, value=1, key="add_parc")

            if st.button("Adicionar", type="primary", key="btn_add"):
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
                st.success("Despesa adicionada.")
                st.rerun()

        # ---- Credit invoice ----
        credit_rows = [
            r for r in rows
            if r[7] and "cart" in r[7].lower() and r[4] == 0
        ]

        if credit_rows:
            total_fatura = sum(float(r[2]) for r in credit_rows)
            st.divider()
            st.subheader("💳 Fatura do cartão")

            c1,c2 = st.columns([3,1])
            c1.metric("Total em aberto", fmt_brl(total_fatura))

            if c2.button("💰 Pagar fatura do cartão", type="primary"):
                repos.mark_credit_invoice_paid(
                    st.session_state.user_id,
                    month,
                    year
                )
                st.success("Fatura paga com sucesso.")
                st.rerun()

        st.divider()

        if not rows:
            st.info("Sem despesas neste período.")
        else:
            for r in rows:
                pid, desc, amount, due, paid, paid_date, cat_id, cat_name, *_ = r

                colA,colB,colC,colD,colE,colF = st.columns([4,1.2,1.5,1.2,1.2,1])

                colA.write(f"**{desc}**" + (f"  \n🏷️ {cat_name}" if cat_name else ""))
                colB.write(fmt_brl(float(amount)))
                colC.write(str(due))
                colD.write("✅ Paga" if paid else "🕓 Em aberto")

                if not paid:
                    if colE.button("Marcar como paga", key=f"pay_{pid}"):
                        repos.mark_paid(st.session_state.user_id, pid, True)
                        st.rerun()
                else:
                    if colE.button("Desfazer", key=f"unpay_{pid}"):
                        repos.mark_paid(st.session_state.user_id, pid, False)
                        st.rerun()

                if colF.button("Excluir", key=f"del_{pid}"):
                    repos.delete_payment(st.session_state.user_id, pid)
                    st.rerun()

    # ================= DASHBOARD =================
    elif page == "📊 Dashboard":
        st.subheader("📊 Dashboard")

        if df.empty:
            st.info("Sem dados para este período.")
        else:
            df2 = df.copy()
            df2["Categoria"] = df2["Categoria"].fillna("Sem categoria")
            df2["Status"] = df2["Pago"].map({0:"Em aberto",1:"Pago"})

            left,right = st.columns([2,1])
            with left:
                fig1 = px.pie(df2, names="Categoria", values="Valor")
                st.plotly_chart(fig1, use_container_width=True)
            with right:
                fig2 = px.bar(
                    df2.groupby("Status", as_index=False)["Valor"].sum(),
                    x="Status", y="Valor"
                )
                st.plotly_chart(fig2, use_container_width=True)

    # ================= CATEGORIAS =================
    elif page == "🏷️ Categorias":
        st.subheader("🏷️ Categorias")

        new_cat = st.text_input("Nova categoria", key="new_cat")
        if st.button("Adicionar", key="btn_add_cat"):
            repos.create_category(st.session_state.user_id, new_cat)
            st.rerun()

        for cid, name in repos.list_categories(st.session_state.user_id):
            a,b = st.columns([4,1])
            a.write(name)
            if b.button("Excluir", key=f"cat_{cid}"):
                repos.delete_category(st.session_state.user_id, cid)
                st.rerun()

    # ================= PLANEJAMENTO =================
    elif page == "💰 Planejamento":
        st.subheader("💰 Planejamento")

        renda_v = st.number_input("Renda do mês", value=float(renda))
        meta_v = st.number_input("Meta de gastos", value=float(budget["expense_goal"]))

        if st.button("Salvar", key="btn_plan"):
            repos.upsert_budget(st.session_state.user_id, month, year, renda_v, meta_v)
            st.success("Planejamento salvo.")

    # ================= EXPORTAR =================
    elif page == "📤 Exportar":
        df_exp = repos.payments_dataframe(st.session_state.user_id, month, year)
        st.dataframe(df_exp, use_container_width=True, hide_index=True)

        st.download_button(
            "📊 Baixar Excel",
            export_excel_bytes(df_exp),
            file_name="despesas.xlsx"
        )

# -------------------- ROUTER --------------------
if st.session_state.user_id is None:
    screen_auth()
else:
    screen_app()
