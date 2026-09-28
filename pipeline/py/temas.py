"""Temas com BERTopic sobre os embeddings (desenho, §8).

1. Ajuste numa amostra equilibrada: todos os projetos e tecnologias + uma
   amostra de publicações com resumo (evita que as publicações, muito mais
   numerosas, dominem os temas).
2. Atribuição de TODOS os documentos ao tema de centróide mais próximo
   (cosseno) — inclusive os "outliers" do HDBSCAN.
3. Rótulos por c-TF-IDF recalculados sobre a base inteira.
4. Macrotemas: agrupamento hierárquico dos centróides dos temas.

O modelo só é reajustado com --reajustar (ex.: uma vez por ano). Sem isso,
os documentos são atribuídos aos centróides já salvos, mantendo os temas
(e rótulos curados) estáveis entre as atualizações mensais.

Saídas em data/processed/: tema.parquet, doc_tema.parquet
Estado do modelo em data/interim/temas/ (centróides e temas).
Rótulos curados (opcional): ref/temas_rotulos.csv (tema_id, rotulo)

Uso: .venv-nlp/Scripts/python pipeline/py/temas.py [--reajustar]
"""

import argparse
import time

import numpy as np
import pandas as pd

from textos import PROC, RAIZ, carregar_textos
from vetores import carregar_vetores

AMOSTRA_PUB = 40_000
MIN_CLUSTER = 60
N_MACRO = 25
SEMENTE = 42
ESTADO = RAIZ / "data" / "interim" / "temas"


def stopwords() -> list[str]:
    linhas = (RAIZ / "ref" / "stopwords_pt.txt").read_text(encoding="utf-8").splitlines()
    return sorted({l.strip().lower() for l in linhas if l.strip() and not l.startswith("#")})


def vetorizador():
    from sklearn.feature_extraction.text import CountVectorizer
    return CountVectorizer(stop_words=stopwords(), ngram_range=(1, 2), min_df=5, max_df=0.4,
                           token_pattern=r"(?u)\b[^\W\d_]{3,}\b", lowercase=True)


def termos_por_grupo(textos: pd.Series, grupos: np.ndarray, n: int = 10) -> dict[int, list[str]]:
    """c-TF-IDF (classe = grupo) sobre textos agregados por grupo."""
    from bertopic.vectorizers import ClassTfidfTransformer
    agreg = pd.DataFrame({"t": textos.values, "g": grupos}).groupby("g").t.apply(" ".join)
    cv = vetorizador()
    X = cv.fit_transform(agreg.values)
    c = ClassTfidfTransformer(reduce_frequent_words=True).fit_transform(X)
    vocab = np.array(cv.get_feature_names_out())
    out = {}
    for i, g in enumerate(agreg.index):
        linha = c[i].toarray().ravel()
        out[int(g)] = vocab[np.argsort(-linha)[:n]].tolist()
    return out


