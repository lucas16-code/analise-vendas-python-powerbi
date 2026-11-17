
from pathlib import Path
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

    # Identifica a categoria de cada registro
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
print(
    f"Movimentações únicas: {dados['rel_idMov'].nunique()}"
)

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

dados = dados.drop(columns=["ID da Movimentação"])


# 10. EXPORTAÇÃO DA BASE TRATADA

pasta_saida = projeto / "dados_tratados"
pasta_saida.mkdir(parents=True, exist_ok=True)

arquivo_saida = pasta_saida / "vendas_outubro_2026.xlsx"

dados.to_excel(arquivo_saida, index=False)

print("\n--- EXPORTAÇÃO CONCLUÍDA ---")
print(f"Arquivo: {arquivo_saida.name}")
print(f"Registros exportados: {len(dados)}")
print(f"Colunas exportadas: {len(dados.columns)}")
