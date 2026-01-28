with st.expander("➕ Adicionar despesa", expanded=True):
    with st.form("form_add_despesa", clear_on_submit=True):
        a1, a2, a3, a4, a5 = st.columns([3,1,1.3,2,1])

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

            st.success("Despesa adicionada!")
            st.rerun()
