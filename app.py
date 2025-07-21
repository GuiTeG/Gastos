import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import date
import plotly.express as px
from pagina_dashboard import dashboard_financeiro
from streamlit_option_menu import option_menu
from streamlit_extras.metric_cards import style_metric_cards
from streamlit_lottie import st_lottie
import requests

# ===================== CSS Premium ==========================
st.set_page_config(page_title="Controle de Finanças", layout="wide")
st.markdown("""
<style>
.main-card {
    background: #fff;
    border-radius: 18px;
    box-shadow: 0 2px 12px #e4002b18;
    padding: 24px 24px 8px 24px;
    margin-bottom: 28px;
}
.form-beauty input, .form-beauty textarea, .form-beauty select {
    background: #fafbfd !important;
    border: 1.4px solid #ececec !important;
    border-radius: 10px !important;
    font-size: 1.07em !important;
    padding: 11px 14px !important;
    margin-bottom: 9px !important;
    transition: border .2s;
}
.form-beauty input:focus, .form-beauty select:focus, .form-beauty textarea:focus {
    border-color: #e4002b !important;
    outline: none !important;
    box-shadow: 0 0 0 2px #e4002b22 !important;
}
.form-beauty label {
    color: #e4002b !important;
    font-weight: 700 !important;
    font-size: 1.08em;
    margin-bottom: 2px !important;
}
div[data-testid="stForm"] {
    border-radius: 16px !important;
    border: 1.2px solid #ececec !important;
    box-shadow: 0 2px 20px #e4002b12 !important;
    padding: 2.2em 2.2em 1.5em 2.2em !important;
    margin-bottom: 26px !important;
    background: #fff !important;
}
.stRadio [role="radiogroup"] label {
    margin-right: 22px;
    font-weight: 600;
    font-size: 1.06em;
}
.stRadio [data-baseweb="radio"] svg {
    color: #e4002b !important;
}
button[kind="secondary"], button[title="Adicionar"] {
    border-radius: 9px !important;
    border: 1.2px solid #e4002b !important;
    background: #e4002b !important;
    color: #fff !important;
    font-weight: 700 !important;
    padding: 9px 28px !important;
    margin-top: 7px;
    transition: background .2s;
    font-size: 1.09em !important;
}
button[kind="secondary"]:hover, button[title="Adicionar"]:hover {
    background: #24bb4e !important;
    color: #fff !important;
}
input::placeholder, textarea::placeholder {
    color: #bcbcbc !important;
    font-size: 1em;
}
</style>
""", unsafe_allow_html=True)

# ========== Função Lottie ==========
def mostra_lottie(url, altura=120, key=None):
    try:
        resp = requests.get(url, timeout=5)
        if resp.status_code == 200:
            st_lottie(resp.json(), height=altura, key=key)
        else:
            st.info("Não foi possível carregar a animação.")
    except Exception:
        st.info("Não foi possível carregar a animação.")

# ========== GOOGLE SHEETS ==========
SCOPE = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]
creds = Credentials.from_service_account_file("credenciais.json", scopes=SCOPE)
gc = gspread.authorize(creds)
SHEET_NAME = 'Controle finanças'
WORKSHEET_TRANSACOES = 'Transacoes'
WORKSHEET_CARTOES = 'Cartoes'
sheet = gc.open(SHEET_NAME)
worksheet = sheet.worksheet(WORKSHEET_TRANSACOES)
try:
    worksheet_cartoes = sheet.worksheet(WORKSHEET_CARTOES)
except:
    worksheet_cartoes = sheet.add_worksheet(title=WORKSHEET_CARTOES, rows="100", cols="5")
    worksheet_cartoes.append_row(["Nome", "Limite", "Vencimento"])

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
    cor = "#24bb4e" if valor > 0 else "#e4002b" if valor < 0 else "#666"
    return f"<span style='color:{cor}; font-weight:700;'>R$ {abs(valor):,.2f}</span>".replace(",", "X").replace(".", ",").replace("X", ".")

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

