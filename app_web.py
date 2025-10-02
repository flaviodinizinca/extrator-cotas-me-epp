# ME-EPPgit/app_web.py - CÓDIGO FINAL E CORRIGIDO
# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import numpy as np
from processador import (
    processar_df_orcamento, COL_QTD_TOTAL, PREFIXO_VALOR,
    PREFIXO_QTD, COL_VALOR_UNITARIO, COL_ITEM, COL_VALOR_TOTAL
)
from exportador import to_excel
import io

# --- Configuração da Página ---
st.set_page_config(
    page_title="Calculadora de Cotas ME/EPP",
    page_icon="images/budget.png",
    layout="wide"
)

# --- Funções Auxiliares ---
def formatar_moeda_br_string(valor):
    """Formata um número para uma string no padrão de moeda brasileiro (R$ #.###,####)."""
    if pd.isna(valor) or not isinstance(valor, (int, float)):
        return "R$ 0,0000"
    return f"R$ {valor:,.4f}".replace(",", "X").replace(".", ",").replace("X", ".")

def validar_e_calcular_totais(df: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    """Valida e recalcula os totais do DataFrame, retornando o DF corrigido e mensagens de correção."""
    correcoes_msgs = []
    
    if COL_VALOR_UNITARIO not in df.columns:
        raise ValueError(f"A coluna '{COL_VALOR_UNITARIO}' é obrigatória e não foi encontrada.")

    df[COL_VALOR_UNITARIO] = pd.to_numeric(df[COL_VALOR_UNITARIO], errors='coerce').fillna(0)
    
    cols_qtd = [c for c in df.columns if str(c).upper().strip().startswith(PREFIXO_QTD) and c != COL_QTD_TOTAL]

    for col_qtd in cols_qtd:
        df[col_qtd] = pd.to_numeric(df[col_qtd], errors='coerce').fillna(0)
        col_total_correspondente = col_qtd.replace(PREFIXO_QTD, PREFIXO_VALOR)
        
        total_correto = (df[col_qtd] * df[COL_VALOR_UNITARIO]).round(4)

        if col_total_correspondente in df.columns:
            valores_originais_usuario = df[col_total_correspondente].copy()
            valores_numericos_usuario = pd.to_numeric(valores_originais_usuario, errors='coerce')

            for index, valor_original in valores_originais_usuario.items():
                if pd.notna(valor_original):
                    valor_numerico = valores_numericos_usuario.at[index]
                    valor_calculado = total_correto.at[index]
                    if pd.isna(valor_numerico) or not np.isclose(valor_numerico, valor_calculado, atol=0.01):
                        item_num = df.at[index, COL_ITEM] if COL_ITEM in df.columns else index + 1
                        correcoes_msgs.append(
                            f"Item {item_num}, Coluna '{col_total_correspondente}': Valor informado "
                            f"({valor_original}) foi corrigido para {formatar_moeda_br_string(valor_calculado)}."
                        )
        
        df[col_total_correspondente] = total_correto

    if cols_qtd:
        total_qtd_correto = df[cols_qtd].sum(axis=1) if len(cols_qtd) > 1 else df[cols_qtd[0]]
        total_geral_correto = (total_qtd_correto * df[COL_VALOR_UNITARIO]).round(4)

        if COL_VALOR_TOTAL in df.columns:
            valores_originais_usuario = df[COL_VALOR_TOTAL].copy()
            valores_numericos_usuario = pd.to_numeric(valores_originais_usuario, errors='coerce')

            for index, valor_original in valores_originais_usuario.items():
                if pd.notna(valor_original):
                    valor_numerico = valores_numericos_usuario.at[index]
                    valor_calculado = total_geral_correto.at[index]
                    if pd.isna(valor_numerico) or not np.isclose(valor_numerico, valor_calculado, atol=0.01):
                        item_num = df.at[index, COL_ITEM] if COL_ITEM in df.columns else index + 1
                        correcoes_msgs.append(
                            f"Item {item_num}, Coluna '{COL_VALOR_TOTAL}': Valor informado "
                            f"({valor_original}) foi corrigido para {formatar_moeda_br_string(valor_calculado)}."
                        )
        
        df[COL_QTD_TOTAL] = total_qtd_correto
        df[COL_VALOR_TOTAL] = total_geral_correto

    return df, correcoes_msgs

# --- Interface da Aplicação ---
st.title("Calculadora de Cotas para ME/EPP")
st.markdown("Faça o upload da sua planilha de orçamento para aplicar as regras de cotas.")

if 'df_original_numerico' not in st.session_state:
    st.session_state.df_original_numerico = None
if 'df_resultado' not in st.session_state:
    st.session_state.df_resultado = None

uploaded_file = st.file_uploader("Selecione a planilha Excel (.xlsx)", type="xlsx")

if uploaded_file is not None:
    try:
        df = pd.read_excel(uploaded_file)
        df.columns = [str(col).upper().strip() for col in df.columns]
        
        df_corrigido, correcoes = validar_e_calcular_totais(df.copy())
        
        if correcoes:
            st.warning("Foram encontradas divergências nos cálculos. Os valores foram corrigidos automaticamente:")
            for msg in correcoes:
                st.info(msg)

        df_corrigido.insert(0, 'SELECIONAR COTA', False)
        
        st.session_state.df_original_numerico = df_corrigido
        st.session_state.df_resultado = None

    except Exception as e:
        st.error(f"Erro ao ler ou validar o arquivo: {e}")
        st.session_state.df_original_numerico = None

if st.session_state.df_original_numerico is not None:
    st.subheader("Planilha Original")
    st.markdown("Marque a caixa de seleção `SELECIONAR COTA` nas linhas que devem ser consideradas para a análise de cotas.")
    
    # Cria uma cópia para exibição com a formatação correta de moeda
    df_para_exibir = st.session_state.df_original_numerico.copy()
    monetary_cols = [col for col in df_para_exibir.columns if 'VALOR' in str(col).upper()]
    for col in monetary_cols:
        df_para_exibir[col] = df_para_exibir[col].apply(formatar_moeda_br_string)
    
    # O data_editor agora edita o DataFrame original numérico
    df_editado = st.data_editor(
        st.session_state.df_original_numerico,
        key='editor_dados',
        use_container_width=True,
        hide_index=True,
    )
    
    if st.button("Processar Cotas Marcadas"):
        indices_marcados = set(df_editado[df_editado['SELECIONAR COTA'] == True].index)

        if not indices_marcados:
            st.warning("Nenhuma linha foi selecionada para processamento de cota.")
        else:
            with st.spinner('Processando...'):
                try:
                    df_para_processar = df_editado.drop(columns=['SELECIONAR COTA'])
                    original_had_qtd_total = "QUANTIDADE TOTAL" in df_para_processar.columns
                    
                    resultado = processar_df_orcamento(
                        df_para_processar.copy(), 
                        original_had_qtd_total, 
                        indices_marcados
                    )
                    st.session_state.df_resultado = resultado
                    st.success("Processamento concluído com sucesso!")

                except Exception as e:
                    st.error(f"Ocorreu um erro durante o processamento: {e}")

if st.session_state.df_resultado is not None:
    st.subheader("Resultado Processado")

    # Cria uma cópia formatada para exibição do resultado final
    df_resultado_display = st.session_state.df_resultado.copy()
    monetary_cols_resultado = [col for col in df_resultado_display.columns if 'VALOR' in str(col).upper()]
    for col in monetary_cols_resultado:
        df_resultado_display[col] = df_resultado_display[col].apply(formatar_moeda_br_string)
    
    st.dataframe(df_resultado_display, use_container_width=True, hide_index=True)
    
    excel_bytes = to_excel(st.session_state.df_resultado)
    
    st.download_button(
        label="Download do Resultado em Excel",
        data=excel_bytes,
        file_name="resultado_cotas_processado.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
