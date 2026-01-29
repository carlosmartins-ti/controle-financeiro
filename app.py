import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import date, datetime
import streamlit.components.v1 as components
import uuid

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
    return st.session_state.get("username") == ADMIN_USERNAME

def gerar_grupo_fatura():
    return str(uuid.uuid4())[:8]

# ================= SESSION =================
for k in ["user_id", "username", "edit_id", "msg"]:
    if k not in st.session_state:
        st.session_state[k] = None

# ================= AUTH =================
def screen_auth():
    st.title("💳 Controle Financeiro")

    components.html(
        '''
        <div style="
            background: linear-gradient(135deg, #1f2937, #111827);
            border-radius: 12px;
            padding: 16px;
            margin: 14px 0;
            color: #e5e7eb;
            box-shadow: 0 6px 18px rgba(0,0,0,0.45);
            font-family: system-ui;
        ">
            <div style="display:flex;align-items:center;gap:10px">
                <span style="font-size:22px">🔐</span>
                <strong>Autenticação e autoria do projeto</strong>
            </div>
            <div style="margin-top:10px;font-size:14px">
                Aplicação desenvolvida por <strong>Carlos Martins</strong>.<br>
                Para dúvidas, sugestões ou suporte técnico:
            </div>
            <div style="margin-top:8px">
                📧 <a href="mailto:cr954479@gmail.com" style="color:#60a5fa">cr954479@gmail.com</a>
            </div>
        </div>
        ''',
        height=170
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
                st.rerun()
            else:
                st.error("Usuário ou senha inválidos.")

    with t2:
        u = st.text_input("Novo usuário")
        p = st.text_input("Nova senha", type="password")
        q = st.selectbox(
            "Pergunta de segurança",
            [
                "Qual o nome do seu primeiro pet?",
                "Qual o nome da sua mãe?",
                "Qual sua cidade de nascimento?",
                "Qual seu filme favorito?"
            ]
        )
        a = st.text_input("Resposta")

        if st.button("Criar conta"):
            create_user(u, p, q, a)
            uid = authenticate(u, p)
            st.session_state.user_id = uid
            st.session_state.username = u.strip().lower()
            repos.seed_default_categories(uid)
            st.success("Conta criada com sucesso.")
            st.rerun()

    with t3:
        u = st.text_input("Usuário")
        q = get_security_question(u) if u else None

        if q:
            st.info(q)
            a = st.text_input("Resposta")
            np = st.text_input("Nova senha", type="password")

            if st.button("Redefinir senha"):
                if reset_password(u, a, np):
                    st.success("Senha alterada!")
                else:
                    st.error("Resposta incorreta.")

# ================= APP =================
def screen_app():
    with st.sidebar:
        st.markdown(f"**Usuário:** {st.session_state.username}")
        if is_admin():
            st.caption("🔑 Administrador")

        today = date.today()
        month_label = st.selectbox("Mês", MESES, index=today.month - 1)
        year = st.selectbox("Ano", list(range(today.year - 2, today.year + 3)), index=2)
        month = MESES.index(month_label) + 1

        page = st.radio("Menu", ["📊 Dashboard", "🧾 Despesas", "🏷️ Categorias", "💰 Planejamento"])

        if st.button("Sair"):
            st.session_state.user_id = None
            st.session_state.username = None
            st.rerun()

    repos.seed_default_categories(st.session_state.user_id)

    rows = repos.list_payments(st.session_state.user_id, month, year)
    df = pd.DataFrame(rows, columns=[
        "id", "Descrição", "Valor", "Vencimento", "Pago", "Data pagamento",
        "CategoriaID", "Categoria", "is_credit", "installments",
        "installment_index", "credit_group"
    ])

    total = df["Valor"].sum() if not df.empty else 0
    pago = df[df["Pago"] == 1]["Valor"].sum() if not df.empty else 0
    aberto = total - pago

    budget = repos.get_budget(st.session_state.user_id, month, year)
    renda = float(budget["income"])
    saldo = renda - total

    st.title("💳 Controle Financeiro")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total", fmt_brl(total))
    c2.metric("Pago", fmt_brl(pago))
    c3.metric("Em aberto", fmt_brl(aberto))
    c4.metric("Saldo", fmt_brl(saldo))

    # ================= DESPESAS =================
    if page == "🧾 Despesas":
        st.subheader("🧾 Despesas")

        cats = repos.list_categories(st.session_state.user_id)
        cat_map = {name: cid for cid, name in cats}
        cat_names = ["(Sem categoria)"] + list(cat_map.keys())

        with st.form("add_despesa", clear_on_submit=True):
            desc = st.text_input("Descrição")
            val = st.number_input("Valor", min_value=0.0)
            venc = st.date_input("Vencimento")
            cat_name = st.selectbox("Categoria", cat_names)
            parcelas = st.number_input("Parcelas", min_value=1, value=1)
            submitted = st.form_submit_button("Adicionar")

        if submitted:
            cid = None if cat_name == "(Sem categoria)" else cat_map[cat_name]
            credit_group = None
            if cid and "cartão" in cat_name.lower() and parcelas > 1:
                credit_group = gerar_grupo_fatura()

            repos.add_payment(
                st.session_state.user_id,
                desc,
                val,
                str(venc),
                month,
                year,
                cid,
                is_credit=1 if parcelas > 1 else 0,
                installments=parcelas,
                credit_group=credit_group
            )
            st.success("Despesa adicionada com sucesso.")

        for r in rows:
            pid, desc, amount, due, paid, _, _, cat_name, is_credit, _, _, credit_group = r
            a, b, c, d, e, f = st.columns([4,1,1,1,1,2])
            a.write(desc)
            b.write(fmt_brl(amount))
            c.write(format_date_br(due))
            d.write("Paga" if paid else "Aberta")

            if not paid and e.button("Marcar paga", key=f"pay_{pid}"):
                repos.mark_paid(st.session_state.user_id, pid, True)
                st.rerun()
            if paid and e.button("Desfazer", key=f"unpay_{pid}"):
                repos.mark_paid(st.session_state.user_id, pid, False)
                st.rerun()

            if f.button("Editar", key=f"edit_{pid}"):
                st.session_state.edit_id = pid

            if is_credit and credit_group:
                if f.button("Unir fatura", key=f"merge_{pid}"):
                    repos.merge_credit_group(st.session_state.user_id, credit_group)
                    st.success("Fatura unificada.")
                if f.button("Desfazer fatura", key=f"unmerge_{pid}"):
                    repos.unmerge_credit_group(st.session_state.user_id, credit_group)
                    st.success("Fatura desfeita.")

    elif page == "📊 Dashboard":
        st.subheader("📊 Dashboard")
        if not df.empty:
            fig = px.pie(df, names="Categoria", values="Valor")
            st.plotly_chart(fig)

    elif page == "🏷️ Categorias":
        st.subheader("🏷️ Categorias")
        with st.form("add_cat", clear_on_submit=True):
            new_cat = st.text_input("Nova categoria")
            if st.form_submit_button("Adicionar") and new_cat:
                repos.create_category(st.session_state.user_id, new_cat)
                st.success("Categoria adicionada.")

        for cid, name in repos.list_categories(st.session_state.user_id):
            st.write(name)

    elif page == "💰 Planejamento":
        st.subheader("💰 Planejamento")
        renda_v = st.number_input("Renda", value=renda)
        meta_v = st.number_input("Meta", value=float(budget["expense_goal"]))
        if st.button("Salvar"):
            repos.upsert_budget(st.session_state.user_id, month, year, renda_v, meta_v)
            st.success("Planejamento salvo.")

# ================= ROUTER =================
if st.session_state.user_id is None:
    screen_auth()
else:
    screen_app()