# ======================= SIDEBAR ============================
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/3135/3135715.png", width=64)
    selecionado = option_menu(
        menu_title="",
        options=["Principal", "Histórico", "Remover", "Cartões", "Dashboard"],
        icons=["house", "list-task", "trash", "credit-card", "bar-chart"],
        default_index=0,
        orientation="vertical",
        styles={
            "nav-link-selected": {"background-color": "#e4002b", "font-weight": "bold", "color": "white"},
            "icon": {"font-size": "1.1em"},
        }
    )
    st.caption("💸 Feito por Guilherme")

if "categorias" not in st.session_state:
    st.session_state.categorias = ["Salário", "Alimentação", "Transporte", "Lazer", "Gastos Fixos", "Outros"]
if "pagina" not in st.session_state:
    st.session_state.pagina = selecionado

if "transacoes" not in st.session_state or "cartoes" not in st.session_state:
    st.session_state.transacoes = ler_transacoes()
    st.session_state.cartoes = ler_cartoes()

if st.session_state.pagina != selecionado:
    st.session_state.pagina = selecionado
    st.rerun()

cols = ["Data Vencimento", "Data Pagamento", "Descrição", "Valor", "Categoria", "Tipo", "Telefone", "Pago"]

# ===================== TELA PRINCIPAL ======================
if st.session_state.pagina == "Principal":
    with st.container():
        st.markdown('<div class="main-card">', unsafe_allow_html=True)
        st.markdown("### <b>Adicione uma Nova Transação</b>", unsafe_allow_html=True)
        col_form, col_painel = st.columns([2,1])
        with col_form:
            with st.form("form_transacao"):
                st.markdown('<div class="form-beauty">', unsafe_allow_html=True)
                data_vencimento = st.date_input("📅 Data de vencimento", value=date.today(), format="DD/MM/YYYY")
                data_pagamento = st.date_input("💸 Data do pagamento (opcional)", value=None, format="DD/MM/YYYY", key="pagamento")
                descricao = st.text_input("✏️ Descrição", placeholder="Ex: Mercado, Uber, Conta de luz...")
                valor_str = st.text_input("💰 Valor (R$)", placeholder="Ex: 14,98 ou 1.234,56")
                categoria = st.selectbox("📂 Categoria", st.session_state.categorias)
                tipo = st.radio("Movimento", ["Entrada", "Saída"], horizontal=True)
                telefone = st.text_input("📱 Telefone para aviso (WhatsApp/SMS)", placeholder="Ex: 5511999998888")
                pago = st.radio("Já foi pago?", ["N", "S"], horizontal=True, index=0)
                enviar = st.form_submit_button("➕ Adicionar")
                st.markdown('</div>', unsafe_allow_html=True)

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
        with col_painel:
            mostra_lottie("https://assets10.lottiefiles.com/packages/lf20_vnikrcia.json", altura=120, key="cadastro")
            st.markdown("Preencha os campos ao lado para adicionar uma nova transação.")

            df_total = pd.DataFrame(st.session_state.transacoes)
            if not df_total.empty:
                nomes_cartoes = [c["nome"] for c in st.session_state.cartoes]
                saldo_geral = df_total[
                    (df_total['Tipo'].isin(['Entrada', 'Saída'])) &
                    (~df_total['Categoria'].isin(nomes_cartoes))
                ]['Valor'].sum()
            else:
                saldo_geral = 0

            if not df_total.empty and st.session_state.cartoes:
                total_cartoes = df_total[df_total["Categoria"].isin(nomes_cartoes)]["Valor"].sum()
            else:
                total_cartoes = 0

            if not df_total.empty:
                df_total["Data Vencimento"] = pd.to_datetime(df_total["Data Vencimento"], errors="coerce")
                mes_atual = date.today().strftime("%Y-%m")
                df_mes = df_total[
                    (df_total["Data Vencimento"].dt.strftime("%Y-%m") == mes_atual) &
                    (~df_total["Categoria"].isin(nomes_cartoes))
                ]
                entrada_mes = df_mes[df_mes["Valor"] > 0]["Valor"].sum()
                saida_mes = df_mes[df_mes["Valor"] < 0]["Valor"].sum()
            else:
                entrada_mes = 0
                saida_mes = 0

            st.markdown("---")
            st.markdown(
                f"""
                <div style='font-size:1.13rem; margin-bottom:0.6em;'><b>Saldo Atual (sem cartões):</b>
                    <span style='color:#24bb4e;font-weight:700;'>R$ {saldo_geral:,.2f}</span>
                </div>
                <div style='font-size:1.05rem; margin-bottom:0.2em;'><b>Entrada (mês):</b>
                    <span style='color:#24bb4e;font-weight:700;'>R$ {entrada_mes:,.2f}</span>
                </div>
                <div style='font-size:1.05rem; margin-bottom:0.4em;'><b>Saída (mês):</b>
                    <span style='color:#e4002b;font-weight:700;'>R$ {abs(saida_mes):,.2f}</span>
                </div>
                <div style='font-size:1.09rem;'><b>Total em Cartão de Crédito:</b>
                    <span style='color:#e4002b;font-weight:700;'>R$ {abs(total_cartoes):,.2f}</span>
                </div>
                """,
                unsafe_allow_html=True,
            )
        st.markdown('</div>', unsafe_allow_html=True)

