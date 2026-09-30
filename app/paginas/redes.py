import networkx as nx
import pandas as pd
import plotly.express as px
import streamlit as st

from lib import dados, ui
from lib.dados import q

a0, a1 = dados.periodo()
st.title("Redes institucionais")
st.caption(f"Nós = unidades · ligações = relações observadas entre elas · {a0}–{a1}")

# Filtros ------------------------------------------------------------------------
un = dados.unidades().query("n_docs > 0")
ids = un.unidade_id.tolist()
c0, c1 = st.columns([2, 3])
with c0:
    foco = ui.seletor_url("Unidade em foco", ids, "foco", "redes_foco", format_func=dados.nome_unidade,
                          placeholder="Todas as unidades (visão geral)")
camadas = c1.pills("Tipo de relação", list(dados.CAMADAS), selection_mode="multi", default=["publicacoes"],
                   format_func=dados.CAMADAS.get, key="redes_camadas", help=dados.CAMADAS_AJUDA)
c2, c3 = st.columns([2, 3])
metrica = c2.radio("Medir a relação por", ["peso", "forca"], horizontal=True,
                   format_func={"peso": "Intensidade", "forca": "Força de associação"}.get,
                   help="Intensidade = volume de trabalho em comum. Força de associação = afinidade além do "
                        "esperado pelo tamanho. Detalhes em *O que são intensidade e força de associação?*")
min_docs = c3.slider("Ignorar relações com menos de … documentos", 1, 20, 1 if foco else 2)

e1, e2 = st.columns(2)
with e2.expander("O que são intensidade e força de associação?"):
    st.markdown(dados.METRICAS_AJUDA)
with e1.expander("Como ler esta página"):
    st.markdown(dados.CAMADAS_AJUDA + "\n\n"
                "**Na rede:** cada círculo é uma unidade (tamanho = volume de relações; cor = comunidade, isto é, "
                "grupo de unidades que colaboram mais entre si). Clique num círculo para destacar suas ligações; "
                "arraste para reorganizar; use a roda do mouse para zoom.\n\n"
                "**Escolha uma unidade em foco** para ver com quem ela se relaciona, a síntese de cada relação e "
                "os documentos que a sustentam.\n\n"
                "Em **Mostrar**, a *proximidade temática* compara o conteúdo da produção das unidades — "
                "separada da colaboração observada. Ainda não disponível: relações por **projetos** "
                "(a base não traz as equipes).")

if not camadas:
    st.info("Escolha ao menos um tipo de relação.")
    st.stop()

# Modo: colaboração observada × proximidade temática (mantidas separadas)
if dados.tem_semantica():
    modo = st.segmented_control(
        "Mostrar", ["colab", "prox", "pot"], default="colab", key="redes_modo",
        format_func={"colab": "Colaboração observada", "prox": "Proximidade temática",
                     "pot": "Colaborações potenciais"}.get)
    if modo in ("prox", "pot"):
        from lib import proximidade
        proximidade.mostrar(modo, foco, tuple(camadas), a0, a1)
        st.stop()
r = dados.rede_unidades(a0, a1, tuple(camadas))
r = r[r.n_docs >= min_docs]
if r.empty:
    st.info("Nenhuma relação com esses filtros.")
    st.stop()

ar = r.rename(columns={"unidade1": "origem", "unidade2": "destino"}).assign(intensidade=r["peso"], peso=r[metrica])
ar["titulo"] = (ar.origem.map(dados.rotulo_unidade) + " — " + ar.destino.map(dados.rotulo_unidade) + ": "
                + ar.n_docs.astype(str) + " documentos")
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


def nos_de(df_metr: pd.DataFrame) -> pd.DataFrame:
    return df_metr.rename(columns={"unidade_id": "id", "unidade": "rotulo"}).assign(
        tamanho=df_metr.intensidade, grupo=df_metr.comunidade - 1,
        titulo=lambda d: d.rotulo + " · " + d.parceiras.astype(str) + " parceiras · comunidade "
        + d.comunidade.astype(str))


rotulo_rede = f"Relações de {dados.rotulo_unidade(foco)}" if foco else "Rede"
ranking = metr.sort_values("intensidade", ascending=False).reset_index(drop=True)
ranking.insert(0, "posicao", ranking.index + 1)
if foco:  # o ranking geral é uma visão da rede inteira: fica só na visão geral
    t_rede, t_evo = st.tabs([rotulo_rede, "Evolução"])
    t_metr = None
else:
    t_rede, t_metr, t_evo = st.tabs([rotulo_rede, "Ranking geral das unidades", "Evolução"])

