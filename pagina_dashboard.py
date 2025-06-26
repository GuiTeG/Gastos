import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import date

def formatar_brl(valor):
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def pagina_dashboard():
    st.header("📊 Dashboard Financeiro Completo")

    df = pd.DataFrame(st.session_state.transacoes)
    if df.empty:
        st.info("Nenhuma transação cadastrada para gerar gráficos.")
        return

    df["Data"] = pd.to_datetime(df["Data"])
    hoje = date.today()
    mes_atual = hoje.strftime("%Y-%m")
    df["AnoMes"] = df["Data"].dt.strftime("%Y-%m")
    df_mes = df[df["AnoMes"] == mes_atual].copy()

    # Indicadores principais
    total_entradas = df[df["Categoria"]=="Salário"]["Valor"].sum()
    total_saidas = df[df["Categoria"]!="Salário"]["Valor"].sum()
    saldo_atual = df["Valor"].sum()
    entrada_mes = df_mes[df_mes["Categoria"]=="Salário"]["Valor"].sum()
    saida_mes = df_mes[df_mes["Categoria"]!="Salário"]["Valor"].sum()
    saldo_mes = df_mes["Valor"].sum()
    n_transacoes = len(df_mes)
    dias_mes = df_mes["Data"].dt.date.nunique()
    media_diaria_gasto = abs(saida_mes) / dias_mes if dias_mes else 0
    receita_extra = df_mes[(df_mes["Valor"]>0) & (df_mes["Categoria"]!="Salário")]["Valor"].sum()
    saldo_diario = df_mes.groupby(df_mes["Data"].dt.date)["Valor"].sum().cumsum()
    saldo_medio = saldo_diario.mean() if not saldo_diario.empty else 0

    # Dias sem gasto
    dias_com_gasto = df_mes[df_mes["Valor"]<0]["Data"].dt.date.unique()
    dias_do_mes = pd.date_range(df_mes["Data"].min(), df_mes["Data"].max()) if not df_mes.empty else []
    dias_sem_gasto = len(set([d.date() for d in dias_do_mes]) - set(dias_com_gasto)) if len(dias_do_mes)>0 else 0

    # Maior gasto em um único dia
    if not df_mes.empty:
        gasto_dia = df_mes[df_mes["Valor"]<0].groupby(df_mes["Data"].dt.date)["Valor"].sum().abs()
        maior_gasto_dia = gasto_dia.max() if not gasto_dia.empty else 0
        dia_maior_gasto = gasto_dia.idxmax() if not gasto_dia.empty else ""
    else:
        maior_gasto_dia = 0
        dia_maior_gasto = ""

    # Menor gasto do mês
    menor_gasto = df_mes[df_mes["Valor"]<0]["Valor"].min() if not df_mes[df_mes["Valor"]<0].empty else 0

    # Top 5 maiores gastos
    df_gastos = df_mes[df_mes["Valor"] < 0].copy()
    df_gastos["ValorAbs"] = df_gastos["Valor"].abs()
    top5 = df_gastos.sort_values("ValorAbs", ascending=False).head(5) if not df_gastos.empty else pd.DataFrame()

    # Maior gasto por categoria
    if not df_gastos.empty:
        cat_maior = df_gastos.groupby("Categoria")["ValorAbs"].sum().idxmax()
        valor_maior = df_gastos.groupby("Categoria")["ValorAbs"].sum().max()
    else:
        cat_maior = ""
        valor_maior = 0

    # KPIs principais
    st.markdown("### Indicadores do Mês Atual")
    kpi1, kpi2, kpi3, kpi4, kpi5 = st.columns(5)
    kpi1.metric("Salário (Entradas)", formatar_brl(entrada_mes))
    kpi2.metric("Saídas Totais", formatar_brl(abs(saida_mes)))
    kpi3.metric("Saldo Atual", formatar_brl(saldo_atual))
    kpi4.metric("Saldo Médio", formatar_brl(saldo_medio))
    kpi5.metric("Dias sem gasto", dias_sem_gasto)

    st.markdown("---")

    # Gráfico evolução saldo acumulado (linha)
    st.subheader("Evolução do Saldo Acumulado (Mês Atual)")
    if not df_mes.empty:
        df_mes_sorted = df_mes.sort_values("Data")
        df_mes_sorted["Saldo_Acumulado"] = df_mes_sorted["Valor"].cumsum()
        st.plotly_chart(
            px.line(
                df_mes_sorted, x="Data", y="Saldo_Acumulado",
                markers=True, title="Evolução Saldo (Mês Atual)"
            ),
            use_container_width=True
        )

    # Gráfico de barras - Entradas, Receitas Extras e Saídas por mês
    st.subheader("Entradas, Receita Extra e Saídas por Mês")
    df_agg = df.groupby("AnoMes").agg(
        Salario=("Valor", lambda x: x[(x>0) & (df.loc[x.index, 'Categoria']=="Salário")].sum()),
        ReceitaExtra=("Valor", lambda x: x[(x>0) & (df.loc[x.index, 'Categoria']!="Salário")].sum()),
        Saidas=("Valor", lambda x: -x[x<0].sum())
    ).reset_index()
    fig = px.bar(df_agg, x="AnoMes", y=["Salario", "ReceitaExtra", "Saidas"], barmode="group",
                 labels={"value": "Valor (R$)", "variable": "Tipo"}, title="Entradas, Receita Extra e Saídas por mês")
    st.plotly_chart(fig, use_container_width=True)

    # Gráfico pizza - gastos por categoria
    st.subheader("Distribuição dos Gastos por Categoria (Pizza)")
    if not df_gastos.empty:
        st.plotly_chart(
            px.pie(df_gastos, names="Categoria", values="ValorAbs",
                   title="Gastos por Categoria"),
            use_container_width=True
        )
    else:
        st.info("Sem despesas para mostrar gráfico de gastos por categoria.")

    # Top 5 maiores gastos - Tabela bonita
    st.markdown("### Top 5 Maiores Gastos do Mês")
    if not top5.empty:
        st.dataframe(top5[["Data", "Descrição", "Categoria", "ValorAbs"]]
            .rename(columns={"ValorAbs": "Valor"})
            .style.format({"Valor": formatar_brl}),
            use_container_width=True
        )
    else:
        st.info("Não há gastos cadastrados neste mês.")

    # Maior gasto por categoria
    if cat_maior:
        st.info(f"**Maior categoria de gasto:** {cat_maior} ({formatar_brl(valor_maior)})")

    # Transação mais cara do mês
    if not df_gastos.empty:
        tx_mais_cara = df_gastos.loc[df_gastos["ValorAbs"].idxmax()]
        st.caption(f"Maior despesa: {tx_mais_cara['Descrição']} - {formatar_brl(tx_mais_cara['ValorAbs'])} em {tx_mais_cara['Data'].strftime('%d/%m/%Y')}")

    # Gastos por dia da semana
    st.subheader("Gastos por Dia da Semana (Mês Atual)")
    if not df_mes[df_mes["Valor"]<0].empty:
        df_mes["DiaSemana"] = df_mes["Data"].dt.day_name(locale="pt_BR")
        fig_semana = px.bar(
            df_mes[df_mes["Valor"]<0],
            x="DiaSemana", y="Valor", color="Categoria",
            title="Gastos por Dia da Semana",
            labels={"Valor": "Valor (R$)"}
        )
        st.plotly_chart(fig_semana, use_container_width=True)

    # Outros indicadores rápidos
    st.markdown("#### Outros Indicadores")
    colA, colB, colC, colD = st.columns(4)
    colA.metric("Receita Extra", formatar_brl(receita_extra))
    colB.metric("Menor Gasto", formatar_brl(menor_gasto))
    colC.metric("Maior gasto diário", formatar_brl(maior_gasto_dia), f"{dia_maior_gasto}")
    colD.metric("Qtde Transações no mês", n_transacoes)
