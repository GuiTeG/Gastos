import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import date
import plotly.express as px

# === CONFIGURAÇÃO GOOGLE SHEETS ===
SCOPE = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]

# Lê as credenciais direto do secrets do Streamlit Cloud
creds = Credentials.from_service_account_info(st.secrets["google_service_account"], scopes=SCOPE)
gc = gspread.authorize(creds)
SHEET_NAME = 'Controle finanças'
sheet = gc.open(SHEET_NAME)
WORKSHEET_TRANSACOES = 'Transacoes'
WORKSHEET_CARTOES = 'Cartoes'

worksheet = sheet.worksheet(WORKSHEET_TRANSACOES)

gc = gspread.authorize(creds)
SHEET_NAME = 'Controle finanças'
sheet = gc.open(SHEET_NAME)
WORKSHEET_TRANSACOES = 'Transacoes'
WORKSHEET_CARTOES = 'Cartoes'

worksheet = sheet.worksheet(WORKSHEET_TRANSACOES)

# Cria worksheet Cartoes se não existir
try:
    worksheet_cartoes = sheet.worksheet(WORKSHEET_CARTOES)
except:
    worksheet_cartoes = sheet.add_worksheet(title=WORKSHEET_CARTOES, rows="100", cols="5")
    worksheet_cartoes.append_row(["Nome", "Limite", "Vencimento"])

# === AUXILIARES ===
def normaliza_valor(valor_str):
    if valor_str is None:
        return 0.0
    valor_str = str(valor_str).replace(" ", "").replace(" ", "").strip()
    if "." in valor_str and "," in valor_str:
        valor_str = valor_str.replace(".", "")
        valor_str = valor_str.replace(",", ".")
    elif "," in valor_str:
        valor_str = valor_str.replace(",", ".")
    return float(valor_str)

def formatar_brl(valor):
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def ler_transacoes():
    rows = worksheet.get_all_records()
    for row in rows:
        try:
            row["Valor"] = float(normaliza_valor(row["Valor"]))
        except Exception:
            row["Valor"] = 0.0
    return rows if rows else []

def adicionar_transacao(data_vencimento, data_pagamento, descricao, valor, categoria, tipo, telefone="", pago="N"):
    valor_final = valor if tipo == "Entrada" else -valor
    valor_final_str = "{:.2f}".format(valor_final).replace(",", ".")
    worksheet.append_row([
        str(data_vencimento) if data_vencimento else "",
        str(data_pagamento) if data_pagamento else "",
        descricao,
        valor_final_str,
        categoria,
        tipo,
        telefone,
        pago
    ])

def ler_cartoes():
    rows = worksheet_cartoes.get_all_records()
    return [
        {
            "nome": r.get("Nome"),
            "limite": float(normaliza_valor(r.get("Limite"))),
            "vencimento": int(r.get("Vencimento", 0)) if str(r.get("Vencimento", "")).isdigit() else ""
        }
        for r in rows if r.get("Nome")
    ]

def adicionar_cartao(nome, limite, vencimento):
    worksheet_cartoes.append_row([nome, str(limite), str(vencimento)])

