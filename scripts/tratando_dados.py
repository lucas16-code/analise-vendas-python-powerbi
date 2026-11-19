from pathlib import Path
import numpy as np
import pandas as pd


# 1. LOCALIZAÇÃO DOS ARQUIVOS

projeto = Path(__file__).resolve().parent.parent
pasta = projeto / "dados_originais"

arquivos = sorted(pasta.glob("*.xlsx"))

if len(arquivos) != 11:
    raise ValueError(
        f"Esperados 11 arquivos Excel, encontrados {len(arquivos)}."
    )


# 2. LEITURA E CONSOLIDAÇÃO

bases = []

for arquivo in arquivos:
    df = pd.read_excel(arquivo)
    df["categoria_origem"] = arquivo.stem
    bases.append(df)

dados = pd.concat(bases, ignore_index=True)


# 3. SELEÇÃO DAS COLUNAS

colunas_necessarias = [
    "categoria_origem",
    "rel_dhEmi",
    "tot_qtdItens",
    "tot_qCom",
    "tot_qtdItensCancelados",
    "tot_vNF",
    "mov_descPag",
    "mov_descTp",
    "rel_indStatusMov",
    "rel_idMov"
]

dados = dados[colunas_necessarias].copy()


# 4. TRATAMENTO E VALIDAÇÃO DAS DATAS

dados["rel_dhEmi"] = pd.to_datetime(
    dados["rel_dhEmi"],
    errors="coerce"
)

datas_invalidas = dados["rel_dhEmi"].isna().sum()

if datas_invalidas > 0:
    raise ValueError(
        f"Encontradas {datas_invalidas} datas inválidas."
    )

inicio = pd.Timestamp("2026-10-01")
fim = pd.Timestamp("2026-11-01")

fora_periodo = ~dados["rel_dhEmi"].between(
    inicio,
    fim,
    inclusive="left"
)

if fora_periodo.any():
    raise ValueError(
        f"Encontrados {fora_periodo.sum()} registros fora de outubro de 2026."
    )


# 5. RESUMO DA BASE

print("\n--- RESUMO DA BASE ---")
print(f"Arquivos importados: {len(arquivos)}")
print(f"Total de registros: {len(dados)}")
print(f"Total de colunas: {len(dados.columns)}")
print(f"Movimentações únicas: {dados['rel_idMov'].nunique()}")
print(f"Primeira data: {dados['rel_dhEmi'].min()}")
print(f"Última data: {dados['rel_dhEmi'].max()}")

print("\nValores ausentes:")
print(dados.isna().sum())


# 6. TIPOS DE MOVIMENTAÇÃO

print("\n--- MOVIMENTAÇÕES ---")

movimentacoes = (
    dados.groupby(
        ["mov_descTp", "rel_indStatusMov"],
        dropna=False
    )["tot_vNF"]
    .agg(["count", "sum"])
)

print(movimentacoes)


# 7. FATURAMENTO POR CATEGORIA

print("\n--- FATURAMENTO POR CATEGORIA ---")

faturamento = (
    dados.groupby("categoria_origem")["tot_vNF"]
    .sum()
    .sort_values(ascending=False)
)

for categoria, valor in faturamento.items():
    print(f"{categoria}: R$ {valor:,.2f}")


# 8. FATURAMENTO TOTAL DO RELATÓRIO

total_geral = dados["tot_vNF"].sum()

print("\n--- TOTAL GERAL ---")
print(f"R$ {total_geral:,.2f}")


# 9. RENOMEAÇÃO DAS COLUNAS

dados = dados.rename(columns={
    "categoria_origem": "Categoria",
    "rel_dhEmi": "Data e Hora",
    "tot_qtdItens": "Itens Registrados",
    "tot_qCom": "Quantidade Vendida",
    "tot_qtdItensCancelados": "Itens Cancelados",
    "tot_vNF": "Valor Total",
    "mov_descPag": "Forma de Pagamento",
    "mov_descTp": "Tipo de Movimentação",
    "rel_indStatusMov": "Status",
    "rel_idMov": "ID da Movimentação"
})


# 10. SIMULAÇÃO DE CENÁRIO: CROSS-SELL POR CUPOM ÚNICO
# Premissa: 15% dos clientes que passaram no caixa com APENAS 1 item no cupom inteiro
# aceitam levar 1 item adicional de R$ 2,00

np.random.seed(42)

taxa_conversao = 0.15
valor_item_adicional = 2.00

# Soma a quantidade total de itens dentro de cada cupom (ID da Movimentação)
qtd_por_cupom = dados.groupby("ID da Movimentação")["Quantidade Vendida"].transform("sum")

# Filtra apenas cupons concluídos (Status == 2) que tiveram EXATAMENTE 1 item na compra inteira
filtro_cupom_um_item = (qtd_por_cupom == 1) & (dados["Status"] == 2)

# Sorteia 15% desses cupons
sorteio = np.random.rand(len(dados)) < taxa_conversao
condicao_cross_sell = filtro_cupom_um_item & sorteio

dados["Valor Total Simulado"] = np.where(
    condicao_cross_sell,
    dados["Valor Total"] + valor_item_adicional,
    dados["Valor Total"]
)

dados["Quantidade Simulada"] = np.where(
    condicao_cross_sell,
    dados["Quantidade Vendida"] + 1,
    dados["Quantidade Vendida"]
)

dados["Cenário Simulação"] = np.where(
    condicao_cross_sell,
    "Com Adicional (+R$ 2,00)",
    "Venda Original"
)

# Remove o ID da Movimentação após usá-lo na simulação
dados = dados.drop(columns=["ID da Movimentação"])

faturamento_simulado = dados["Valor Total Simulado"].sum()
diferenca = faturamento_simulado - total_geral
ticket_medio_real = dados["Valor Total"].mean()
ticket_medio_simulado = dados["Valor Total Simulado"].mean()

print("\n--- RESULTADO DA SIMULAÇÃO (POR CUPOM ÚNICO) ---")
print(f"Cupons de 1 item na compra inteira: {filtro_cupom_um_item.sum()}")
print(f"Cupons convertidos (15%): {condicao_cross_sell.sum()}")
print(f"Faturamento Real: R$ {total_geral:,.2f}")
print(f"Faturamento Simulado: R$ {faturamento_simulado:,.2f} (+R$ {diferenca:,.2f})")
print(f"Ticket Médio: R$ {ticket_medio_real:.2f} -> R$ {ticket_medio_simulado:.2f}")


# 11. EXPORTAÇÃO DA BASE TRATADA

pasta_saida = projeto / "dados_tratados"
pasta_saida.mkdir(parents=True, exist_ok=True)

arquivo_saida = pasta_saida / "vendas_outubro_2026.xlsx"

dados.to_excel(arquivo_saida, index=False)

print("\n--- EXPORTAÇÃO CONCLUÍDA ---")
print(f"Arquivo: {arquivo_saida.name}")
print(f"Registros exportados: {len(dados)}")
print(f"Colunas exportadas: {len(dados.columns)}")