"""Texto semântico de cada documento (projeto, obra, tecnologia).

Usa título + resumo/descrição + palavras-chave. Não inclui unidades, pessoas
ou URLs, para que a similaridade reflita conteúdo e não identidade
institucional (ver docs/01-desenho-do-sistema.md, §6).
"""

from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parents[2]
PROC = RAIZ / "data" / "processed"


def carregar_textos() -> pd.DataFrame:
    doc = pd.read_parquet(PROC / "documento.parquet",
                          columns=["doc_uid", "tipo_doc", "titulo", "resumo", "ano", "unidade_id"])
    kw = pd.read_parquet(PROC / "documento_keyword.parquet", columns=["doc_uid", "keyword_raw"])
    kw = kw.groupby("doc_uid").keyword_raw.agg(lambda s: "; ".join(dict.fromkeys(s)))
    doc["palavras_chave"] = doc.doc_uid.map(kw)
    partes = [doc.titulo.fillna("").str.strip().str.rstrip("."),
              doc.resumo.fillna("").str.strip(),
              ("Palavras-chave: " + doc.palavras_chave).where(doc.palavras_chave.notna(), "")]
    doc["texto"] = (partes[0] + ". " + partes[1] + " " + partes[2]).str.replace(r"\s+", " ", regex=True).str.strip()
    doc["texto_curto"] = doc.resumo.isna() | (doc.resumo.str.len() < 30)
    return doc


def gold_tecnologia_publicacao() -> pd.DataFrame:
    """Pares declarados: tecnologia (T:) → obra (OB:) citada em 'Onde encontrar'."""
    link = pd.read_parquet(PROC / "doc_link.parquet")
    pub = pd.read_parquet(PROC / "publicacao.parquet", columns=["doc_uid", "obra_id"])
    g = link[link.destino_na_base].merge(pub, left_on="destino_uid", right_on="doc_uid")
    return g[["origem_uid", "obra_id"]].drop_duplicates().rename(columns={"origem_uid": "tecnologia", "obra_id": "obra"})
