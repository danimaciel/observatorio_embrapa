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
    # Versão para rotular temas (sem o prefixo "Palavras-chave:")
    doc["texto_rotulo"] = (partes[0] + ". " + partes[1] + " " + doc.palavras_chave.fillna("")) \
        .str.replace(r"\s+", " ", regex=True).str.strip()
    doc["idioma"] = detectar_idioma(doc.texto)
    return doc


_PT = set("de da do dos das para com em na no nas nos que e os as um uma foi são pelo pela".split())
_EN = set("the of and in to for with on is are from was were by this that".split())


def detectar_idioma(textos: pd.Series) -> pd.Series:
    """'en' ou 'pt' pela frequência de palavras funcionais (suficiente para calibrar os vetores)."""
    tok = textos.str.lower().str.findall(r"[a-zà-ú]+")
    pt = tok.map(lambda t: sum(w in _PT for w in t))
    en = tok.map(lambda t: sum(w in _EN for w in t))
    return (en > pt).map({True: "en", False: "pt"})


def gold_tecnologia_publicacao() -> pd.DataFrame:
    """Pares declarados: tecnologia (T:) → obra (OB:) citada em 'Onde encontrar'."""
    link = pd.read_parquet(PROC / "doc_link.parquet")
    pub = pd.read_parquet(PROC / "publicacao.parquet", columns=["doc_uid", "obra_id"])
    g = link[link.destino_na_base].merge(pub, left_on="destino_uid", right_on="doc_uid")
    return g[["origem_uid", "obra_id"]].drop_duplicates().rename(columns={"origem_uid": "tecnologia", "obra_id": "obra"})
