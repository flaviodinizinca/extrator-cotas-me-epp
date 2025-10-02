# ME-EPPgit/processador.py - CÓDIGO COMPLETO E CORRIGIDO
# -*- coding: utf-8 -*-
"""
Módulo contendo a lógica de negócio para processamento de cotas ME/EPP.
Versão Final: Torna a coluna QUANTIDADE TOTAL opcional no arquivo de entrada
e a remove do resultado se ela não existia no original.
"""
import pandas as pd
import numpy as np
from typing import List, Dict, Any, Set

# --- Constantes ---
COL_ITEM: str = "ITEM"
COL_ESPECIFICACAO: str = "ESPECIFICAÇÃO"
COL_QTD_TOTAL: str = "QUANTIDADE TOTAL"
COL_VALOR_UNITARIO: str = "VALOR UNITÁRIO"
COL_VALOR_TOTAL: str = "VALOR TOTAL"
PREFIXO_QTD: str = "QUANTIDADE"
PREFIXO_VALOR: str = "VALOR TOTAL"
COL_TRATAMENTO: str = "TRATAMENTO FAVORECIDO DECRETO 8538/2015"
TRATAMENTO_EXCLUSIVO: str = "Exclusivo para ME/EPP"
TRATAMENTO_AMPLA: str = "Ampla Disputa"
TRATAMENTO_COTA: str = "Cota reservada para ME/EPP"
TETO_ME_EPP: float = 80000.0
PERCENTUAL_MAX_COTA: int = 25

def processar_df_orcamento(df: pd.DataFrame, original_had_qtd_total: bool, indices_marcados: Set[int]) -> pd.DataFrame:
    """
    Processa um DataFrame de orçamento para aplicar regras de cotas.

    Args:
        df: DataFrame contendo os dados do orçamento.
        original_had_qtd_total: Flag booleana que indica se a coluna
                                'QUANTIDADE TOTAL' existia no arquivo original.
        indices_marcados: Um conjunto com os índices das linhas marcadas para cota.
    Returns:
        Um novo DataFrame com os itens processados.
    """
    cols_quantidades = [c for c in df.columns if c.startswith(PREFIXO_QTD) and c != COL_QTD_TOTAL]

    if COL_QTD_TOTAL not in df.columns:
        if not cols_quantidades:
            raise ValueError(
                "O arquivo não possui 'QUANTIDADE TOTAL' nem colunas parciais "
                "como 'QUANTIDADE' para o cálculo."
            )
        df[COL_QTD_TOTAL] = df[cols_quantidades].sum(axis=1, skipna=True)

    processed_rows: List[Dict[str, Any]] = []
    
    for index, row in df.iterrows():
        original_row = row.to_dict()
        if index in indices_marcados:
            valor_unitario = row.get(COL_VALOR_UNITARIO, 0)
            qtd_total = row.get(COL_QTD_TOTAL, 0)
            valor_total_item = valor_unitario * qtd_total if pd.notna(valor_unitario) and pd.notna(qtd_total) else 0

            if valor_total_item <= TETO_ME_EPP:
                original_row[COL_TRATAMENTO] = TRATAMENTO_EXCLUSIVO
                processed_rows.append(original_row)
            else:
                if valor_unitario > TETO_ME_EPP:
                    original_row[COL_TRATAMENTO] = TRATAMENTO_AMPLA
                    processed_rows.append(original_row)
                else:
                    cota_perc_encontrado = 0
                    for perc in range(PERCENTUAL_MAX_COTA, 0, -1):
                        qtd_cota = round(qtd_total * (perc / 100))
                        if qtd_cota >= 1 and (qtd_cota * valor_unitario) <= TETO_ME_EPP:
                            cota_perc_encontrado = perc
                            break
                    
                    if cota_perc_encontrado
