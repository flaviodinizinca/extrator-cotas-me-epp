# SECOM Tools/ME-EPP/ui_components.py
import pandas as pd
import io
import traceback
from processador import COL_VALOR_UNITARIO, PREFIXO_VALOR

def to_excel(df: pd.DataFrame) -> bytes:
    """Converte um DataFrame para um arquivo Excel em memória com formatação de moeda e uma linha de totais."""
    output = io.BytesIO()
    try:
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, sheet_name='PlanilhaOrc', index=False)
            
            workbook = writer.book
            worksheet = writer.sheets['PlanilhaOrc']
            
            # Formato de moeda corrigido para garantir o separador de milhar.
            money_format = workbook.add_format({'num_format': 'R$ #,##0.0000_ ;[Red]-R$ #,##0.0000_ ;R$ 0,0000_ ;@_ '})
            
            header = [str(c).upper().strip() for c in df.columns]
            
            cols_valores_dinamicas = [c for c in header if c.startswith(PREFIXO_VALOR.strip())]
            monetary_cols_indices = [
                header.index(c) for c in [COL_VALOR_UNITARIO] + cols_valores_dinamicas 
                if c in header
            ]
            
            for col_idx in monetary_cols_indices:
                worksheet.set_column(col_idx, col_idx, 20, money_format)

            for idx, col_name in enumerate(df.columns):
                if idx not in monetary_cols_indices:
                    max_len = max(
                        (df[col_name].astype(str).map(len).max() or 0),
                        len(str(col_name))
                    ) + 2
                    worksheet.set_column(idx, idx, max_len)

            # --- LÓGICA ATUALIZADA PARA ADICIONAR A LINHA DE TOTAIS ---
            num_rows = len(df.index)
            total_row_idx = num_rows + 1

            total_value_cols = [c for c in df.columns if str(c).upper().strip().startswith(PREFIXO_VALOR.strip())]
            
            if total_value_cols:
                first_total_col_idx = header.index(total_value_cols[0])

                total_label_format = workbook.add_format({'bold': True, 'align': 'center', 'valign': 'vcenter', 'top': 1})
                total_money_format = workbook.add_format({'num_format': 'R$ #,##0.0000_ ;[Red]-R$ #,##0.0000_ ;R$ 0,0000_ ;@_ ', 'bold': True, 'top': 1, 'valign': 'vcenter'})

                if first_total_col_idx > 0:
                    worksheet.merge_range(
                        total_row_idx, 0, total_row_idx, first_total_col_idx - 1,
                        "VALOR TOTAL QUE AS INSTITUIÇÕES SE DISPÕEM A PAGAR",
                        total_label_format
                    )

                last_total_col_name = total_value_cols[-1]

                for col_name in total_value_cols:
                    col_idx = header.index(col_name)
                    total_value = pd.to_numeric(df[col_name], errors='coerce').sum()

                    if col_name == last_total_col_name:
                        worksheet.merge_range(
                            total_row_idx, col_idx, total_row_idx, col_idx + 1,
                            total_value,
                            total_money_format
                        )
                    else:
                        worksheet.write_number(total_row_idx, col_idx, total_value, total_money_format)
                
    except Exception as e:
        print(f"\n--- OCORREU UM ERRO DENTRO DA FUNÇÃO to_excel ---\n{traceback.format_exc()}")
        try:
            worksheet.write('A1', "Ocorreu um erro ao gerar o arquivo Excel:")
            worksheet.write('A2', str(e))
        except:
            pass
    
    return output.getvalue()