"""Arquivo público de resultados para outros projetos (iAgro): produtos, localização e temas de cada documento,
e quem trabalha com cada produto e tema.

Só resultados analíticos e informação que já é pública nas publicações e projetos do Redape. Nada da base
interna de pessoas além do nome de exibição e da unidade (sem matrícula, contato ou id interno).
  data/processed/enriquecimento.csv.gz  doc_uid (OB:/P:/T:), produtos (principais, ids separados por ";"),
                                        produtos_citados, ufs, municipios (cod_ibge), biomas, tema, macrotema
  data/processed/registro_obra.csv.gz   registro de publicação (B:id, um por unidade depositante) → obra (OB:id)
  data/processed/produtos.csv           cópia da taxonomia (produto_id → nome, categoria, grupo, fonte IBGE)
  data/processed/temas.csv              tema_id (T###) e macrotema (M##) → rótulo (BERTopic, rótulos curados)
  data/processed/pessoas.csv.gz         pessoa (id público), nome, unidade_id, unidade (nome), n_docs, ano_ultimo
  data/processed/pessoa_produto.csv.gz  pessoa × produto (só força principal): indicadores e evidências
  data/processed/pessoa_tema.csv.gz     pessoa × tema (T###): mesmos indicadores
  data/processed/evidencias.csv.gz      doc_uid, tipo_doc, titulo, ano, url dos documentos citados como evidência
  data/processed/rede_produto_tema.csv.gz  produto × tema: n_docs, n_recentes, palavras-chave típicas e documentos
                                        de exemplo (rede por produto da Rede iAgro)
  data/processed/rede_vizinhos.csv.gz   produto × produto vizinho (documentos em comum, força principal)
  data/processed/documentos_rede.csv.gz doc_uid, tipo_doc, titulo, ano, url, unidade_id dos documentos de exemplo
Rede por produto (outubro de 2026):
  - Pares produto (força principal) × tema com ao menos 3 documentos; até 12 temas por produto.
  - Palavras-chave típicas do par: peso = n no par × log(N / n no acervo), ao menos 2 ocorrências no par,
    sem os termos de busca do próprio produto; até 8 por par.
  - Documentos de exemplo: os mais recentes do par, até 12 publicações, 4 projetos e 4 soluções.
  - Vizinhos: os 8 produtos com mais documentos em comum (ao menos 3), para navegar de um produto a outro.
Publicado a cada mês como release pública "enriquecimento-AAAA-MM" em danimaciel/observatorio_embrapa
(ver skill atualizacao-mensal). Consumido por danimaciel/iagro-embrapa, iagro (Rede iAgro) e iagro-conversa.

"Quem trabalha com isso" (critérios de outubro de 2026):
  - Só vínculos de confiança A, B ou M (documento_pessoa) e pessoas com unidade da Embrapa.
  - Peso por documento: projeto liderado 3, solução tecnológica 2 (autor de obra citada pela solução,
    pessoa_tecnologia), publicação ou participação em projeto 1; documentos com mais de 10 anos valem metade.
  - foco = documentos da pessoa no produto/tema ÷ todos os documentos da pessoa.
  - Entra só quem tem ao menos 3 documentos no produto/tema, sendo 1 dos últimos 10 anos.
  - Evidências: até 5 documentos (mais recentes e de maior peso) para mostrar ao lado do nome.
"""
import hashlib
import shutil
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from textos import RAIZ  # noqa: E402

PROC = RAIZ / "data" / "processed"

PESO_PAPEL = {"lider": 3, "tecnologia": 2, "autor": 1, "membro": 1}
JANELA_ANOS = 10
MIN_DOCS, MIN_RECENTES, N_EVIDENCIAS = 3, 1, 5
TEMAS_POR_PRODUTO, PALAVRAS_POR_PAR = 12, 8
EXEMPLOS = {"publicacao": 12, "projeto": 4, "tecnologia": 4}


def juntar(s: pd.Series) -> str:
    return ";".join(sorted(set(map(str, s.dropna()))))


def id_publico(pessoa_id: str) -> str:
    """Id estável e público: não expõe o id da base interna de autores."""
    return "PS" + hashlib.sha1(pessoa_id.encode("utf-8")).hexdigest()[:10]


