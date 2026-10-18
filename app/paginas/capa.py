"""Capa do Observatório: Visão geral e Visão por programação (objetivos estratégicos e portfólios)."""

import html
import json
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

from lib import dados, ui
from lib.dados import q

COD_UF = {"RO": "11", "AC": "12", "AM": "13", "RR": "14", "PA": "15", "AP": "16", "TO": "17", "MA": "21",
          "PI": "22", "CE": "23", "RN": "24", "PB": "25", "PE": "26", "AL": "27", "SE": "28", "BA": "29",
          "MG": "31", "ES": "32", "RJ": "33", "SP": "35", "PR": "41", "SC": "42", "RS": "43", "MS": "50",
          "MT": "51", "GO": "52", "DF": "53"}
VERDE, VERDE_CLARO = "#2E7D32", "#A5D6A7"
ANO_MIN = 1990
# "Desde 2024": produção sob a programação atual — projetos em execução a partir de 2024;
# publicações e tecnologias com ano >= 2024.
DESDE_2024 = "(case when d.tipo_doc = 'projeto' then coalesce(d.ano_fim, 9999) >= 2024 else d.ano >= 2024 end)"

# A capa usa camadas do banco 2026-10 em diante; com um banco anterior, abre a página Embrapa
if not {"doc_produto", "doc_localizacao"} <= set(q("select table_name from duckdb_tables()").table_name):
    st.switch_page("paginas/embrapa.py")

st.markdown("""
<style>
.hero {padding: 1.6rem 1.8rem; border-radius: 18px; color: #fff; margin-bottom: 1.2rem;
       background: linear-gradient(120deg, #1B5E20 0%, #2E7D32 55%, #558B2F 100%);}
.hero h1 {color: #fff; font-size: 2.1rem; margin: 0 0 .3rem 0; padding: 0;}
.hero p {margin: 0; opacity: .92; font-size: 1.02rem;}
.kpi {background: #F3F6F4; border-radius: 14px; padding: .9rem 1rem; height: 100%;}
.kpi .v {font-size: 1.65rem; font-weight: 700; color: #1B5E20; line-height: 1.1;}
.kpi .r {font-size: .85rem; color: #4A5A50; margin-top: .2rem;}
.card {border: 1px solid #DDE6E0; border-radius: 14px; padding: .9rem 1rem .8rem; background: #fff; height: 100%;
       box-shadow: 0 1px 2px rgba(0,0,0,.04);}
.card h4 {margin: 0 0 .25rem 0; font-size: 1.0rem; color: #1F2A24; line-height: 1.25;}
.card .sub {font-size: .80rem; color: #5F6B66; margin-bottom: .45rem; line-height: 1.3;}
.card .num {font-size: 1.35rem; font-weight: 700; color: #1B5E20;}
.card .num small {font-size: .78rem; font-weight: 400; color: #5F6B66;}
.card .duas {display: flex; gap: 1.4rem; align-items: flex-start; margin: .2rem 0 .3rem;}
.card .duas small {display: block; margin-top: .05rem;}
.chip {display: inline-block; background: #EEF4EF; color: #1F4D27; border-radius: 999px; padding: .08rem .55rem;
       font-size: .74rem; margin: 0 .25rem .25rem 0;}
a.cardlink {text-decoration: none; color: inherit; display: block; height: 100%;}
a.cardlink .card {transition: box-shadow .15s, border-color .15s;}
a.cardlink:hover .card {border-color: #2E7D32; box-shadow: 0 3px 10px rgba(46,125,50,.18);}
.card .seta {color: #2E7D32; font-weight: 400;}
.secao {font-size: 1.25rem; font-weight: 700; color: #1F2A24; margin: 1.3rem 0 .5rem;}
</style>""", unsafe_allow_html=True)


def fmt(n) -> str:
    return f"{int(n):,}".replace(",", ".")


def sparkline(serie: pd.Series, largura: int = 140, altura: int = 34) -> str:
    """Minigráfico SVG da série anual (participação ou contagem)."""
    s = serie.reindex(range(ANO_MIN, int(serie.index.max()) + 1 if len(serie) else ANO_MIN + 1), fill_value=0)
    if s.max() <= 0:
        return ""
    xs = [i * largura / max(len(s) - 1, 1) for i in range(len(s))]
    ys = [altura - 3 - (v / s.max()) * (altura - 6) for v in s.values]
    pts = " ".join(f"{x:.1f},{y:.1f}" for x, y in zip(xs, ys))
    area = f"0,{altura} " + pts + f" {largura},{altura}"
    return (f'<svg width="{largura}" height="{altura}" viewBox="0 0 {largura} {altura}">'
            f'<polygon points="{area}" fill="{VERDE_CLARO}" opacity=".45"/>'
            f'<polyline points="{pts}" fill="none" stroke="{VERDE}" stroke-width="1.6"/></svg>')


