import json
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from lib import dados, ui
from lib.dados import q

COD_UF = {"RO": "11", "AC": "12", "AM": "13", "RR": "14", "PA": "15", "AP": "16", "TO": "17", "MA": "21",
          "PI": "22", "CE": "23", "RN": "24", "PB": "25", "PE": "26", "AL": "27", "SE": "28", "BA": "29",
          "MG": "31", "ES": "32", "RJ": "33", "SP": "35", "PR": "41", "SC": "42", "RS": "43", "MS": "50",
          "MT": "51", "GO": "52", "DF": "53"}

a0, a1 = dados.periodo()
st.title("Mapa da produção")
st.caption(f"Produção e temas no território · {a0}–{a1}")

tabelas = set(q("select table_name from duckdb_tables()").table_name)
visoes = {"sede": "Sedes das unidades"}
if "doc_municipio" in tabelas:
    visoes["territorio"] = "Onde a pesquisa acontece"
if "doc_bioma" in tabelas:
    visoes["bioma"] = "Biomas"
visao = "sede"
if len(visoes) > 1:
    visao = st.segmented_control("Mostrar", list(visoes), default="sede", key="mapa_visao",
                                 format_func=visoes.get) or "sede"

# Filtros comuns -------------------------------------------------------------------
c1, c2, c3 = st.columns([2, 2, 2])
tipos = c1.pills("Produção", list(dados.TIPOS), selection_mode="multi", default=list(dados.TIPOS),
                 format_func=dados.TIPOS.get, key="mapa_tipos")
tema_sel = None
if dados.tem_semantica():
    tm = dados.temas()
    macro_ids = tm[tm.nivel == 1].sort_values("n_total", ascending=False).tema_id.tolist()
    tema_ids = tm[tm.nivel == 2].sort_values("n_total", ascending=False).tema_id.tolist()
    with c2:
        tema_sel = st.selectbox("Tema ou macrotema", macro_ids + tema_ids, index=None,
                                format_func=lambda t: ("◆ " if t.startswith("M") else "") + dados.rotulo_tema(t),
                                placeholder="Toda a produção", help="◆ = macrotema.")
if not tipos:
    st.info("Escolha ao menos um tipo de produção.")
    st.stop()
col_tema = ("macro_id" if tema_sel and tema_sel.startswith("M") else "tema_id") if tema_sel else None
join_tema = "join doc_tema t using (doc_uid)" if tema_sel else ""
filtro_tema = f"and t.{col_tema} = ?" if tema_sel else ""
params_tema = (tema_sel,) if tema_sel else ()


