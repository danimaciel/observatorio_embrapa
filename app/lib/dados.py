"""Acesso somente leitura ao observatorio_app.duckdb gerado pelo pipeline R.

Localmente o banco é lido de data/processed/. No Streamlit Cloud (onde data/
não é versionada) ele é baixado de uma Release do GitHub, configurada em
.streamlit/secrets.toml:

    [dados]
    repo = "usuario/repositorio"
    tag = "dados-2026-09"
    arquivo = "observatorio_app.duckdb"
    token = "..."   # só para repositório privado
"""

import json
import urllib.request
from pathlib import Path

import duckdb
import pandas as pd
import streamlit as st

RAIZ = Path(__file__).resolve().parents[2]
DB = RAIZ / "data" / "processed" / "observatorio_app.duckdb"

TIPOS = {"projeto": "Projetos", "publicacao": "Publicações", "tecnologia": "Tecnologias"}
CORES_TIPO = {"projeto": "#2E7D32", "publicacao": "#1565C0", "tecnologia": "#EF6C00"}
CAMADAS = {
    "publicacoes": "Coautoria em publicações",
    "tecnologias_indireta": "Tecnologias (via publicações citadas)",
}
GRUPOS_PUB = {
    "periodico": "Artigo em periódico",
    "anais_completo": "Artigo em anais",
    "anais_resumo": "Resumo em anais",
    "livro_capitulo": "Livro / capítulo",
    "tecnica": "Publicação técnica",
    "tese": "Tese",
    "divulgacao": "Divulgação",
    "outros": "Outros",
}


def _baixar_da_release(cfg, destino: Path) -> None:
    """Baixa o banco anexado a uma Release (funciona para repositório público ou privado)."""
    cab = {"Accept": "application/vnd.github+json", "User-Agent": "observatorio-embrapa"}
    if cfg.get("token"):
        cab["Authorization"] = f"Bearer {cfg['token']}"
    url = f"https://api.github.com/repos/{cfg['repo']}/releases/tags/{cfg['tag']}"
    with urllib.request.urlopen(urllib.request.Request(url, headers=cab)) as r:
        release = json.load(r)
    asset = next((a for a in release["assets"] if a["name"] == cfg.get("arquivo", DB.name)), None)
    if asset is None:
        raise FileNotFoundError(f"{cfg.get('arquivo', DB.name)} não está na release {cfg['tag']}")
    cab["Accept"] = "application/octet-stream"
    destino.parent.mkdir(parents=True, exist_ok=True)
    tmp = destino.with_suffix(".part")
    with urllib.request.urlopen(urllib.request.Request(asset["url"], headers=cab)) as r, open(tmp, "wb") as f:
        while bloco := r.read(1 << 20):
            f.write(bloco)
    tmp.replace(destino)


@st.cache_resource(show_spinner="Carregando a base do Observatório…")
def conexao() -> duckdb.DuckDBPyConnection:
    if not DB.exists():
        try:
            cfg = st.secrets.get("dados")
        except Exception:  # sem secrets.toml
            cfg = None
        if not cfg:
            st.error(f"Base não encontrada em `{DB}`. Rode o pipeline (`targets::tar_make()`) ou configure "
                     "`[dados]` em `.streamlit/secrets.toml`.")
            st.stop()
        _baixar_da_release(cfg, DB)
    return duckdb.connect(str(DB), read_only=True)


@st.cache_data(ttl=3600, show_spinner=False)
def q(sql: str, params: tuple = ()) -> pd.DataFrame:
    return conexao().cursor().execute(sql, list(params)).df()


# Filtros globais (definidos na barra lateral em app.py) -----------------------

def periodo() -> tuple[int, int]:
    return st.session_state.get("periodo", (1990, 2026))


# Consultas de referência ------------------------------------------------------

@st.cache_data(show_spinner=False)
def unidades() -> pd.DataFrame:
    df = q("select unidade_id, nome_atual, sigla_historica, categoria, uf from unidade order by nome_atual")
    df["rotulo"] = df["nome_atual"].str.replace("Embrapa ", "", regex=False)
    return df


def nome_unidade(unidade_id: str | None) -> str:
    if not unidade_id:
        return "—"
    u = unidades().set_index("unidade_id")
    return u["nome_atual"].get(unidade_id, unidade_id)


def rotulo_unidade(unidade_id: str | None) -> str:
    return nome_unidade(unidade_id).replace("Embrapa ", "")


@st.cache_data(show_spinner=False)
def meta() -> dict:
    return q("select * from meta").iloc[0].to_dict()


@st.cache_data(show_spinner=False)
def rede_unidades(a0: int, a1: int, camadas: tuple[str, ...]) -> pd.DataFrame:
    """Arestas unidade–unidade agregadas no período, com:
    peso      contagem fracionária (cada documento distribui 1 entre seus pares)
    n_docs    documentos que sustentam a relação
    forca     força de associação = observado / esperado dado o tamanho das
              duas unidades (> 1: relação mais intensa que o esperado)"""
    if not camadas:
        return pd.DataFrame(columns=["unidade1", "unidade2", "peso", "n_docs", "forca"])
    a = q("""
        select unidade1, unidade2, sum(peso_frac) peso, count(distinct doc_uid) n_docs
        from aresta_unidade where ano between ? and ? and list_contains(?, camada)
        group by all
    """, (a0, a1, list(camadas)))
    if a.empty:
        return a.assign(forca=[])
    s = pd.concat([a[["unidade1", "peso"]].rename(columns={"unidade1": "u"}),
                   a[["unidade2", "peso"]].rename(columns={"unidade2": "u"})]).groupby("u")["peso"].sum()
    W = a["peso"].sum()
    a["forca"] = 2 * W * a["peso"] / (a["unidade1"].map(s) * a["unidade2"].map(s))
    return a


def docs_da_relacao(u1: str, u2: str, a0: int, a1: int, camadas: tuple[str, ...]) -> list[str]:
    x, y = sorted([u1, u2])
    return q("""select distinct doc_uid from aresta_unidade
                where unidade1 = ? and unidade2 = ? and ano between ? and ? and list_contains(?, camada)""",
             (x, y, a0, a1, list(camadas)))["doc_uid"].tolist()


@st.cache_data(show_spinner=False)
def palavras_chave(doc_uids: tuple[str, ...], n: int = 15) -> pd.DataFrame:
    return q("""
        select lower(any_value(keyword_raw)) palavra, count(distinct doc_uid) n
        from documento_keyword where list_contains(?, doc_uid)
        group by keyword_norm order by n desc limit ?
    """, (list(doc_uids), n))


@st.cache_data(show_spinner=False)
def faixa_anos() -> tuple[int, int]:
    r = q("select min(ano) a0, max(ano) a1 from documento where ano >= 1970")
    return int(r.a0[0]), int(r.a1[0])
