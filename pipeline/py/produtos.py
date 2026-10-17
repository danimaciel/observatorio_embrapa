"""Produtos agropecuários mencionados nos documentos (taxonomia ref/produtos.csv, base IBGE PAM/PPM/PEVS).

Casa os termos de cada produto no título, resumo e palavras-chave (sem acento, minúsculas, palavra inteira;
"*" no fim do termo = qualquer terminação). Termos ambíguos ("manga", "mel", "pera"...) só contam se o texto
tiver uma das palavras da coluna `contexto`. Onde o termo apareceu fica registrado (título, palavras-chave ou
resumo): título ou palavras-chave = produto "principal"; só no resumo = "citado".

Antes de procurar, o texto perde os nomes das unidades da Embrapa (ref/unidade.csv, ref/unidade_alias.csv e
"Centro Nacional de Pesquisa de ..."): sem isso, "Embrapa Soja" ou "Embrapa Gado de Leite" marcariam o produto
em qualquer texto que só cita a unidade.

Saídas em data/processed/:
  doc_produto.parquet   doc_uid, produto_id, produto, categoria_ampla, grupo_atividade, onde, forca, n_mencoes
  e relatorios/produtos_piloto.md (cobertura, produtos mais citados) + relatorios/produtos_amostra.csv (validação)
"""
import re
import sys
import unicodedata
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from textos import RAIZ  # noqa: E402

PROC = RAIZ / "data" / "processed"


def sem_acento(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", str(s).lower()) if unicodedata.category(c) != "Mn")


def padrao(termos: str) -> re.Pattern:
    partes = []
    for t in filter(None, (x.strip() for x in termos.split("|"))):
        t = sem_acento(t)
        partes.append(re.escape(t[:-1]) + r"[a-z]*" if t.endswith("*") else re.escape(t))
    # palavra inteira e fora de palavra composta: "açoita-cavalo" não é cavalo, "batata-doce" não é batata
    return re.compile(r"(?<![\w-])(?:" + "|".join(sorted(partes, key=len, reverse=True)) + r")(?![\w-])")


def removedor_unidades() -> re.Pattern:
    nomes = pd.read_csv(RAIZ / "ref" / "unidade.csv", dtype=str).nome_atual.dropna().tolist()
    nomes += pd.read_csv(RAIZ / "ref" / "unidade_alias.csv", dtype=str).alias.dropna().tolist()
    nomes = sorted({sem_acento(n).strip() for n in nomes if n.lower().startswith("embrapa ")}, key=len, reverse=True)
    antigos = r"centro nacional de pesquisa (?:de|do|da|em)\s+(?:\w+[\s,-]*){1,5}?(?=[.,;:()]|$)"
    return re.compile(r"\b(?:" + "|".join(map(re.escape, nomes)) + r")\b|" + antigos)


def main() -> None:
    tax = pd.read_csv(RAIZ / "ref" / "produtos.csv", dtype=str).fillna("")
    regras = []
    for r in tax.itertuples():
        termos = r.termos + ("|" + r.cientifico.replace("; ", "|") if r.cientifico else "")
        regras.append((r, padrao(termos), padrao(r.contexto) if r.contexto else None,
                       re.compile("|".join(map(re.escape, r.excluir.split("|")))) if r.excluir else None))

    doc = pd.read_parquet(PROC / "documento.parquet", columns=["doc_uid", "tipo_doc", "titulo", "resumo"])
    kw = pd.read_parquet(PROC / "documento_keyword.parquet", columns=["doc_uid", "keyword_raw"])
    kw = kw.groupby("doc_uid").keyword_raw.agg(lambda s: " ; ".join(dict.fromkeys(s)))
    doc["palavras"] = doc.doc_uid.map(kw).fillna("")
    tira_unidade = removedor_unidades()
    for c in ("titulo", "resumo", "palavras"):
        doc[c + "_n"] = doc[c].fillna("").map(lambda t: tira_unidade.sub(" ", sem_acento(t)))

    linhas = []
    for d in doc.itertuples(index=False):
        tudo = f"{d.titulo_n} \n {d.palavras_n} \n {d.resumo_n}"
        for r, rx, ctx, excl in regras:
            texto = excl.sub(" ", tudo) if excl else tudo
            achados = rx.findall(texto)
            if not achados or (ctx is not None and not ctx.search(texto)):
                continue
            ex = (lambda t: excl.sub(" ", t)) if excl else (lambda t: t)
            onde = "titulo" if rx.search(ex(d.titulo_n)) else "palavras" if rx.search(ex(d.palavras_n)) else "resumo"
            forca = "principal" if onde in ("titulo", "palavras") else "citado"
            linhas.append((d.doc_uid, r.produto_id, r.produto, r.categoria_ampla, r.grupo_atividade, onde, forca, len(achados)))
    dp = pd.DataFrame(linhas, columns=["doc_uid", "produto_id", "produto", "categoria_ampla", "grupo_atividade", "onde", "forca", "n_mencoes"])
    dp.to_parquet(PROC / "doc_produto.parquet", index=False)

    # relatório de cobertura e amostra para validação humana
    rel = RAIZ / "relatorios"
    rel.mkdir(exist_ok=True)
    tipo = doc.set_index("doc_uid").tipo_doc
    cob = (dp.drop_duplicates("doc_uid").doc_uid.map(tipo).value_counts() / doc.tipo_doc.value_counts() * 100).round(1)
    top = dp.groupby("produto").doc_uid.nunique().sort_values(ascending=False)
    cat = dp.groupby("categoria_ampla").doc_uid.nunique().sort_values(ascending=False)
    exp = (pd.read_parquet(PROC / "meta.parquet").iloc[0, 0] if (PROC / "meta.parquet").exists() else "?")
    md = ["# Produtos agropecuários nos documentos (piloto)", "",
          f"Exportação {exp}. Taxonomia `ref/produtos.csv` ({len(tax)} produtos). Texto: título + resumo + palavras-chave.", "",
          f"- Documentos com ao menos um produto: {dp.doc_uid.nunique():,} de {len(doc):,}",
          f"- Pares documento × produto: {len(dp):,} (principal: {(dp.forca == 'principal').sum():,}; citado: {(dp.forca == 'citado').sum():,})",
          f"- Documentos com produto principal (título ou palavras-chave): {dp[dp.forca == 'principal'].doc_uid.nunique():,}", "",
          "## Cobertura por tipo de documento (%)", cob.rename_axis("tipo").reset_index(name="%").to_markdown(index=False), "",
          "## Documentos por categoria ampla", cat.rename_axis("categoria").reset_index(name="documentos").to_markdown(index=False), "",
          "## 40 produtos mais citados", top.head(40).rename_axis("produto").reset_index(name="documentos").to_markdown(index=False)]
    (rel / "produtos_piloto.md").write_text("\n".join(md), encoding="utf-8")
    amostra = pd.concat([g.sample(min(len(g), 50), random_state=42) for _, g in dp.groupby("onde")])
    amostra = amostra.merge(doc[["doc_uid", "titulo", "resumo"]], on="doc_uid")
    amostra["resumo"] = amostra.resumo.fillna("").str.slice(0, 400)
    amostra["correto"] = ""
    amostra.to_csv(rel / "produtos_amostra.csv", index=False, encoding="utf-8")
    print("\n".join(md[:6]))


if __name__ == "__main__":
    main()