# ==================================================================================
def mapa_sedes() -> None:
    with c3:
        mostrar_rede = st.toggle("Mostrar colaboração entre unidades", value=False)
        n_arcos = st.slider("Ligações desenhadas (as mais fortes)", 10, 150, 40, disabled=not mostrar_rede)
    st.info("Cada unidade aparece no local do seu **campus-sede** (coordenadas do Portal Embrapa). A sede indica "
            "onde a unidade está, não necessariamente onde a pesquisa acontece — para isso, veja *Onde a pesquisa "
            "acontece*.", icon=":material/location_on:")
    loc = q("select * from unidade_localizacao")
    base = q(f"""select du.unidade_id, d.tipo_doc, count(distinct du.doc_uid) n
                 from documento_unidade du join documento d using (doc_uid) {join_tema}
                 where d.ano between ? and ? and list_contains(?, d.tipo_doc) {filtro_tema} group by all""",
             (a0, a1, list(tipos)) + params_tema)
    tab = base.pivot_table(index="unidade_id", columns="tipo_doc", values="n", aggfunc="sum", fill_value=0)
    for t in dados.TIPOS:
        if t not in tab:
            tab[t] = 0
    tab["total"] = tab[list(dados.TIPOS)].sum(axis=1)
    tab = tab.reset_index().merge(loc, on="unidade_id", how="inner")
    tab["unidade"] = tab.unidade_id.map(dados.rotulo_unidade)
    if tema_sel:
        tot_un = q("""select du.unidade_id, count(distinct du.doc_uid) n from documento_unidade du
                      join documento d using (doc_uid) where d.ano between ? and ? and list_contains(?, d.tipo_doc)
                      group by 1""", (a0, a1, list(tipos))).set_index("unidade_id").n
        tot = q(f"""select count(*) n, count(*) filter (where t.{col_tema} = ?) nt from documento d
                    join doc_tema t using (doc_uid) where d.ano between ? and ? and list_contains(?, d.tipo_doc)""",
                (tema_sel, a0, a1, list(tipos))).iloc[0]
        tab["especializacao"] = (tab.total / tab.unidade_id.map(tot_un)) / (tot.nt / max(tot.n, 1))
        cor = "especializacao"
    elif dados.tem_semantica():
        dom = q("""select du.unidade_id, t.macro_id, count(distinct du.doc_uid) n from documento_unidade du
                   join documento d using (doc_uid) join doc_tema t using (doc_uid)
                   where d.ano between ? and ? and list_contains(?, d.tipo_doc) group by all""",
                (a0, a1, list(tipos)))
        dom = dom.sort_values("n", ascending=False).drop_duplicates("unidade_id")
        tab["macrotema"] = tab.unidade_id.map(dom.set_index("unidade_id").macro_id).map(dados.rotulo_tema).fillna("—")
        cor = "macrotema"
    else:
        cor = None
    tab = tab[tab.total > 0]
    if tab.empty:
        st.info("Nenhuma produção com esses filtros.")
        return
    tab["rotulo_hover"] = tab.unidade + " — " + tab.municipio + "/" + tab.uf
    hover = {"lat": False, "lon": False, "total": True, "projeto": True, "publicacao": True, "tecnologia": True}
    if tema_sel:
        hover["especializacao"] = ":.2f"
    fig = px.scatter_map(
        tab, lat="lat", lon="lon", size="total", size_max=42, hover_name="rotulo_hover", hover_data=hover,
        color=cor, color_continuous_scale="RdYlGn" if tema_sel else None,
        color_continuous_midpoint=1 if tema_sel else None,
        labels={"total": "Documentos", "projeto": "Projetos", "publicacao": "Publicações", "tecnologia": "Tecnologias",
                "especializacao": "Especialização", "macrotema": "Macrotema dominante"},
        zoom=3.2, center={"lat": -14.5, "lon": -52}, height=680, map_style="carto-positron")
    if mostrar_rede:
        r = dados.rede_unidades(a0, a1, ("publicacoes",)).nlargest(n_arcos, "peso")
        pos = loc.set_index("unidade_id")[["lat", "lon"]]
        r = r[r.unidade1.isin(pos.index) & r.unidade2.isin(pos.index)]
        if not r.empty:
            wmax = r.peso.max()
            for li, ls, larg in [(0, 1 / 3, 1), (1 / 3, 2 / 3, 2.5), (2 / 3, 1.01, 4.5)]:
                sub = r[(r.peso / wmax >= li) & (r.peso / wmax < ls)]
                lats, lons = [], []
                for _, e in sub.iterrows():
                    lats += [pos.lat[e.unidade1], pos.lat[e.unidade2], None]
                    lons += [pos.lon[e.unidade1], pos.lon[e.unidade2], None]
                if lats:
                    fig.add_trace(go.Scattermap(lat=lats, lon=lons, mode="lines", hoverinfo="skip", showlegend=False,
                                                line=dict(width=larg, color="rgba(21,101,192,0.45)")))
            fig.data = tuple([d for d in fig.data if getattr(d, "mode", "") == "lines"] +
                             [d for d in fig.data if getattr(d, "mode", "") != "lines"])
    fig.update_layout(margin=dict(t=0, l=0, r=0, b=0), legend=dict(orientation="h", y=-0.02))
    st.plotly_chart(fig, width="stretch")
    leg = ("Tamanho = documentos com participação da unidade (líder, depositante, responsável ou afiliação de autor).")
    if tema_sel:
        leg += f" Tema: **{dados.rotulo_tema(tema_sel)}** — cor = especialização (verde > 1: acima da média)."
    elif cor:
        leg += " Cor = macrotema com mais documentos da unidade."
    if mostrar_rede:
        leg += " Linhas = publicações em conjunto (espessura = intensidade)."
    st.caption(leg)
    cols = ["unidade_id", "unidade", "municipio", "uf", "total", "projeto", "publicacao", "tecnologia"]
    cols += ["especializacao"] if tema_sel else (["macrotema"] if cor else [])
    ui.tabela_navegavel(tab.sort_values("total", ascending=False)[cols], "unidade", "unidade_id", "mapa_tab",
                        altura=420, colunas={"unidade": "Unidade", "municipio": "Município", "uf": "UF",
                                             "total": "Documentos", "projeto": "Projetos",
                                             "publicacao": "Publicações", "tecnologia": "Tecnologias",
                                             "especializacao": st.column_config.NumberColumn("Especialização",
                                                                                             format="%.2f"),
                                             "macrotema": "Macrotema dominante"})