# ================= HISTÓRICO =================
elif st.session_state.pagina == "Histórico":
    st.markdown("""
        <style>
        .transacao-card {
            background: #fff;
            border-radius: 14px;
            box-shadow: 0 1px 8px #e4002b22;
            padding: 18px 24px;
            margin-bottom: 24px;
            border-left: 6px solid #e4002b22;
            display: flex;
            align-items: center;
            justify-content: space-between;
            transition: box-shadow 0.2s;
        }
        .transacao-card.entrada { border-left: 6px solid #24bb4e; }
        .transacao-card.saida   { border-left: 6px solid #e4002b; }
        .transacao-chip {
            display: inline-block;
            padding: 3px 12px;
            font-size: 0.97em;
            background: #f4f4f4;
            border-radius: 8px;
            margin-right: 6px;
            margin-bottom: 2px;
            color: #555;
        }
        .entrada-chip { background:#e6f9ee; color:#119944; font-weight:600;}
        .saida-chip { background:#ffeaea; color:#d61e1e; font-weight:600;}
        .valor-entrada { color: #24bb4e; font-weight:600; font-size:1.18em; }
        .valor-saida   { color: #e4002b; font-weight:600; font-size:1.18em; }
        </style>
    """, unsafe_allow_html=True)

    st.markdown("## Histórico de Transações")

    df = pd.DataFrame(st.session_state.transacoes, columns=cols)
    df["Valor"] = df["Valor"].apply(lambda x: float(normaliza_valor(x)))
    df = df.sort_values(by="Data Vencimento", ascending=False).reset_index(drop=True)

    busca = st.text_input("🔎 Buscar por descrição ou categoria", key="busca_hist")
    df_filtrado = df.copy()
    if busca:
        mask = (
            df_filtrado["Descrição"].str.contains(busca, case=False, na=False) |
            df_filtrado["Categoria"].str.contains(busca, case=False, na=False)
        )
        df_filtrado = df_filtrado[mask]

    if df_filtrado.empty:
        st.info("Nenhuma transação encontrada.")
    else:
        for _, row in df_filtrado.iterrows():
            tipo = "entrada" if row["Valor"] > 0 else "saida"
            valor_html = (
                f"<span class='valor-entrada'>R$ {row['Valor']:,.2f}</span>" if row["Valor"] > 0
                else f"<span class='valor-saida'>R$ {abs(row['Valor']):,.2f}</span>"
            )
            st.markdown(
                f"""
                <div class='transacao-card {tipo}'>
                    <div>
                        <b>{row['Descrição']}</b>
                        <span class='transacao-chip'>{row['Categoria']}</span>
                        <span class='transacao-chip'>{row['Tipo']}</span>
                        {"<span class='entrada-chip'>Entrada</span>" if row['Valor'] > 0 else "<span class='saida-chip'>Saída</span>"}
                    </div>
                    <div>
                        {valor_html}
                    </div>
                </div>
                """, unsafe_allow_html=True
            )


