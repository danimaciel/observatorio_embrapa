"""Arquivo público de resultados para outros projetos (iAgro): produtos e localização de cada documento.

Só resultados analíticos e identificadores públicos do Redape — nenhum dado de pessoas.
  data/processed/enriquecimento.csv.gz  doc_uid (OB:/P:/T:), produtos (principais, ids separados por ";"),
                                        produtos_citados, ufs, municipios (cod_ibge), biomas
  data/processed/registro_obra.csv.gz   registro de publicação (B:id, um por unidade depositante) → obra (OB:id)
  data/processed/produtos.csv           cópia da taxonomia (produto_id → nome, categoria, grupo, fonte IBGE)
Publicado a cada mês como release pública "enriquecimento-AAAA-MM" em danimaciel/observatorio_embrapa
(ver skill atualizacao-mensal). Consumido por danimaciel/iagro-embrapa, iagro e iagro-conversa.
"""
import shutil
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from textos import RAIZ  # noqa: E402

PROC = RAIZ / "data" / "processed"


def juntar(s: pd.Series) -> str:
    return ";".join(sorted(set(map(str, s.dropna()))))


def main() -> None:
    doc = pd.read_parquet(PROC / "documento.parquet", columns=["doc_uid"])
    dp = pd.read_parquet(PROC / "doc_produto.parquet")
    dm = pd.read_parquet(PROC / "doc_municipio.parquet")
    dm = dm[dm.confianca.isin(["alta", "media"])]
    de = pd.read_parquet(PROC / "doc_estado.parquet")
    db = pd.read_parquet(PROC / "doc_bioma.parquet")

    e = doc.set_index("doc_uid")
    e["produtos"] = dp[dp.forca == "principal"].groupby("doc_uid").produto_id.agg(juntar)
    e["produtos_citados"] = dp[dp.forca == "citado"].groupby("doc_uid").produto_id.agg(juntar)
    e["ufs"] = de.groupby("doc_uid").uf.agg(juntar)
    e["municipios"] = dm.groupby("doc_uid").cod_ibge.agg(juntar)
    e["biomas"] = db.groupby("doc_uid").bioma.agg(juntar)
    e = e.dropna(how="all").reset_index()
    e.to_csv(PROC / "enriquecimento.csv.gz", index=False, encoding="utf-8")

    pub = pd.read_parquet(PROC / "publicacao.parquet", columns=["doc_uid", "obra_id"])
    pub.rename(columns={"doc_uid": "registro"}).to_csv(PROC / "registro_obra.csv.gz", index=False, encoding="utf-8")
    shutil.copy(RAIZ / "ref" / "produtos.csv", PROC / "produtos.csv")
    print(f"enriquecimento: {len(e):,} documentos com produto ou local; registro_obra: {len(pub):,} registros")


if __name__ == "__main__":
    main()