@st.cache_data(show_spinner=False)
def geo_ufs() -> dict:
    return json.loads((Path(__file__).resolve().parents[1] / "assets" / "br_uf.geojson").read_text(encoding="utf-8"))


def mapa_estados(where_docs: str, params: tuple, completar: bool, altura: int = 470, chave: str = "") -> None:
    """Coroplético por estado com a localização combinada (local citado → sede da unidade)."""
    fontes = ["municipio_citado", "estado_citado"] + (["sede_unidade"] if completar else [])
    e = q(f"""select l.uf, count(distinct l.doc_uid) documentos,
                     count(distinct l.doc_uid) filter (where l.fonte <> 'sede_unidade') citados
              from doc_localizacao l join documento d using (doc_uid)
              where list_contains(?, l.fonte) and {where_docs} group by 1""", (fontes,) + params)
    if e.empty:
        st.caption("Sem localização para este recorte.")
        return
    e["pela_sede"] = e.documentos - e.citados
    e["codarea"] = e.uf.map(COD_UF)
    fig = px.choropleth_map(e, geojson=geo_ufs(), locations="codarea", featureidkey="properties.codarea",
                            color="documentos", color_continuous_scale="Greens", hover_name="uf",
                            hover_data={"codarea": False, "documentos": True, "citados": True, "pela_sede": True},
                            labels={"documentos": "Documentos", "citados": "Local citado no texto",
                                    "pela_sede": "Pela sede da unidade"},
                            zoom=2.8, center={"lat": -14.5, "lon": -53}, height=altura,
                            map_style="carto-positron", opacity=0.8)
    fig.update_layout(margin=dict(t=0, l=0, r=0, b=0), coloraxis_showscale=False)
    st.plotly_chart(fig, width="stretch", key=f"mapa_{chave}")
    pct = 100 * e.citados.sum() / max(e.documentos.sum(), 1)
    st.caption(f"Estado do local citado no texto ou, sem citação, da sede da unidade (aproximação). "
               f"{pct:.0f}% das contagens vêm de local citado." if completar else
               "Só locais citados no texto (título, resumo, palavras-chave).")


# ==================================================================================
m = dados.meta()
st.markdown(f"""<div class="hero"><h1>Observatório de Pesquisa da Embrapa</h1>
<p>Projetos, publicações e soluções tecnológicas da Embrapa — temas, produtos, território e programação.
Dados do Redape, exportação {html.escape(m['exportacao'])}.</p></div>""", unsafe_allow_html=True)

visao = st.segmented_control("Visão", ["geral", "programacao"], default="geral", key="capa_visao",
                             format_func={"geral": "Visão geral", "programacao": "Visão por programação"}.get,
                             label_visibility="collapsed") or "geral"


