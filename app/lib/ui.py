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
    "tema": "paginas/temas.py",
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


def seletor_url(rotulo: str, opcoes: list, param: str, key: str, **kw):
    """Selectbox sincronizado com ?param= na URL, nos dois sentidos.

    Um link (ou clique numa tabela) que muda o parâmetro prevalece sobre a
    seleção guardada na sessão; escolher no seletor atualiza a URL."""
    url = st.query_params.get(param)
    marca = f"_url_{key}"
    if url != st.session_state.get(marca):          # a URL mudou por fora
        st.session_state[key] = url if url in opcoes else None
        st.session_state[marca] = url
    elif key not in st.session_state:
        st.session_state[key] = None
    sel = st.selectbox(rotulo, opcoes, key=key, **kw)
    if sel is not None:
        st.query_params[param] = sel
    elif param in st.query_params:
        del st.query_params[param]
    st.session_state[marca] = sel
    return sel


def link(destino: str, valor: str, rotulo: str, icone: str | None = None) -> None:
    st.page_link(PAGINAS[destino], label=rotulo, icon=icone, query_params={destino: valor})


def aviso_tema_provisorio() -> None:
    from lib import dados
    if dados.tem_semantica():
        st.caption("Temas identificados por similaridade semântica (SBERT + BERTopic) a partir de título, resumo "
                   "e palavras-chave; nomes dos temas revisados a partir dos termos mais característicos de cada um.")
    else:
        st.info("**Temas provisórios:** enquanto o modelo de temas não é gerado, os temas são aproximados "
                "pelas palavras-chave declaradas nos documentos.", icon=":material/info:")


def rede_pyvis(nos: pd.DataFrame, arestas: pd.DataFrame, altura: int = 620,
               destaque: str | None = None, layout_arestas: pd.DataFrame | None = None,
               centro: str | None = None) -> None:
    """nos: id, rotulo, tamanho, grupo, titulo · arestas: origem, destino, peso, titulo

    O layout é calculado aqui (força dirigida, semente fixa) e enviado com
    posições fixas: sem simulação física no navegador, a rede não fica se
    movendo. Clicar num nó destaca suas conexões e esmaece o resto; nós são
    arrastáveis; zoom e tooltips funcionam. `centro` fixa um nó no meio."""
    # Layout sobre todas as relações (não só as exibidas), com pesos
    # normalizados: pesos brutos altos colapsariam os nós no centro.
    base = arestas if layout_arestas is None else layout_arestas
    g = nx.Graph()
    g.add_nodes_from(nos["id"].astype(str))
    wref = base["peso"].max() if not base.empty else 1
    for _, a in base.iterrows():
        g.add_edge(str(a["origem"]), str(a["destino"]), weight=(float(a["peso"]) / wref) ** 0.5)
    k = 1.5 / max(g.number_of_nodes(), 1) ** 0.5
    if centro and centro in g:
        # Radial: foco no centro; parceiras em círculo, ordenadas por grupo,
        # mais próximas quanto mais forte a relação com o foco.
        import math
        viz = [n for n in g.nodes if n != centro]
        forca_rel = {n: g[centro][n]["weight"] if g.has_edge(centro, n) else 0 for n in viz}
        fmax = max(forca_rel.values(), default=1) or 1
        grupo = dict(zip(nos["id"].astype(str), nos.get("grupo", pd.Series(0, index=nos.index))))
        viz.sort(key=lambda n: (grupo.get(n, 0), -forca_rel[n]))
        pos = {centro: (0.0, 0.0)}
        for i, n in enumerate(viz):
            ang = 2 * math.pi * i / max(len(viz), 1)
            r = 0.45 + 0.55 * (1 - forca_rel[n] / fmax)
            pos[n] = (r * math.cos(ang), r * math.sin(ang))
    else:
        pos = nx.spring_layout(g, weight="weight", k=k, iterations=500, seed=42)
    raio = 380

    net = Network(height=f"{altura}px", width="100%", bgcolor="#ffffff", font_color="#222222",
                  cdn_resources="remote", neighborhood_highlight=True)
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
