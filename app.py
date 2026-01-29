import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import date, datetime
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
    if not s:
        return ""
    try:
        return datetime.fromisoformat(str(s)).strftime("%d/%m/%Y")
    except:
        return str(s)

def is_admin():
    return st.session_state.username == ADMIN_USERNAME

# ================= SESSION =================
if "user_id" not in st.session_state:
    st.session_state.user_id = None
if "username" not in st.session_state:
    st.session_state.username = None
if "edit_id" not in st.session_state:
    st.session_state.edit_id = None

# ================= AUTH (ORIGINAL) =================
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

        if st.button("Entrar", key="btn_login"):
            uid = authenticate(u, p)
            if uid:
                st.session_state.user_id = uid
                st.session_state.username = u.strip().lower()
                st.rerun()
            else:
                st.error("Usuário ou senha inválidos.")

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
        a = st.text_input("Resposta", key="signup_answer")

        if st.button("Criar conta", key="btn_signup"):
            create_user(u, p, q, a)
            uid = authenticate(u, p)
            st.session_state.user_id = uid
            st.session_state.username = u.strip().lower()
            repos.seed_default_categories(uid)
            st.success("Conta criada com sucesso.")
            st.rerun()

    with t3:
        u = st.text_input("Usuário", key="reset_user")
        q = get_security_question(u) if u else None

        if q:
            st.info(q)
            a = st.text_input("Resposta", key="reset_answer")
            np = st.text_input("Nova senha", type="password", key="reset_pass")

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

    with st.sidebar:
        st.markdown(f"**Usuário:** {st.session_state.username}")
        today = date.today()
        month_label = st.selectbox("Mês", MESES, index=today.month - 1)
        year = st.selectbox("Ano", list(range(today.year - 2, today.year + 3)), index=2)
        month = MESES.index(month_label) + 1

        st.divider()
        page = st.radio(
            "Menu",
            ["📊 Dashboard", "🧾 Despesas", "🏷️ Categorias", "💰 Planejamento"]
        )

        if st.button("Sair", use_container_width=True):
            st.session_state.user_id = None
            st.session_state.username = None
            st.rerun()

    if "msg_ok" in st.session_state:
        st.toast(st.session_state.msg_ok, icon="✅", duration=15)
        del st.session_state.msg_ok

    repos.seed_default_categories(st.session_state.user_id)

    rows = repos.list_payments(st.session_state.user_id, month, year)
    df = pd.DataFrame(
        rows,
        columns=[
            "id","Descrição","Valor","Vencimento","Pago","Data pagamento",
            "CategoriaID","Categoria","is_credit","installments",
            "installment_index","credit_group"
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

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total do mês", fmt_brl(total))
    c2.metric("Pago", fmt_brl(pago))
    c3.metric("Em aberto", fmt_brl(aberto))
    c4.metric("Saldo", fmt_brl(saldo))

    st.divider()

    # ================= DESPESAS (RESTAURADA) =================
    if page == "🧾 Despesas":
        st.subheader("🧾 Despesas")

        cats = repos.list_categories(st.session_state.user_id)
        cat_map = {name: cid for cid, name in cats}
        cat_names = ["(Sem categoria)"] + list(cat_map.keys())

        with st.expander("➕ Adicionar despesa", expanded=True):
            with st.form("form_add_despesa", clear_on_submit=True):
                a1, a2, a3, a4, a5 = st.columns([3, 1, 1.3, 2, 1])

                desc = a1.text_input("Descrição")
                val = a2.number_input("Valor (R$)", min_value=0.0, step=10.0)
                venc = a3.date_input("Vencimento", value=date.today())
                cat_name = a4.selectbox("Categoria", cat_names)
                parcelas = a5.number_input("Parcelas", min_value=1, step=1, value=1)

                submitted = st.form_submit_button("Adicionar")

        if submitted:
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
            st.session_state.msg_ok = "Despesa cadastrada com sucesso!"
            st.rerun()

        st.divider()

        if df.empty:
            st.info("Nenhuma despesa cadastrada.")
        else:
            for r in rows:
                pid, desc, amount, due, paid, *_ = r

                a, b, c, d, e, f = st.columns([4,1.2,1.8,1.2,1.2,1])

                a.write(f"**{desc}**")
                b.write(fmt_brl(amount))
                c.write(format_date_br(due))
                d.write("✅ Paga" if paid else "🕓 Em aberto")

                if not paid:
                    if e.button("Marcar como paga", key=f"pay_{pid}"):
                        repos.mark_paid(st.session_state.user_id, pid, True)
                        st.session_state.msg_ok = "Despesa marcada como paga."
                        st.rerun()
                else:
                    if e.button("Desfazer", key=f"unpay_{pid}"):
                        repos.mark_paid(st.session_state.user_id, pid, False)
                        st.session_state.msg_ok = "Pagamento desfeito."
                        st.rerun()

                if f.button("✏️ Editar", key=f"edit_{pid}"):
                    st.session_state.edit_id = pid
                    st.rerun()

                if st.session_state.edit_id == pid:
                    with st.form(f"edit_form_{pid}", clear_on_submit=False):
                        n_desc = st.text_input("Descrição", value=desc)
                        n_val = st.number_input("Valor", value=float(amount), step=10.0)
                        n_venc = st.date_input("Vencimento", value=datetime.fromisoformat(due).date())

                        salvar = st.form_submit_button("Salvar")

                    if salvar:
                        repos.update_payment(
                            st.session_state.user_id,
                            pid,
                            n_desc,
                            n_val,
                            str(n_venc),
                            None
                        )
                        st.session_state.edit_id = None
                        st.session_state.msg_ok = "Despesa atualizada com sucesso!"
                        st.rerun()

    elif page == "🏷️ Categorias":
        st.subheader("🏷️ Categorias")

        with st.form("form_categoria", clear_on_submit=True):
            new_cat = st.text_input("Nova categoria")
            submitted_cat = st.form_submit_button("Adicionar")

        if submitted_cat:
            repos.create_category(st.session_state.user_id, new_cat)
            st.session_state.msg_ok = "Categoria cadastrada com sucesso!"
         
