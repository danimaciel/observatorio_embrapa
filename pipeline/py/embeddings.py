"""Atualiza o cache de embeddings (incremental).

1. Importa resultados do Colab, se houver em data/interim/embeddings/colab/
   (arquivos embeddings_colab.npy + embeddings_colab_ids.parquet).
2. Calcula na CPU os documentos novos ou alterados que ainda faltarem.
3. Remove do cache documentos que não existem mais.

Uso (na raiz do projeto):
    .venv-nlp/Scripts/python pipeline/py/embeddings.py [--limite N]
Com --limite, calcula no máximo N documentos na CPU (o restante fica para
a próxima execução ou para o Colab).
"""

import argparse
import time

import numpy as np
import pandas as pd

from embeddings_cache import DIR, MAX_TOKENS, MODELO, gravar_cache, ler_cache, textos_para_modelo


def importar_colab(ids: pd.DataFrame, vet: np.ndarray) -> tuple[pd.DataFrame, np.ndarray]:
    pasta = DIR / "colab"
    arq_ids, arq_vet = pasta / "embeddings_colab_ids.parquet", pasta / "embeddings_colab.npy"
    if not arq_ids.exists():
        return ids, vet
    novos_ids, novos_vet = pd.read_parquet(arq_ids), np.load(arq_vet)
    assert len(novos_ids) == len(novos_vet), "arquivos do Colab inconsistentes"
    manter = ~ids.hash.isin(set(novos_ids.hash))
    print(f"Importando {len(novos_ids):,} vetores do Colab".replace(",", "."))
    ids = pd.concat([ids[manter], novos_ids[["doc_uid", "hash"]]], ignore_index=True)
    vet = np.vstack([vet[manter.values], novos_vet.astype(np.float16)])
    for f in (arq_ids, arq_vet):
        f.rename(f.with_name(f.stem + "_importado" + f.suffix))
    return ids, vet


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limite", type=int, default=None)
    args = ap.parse_args()

    d = textos_para_modelo()
    ids, vet = ler_cache()
    ids, vet = importar_colab(ids, vet)

    # descarta vetores de documentos removidos ou com texto alterado
    validos = ids.hash.isin(set(d.hash)).values
    ids, vet = ids[validos].reset_index(drop=True), vet[validos]
    ids = ids.drop_duplicates("hash")
    vet = vet[ids.index.values]
    ids = ids.reset_index(drop=True)

    faltam = d[~d.hash.isin(set(ids.hash))]
    if args.limite is not None:
        faltam = faltam.head(args.limite)
    print(f"Cache: {len(ids):,} documentos · faltam {len(faltam):,}".replace(",", "."), flush=True)

    if len(faltam):
        import torch
        from sentence_transformers import SentenceTransformer
        torch.set_num_threads(max(torch.get_num_threads(), 8))
        modelo = SentenceTransformer(MODELO, device="cpu")
        modelo.max_seq_length = MAX_TOKENS
        t0 = time.time()
        novos = modelo.encode(faltam.texto_modelo.tolist(), batch_size=32, normalize_embeddings=True,
                              show_progress_bar=True, convert_to_numpy=True)
        print(f"{len(faltam) / (time.time() - t0):.1f} docs/s", flush=True)
        ids = pd.concat([ids, faltam[["doc_uid", "hash"]]], ignore_index=True)
        vet = np.vstack([vet, novos.astype(np.float16)])

    gravar_cache(ids, vet)
    cobertura = d.hash.isin(set(ids.hash)).mean()
    print(f"Cache gravado: {len(ids):,} vetores · cobertura {cobertura:.1%}".replace(",", "."))


if __name__ == "__main__":
    main()
