import streamlit as st
import pandas as pd
import gspread
import json
from google.oauth2.service_account import Credentials
from pagina_dashboard import pagina_dashboard
from datetime import date



def normaliza_valor(valor_str):
    """
    Garante conversão correta para float (aceita milhar, vírgula, ponto, espaços e float puro).
    """
    if valor_str is None:
        return 0.0
    valor_str = str(valor_str).replace(" ", "").replace(" ", "").strip()
    if "." in valor_str and "," in valor_str:
        valor_str = valor_str.replace(".", "")
        valor_str = valor_str.replace(",", ".")
    elif "," in valor_str:
        valor_str = valor_str.replace(",", ".")
    return valor_str

SCOPE = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]

# LEITURA SEGURA DAS CREDENCIAIS
if "google_service_account" in st.secrets:
    try:
        service_account_info = json.loads(st.secrets["google_service_account"])
    except Exception:
        service_account_info = dict(st.secrets["google_service_account"])
    creds = Credentials.from_service_account_info(service_account_info, scopes=SCOPE)
else:
    creds = Credentials.from_service_account_file('credenciais.json', scopes=SCOPE)

gc = gspread.authorize(creds)
SHEET_NAME = 'Controle finanças'
WORKSHEET_NAME = 'Transacoes'
sheet = gc.open(SHEET_NAME)
worksheet = sheet.worksheet(WORKSHEET_NAME)

def ler_transacoes():
    rows = worksheet.get_all_records()
    for row in rows:
        try:
            # Sempre normalize e converta, independente do que veio
            row["Valor"] = float(normaliza_valor(row["Valor"]))
        except Exception:
            row["Valor"] = 0.0
    return rows if rows else []

def adicionar_transacao(data, descricao, valor, categoria, tipo):
    # SEMPRE salva valor como float com ponto (ex: 14.98)
    valor_final = float(valor) if tipo == "Entrada" else -float(valor)
    worksheet.append_row([str(data), descricao, valor_final, categoria, tipo])

def remover_transacao(row_dict):
    all_rows = worksheet.get_all_records()
    idx = None
    for i, row in enumerate(all_rows, start=2):  # começa em 2 porque linha 1 é header
        try:
            data1 = pd.to_datetime(row.get("Data")).date()
            data2 = pd.to_datetime(row_dict.get("Data")).date()
            desc1 = str(row.get("Descrição")).strip()
            desc2 = str(row_dict.get("Descrição")).strip()
            cat1 = str(row.get("Categoria")).strip()
            cat2 = str(row_dict.get("Categoria")).strip()
            tipo1 = str(row.get("Tipo")).strip()
            tipo2 = str(row_dict.get("Tipo")).strip()
            val1 = float(normaliza_valor(row.get("Valor")))
            val2 = float(normaliza_valor(row_dict.get("Valor")))
            if (
                data1 == data2 and
                desc1 == desc2 and
                cat1 == cat2 and
                tipo1 == tipo2 and
                abs(val1 - val2) < 0.01
            ):
                idx = i
                break
        except Exception as e:
            continue
    if idx:
        worksheet.delete_rows(idx)

def formatar_brl(valor):
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

st.set_page_config(page_title="Controle de Finanças", layout="wide")

if "categorias" not in st.session_state:
    st.session_state.categorias = ["Salário", "Alimentação", "Transporte", "Lazer", "Gastos Fixos", "Outros"]
if "pagina" not in st.session_state:
    st.session_state.pagina = "principal"

# Sempre atualiza transacoes lendo do Sheets
st.session_state.transacoes = ler_transacoes()
cols = ["Data", "Descrição", "Valor", "Categoria", "Tipo"]
df_total = pd.DataFrame(st.session_state.transacoes, columns=cols)

st.write(df_total)

valores_numericos = df_total["Valor"] if not df_total.empty else pd.Series(dtype="float")
total_entrada = valores_numericos[valores_numericos > 0].sum() if not df_total.empty else 0
total_saida = valores_numericos[valores_numericos < 0].sum() if not df_total.empty else 0
saldo = valores_numericos.sum() if not df_total.empty else 0

col_esq, col_dir = st.columns([1, 3], gap="large")

with col_esq:
    if st.button("🏠 Principal"):
        st.session_state.pagina = "principal"
        st.rerun()
    if st.button("📋 Histórico"):
        st.session_state.pagina = "historico"
        st.rerun()
    if st.button("🗑️ Remover"):
        st.session_state.pagina = "remover"
        st.rerun()
    if st.button("📊 Dashboard"):
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
            valor_str = st.text_input("Valor (R$)", placeholder="Ex: 14,98 ou 1.234,56")
            categoria = st.selectbox("Categoria", st.session_state.categorias)
            tipo = st.radio("Tipo", ["Entrada", "Saída"], horizontal=True)
            enviar = st.form_submit_button("Adicionar")
            if enviar:
                valor_str_tratado = normaliza_valor(valor_str)
                try:
                    valor = float(valor_str_tratado)
                except Exception:
                    st.warning("Digite um valor numérico válido (ex: 14,98 ou 1.234,56).")
                    st.stop()
                if not descricao:
                    st.warning("Preencha a descrição da transação.")
                elif valor <= 0:
                    st.warning("Valor deve ser maior que zero.")
                else:
                    adicionar_transacao(data, descricao, valor, categoria, tipo)
                    st.success("✨ Transação registrada com sucesso!")
                    st.rerun()

    elif st.session_state.pagina == "historico":
        st.header("📋 Histórico de Transações")
        if st.session_state.transacoes:
            df = pd.DataFrame(st.session_state.transacoes, columns=cols)
            df["Valor"] = df["Valor"].apply(lambda x: float(normaliza_valor(x)))
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
            df["Valor"] = df["Valor"].apply(lambda x: float(normaliza_valor(x)))
            df["Data"] = pd.to_datetime(df["Data"])
            df = df.sort_values(by="Data", ascending=False).reset_index(drop=True)
            for i, row in df.iterrows():
                col1, col2 = st.columns([6, 1])
                with col1:
                    st.write(f"{row['Data'].strftime('%d/%m/%Y')} | {row['Descrição']} | {row['Categoria']} | {formatar_brl(row['Valor'])}")
                with col2:
                    if st.button("Remover", key=f"remove_{i}_{row['Data']}_{row['Descrição']}"):
                        remover_transacao(row)
                        st.success("Transação removida com sucesso!")
                        st.rerun()

    elif st.session_state.pagina == "dashboard":
        pagina_dashboard()
