import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import date, datetime

from database import init_db
from auth import authenticate, create_user, get_security_question, reset_password
import repos
from export_utils import export_excel_bytes, export_pdf_bytes

# ========================
# CONFIGURAÇÃO INICIAL
# ========================
st.set_page_config(
    page_title="Controle Financeiro",
    page_icon="💳",
    layout="wide"
)

init_db()

# ========================
# CSS
# ========================
def inject_css():
    try:
        with open("style.css", "r", encoding="utf-8") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
    except FileNotFoundError:
        pass

inject_css()

# ========================
# SESSION
# ========================
if "user_id" not in st.session_state:
    st.session_state.user_id = None

if "username" not in st.session_state:
    st.session_state.username = None

MESES = [
    "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
    "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"
]

# ========================
# AUTENTICAÇÃO
# ========================
def tela_login():
    st.title("💳 Controle Financeiro")
    st.caption("Cada usuário acessa apenas seus próprios dados")

    tab1, tab2, tab3 = st.tabs(["Entrar", "Criar conta", "Recuperar senha"])

    with tab1:
        usuario = st.text_input("Usuário")
        senha = st.text_input("Senha", type="password")
        if st.button("Entrar", use_container_width=True):
            uid = authenticate(usuario, senha)
            if uid:
                st.session_state.user_id = uid
                st.session_state.username = usuario
                st.rerun()
            else:
                st.error("Usuário ou senha inválidos")

    with tab2:
        novo_usuario = st.text_input("Novo usuário")
        nova_senha = st.text_input("Nova senha", type="password")
        pergunta = st.selectbox(
            "Pergunta de segurança",
            [
                "Nome do primeiro pet?",
                "Nome da mãe?",
                "Cidade onde nasceu?",
                "Filme favorito?"
            ]
        )
        resposta = st.text_input("Resposta de segurança")
        if st.button("Criar conta", type="primary", use_container_width=True):
            try:
                create_user(novo_usuario, nova_senha, pergunta, resposta)
                st.success("Conta criada com sucesso! Faça login.")
            except Exception as e:
                st.error(str(e))

    with tab3:
        usuario = st.text_input("Usuário para recuperação")
        pergunta = get_security_question(usuario) if usuario else None
        if pergunta:
            st.info(pergunta)
            resposta = st.text_input("Resposta")
            nova_senha = st.text_input("Nova senha", type="password")
            if st.button("Redefinir senha", use_container_width=True):
                try:
                    ok = reset_password(usuario, resposta, nova_senha)
                    if ok:
                        st.success("Senha alterada com sucesso")
                    else:
                        st.error("Resposta incorreta")
                except Exception as e:
                    st.error(str(e))

# ========================
# APP PRINCIPAL
# ========================
def app():
    hoje = date.today()

    with st.sidebar:
        st.markdown(f"👤 **{st.session_state.username}**")

        mes_nome = st.selectbox("Mês", MESES, index=hoje.month - 1)
        ano = st.selectbox("Ano", list(range(hoje.year - 2, hoje.year + 3)))

        mes = MESES.index(mes_nome) + 1

        menu = st.radio(
            "Menu",
            ["📊 Dashboard", "🧾 Pagamentos", "🏷️ Categorias", "💰 Planejamento", "📤 Exportar"]
        )

        if st.button("🚪 Sair"):
            st.session_state.user_id = None
            st.session_state.username = None
            st.rerun()

    dados = repos.list_payments(st.session_state.user_id, mes, ano)
    df = pd.DataFrame(
        dados,
        columns=["id", "Descrição", "Valor", "Vencimento", "Pago", "Data Pagamento", "Categoria"]
    )

    st.title(f"📅 {mes_nome}/{ano}")

    total = df["Valor"].sum() if not df.empty else 0
    pago = df[df["Pago"] == 1]["Valor"].sum() if not df.empty else 0
    aberto = total - pago

    c1, c2, c3 = st.columns(3)
    c1.metric("Total", f"R$ {total:,.2f}")
    c2.metric("Pago", f"R$ {pago:,.2f}")
    c3.metric("Em aberto", f"R$ {aberto:,.2f}")

    # ========================
    # PAGAMENTOS
    # ========================
    if menu == "🧾 Pagamentos":
        st.subheader("🧾 Pagamentos")

        categorias = repos.list_categories(st.session_state.user_id)
        mapa = {nome: cid for cid, nome in categorias}
        nomes = ["(Sem categoria)"] + list(mapa.keys())

        with st.expander("➕ Novo pagamento", expanded=True):
            d = st.text_input("Descrição")
            v = st.number_input("Valor", min_value=0.0)
            ven = st.date_input("Vencimento")
            cat = st.selectbox("Categoria", nomes)

            if st.button("Adicionar", type="primary"):
                cid = None if cat == "(Sem categoria)" else mapa[cat]
                repos.add_payment(
                    st.session_state.user_id,
                    d,
                    v,
                    str(ven),
                    mes,
                    ano,
                    cid
                )
                st.rerun()

        if not df.empty:
            for r in dados:
                pid, desc, val, venc, pago_flag, _, cat = r
                a, b, c, d = st.columns([4, 1, 1, 1])
                a.write(f"**{desc}**  \n🏷️ {cat or '—'}")
                b.write(f"R$ {val:,.2f}")
                c.write("✅ Pago" if pago_flag else "🕓 Aberto")

                if not pago_flag:
                    if d.button("Pagar", key=f"p{pid}"):
                        repos.mark_paid(st.session_state.user_id, pid, True)
                        st.rerun()
                else:
                    if d.button("Desfazer", key=f"u{pid}"):
                        repos.mark_paid(st.session_state.user_id, pid, False)
                        st.rerun()

    # ========================
    # DASHBOARD
    # ========================
    if menu == "📊 Dashboard" and not df.empty:
        df2 = df.copy()
        df2["Categoria"] = df2["Categoria"].fillna("Sem categoria")
        fig = px.pie(df2, names="Categoria", values="Valor", title="Gastos por categoria")
        st.plotly_chart(fig, use_container_width=True)

    # ========================
    # EXPORTAR
    # ========================
    if menu == "📤 Exportar":
        df_exp = repos.payments_dataframe(st.session_state.user_id, mes, ano)
        st.dataframe(df_exp, use_container_width=True)

        st.download_button(
            "📊 Excel",
            export_excel_bytes(df_exp),
            file_name="pagamentos.xlsx"
        )

        st.download_button(
            "📄 PDF",
            export_pdf_bytes(df_exp),
            file_name="pagamentos.pdf"
        )

# ========================
# ROUTER
# ========================
if st.session_state.user_id is None:
    tela_login()
else:
    app()
