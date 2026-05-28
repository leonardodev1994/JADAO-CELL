Jadão Cell

Sistema Streamlit para assistência técnica, estoque, vendas, caixa, clientes, financeiro e ordens de serviço.

Arquivo principal:
app.py

Rodar localmente:
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py

Deploy:
Consulte DEPLOY.md.

Segurança:
Não publique .env, .streamlit/secrets.toml, banco.db, backups ou uploads no GitHub.
