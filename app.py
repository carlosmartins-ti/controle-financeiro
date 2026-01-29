import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import date, datetime
import time
import streamlit.components.v1 as components

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
    try:
        return datetime.fromisoformat(str(s)).strftime("%d/%m/%Y")
    except:
        return ""

def is_admin():
    return st.session_state.username == ADMIN_USERNAME

def flash(msg, kind="success", seconds=15):
    box = st.empty()
    if kind == "success":
        box.success(msg)
    elif kind == "warning":
        box.warning(msg)
    else:
        box.error(msg)
    time.sleep(seconds)
    box.empty()

# ================= SESSION =================
for k in ["user_id", "username", "edit_id"]:
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
        q = st.selectbox("Pergunta de segurança", [
            "Qual o nome do seu primeiro pet?",
            "Qual o nome da sua mãe?",
            "Qual sua cidade de nascimento?",
            "Qual seu filme favorito?"
        ])
        a = st.text_input("Resposta")

        if st.button("Criar conta"):
            try:
                create_user(u, p, q, a)
                uid = authenticate(u, p)
                st.session_state.user_id = uid
                st.session_state.username = u.strip().lower()
                repos.seed_default_categories(uid)
                flash("Conta criada com sucesso!")
                st.rerun()
            except ValueError as e:
                st.error(str(e))

    with t3:
        u = st.text_input("Usuário")
        q = get_security_question(u) if u else None
        if q:
            st.info(q)
            a = st.text_input("Resposta")
            np = st.text_input("Nova senha", type="password")
            if st.button("Redefinir senha"):
                if reset_password(u, a, np):
                    flash("Senha alterada com sucesso!")
                else:
                    st.error("Resposta incorreta.")

