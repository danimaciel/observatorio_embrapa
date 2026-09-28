"""Exporta os textos que ainda não têm embedding, para calcular no Google Colab (GPU).

Uso (na raiz do projeto):
    .venv-nlp/Scripts/python pipeline/py/exportar_textos.py [--partes N]
Gera data/interim/textos_para_embeddings_parteXXdeYY.parquet — suba todas as
partes no notebook pipeline/colab/embeddings_colab.ipynb. Por padrão, as
partes têm até ~7 MB (facilita o envio pelo navegador).
"""

import argparse
import math

from embeddings_cache import DIR, ler_cache, textos_para_modelo

ap = argparse.ArgumentParser()
ap.add_argument("--partes", type=int, default=None, help="número de partes (padrão: automático, ~7 MB cada)")
args = ap.parse_args()

d = textos_para_modelo()
cache, _ = ler_cache()
faltam = d[~d.hash.isin(set(cache.hash))][["doc_uid", "hash", "texto_modelo"]].reset_index(drop=True)
destino = DIR.parent
destino.mkdir(parents=True, exist_ok=True)
for antigo in destino.glob("textos_para_embeddings*.parquet"):
    antigo.unlink()

bytes_por_doc = 300  # ~52 MB / 181 mil docs, comprimido
n = args.partes or max(1, math.ceil(len(faltam) * bytes_por_doc / (7 * 1024**2)))
tam = math.ceil(len(faltam) / n) if len(faltam) else 0
for i in range(n):
    parte = faltam.iloc[i * tam:(i + 1) * tam]
    arq = destino / f"textos_para_embeddings_parte{i + 1:02d}de{n:02d}.parquet"
    parte.to_parquet(arq, index=False, compression="zstd")
    print(f"{arq.name}: " + f"{len(parte):,} docs; {arq.stat().st_size / 1024**2:.1f} MB".replace(",", "."))
print(f"Total: {len(faltam):,} de {len(d):,} documentos sem embedding".replace(",", "."))