# ==================================================================================
@st.cache_data(show_spinner=False)
def geo_ufs() -> dict:
    return json.loads((Path(__file__).resolve().parents[1] / "assets" / "br_uf.geojson").read_text(encoding="utf-8"))


def mapa_territorio() -> None:
    un = dados.unidades().query("n_docs > 0")
    with c3:
        unidade = st.selectbox("Produção da unidade", un.unidade_id.tolist(), index=None,
                               format_func=dados.nome_unidade, placeholder="Todas as unidades",
                               help="Mostra onde acontece a pesquisa de uma unidade específica.")
        escala = st.radio("Agregar por", ["municipio", "estado"], horizontal=True,
                          format_func={"municipio": "Município", "estado": "Estado"}.get)
    st.info("Locais **citados nos textos** (título, resumo e palavras-chave). Só entram menções com contexto "
            "geográfico claro — UF ou estado ao lado (“Petrolina, PE”), “município de…”, ou o estado citado no "
            "texto —, com ~98% de precisão numa amostra conferida. Cerca de 15% das publicações e 13% dos projetos "
            "citam algum município.", icon=":material/travel_explore:")
    join_un = "join documento_unidade du using (doc_uid)" if unidade else ""
    filtro_un = "and du.unidade_id = ?" if unidade else ""
    params = (a0, a1, list(tipos)) + params_tema + ((unidade,) if unidade else ())

    if escala == "municipio":
        m = q(f"""select dm.cod_ibge, any_value(dm.municipio) municipio, any_value(dm.uf) uf,
                         count(distinct dm.doc_uid) documentos
                  from doc_municipio dm join documento d using (doc_uid) {join_tema} {join_un}
                  where d.ano between ? and ? and list_contains(?, d.tipo_doc) {filtro_tema} {filtro_un}
                  group by dm.cod_ibge""", params)
        m = m.merge(q("select cod_ibge, lat, lon from municipio_centroide"), on="cod_ibge", how="inner")
        if m.empty:
            st.info("Nenhum município citado com esses filtros.")
            return
        m["local"] = m.municipio + "/" + m.uf
        fig = px.scatter_map(m, lat="lat", lon="lon", size="documentos", size_max=35, hover_name="local",
                             hover_data={"lat": False, "lon": False, "documentos": True},
                             color_discrete_sequence=["#2E7D32"], zoom=3.2, center={"lat": -14.5, "lon": -52},
                             height=680, map_style="carto-positron", opacity=0.6)
        if unidade:
            sede = q("select * from unidade_localizacao where unidade_id = ?", (unidade,))
            if not sede.empty:
                fig.add_trace(go.Scattermap(lat=sede.lat, lon=sede.lon, mode="markers+text", text=["Sede"],
                                            textposition="top right", marker=dict(size=16, color="#C62828"),
                                            name="Sede da unidade", hoverinfo="text",
                                            hovertext=[f"Sede: {dados.nome_unidade(unidade)}"]))
        fig.update_layout(margin=dict(t=0, l=0, r=0, b=0), showlegend=False)
        st.plotly_chart(fig, width="stretch")
        st.caption(f"{len(m):,} municípios citados. Tamanho = número de documentos que citam o município."
                   .replace(",", ".") + (" Ponto vermelho = sede da unidade." if unidade else "") +
                   " Contornos: IBGE.")
        tabela = m.sort_values("documentos", ascending=False)[["cod_ibge", "municipio", "uf", "documentos"]]
        chave, rotulo_col = "cod_ibge", "Município"
    else:
        e = q(f"""with m as (select distinct dm.doc_uid, dm.uf from doc_municipio dm
                             union select distinct doc_uid, uf from doc_estado)
                  select m.uf, count(distinct m.doc_uid) documentos
                  from m join documento d using (doc_uid) {join_tema} {join_un}
                  where d.ano between ? and ? and list_contains(?, d.tipo_doc) {filtro_tema} {filtro_un}
                  group by m.uf""", params)
        if e.empty:
            st.info("Nenhum estado citado com esses filtros.")
            return
        e["codarea"] = e.uf.map(COD_UF)
        fig = px.choropleth_map(e, geojson=geo_ufs(), locations="codarea", featureidkey="properties.codarea",
                                color="documentos", color_continuous_scale="Greens", hover_name="uf",
                                hover_data={"codarea": False, "documentos": True}, zoom=3.2,
                                center={"lat": -14.5, "lon": -52}, height=680, map_style="carto-positron",
                                opacity=0.75, labels={"documentos": "Documentos"})
        fig.update_layout(margin=dict(t=0, l=0, r=0, b=0))
        st.plotly_chart(fig, width="stretch")
        st.caption("Cor = documentos que citam o estado (pelo nome do estado ou de um de seus municípios). "
                   "Contornos: IBGE.")
        tabela = e.sort_values("documentos", ascending=False)[["uf", "documentos"]]
        chave, rotulo_col = "uf", "UF"

    # Detalhe: documentos que citam o local escolhido --------------------------------
    st.markdown("#### Locais mais citados")
    ev = st.dataframe(tabela, hide_index=True, width="stretch", on_select="rerun", selection_mode="single-row",
                      key=f"mapa_loc_{escala}", height=320,
                      column_config={"cod_ibge": None, "municipio": "Município", "uf": "UF",
                                     "documentos": "Documentos"})
    if not ev.selection.rows:
        st.caption("Clique num local para ver os documentos que o citam.")
        return
    sel = tabela.iloc[ev.selection.rows[0]]
    if escala == "municipio":
        docs = q(f"""select distinct d.doc_uid, d.tipo_doc tipo, d.ano, d.titulo, d.unidade_id
                     from doc_municipio dm join documento d using (doc_uid) {join_tema} {join_un}
                     where dm.cod_ibge = ? and d.ano between ? and ? and list_contains(?, d.tipo_doc)
                     {filtro_tema} {filtro_un} order by d.ano desc""", (sel.cod_ibge,) + params)
        titulo = f"{sel.municipio}/{sel.uf}"
    else:
        docs = q(f"""with m as (select distinct doc_uid, uf from doc_municipio union select distinct doc_uid, uf from doc_estado)
                     select distinct d.doc_uid, d.tipo_doc tipo, d.ano, d.titulo, d.unidade_id
                     from m join documento d using (doc_uid) {join_tema} {join_un}
                     where m.uf = ? and d.ano between ? and ? and list_contains(?, d.tipo_doc)
                     {filtro_tema} {filtro_un} order by d.ano desc""", (sel.uf,) + params)
        titulo = sel.uf
    docs["unidade"] = docs.unidade_id.map(dados.rotulo_unidade)
    docs["tipo"] = docs.tipo.map({"projeto": "Projeto", "publicacao": "Publicação", "tecnologia": "Tecnologia"})
    st.markdown(f"**Documentos que citam {titulo}** ({len(docs)})")
    ui.tabela_navegavel(docs.drop(columns="unidade_id"), "doc", "doc_uid", f"mapa_docs_{escala}", altura=380)


