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

if "user_id" not in st.session_state:
    st.session_state.user_id = None
if "username" not in st.session_state:
    st.session_state.username = None
if "edit_id" not in st.session_state:
    st.session_state.edit_id = None


MESES = ["Janeiro","Fevereiro","Março","Abril","Maio","Junho","Julho","Agosto","Setembro","Outubro","Novembro","Dezembro"]

def fmt_brl(v: float) -> str:
    return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def parse_date_str(s: str):
    # s costuma vir "YYYY-MM-DD"
    try:
        return datetime.fromisoformat(str(s)).date()
    except:
        return datetime.strptime(str(s), "%Y-%m-%d").date()


# -------------------- Auth --------------------
def screen_auth():
    st.title("💳 Controle Financeiro")
    st.caption("Acesso por PC e celular. Cada usuário vê apenas seus próprios dados.")

    tab_login, tab_signup, tab_reset = st.tabs(["Entrar", "Criar conta", "Recuperar senha"])

    with tab_login:
        u = st.text_input("Usuário", key="login_user")
        p = st.text_input("Senha", type="password", key="login_pass")
        if st.button("Entrar", use_container_width=True):
            uid = authenticate(u, p)
            if uid:
                st.session_state.user_id = uid
                st.session_state.username = u.strip()
                st.rerun()
            else:
                st.error("Usuário ou senha inválidos.")

    with tab_signup:
        u = st.text_input("Novo usuário", key="su_user")
        p = st.text_input("Nova senha", type="password", key="su_pass")
        q = st.selectbox("Pergunta de segurança", [
            "Qual o nome do seu primeiro pet?",
            "Qual o nome da sua mãe?",
            "Qual sua cidade de nascimento?",
            "Qual seu filme favorito?",
        ], key="su_q")
        a = st.text_input("Resposta de segurança", key="su_a")
        if st.button("Criar conta", type="primary", use_container_width=True):
            try:
                create_user(u, p, q, a)
                st.success("Conta criada! Agora faça login na aba 'Entrar'.")
            except Exception as e:
                st.error(f"Não foi possível criar: {e}")

    with tab_reset:
        u = st.text_input("Usuário", key="rp_user")
        q = get_security_question(u) if u else None
        if q:
            st.info(f"Pergunta: {q}")
            a = st.text_input("Resposta", key="rp_answer")
            np = st.text_input("Nova senha", type="password", key="rp_newpass")
            if st.button("Redefinir senha", use_container_width=True):
                try:
                    ok = reset_password(u, a, np)
                    if ok:
                        st.success("Senha alterada! Volte na aba 'Entrar'.")
                    else:
                        st.error("Resposta inválida ou usuário não encontrado.")
                except Exception as e:
                    st.error(str(e))
        else:
            st.caption("Digite um usuário existente para mostrar a pergunta.")