with t_rede:
    if foco is None:
        # Visão geral ------------------------------------------------------------
        n_vis = len(ar)
        if len(ar) > 20:
            n_vis = st.slider("Ligações desenhadas (as mais fortes da rede)", 20, len(ar), min(120, len(ar)),
                              help="Só afeta o desenho. Comunidades e métricas usam todas as relações.")
        # Garante que nenhuma unidade apareça solta: além das N mais fortes da
        # rede, desenha as 2 ligações mais fortes de cada unidade.
        por_no = pd.concat([ar.assign(no=ar.origem), ar.assign(no=ar.destino)])
        top_no = por_no.sort_values("peso", ascending=False).groupby("no").head(2)
        desenho = pd.concat([ar.nlargest(n_vis, "peso"), top_no.drop(columns="no")])             .drop_duplicates(subset=["origem", "destino"])
        ui.rede_pyvis(nos_de(metr), desenho, altura=620, layout_arestas=ar)
        n_vis = len(desenho)
        st.caption(f"{g.number_of_nodes()} unidades · {g.number_of_edges()} relações ({n_vis} desenhadas: as mais "
                   "fortes da rede + as 2 mais fortes de cada unidade) · "
                   f"{metr.comunidade.nunique()} comunidades. **Clique numa unidade** para destacar suas "
                   "ligações, ou **escolha uma unidade em foco** acima para ver os detalhes.")
        st.markdown("**Comunidades** — grupos de unidades que se relacionam mais entre si")
        cm = metr.groupby("comunidade").unidade.apply(lambda s: ", ".join(sorted(s))).reset_index()
        st.dataframe(cm, hide_index=True, width="stretch",
                     column_config={"comunidade": st.column_config.NumberColumn("Comunidade", width="small"),
                                    "unidade": "Unidades"})
    elif foco not in g:
        st.info(f"{dados.nome_unidade(foco)} não tem relações com esses filtros.")
    else:
        # Unidade em foco ----------------------------------------------------------
        lin = ranking[ranking.unidade_id == foco].iloc[0]
        st.info(f"**{dados.nome_unidade(foco)}** relaciona-se com **{lin.parceiras}** das {len(ranking) - 1} outras "
                f"unidades. No conjunto da Embrapa, é a **{lin.posicao}ª** de {len(ranking)} em volume total de "
                f"relações e pertence à comunidade {lin.comunidade} (grupo de unidades que colaboram mais entre si). "
                "Para comparar todas as unidades, limpe a unidade em foco e veja *Ranking geral das unidades*.",
                icon=":material/info:")
        rel = ar[(ar.origem == foco) | (ar.destino == foco)].copy()
        rel["parceira_id"] = rel.origem.where(rel.origem != foco, rel.destino)
        rel = rel.sort_values("peso", ascending=False)
        n_parc = len(rel)
        if n_parc > 5:
            n_parc = st.slider("Parceiras desenhadas", 5, len(rel), min(20, len(rel)))
        vis = rel.head(n_parc)
        nos_ids = [foco] + vis.parceira_id.tolist()
        entre = ar[ar.origem.isin(nos_ids) & ar.destino.isin(nos_ids)]
        mostrar_entre = st.toggle("Mostrar também as relações entre as parceiras", value=False)
        desenho = entre if mostrar_entre else vis
        ui.rede_pyvis(nos_de(metr[metr.unidade_id.isin(nos_ids)]), desenho, altura=560,
                      layout_arestas=entre, centro=foco, destaque=foco)
        st.caption(f"{dados.nome_unidade(foco)} no centro, com {len(rel)} unidades parceiras "
                   f"({n_parc} desenhadas). Espessura = {'intensidade' if metrica == 'peso' else 'força de associação'}.")

        # Síntese das relações -------------------------------------------------------
        st.markdown(f"#### Relações de {dados.nome_unidade(foco)}")
        docs_parc = q("""
            select case when unidade1 = ? then unidade2 else unidade1 end parceira_id,
                   list(distinct doc_uid) docs
            from aresta_unidade where (unidade1 = ? or unidade2 = ?) and ano between ? and ?
              and list_contains(?, camada) group by 1
        """, (foco, foco, foco, a0, a1, list(camadas)))
        rel = rel.merge(docs_parc, on="parceira_id", how="left")
        todos = sorted({d for l in rel.docs.dropna() for d in l})
        kw = q("""select doc_uid, lower(any_value(keyword_raw)) palavra from documento_keyword
                  where list_contains(?, doc_uid) group by doc_uid, keyword_norm""", (todos,))
        def temas(lista):
            if lista is None or len(lista) == 0:
                return ""
            return ", ".join(kw[kw.doc_uid.isin(lista)].groupby("palavra").size().nlargest(4).index)
        rel["temas"] = rel.docs.map(temas)
        rel["parceira"] = rel.parceira_id.map(dados.nome_unidade)
        sint = rel[["parceira_id", "parceira", "n_docs", "intensidade", "forca", "temas"]]
        ev = st.dataframe(
            sint, hide_index=True, width="stretch", on_select="rerun",
            selection_mode="single-row", key=f"redes_rel_{foco}",
            column_config={"parceira_id": None, "parceira": "Unidade parceira", "n_docs": "Documentos em comum",
                           "intensidade": st.column_config.NumberColumn("Intensidade", format="%.1f"),
                           "forca": st.column_config.NumberColumn("Força de associação", format="%.2f"),
                           "temas": "Temas em comum (palavras-chave)"})
        ui.aviso_tema_provisorio()

        linhas = ev.selection.rows
        if not linhas:
            st.caption("Clique numa linha para ver os documentos que sustentam a relação.")
        else:
            p = sint.iloc[linhas[0]]
            dd = rel.iloc[linhas[0]].docs
            st.markdown(f"#### Documentos em comum: {dados.rotulo_unidade(foco)} — {dados.rotulo_unidade(p.parceira_id)}")
            lista = q("""select doc_uid, tipo_doc tipo, ano, titulo from documento
                         where list_contains(?, doc_uid) order by ano desc""", (list(dd),))
            lista["tipo"] = lista.tipo.map({"publicacao": "Publicação", "tecnologia": "Tecnologia",
                                            "projeto": "Projeto"})
            ui.tabela_navegavel(lista, "doc", "doc_uid", f"redes_docs_{foco}", altura=380)
            ui.link("unidade", p.parceira_id, f"Abrir o perfil de {p.parceira}", ":material/apartment:")