def vinculos(doc: pd.DataFrame) -> pd.DataFrame:
    """Uma linha por pessoa × documento, com o maior peso entre os papéis e o fator de recência."""
    dp = pd.read_parquet(PROC / "documento_pessoa.parquet", columns=["doc_uid", "pessoa_id", "papel", "nivel"])
    dp = dp[dp.nivel.isin(["A", "B", "M"]) & dp.pessoa_id.notna()]
    pt = pd.read_parquet(PROC / "pessoa_tecnologia.parquet", columns=["pessoa_id", "tecnologia_uid"])
    pt = pt.rename(columns={"tecnologia_uid": "doc_uid"}).assign(papel="tecnologia")
    v = pd.concat([dp[["doc_uid", "pessoa_id", "papel"]], pt[["doc_uid", "pessoa_id", "papel"]]])
    v["peso"] = v.papel.map(PESO_PAPEL).fillna(1)
    v = v.groupby(["pessoa_id", "doc_uid"], as_index=False).agg(peso=("peso", "max"),
                                                                 lider=("papel", lambda p: (p == "lider").any()),
                                                                 tecnologia=("papel", lambda p: (p == "tecnologia").any()))
    v = v.merge(doc[["doc_uid", "ano"]], on="doc_uid", how="inner")
    ano_ref = int(doc.ano.max())
    v["recente"] = v.ano >= ano_ref - JANELA_ANOS + 1
    v["peso"] = v.peso * v.recente.map({True: 1.0, False: 0.5})
    return v


def por_eixo(v: pd.DataFrame, eixo: pd.DataFrame, col: str, total: pd.Series) -> pd.DataFrame:
    """Indicadores de pessoa × (produto ou tema), com as salvaguardas mínimas."""
    x = v.merge(eixo, on="doc_uid")
    g = x.groupby(["pessoa_id", col])
    r = g.agg(n_docs=("doc_uid", "nunique"), n_recentes=("recente", "sum"),
              n_projetos_lider=("lider", "sum"), n_tecnologias=("tecnologia", "sum"), peso=("peso", "sum"))
    r = r[(r.n_docs >= MIN_DOCS) & (r.n_recentes >= MIN_RECENTES)].reset_index()
    r["foco"] = (r.n_docs / r.pessoa_id.map(total)).round(3)
    r["peso"] = r.peso.round(2)
    ev = (x.sort_values(["recente", "peso", "ano"], ascending=False)
           .groupby(["pessoa_id", col]).doc_uid.agg(lambda s: ";".join(s.head(N_EVIDENCIAS))))
    r["evidencias"] = [ev.get((p, c), "") for p, c in zip(r.pessoa_id, r[col])]
    return r.sort_values([col, "peso"], ascending=[True, False])


