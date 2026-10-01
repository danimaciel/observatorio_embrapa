import pandas as pd
import plotly.express as px
import streamlit as st

from lib import dados, ui
from lib.dados import q, q_interno

ODS = {1: "Erradicação da pobreza", 2: "Fome zero e agricultura sustentável", 3: "Saúde e bem-estar",
       4: "Educação de qualidade", 5: "Igualdade de gênero", 6: "Água potável e saneamento",
       7: "Energia limpa e acessível", 8: "Trabalho decente e crescimento econômico",
       9: "Indústria, inovação e infraestrutura", 10: "Redução das desigualdades",
       11: "Cidades e comunidades sustentáveis", 12: "Consumo e produção responsáveis",
       13: "Ação contra a mudança global do clima", 14: "Vida na água", 15: "Vida terrestre",
       16: "Paz, justiça e instituições eficazes", 17: "Parcerias e meios de implementação"}
NIVEIS = {"portfolio": "Portfólio", "objetivo": "Objetivo estratégico", "meta": "Meta estratégica",
          "desafio": "Desafio para Inovação", "ods": "ODS"}
CONF = {"alta": "Alta", "media": "Média", "baixa": "Baixa"}

st.title("Programação")
st.caption(":material/lock: Área restrita — conteúdo da programação de uso interno.")
if not dados.liberar_interno():
    st.stop()

st.caption("Aderência da produção à estrutura da programação da Embrapa — Desafios para Inovação, portfólios, "
           "objetivos, metas e ODS — por **similaridade semântica (SBERT)**. Conteúdo produzido sob a programação "
           "atual: projetos em execução desde 2024 e publicações e tecnologias de 2024 em diante.")
with st.expander("Como ler esta página"):
    st.markdown(
        "- Cada documento é comparado ao texto dos **107 Desafios para Inovação**; o desafio mais próximo em "
        "conteúdo define o portfólio, o objetivo estratégico, a meta e o ODS (pela tabela da programação).\n"
        "- É **aderência de conteúdo**, não o vínculo formal do projeto no SEG.\n"
        "- **Confiança** (alta, média, baixa): terços da similaridade com o desafio, por tipo de documento. Numa "
        "conferência inicial, a maioria dos casos de confiança alta faz sentido; os de baixa, em geral, não — "
        "por isso o padrão mostra alta e média.\n"
        "- O **ODS** vem do desafio: como 49 dos 107 desafios apontam para o ODS 2, ele predomina. É uma leitura "
        "pela programação, não uma classificação independente dos ODS.\n"
        "- Metas marcadas como encerradas na programação aparecem com *(encerrada)*.")


@st.cache_data(show_spinner=False)
def desafios() -> pd.DataFrame:
    d = q_interno("select * from desafio")
    d["ods_rotulo"] = d.ods_num.map(lambda n: f"ODS {int(n)} · {ODS.get(int(n), '')}" if pd.notna(n) else "Sem ODS")
    d["meta_rotulo"] = d.meta_id + " · " + d.meta.str.slice(0, 90) + d.meta.str.len().gt(90).map({True: "…", False: ""}) \
        + d.meta_encerrada.map({True: " (encerrada)", False: ""})
    d["desafio_rotulo"] = d.desafio_id + " · " + d.desafio.str.slice(0, 90) + \
        d.desafio.str.len().gt(90).map({True: "…", False: ""})
    return d


des = desafios()
COL = {"portfolio": "portfolio", "objetivo": "objetivo", "meta": "meta_rotulo", "desafio": "desafio_rotulo",
       "ods": "ods_rotulo"}

# Filtros ---------------------------------------------------------------------------
c1, c2, c3 = st.columns([3, 2, 2])
nivel = c1.segmented_control("Ver por", list(NIVEIS), default="portfolio", format_func=NIVEIS.get,
                             key="prog_nivel") or "portfolio"
conf = c2.pills("Confiança", list(CONF), selection_mode="multi", default=["alta", "media"],
                format_func=CONF.get, key="prog_conf")
tipos = c3.pills("Produção", list(dados.TIPOS), selection_mode="multi", default=list(dados.TIPOS),
                 format_func=dados.TIPOS.get, key="prog_tipos")