# -------------------- Main app --------------------
def screen_app():
    # Sidebar
    with st.sidebar:
        st.markdown(f"**Usuário:** `{st.session_state.username}`")

        today = date.today()
        month_label = st.selectbox("Mês", MESES, index=today.month-1)
        year = st.selectbox("Ano", list(range(today.year-2, today.year+3)), index=2)
        month = MESES.index(month_label) + 1

        st.divider()
        page = st.radio("Menu", ["📊 Dashboard", "🧾 Pagamentos", "🏷️ Categorias", "💰 Planejamento", "📤 Exportar"], index=0)
        st.divider()

        if st.button("Sair", use_container_width=True):
            st.session_state.user_id = None
            st.session_state.username = None
            st.session_state.edit_id = None
            st.rerun()

    # Load data
    rows = repos.list_payments(st.session_state.user_id, month, year)
    df = pd.DataFrame(rows, columns=["id","Descrição","Valor","Vencimento","Pago","Data pagamento","CategoriaID","Categoria"])

    total = float(df["Valor"].sum()) if not df.empty else 0.0
    total_pago = float(df.loc[df["Pago"]==1, "Valor"].sum()) if not df.empty else 0.0
    total_aberto = total - total_pago

    overdue = 0.0
    if not df.empty:
        def _is_overdue(row):
            d = parse_date_str(row["Vencimento"])
            return (row["Pago"] == 0) and (d < date.today())
        overdue = float(df[df.apply(_is_overdue, axis=1)]["Valor"].sum())

    budget = repos.get_budget(st.session_state.user_id, month, year)
    income = float(budget["income"])
    goal = float(budget["expense_goal"])
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

    # -------------------- Pagamentos --------------------
    if page == "🧾 Pagamentos":
        st.subheader("🧾 Pagamentos (adicionar / editar / excluir)")

        # categorias para select
        cats = repos.list_categories(st.session_state.user_id)
        cat_map = {name: cid for cid, name in cats}
        cat_names = ["(Sem categoria)"] + list(cat_map.keys())

        with st.expander("➕ Adicionar pagamento", expanded=True):
            a1, a2, a3, a4 = st.columns([3,1,1.3,2])
            desc = a1.text_input("Descrição", key="add_desc")
            val = a2.number_input("Valor (R$)", min_value=0.0, step=10.0, key="add_val")
            venc = a3.date_input("Vencimento", key="add_due")
            cat_name = a4.selectbox("Categoria", cat_names, key="add_cat")

            if st.button("Adicionar", type="primary", key="btn_add"):
                try:
                    cid = None if cat_name == "(Sem categoria)" else cat_map[cat_name]
                    repos.add_payment(st.session_state.user_id, desc, val, str(venc), month, year, cid)
                    st.success("Pagamento adicionado.")
                    st.rerun()
                except Exception as e:
                    st.error(str(e))

        # Editor (quando clicar em editar)
        if st.session_state.edit_id is not None:
            # achar a linha do id
            edit_row = None
            for r in rows:
                if r[0] == st.session_state.edit_id:
                    edit_row = r
                    break

            if edit_row:
                pid, dsc, amt, due, paid, paid_date, cat_id, cat_name = edit_row
                st.info(f"Editando ID **{pid}**")
                cats = repos.list_categories(st.session_state.user_id)
                cat_map2 = {name: cid for cid, name in cats}
                cat_names2 = ["(Sem categoria)"] + list(cat_map2.keys())
                current_cat = cat_name if cat_name else "(Sem categoria)"
                if current_cat not in cat_names2:
                    current_cat = "(Sem categoria)"

                with st.form("form_edit"):
                    e1, e2, e3, e4 = st.columns([3,1,1.3,2])
                    new_desc = e1.text_input("Descrição", value=str(dsc))
                    new_val = e2.number_input("Valor (R$)", min_value=0.0, step=10.0, value=float(amt))
                    new_due = e3.date_input("Vencimento", value=parse_date_str(due))
                    new_cat_name = e4.selectbox("Categoria", cat_names2, index=cat_names2.index(current_cat))

                    s1, s2 = st.columns(2)
                    save = s1.form_submit_button("Salvar alterações", type="primary")
                    cancel = s2.form_submit_button("Cancelar")

                    if cancel:
                        st.session_state.edit_id = None
                        st.rerun()

                    if save:
                        try:
                            new_cid = None if new_cat_name == "(Sem categoria)" else cat_map2[new_cat_name]
                            repos.update_payment(st.session_state.user_id, pid, new_desc, new_val, str(new_due), new_cid)
                            st.session_state.edit_id = None
                            st.success("Pagamento atualizado.")
                            st.rerun()
                        except Exception as e:
                            st.error(str(e))

        st.divider()
        if df.empty:
            st.info("Sem pagamentos para este mês/ano.")
        else:
            st.caption("Dica: no celular, role para ver tudo. Os botões ficam por linha.")

            for r in rows:
                pid, desc, amount, due, paid, paid_date, cat_id, cat_name = r

                colA, colB, colC, colD, colE, colF, colG = st.columns([4,1.2,1.5,1.2,1.2,1.0,1.0])
                colA.write(f"**{desc}**" + (f"  \n🏷️ {cat_name}" if cat_name else ""))
                colB.write(fmt_brl(float(amount)))
                colC.write(str(due))

                status = "✅ Pago" if paid else "🕓 Aberto"
                colD.write(status)

                if not paid:
                    if colE.button("Marcar pago", key=f"pay_{pid}"):
                        repos.mark_paid(st.session_state.user_id, pid, True)
                        st.rerun()
                else:
                    if colE.button("Desfazer", key=f"unpay_{pid}"):
                        repos.mark_paid(st.session_state.user_id, pid, False)
                        st.rerun()

                if colF.button("Editar", key=f"edit_{pid}"):
                    st.session_state.edit_id = pid
                    st.rerun()

                if colG.button("Excluir", key=f"del_{pid}"):
                    repos.delete_payment(st.session_state.user_id, pid)
                    st.rerun()

    # -------------------- Categorias --------------------
    elif page == "🏷️ Categorias":
        st.subheader("🏷️ Categorias (criar / excluir)")

        c1, c2 = st.columns([2,3])
        with c1:
            new_cat = st.text_input("Nova categoria", key="cat_new")
            if st.button("Adicionar categoria", type="primary", key="cat_add"):
                try:
                    repos.create_category(st.session_state.user_id, new_cat)
                    st.success("Categoria criada.")
                    st.rerun()
                except Exception as e:
                    st.error(str(e))

        with c2:
            cats = repos.list_categories(st.session_state.user_id)
            if not cats:
                st.info("Você ainda não criou categorias.")
            else:
                for cid, name in cats:
                    a, b = st.columns([4,1])
                    a.write(name)
                    if b.button("Excluir", key=f"catdel_{cid}"):
                        repos.delete_category(st.session_state.user_id, cid)
                        st.rerun()

    # -------------------- Planejamento --------------------
    elif page == "💰 Planejamento":
        st.subheader("💰 Planejamento do mês (renda + meta)")

        current = repos.get_budget(st.session_state.user_id, month, year)
        income_val = st.number_input("Renda do mês (R$)", min_value=0.0, step=100.0, value=float(current["income"]))
        goal_val = st.number_input("Meta de gastos (R$)", min_value=0.0, step=100.0, value=float(current["expense_goal"]))

        if st.button("Salvar planejamento", type="primary"):
            repos.upsert_budget(st.session_state.user_id, month, year, income_val, goal_val)
            st.success("Planejamento salvo.")
            st.rerun()

        st.divider()
        st.write("📌 Indicadores do mês")
        gasto = float(df["Valor"].sum()) if not df.empty else 0.0
        sobra = income_val - gasto
        meta_restante = (goal_val - gasto) if goal_val else 0.0

        c1, c2, c3 = st.columns(3)
        c1.metric("Gasto do mês", fmt_brl(gasto))
        c2.metric("Sobra (renda - gasto)", fmt_brl(sobra))
        c3.metric("Meta restante (meta - gasto)", fmt_brl(meta_restante))

        if goal_val > 0:
            pct = (gasto / goal_val) * 100 if goal_val else 0
            st.progress(min(1.0, gasto / goal_val))
            st.caption(f"Você já usou **{pct:.1f}%** da meta de gastos.")

    # -------------------- Exportar --------------------
    elif page == "📤 Exportar":
        st.subheader("📤 Exportar (mês/ano selecionado)")

        df_exp = repos.payments_dataframe(st.session_state.user_id, month, year)
        st.dataframe(df_exp, use_container_width=True, hide_index=True)

        excel_bytes = export_excel_bytes(df_exp, sheet_name=f"{MESES[month-1]}_{year}")
        st.download_button(
            "📊 Baixar Excel",
            data=excel_bytes,
            file_name=f"pagamentos_{month:02d}_{year}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )

        pdf_bytes = export_pdf_bytes(df_exp, title=f"Pagamentos - {MESES[month-1]}/{year}")
        st.download_button(
            "📄 Baixar PDF",
            data=pdf_bytes,
            file_name=f"pagamentos_{month:02d}_{year}.pdf",
            mime="application/pdf",
            use_container_width=True
        )

    # -------------------- Dashboard --------------------
    else:
        st.subheader("📊 Dashboard")

        if df.empty:
            st.info("Sem dados para gerar gráficos neste mês/ano.")
            return

        df2 = df.copy()
        df2["Categoria"] = df2["Categoria"].fillna("Sem categoria")
        df2["Status"] = df2["Pago"].map({0: "Em aberto", 1: "Pago"})

        left, right = st.columns([2,1])
        with left:
            fig1 = px.pie(df2, names="Categoria", values="Valor", title="Gastos por categoria")
            st.plotly_chart(fig1, use_container_width=True)

        with right:
            fig2 = px.bar(df2.groupby("Status", as_index=False)["Valor"].sum(), x="Status", y="Valor", title="Pago x Em aberto")
            st.plotly_chart(fig2, use_container_width=True)

        st.divider()
        by_cat = df2.groupby("Categoria", as_index=False)["Valor"].sum().sort_values("Valor", ascending=False)
        st.write("📌 Resumo por categoria")
        st.dataframe(by_cat, use_container_width=True, hide_index=True)


# -------------------- Router --------------------
if st.session_state.user_id is None:
    screen_auth()
else:
    screen_app()
