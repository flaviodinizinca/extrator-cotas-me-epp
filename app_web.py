# ME-EPP/app_web.py - Versão para rodar ONLINE
# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
from processador import processar_df_orcamento
from exportador import to_excel

# --- Configuração da Página ---
st.set_page_config(
    page_title="Calculadora de Cotas ME/EPP",
    page_icon="images/budget.png", # Usa o seu ícone
    layout="wide"
)

# --- Título da Aplicação ---
st.title("Calculadora de Cotas para ME/EPP")
st.markdown("Faça o upload da sua planilha de orçamento para aplicar as regras de cotas.")

# --- Lógica da Aplicação ---

# Armazena os dados na sessão para não perdê-los ao interagir
if 'df_original' not in st.session_state:
    st.session_state.df_original = None
if 'df_resultado' not in st.session_state:
    st.session_state.df_resultado = None

# 1. Upload do Arquivo
uploaded_file = st.file_uploader("Selecione a planilha Excel (.xlsx)", type="xlsx")

if uploaded_file is not None:
    try:
        df = pd.read_excel(uploaded_file)
        df.columns = [str(col).upper().strip() for col in df.columns]
        
        # Adiciona a coluna para o usuário marcar (a "cota")
        df.insert(0, 'SELECIONAR COTA', False)
        
        st.session_state.df_original = df
        # Limpa o resultado anterior se um novo arquivo for carregado
        st.session_state.df_resultado = None 

    except Exception as e:
        st.error(f"Erro ao ler o arquivo: {e}")
        st.session_state.df_original = None


# 2. Exibição da Tabela e Seleção
if st.session_state.df_original is not None:
    st.subheader("Planilha Original")
    st.markdown("Marque a caixa de seleção `SELECIONAR COTA` nas linhas que devem ser consideradas para a análise de cotas.")
    
    # Usamos o editor de dados para que o usuário possa marcar as caixas
    df_editado = st.data_editor(
        st.session_state.df_original,
        key='editor_dados',
        use_container_width=True
    )
    
    # Botão para processar
    if st.button("Processar Cotas Marcadas"):
        # Pega os índices das linhas onde a coluna 'SELECIONAR COTA' foi marcada
        indices_marcados = set(df_editado[df_editado['SELECIONAR COTA'] == True].index)

        if not indices_marcados:
            st.warning("Nenhuma linha foi selecionada para processamento de cota.")
        else:
            with st.spinner('Processando...'):
                try:
                    # Remove a coluna de seleção antes de enviar para a lógica
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

# 3. Exibição e Download do Resultado
if st.session_state.df_resultado is not None:
    st.subheader("Resultado Processado")
    st.dataframe(st.session_state.df_resultado, use_container_width=True)
    
    # Converte o resultado para Excel em memória
    excel_bytes = to_excel(st.session_state.df_resultado)
    
    st.download_button(
        label="Download do Resultado em Excel",
        data=excel_bytes,
        file_name="resultado_cotas_processado.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )