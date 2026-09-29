import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from lib import dados, ui
from lib.dados import q

a0, a1 = dados.periodo()
st.title("Mapa da produção")
st.caption(f"Produção e temas pela localização das unidades · {a0}–{a1}")
st.info("Cada unidade aparece no local do seu **campus-sede** (coordenadas do Portal Embrapa). A sede indica onde a "
        "unidade está, não necessariamente onde a pesquisa acontece — muitas unidades atuam em todo o país.",
        icon=":material/location_on:")

# Filtros --------------------------------------------------------------------------
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
                                placeholder="Toda a produção",
                                help="◆ = macrotema. Com um tema escolhido, o tamanho mostra a produção da unidade "
                                     "no tema e a cor, a especialização da unidade nele.")
with c3:
    mostrar_rede = st.toggle("Mostrar colaboração entre unidades", value=False)
    n_arcos = st.slider("Ligações desenhadas (as mais fortes)", 10, 150, 40, disabled=not mostrar_rede)

if not tipos:
    st.info("Escolha ao menos um tipo de produção.")
    st.stop()

# Dados ----------------------------------------------------------------------------
loc = q("select * from unidade_localizacao")
filtro_tema, params_tema = "", ()
if tema_sel:
    col = "macro_id" if tema_sel.startswith("M") else "tema_id"
    filtro_tema, params_tema = f"and t.{col} = ?", (tema_sel,)

base = q(f"""
    select du.unidade_id, d.tipo_doc, count(distinct du.doc_uid) n
    from documento_unidade du join documento d using (doc_uid)
    {"join doc_tema t using (doc_uid)" if tema_sel else ""}
    where d.ano between ? and ? and list_contains(?, d.tipo_doc) {filtro_tema}
    group by all
""", (a0, a1, list(tipos)) + params_tema)
tab = base.pivot_table(index="unidade_id", columns="tipo_doc", values="n", aggfunc="sum", fill_value=0)
for t in dados.TIPOS:
    if t not in tab:
        tab[t] = 0
tab["total"] = tab[list(dados.TIPOS)].sum(axis=1)
tab = tab.reset_index().merge(loc, on="unidade_id", how="inner")
tab["unidade"] = tab.unidade_id.map(dados.rotulo_unidade)

if tema_sel:
    # especialização: peso do tema na unidade ÷ peso do tema na Embrapa (mesmos tipos e período)
    tot_un = q("""select du.unidade_id, count(distinct du.doc_uid) n from documento_unidade du
                  join documento d using (doc_uid) where d.ano between ? and ? and list_contains(?, d.tipo_doc)
                  group by 1""", (a0, a1, list(tipos))).set_index("unidade_id").n
    tot = q("""select count(*) n, count(*) filter (where t.{0} = ?) nt from documento d join doc_tema t using (doc_uid)
               where d.ano between ? and ? and list_contains(?, d.tipo_doc)""".format(col),
            (tema_sel, a0, a1, list(tipos))).iloc[0]
    tab["especializacao"] = (tab.total / tab.unidade_id.map(tot_un)) / (tot.nt / max(tot.n, 1))
    cor, legenda_cor = "especializacao", "Especialização"
elif dados.tem_semantica():
    dom = q("""select du.unidade_id, t.macro_id, count(distinct du.doc_uid) n from documento_unidade du
               join documento d using (doc_uid) join doc_tema t using (doc_uid)
               where d.ano between ? and ? and list_contains(?, d.tipo_doc) group by all""", (a0, a1, list(tipos)))
    dom = dom.sort_values("n", ascending=False).drop_duplicates("unidade_id")
    tab["macrotema"] = tab.unidade_id.map(dom.set_index("unidade_id").macro_id).map(dados.rotulo_tema).fillna("—")
    cor, legenda_cor = "macrotema", "Macrotema dominante"
else:
    cor, legenda_cor = None, None

tab = tab[tab.total > 0]
if tab.empty:
    st.info("Nenhuma produção com esses filtros.")
    st.stop()

# Mapa -----------------------------------------------------------------------------
tab["rotulo_hover"] = (tab.unidade + " — " + tab.municipio + "/" + tab.uf)
hover = {"lat": False, "lon": False, "total": True, "projeto": True, "publicacao": True, "tecnologia": True}
if tema_sel:
    hover["especializacao"] = ":.2f"
fig = px.scatter_map(
    tab, lat="lat", lon="lon", size="total", size_max=42, hover_name="rotulo_hover", hover_data=hover,
    color=cor, color_continuous_scale="RdYlGn" if tema_sel else None,
    color_continuous_midpoint=1 if tema_sel else None,
    labels={"total": "Documentos", "projeto": "Projetos", "publicacao": "Publicações",
            "tecnologia": "Tecnologias", "especializacao": "Especialização", "macrotema": "Macrotema dominante"},
    zoom=3.2, center={"lat": -14.5, "lon": -52}, height=680, map_style="carto-positron")

if mostrar_rede:
    r = dados.rede_unidades(a0, a1, ("publicacoes",)).nlargest(n_arcos, "peso")
    pos = loc.set_index("unidade_id")[["lat", "lon"]]
    r = r[r.unidade1.isin(pos.index) & r.unidade2.isin(pos.index)]
    if not r.empty:
        wmax = r.peso.max()
        # três classes de espessura (um traço por classe, segmentos separados por None)
        for lim_inf, lim_sup, larg in [(0, 1 / 3, 1), (1 / 3, 2 / 3, 2.5), (2 / 3, 1.01, 4.5)]:
            sub = r[(r.peso / wmax >= lim_inf) & (r.peso / wmax < lim_sup)]
            lats, lons = [], []
            for _, e in sub.iterrows():
                lats += [pos.lat[e.unidade1], pos.lat[e.unidade2], None]
                lons += [pos.lon[e.unidade1], pos.lon[e.unidade2], None]
            if lats:
                fig.add_trace(go.Scattermap(lat=lats, lon=lons, mode="lines", hoverinfo="skip", showlegend=False,
                                            line=dict(width=larg, color="rgba(21,101,192,0.45)")))
        # linhas por baixo dos círculos
        fig.data = tuple([d for d in fig.data if getattr(d, "mode", "") == "lines"] +
                         [d for d in fig.data if getattr(d, "mode", "") != "lines"])

fig.update_layout(margin=dict(t=0, l=0, r=0, b=0), legend=dict(title=legenda_cor, orientation="h", y=-0.02))
st.plotly_chart(fig, width="stretch")

legenda = ("Tamanho = número de documentos com participação da unidade (qualquer papel: líder, depositante, "
           "responsável ou afiliação de autor).")
if tema_sel:
    legenda += (f" Tema: **{dados.rotulo_tema(tema_sel)}**. Cor = especialização da unidade no tema "
                "(verde > 1: o tema pesa mais na unidade que na média da Embrapa).")
elif cor:
    legenda += " Cor = macrotema com mais documentos da unidade."
if mostrar_rede:
    legenda += " Linhas = publicações em conjunto (espessura = intensidade)."
st.caption(legenda)

# Tabela ---------------------------------------------------------------------------
st.markdown("#### Unidades")
cols = ["unidade_id", "unidade", "municipio", "uf", "total", "projeto", "publicacao", "tecnologia"]
if tema_sel:
    cols.append("especializacao")
elif cor:
    cols.append("macrotema")
ui.tabela_navegavel(
    tab.sort_values("total", ascending=False)[cols], "unidade", "unidade_id", "mapa_tab", altura=420,
    colunas={"unidade": "Unidade", "municipio": "Município", "uf": "UF", "total": "Documentos",
             "projeto": "Projetos", "publicacao": "Publicações", "tecnologia": "Tecnologias",
             "especializacao": st.column_config.NumberColumn("Especialização", format="%.2f"),
             "macrotema": "Macrotema dominante"})
