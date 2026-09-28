"""Exporta os textos que ainda não têm embedding, para calcular no Google Colab (GPU).

Uso (na raiz do projeto):
    .venv-nlp/Scripts/python pipeline/py/exportar_textos.py
Gera data/interim/textos_para_embeddings.parquet — suba esse arquivo no
notebook pipeline/colab/embeddings_colab.ipynb.
"""

from embeddings_cache import DIR, ler_cache, textos_para_modelo

d = textos_para_modelo()
cache, _ = ler_cache()
faltam = d[~d.hash.isin(set(cache.hash))]
saida = DIR.parent / "textos_para_embeddings.parquet"
saida.parent.mkdir(parents=True, exist_ok=True)
faltam[["doc_uid", "hash", "texto_modelo"]].to_parquet(saida, index=False, compression="zstd")
print(f"{len(faltam):,} de {len(d):,} documentos sem embedding → {saida} "
      f"({saida.stat().st_size / 1024**2:.1f} MB)".replace(",", "."))
