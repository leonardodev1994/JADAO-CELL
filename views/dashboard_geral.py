import streamlit as st

from utils.db_queries import cached_read_sql
from utils.dashboard_ui import bar_chart, empty_state, metric_card, moeda, page_header, pie_chart


def render_dashboard_geral(conn):
    resumo = cached_read_sql(conn, """
    SELECT
        COALESCE(SUM(valor), 0) AS faturamento,
        COALESCE(SUM(CASE WHEN tipo = 'Serviço' THEN valor ELSE 0 END), 0) AS servicos,
        COALESCE(SUM(CASE WHEN tipo = 'Produto' THEN valor ELSE 0 END), 0) AS produtos,
        COUNT(*) AS quantidade
    FROM lancamentos
    """).iloc[0]
    despesas_df = cached_read_sql(conn, "SELECT COALESCE(SUM(valor), 0) AS total FROM despesas")
    resumo_pag = cached_read_sql(conn, """
    SELECT forma_pagamento, COALESCE(SUM(valor), 0) AS valor
    FROM pagamentos
    GROUP BY forma_pagamento
    ORDER BY valor DESC
    """)
    resumo_tipo = cached_read_sql(conn, """
    SELECT tipo, COALESCE(SUM(valor), 0) AS valor
    FROM lancamentos
    GROUP BY tipo
    ORDER BY valor DESC
    """)
    top = cached_read_sql(conn, """
    SELECT descricao, COALESCE(SUM(valor), 0) AS valor, COUNT(id) AS quantidade
    FROM lancamentos
    GROUP BY descricao
    ORDER BY valor DESC
    LIMIT 8
    """)

    page_header(
        "Dashboard Geral",
        "Visão consolidada do faturamento, mix de vendas e formas de pagamento.",
    )

    faturamento = resumo["faturamento"]
    despesas = despesas_df.iloc[0]["total"] if not despesas_df.empty else 0
    lucro = faturamento - despesas
    servicos = resumo["servicos"]
    produtos = resumo["produtos"]
    quantidade = int(resumo["quantidade"] or 0)

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        metric_card("Faturamento", moeda(faturamento), "Receita total lançada", "#5B8DEF")
    with c2:
        metric_card("Serviços", moeda(servicos), "Reparos e mão de obra", "#18C29C")
    with c3:
        metric_card("Produtos", moeda(produtos), "Produtos vendidos", "#F59E0B")
    with c4:
        metric_card("Lucro estimado", moeda(lucro), f"Despesas: {moeda(despesas)}", "#EF4444")

    st.divider()

    col1, col2 = st.columns(2)

    with col1:
        if resumo_pag.empty:
            empty_state("Nenhum pagamento cadastrado ainda.")
        else:
            st.plotly_chart(
                pie_chart(resumo_pag, "forma_pagamento", "valor", "Formas de pagamento"),
                width="stretch",
            )

    with col2:
        if resumo_tipo.empty:
            empty_state("Nenhum lançamento cadastrado ainda.")
        else:
            st.plotly_chart(
                bar_chart(resumo_tipo, "tipo", "valor", "Serviços x Produtos"),
                width="stretch",
            )

    if quantidade:
        st.divider()
        st.subheader("Itens mais relevantes")
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