# ==================================================================================
@st.cache_data(show_spinner=False)
def geo_biomas() -> dict:
    return json.loads((Path(__file__).resolve().parents[1] / "assets" / "br_biomas.geojson").read_text(encoding="utf-8"))


def mapa_biomas() -> None:
    un = dados.unidades().query("n_docs > 0")
    with c3:
        fonte = st.radio("Origem do bioma", ["declarado", "municipio_citado"], horizontal=True,
                         format_func={"declarado": "Declarado (tecnologias)",
                                      "municipio_citado": "Municípios citados"}.get,
                         help="**Declarado**: campo *Bioma* do cadastro de tecnologias. **Municípios citados**: "
                              "bioma predominante (maior área) dos municípios citados no texto de projetos, "
                              "publicações e tecnologias.")
        unidade = st.selectbox("Produção da unidade", un.unidade_id.tolist(), index=None, key="bioma_un",
                               format_func=dados.nome_unidade, placeholder="Todas as unidades")
    tipos_b = list(tipos)
    if fonte == "declarado":
        st.info("O cadastro de tecnologias informa em que **biomas** cada tecnologia se aplica. Uma tecnologia "
                "pode valer para vários, e cerca de um quarto delas é indicada para **todos os seis** — por padrão "
                "essas ficam de fora, para o mapa mostrar as tecnologias voltadas a biomas específicos.",
                icon=":material/forest:")
        incluir_todos = st.toggle("Incluir tecnologias indicadas para todos os biomas", value=False)
        if "tecnologia" not in tipos:
            st.info("O bioma declarado só existe para tecnologias: inclua *Tecnologias* nos filtros de produção.")
            return
        tipos_b = ["tecnologia"]
    else:
        st.info("Cada município citado nos textos (ver *Onde a pesquisa acontece*) recebe o **bioma predominante** "
                "no seu território (maior área, contornos IBGE 2019). Um documento conta uma vez por bioma.",
                icon=":material/forest:")
        incluir_todos = True
    join_un = "join documento_unidade du using (doc_uid)" if unidade else ""
    filtro_un = "and du.unidade_id = ?" if unidade else ""
    base_where = f"""b.fonte = ? and (? or b.n_biomas < 6) and d.ano between ? and ?
                     and list_contains(?, d.tipo_doc) {filtro_tema} {filtro_un}"""
    params = (fonte, incluir_todos, a0, a1, tipos_b) + params_tema + ((unidade,) if unidade else ())
    b = q(f"""select b.bioma, count(distinct b.doc_uid) documentos
              from doc_bioma b join documento d using (doc_uid) {join_tema} {join_un}
              where {base_where} group by b.bioma""", params)
    if b.empty:
        st.info("Nenhum documento com bioma para esses filtros.")
        return
    tot = int(q(f"""select count(distinct b.doc_uid) n from doc_bioma b join documento d using (doc_uid)
                    {join_tema} {join_un} where {base_where}""", params).n.iloc[0])
    b["pct"] = 100 * b.documentos / tot

    col_mapa, col_barra = st.columns([3, 2])
    with col_mapa:
        fig = px.choropleth_map(b, geojson=geo_biomas(), locations="bioma", featureidkey="properties.bioma",
                                color="documentos", color_continuous_scale="Greens", hover_name="bioma",
                                range_color=(0, b.documentos.max()),
                                hover_data={"bioma": False, "documentos": True, "pct": ":.1f"},
                                labels={"documentos": "Documentos", "pct": "% dos documentos"},
                                zoom=2.8, center={"lat": -14.5, "lon": -53}, height=600,
                                map_style="carto-positron", opacity=0.8)
        if unidade:
            sede = q("select * from unidade_localizacao where unidade_id = ?", (unidade,))
            if not sede.empty:
                fig.add_trace(go.Scattermap(lat=sede.lat, lon=sede.lon, mode="markers", name="Sede",
                                            marker=dict(size=14, color="#C62828"), hoverinfo="text",
                                            hovertext=[f"Sede: {dados.nome_unidade(unidade)}"]))
        fig.update_layout(margin=dict(t=0, l=0, r=0, b=0), showlegend=False, coloraxis_showscale=False)
        st.plotly_chart(fig, width="stretch")
    with col_barra:
        bs = b.sort_values("documentos")
        fb = px.bar(bs, x="documentos", y="bioma", orientation="h", text=bs.pct.map(lambda v: f"{v:.0f}%"),
                    color="documentos", color_continuous_scale="Greens",
                    range_color=(0, bs.documentos.max()), labels={"documentos": "Documentos", "bioma": ""}, height=600)
        fb.update_layout(showlegend=False, coloraxis_showscale=False, margin=dict(t=10, l=0, r=10, b=0))
        st.plotly_chart(fb, width="stretch")
    st.caption(f"{tot:,} documentos com bioma. Os percentuais somam mais de 100% porque um documento pode se "
               "referir a vários biomas. Contornos: IBGE 2019 (via geobr/IPEA).".replace(",", ".") +
               (" Ponto vermelho = sede da unidade." if unidade else ""))

    # Detalhe por bioma -------------------------------------------------------------
    bioma = st.pills("Detalhar bioma", sorted(b.bioma), key=f"bioma_sel_{fonte}")
    if not bioma:
        st.caption("Escolha um bioma para ver as unidades e os documentos.")
        return
    t1, t2 = st.tabs(["Unidades", "Documentos"])
    with t1:
        u = q(f"""select du2.unidade_id, count(distinct b.doc_uid) documentos
                  from doc_bioma b join documento d using (doc_uid) {join_tema} {join_un}
                  join documento_unidade du2 on du2.doc_uid = b.doc_uid
                  where b.bioma = ? and {base_where} group by 1 order by 2 desc""", (bioma,) + params)
        u["unidade"] = u.unidade_id.map(dados.rotulo_unidade)
        ui.tabela_navegavel(u[["unidade_id", "unidade", "documentos"]], "unidade", "unidade_id",
                            f"bioma_un_{fonte}", altura=380, colunas={"unidade": "Unidade", "documentos": "Documentos"})
    with t2:
        docs = q(f"""select distinct d.doc_uid, d.tipo_doc tipo, d.ano, d.titulo, d.unidade_id
                     from doc_bioma b join documento d using (doc_uid) {join_tema} {join_un}
                     where b.bioma = ? and {base_where} order by d.ano desc""", (bioma,) + params)
        docs["unidade"] = docs.unidade_id.map(dados.rotulo_unidade)
        docs["tipo"] = docs.tipo.map({"projeto": "Projeto", "publicacao": "Publicação", "tecnologia": "Tecnologia"})
        st.markdown(f"**{bioma}** — {len(docs)} documentos")
        ui.tabela_navegavel(docs.drop(columns="unidade_id"), "doc", "doc_uid", f"bioma_docs_{fonte}", altura=380)


if visao == "sede":
    mapa_sedes()
elif visao == "territorio":
    mapa_territorio()
else:
    mapa_biomas()
