
# Controle Financeiro (Streamlit) — v2

Sistema com:
- Cadastro / Login (usuário + senha)
- Isolamento total por usuário (cada um vê apenas os próprios dados)
- Separação por mês/ano
- Categorias
- Dashboard com gráficos
- Exportar Excel e PDF
- Recuperação de senha por pergunta de segurança

## Rodar local
```bash
pip install -r requirements.txt
streamlit run app.py
```

## Deploy (Streamlit Community Cloud)
1. Suba este projeto no GitHub
2. Abra Streamlit Cloud e conecte o repo
3. Entry point: `app.py`