# ================= APP =================
def screen_app():
    repos.seed_default_categories(st.session_state.user_id)

    with st.sidebar:
        st.markdown(f"**Usuário:** {st.session_state.username}")
        today = date.today()
        month_label = st.selectbox("Mês", MESES, index=today.month-1)
        year = st.selectbox("Ano", list(range(today.year-2, today.year+3)), index=2)
        month = MESES.index(month_label) + 1

        st.divider()
        page = st.radio("Menu", ["📊 Dashboard", "🧾 Despesas", "🏷️ Categorias", "💰 Planejamento"])

        if st.button("Sair"):
            st.session_state.user_id = None
            st.session_state.username = None
            st.rerun()

    rows = repos.list_payments(st.session_state.user_id, month, year)

    df = pd.DataFrame(rows, columns=[
        "id","Descrição","Valor","Vencimento","Pago","Data pagamento",
        "CategoriaID","Categoria","is_credit","installments","installment_index","credit_group"
    ])

    total = df["Valor"].sum() if not df.empty else 0
    pago = df[df["Pago"] == 1]["Valor"].sum() if not df.empty else 0
    aberto = total - pago

    budget = repos.get_budget(st.session_state.user_id, month, year)
    renda = float(budget["income"])
    saldo = renda - total

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
        cats = repos.list_categories(st.session_state.user_id)
        cat_map = {name: cid for cid, name in cats}
        cat_names = ["(Sem categoria)"] + list(cat_map.keys())

        with st.expander("➕ Adicionar despesa", expanded=True):
            a1,a2,a3,a4,a5 = st.columns([3,1,1.3,2,1])
            desc = a1.text_input("Descrição")
            val = a2.number_input("Valor (R$)", min_value=0.0)
            venc = a3.date_input("Vencimento", value=date.today(), format="DD/MM/YYYY")
            cat = a4.selectbox("Categoria", cat_names)
            parc = a5.number_input("Parcelas", min_value=1, value=1)

            if st.button("Adicionar"):
                if not desc.strip():
                    flash("Informe a descrição", "warning")
                elif val <= 0:
                    flash("Informe um valor maior que zero", "warning")
                else:
                    cid = None if cat == "(Sem categoria)" else cat_map[cat]
                    repos.add_payment(
                        st.session_state.user_id,
                        desc, val, str(venc),
                        month, year, cid,
                        is_credit=1 if parc > 1 else 0,
                        installments=parc
                    )
                    flash("Despesa adicionada com sucesso!")
                    st.rerun()

        # -------- FATURA CARTÃO --------
        credit_rows = [r for r in rows if r[7] and "cart" in r[7].lower()]
        if credit_rows:
            open_credit = [r for r in credit_rows if r[4] == 0]
            total_fatura = sum(float(r[2]) for r in open_credit)

            st.divider()
            st.subheader("💳 Fatura do cartão")
            st.metric("Total em aberto", fmt_brl(total_fatura))

            if open_credit:
                if st.button("💰 Pagar fatura"):
                    repos.mark_credit_invoice_paid(st.session_state.user_id, month, year)
                    flash("Fatura paga com sucesso!")
                    st.rerun()
            else:
                if st.button("🔄 Desfazer pagamento"):
                    repos.unmark_credit_invoice_paid(st.session_state.user_id, month, year)
                    flash("Pagamento da fatura desfeito")
                    st.rerun()

        st.divider()

        for r in rows:
            pid, desc, amount, due, paid, _, _, cat, *_ = r
            a,b,c,d,e,f = st.columns([4,1.2,1.8,1.2,1.2,1])

            a.write(f"**{desc}**" + (f"  \n🏷️ {cat}" if cat else ""))
            b.write(fmt_brl(amount))
            c.write(format_date_br(due))
            d.write("✅ Paga" if paid else "🕓 Em aberto")

            if not paid:
                if e.button("Marcar como paga", key=f"pay_{pid}"):
                    repos.mark_paid(st.session_state.user_id, pid, True)
                    flash("Despesa marcada como paga")
                    st.rerun()
            else:
                if e.button("Desfazer", key=f"unpay_{pid}"):
                    repos.mark_paid(st.session_state.user_id, pid, False)
                    flash("Pagamento desfeito")
                    st.rerun()

            if f.button("Excluir", key=f"del_{pid}"):
                repos.delete_payment(st.session_state.user_id, pid)
                flash("Despesa excluída")
                st.rerun()

    # ================= DASHBOARD =================
    elif page == "📊 Dashboard":
        if not df.empty:
            df2 = df.copy()
            df2["Categoria"] = df2["Categoria"].fillna("Sem categoria")
            fig = px.pie(df2, names="Categoria", values="Valor")
            st.plotly_chart(fig, use_container_width=True)

    # ================= CATEGORIAS =================
    elif page == "🏷️ Categorias":
        new_cat = st.text_input("Nova categoria")
        if st.button("Adicionar categoria"):
            if not new_cat.strip():
                flash("Informe o nome da categoria", "warning")
            else:
                try:
                    repos.create_category(st.session_state.user_id, new_cat)
                    flash("Categoria adicionada com sucesso!")
                    st.rerun()
                except:
                    flash("Categoria já cadastrada", "error")

        for cid, name in repos.list_categories(st.session_state.user_id):
            a,b = st.columns([4,1])
            a.write(name)
            if b.button("Excluir", key=f"cat_{cid}"):
                repos.delete_category(st.session_state.user_id, cid)
                flash("Categoria excluída")
                st.rerun()

    # ================= PLANEJAMENTO =================
    elif page == "💰 Planejamento":
        renda_v = st.number_input("Renda", value=float(renda))
        meta_v = st.number_input("Meta de gastos", value=float(budget["expense_goal"]))
        if st.button("Salvar planejamento"):
            repos.upsert_budget(st.session_state.user_id, month, year, renda_v, meta_v)
            flash("Planejamento salvo com sucesso")

# ================= ROUTER =================
if st.session_state.user_id is None:
    screen_auth()
else:
    screen_app()