elif st.session_state.pagina == "Remover":
    st.markdown("""
        <style>
        .remover-card {
            background: #fff;
            border-radius: 14px;
            box-shadow: 0 1px 8px #e4002b22;
            padding: 14px 24px;
            margin-bottom: 18px;
            border-left: 6px solid #e4002b22;
            display: flex;
            align-items: center;
            justify-content: space-between;
            transition: box-shadow 0.2s;
        }
        .remover-card.entrada { border-left: 6px solid #24bb4e; }
        .remover-card.saida   { border-left: 6px solid #e4002b; }
        .valor-entrada { color: #24bb4e; font-weight:600; font-size:1.18em; }
        .valor-saida   { color: #e4002b; font-weight:600; font-size:1.18em; }
        </style>
    """, unsafe_allow_html=True)

    st.markdown("## Remover Transações em Lote")
    df = pd.DataFrame(st.session_state.transacoes, columns=cols)
    df["Valor"] = df["Valor"].apply(lambda x: float(normaliza_valor(x)))
    df["Data Vencimento"] = pd.to_datetime(df["Data Vencimento"], errors="coerce")
    df = df.sort_values(by="Data Vencimento", ascending=False).reset_index(drop=True)

    busca = st.text_input("🔎 Buscar por descrição ou categoria", key="busca_remover")
    df_filtrado = df.copy()
    if busca:
        mask = (
            df_filtrado["Descrição"].str.contains(busca, case=False, na=False) |
            df_filtrado["Categoria"].str.contains(busca, case=False, na=False)
        )
        df_filtrado = df_filtrado[mask]

    # Estado dos checkboxes
    if "selecionados_remover" not in st.session_state or len(st.session_state.selecionados_remover) != len(df_filtrado):
        st.session_state.selecionados_remover = [False] * len(df_filtrado)

    if df_filtrado.empty:
        st.info("Nenhuma transação encontrada.")
    else:
        # Botão para selecionar/deselecionar todos
        col_a, col_b = st.columns([1, 2])
        with col_a:
            if st.button("Selecionar Todos"):
                st.session_state.selecionados_remover = [True] * len(df_filtrado)
        with col_b:
            if st.button("Desmarcar Todos"):
                st.session_state.selecionados_remover = [False] * len(df_filtrado)

        indices_remover = []
        for idx, (_, row) in enumerate(df_filtrado.iterrows()):
            tipo = "entrada" if row["Valor"] > 0 else "saida"
            valor_html = (
                f"<span class='valor-entrada'>R$ {row['Valor']:,.2f}</span>" if row["Valor"] > 0
                else f"<span class='valor-saida'>R$ {abs(row['Valor']):,.2f}</span>"
            )
            cols_rem = st.columns([1, 18, 4])
            with cols_rem[0]:
                st.session_state.selecionados_remover[idx] = st.checkbox("", value=st.session_state.selecionados_remover[idx], key=f"cb_remover_{idx}")
            with cols_rem[1]:
                st.markdown(
                    f"""
                    <div class='remover-card {tipo}' style='box-shadow:none; margin:0; padding:7px 0 7px 0; border-radius:0; border-left-width:4px;'>
                        <b>{row['Descrição']}</b> &nbsp;
                        <span style='font-size:0.97em;color:#777;'>({row['Categoria']})</span>
                    </div>
                    """, unsafe_allow_html=True
                )
            with cols_rem[2]:
                st.markdown(valor_html, unsafe_allow_html=True)
            if st.session_state.selecionados_remover[idx]:
                indices_remover.append(idx)

        st.markdown("---")
        if st.button("🗑️ Excluir selecionadas", use_container_width=True):
            if not indices_remover:
                st.warning("Selecione ao menos uma transação para remover.")
            else:
                # Montar lista de índices reais no df original
                all_rows = worksheet.get_all_values()[1:]  # Ignora cabeçalho
                removidos = 0
                debug_msgs = []
                for idx_df in sorted(indices_remover, reverse=True):
                    transacao_df = {
                        "Data Vencimento": str(df_filtrado.iloc[idx_df]["Data Vencimento"].date() if pd.notnull(df_filtrado.iloc[idx_df]["Data Vencimento"]) else ""),
                        "Descrição": str(df_filtrado.iloc[idx_df]["Descrição"]).strip(),
                        "Valor": "{:.2f}".format(float(df_filtrado.iloc[idx_df]["Valor"])).replace(",", "."),
                        "Categoria": str(df_filtrado.iloc[idx_df]["Categoria"]).strip(),
                        "Tipo": str(df_filtrado.iloc[idx_df]["Tipo"]).strip(),
                        "Telefone": str(df_filtrado.iloc[idx_df]["Telefone"]).strip(),
                        "Pago": str(df_filtrado.iloc[idx_df]["Pago"]).strip()
                    }
                    found = False
                    for row_num, row_values in enumerate(all_rows, start=2):
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


