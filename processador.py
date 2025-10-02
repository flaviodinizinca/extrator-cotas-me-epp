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
                    
                    if cota_perc_encontrado > 0:
                        cota_row = original_row.copy()
                        cota_row[COL_ESPECIFICACAO] = f"##TEMP_COTA##{cota_perc_encontrado}"
                        cota_row[COL_TRATAMENTO] = TRATAMENTO_COTA
                        
                        original_row[COL_TRATAMENTO] = TRATAMENTO_AMPLA
                        
                        for col_qtd in cols_quantidades:
                            qtd_original_parcial = original_row.get(col_qtd, 0)
                            qtd_cota_parcial = round(qtd_original_parcial * (cota_perc_encontrado / 100))
                            cota_row[col_qtd] = qtd_cota_parcial
                            original_row[col_qtd] -= qtd_cota_parcial
                            
                        processed_rows.append(original_row)
                        processed_rows.append(cota_row)
                    else:
                        original_row[COL_TRATAMENTO] = TRATAMENTO_AMPLA
                        processed_rows.append(original_row)
        else:
            original_row[COL_TRATAMENTO] = TRATAMENTO_AMPLA
            processed_rows.append(original_row)
            
    if not processed_rows:
        return pd.DataFrame()

    result_df = pd.DataFrame(processed_rows).reset_index(drop=True)
    
    if cols_quantidades:
        result_df[COL_QTD_TOTAL] = result_df[cols_quantidades].sum(axis=1, skipna=True)
    
    if COL_QTD_TOTAL in result_df.columns and COL_VALOR_UNITARIO in result_df.columns:
        result_df[COL_VALOR_TOTAL] = (result_df[COL_QTD_TOTAL] * result_df[COL_VALOR_UNITARIO]).round(4)
    
    cols_valores = [c for c in df.columns if c.startswith(PREFIXO_VALOR) and c != COL_VALOR_TOTAL]
    for col_val, col_qtd in zip(cols_valores, cols_quantidades):
        if col_val in result_df.columns and col_qtd in result_df.columns and COL_VALOR_UNITARIO in result_df.columns:
            result_df[col_val] = (result_df[col_qtd] * result_df[COL_VALOR_UNITARIO]).round(4)
            
    result_df[COL_ITEM] = np.arange(1, len(result_df) + 1)

    last_item_mae_num = 0
    for i, row in result_df.iterrows():
        especificacao = str(row.get(COL_ESPECIFICACAO, ''))
        if especificacao.startswith("##TEMP_COTA##"):
            item_mae_num = result_df.at[i - 1, COL_ITEM] if i > 0 else last_item_mae_num
            perc = especificacao.replace("##TEMP_COTA##", "")
            new_desc = f"Idem ao item {item_mae_num}, cota reservada para me/epp de até {perc}%"
            result_df.at[i, COL_ESPECIFICACAO] = new_desc
        else:
            last_item_mae_num = row[COL_ITEM]

    if not original_had_qtd_total:
        if COL_QTD_TOTAL in result_df.columns:
            result_df = result_df.drop(columns=[COL_QTD_TOTAL])

    return result_df