if t_metr is not None:
    with t_metr:
        st.caption("Todas as unidades da Embrapa, ordenadas pela intensidade total de relações com **todas** as "
                   "demais (soma das suas ligações). É uma visão da rede inteira — não muda com a unidade em foco. "
                   "**Parceiras**: com quantas unidades se relaciona. **Intermediação**: quanto a unidade funciona "
                   "como ponte entre outras que pouco se relacionam diretamente.")
        ui.tabela_navegavel(
            ranking, "unidade", "unidade_id", "redes_metr",
            colunas={"posicao": st.column_config.NumberColumn("Posição", width="small"),
                     "unidade": "Unidade", "parceiras": "Parceiras", "comunidade": "Comunidade",
                     "intensidade": st.column_config.NumberColumn("Intensidade total", format="%.1f"),
                     "intermediacao": st.column_config.NumberColumn("Intermediação", format="%.3f",
                                                                    help="Quanto a unidade conecta outras")})
        st.markdown("**Pares de unidades com relações mais intensas** (rede inteira)")
        top = r.sort_values(metrica, ascending=False).head(30).assign(
            unidade_a=lambda d: d.unidade1.map(dados.rotulo_unidade),
            unidade_b=lambda d: d.unidade2.map(dados.rotulo_unidade))
        st.dataframe(top[["unidade_a", "unidade_b", "n_docs", "peso", "forca"]], hide_index=True,
                     width="stretch",
                     column_config={"unidade_a": "Unidade", "unidade_b": "Unidade parceira",
                                    "peso": st.column_config.NumberColumn("Intensidade", format="%.1f"),
                                    "forca": st.column_config.NumberColumn("Força de associação", format="%.2f"),
                                    "n_docs": "Documentos"})

with t_evo:
    jan = st.select_slider("Janela (anos)", [3, 5, 10], value=5)
    e = q("""select ano, unidade1, unidade2, doc_uid from aresta_unidade
             where ano between ? and ? and list_contains(?, camada)""", (a0, a1, list(camadas)))
    if foco:
        e = e[(e.unidade1 == foco) | (e.unidade2 == foco)]
        st.caption(f"Relações de {dados.nome_unidade(foco)} ao longo do tempo.")
    e["janela"] = (e.ano // jan) * jan
    ev = e.groupby("janela").agg(documentos=("doc_uid", "nunique"),
                                 relacoes=("unidade1", lambda s: len(set(zip(s, e.loc[s.index, "unidade2"])))),
                                 unidades=("unidade1", lambda s: len(set(s) | set(e.loc[s.index, "unidade2"]))))
    ev = ev.reset_index().melt("janela", var_name="indicador", value_name="valor")
    ev["indicador"] = ev.indicador.map({"documentos": "Documentos em colaboração",
                                        "relacoes": "Pares de unidades", "unidades": "Unidades envolvidas"})
    st.plotly_chart(px.line(ev, x="janela", y="valor", color="indicador", markers=True,
                            labels={"janela": f"Início da janela de {jan} anos", "valor": "", "indicador": ""}),
                    width="stretch")
