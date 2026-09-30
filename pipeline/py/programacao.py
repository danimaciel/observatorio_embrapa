"""Aderência dos documentos aos Desafios para Inovação da programação da Embrapa.

Cada desafio (ref/programacao_desafios.csv) pertence a um portfólio, um objetivo
estratégico, uma meta e um ODS. O texto do desafio é representado pelo mesmo
modelo SBERT dos documentos; a aderência é o cosseno entre os vetores
calibrados (vetores.py). Para cada documento guardam-se os 3 desafios mais
aderentes; o 1º define portfólio, objetivo, meta e ODS.

Só entra o conteúdo produzido sob a programação atual (desde CORTE): projetos
em execução a partir de CORTE; publicações e tecnologias com ano >= CORTE.

Confiança (por tipo de documento, sobre o cosseno do 1º desafio): alta = terço
superior, média = terço do meio, baixa = terço inferior. É uma medida relativa
— a precisão real vem da conferência de relatorios/programacao_amostra.csv.

Saídas em data/processed/: desafio.parquet, doc_desafio.parquet
Uso: .venv-nlp/Scripts/python pipeline/py/programacao.py
"""

import hashlib

import numpy as np
import pandas as pd

from embeddings_cache import MODELO, PREFIXO
from textos import PROC, RAIZ
from vetores import carregar_vetores

CORTE = 2024
TOP = 3
CACHE = RAIZ / "data" / "interim" / "programacao"


def texto_desafio(r) -> str:
    return f"Desafio de inovação do portfólio {r.portfolio}: {r.desafio}"


def vetores_desafios(des: pd.DataFrame) -> np.ndarray:
    textos = [PREFIXO + texto_desafio(r) for r in des.itertuples()]
    chave = hashlib.sha1(("|".join([MODELO] + textos)).encode("utf-8")).hexdigest()[:16]
    arq = CACHE / f"desafios_{chave}.npy"
    if arq.exists():
        return np.load(arq)
    from sentence_transformers import SentenceTransformer
    m = SentenceTransformer(MODELO, device="cpu")
    D = m.encode(textos, normalize_embeddings=True, batch_size=16).astype(np.float32)
    CACHE.mkdir(parents=True, exist_ok=True)
    np.save(arq, D)
    return D


def main() -> None:
    des = pd.read_csv(RAIZ / "ref" / "programacao_desafios.csv", dtype=str, keep_default_na=False)
    des["ods_num"] = pd.to_numeric(des.ods_num, errors="coerce").astype("Int64")
    des["meta_encerrada"] = des.meta_encerrada.str.upper().eq("TRUE")
    D = vetores_desafios(des)
    D = D - D.mean(axis=0)                       # calibração: remove o "sotaque" comum aos desafios
    D /= np.linalg.norm(D, axis=1, keepdims=True)

    docs, V = carregar_vetores(calibrar=True)
    fim = pd.read_parquet(PROC / "documento.parquet", columns=["doc_uid", "ano_fim"]).set_index("doc_uid").ano_fim
    ano_fim = docs.doc_uid.map(fim)
    dentro = np.where(docs.tipo_doc == "projeto",
                      ano_fim.fillna(9999) >= CORTE,
                      docs.ano.fillna(0) >= CORTE)
    idx = np.where(dentro)[0]
    S = V[idx] @ D.T
    ordem = np.argsort(-S, axis=1)[:, :TOP]
    sims = np.take_along_axis(S, ordem, axis=1)

    out = pd.DataFrame({
        "doc_uid": np.repeat(docs.doc_uid.values[idx], TOP),
        "tipo_doc": np.repeat(docs.tipo_doc.values[idx], TOP),
        "rank": np.tile(np.arange(1, TOP + 1), len(idx)),
        "desafio_id": des.desafio_id.values[ordem.ravel()],
        "sim": sims.ravel().round(4),
    })
    # confiança: terços do cosseno do 1º desafio, por tipo de documento
    lim = out[out["rank"] == 1].groupby("tipo_doc").sim.quantile([1 / 3, 2 / 3]).unstack()
    lo, hi = out.tipo_doc.map(lim[1 / 3]), out.tipo_doc.map(lim[2 / 3])
    out["confianca"] = np.select([out.sim >= hi, out.sim >= lo], ["alta", "media"], "baixa")
    out = out.drop(columns="tipo_doc")

    des.to_parquet(PROC / "desafio.parquet", index=False)
    out.to_parquet(PROC / "doc_desafio.parquet", index=False)

    # amostra estratificada para conferência (1º desafio de cada documento)
    meta = pd.read_parquet(PROC / "documento.parquet", columns=["doc_uid", "tipo_doc", "ano", "titulo"])
    am = out[out["rank"] == 1].merge(meta, on="doc_uid").merge(
        des[["desafio_id", "portfolio", "desafio"]], on="desafio_id")
    am = am.groupby("confianca").sample(n=20, random_state=42)          # cada terço tem milhares de documentos
    am["correto"] = ""
    am[["confianca", "tipo_doc", "ano", "titulo", "desafio_id", "portfolio", "desafio", "sim", "correto"]] \
        .to_csv(RAIZ / "relatorios" / "programacao_amostra.csv", index=False, encoding="utf-8-sig")

    n = docs.iloc[idx].tipo_doc.value_counts()
    print(f"Documentos na programação (desde {CORTE}): " + ", ".join(f"{k} " + f"{v:,}".replace(",", ".") for k, v in n.items()))
    print(out[out["rank"] == 1].confianca.value_counts().to_string())


if __name__ == "__main__":
    main()