# ==================================================================================
def visao_geral() -> None:
    tot = q("select tipo_doc, count(*) n from documento group by 1").set_index("tipo_doc").n
    n_doc = int(tot.sum())
    n_un = q("select count(distinct unidade_id) n from documento_unidade").n.iloc[0]
    n_prod = q("select count(distinct doc_uid) n from doc_produto where forca = 'principal'").n.iloc[0]
    n_loc = q("select count(distinct doc_uid) n from doc_localizacao where fonte <> 'sede_unidade'").n.iloc[0]
    kpis = [(fmt(tot.get("publicacao", 0)), "publicações (obras)"), (fmt(tot.get("projeto", 0)), "projetos"),
            (fmt(tot.get("tecnologia", 0)), "soluções tecnológicas"), (fmt(n_un), "unidades com produção"),
            (f"{100 * n_prod / n_doc:.0f}%", "com produto agropecuário"),
            (f"{100 * n_loc / n_doc:.0f}%", "com local citado no texto")]
    for col, (v, r) in zip(st.columns(len(kpis)), kpis):
        col.markdown(f'<div class="kpi"><div class="v">{v}</div><div class="r">{r}</div></div>',
                     unsafe_allow_html=True)

    st.markdown('<div class="secao">Onde está a produção</div>', unsafe_allow_html=True)
    tm = dados.temas()
    macros = tm[tm.nivel == 1].sort_values("n_total", ascending=False)
    prods = q("""select produto, count(distinct doc_uid) n from doc_produto where forca = 'principal'
                 group by 1 order by 2 desc""")
    # Filtros encadeados: o macrotema restringe a lista de produtos (só os que aparecem nele), em ordem alfabética
    c1, c2, c3 = st.columns([3, 3, 2])
    macro = c1.selectbox("Macrotema", macros.tema_id.tolist(), index=None, key="capa_macro",
                         format_func=dados.rotulo_tema, placeholder="Todos os macrotemas")
    if macro:
        pm = q("""select p.produto, count(distinct p.doc_uid) n from doc_produto p join doc_tema t using (doc_uid)
                  where p.forca = 'principal' and t.macro_id = ? group by 1""", (macro,))
        # só produtos com peso no macrotema (>= 0,5% dos documentos dele, mínimo 5): evita menções marginais
        n_macro = int(macros.set_index("tema_id").n_total[macro])
        pm = pm[pm.n >= max(5, 0.005 * n_macro)]
    else:
        pm = prods
    sem_acento = lambda s: s.str.normalize("NFKD").str.encode("ascii", "ignore").str.decode("ascii").str.lower()
    pm = pm.sort_values("produto", key=sem_acento)
    n_prod = dict(zip(pm.produto, pm.n))
    if st.session_state.get("capa_prod") not in n_prod:      # produto fora do macrotema escolhido
        st.session_state["capa_prod"] = None
    produto = c2.selectbox("Produto", list(n_prod), index=None, key="capa_prod",
                           format_func=lambda p: f"{p} ({fmt(n_prod[p])})",
                           placeholder="Todos os produtos" + (" deste macrotema" if macro else ""))
    completar = c3.toggle("Completar com a sede da unidade", value=True, key="capa_completar")
    cond, params = ["true"], ()
    if macro:
        cond.append("d.doc_uid in (select doc_uid from doc_tema where macro_id = ?)")
        params += (macro,)
    if produto:
        cond.append("d.doc_uid in (select doc_uid from doc_produto where forca = 'principal' and produto = ?)")
        params += (produto,)
    mapa_estados(" and ".join(cond), params, completar, chave="geral")

    # Cards: macrotemas e produtos -----------------------------------------------------
    serie_tema = q(f"""select t.macro_id, d.ano, count(*) n from doc_tema t join documento d using (doc_uid)
                       where d.ano >= {ANO_MIN} group by all""")
    st.markdown('<div class="secao">Grandes temas</div>', unsafe_allow_html=True)
    cards = []
    for r in macros.head(12).itertuples():
        s = serie_tema[serie_tema.macro_id == r.tema_id].set_index("ano").n
        filhos = tm[(tm.nivel == 2) & (tm.pai_id == r.tema_id)].sort_values("n_total", ascending=False).rotulo.head(3)
        cards.append(f"""<a class="cardlink" href="temas?macro={r.tema_id}" target="_self"><div class="card">
            <h4>{html.escape(r.rotulo)} <span class="seta">→</span></h4>
            <div class="num">{fmt(r.n_total)} <small>documentos · {100 * r.n_total / n_doc:.1f}% do acervo</small></div>
            {sparkline(s)}<div>{''.join(f'<span class="chip">{html.escape(f)}</span>' for f in filhos)}</div></div></a>""")
    grade(cards, 4)
    st.caption("Temas identificados por similaridade semântica (SBERT + BERTopic). Minigráfico: documentos por ano "
               f"desde {ANO_MIN}. **Clique num card** para abrir o macrotema na página Temas.")

    st.markdown('<div class="secao">Produtos agropecuários</div>', unsafe_allow_html=True)
    serie_prod = q(f"""select p.produto, d.ano, count(distinct p.doc_uid) n
                       from doc_produto p join documento d using (doc_uid)
                       where p.forca = 'principal' and d.ano >= {ANO_MIN} group by all""")
    cat = q("select distinct produto, categoria_ampla from doc_produto").drop_duplicates("produto") \
        .set_index("produto").categoria_ampla
    cards = []
    for r in prods.head(12).itertuples():
        s = serie_prod[serie_prod.produto == r.produto].set_index("ano").n
        cards.append(f"""<div class="card"><h4>{html.escape(r.produto)}</h4>
            <div class="sub">{html.escape(str(cat.get(r.produto, '')))}</div>
            <div class="num">{fmt(r.n)} <small>documentos</small></div>{sparkline(s)}</div>""")
    grade(cards, 4)
    st.caption(f"Produto principal = citado no título ou nas palavras-chave ({fmt(n_prod)} documentos). Taxonomia de "
               "produtos com base nas categorias do IBGE (PAM, PPM, PEVS); termos e agrupamentos em validação.")


