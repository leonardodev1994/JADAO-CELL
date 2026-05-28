# Deploy da Jadão Cell no GitHub + Streamlit Community Cloud

## Estrutura do projeto

- Arquivo principal: `app.py`
- Dependências: `requirements.txt`
- Configuração visual do Streamlit: `.streamlit/config.toml`
- Exemplo de secrets: `.streamlit/secrets.toml.example`
- Banco local de desenvolvimento: `banco.db` (não deve ser publicado)
- Banco recomendado para produção: PostgreSQL/Supabase via `DATABASE_URL`

## Arquivos protegidos

O `.gitignore` protege arquivos locais e sensíveis:

- `.env` e `.env.*`
- `.streamlit/secrets.toml`
- `banco.db`, `*.db`, `*.sqlite`, `*.sqlite3`
- `backups/`
- `uploads/`
- `.venv/`, `venv/`, `env/`
- `tools/rclone`
- chaves como `*.pem` e `*.key`

## Rodar localmente

```bash
cd "CAMINHO/DO/PROJETO/Jadão Cell"
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

Sem `DATABASE_URL`, o sistema usa SQLite local (`banco.db`). Isso é bom para teste local, mas não é recomendado como banco principal no Streamlit Community Cloud.

## Configurar Supabase

1. Crie um projeto no Supabase.
2. Vá em `Project Settings > Database`.
3. Copie a connection string PostgreSQL.
4. Use a URL no formato abaixo, trocando apenas pelos dados reais do seu projeto:

```toml
DATABASE_URL = "postgresql://postgres.SEUPROJETO:SUA_SENHA@aws-0-sa-east-1.pooler.supabase.com:6543/postgres"
SUPABASE_URL = "https://SEUPROJETO.supabase.co"
SUPABASE_KEY = "SUA_CHAVE"
```

Nunca coloque essa URL dentro do código nem faça commit dela no GitHub.

## Migrar dados do SQLite para Supabase

Com o banco local `banco.db` pronto e a URL do Supabase em mãos:

```bash
source .venv/bin/activate
python scripts/migrate_sqlite_to_supabase.py --database-url "SUA_DATABASE_URL_DO_SUPABASE" --replace
```

Use `--replace` somente quando quiser apagar os dados atuais do Supabase antes de enviar os dados locais. Para evitar apagar dados online, rode sem `--replace`.

## Publicar no GitHub

Se ainda não existir repositório remoto:

```bash
git init
git add .
git commit -m "Prepara Jadão Cell para deploy"
git branch -M main
git remote add origin https://github.com/SEU_USUARIO/SEU_REPOSITORIO.git
git push -u origin main
```

Se o repositório já existir:

```bash
git status
git add .gitignore .streamlit/config.toml .streamlit/secrets.toml.example DEPLOY.md README.txt Procfile app.py database utils views scripts requirements.txt assets
git commit -m "Prepara deploy da Jadao Cell"
git push origin main
```

Antes de fazer `git add .`, confirme que `banco.db`, `.env`, `backups/`, `uploads/` e `.streamlit/secrets.toml` não aparecem no `git status`.

## Conectar no Streamlit Community Cloud

1. Acesse `https://share.streamlit.io`.
2. Entre com sua conta GitHub.
3. Clique em `Create app` ou `New app`.
4. Escolha o repositório da Jadão Cell.
5. Branch: `main`.
6. Main file path: `app.py`.
7. Abra `Advanced settings`.
8. Em `Secrets`, cole:

```toml
DATABASE_URL = "postgresql://postgres.SEUPROJETO:SUA_SENHA@aws-0-sa-east-1.pooler.supabase.com:6543/postgres"
SUPABASE_URL = "https://SEUPROJETO.supabase.co"
SUPABASE_KEY = "SUA_CHAVE"
```

9. Salve e clique em `Deploy`.

## Tratamento de erro no deploy

O sistema agora mostra uma mensagem clara se o `DATABASE_URL` estiver configurado mas a conexão com Supabase falhar.

Se o `DATABASE_URL` não estiver configurado, o sistema roda com SQLite local e mostra um aviso no menu lateral. No Streamlit Community Cloud, use Supabase para manter dados persistentes.

## Atualizações futuras

Para publicar novas versões:

```bash
git status
git add ARQUIVOS_ALTERADOS
git commit -m "Descreva a melhoria"
git push origin main
```

O Streamlit Community Cloud redeploya automaticamente quando detectar o novo commit no GitHub.
