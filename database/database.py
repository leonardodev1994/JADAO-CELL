import os
import sqlite3
from pathlib import Path


class DatabaseConfigError(RuntimeError):
    pass


def get_streamlit_secret(name, required=False):
    try:
        import streamlit as st

        value = st.secrets[name]
    except KeyError as error:
        if required:
            raise DatabaseConfigError(f"Secret obrigatório não configurado: {name}") from error
        return None
    except Exception:
        return None

    value = str(value).strip()
    return value or None


def _get_database_url():
    return get_streamlit_secret("DATABASE_URL")


def is_streamlit_cloud():
    return (
        os.getenv("STREAMLIT_CLOUD") == "1"
        or os.getenv("STREAMLIT_SHARING_MODE") is not None
        or Path("/mount/src").exists()
    )


def is_database_url_configured():
    return bool(_get_database_url())


def is_supabase_project_configured():
    return bool(get_streamlit_secret("SUPABASE_URL") and get_streamlit_secret("SUPABASE_KEY"))


def database_mode_label():
    return "PostgreSQL/Supabase" if is_database_url_configured() else "SQLite local"


class PostgresCursor:
    def __init__(self, cursor):
        self._cursor = cursor

    def execute(self, query, params=None):
        self._cursor.execute(_postgres_query(query), params)
        return self

    def fetchone(self):
        return self._cursor.fetchone()

    def fetchall(self):
        return self._cursor.fetchall()

    def close(self):
        return self._cursor.close()

    @property
    def description(self):
        return self._cursor.description

    @property
    def rowcount(self):
        return self._cursor.rowcount

    def __iter__(self):
        return iter(self._cursor)

    def __getattr__(self, name):
        return getattr(self._cursor, name)


class PostgresConnection:
    backend = "postgres"

    def __init__(self, conn):
        self._conn = conn

    def cursor(self):
        return PostgresCursor(self._conn.cursor())

    def commit(self):
        return self._conn.commit()

    def rollback(self):
        return self._conn.rollback()

    def close(self):
        return self._conn.close()

    def __getattr__(self, name):
        return getattr(self._conn, name)


def _postgres_query(query):
    return query.replace("?", "%s")


def init_db(db_path="banco.db"):
    try:
        import streamlit as st

        return _init_db_cached(db_path)
    except RuntimeError:
        return _init_db_uncached(db_path)