def grade(cards: list[str], por_linha: int) -> None:
    for i in range(0, len(cards), por_linha):
        cols = st.columns(por_linha)
        for c, h in zip(cols, cards[i:i + por_linha]):
            c.markdown(h, unsafe_allow_html=True)
        st.write("")


# ==================================================================================
@st.cache_data(show_spinner=False)
def base_programacao() -> pd.DataFrame:
    """Documento → objetivo, especificação e portfólios, herdados do tema (tabela referendada)."""
    return q(f"""select dt.doc_uid, d.tipo_doc, d.ano, {DESDE_2024} desde_2024,
                        tp.portfolio_1, tp.portfolio_2, tp.especificacao_1, tp.especificacao_2,
                        substr(tp.especificacao_1, 1, 3) objetivo_1, substr(tp.especificacao_2, 1, 3) objetivo_2
                 from doc_tema dt join documento d using (doc_uid)
                 join tema_programacao tp using (tema_id)""")


def visao_programacao() -> None:
    if "tema_programacao" not in set(q("select table_name from duckdb_tables()").table_name):
        st.info("A tabela tema → programação ainda não está neste banco.")
        return
    base = base_programacao()
    port = q("select * from portfolio")
    esp = q("select * from especificacao")
    obj = esp.drop_duplicates("objetivo_id")[["objetivo_id", "objetivo", "enunciado"]]
    c1, c2 = st.columns([2, 3])
    eixo = c1.segmented_control("Organizar por", ["objetivo", "portfolio"], default="objetivo", key="capa_eixo",
                                format_func={"objetivo": "Objetivos estratégicos", "portfolio": "Portfólios"}.get) \
        or "objetivo"
    c2.caption("Cada documento herda objetivo, especificação e portfólios do seu **tema** (tabela tema → programação "
               "referendada em 18/10/2026). **Todo o acervo** = aderência de conteúdo à agenda atual; **desde 2024** "
               "= produção sob a programação vigente. Temas de gestão institucional ficam de fora (transversais).")

    col1, col2 = ("objetivo_1", "objetivo_2") if eixo == "objetivo" else ("portfolio_1", "portfolio_2")
    itens = obj.rename(columns={"objetivo_id": "id", "objetivo": "nome", "enunciado": "texto"}) if eixo == "objetivo" \
        else port.rename(columns={"portfolio_id": "id", "nome_portal": "nome", "caracterizacao": "texto"})
    prod = q("select doc_uid, produto from doc_produto where forca = 'principal'")
    tm = dados.temas()

    cards = []
    for r in itens.itertuples():
        b = base[base[col1] == r.id]
        sec = base[(base[col2] == r.id) & (base[col1] != r.id)].doc_uid.nunique()
        recentes = int(b.desde_2024.sum())
        s = b[b.ano >= ANO_MIN].groupby("ano").size()
        tops_p = prod[prod.doc_uid.isin(b.doc_uid)].produto.value_counts().head(3).index
        texto = r.texto.split(". ")[0][:150] + ("…" if len(r.texto) > 150 else "")
        cards.append(f"""<div class="card"><h4>{html.escape(r.nome)}</h4>
            <div class="sub">{html.escape(texto)}</div>
            <div class="duas"><div class="num">{fmt(len(b))} <small>todo o acervo</small></div>
            <div class="num">{fmt(recentes)} <small>desde 2024</small></div></div>
            <div class="sub">+{fmt(sec)} como {"objetivo" if eixo == "objetivo" else "portfólio"} secundário</div>
            {sparkline(s)}<div>{''.join(f'<span class="chip">{html.escape(p)}</span>' for p in tops_p)}</div></div>""")
    grade(cards, 3 if eixo == "objetivo" else 3)

    # Detalhe ---------------------------------------------------------------------------
    st.markdown('<div class="secao">Detalhar</div>', unsafe_allow_html=True)
    nomes = dict(zip(itens.id, itens.nome))
    sel = st.pills("Escolha", list(nomes), format_func=nomes.get, key=f"capa_sel_{eixo}",
                   label_visibility="collapsed")
    if not sel:
        st.caption("Escolha um card para ver mapa, especificações, produtos, temas, unidades e documentos.")
        return
    leitura = st.segmented_control("Leitura", ["todo", "2024"], default="todo", key="capa_leitura",
                                   format_func={"todo": "Todo o acervo", "2024": "Desde 2024"}.get) or "todo"
    b = base[base[col1] == sel]
    if leitura == "2024":
        b = b[b.desde_2024]
    st.markdown(f"**{nomes[sel]}** — {fmt(len(b))} documentos " +
                ("(todo o acervo)" if leitura == "todo" else "(desde 2024)"))
    ids = tuple(b.doc_uid)
    if not ids:
        st.info("Nenhum documento neste recorte.")
        return
    c1, c2 = st.columns([3, 2])
    with c1:
        mapa_estados("list_contains(?, d.doc_uid)", (list(ids),), True, altura=430, chave=f"det_{sel}_{leitura}")
    with c2:
        if eixo == "objetivo":
            g = b.especificacao_1.value_counts().rename_axis("especificacao_id").reset_index(name="documentos") \
                .merge(esp[["especificacao_id", "especificacao"]], on="especificacao_id")
            fig = px.bar(g.sort_values("documentos"), x="documentos", y="especificacao", orientation="h",
                         color_discrete_sequence=[VERDE], labels={"documentos": "Documentos", "especificacao": ""},
                         height=430, title="Especificações do Plano Diretor")
        else:
            g = b.especificacao_1.str.slice(0, 3).value_counts().rename_axis("objetivo_id") \
                .reset_index(name="documentos").merge(obj, on="objetivo_id")
            fig = px.bar(g.sort_values("documentos"), x="documentos", y="objetivo", orientation="h",
                         color_discrete_sequence=[VERDE], labels={"documentos": "Documentos", "objetivo": ""},
                         height=430, title="Objetivos estratégicos")
        fig.update_layout(margin=dict(l=0, r=10, t=40, b=0), title_font_size=14)
        st.plotly_chart(fig, width="stretch", key=f"barras_{sel}_{leitura}")

    t_prod, t_tema, t_un, t_docs = st.tabs(["Produtos", "Temas", "Unidades", "Documentos"])
    with t_prod:
        p = prod[prod.doc_uid.isin(ids)].produto.value_counts().head(20).rename_axis("produto") \
            .reset_index(name="documentos")
        fig = px.bar(p.sort_values("documentos"), x="documentos", y="produto", orientation="h",
                     color_discrete_sequence=[VERDE], height=max(300, 22 * len(p) + 80),
                     labels={"documentos": "Documentos", "produto": ""})
        fig.update_layout(margin=dict(l=0, r=10, t=10, b=0))
        st.plotly_chart(fig, width="stretch", key=f"prod_{sel}_{leitura}")
    with t_tema:
        t = q("select tema_id, count(*) documentos from doc_tema where list_contains(?, doc_uid) group by 1 "
              "order by 2 desc limit 20", (list(ids),))
        t["tema"] = t.tema_id.map(dados.rotulo_tema)
        ui.tabela_navegavel(t[["tema_id", "tema", "documentos"]], "tema", "tema_id", f"capa_temas_{sel}",
                            altura=360, colunas={"tema": "Tema", "documentos": "Documentos"})
    with t_un:
        u = q("select unidade_id, count(distinct doc_uid) documentos from documento_unidade "
              "where list_contains(?, doc_uid) group by 1 order by 2 desc", (list(ids),))
        u["unidade"] = u.unidade_id.map(dados.rotulo_unidade)
        ui.tabela_navegavel(u[["unidade_id", "unidade", "documentos"]], "unidade", "unidade_id", f"capa_un_{sel}",
                            altura=360, colunas={"unidade": "Unidade", "documentos": "Documentos"})
    with t_docs:
        d = q("select doc_uid, tipo_doc tipo, ano, titulo, unidade_id from documento where list_contains(?, doc_uid) "
              "order by ano desc limit 500", (list(ids),))
        d["unidade"] = d.unidade_id.map(dados.rotulo_unidade)
        d["tipo"] = d.tipo.map({"projeto": "Projeto", "publicacao": "Publicação", "tecnologia": "Tecnologia"})
        st.caption("Os 500 mais recentes.")
        ui.tabela_navegavel(d.drop(columns="unidade_id"), "doc", "doc_uid", f"capa_docs_{sel}", altura=380)


if visao == "geral":
    visao_geral()
else:
    visao_programacao()
