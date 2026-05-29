from datetime import datetime
from datetime import timedelta

import pandas as pd
import streamlit as st

from utils.db_queries import cached_read_sql
from utils.dashboard_ui import bar_chart, empty_state, metric_card, moeda, page_header, pie_chart


def _date_bounds(conn):
    hoje = datetime.today().date()
    bounds = cached_read_sql(conn, """
    SELECT MIN(data) AS min_data, MAX(data) AS max_data
    FROM lancamentos
    """)
    if bounds.empty or not bounds.iloc[0]["min_data"]:
        return hoje.replace(day=1), hoje

    min_date = pd.to_datetime(bounds.iloc[0]["min_data"], errors="coerce")
    max_date = pd.to_datetime(bounds.iloc[0]["max_data"], errors="coerce")
    if pd.isna(min_date) or pd.isna(max_date):
        return hoje.replace(day=1), hoje

    return min_date.date(), max(max_date.date(), hoje)


def _month_start(date_value):
    return date_value.replace(day=1)


def _next_month(date_value):
    if date_value.month == 12:
        return date_value.replace(year=date_value.year + 1, month=1, day=1)
    return date_value.replace(month=date_value.month + 1, day=1)


def _period_label(start, end):
    return f"{start.strftime('%d/%m/%Y')} até {end.strftime('%d/%m/%Y')}"


def render_dashboard_mensal(conn):
    min_date, max_date = _date_bounds(conn)

    modo = st.segmented_control(
        "Tipo de análise",
        ["Mês fechado", "Período personalizado"],
        default="Mês fechado",
    )

    if modo == "Mês fechado":
        meses = pd.date_range(_month_start(min_date), _month_start(max_date), freq="MS")
        opcoes = [mes.date() for mes in meses]
        labels = {mes: mes.strftime("%m/%Y") for mes in opcoes}
        selected_month = st.selectbox(
            "Escolha o mês",
            opcoes,
            format_func=lambda value: labels[value],
            index=len(opcoes) - 1 if opcoes else 0,
        )
        start_date = selected_month
        end_date = _next_month(selected_month) - timedelta(days=1)
    else:
        start_date, end_date = st.date_input(
            "Escolha o período",
            value=(min_date, max_date),
            min_value=min_date,
            max_value=max_date,
        )

    page_header(
        "Dashboard Mensal",
        f"Visão financeira e comercial: {_period_label(start_date, end_date)}",
    )

    start_sql = start_date.strftime("%Y-%m-%d")
    end_sql = end_date.strftime("%Y-%m-%d")
    resumo = cached_read_sql(conn, """
    SELECT
        COUNT(*) AS quantidade,
        COALESCE(SUM(valor), 0) AS faturamento,
        COALESCE(SUM(CASE WHEN tipo = 'Serviço' THEN valor ELSE 0 END), 0) AS servicos,
        COALESCE(SUM(CASE WHEN tipo = 'Produto' THEN valor ELSE 0 END), 0) AS produtos
    FROM lancamentos
    WHERE data BETWEEN ? AND ?
    """, (start_sql, end_sql)).iloc[0]

    if not int(resumo["quantidade"] or 0):
        empty_state("Nenhum lançamento cadastrado ainda.")
        return

    despesas_df = cached_read_sql(conn, """
    SELECT COALESCE(SUM(valor), 0) AS total
    FROM despesas
    WHERE data BETWEEN ? AND ?
    """, (start_sql, end_sql))

    faturamento = resumo["faturamento"]
    despesas = despesas_df.iloc[0]["total"] if not despesas_df.empty else 0
    lucro = faturamento - despesas
    servicos = resumo["servicos"]
    produtos = resumo["produtos"]

    dias_periodo = max((end_date - start_date).days + 1, 1)
    media_dia = faturamento / dias_periodo
    projecao = media_dia * 30

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        metric_card("Faturamento", moeda(faturamento), f"Média/dia: {moeda(media_dia)}", "#5B8DEF")
    with c2:
        metric_card("Serviços", moeda(servicos), "Receita de reparos", "#18C29C")
    with c3:
        metric_card("Produtos", moeda(produtos), "Receita de vendas", "#F59E0B")
    with c4:
        metric_card("Lucro estimado", moeda(lucro), f"Projeção 30d: {moeda(projecao)}", "#EF4444")

    st.divider()

    diario = cached_read_sql(conn, """
    SELECT data AS dia, COALESCE(SUM(valor), 0) AS valor
    FROM lancamentos
    WHERE data BETWEEN ? AND ?
    GROUP BY data
    ORDER BY data
    """, (start_sql, end_sql))
    if not diario.empty:
        diario["dia"] = pd.to_datetime(diario["dia"], errors="coerce").dt.strftime("%d/%m")
    tipo = cached_read_sql(conn, """
    SELECT tipo, COALESCE(SUM(valor), 0) AS valor
    FROM lancamentos
    WHERE data BETWEEN ? AND ?
    GROUP BY tipo
    ORDER BY valor DESC
    """, (start_sql, end_sql))
    top = cached_read_sql(conn, """
    SELECT descricao, COALESCE(SUM(valor), 0) AS valor, COUNT(id) AS quantidade
    FROM lancamentos
    WHERE data BETWEEN ? AND ?
    GROUP BY descricao
    ORDER BY valor DESC
    LIMIT 10
    """, (start_sql, end_sql))

    col1, col2 = st.columns(2)
    with col1:
        st.plotly_chart(
            bar_chart(diario, "dia", "valor", "Faturamento por dia"),
            width="stretch",
        )
    with col2:
        st.plotly_chart(
            pie_chart(tipo, "tipo", "valor", "Serviços x Produtos"),
            width="stretch",
        )

    st.divider()

    col1, col2 = st.columns([1.2, 1])
    with col1:
        st.subheader("Mais vendidos / maior faturamento")
        st.dataframe(
            top.rename(columns={
                "descricao": "Descrição",
                "valor": "Faturamento",
                "quantidade": "Quantidade",
            }),
            width="stretch",
            hide_index=True,
            column_config={
                "Faturamento": st.column_config.NumberColumn("Faturamento", format="R$ %.2f"),
            },
        )
    with col2:
        st.plotly_chart(
            bar_chart(top, "valor", "descricao", "Top itens"),
            width="stretch",
        )
