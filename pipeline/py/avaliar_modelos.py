"""Compara modelos de embeddings no gold set tecnologia → publicação citada.

Para cada tecnologia, ranqueia um conjunto de publicações (as citadas + uma
amostra aleatória) por similaridade de cosseno e mede se as citadas aparecem
no topo. Também mede a velocidade, para estimar o tempo da execução completa.

Uso (na raiz do projeto):
    .venv-nlp/Scripts/python pipeline/py/avaliar_modelos.py [tamanho_amostra]
Resultado: relatorios/avaliacao_modelos.md
"""

import sys
import time
from datetime import datetime

import numpy as np
import torch
from sentence_transformers import SentenceTransformer

from textos import RAIZ, carregar_textos, gold_tecnologia_publicacao

MODELOS = {
    "paraphrase-multilingual-MiniLM-L12-v2": dict(nome="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
                                                  prefixo="", max_len=256),
    "multilingual-e5-base": dict(nome="intfloat/multilingual-e5-base", prefixo="query: ", max_len=512),
    "bge-m3": dict(nome="BAAI/bge-m3", prefixo="", max_len=512),
}
AMOSTRA = int(sys.argv[1]) if len(sys.argv) > 1 else 5000
SEMENTE = 42


def main() -> None:
    torch.set_num_threads(max(torch.get_num_threads(), 8))
    docs = carregar_textos().set_index("doc_uid")
    gold = gold_tecnologia_publicacao()
    gold = gold[gold.tecnologia.isin(docs.index) & gold.obra.isin(docs.index)]
    tecs = gold.tecnologia.unique()
    citadas = set(gold.obra)
    outras = docs[(docs.tipo_doc == "publicacao") & ~docs.index.isin(citadas)]
    pool = list(citadas) + outras.sample(AMOSTRA, random_state=SEMENTE).index.tolist()
    print(f"{len(tecs)} tecnologias · {len(gold)} citações · conjunto de {len(pool)} publicações", flush=True)
    n_total = len(docs)

    linhas = []
    for rotulo, cfg in MODELOS.items():
        print(f"\n== {rotulo}", flush=True)
        t0 = time.time()
        modelo = SentenceTransformer(cfg["nome"], device="cpu")
        modelo.max_seq_length = cfg["max_len"]
        t_carga = time.time() - t0

        def emb(ids):
            textos = [cfg["prefixo"] + docs.at[i, "texto"] for i in ids]
            return modelo.encode(textos, batch_size=32, normalize_embeddings=True,
                                 show_progress_bar=True, convert_to_numpy=True)

        t1 = time.time()
        e_pool = emb(pool)
        e_tec = emb(tecs)
        t_enc = time.time() - t1
        docs_s = (len(pool) + len(tecs)) / t_enc

        sim = e_tec @ e_pool.T
        pos = {d: i for i, d in enumerate(pool)}
        ordem = np.argsort(-sim, axis=1)
        rank_de = np.empty_like(ordem)
        rank_de[np.arange(len(tecs))[:, None], ordem] = np.arange(ordem.shape[1])
        ranks = np.array([rank_de[list(tecs).index(t), pos[o]] + 1 for t, o in zip(gold.tecnologia, gold.obra)])
        linhas.append(dict(modelo=rotulo, r10=(ranks <= 10).mean(), r50=(ranks <= 50).mean(),
                           mrr=(1 / ranks).mean(), mediana=int(np.median(ranks)), docs_s=docs_s,
                           horas=n_total / docs_s / 3600, carga=t_carga))
        print(f"recall@10={linhas[-1]['r10']:.1%} · MRR={linhas[-1]['mrr']:.3f} · {docs_s:.1f} docs/s", flush=True)
        del modelo

    md = [f"# Avaliação de modelos de embeddings — {datetime.now():%Y-%m-%d %H:%M}", "",
          f"Tarefa: para cada uma de {len(tecs)} tecnologias, encontrar as publicações que ela cita no portal "
          f"({len(gold)} citações) entre {len(pool)} publicações ({len(citadas)} citadas + {AMOSTRA} sorteadas).",
          "Texto: título + resumo/descrição + palavras-chave. CPU, lotes de 32.", "",
          "| Modelo | recall@10 | recall@50 | MRR | posição mediana | docs/s | horas p/ base completa |",
          "|---|---|---|---|---|---|---|"]
    for l in linhas:
        md.append(f"| {l['modelo']} | {l['r10']:.1%} | {l['r50']:.1%} | {l['mrr']:.3f} | {l['mediana']} | "
                  f"{l['docs_s']:.1f} | {l['horas']:.1f} |")
    md += ["", "**recall@10**: % das publicações citadas que aparecem entre as 10 mais parecidas com a tecnologia. "
           "**MRR**: média de 1/posição (1 = sempre em 1º). "
           f"**Horas p/ base completa**: estimativa para os {n_total:,} documentos nesta máquina.".replace(",", ".")]
    saida = RAIZ / "relatorios" / "avaliacao_modelos.md"
    saida.write_text("\n".join(md) + "\n", encoding="utf-8")
    print("\n" + "\n".join(md))


if __name__ == "__main__":
    main()
