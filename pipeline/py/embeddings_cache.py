"""Cache de embeddings por hash do texto.

Cada documento é identificado por doc_uid + hash(modelo + texto). Se o texto
de um documento muda (ou o modelo muda), o hash muda e ele é recalculado;
documentos inalterados reaproveitam o vetor já calculado.

Arquivos em data/interim/embeddings/:
    <modelo>.npy            vetores float16 normalizados (n × dim)
    <modelo>_ids.parquet    doc_uid, hash — na mesma ordem das linhas do .npy
"""

import hashlib

import numpy as np
import pandas as pd

from textos import RAIZ, carregar_textos

MODELO = "intfloat/multilingual-e5-base"
ROTULO = "e5-base"
PREFIXO = "query: "       # e5: prefixo "query: " dos dois lados para similaridade simétrica
MAX_TOKENS = 512
DIR = RAIZ / "data" / "interim" / "embeddings"


def textos_para_modelo() -> pd.DataFrame:
    """doc_uid, texto_modelo (exatamente o que o modelo recebe) e hash."""
    d = carregar_textos()[["doc_uid", "tipo_doc", "texto"]].copy()
    d["texto_modelo"] = PREFIXO + d.texto
    d["hash"] = [hashlib.sha1(f"{MODELO}|{MAX_TOKENS}|{t}".encode("utf-8")).hexdigest() for t in d.texto_modelo]
    return d[["doc_uid", "tipo_doc", "texto_modelo", "hash"]]


def ler_cache() -> tuple[pd.DataFrame, np.ndarray]:
    ids, vet = DIR / f"{ROTULO}_ids.parquet", DIR / f"{ROTULO}.npy"
    if not ids.exists():
        return pd.DataFrame(columns=["doc_uid", "hash"]), np.zeros((0, 768), dtype=np.float16)
    return pd.read_parquet(ids), np.load(vet)


def gravar_cache(ids: pd.DataFrame, vetores: np.ndarray) -> None:
    assert len(ids) == len(vetores)
    DIR.mkdir(parents=True, exist_ok=True)
    np.save(DIR / f"{ROTULO}.npy", vetores.astype(np.float16))
    ids[["doc_uid", "hash"]].reset_index(drop=True).to_parquet(DIR / f"{ROTULO}_ids.parquet", index=False)
