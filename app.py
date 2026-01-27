
    import streamlit as st
    import pandas as pd
    import plotly.express as px
    from datetime import date, datetime

    from database import init_db
    from auth import authenticate, create_user, get_security_question, reset_password
    import repos
    from export_utils import export_excel_bytes, export_pdf_bytes

    # -------------------- Setup --------------------
    st.set_page_config(page_title="Financeiro", page_icon="💳", layout="wide")
    init_db()

    def inject_css():
        with open("style.css", "r", encoding="utf-8") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

    inject_css()

    # Session
    if "user_id" not in st.session_state:
        st.session_state.user_id = None
    if "username" not in st.session_state:
        st.session_state.username = None

    # Helpers
    MESES = [
        "Janeiro","Fevereiro","Março","Abril","Maio","Junho",
        "Julho","Agosto","Setembro","Outubro","Novembro","Dezembro"
    ]

    def month_label_to_int(label):
        return MESES.index(label) + 1

    def int_to_month_label(m):
        return MESES[m-1]

    # -------------------- Auth screens --------------------
    def screen_auth():
        st.title("💳 Controle Financeiro")
        st.write("Acesse pelo computador ou celular. Cada usuário vê apenas os próprios dados.")

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
    def kpi(label, value, help_text=None):
        st.markdown(
            f"""
            <div class="kpi-card">
              <div class="muted">{label}</div>
              <div style="font-size: 1.6rem; font-weight: 700; margin-top: 2px;">{value}</div>
            </div>
            """,
            unsafe_allow_html=True
        )
        if help_text:
            st.caption(help_text)

    def screen_app():
        # Sidebar
        with st.sidebar:
            st.markdown(f"**Usuário:** `{st.session_state.username}`")
            today = date.today()
            default_month = today.month
            default_year = today.year

            month_label = st.selectbox("Mês", MESES, index=default_month-1)
            year = st.selectbox("Ano", list(range(default_year-2, default_year+3)), index=2)

            month = month_label_to_int(month_label)

            st.divider()
            page = st.radio("Menu", ["📊 Dashboard", "🧾 Pagamentos", "🏷️ Categorias", "💰 Planejamento", "📤 Exportar"], index=0)
            st.divider()
            if st.button("Sair", use_container_width=True):
                st.session_state.user_id = None
                st.session_state.username = None
                st.rerun()

        # Data for period
        rows = repos.list_payments(st.session_state.user_id, month, year)
        df = pd.DataFrame(rows, columns=["id","Descrição","Valor","Vencimento","Pago","Data pagamento","Categoria"])

        # KPIs
        total = float(df["Valor"].sum()) if not df.empty else 0.0
        total_pago = float(df.loc[df["Pago"]==1, "Valor"].sum()) if not df.empty else 0.0
        total_aberto = total - total_pago

        # overdue
        overdue = 0.0
        if not df.empty:
            def _is_overdue(row):
                try:
                    d = datetime.fromisoformat(str(row["Vencimento"])).date()
                except:
                    d = datetime.strptime(str(row["Vencimento"]), "%Y-%m-%d").date()
                return (row["Pago"]==0) and (d < date.today())
            overdue = float(df[df.apply(_is_overdue, axis=1)]["Valor"].sum())

        budget = repos.get_budget(st.session_state.user_id, month, year)
        income = float(budget["income"])
        goal = float(budget["expense_goal"])
        saldo = income - total

        st.title("💳 Controle Financeiro")
        st.caption(f"Período: **{int_to_month_label(month)}/{year}**")

        c1, c2, c3, c4, c5 = st.columns(5)
        with c1: kpi("Total do mês", f"R$ {total:,.2f}".replace(",", "X").replace(".", ",").replace("X","."))
        with c2: kpi("Pago", f"R$ {total_pago:,.2f}".replace(",", "X").replace(".", ",").replace("X","."))
        with c3: kpi("Em aberto", f"R$ {total_aberto:,.2f}".replace(",", "X").replace(".", ",").replace("X","."))
        with c4: kpi("Em atraso", f"R$ {overdue:,.2f}".replace(",", "X").replace(".", ",").replace("X","."))
        with c5: kpi("Saldo (renda - total)", f"R$ {saldo:,.2f}".replace(",", "X").replace(".", ",").replace("X","."),
                    "Defina renda no menu Planejamento.")

        st.divider()

        # Pages
        if page == "🧾 Pagamentos":
            st.subheader("🧾 Pagamentos")

            # Category mapping
            cats = repos.list_categories(st.session_state.user_id)
            cat_map = {name: cid for cid, name in cats}
            cat_names = ["(Sem categoria)"] + list(cat_map.keys())

            with st.expander("➕ Adicionar pagamento", expanded=True):
                cc1, cc2, cc3, cc4 = st.columns([3,1,1,2])
                desc = cc1.text_input("Descrição")
                val = cc2.number_input("Valor (R$)", min_value=0.0, step=10.0)
                venc = cc3.date_input("Vencimento")
                cat_name = cc4.selectbox("Categoria", cat_names)
                if st.button("Adicionar", type="primary"):
                    try:
                        cid = None if cat_name == "(Sem categoria)" else cat_map[cat_name]
                        repos.add_payment(st.session_state.user_id, desc, val, str(venc), month, year, cid)
                        st.success("Pagamento adicionado.")
                        st.rerun()
                    except Exception as e:
                        st.error(str(e))

            st.divider()
            st.write("✅ Dica: no celular, role a tabela; os botões ficam por linha.")

            if df.empty:
                st.info("Sem pagamentos para este mês/ano.")
            else:
                # Render rows with action buttons
                for r in rows:
                    pid, desc, amount, due, paid, paid_date, cat = r
                    colA, colB, colC, colD, colE, colF = st.columns([4,1.2,1.5,1.2,1.2,1.2])
                    colA.write(f"**{desc}**" + (f"  
🏷️ {cat}" if cat else ""))
                    colB.write(f"R$ {float(amount):,.2f}".replace(",", "X").replace(".", ",").replace("X","."))
                    colC.write(str(due))
                    colD.write("✅ Pago" if paid else "🕓 Aberto")
                    if not paid:
                        if colE.button("Marcar pago", key=f"pay_{pid}"):
                            repos.mark_paid(st.session_state.user_id, pid, True)
                            st.rerun()
                    else:
                        if colE.button("Desfazer", key=f"unpay_{pid}"):
                            repos.mark_paid(st.session_state.user_id, pid, False)
                            st.rerun()
                    if colF.button("Excluir", key=f"del_{pid}"):
                        repos.delete_payment(st.session_state.user_id, pid)
                        st.rerun()

        elif page == "🏷️ Categorias":
            st.subheader("🏷️ Categorias")
            c1, c2 = st.columns([2,3])
            with c1:
                new_cat = st.text_input("Nova categoria")
                if st.button("Adicionar categoria", type="primary"):
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

        elif page == "💰 Planejamento":
            st.subheader("💰 Planejamento do mês")
            current = repos.get_budget(st.session_state.user_id, month, year)
            income = st.number_input("Renda do mês (R$)", min_value=0.0, step=100.0, value=float(current["income"]))
            goal = st.number_input("Meta de gastos (R$)", min_value=0.0, step=100.0, value=float(current["expense_goal"]))

            if st.button("Salvar planejamento", type="primary"):
                repos.upsert_budget(st.session_state.user_id, month, year, income, goal)
                st.success("Planejamento salvo.")
                st.rerun()

            st.divider()
            st.write("📌 Indicadores")
            total = float(df["Valor"].sum()) if not df.empty else 0.0
            gasto = total
            sobra = income - gasto
            meta_restante = goal - gasto if goal else 0.0

            c1, c2, c3 = st.columns(3)
            c1.metric("Gasto do mês", f"R$ {gasto:,.2f}".replace(",", "X").replace(".", ",").replace("X","."))
            c2.metric("Sobra (renda - gasto)", f"R$ {sobra:,.2f}".replace(",", "X").replace(".", ",").replace("X","."))
            c3.metric("Meta restante (meta - gasto)", f"R$ {meta_restante:,.2f}".replace(",", "X").replace(".", ",").replace("X","."))

            if goal > 0:
                pct = (gasto / goal) * 100 if goal else 0
                st.progress(min(1.0, gasto/goal) if goal else 0.0)
                st.caption(f"Você já usou **{pct:.1f}%** da meta de gastos.")

        elif page == "📤 Exportar":
            st.subheader("📤 Exportar (mês/ano selecionado)")
            df_exp = repos.payments_dataframe(st.session_state.user_id, month, year)

            st.dataframe(df_exp, use_container_width=True, hide_index=True)

            excel_bytes = export_excel_bytes(df_exp, sheet_name=f"{int_to_month_label(month)}_{year}")
            st.download_button(
                "📊 Baixar Excel",
                data=excel_bytes,
                file_name=f"pagamentos_{month:02d}_{year}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )

            pdf_bytes = export_pdf_bytes(df_exp, title=f"Pagamentos - {int_to_month_label(month)}/{year}")
            st.download_button(
                "📄 Baixar PDF",
                data=pdf_bytes,
                file_name=f"pagamentos_{month:02d}_{year}.pdf",
                mime="application/pdf",
                use_container_width=True
            )

        else:  # Dashboard
            st.subheader("📊 Dashboard")

            if df.empty:
                st.info("Sem dados para gerar gráficos neste mês/ano.")
                return

            df2 = df.copy()
            df2["Categoria"] = df2["Categoria"].fillna("Sem categoria")
            df2["Status"] = df2["Pago"].map({0:"Em aberto", 1:"Pago"})

            left, right = st.columns([2,1])
            with left:
                fig1 = px.pie(df2, names="Categoria", values="Valor", title="Gastos por categoria")
                st.plotly_chart(fig1, use_container_width=True)

            with right:
                fig2 = px.bar(df2.groupby("Status", as_index=False)["Valor"].sum(), x="Status", y="Valor", title="Pago x Em aberto")
                st.plotly_chart(fig2, use_container_width=True)

            st.divider()
            # Table summary
            by_cat = df2.groupby("Categoria", as_index=False)["Valor"].sum().sort_values("Valor", ascending=False)
            st.write("📌 Resumo por categoria")
            st.dataframe(by_cat, use_container_width=True, hide_index=True)

    # Router
    if st.session_state.user_id is None:
        screen_auth()
    else:
        screen_app()
