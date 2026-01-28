import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import date, datetime

from database import init_db
from auth import authenticate, create_user, get_security_question, reset_password
import repos

# ================= SETUP =================
st.set_page_config(
    page_title="Controle Financeiro",
    page_icon="💳",
    layout="wide"
)

# 🔥 CSS (OBRIGATÓRIO PARA MOBILE)
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

def status_vencimento(due_date, paid):
    if paid:
        return "", ""
    try:
        d = datetime.fromisoformat(str(due_date)).date()
    except:
        return "", ""
    today = date.today()
    if d < today:
        return "🔴 VENCIDA", "#ff4d4d"
    if d == today:
        return "🟡 VENCE HOJE", "#ffcc00"
    return "", ""

def is_admin():
    return st.session_state.username == ADMIN_USERNAME

# ================= SESSION =================
for k in ["user_id", "username"]:
    if k not in st.session_state:
        st.session_state[k] = None

# ================= AUTH =================
def screen_auth():
    st.title("💳 Controle Financeiro")

    st.markdown(
    """
    <div class="auth-box">
        🔐 <b>Autenticação e autoria do projeto</b><br>
        Aplicação desenvolvida por <b>Carlos Martins</b>.<br>
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


# ================= APP =================
def screen_app():
    if not st.session_state.user_id:
        st.error("Usuário não autenticado.")
        return

    repos.seed_default_categories(st.session_state.user_id)

    with st.sidebar:
        st.markdown(f"**Usuário:** `{st.session_state.username}`")
        if is_admin():
            st.caption("🔑 Administrador")


        today = date.today()
        month_label = st.selectbox("Mês", MESES, index=today.month-1, key="sel_month")
        year = st.selectbox("Ano", list(range(today.year-2, today.year+3)), index=2, key="sel_year")
        month = MESES.index(month_label) + 1

        st.divider()
        page = st.radio(
            "Menu",
            ["📊 Dashboard", "🧾 Despesas", "🏷️ Categorias", "💰 Planejamento"],
            key="menu"
        )

        if st.button("Sair", key="btn_logout", use_container_width=True):
            st.session_state.user_id = None
            st.session_state.username = None
            st.rerun()

    if st.session_state.user_id is not None:
     repos.seed_default_categories(st.session_state.user_id)

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

    budget = repos.get_budget(st.session_state.user_id, month, year)
    renda = float(budget["income"])
    saldo = renda - total

    st.title("💳 Controle Financeiro")
    st.caption(f"Período: **{month_label}/{year}**")

    c1,c2,c3,c4 = st.columns(4)
    c1.metric("Total do mês", fmt_brl(total))
    c2.metric("Pago", fmt_brl(pago))
    c3.metric("Em aberto", fmt_brl(aberto))
    c4.metric("Saldo", fmt_brl(saldo))

    st.divider()

    # ================= DESPESAS =================
if page == "🧾 Despesas":
    st.subheader("🧾 Despesas")

    # Categorias
    cats = repos.list_categories(st.session_state.user_id)
    cat_map = {name: cid for cid, name in cats}
    cat_names = ["(Sem categoria)"] + list(cat_map.keys())

    # ---------- FORMULÁRIO ----------
    with st.expander("➕ Adicionar despesa", expanded=True):
        with st.form("form_add_despesa", clear_on_submit=True):

            a1, a2, a3, a4, a5 = st.columns([3, 1, 1.3, 2, 1])

            desc = a1.text_input("Descrição")
            val = a2.number_input("Valor (R$)", min_value=0.0, step=10.0)

            venc = a3.date_input(
                "Vencimento",
                value=date.today(),
                format="DD/MM/YYYY"
            )

            cat_name = a4.selectbox("Categoria", cat_names)
            parcelas = a5.number_input("Parcelas", min_value=1, step=1, value=1)

            submitted = st.form_submit_button("Adicionar")

        # ---------- PROCESSAMENTO ----------
        if submitted:
            if not desc or val <= 0:
                st.error("Preencha a descrição e um valor válido.")
            else:
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

                st.success("Despesa adicionada com sucesso!")
                st.rerun()


        # -------- FATURA DO CARTÃO --------
        credit_rows = [r for r in rows if r[7] and "cart" in r[7].lower()]
        if credit_rows:
            open_credit = [r for r in credit_rows if r[4] == 0]
            total_fatura = sum(float(r[2]) for r in open_credit)

            st.divider()
            st.subheader("💳 Fatura do cartão")
            c1,c2 = st.columns([3,1])
            c1.metric("Total em aberto", fmt_brl(total_fatura))

            if open_credit:
                if c2.button("💰 Pagar fatura do cartão", key="pay_card"):
                    repos.mark_credit_invoice_paid(st.session_state.user_id, month, year)
                    st.rerun()
            else:
                if c2.button("🔄 Desfazer pagamento da fatura", key="unpay_card"):
                    repos.unmark_credit_invoice_paid(st.session_state.user_id, month, year)
                    st.rerun()

        st.divider()

        for r in rows:
            pid, desc, amount, due, paid, _, _, cat_name, *_ = r
            a,b,c,d,e,f = st.columns([4,1.2,1.8,1.2,1.2,1])

            a.write(f"**{desc}**" + (f"  \n🏷️ {cat_name}" if cat_name else ""))
            b.write(fmt_brl(amount))

            status, color = status_vencimento(due, paid)
            if status:
                c.markdown(
                    f"<span style='color:{color}; font-weight:600'>{format_date_br(due)} — {status}</span>",
                    unsafe_allow_html=True
                )
            else:
                c.write(format_date_br(due))

            d.write("✅ Paga" if paid else "🕓 Em aberto")

            if not paid:
                if e.button("Marcar como paga", key=f"pay_{pid}"):
                    repos.mark_paid(st.session_state.user_id, pid, True)
                    st.rerun()
            else:
                if e.button("Desfazer", key=f"unpay_{pid}"):
                    repos.mark_paid(st.session_state.user_id, pid, False)
                    st.rerun()

            if f.button("Excluir", key=f"del_{pid}"):
                repos.delete_payment(st.session_state.user_id, pid)
                st.rerun()

    # ================= DASHBOARD =================
    elif page == "📊 Dashboard":
        st.subheader("📊 Dashboard")
        if not df.empty:
            df2 = df.copy()
            df2["Categoria"] = df2["Categoria"].fillna("Sem categoria")
            fig = px.pie(df2, names="Categoria", values="Valor")
            st.plotly_chart(fig, use_container_width=True)

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
        renda_v = st.number_input("Renda", value=float(renda), key="renda")
        meta_v = st.number_input("Meta de gastos", value=float(budget["expense_goal"]), key="meta")
        if st.button("Salvar", key="btn_save_plan"):
            repos.upsert_budget(st.session_state.user_id, month, year, renda_v, meta_v)
            st.success("Planejamento salvo.")

# ================= ROUTER =================
if st.session_state.user_id is None:
    screen_auth()
else:
    screen_app()