# === DASHBOARD ===
def pagina_dashboard():
    st.header("📊 Dashboard Financeiro Completo")
    df = pd.DataFrame(st.session_state.transacoes)
    if df.empty:
        st.info("Nenhuma transação cadastrada para gerar gráficos.")
        return

    df["Data Vencimento"] = pd.to_datetime(df["Data Vencimento"], errors="coerce")
    hoje = date.today()
    mes_atual = hoje.strftime("%Y-%m")
    df["AnoMes"] = df["Data Vencimento"].dt.strftime("%Y-%m")
    df_mes = df[df["AnoMes"] == mes_atual].copy()

    total_entradas = df[df["Valor"] > 0]["Valor"].sum()
    total_saidas = df[df["Valor"] < 0]["Valor"].sum()
    saldo_atual = df["Valor"].sum()
    entrada_mes = df_mes[df_mes["Valor"] > 0]["Valor"].sum()
    saida_mes = df_mes[df_mes["Valor"] < 0]["Valor"].sum()
    n_transacoes = len(df_mes)

    st.markdown("### Indicadores do Mês Atual")
    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    kpi1.metric("Entradas (mês)", formatar_brl(entrada_mes))
    kpi2.metric("Saídas (mês)", formatar_brl(abs(saida_mes)))
    kpi3.metric("Saldo Atual", formatar_brl(saldo_atual))
    kpi4.metric("Qtde Transações", n_transacoes)

    st.markdown("---")

    st.subheader("Evolução do Saldo Acumulado (Mês Atual)")
    if not df_mes.empty:
        df_mes_sorted = df_mes.sort_values("Data Vencimento")
        df_mes_sorted["Saldo_Acumulado"] = df_mes_sorted["Valor"].cumsum()
        st.plotly_chart(
            px.line(
                df_mes_sorted, x="Data Vencimento", y="Saldo_Acumulado",
                markers=True, title="Evolução Saldo (Mês Atual)"
            ),
            use_container_width=True
        )

    st.subheader("Distribuição dos Gastos por Categoria (Pizza)")
    df_gastos = df_mes[df_mes["Valor"] < 0].copy()
    df_gastos["ValorAbs"] = df_gastos["Valor"].abs()
    if not df_gastos.empty:
        st.plotly_chart(
            px.pie(df_gastos, names="Categoria", values="ValorAbs",
                   title="Gastos por Categoria"),
            use_container_width=True
        )
    else:
        st.info("Sem despesas para mostrar gráfico de gastos por categoria.")

    st.markdown("### Top 5 Maiores Gastos do Mês")
    top5 = df_gastos.sort_values("ValorAbs", ascending=False).head(5) if not df_gastos.empty else pd.DataFrame()
    if not top5.empty:
        st.dataframe(top5[["Data Vencimento", "Descrição", "Categoria", "ValorAbs"]]
            .rename(columns={"ValorAbs": "Valor"})
            .style.format({"Valor": formatar_brl}),
            use_container_width=True
        )
    else:
        st.info("Não há gastos cadastrados neste mês.")

# === APP PRINCIPAL ===
st.set_page_config(page_title="Controle de Finanças", layout="wide")

if "categorias" not in st.session_state:
    st.session_state.categorias = ["Salário", "Alimentação", "Transporte", "Lazer", "Gastos Fixos", "Outros"]
if "pagina" not in st.session_state:
    st.session_state.pagina = "principal"

# Atualização manual dos dados
if "transacoes" not in st.session_state or "cartoes" not in st.session_state:
    st.session_state.transacoes = ler_transacoes()
    st.session_state.cartoes = ler_cartoes()

# Botão de atualização manual
with st.sidebar:
    if st.button("🔄 Atualizar dados do Google Sheets"):
        st.session_state.transacoes = ler_transacoes()
        st.session_state.cartoes = ler_cartoes()
        st.success("Dados atualizados!")

cols = ["Data Vencimento", "Data Pagamento", "Descrição", "Valor", "Categoria", "Tipo", "Telefone", "Pago"]
df_total = pd.DataFrame(st.session_state.transacoes, columns=cols)
valores_numericos = df_total["Valor"] if not df_total.empty else pd.Series(dtype="float")
total_entrada = valores_numericos[valores_numericos > 0].sum() if not df_total.empty else 0
total_saida = valores_numericos[valores_numericos < 0].sum() if not df_total.empty else 0
saldo = valores_numericos.sum() if not df_total.empty else 0

col_esq, col_dir = st.columns([1, 3], gap="large")

# MENU ESQUERDO
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
    if st.button("💳 Cartões"):
        st.session_state.pagina = "cartoes"
        st.rerun()
    if st.button("📊 Dashboard"):
        st.session_state.pagina = "dashboard"
        st.rerun()

    st.markdown("---")
    st.subheader("Resumo")
    st.write(f"**Entradas:** {formatar_brl(total_entrada)}")
    st.write(f"**Saídas:** {formatar_brl(abs(total_saida))}")
    st.write(f"**Saldo Atual:** {formatar_brl(saldo)}")