def rede_produto_tema(doc: pd.DataFrame, dp: pd.DataFrame, dt: pd.DataFrame) -> tuple[pd.DataFrame, set]:
    """Produto × tema com contagens, palavras-chave típicas e documentos de exemplo."""
    pt = (dp.loc[dp.forca == "principal", ["doc_uid", "produto_id"]].drop_duplicates()
          .merge(dt[["doc_uid", "tema_id"]], on="doc_uid")
          .merge(doc[["doc_uid", "tipo_doc", "ano"]], on="doc_uid"))
    ano_ref = int(doc.ano.max())
    pt["recente"] = pt.ano >= ano_ref - JANELA_ANOS + 1
    par = pt.groupby(["produto_id", "tema_id"]).agg(n_docs=("doc_uid", "nunique"), n_recentes=("recente", "sum"))
    par = par[par.n_docs >= MIN_DOCS].reset_index().sort_values(["produto_id", "n_docs"], ascending=[True, False])
    par = par.groupby("produto_id").head(TEMAS_POR_PRODUTO)

    kw = pd.read_parquet(PROC / "documento_keyword.parquet", columns=["doc_uid", "keyword_norm", "keyword_raw"])
    kw = kw.drop_duplicates(["doc_uid", "keyword_norm"])
    idf = np.log(doc.doc_uid.nunique() / kw.groupby("keyword_norm").doc_uid.nunique())
    rotulo = kw.groupby("keyword_norm").keyword_raw.agg(lambda s: s.str.lower().mode().iat[0])
    tax = pd.read_csv(RAIZ / "ref" / "produtos.csv", dtype=str).fillna("").set_index("produto_id")
    proprios = {p: {t.strip("*").strip() for t in (tax.at[p, "termos"] + "|" + tax.at[p, "produto"].lower()).split("|")}
                if p in tax.index else set() for p in par.produto_id.unique()}
    pk = pt.merge(par[["produto_id", "tema_id"]]).merge(kw[["doc_uid", "keyword_norm"]], on="doc_uid")
    cont = pk.groupby(["produto_id", "tema_id", "keyword_norm"]).doc_uid.nunique().rename("n").reset_index()
    alheio = np.array([k not in proprios[p] for p, k in zip(cont.produto_id, cont.keyword_norm)], dtype=bool)
    cont = cont[(cont.n >= 2).to_numpy() & alheio]
    cont["peso"] = cont.n * cont.keyword_norm.map(idf)
    cont = cont.sort_values("peso", ascending=False).groupby(["produto_id", "tema_id"]).head(PALAVRAS_POR_PAR)
    palavras = cont.groupby(["produto_id", "tema_id"]).apply(
        lambda g: ";".join(f"{rotulo[k]}:{n}" for k, n in zip(g.keyword_norm, g.n)), include_groups=False)

    ex = pt.merge(par[["produto_id", "tema_id"]]).sort_values("ano", ascending=False)
    ex = ex[ex.groupby(["produto_id", "tema_id", "tipo_doc"]).cumcount() < ex.tipo_doc.map(EXEMPLOS).fillna(0)]
    docs = ex.groupby(["produto_id", "tema_id"]).doc_uid.agg(";".join)

    chave = list(zip(par.produto_id, par.tema_id))
    par["palavras"] = [palavras.get(c, "") for c in chave]
    par["docs"] = [docs.get(c, "") for c in chave]
    return par, set(ex.doc_uid)