def _init_db_uncached(db_path="banco.db"):
    database_url = _get_database_url()

    if database_url:
        try:
            return init_postgres_db(database_url)
        except Exception as error:
            raise DatabaseConfigError(
                "Não foi possível conectar ao PostgreSQL/Supabase. "
                "Confira se o Secret DATABASE_URL está configurado corretamente no Streamlit Cloud "
                "e se a senha/host/porta do Supabase estão válidos."
            ) from error

    if is_streamlit_cloud():
        raise DatabaseConfigError(
            "DATABASE_URL não foi encontrado nos Secrets do Streamlit Cloud. "
            "Por segurança, o sistema online não usa SQLite local. "
            "Configure DATABASE_URL em App > Settings > Secrets e reinicie o app."
        )

    conn = sqlite3.connect(db_path, check_same_thread=False)
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS lancamentos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        data TEXT,
        tipo TEXT,
        descricao TEXT,
        valor REAL
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS pagamentos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        lancamento_id INTEGER,
        forma_pagamento TEXT,
        valor REAL
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS vendas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        data TEXT,
        total REAL,
        status TEXT DEFAULT 'Ativa',
        usuario_id INTEGER,
        usuario_nome TEXT,
        criado_em TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS venda_itens (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        venda_id INTEGER,
        lancamento_id INTEGER,
        tipo TEXT,
        descricao TEXT,
        produto_id INTEGER,
        quantidade REAL,
        valor_unitario REAL,
        valor_total REAL
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS auditoria (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        data_hora TEXT DEFAULT CURRENT_TIMESTAMP,
        usuario_id INTEGER,
        usuario_nome TEXT,
        acao TEXT,
        entidade TEXT,
        entidade_id INTEGER,
        detalhes TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS estoque (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        produto TEXT NOT NULL,
        modelo TEXT,
        categoria TEXT,
        quantidade REAL NOT NULL DEFAULT 0,
        valor_venda REAL NOT NULL DEFAULT 0,
        estoque_minimo REAL NOT NULL DEFAULT 0,
        observacao TEXT,
        ativo INTEGER NOT NULL DEFAULT 1,
        criado_em TEXT DEFAULT CURRENT_TIMESTAMP,
        atualizado_em TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS estoque_movimentacoes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        produto_id INTEGER,
        data TEXT,
        tipo TEXT,
        quantidade REAL,
        motivo TEXT,
        lancamento_id INTEGER,
        responsavel TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS despesas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        data TEXT,
        descricao TEXT,
        valor REAL
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS caixa (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        data TEXT,
        valor_inicial REAL
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS ordens_servico (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        data TEXT,
        atendente TEXT,
        loja TEXT,
        cliente TEXT,
        cpf TEXT,
        telefone TEXT,
        endereco TEXT,
        marca TEXT,
        modelo TEXT,
        imei TEXT,
        senha TEXT,
        defeito TEXT,
        servico TEXT,
        valor REAL,
        garantia TEXT,
        status TEXT,
        observacoes TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS clientes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL,
        cpf TEXT,
        telefone TEXT,
        endereco TEXT,
        email TEXT,
        observacoes TEXT,
        ativo INTEGER NOT NULL DEFAULT 1,
        criado_em TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS usuarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL,
        usuario TEXT NOT NULL UNIQUE,
        senha_hash TEXT NOT NULL,
        senha_salt TEXT NOT NULL,
        perfil TEXT NOT NULL DEFAULT 'Atendente',
        ativo INTEGER NOT NULL DEFAULT 1,
        criado_em TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)

    for column, column_type in [
        ("cliente_id", "INTEGER"),
        ("data", "TEXT"),
        ("atendente", "TEXT"),
        ("loja", "TEXT"),
        ("cliente", "TEXT"),
        ("cpf", "TEXT"),
        ("telefone", "TEXT"),
        ("endereco", "TEXT"),
        ("marca", "TEXT"),
        ("modelo", "TEXT"),
        ("imei", "TEXT"),
        ("senha", "TEXT"),
        ("defeito", "TEXT"),
        ("servico", "TEXT"),
        ("valor", "REAL"),
        ("garantia", "TEXT"),
        ("status", "TEXT"),
        ("observacoes", "TEXT"),
    ]:
        _add_column_if_missing(cursor, "ordens_servico", column, column_type)

    _add_column_if_missing(cursor, "lancamentos", "produto_id", "INTEGER")
    _add_column_if_missing(cursor, "lancamentos", "quantidade", "REAL")
    _add_column_if_missing(cursor, "lancamentos", "venda_id", "INTEGER")
    _add_column_if_missing(cursor, "lancamentos", "venda_item_id", "INTEGER")

    _add_column_if_missing(cursor, "ordens_servico", "checklist_entrada", "TEXT")
    _add_column_if_missing(cursor, "ordens_servico", "checklist_reparo", "TEXT")
    _add_column_if_missing(cursor, "ordens_servico", "checklist_saida", "TEXT")
    _add_column_if_missing(cursor, "ordens_servico", "pagamento_os", "TEXT")
    _add_column_if_missing(cursor, "ordens_servico", "assinatura_entrada", "TEXT")
    _add_column_if_missing(cursor, "ordens_servico", "assinatura_saida", "TEXT")

    conn.commit()
    return conn


try:
    import streamlit as st

    _init_db_cached = st.cache_resource(show_spinner=False)(_init_db_uncached)
except Exception:
    _init_db_cached = _init_db_uncached


def init_postgres_db(database_url):
    import psycopg2

    connect_options = {
        "connect_timeout": 10,
        "keepalives": 1,
        "keepalives_idle": 30,
        "keepalives_interval": 10,
        "keepalives_count": 5,
    }

    if "sslmode=" in database_url:
        raw_conn = psycopg2.connect(database_url, **connect_options)
    else:
        raw_conn = psycopg2.connect(database_url, sslmode="require", **connect_options)
    conn = PostgresConnection(raw_conn)
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS lancamentos (
        id SERIAL PRIMARY KEY,
        data TEXT,
        tipo TEXT,
        descricao TEXT,
        valor DOUBLE PRECISION,
        produto_id INTEGER,
        quantidade DOUBLE PRECISION,
        venda_id INTEGER,
        venda_item_id INTEGER
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS pagamentos (
        id SERIAL PRIMARY KEY,
        lancamento_id INTEGER,
        forma_pagamento TEXT,
        valor DOUBLE PRECISION
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS vendas (
        id SERIAL PRIMARY KEY,
        data TEXT,
        total DOUBLE PRECISION,
        status TEXT DEFAULT 'Ativa',
        usuario_id INTEGER,
        usuario_nome TEXT,
        criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS venda_itens (
        id SERIAL PRIMARY KEY,
        venda_id INTEGER,
        lancamento_id INTEGER,
        tipo TEXT,
        descricao TEXT,
        produto_id INTEGER,
        quantidade DOUBLE PRECISION,
        valor_unitario DOUBLE PRECISION,
        valor_total DOUBLE PRECISION
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS auditoria (
        id SERIAL PRIMARY KEY,
        data_hora TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        usuario_id INTEGER,
        usuario_nome TEXT,
        acao TEXT,
        entidade TEXT,
        entidade_id INTEGER,
        detalhes TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS estoque (
        id SERIAL PRIMARY KEY,
        produto TEXT NOT NULL,
        modelo TEXT,
        categoria TEXT,
        quantidade DOUBLE PRECISION NOT NULL DEFAULT 0,
        valor_venda DOUBLE PRECISION NOT NULL DEFAULT 0,
        estoque_minimo DOUBLE PRECISION NOT NULL DEFAULT 0,
        observacao TEXT,
        ativo INTEGER NOT NULL DEFAULT 1,
        criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS estoque_movimentacoes (
        id SERIAL PRIMARY KEY,
        produto_id INTEGER,
        data TEXT,
        tipo TEXT,
        quantidade DOUBLE PRECISION,
        motivo TEXT,
        lancamento_id INTEGER,
        responsavel TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS despesas (
        id SERIAL PRIMARY KEY,
        data TEXT,
        descricao TEXT,
        valor DOUBLE PRECISION
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS caixa (
        id SERIAL PRIMARY KEY,
        data TEXT,
        valor_inicial DOUBLE PRECISION
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS ordens_servico (
        id SERIAL PRIMARY KEY,
        data TEXT,
        cliente_id INTEGER,
        atendente TEXT,
        loja TEXT,
        cliente TEXT,
        cpf TEXT,
        telefone TEXT,
        endereco TEXT,
        marca TEXT,
        modelo TEXT,
        imei TEXT,
        senha TEXT,
        defeito TEXT,
        servico TEXT,
        valor DOUBLE PRECISION,
        garantia TEXT,
        status TEXT,
        observacoes TEXT,
        checklist_entrada TEXT,
        checklist_reparo TEXT,
        checklist_saida TEXT,
        pagamento_os TEXT,
        assinatura_entrada TEXT,
        assinatura_saida TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS clientes (
        id SERIAL PRIMARY KEY,
        nome TEXT NOT NULL,
        cpf TEXT,
        telefone TEXT,
        endereco TEXT,
        email TEXT,
        observacoes TEXT,
        ativo INTEGER NOT NULL DEFAULT 1,
        criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS usuarios (
        id SERIAL PRIMARY KEY,
        nome TEXT NOT NULL,
        usuario TEXT NOT NULL UNIQUE,
        senha_hash TEXT NOT NULL,
        senha_salt TEXT NOT NULL,
        perfil TEXT NOT NULL DEFAULT 'Atendente',
        ativo INTEGER NOT NULL DEFAULT 1,
        criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    conn.commit()
    _add_postgres_column_if_missing(cursor, "lancamentos", "produto_id", "INTEGER")
    _add_postgres_column_if_missing(cursor, "lancamentos", "quantidade", "DOUBLE PRECISION")
    _add_postgres_column_if_missing(cursor, "lancamentos", "venda_id", "INTEGER")
    _add_postgres_column_if_missing(cursor, "lancamentos", "venda_item_id", "INTEGER")
    _ensure_postgres_indexes(cursor)
    conn.commit()
    return conn


def execute_insert_returning_id(conn, cursor, query, params):
    if getattr(conn, "backend", "sqlite") == "postgres":
        cursor.execute(f"{query.strip()} RETURNING id", params)
        new_id = cursor.fetchone()[0]
        conn.commit()
        return new_id

    cursor.execute(query, params)
    conn.commit()
    return cursor.lastrowid


def _add_column_if_missing(cursor, table, column, column_type):
    columns = [
        row[1]
        for row in cursor.execute(f"PRAGMA table_info({table})").fetchall()
    ]

    if column not in columns:
        cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {column_type}")


def _add_postgres_column_if_missing(cursor, table, column, column_type):
    cursor.execute(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {column} {column_type}")


def _ensure_postgres_indexes(cursor):
    for query in [
        "CREATE INDEX IF NOT EXISTS idx_lancamentos_data ON lancamentos(data)",
        "CREATE INDEX IF NOT EXISTS idx_lancamentos_tipo ON lancamentos(tipo)",
        "CREATE INDEX IF NOT EXISTS idx_pagamentos_lancamento_id ON pagamentos(lancamento_id)",
        "CREATE INDEX IF NOT EXISTS idx_despesas_data ON despesas(data)",
        "CREATE INDEX IF NOT EXISTS idx_caixa_data ON caixa(data)",
        "CREATE INDEX IF NOT EXISTS idx_ordens_servico_cliente_id ON ordens_servico(cliente_id)",
        "CREATE INDEX IF NOT EXISTS idx_ordens_servico_cpf ON ordens_servico(cpf)",
        "CREATE INDEX IF NOT EXISTS idx_ordens_servico_telefone ON ordens_servico(telefone)",
        "CREATE INDEX IF NOT EXISTS idx_ordens_servico_status ON ordens_servico(status)",
        "CREATE INDEX IF NOT EXISTS idx_estoque_ativo ON estoque(ativo)",
        "CREATE INDEX IF NOT EXISTS idx_clientes_ativo ON clientes(ativo)",
        "CREATE INDEX IF NOT EXISTS idx_usuarios_usuario ON usuarios(usuario)",
    ]:
        cursor.execute(query)