# CONTEÚDO PRINCIPAL (col_dir)
with col_dir:
    if st.session_state.pagina == "principal":
        st.header("➕ Nova Transação")
        with st.form("form_transacao"):
            data_vencimento = st.date_input("Data de vencimento", value=date.today(), format="DD/MM/YYYY")
            data_pagamento = st.date_input("Data do pagamento (deixe vazio se não foi pago)", value=None, format="DD/MM/YYYY", key="pagamento")
            descricao = st.text_input("Descrição", placeholder="Ex: Mercado, Uber, Conta de luz...")
            valor_str = st.text_input("Valor (R$)", placeholder="Ex: 14,98 ou 1.234,56")
            categoria = st.selectbox("Categoria", st.session_state.categorias)
            tipo = st.radio("Tipo", ["Entrada", "Saída"], horizontal=True)
            telefone = st.text_input("Telefone para aviso (WhatsApp/SMS)", placeholder="Ex: 5511999998888")
            pago = st.radio("Já foi pago?", ["N", "S"], horizontal=True, index=0)
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
                    data_pagamento_str = data_pagamento if pago == "S" or data_pagamento else ""
                    adicionar_transacao(data_vencimento, data_pagamento_str, descricao, valor, categoria, tipo, telefone, pago)
                    st.session_state.transacoes = ler_transacoes()
                    st.success("✨ Transação registrada com sucesso!")
                    st.rerun()

    elif st.session_state.pagina == "historico":
        st.header("📋 Histórico de Transações")
        if st.session_state.transacoes:
            df = pd.DataFrame(st.session_state.transacoes, columns=cols)
            df["Valor"] = df["Valor"].apply(lambda x: float(normaliza_valor(x)))
            df["Data Vencimento"] = pd.to_datetime(df["Data Vencimento"], errors="coerce")
            df = df.sort_values(by="Data Vencimento", ascending=False).reset_index(drop=True)
            busca = st.text_input("🔎 Buscar por descrição ou categoria")
            df_filtrado = df.copy()
            if busca:
                mask = df_filtrado["Descrição"].str.contains(busca, case=False) | df_filtrado["Categoria"].str.contains(busca, case=False)
                df_filtrado = df_filtrado[mask]
            st.dataframe(df_filtrado, use_container_width=True)
        else:
            st.info("Nenhuma transação cadastrada.")

    elif st.session_state.pagina == "remover":
        st.header("🗑️ Remover Transações em Lote")
        if not st.session_state.transacoes:
            st.info("Nenhuma transação cadastrada para remover.")
        else:
            df = pd.DataFrame(st.session_state.transacoes, columns=cols)
            df["Valor"] = df["Valor"].apply(lambda x: float(normaliza_valor(x)))
            df["Data Vencimento"] = pd.to_datetime(df["Data Vencimento"], errors="coerce")
            df = df.sort_values(by="Data Vencimento", ascending=False).reset_index(drop=True)
            if "selecionados_remover" not in st.session_state or len(st.session_state.selecionados_remover) != len(df):
                st.session_state.selecionados_remover = [False] * len(df)

            st.write("Marque as transações que deseja remover e clique em **Excluir selecionadas**.")

            for i, row in df.iterrows():
                col1, col2 = st.columns([7, 1])
                with col1:
                    data_venc = row['Data Vencimento']
                    if pd.notnull(data_venc):
                        try:
                            data_venc_str = data_venc.strftime('%d/%m/%Y')
                        except Exception:
                            data_venc_str = str(data_venc)
                    else:
                        data_venc_str = "-"
                    st.write(f"{data_venc_str} | {row['Descrição']} | {row['Categoria']} | {formatar_brl(row['Valor'])} | {row['Telefone']} | {'Pago' if row['Pago'] in ['S', 'Sim', '1'] else 'Não Pago'}")
                with col2:
                    st.session_state.selecionados_remover[i] = st.checkbox(
                        "", value=st.session_state.selecionados_remover[i], key=f"cb_remover_{i}"
                    )

            if st.button("🗑️ Excluir selecionadas"):
                indices_a_remover = [i for i, marcado in enumerate(st.session_state.selecionados_remover) if marcado]
                if not indices_a_remover:
                    st.warning("Selecione ao menos uma transação para remover.")
                else:
                    all_rows = worksheet.get_all_values()[1:]  # Ignora cabeçalho
                    removidos = 0
                    debug_msgs = []
                    for idx_df in sorted(indices_a_remover, reverse=True):
                        transacao_df = {
                            "Data Vencimento": str(df.iloc[idx_df]["Data Vencimento"].date() if pd.notnull(df.iloc[idx_df]["Data Vencimento"]) else ""),
                            "Descrição": str(df.iloc[idx_df]["Descrição"]).strip(),
                            "Valor": "{:.2f}".format(float(df.iloc[idx_df]["Valor"])).replace(",", "."),
                            "Categoria": str(df.iloc[idx_df]["Categoria"]).strip(),
                            "Tipo": str(df.iloc[idx_df]["Tipo"]).strip(),
                            "Telefone": str(df.iloc[idx_df]["Telefone"]).strip(),
                            "Pago": str(df.iloc[idx_df]["Pago"]).strip()
                        }
                        found = False
                        for row_num, row_values in enumerate(all_rows, start=2):
                            # Monta dict para a linha do Sheets
                            row_check = {
                                "Data Vencimento": str(row_values[0]).strip(),
                                "Descrição": str(row_values[2]).strip(),
                                "Valor": str(float(normaliza_valor(row_values[3]))),
                                "Categoria": str(row_values[4]).strip(),
                                "Tipo": str(row_values[5]).strip(),
                                "Telefone": str(row_values[6]).strip(),
                                "Pago": str(row_values[7]).strip(),
                            }
                            cmp = (
                                row_check["Data Vencimento"] == transacao_df["Data Vencimento"] and
                                row_check["Descrição"] == transacao_df["Descrição"] and
                                abs(float(row_check["Valor"]) - float(transacao_df["Valor"])) < 0.01 and
                                row_check["Categoria"] == transacao_df["Categoria"] and
                                row_check["Tipo"] == transacao_df["Tipo"] and
                                row_check["Telefone"] == transacao_df["Telefone"] and
                                row_check["Pago"] == transacao_df["Pago"]
                            )
                            if cmp:
                                worksheet.delete_rows(row_num)
                                removidos += 1
                                all_rows.pop(row_num-2)
                                found = True
                                break
                        if not found:
                            debug_msgs.append(
                                f"\nLinha no sheets: {row_check}\nLinha no DataFrame: {transacao_df}\n"
                            )
                    if removidos > 0:
                        st.success(f"{removidos} transação(ões) removida(s) com sucesso!")
                    else:
                        st.warning("Nenhuma transação foi removida. Veja debug abaixo para ajustar campos:\n" + "".join(debug_msgs))
                    st.session_state.transacoes = ler_transacoes()
                    st.session_state.selecionados_remover = []
                    st.rerun()

    elif st.session_state.pagina == "dashboard":
        pagina_dashboard()

    elif st.session_state.pagina == "cartoes":
        st.header("💳 Controle de Cartões de Crédito")

        st.subheader("Cadastrar novo cartão")
        with st.form("form_cartao"):
            nome_cartao = st.text_input("Nome do cartão")
            limite_cartao = st.text_input("Limite do cartão (R$)", placeholder="Ex: 2000,00")
            vencimento = st.number_input("Dia do vencimento", min_value=1, max_value=31, step=1, format="%d")
            submitted_cartao = st.form_submit_button("Cadastrar cartão")
            if submitted_cartao:
                if not nome_cartao or not limite_cartao or not vencimento:
                    st.warning("Preencha todos os campos do cartão.")
                else:
                    adicionar_cartao(nome_cartao, normaliza_valor(limite_cartao), vencimento)
                    st.session_state.cartoes = ler_cartoes()
                    st.success(f"Cartão '{nome_cartao}' cadastrado!")
                    st.rerun()

        st.subheader("Seus cartões")
        if st.session_state.cartoes:
            cartoes_df = pd.DataFrame(st.session_state.cartoes)
            cartoes_df.columns = [c.lower() for c in cartoes_df.columns]
            for idx, row in cartoes_df.iterrows():
                col1, col2, col3, col4 = st.columns([3, 2, 2, 1])
                with col1:
                    st.write(f"**{row['nome']}**")
                with col2:
                    st.write(f"Limite: {formatar_brl(row['limite'])}")
                with col3:
                    venc_txt = int(row['vencimento']) if row.get('vencimento') not in (None, "", 0) else "-"
                    st.write(f"Vencimento: {venc_txt}")
                with col4:
                    if st.button("🗑️ Excluir", key=f"excluir_cartao_{idx}"):
                        todas = worksheet_cartoes.get_all_records()
                        for i, c in enumerate(todas, start=2):
                            venc_sheet = c.get("Vencimento") or c.get("vencimento") or ""
                            if (c.get("Nome") == row["nome"] and 
                                float(normaliza_valor(c.get("Limite",0))) == row["limite"] and 
                                str(venc_sheet) == str(row.get("vencimento", ""))):
                                worksheet_cartoes.delete_rows(i)
                                break
                        st.session_state.cartoes = ler_cartoes()
                        st.success(f"Cartão '{row['nome']}' removido!")
                        st.rerun()
        else:
            st.info("Nenhum cartão cadastrado.")

        st.subheader("Registrar compra no cartão")
        cartoes = [c["nome"] for c in st.session_state.get("cartoes",[])]
        if cartoes:
            with st.form("form_compra_cartao"):
                cartao = st.selectbox("Selecione o cartão", cartoes)
                valor = st.text_input("Valor da compra (R$)", placeholder="Ex: 299,90")
                descricao = st.text_input("Descrição da compra")
                data_compra = st.date_input("Data da compra", value=date.today())
                parcelas = st.number_input("Parcelas", min_value=1, max_value=24, value=1, step=1)
                telefone = st.text_input("Telefone para aviso (WhatsApp/SMS)", placeholder="Ex: 5511999998888")
                pago = st.radio("Já foi pago?", ["N", "S"], horizontal=True, index=0)
                submit_compra = st.form_submit_button("Adicionar compra")
                if submit_compra:
                    if not cartao or not valor or not descricao:
                        st.warning("Preencha todos os campos da compra.")
                    else:
                        adicionar_transacao(
                            data_compra,
                            data_compra if pago == "S" else "",
                            descricao,
                            float(normaliza_valor(valor)),
                            cartao,
                            "Saída",
                            telefone,
                            pago
                        )
                        st.session_state.transacoes = ler_transacoes()
                        st.success("Compra lançada com sucesso!")
                        st.rerun()
        else:
            st.info("Cadastre ao menos um cartão antes de registrar compras.")

        df = pd.DataFrame(st.session_state.transacoes, columns=cols)
        if not df.empty and cartoes:
            df["Valor"] = df["Valor"].apply(lambda x: float(normaliza_valor(x)))
            df["Data Vencimento"] = pd.to_datetime(df["Data Vencimento"], errors="coerce")
            df["mes_ano"] = df["Data Vencimento"].dt.strftime("%m/%Y")
            df = df[df["Tipo"] == "Saída"]

            for cartao in cartoes:
                cartao_info = next((c for c in st.session_state.cartoes if c["nome"] == cartao), {})
                venc = cartao_info.get("vencimento")
                st.header(f"Cartão: {cartao}")
                if venc:
                    st.markdown(
                        f"<span style='font-size:0.95em;color:#666;'>Vencimento da fatura: dia <b>{venc}</b></span>",
                        unsafe_allow_html=True
                    )
                for mesano in sorted(df["mes_ano"].unique(), reverse=True):
                    df_mes = df[(df["Categoria"] == cartao) & (df["mes_ano"] == mesano)]
                    if not df_mes.empty:
                        total = df_mes["Valor"].sum()
                        st.subheader(f"{mesano} | Total: {formatar_brl(total)}")
                        st.table(df_mes[["Data Vencimento", "Descrição", "Valor"]].sort_values("Data Vencimento"))
        else:
            st.info("Nenhuma transação de cartão cadastrada ainda.")