def main() -> None:
    doc = pd.read_parquet(PROC / "documento.parquet",
                          columns=["doc_uid", "tipo_doc", "titulo", "ano", "url", "unidade_id"])
    dp = pd.read_parquet(PROC / "doc_produto.parquet")
    dm = pd.read_parquet(PROC / "doc_municipio.parquet")
    dm = dm[dm.confianca.isin(["alta", "media"])]
    de = pd.read_parquet(PROC / "doc_estado.parquet")
    db = pd.read_parquet(PROC / "doc_bioma.parquet")
    dt = pd.read_parquet(PROC / "doc_tema.parquet", columns=["doc_uid", "tema_id", "macro_id"])

    e = doc[["doc_uid"]].set_index("doc_uid")
    e["produtos"] = dp[dp.forca == "principal"].groupby("doc_uid").produto_id.agg(juntar)
    e["produtos_citados"] = dp[dp.forca == "citado"].groupby("doc_uid").produto_id.agg(juntar)
    e["ufs"] = de.groupby("doc_uid").uf.agg(juntar)
    e["municipios"] = dm.groupby("doc_uid").cod_ibge.agg(juntar)
    e["biomas"] = db.groupby("doc_uid").bioma.agg(juntar)
    e["tema"] = dt.set_index("doc_uid").tema_id
    e["macrotema"] = dt.set_index("doc_uid").macro_id
    e = e.dropna(how="all").reset_index()
    e.to_csv(PROC / "enriquecimento.csv.gz", index=False, encoding="utf-8")

    pub = pd.read_parquet(PROC / "publicacao.parquet", columns=["doc_uid", "obra_id"])
    pub.rename(columns={"doc_uid": "registro"}).to_csv(PROC / "registro_obra.csv.gz", index=False, encoding="utf-8")
    shutil.copy(RAIZ / "ref" / "produtos.csv", PROC / "produtos.csv")
    tema = pd.read_parquet(PROC / "tema.parquet", columns=["tema_id", "nivel", "pai_id", "rotulo"])
    tema.to_csv(PROC / "temas.csv", index=False, encoding="utf-8")

    # Quem trabalha com cada produto e tema
    pes = pd.read_parquet(PROC / "pessoa.parquet", columns=["pessoa_id", "nome_exibicao", "unidade_ref_id"])
    pes = pes[pes.unidade_ref_id.notna() & pes.nome_exibicao.notna()]
    v = vinculos(doc)
    v = v[v.pessoa_id.isin(pes.pessoa_id)]
    total = v.groupby("pessoa_id").doc_uid.nunique()
    pp = por_eixo(v, dp.loc[dp.forca == "principal", ["doc_uid", "produto_id"]].drop_duplicates(), "produto_id", total)
    ptm = por_eixo(v, dt[["doc_uid", "tema_id"]], "tema_id", total)

    listadas = set(pp.pessoa_id) | set(ptm.pessoa_id)
    p = pes[pes.pessoa_id.isin(listadas)].copy()
    p["n_docs"] = p.pessoa_id.map(total)
    p["ano_ultimo"] = p.pessoa_id.map(v.groupby("pessoa_id").ano.max())
    uni = pd.read_csv(RAIZ / "ref" / "unidade.csv", dtype=str).set_index("unidade_id").nome_atual
    p["unidade"] = p.unidade_ref_id.map(uni)
    ids = {k: id_publico(k) for k in p.pessoa_id}
    (p.assign(pessoa=p.pessoa_id.map(ids))
      .rename(columns={"nome_exibicao": "nome", "unidade_ref_id": "unidade_id"})
      [["pessoa", "nome", "unidade_id", "unidade", "n_docs", "ano_ultimo"]]
      .to_csv(PROC / "pessoas.csv.gz", index=False, encoding="utf-8"))
    for t, arq in ((pp, "pessoa_produto.csv.gz"), (ptm, "pessoa_tema.csv.gz")):
        t.assign(pessoa=t.pessoa_id.map(ids)).drop(columns="pessoa_id") \
         .pipe(lambda d: d[["pessoa"] + [c for c in d.columns if c != "pessoa"]]) \
         .to_csv(PROC / arq, index=False, encoding="utf-8")
    usados = set(";".join(pd.concat([pp.evidencias, ptm.evidencias])).split(";")) - {""}
    doc.loc[doc.doc_uid.isin(usados), ["doc_uid", "tipo_doc", "titulo", "ano", "url"]] \
       .to_csv(PROC / "evidencias.csv.gz", index=False, encoding="utf-8")

    # Rede por produto
    rede, exemplos = rede_produto_tema(doc, dp, dt)
    rede.to_csv(PROC / "rede_produto_tema.csv.gz", index=False, encoding="utf-8")
    pr = dp.loc[dp.forca == "principal", ["doc_uid", "produto_id"]].drop_duplicates()
    viz = pr.merge(pr, on="doc_uid", suffixes=("", "_viz"))
    viz = viz[viz.produto_id != viz.produto_id_viz].groupby(["produto_id", "produto_id_viz"]).size().rename("n")
    viz = viz[viz >= MIN_DOCS].reset_index().sort_values(["produto_id", "n"], ascending=[True, False])
    viz.groupby("produto_id").head(8).rename(columns={"produto_id_viz": "vizinho"}) \
       .to_csv(PROC / "rede_vizinhos.csv.gz", index=False, encoding="utf-8")
    doc[doc.doc_uid.isin(exemplos)].to_csv(PROC / "documentos_rede.csv.gz", index=False, encoding="utf-8")

    print(f"enriquecimento: {len(e):,} documentos com produto, local ou tema; registro_obra: {len(pub):,} registros")
    print(f"pessoas: {len(p):,} listadas; pessoa×produto: {len(pp):,}; pessoa×tema: {len(ptm):,}; "
          f"evidências: {len(usados):,} documentos")
    print(f"rede: {len(rede):,} pares produto×tema em {rede.produto_id.nunique()} produtos; "
          f"{len(exemplos):,} documentos de exemplo")


if __name__ == "__main__":
    main()
