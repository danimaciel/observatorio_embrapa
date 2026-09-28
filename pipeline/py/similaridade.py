"""Documentos semelhantes e proximidade temática entre unidades.

Saídas em data/processed/:
  similaridade.parquet         para cada documento e cada tipo de destino
                               (projeto, publicação, tecnologia), os K mais
                               semelhantes: origem_uid, destino_uid,
                               tipo_destino, cos, percentil, rank
  proximidade_unidade.parquet  unidade1, unidade2, cos, percentil — cosseno
                               entre os perfis temáticos (centróides) das
                               unidades, separado da colaboração observada

Cossenos são calculados sobre vetores calibrados por tipo (vetores.py). O
percentil situa cada valor na distribuição daquele par de tipos (ex.: entre
projeto→publicação), para ser comparável entre pares.

Uso: .venv-nlp/Scripts/python pipeline/py/similaridade.py
"""

import time

import numpy as np
import pandas as pd

from textos import PROC
from vetores import carregar_vetores

K = 10
BLOCO = 1024
SEMENTE = 42


def distribuicao_nula(A: np.ndarray, B: np.ndarray, n: int = 300_000) -> np.ndarray:
    """Cossenos de pares sorteados — referência para os percentis."""
    rng = np.random.default_rng(SEMENTE)
    i = rng.integers(0, len(A), n)
    j = rng.integers(0, len(B), n)
    return np.sort((A[i] * B[j]).sum(1))


def top_k(A: np.ndarray, B: np.ndarray, mesmo_conjunto: bool) -> tuple[np.ndarray, np.ndarray]:
    k = min(K, len(B) - (1 if mesmo_conjunto else 0))
    idx = np.empty((len(A), k), dtype=np.int32)
    val = np.empty((len(A), k), dtype=np.float32)
    for s in range(0, len(A), BLOCO):
        S = A[s:s + BLOCO] @ B.T
        if mesmo_conjunto:
            S[np.arange(len(S)), np.arange(s, s + len(S))] = -np.inf
        p = np.argpartition(-S, k, axis=1)[:, :k]
        v = np.take_along_axis(S, p, axis=1)
        o = np.argsort(-v, axis=1)
        idx[s:s + BLOCO] = np.take_along_axis(p, o, axis=1)
        val[s:s + BLOCO] = np.take_along_axis(v, o, axis=1)
    return idx, val


def main() -> None:
    t0 = time.time()
    docs, V = carregar_vetores(calibrar=True)
    print(f"{len(docs):,} documentos com vetor".replace(",", "."), flush=True)
    tipos = ["projeto", "publicacao", "tecnologia"]
    grupos = {t: np.where(docs.tipo_doc.values == t)[0] for t in tipos}

    partes = []
    for ta in tipos:
        for tb in tipos:
            ia, ib = grupos[ta], grupos[tb]
            A, B = V[ia], V[ib]
            nula = distribuicao_nula(A, B)
            idx, val = top_k(A, B, mesmo_conjunto=(ta == tb))
            k = idx.shape[1]
            partes.append(pd.DataFrame({
                "origem_uid": np.repeat(docs.doc_uid.values[ia], k),
                "destino_uid": docs.doc_uid.values[ib][idx.ravel()],
                "tipo_origem": ta, "tipo_destino": tb,
                "cos": val.ravel().round(4),
                "percentil": (100 * np.searchsorted(nula, val.ravel()) / len(nula)).round(2),
                "rank": np.tile(np.arange(1, k + 1), len(ia)).astype(np.int8),
            }))
            print(f"  {ta:>10} → {tb:<10} {len(ia):>7,} × {len(ib):>7,}  "
                  f"({time.time() - t0:5.0f}s)".replace(",", "."), flush=True)
    sim = pd.concat(partes, ignore_index=True)
    sim.to_parquet(PROC / "similaridade.parquet", index=False, compression="zstd")
    print(f"similaridade.parquet: {len(sim):,} linhas".replace(",", "."), flush=True)

    # Proximidade temática entre unidades: centróide dos documentos com
    # participação da unidade (qualquer papel), centrado na média geral.
    du = pd.read_parquet(PROC / "documento_unidade.parquet", columns=["doc_uid", "unidade_id"]).drop_duplicates()
    pos = pd.Series(np.arange(len(docs)), index=docs.doc_uid)
    du = du[du.doc_uid.isin(pos.index)]
    unidades = sorted(du.unidade_id.unique())
    C = np.zeros((len(unidades), V.shape[1]), dtype=np.float32)
    n_docs = []
    for u_i, u in enumerate(unidades):
        linhas = pos.loc[du.doc_uid[du.unidade_id == u]].values
        C[u_i] = V[linhas].mean(axis=0)
        n_docs.append(len(linhas))
    C -= C.mean(axis=0)
    C /= np.linalg.norm(C, axis=1, keepdims=True) + 1e-12
    S = C @ C.T
    iu = np.triu_indices(len(unidades), 1)
    prox = pd.DataFrame({"unidade1": np.array(unidades)[iu[0]], "unidade2": np.array(unidades)[iu[1]],
                         "cos": S[iu].round(4)})
    prox["percentil"] = (100 * prox.cos.rank(pct=True)).round(1)
    prox.to_parquet(PROC / "proximidade_unidade.parquet", index=False)
    print(f"proximidade_unidade.parquet: {len(prox)} pares de {len(unidades)} unidades "
          f"(docs por unidade: mín {min(n_docs)}, mediana {int(np.median(n_docs))})", flush=True)
    print(f"Concluído em {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