un = dados.unidades().query("n_docs > 0")
unidade = st.selectbox("Unidade", un.unidade_id.tolist(), index=None, format_func=dados.nome_unidade,
                       placeholder="Todas as unidades", key="prog_un")
if not conf or not tipos:
    st.info("Escolha ao menos um nível de confiança e um tipo de produção.")
    st.stop()

join_un = "join doc_unidade_prog du using (doc_uid)" if unidade else ""
filtro_un = "and du.unidade_id = ?" if unidade else ""
base = q_interno(f"""select distinct dd.doc_uid, dd.desafio_id, dd.sim, dd.confianca, d.tipo_doc, d.ano, d.titulo, d.unidade_id
             from doc_desafio dd join doc_info d using (doc_uid) {join_un}
             where dd.rank = 1 and list_contains(?, dd.confianca) and list_contains(?, d.tipo_doc) {filtro_un}""",
         (list(conf), list(tipos)) + ((unidade,) if unidade else ()))
base = base.merge(des, on="desafio_id", how="left")
if base.empty:
    st.info("Nenhum documento com esses filtros.")
    st.stop()

cont = base.tipo_doc.value_counts()
ui.kpis([("Projetos", int(cont.get("projeto", 0))), ("Publicações", int(cont.get("publicacao", 0))),
         ("Tecnologias", int(cont.get("tecnologia", 0))),
         (f"{NIVEIS[nivel]}s com produção" if nivel != "ods" else "ODS com produção", base[COL[nivel]].nunique())])

t_dist, t_estr, t_un = st.tabs(["Distribuição", "Estrutura", "Unidades × portfólios"])

with t_dist:
    g = base.groupby([COL[nivel], "tipo_doc"]).size().reset_index(name="n")
    ordem = g.groupby(COL[nivel]).n.sum().sort_values(ascending=False).index.tolist()
    g["tipo"] = g.tipo_doc.map(dados.TIPOS)
    fig = px.bar(g, x="n", y=COL[nivel], color="tipo", orientation="h",
                 color_discrete_map={dados.TIPOS[k]: v for k, v in dados.CORES_TIPO.items()},
                 category_orders={COL[nivel]: ordem}, height=max(320, 26 * len(ordem) + 120),
                 labels={"n": "Documentos", COL[nivel]: "", "tipo": ""})
    fig.update_layout(legend=dict(orientation="h", y=1.02, yanchor="bottom", x=0), margin=dict(l=0, r=10, t=30))
    st.plotly_chart(fig, width="stretch")
    st.caption("Documentos pelo desafio mais aderente de cada um.")

with t_estr:
    e = base.groupby(["objetivo", "portfolio", "desafio_id", "desafio"]).size().reset_index(name="documentos")
    e["rotulo"] = e.desafio_id + " · " + e.desafio.str.slice(0, 45) + "…"
    fig = px.treemap(e, path=[px.Constant("Programação"), "objetivo", "portfolio", "rotulo"],
                     values="documentos", height=720, custom_data=["desafio"])
    fig.update_traces(root_color="#f3f3f3", textinfo="label+value",
                      hovertemplate="%{label}<br>%{value} documentos<extra></extra>")
    fig.update_layout(margin=dict(t=10, l=0, r=0, b=0))
    st.plotly_chart(fig, width="stretch")
    st.caption("Objetivo estratégico › portfólio › desafio. Clique numa caixa para ampliar; clique no topo para voltar.")

with t_un:
    x = q_interno(f"""select du.unidade_id, dd.desafio_id, count(distinct dd.doc_uid) n
              from doc_desafio dd join doc_info d using (doc_uid) join doc_unidade_prog du using (doc_uid)
              where dd.rank = 1 and list_contains(?, dd.confianca) and list_contains(?, d.tipo_doc)
              group by all""", (list(conf), list(tipos))).merge(des[["desafio_id", "portfolio"]], on="desafio_id")
    m = x.groupby(["unidade_id", "portfolio"]).n.sum().unstack(fill_value=0)
    m = m[m.sum(axis=1) >= 10]
    pct = (100 * m.div(m.sum(axis=1), axis=0)).round(0)
    pct.index = pct.index.map(dados.rotulo_unidade)
    pct = pct.sort_index()
    fig = px.imshow(pct, color_continuous_scale="Greens", aspect="auto", text_auto=".0f",
                    labels={"x": "", "y": "", "color": "% da unidade"}, height=max(400, 22 * len(pct) + 160))
    fig.update_xaxes(side="top", tickangle=-30)
    fig.update_layout(margin=dict(t=10, l=0, r=0, b=0))
    st.plotly_chart(fig, width="stretch")
    st.caption("Percentual da produção de cada unidade (desde 2024) em cada portfólio. Unidades com ao menos "
               "10 documentos.")

