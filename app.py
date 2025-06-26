import streamlit as st
import pandas as pd
from pagina_dashboard import pagina_dashboard
from datetime import date, timedelta

st.set_page_config(page_title="Controle de Finanças", layout="wide")

def formatar_brl(valor):
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

if "categorias" not in st.session_state:
    st.session_state.categorias = ["Salário", "Alimentação", "Transporte", "Lazer", "Gastos Fixos", "Outros"]
if "transacoes" not in st.session_state:
    st.session_state.transacoes = []
if "pagina" not in st.session_state:
    st.session_state.pagina = "principal"

# --- KPIs ---
cols = ["Data", "Descrição", "Valor", "Categoria", "Tipo"]
df_total = pd.DataFrame(st.session_state.transacoes, columns=cols)
total_entrada = df_total[df_total["Valor"] > 0]["Valor"].sum() if not df_total.empty else 0
total_saida = df_total[df_total["Valor"] < 0]["Valor"].sum() if not df_total.empty else 0
saldo = df_total["Valor"].sum() if not df_total.empty else 0

# --- LAYOUT: 2 colunas (menu/kpi | formulário) ---
col_esq, col_dir = st.columns([1, 3], gap="large")

with col_esq:
    # --- MENU lateral: só botões simples padrão Streamlit ---
    if  st.button("🏠 Principal"):
        st.session_state.pagina = "principal"
        st.rerun()
    if  st.button("📋 Histórico"):
        st.session_state.pagina = "historico"
        st.rerun()
    if  st.button("🗑️ Remover"):
        st.session_state.pagina = "remover"
        st.rerun()
    if  st.button("📊 Dashboard"):
        st.session_state.pagina = "dashboard"
        st.rerun()

    st.markdown("---")
    st.subheader("Resumo")
    st.write(f"**Entradas:** {formatar_brl(total_entrada)}")
    st.write(f"**Saídas:** {formatar_brl(abs(total_saida))}")
    st.write(f"**Saldo Atual:** {formatar_brl(saldo)}")

with col_dir:
    if st.session_state.pagina == "principal":
        st.header("➕ Nova Transação")
        with st.form("form_transacao"):
            data = st.date_input("Data de Pagamento", value=date.today(), format="DD/MM/YYYY")
            descricao = st.text_input("Descrição", placeholder="Ex: Mercado, Uber, Conta de luz...")
            valor = st.number_input("Valor (R$)", min_value=0.01, step=0.01, format="%.2f")
            categoria = st.selectbox("Categoria", st.session_state.categorias)
            tipo = st.radio("Tipo", ["Entrada", "Saída"], horizontal=True)
            enviar = st.form_submit_button("Adicionar")
            if enviar:
                if not descricao:
                    st.warning("Preencha a descrição da transação.")
                elif valor <= 0:
                    st.warning("Valor deve ser maior que zero.")
                else:
                    st.session_state.transacoes.append({
                        "Data": data,
                        "Descrição": descricao,
                        "Valor": valor if tipo == "Entrada" else -valor,
                        "Categoria": categoria,
                        "Tipo": tipo
                    })
                    st.success("✨ Transação registrada com sucesso!")
                    st.rerun()
    elif st.session_state.pagina == "historico":
        st.header("📋 Histórico de Transações")
        if st.session_state.transacoes:
            df = pd.DataFrame(st.session_state.transacoes, columns=cols)
            df["Data"] = pd.to_datetime(df["Data"])
            df = df.sort_values(by="Data", ascending=False).reset_index(drop=True)
            busca = st.text_input("🔎 Buscar por descrição ou categoria")
            df_filtrado = df.copy()
            if busca:
                mask = df_filtrado["Descrição"].str.contains(busca, case=False) | df_filtrado["Categoria"].str.contains(busca, case=False)
                df_filtrado = df_filtrado[mask]
            st.dataframe(df_filtrado, use_container_width=True)
        else:
            st.info("Nenhuma transação cadastrada.")
    elif st.session_state.pagina == "remover":
        st.header("🗑️ Remover Transação")
        if not st.session_state.transacoes:
            st.info("Nenhuma transação cadastrada para remover.")
        else:
            df = pd.DataFrame(st.session_state.transacoes, columns=cols)
            df["Data"] = pd.to_datetime(df["Data"])
            df = df.sort_values(by="Data", ascending=False).reset_index(drop=True)
            for i, row in df.iterrows():
                col1, col2 = st.columns([6, 1])
                with col1:
                    st.write(f"{row['Data'].strftime('%d/%m/%Y')} | {row['Descrição']} | {row['Categoria']} | {formatar_brl(row['Valor'])}")
                with col2:
                    if st.button("Remover", key=f"remove_{i}_{row['Data']}_{row['Descrição']}"):
                        for idx, item in enumerate(st.session_state.transacoes):
                            if (item['Data'] == row['Data'].date() and 
                                item['Descrição'] == row['Descrição'] and 
                                item['Valor'] == row['Valor'] and
                                item['Categoria'] == row['Categoria'] and
                                item['Tipo'] == row['Tipo']):
                                st.session_state.transacoes.pop(idx)
                                st.success("Transação removida com sucesso!")
                                st.rerun()
                                break
    elif st.session_state.pagina == "dashboard":
                          pagina_dashboard()