def ajustar(docs: pd.DataFrame, V: np.ndarray, textos: pd.Series) -> np.ndarray:
    from bertopic import BERTopic
    from hdbscan import HDBSCAN
    from umap import UMAP

    rng = np.random.default_rng(SEMENTE)
    base = np.where(docs.tipo_doc.isin(["projeto", "tecnologia"]))[0]
    pubs = np.where((docs.tipo_doc == "publicacao") & ~docs.texto_curto)[0]
    amostra = np.concatenate([base, rng.choice(pubs, min(AMOSTRA_PUB, len(pubs)), replace=False)])
    print(f"Ajuste em {len(amostra):,} documentos".replace(",", "."), flush=True)

    modelo = BERTopic(
        umap_model=UMAP(n_neighbors=15, n_components=5, min_dist=0.0, metric="cosine", random_state=SEMENTE),
        hdbscan_model=HDBSCAN(min_cluster_size=MIN_CLUSTER, min_samples=10, metric="euclidean",
                              cluster_selection_method="eom", prediction_data=False),
        vectorizer_model=vetorizador(), calculate_probabilities=False, verbose=True)
    topicos, _ = modelo.fit_transform(textos.iloc[amostra].tolist(), embeddings=V[amostra])
    topicos = np.array(topicos)
    ids = sorted(t for t in set(topicos) if t != -1)
    C = np.vstack([V[amostra][topicos == t].mean(axis=0) for t in ids])
    C /= np.linalg.norm(C, axis=1, keepdims=True)
    print(f"{len(ids)} temas · {np.mean(topicos == -1):.0%} da amostra como outlier", flush=True)
    return C


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--reajustar", action="store_true")
    args = ap.parse_args()
    t0 = time.time()

    docs, V = carregar_vetores(calibrar=True)
    tx = carregar_textos().set_index("doc_uid")
    docs["texto_curto"] = docs.doc_uid.map(tx.texto_curto).fillna(True).values
    textos = docs.doc_uid.map(tx.texto_rotulo).fillna("")

    ESTADO.mkdir(parents=True, exist_ok=True)
    arq_c = ESTADO / "centroides.npy"
    if args.reajustar or not arq_c.exists():
        C = ajustar(docs, V, textos)
        # macrotemas: agrupamento hierárquico dos centróides
        from sklearn.cluster import AgglomerativeClustering
        macro = AgglomerativeClustering(n_clusters=min(N_MACRO, len(C)), linkage="ward").fit_predict(C)
        np.save(arq_c, C)
        np.save(ESTADO / "macro.npy", macro)
    else:
        C, macro = np.load(arq_c), np.load(ESTADO / "macro.npy")
        print(f"Usando {len(C)} temas salvos (sem reajuste)", flush=True)

    # atribuição de todos os documentos ao tema mais próximo
    tema = np.empty(len(docs), dtype=np.int32)
    score = np.empty(len(docs), dtype=np.float32)
    for s in range(0, len(docs), 8192):
        S = V[s:s + 8192] @ C.T
        tema[s:s + 8192] = S.argmax(1)
        score[s:s + 8192] = S.max(1)
    macro_doc = macro[tema]

    termos = termos_por_grupo(textos, tema)
    termos_macro = termos_por_grupo(textos, macro_doc)
    curados = {}
    arq_rot = RAIZ / "ref" / "temas_rotulos.csv"
    if arq_rot.exists():
        r = pd.read_csv(arq_rot)
        curados = dict(zip(r.tema_id.astype(str), r.rotulo))

    def rotulo(ts, n=4):
        """Até n termos, pulando os já cobertos (ex.: 'spodoptera frugiperda' após 'spodoptera')."""
        escolhidos, vistos = [], set()
        for t in ts:
            palavras = set(t.split())
            if len(palavras) < len(t.split()) or palavras <= vistos:   # "irrigação irrigação" ou já coberto
                continue
            escolhidos = [e for e in escolhidos if not set(e.split()) < palavras]
            escolhidos.append(t)
            vistos |= palavras
            if len(escolhidos) == n:
                break
        return ", ".join(escolhidos).capitalize()

    cont = pd.crosstab(tema, docs.tipo_doc.values)
    linhas = []
    for t in range(len(C)):
        tid = f"T{t:03d}"
        linhas.append(dict(tema_id=tid, nivel=2, pai_id=f"M{macro[t]:02d}",
                           rotulo=curados.get(tid, rotulo(termos.get(t, []))),
                           termos=", ".join(termos.get(t, [])),
                           n_projeto=int(cont.loc[t].get("projeto", 0)) if t in cont.index else 0,
                           n_publicacao=int(cont.loc[t].get("publicacao", 0)) if t in cont.index else 0,
                           n_tecnologia=int(cont.loc[t].get("tecnologia", 0)) if t in cont.index else 0))
    tamanho = pd.Series(tema).value_counts()
    for m in sorted(set(macro)):
        mid = f"M{m:02d}"
        # nome do macrotema: termo principal dos seus 3 maiores temas
        filhos = sorted([t for t in range(len(C)) if macro[t] == m], key=lambda t: -tamanho.get(t, 0))[:3]
        nome = " · ".join(dict.fromkeys(rotulo(termos.get(t, []), n=1) for t in filhos))
        linhas.append(dict(tema_id=mid, nivel=1, pai_id=None,
                           rotulo=curados.get(mid, nome),
                           termos=", ".join(termos_macro.get(int(m), [])),
                           n_projeto=int(((macro_doc == m) & (docs.tipo_doc == "projeto")).sum()),
                           n_publicacao=int(((macro_doc == m) & (docs.tipo_doc == "publicacao")).sum()),
                           n_tecnologia=int(((macro_doc == m) & (docs.tipo_doc == "tecnologia")).sum())))
    tema_df = pd.DataFrame(linhas)
    tema_df.to_parquet(PROC / "tema.parquet", index=False)

    # Planilha de curadoria: preencha "rotulo" nas linhas que quiser renomear e
    # copie tema_id + rotulo para ref/temas_rotulos.csv (aplicado na próxima execução).
    cur = tema_df.assign(macrotema=tema_df.pai_id.map(tema_df.set_index("tema_id").rotulo),
                         rotulo_automatico=tema_df.rotulo, rotulo="")
    cur = cur.sort_values(["nivel", "pai_id", "tema_id"], na_position="first")
    cur[["tema_id", "nivel", "macrotema", "rotulo_automatico", "termos", "n_projeto", "n_publicacao",
         "n_tecnologia", "rotulo"]].to_csv(RAIZ / "relatorios" / "temas_para_curadoria.csv", index=False,
                                          encoding="utf-8-sig")
    pd.DataFrame({"doc_uid": docs.doc_uid, "tema_id": [f"T{t:03d}" for t in tema],
                  "macro_id": [f"M{m:02d}" for m in macro_doc], "score": score.round(4)}) \
        .to_parquet(PROC / "doc_tema.parquet", index=False)
    print(f"{(tema_df.nivel == 2).sum()} temas em {(tema_df.nivel == 1).sum()} macrotemas · "
          f"{time.time() - t0:.0f}s", flush=True)
    print(tema_df[tema_df.nivel == 1].sort_values("n_publicacao", ascending=False)[["tema_id", "rotulo"]]
          .to_string(index=False))


if __name__ == "__main__":
    main()