# Detalhe ---------------------------------------------------------------------------
st.divider()
opcoes = base[COL[nivel]].value_counts().index.tolist()
item = st.selectbox(f"Detalhar {NIVEIS[nivel].lower()}", opcoes, index=None, key=f"prog_item_{nivel}",
                    placeholder=f"Escolha um item para ver documentos e unidades")
if not item:
    st.stop()
sub = base[base[COL[nivel]] == item]
dd = des[des[COL[nivel]] == item]
if nivel == "desafio":
    r = dd.iloc[0]
    st.markdown(f"**{r.desafio_id}** — {r.desafio}")
    st.markdown(f"Portfólio: **{r.portfolio}** · Objetivo: **{r.objetivo}** · ODS: **{r.ods_rotulo}**  \n"
                f"Meta: {r.meta_rotulo}")
else:
    st.markdown(f"**{item}** — {dd.desafio_id.nunique()} desafios, {len(sub)} documentos")

t_docs, t_uns, t_des = st.tabs(["Documentos mais aderentes", "Unidades", "Desafios"])
with t_docs:
    if nivel == "desafio":
        # para um desafio, entram também documentos em que ele é o 2º ou 3º mais aderente
        docs = q_interno(f"""select dd.doc_uid, dd.rank, dd.sim, dd.confianca, d.tipo_doc tipo, d.ano, d.titulo, d.unidade_id
                     from doc_desafio dd join doc_info d using (doc_uid) {join_un}
                     where dd.desafio_id = ? and list_contains(?, dd.confianca) and list_contains(?, d.tipo_doc)
                     {filtro_un} order by dd.sim desc limit 300""",
                 (dd.desafio_id.iloc[0], list(conf), list(tipos)) + ((unidade,) if unidade else ()))
        st.caption("Inclui documentos em que este é o 2º ou 3º desafio mais aderente (coluna *posição*).")
    else:
        docs = sub.sort_values("sim", ascending=False).head(300).rename(columns={"tipo_doc": "tipo"}).assign(rank=1)
    docs["unidade"] = docs.unidade_id.map(dados.rotulo_unidade)
    docs["tipo"] = docs.tipo.map({"projeto": "Projeto", "publicacao": "Publicação", "tecnologia": "Tecnologia"})
    docs["confianca"] = docs.confianca.map(CONF)
    cols = ["doc_uid", "titulo", "tipo", "ano", "unidade", "confianca", "sim"] + (["rank"] if nivel == "desafio" else [])
    ui.tabela_navegavel(docs[cols], "doc", "doc_uid", f"prog_docs_{nivel}", altura=420,
                        colunas={"titulo": "Título", "tipo": "Tipo", "ano": "Ano", "unidade": "Unidade",
                                 "confianca": "Confiança", "rank": "Posição",
                                 "sim": st.column_config.ProgressColumn("Aderência", min_value=0, max_value=0.5,
                                                                        format="%.2f")})
with t_uns:
    u = q_interno("select doc_uid, unidade_id from doc_unidade_prog where list_contains(?, doc_uid)",
          (sub.doc_uid.tolist(),))
    u = u.groupby("unidade_id").doc_uid.nunique().sort_values(ascending=False).reset_index(name="documentos")
    u["unidade"] = u.unidade_id.map(dados.rotulo_unidade)
    ui.tabela_navegavel(u[["unidade_id", "unidade", "documentos"]], "unidade", "unidade_id", f"prog_un_{nivel}",
                        altura=380, colunas={"unidade": "Unidade", "documentos": "Documentos"})
with t_des:
    d2 = sub.groupby(["desafio_id", "desafio", "portfolio"]).size().reset_index(name="documentos") \
        .sort_values("documentos", ascending=False)
    st.dataframe(d2, hide_index=True, width="stretch",
                 column_config={"desafio_id": "Id", "desafio": "Desafio", "portfolio": "Portfólio",
                                "documentos": "Documentos"})
