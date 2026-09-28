"""Componentes de interface compartilhados entre as páginas."""

import networkx as nx
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
from pyvis.network import Network

PAGINAS = {
    "embrapa": "paginas/embrapa.py",
    "unidade": "paginas/unidades.py",
    "redes": "paginas/redes.py",
    "temas": "paginas/temas.py",
    "pessoa": "paginas/pesquisadores.py",
    "doc": "paginas/documentos.py",
}
PALETA = ["#1565C0", "#2E7D32", "#EF6C00", "#6A1B9A", "#C62828", "#00838F", "#9E9D24",
          "#4E342E", "#AD1457", "#283593", "#558B2F", "#F9A825"]


def kpis(valores: list[tuple[str, object]]) -> None:
    cols = st.columns(len(valores))
    for c, (rotulo, valor) in zip(cols, valores):
        if isinstance(valor, (int, float)) and not isinstance(valor, bool):
            valor = f"{valor:,.0f}".replace(",", ".")
        c.metric(rotulo, valor)


def tabela_navegavel(df: pd.DataFrame, destino: str, coluna_id: str, key: str,
                     colunas: dict | None = None, altura: int | None = None) -> None:
    """Tabela em que clicar numa linha abre a página de destino
    (unidade, pessoa ou doc) com o id da linha na URL."""
    if df.empty:
        st.caption("Nenhum registro.")
        return
    config = {coluna_id: None}
    config.update(colunas or {})
    n = st.session_state.get("_nav", 0)
    kw = {"height": altura} if altura else {}
    ev = st.dataframe(df, hide_index=True, on_select="rerun", selection_mode="single-row",
                      column_config=config, key=f"{key}_{n}", width="stretch", **kw)
    linhas = ev.selection.rows
    if linhas:
        st.session_state["_nav"] = n + 1
        st.switch_page(PAGINAS[destino], query_params={destino: str(df.iloc[linhas[0]][coluna_id])})
    st.caption("Clique numa linha para abrir o detalhe.")


def link(destino: str, valor: str, rotulo: str, icone: str | None = None) -> None:
    st.page_link(PAGINAS[destino], label=rotulo, icon=icone, query_params={destino: valor})


def aviso_tema_provisorio() -> None:
    st.info("**Temas provisórios:** enquanto o modelo de temas (BERTopic sobre embeddings) não é "
            "gerado, os temas são aproximados pelas palavras-chave declaradas nos documentos.",
            icon=":material/info:")


def rede_pyvis(nos: pd.DataFrame, arestas: pd.DataFrame, altura: int = 620,
               destaque: str | None = None, layout_arestas: pd.DataFrame | None = None) -> None:
    """nos: id, rotulo, tamanho, grupo, titulo · arestas: origem, destino, peso, titulo

    O layout é calculado aqui (força dirigida, semente fixa) e enviado com
    posições fixas: sem simulação física no navegador, a rede não fica se
    movendo. Nós continuam arrastáveis; zoom e tooltips funcionam."""
    # Layout sobre todas as relações (não só as exibidas), com pesos
    # normalizados: pesos brutos altos colapsariam os nós no centro.
    base = arestas if layout_arestas is None else layout_arestas
    g = nx.Graph()
    g.add_nodes_from(nos["id"].astype(str))
    wref = base["peso"].max() if not base.empty else 1
    for _, a in base.iterrows():
        g.add_edge(str(a["origem"]), str(a["destino"]), weight=(float(a["peso"]) / wref) ** 0.5)
    k = 1.5 / max(g.number_of_nodes(), 1) ** 0.5
    pos = nx.spring_layout(g, weight="weight", k=k, iterations=500, seed=42)
    raio = 380

    net = Network(height=f"{altura}px", width="100%", bgcolor="#ffffff", font_color="#222222",
                  cdn_resources="remote")
    tam = nos["tamanho"].astype(float)
    escala = (tam - tam.min()) / (tam.max() - tam.min() + 1e-9)
    for (_, n), e in zip(nos.iterrows(), escala):
        cor = PALETA[int(n.get("grupo", 0)) % len(PALETA)]
        x, y = pos[str(n["id"])]
        net.add_node(str(n["id"]), label=str(n["rotulo"]), title=str(n.get("titulo", n["rotulo"])),
                     size=8 + 22 * float(e), color=cor, x=float(x) * raio, y=float(y) * raio,
                     physics=False, font={"size": 15, "strokeWidth": 4, "strokeColor": "#ffffff"},
                     borderWidth=4 if destaque and n["id"] == destaque else 1)
    wmax = arestas["peso"].max() if not arestas.empty else 1
    for _, a in arestas.iterrows():
        rel = float(a["peso"]) / wmax
        net.add_edge(str(a["origem"]), str(a["destino"]), title=str(a.get("titulo", "")),
                     width=0.5 + 6 * rel, color={"color": "#8a96a3", "opacity": 0.25 + 0.5 * rel})
    net.set_options("""{
      "physics": {"enabled": false},
      "edges": {"smooth": false},
      "interaction": {"hover": true, "navigationButtons": true, "dragNodes": true, "tooltipDelay": 120}
    }""")
    components.html(net.generate_html(), height=altura + 20, scrolling=False)


def comunidades(arestas: pd.DataFrame) -> dict:
    """Louvain (semente fixa) sobre o grafo ponderado → {nó: comunidade}"""
    g = nx.Graph()
    for _, a in arestas.iterrows():
        g.add_edge(a["origem"], a["destino"], weight=float(a["peso"]))
    if g.number_of_edges() == 0:
        return {}
    comms = nx.community.louvain_communities(g, weight="weight", seed=42)
    comms = sorted(comms, key=len, reverse=True)
    return {n: i for i, c in enumerate(comms) for n in c}
