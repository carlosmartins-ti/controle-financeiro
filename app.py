import streamlit as st
from datetime import date
import repos

st.set_page_config(page_title="Controle Financeiro", layout="wide")

CATEGORIA_CARTAO = "Cartão de crédito"

st.title("💳 Controle Financeiro")

# ================== LOGIN SIMPLES ==================
if "user_id" not in st.session_state:
    st.session_state.user_id = 1  # exemplo fixo (ajuste depois)

month = st.selectbox("Mês", list(range(1,13)))
year = st.selectbox("Ano", list(range(2024,2030)))

# ================== CATEGORIAS ==================
cats = repos.list_categories(st.session_state.user_id)
cat_map = {name: cid for cid, name in cats}

# ================== ADICIONAR PAGAMENTO ==================
st.subheader("➕ Novo lançamento")

desc = st.text_input("Descrição")
val = st.number_input("Valor total", min_value=0.0)
cat = st.selectbox("Categoria", list(cat_map.keys()))
parcelado = st.checkbox("Parcelado?")
parcelas = st.number_input("Qtd parcelas", min_value=1, value=1)

if st.button("Salvar"):
    if parcelado and parcelas > 1:
        repos.create_installments(
            st.session_state.user_id,
            desc,
            val,
            parcelas,
            month,
            year,
            cat_map[cat]
        )
    else:
        repos.add_payment(
            st.session_state.user_id,
            desc,
            val,
            "01",
            month,
            year,
            cat_map[cat]
        )
    st.success("Lançamento criado")
    st.rerun()

# ================== FATURA ==================
rows = repos.list_payments(st.session_state.user_id, month, year)

total_cartao = sum(r[2] for r in rows if cat == CATEGORIA_CARTAO)

if total_cartao > 0:
    st.divider()
    st.subheader(f"💳 Fatura Cartão {month}/{year}")
    st.write(f"Total: R$ {total_cartao:.2f}")

    if st.button("Pagar fatura"):
        repos.mark_month_paid_by_category(
            st.session_state.user_id,
            month,
            year,
            CATEGORIA_CARTAO
        )
        st.success("Fatura paga")
        st.rerun()
