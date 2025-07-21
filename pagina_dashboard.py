import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import date
from streamlit_extras.metric_cards import style_metric_cards
from streamlit_lottie import st_lottie
import requests

def mostra_lottie(url, altura=120, key=None):
    try:
        resp = requests.get(url, timeout=5)
        if resp.status_code == 200:
            st_lottie(resp.json(), height=altura, key=key)
    except Exception:
        st.info("Não foi possível carregar a animação.")

def formatar_brl(valor):
    cor = "#24bb4e" if valor > 0 else "#e4002b" if valor < 0 else "#888"
    return f"<span style='color:{cor}; font-weight:700;'>R$ {abs(valor):,.2f}</span>".replace(",", "X").replace(".", ",").replace("X", ".")

def dashboard_financeiro():
    # Carregar df das transações reais
    df = pd.DataFrame(st.session_state.transacoes)

    if df.empty:
        mostra_lottie("https://assets4.lottiefiles.com/packages/lf20_puciaact.json", altura=140)
        st.info("Nenhuma transação cadastrada para gerar gráficos.")
        return

    # Corrigir nome da coluna de data conforme seu app (Data Vencimento ou Data)
    if "Data" in df.columns:
        df["Data"] = pd.to_datetime(df["Data"], errors="coerce")
    elif "Data Vencimento" in df.columns:
        df["Data"] = pd.to_datetime(df["Data Vencimento"], errors="coerce")
    else:
        st.warning("Coluna de data não encontrada.")
        return

    df = df.dropna(subset=["Data"])  # Remove linhas sem data válida

    hoje = date.today()
    mes_atual = hoje.strftime("%Y-%m")
    df["AnoMes"] = df["Data"].dt.strftime("%Y-%m")
    df_mes = df[df["AnoMes"] == mes_atual].copy()

    # Indicadores práticos
    entradas = df[df["Valor"] > 0]["Valor"].sum()
    saidas = df[df["Valor"] < 0]["Valor"].sum()
    saldo_atual = df["Valor"].sum()
    entrada_mes = df_mes[df_mes["Valor"] > 0]["Valor"].sum()
    saida_mes = df_mes[df_mes["Valor"] < 0]["Valor"].sum()
    saldo_mes = df_mes["Valor"].sum()
    qtd_transacoes = len(df_mes)
    maior_gasto = df_mes[df_mes["Valor"] < 0]["Valor"].min() if not df_mes[df_mes["Valor"] < 0].empty else 0

    # Layout visual e bonito
    st.markdown("<h1 style='color:#e4002b;'>💸 Dashboard Financeiro</h1>", unsafe_allow_html=True)
    col_anim, col_kpis = st.columns([1, 3])
    with col_anim:
        mostra_lottie("https://assets4.lottiefiles.com/packages/lf20_puciaact.json", altura=130)

    with col_kpis:
        kpi1, kpi2, kpi3, kpi4 = st.columns(4)
        kpi1.metric("Entradas (Mês)", f"R$ {entrada_mes:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
        kpi2.metric("Saídas (Mês)", f"R$ {abs(saida_mes):,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
        kpi3.metric("Saldo Atual", f"R$ {saldo_atual:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
        kpi4.metric("Transações", qtd_transacoes)
        style_metric_cards(
            background_color="#fffbe7",
            border_left_color="#e4002b",
            border_radius_px=18,
        )

    st.markdown("---")
    st.subheader("📈 Evolução do Saldo Acumulado (Mês Atual)")
    if not df_mes.empty:
        df_mes_sorted = df_mes.sort_values("Data")
        df_mes_sorted["Saldo_Acumulado"] = df_mes_sorted["Valor"].cumsum()
        st.plotly_chart(
            px.line(
                df_mes_sorted, x="Data", y="Saldo_Acumulado",
                markers=True, title="Evolução do Saldo no mês",
            ),
            use_container_width=True
        )

    st.subheader("🍕 Gastos por Categoria (Mês Atual)")
    df_gastos = df_mes[df_mes["Valor"] < 0].copy()
    if not df_gastos.empty:
        df_gastos["ValorAbs"] = df_gastos["Valor"].abs()
        st.plotly_chart(
            px.pie(df_gastos, names="Categoria", values="ValorAbs",
                   title="Gastos por Categoria"),
            use_container_width=True
        )
    else:
        st.info("Sem despesas para mostrar pizza.")

    st.markdown("### Top 5 Maiores Gastos do Mês")
    top5 = df_gastos.sort_values("ValorAbs", ascending=False).head(5) if not df_gastos.empty else pd.DataFrame()
    if not top5.empty:
        st.dataframe(top5[["Data", "Descrição", "Categoria", "ValorAbs"]]
            .rename(columns={"ValorAbs": "Valor"})
            .style.format({"Valor": lambda v: f"R$ {abs(v):,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')}),
            use_container_width=True
        )
    else:
        st.info("Não há gastos cadastrados neste mês.")

    # ... (código anterior permanece igual)

    # Outros KPIs (personalizados e bonitos!)
    st.markdown("#### Outros Indicadores")
    colA, colB = st.columns(2)
    with colA:
        st.markdown(
            """
            <div style='background: #fffbe7; border-radius: 18px; border-left: 7px solid #e4002b; 
            box-shadow: 0 2px 8px #e4002b14; padding: 20px 32px; margin-bottom:16px; min-height:60px'>
                <div style='font-size:1.02em; color:#222; margin-bottom:8px;'>Maior gasto</div>
                <div style='font-size:1.5em; color:#e4002b; font-weight:800;'>R$ {:,.2f}</div>
            </div>
            """.format(abs(maior_gasto)).replace(",", "X").replace(".", ",").replace("X", "."),
            unsafe_allow_html=True
        )

    with colB:
        st.markdown(
            """
            <div style='background: #fffbe7; border-radius: 18px; border-left: 7px solid #24bb4e; 
            box-shadow: 0 2px 8px #24bb4e14; padding: 20px 32px; margin-bottom:16px; min-height:60px'>
                <div style='font-size:1.02em; color:#222; margin-bottom:8px;'>Saldo do mês</div>
                <div style='font-size:1.5em; color:#24bb4e; font-weight:800;'>R$ {:,.2f}</div>
            </div>
            """.format(saldo_mes).replace(",", "X").replace(".", ",").replace("X", "."),
            unsafe_allow_html=True
        )


