import networkx as nx
import pandas as pd
import plotly.express as px
import streamlit as st

from lib import dados, ui
from lib.dados import q

a0, a1 = dados.periodo()
st.title("Redes institucionais")
st.caption(f"Nós = unidades · arestas = relações observadas · {a0}–{a1}")

c1, c2, c3 = st.columns([2, 1, 1])
camadas = c1.pills("Evidência", list(dados.CAMADAS), selection_mode="multi", default=["publicacoes"],
                   format_func=dados.CAMADAS.get, key="redes_camadas")
metrica = c2.radio("Peso da aresta", ["peso", "forca"], horizontal=True,
                   format_func={"peso": "Intensidade", "forca": "Força de associação"}.get)
min_docs = c3.slider("Mín. documentos por aresta", 1, 20, 2)
st.caption("Camadas **projetos** (requer equipes dos projetos) e **proximidade temática** (requer o modelo de "
           "temas) serão adicionadas quando os dados estiverem disponíveis. A proximidade temática será "
           "exibida separada da colaboração observada.")

r = dados.rede_unidades(a0, a1, tuple(camadas))
r = r[r.n_docs >= min_docs]
if r.empty:
    st.info("Nenhuma relação com esses filtros.")
    st.stop()

ar = r.rename(columns={"unidade1": "origem", "unidade2": "destino"}).assign(peso=r[metrica])
comm = ui.comunidades(ar)
g = nx.Graph()
for _, a in ar.iterrows():
    g.add_edge(a.origem, a.destino, weight=a.peso, distance=1 / a.peso)
forca_no = dict(g.degree(weight="weight"))
metr = pd.DataFrame({
    "unidade_id": list(g.nodes),
    "unidade": [dados.rotulo_unidade(n) for n in g.nodes],
    "parceiras": [g.degree(n) for n in g.nodes],
    "intensidade": [forca_no[n] for n in g.nodes],
    "intermediacao": pd.Series(nx.betweenness_centrality(g, weight="distance")).reindex(list(g.nodes)).values,
    "comunidade": [comm.get(n, 0) + 1 for n in g.nodes],
})

nos = metr.rename(columns={"unidade_id": "id", "unidade": "rotulo"}).assign(
    tamanho=metr.intensidade, grupo=metr.comunidade - 1,
    titulo=lambda d: d.rotulo + " · parceiras: " + d.parceiras.astype(str) + " · comunidade " + d.comunidade.astype(str))
ar["titulo"] = (ar.origem.map(dados.rotulo_unidade) + " — " + ar.destino.map(dados.rotulo_unidade) + ": "
                + ar.n_docs.astype(str) + " documentos")

t_rede, t_metr, t_evo = st.tabs(["Rede", "Unidades mais conectadas", "Evolução"])
with t_rede:
    n_vis = st.slider("Relações exibidas (as mais fortes)", min_value=min(10, len(ar)), max_value=len(ar),
                      value=min(120, len(ar)),
                      help="Só afeta o desenho. Comunidades e métricas usam todas as relações.")
    ui.rede_pyvis(nos, ar.nlargest(n_vis, "peso"), altura=650, layout_arestas=ar)
    st.caption(f"{g.number_of_nodes()} unidades · {g.number_of_edges()} relações ({n_vis} exibidas) · "
               f"{metr.comunidade.nunique()} comunidades (Louvain). Cor = comunidade; tamanho = intensidade. "
               "Arraste os nós para reorganizar; use a roda do mouse para zoom.")

with t_metr:
    ui.tabela_navegavel(
        metr.sort_values("intensidade", ascending=False), "unidade", "unidade_id", "redes_metr",
        colunas={"intensidade": st.column_config.NumberColumn("Intensidade", format="%.1f"),
                 "intermediacao": st.column_config.NumberColumn("Intermediação", format="%.3f",
                                                                help="Quanto a unidade conecta outras")})
    st.markdown("**Relações mais intensas**")
    top = r.sort_values(metrica, ascending=False).head(30).assign(
        unidade_a=lambda d: d.unidade1.map(dados.rotulo_unidade),
        unidade_b=lambda d: d.unidade2.map(dados.rotulo_unidade))
    st.dataframe(top[["unidade_a", "unidade_b", "n_docs", "peso", "forca"]], hide_index=True,
                 width="stretch",
                 column_config={"peso": st.column_config.NumberColumn("Intensidade", format="%.1f"),
                                "forca": st.column_config.NumberColumn("Força de associação", format="%.2f"),
                                "n_docs": "Documentos"})

with t_evo:
    jan = st.select_slider("Janela (anos)", [3, 5, 10], value=5)
    e = q("""select ano, unidade1, unidade2, doc_uid from aresta_unidade
             where ano between ? and ? and list_contains(?, camada)""", (a0, a1, list(camadas)))
    e["janela"] = (e.ano // jan) * jan
    ev = e.groupby("janela").agg(documentos=("doc_uid", "nunique"),
                                 relacoes=("unidade1", lambda s: len(set(zip(s, e.loc[s.index, "unidade2"])))),
                                 unidades=("unidade1", lambda s: len(set(s) | set(e.loc[s.index, "unidade2"]))))
    ev = ev.reset_index().melt("janela", var_name="indicador", value_name="valor")
    st.plotly_chart(px.line(ev, x="janela", y="valor", color="indicador", markers=True,
                            labels={"janela": f"Início da janela de {jan} anos", "valor": "", "indicador": ""}),
                    width="stretch")