elif st.session_state.pagina == "Dashboard":
     dashboard_financeiro()

elif st.session_state.pagina == "Cartões":
    st.markdown("""
        <style>
        .cartao-box {
            background: #fff;
            border-radius: 14px;
            box-shadow: 0 2px 12px #e4002b24;
            padding: 18px 22px 10px 22px;
            margin-bottom: 18px;
        }
        .limite-label { color: #888; font-size: 0.99em;}
        .limite-valor { font-size: 1.12em; font-weight: 700;}
        .venc-label { color: #888; }
        .cartao-nome { font-size: 1.15em; font-weight: bold; }
        .fatura-mes { background: #e4002b11; padding:4px 14px; border-radius:8px; font-size: 1.04em; font-weight:600; display:inline-block;}
        </style>
    """, unsafe_allow_html=True)
    st.markdown("## 💳 Cartões de Crédito")

    st.subheader("Adicionar novo cartão")
    with st.form("form_cartao"):
        col1, col2, col3 = st.columns([4,2,2])
        with col1:
            nome_cartao = st.text_input("Nome do cartão", placeholder="Ex: Nubank, Itaú Gold")
        with col2:
            limite_cartao = st.text_input("Limite (R$)", placeholder="Ex: 3000")
        with col3:
            vencimento = st.number_input("Vencimento", min_value=1, max_value=31, step=1, format="%d")
        submitted_cartao = st.form_submit_button("Cadastrar cartão")
        if submitted_cartao:
            if not nome_cartao or not limite_cartao or not vencimento:
                st.warning("Preencha todos os campos.")
            else:
                adicionar_cartao(nome_cartao, normaliza_valor(limite_cartao), vencimento)
                st.session_state.cartoes = ler_cartoes()
                st.success(f"Cartão '{nome_cartao}' cadastrado!")
                st.rerun()

    st.divider()
    st.subheader("Seus cartões")
    if st.session_state.cartoes:
        for idx, cartao in enumerate(st.session_state.cartoes):
            col1, col2, col3, col4 = st.columns([3,2,2,1])
            with col1:
                st.markdown(f"<div class='cartao-nome'>{cartao['nome']}</div>", unsafe_allow_html=True)
            with col2:
                st.markdown(
                    f"<span class='limite-label'>Limite:</span> <span class='limite-valor'>{formatar_brl(cartao['limite'])}</span>",
                    unsafe_allow_html=True
                )
            with col3:
                st.markdown(
                    f"<span class='venc-label'>Vencimento:</span> <b>{cartao['vencimento']}</b>",
                    unsafe_allow_html=True
                )
            with col4:
                if st.button("🗑️", key=f"excluir_cartao_{idx}"):
                    todas = worksheet_cartoes.get_all_records()
                    for i, c in enumerate(todas, start=2):
                        if (c.get("Nome") == cartao["nome"]
                            and float(normaliza_valor(c.get("Limite",0))) == cartao["limite"]
                            and str(c.get("Vencimento")) == str(cartao.get("vencimento", ""))):
                            worksheet_cartoes.delete_rows(i)
                            break
                    st.session_state.cartoes = ler_cartoes()
                    st.success(f"Cartão '{cartao['nome']}' removido!")
                    st.rerun()
            st.markdown('<div class="cartao-box"></div>', unsafe_allow_html=True)
    else:
        st.info("Nenhum cartão cadastrado.")

    st.divider()
    st.subheader("Lançar compra no cartão")
    cartoes = [c["nome"] for c in st.session_state.get("cartoes",[])]
    if cartoes:
        with st.form("form_compra_cartao"):
            col1, col2 = st.columns(2)
            with col1:
                cartao = st.selectbox("Cartão", cartoes)
                descricao = st.text_input("Descrição")
                valor = st.text_input("Valor (R$)", placeholder="Ex: 299,90")
            with col2:
                data_compra = st.date_input("Data da compra", value=date.today())
                parcelas = st.number_input("Parcelas", min_value=1, max_value=24, value=1, step=1)
                pago = st.radio("Pago?", ["N", "S"], horizontal=True, index=0)
            telefone = st.text_input("WhatsApp/SMS", placeholder="Ex: 5511999998888")
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

    st.divider()
    st.subheader("Faturas e compras dos cartões")
    df = pd.DataFrame(st.session_state.transacoes, columns=cols)
    if not df.empty and cartoes:
        df["Valor"] = df["Valor"].apply(lambda x: float(normaliza_valor(x)))
        df["Data Vencimento"] = pd.to_datetime(df["Data Vencimento"], errors="coerce")
        df["mes_ano"] = df["Data Vencimento"].dt.strftime("%m/%Y")
        df = df[df["Tipo"] == "Saída"]
        for cartao in cartoes:
            cartao_info = next((c for c in st.session_state.cartoes if c["nome"] == cartao), {})
            venc = cartao_info.get("vencimento")
            compras_cartao = df[df["Categoria"] == cartao]
            if not compras_cartao.empty:
                st.markdown(f"### <span style='color:#e4002b'>{cartao}</span>", unsafe_allow_html=True)
                if venc:
                    st.markdown(
                        f"<span class='venc-label'>Vencimento da fatura: dia <b>{venc}</b></span>",
                        unsafe_allow_html=True
                    )
                for mesano in sorted(compras_cartao["mes_ano"].unique(), reverse=True):
                    df_mes = compras_cartao[compras_cartao["mes_ano"] == mesano]
                    total = df_mes["Valor"].sum()
                    st.markdown(f"<div class='fatura-mes'>{mesano} | Total: {formatar_brl(total)}</div>", unsafe_allow_html=True)
                    st.table(
                        df_mes[["Data Vencimento", "Descrição", "Valor"]]
                        .sort_values("Data Vencimento")
                        .rename(columns={"Data Vencimento": "Vencimento"})
                    )
            else:
                st.info(f"Nenhuma compra cadastrada no cartão {cartao}.")
    else:
        st.info("Nenhuma compra registrada ainda.")
