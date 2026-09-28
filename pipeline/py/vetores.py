"""Vetores por documento (P:, OB:, T:), alinhados à tabela documento.

Os embeddings ficam no cache indexados pelo hash do texto; aqui cada
documento recebe o vetor do seu hash. Também oferece a versão "calibrada":
subtrai-se o vetor médio de cada grupo (tipo de documento × idioma) e
renormaliza-se. Isso remove o "sotaque" do gênero textual (projeto,
publicação, tecnologia) e do idioma (16% das publicações estão em inglês),
para que documentos sobre o mesmo assunto se aproximem independentemente
do tipo e da língua (desenho, §7.2).
"""

import numpy as np
import pandas as pd

from embeddings_cache import ler_cache, textos_para_modelo
from textos import PROC, carregar_textos


def carregar_vetores(calibrar: bool = True) -> tuple[pd.DataFrame, np.ndarray]:
    docs = textos_para_modelo()[["doc_uid", "tipo_doc", "hash"]]
    ids, vet = ler_cache()
    linha = pd.Series(np.arange(len(ids)), index=ids.hash)
    docs = docs[docs.hash.isin(linha.index)].reset_index(drop=True)
    V = vet[linha.loc[docs.hash].values].astype(np.float32)
    meta = pd.read_parquet(PROC / "documento.parquet", columns=["doc_uid", "ano", "titulo"])
    docs = docs.merge(meta, on="doc_uid", how="left")
    docs["idioma"] = docs.doc_uid.map(carregar_textos().set_index("doc_uid").idioma).fillna("pt").values
    if calibrar:
        for _, g in docs.groupby(["tipo_doc", "idioma"]).groups.items():
            g = np.asarray(g)
            V[g] -= V[g].mean(axis=0)
        V /= np.linalg.norm(V, axis=1, keepdims=True) + 1e-12
    return docs, V
