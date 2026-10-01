import pandas as pd
import plotly.express as px
import streamlit as st

from lib import dados, ui
from lib.dados import q

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
if "doc_desafio" not in set(q("select table_name from duckdb_tables()").table_name):
    st.info("A camada de programação ainda não foi gerada neste banco.")
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
        "pela programação, não uma classificação independente dos ODS.")


@st.cache_data(show_spinner=False)
def desafios() -> pd.DataFrame:
    d = q("select * from desafio")
    d["ods_rotulo"] = d.ods_num.map(lambda n: f"ODS {int(n)} · {ODS.get(int(n), '')}" if pd.notna(n) else "Sem ODS")
    d["meta_rotulo"] = d.meta_id + " · " + d.meta.str.slice(0, 90) + d.meta.str.len().gt(90).map({True: "…", False: ""})
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


# Dados -----------------------------------------------------------------------------
# todos: um documento por linha (desafio mais aderente); part: participação documento × unidade
todos = q("""select dd.doc_uid, dd.desafio_id, dd.sim, dd.confianca, d.tipo_doc, d.ano, d.titulo, d.unidade_id
             from doc_desafio dd join documento d using (doc_uid)
             where dd.rank = 1 and list_contains(?, dd.confianca) and list_contains(?, d.tipo_doc)""",
          (list(conf), list(tipos))).merge(des, on="desafio_id", how="left")
part = q("""select distinct du.doc_uid, du.unidade_id
            from doc_desafio dd join documento d using (doc_uid) join documento_unidade du using (doc_uid)
            where dd.rank = 1 and list_contains(?, dd.confianca) and list_contains(?, d.tipo_doc)""",
         (list(conf), list(tipos))).merge(todos[["doc_uid"] + list(COL.values())], on="doc_uid")
base = todos[todos.doc_uid.isin(part[part.unidade_id == unidade].doc_uid)] if unidade else todos
if base.empty:
    st.info("Nenhum documento com esses filtros.")
    st.stop()
nome_un = dados.rotulo_unidade(unidade) if unidade else None
col = COL[nivel]

cont = base.tipo_doc.value_counts()
ui.kpis([("Projetos", int(cont.get("projeto", 0))), ("Publicações", int(cont.get("publicacao", 0))),
         ("Tecnologias", int(cont.get("tecnologia", 0))),
         (f"{NIVEIS[nivel]}s com produção" if nivel != "ods" else "ODS com produção", base[col].nunique())])
if unidade:
    st.caption(f"Números da unidade **{nome_un}** (documentos com participação dela).")

t_perfil, t_matriz, t_estr = st.tabs([
    "Perfil da unidade" if unidade else "Distribuição", "Unidades × " + NIVEIS[nivel].lower() + "s"
    if nivel in ("portfolio", "objetivo", "ods") else "Unidades × portfólios", "Estrutura da programação"])

with t_perfil:
    if unidade:
        # posição da unidade: % da produção dela em cada categoria × % da Embrapa
        pu = base[col].value_counts(normalize=True).mul(100).rename(nome_un)
        pe = todos[col].value_counts(normalize=True).mul(100).rename("Embrapa (todas as unidades)")
        g = pd.concat([pu, pe], axis=1).fillna(0)
        g = g[g.max(axis=1) > 0].sort_values(nome_un, ascending=False)
        gl = g.reset_index(names=col).melt(id_vars=col, var_name="quem", value_name="pct")
        fig = px.bar(gl, x="pct", y=col, color="quem", orientation="h", barmode="group",
                     color_discrete_map={nome_un: "#2E7D32", "Embrapa (todas as unidades)": "#B0BEC5"},
                     category_orders={col: g.index.tolist()}, height=max(360, 34 * len(g) + 120),
                     labels={"pct": "% dos documentos", col: "", "quem": ""})
        fig.update_layout(legend=dict(orientation="h", y=1.02, yanchor="bottom", x=0), margin=dict(l=0, r=10, t=30))
        st.plotly_chart(fig, width="stretch")
        st.caption(f"Verde: como a produção da **{nome_un}** se distribui entre as categorias. Cinza: a mesma "
                   "distribuição para a Embrapa inteira. Barra verde maior que a cinza = a unidade se concentra "
                   "mais naquela categoria do que a média.")
    else:
        g = base.groupby([col, "tipo_doc"]).size().reset_index(name="n")
        ordem = g.groupby(col).n.sum().sort_values(ascending=False).index.tolist()
        g["tipo"] = g.tipo_doc.map(dados.TIPOS)
        fig = px.bar(g, x="n", y=col, color="tipo", orientation="h",
                     color_discrete_map={dados.TIPOS[k]: v for k, v in dados.CORES_TIPO.items()},
                     category_orders={col: ordem}, height=max(320, 26 * len(ordem) + 120),
                     labels={"n": "Documentos", col: "", "tipo": ""})
        fig.update_layout(legend=dict(orientation="h", y=1.02, yanchor="bottom", x=0), margin=dict(l=0, r=10, t=30))
        st.plotly_chart(fig, width="stretch")
        st.caption("Documentos da Embrapa em cada categoria, pelo desafio mais aderente de cada documento.")

with t_matriz:
    colm = col if nivel in ("portfolio", "objetivo", "ods") else "portfolio"
    medida = st.radio("Mostrar", ["pct", "n"], horizontal=True, key="prog_matriz_medida",
                      format_func={"pct": "% da produção da unidade", "n": "Nº de documentos"}.get)
    m = part.groupby(["unidade_id", colm]).doc_uid.nunique().unstack(fill_value=0)
    m = m[m.sum(axis=1) >= 10]
    valores = (100 * m.div(m.sum(axis=1), axis=0)).round(0) if medida == "pct" else m
    rot = {u: dados.rotulo_unidade(u) for u in valores.index}
    if unidade in rot:
        rot[unidade] = "▶ " + rot[unidade]
    valores.index = valores.index.map(rot)
    valores = valores.loc[sorted(valores.index, key=lambda s: (not s.startswith("▶"), s))]
    fig = px.imshow(valores, color_continuous_scale="Greens", aspect="auto", text_auto=".0f",
                    labels={"x": "", "y": "", "color": "%" if medida == "pct" else "Docs"},
                    height=max(400, 22 * len(valores) + 160))
    fig.update_xaxes(side="top", tickangle=-30)
    fig.update_layout(margin=dict(t=10, l=0, r=0, b=0))
    st.plotly_chart(fig, width="stretch")
    st.caption(("Cada linha é uma unidade e **soma 100%**: em que categorias ela concentra a sua produção desde 2024. "
                if medida == "pct" else "Número de documentos de cada unidade em cada categoria. ")
               + "Conta **documentos** (projetos, publicações e tecnologias), não desafios; um documento com várias "
                 "unidades conta para cada uma. Unidades com ao menos 10 documentos"
               + (f"; a unidade escolhida aparece primeiro (▶)." if unidade else "."))

with t_estr:
    e = des.groupby(["objetivo", "portfolio"]).desafio_id.nunique().reset_index(name="desafios")
    nd = base.groupby(["objetivo", "portfolio"]).doc_uid.nunique().reset_index(name="documentos")
    e = e.merge(nd, on=["objetivo", "portfolio"], how="left").fillna({"documentos": 0})
    e["documentos"] = e.documentos.astype(int)
    st.dataframe(e.sort_values(["objetivo", "documentos"], ascending=[True, False]), hide_index=True, width="stretch",
                 height=min(38 * len(e) + 40, 700),
                 column_config={"objetivo": "Objetivo estratégico", "portfolio": "Portfólio",
                                "desafios": "Desafios",
                                "documentos": st.column_config.ProgressColumn(
                                    "Documentos" + (f" da {nome_un}" if unidade else ""), format="%d",
                                    min_value=0, max_value=int(e.documentos.max()) or 1)})
    st.caption("Como a programação se organiza: cada combinação de objetivo estratégico e portfólio, com o número de "
               "desafios e de documentos aderentes.")

# Detalhe ---------------------------------------------------------------------------
st.divider()
opcoes = todos[col].value_counts().index.tolist()
item = st.selectbox(f"Detalhar {NIVEIS[nivel].lower()}", opcoes, index=None, key=f"prog_item_{nivel}",
                    placeholder="Escolha um item para ver todas as unidades e os documentos")
if not item:
    st.stop()
dd = des[des[col] == item]
if nivel == "desafio":
    r = dd.iloc[0]
    st.markdown(f"**{r.desafio_id}** — {r.desafio}")
    st.markdown(f"Portfólio: **{r.portfolio}** · Objetivo: **{r.objetivo}** · ODS: **{r.ods_rotulo}**  \n"
                f"Meta: {r.meta_rotulo}")
else:
    st.markdown(f"**{item}** — {dd.desafio_id.nunique()} desafios · "
                f"{todos[todos[col] == item].doc_uid.nunique():,} documentos de todas as unidades".replace(",", "."))

t_uns, t_docs, t_des = st.tabs(["Unidades neste " + NIVEIS[nivel].lower(),
                                "Documentos" + (f" da {nome_un}" if unidade else ""),
                                "Desafios" + (f" da {nome_un}" if unidade else "")])
with t_uns:
    # todas as unidades com produção no item (não depende do filtro de unidade)
    no_item = part[part[col] == item].groupby("unidade_id").doc_uid.nunique().rename("documentos")
    total_un = part.groupby("unidade_id").doc_uid.nunique()
    peso_embrapa = (todos[col] == item).mean()
    u = no_item.reset_index()
    u["pct_unidade"] = 100 * u.documentos / u.unidade_id.map(total_un)
    u["especializacao"] = (u.pct_unidade / 100) / peso_embrapa if peso_embrapa else 0
    u["unidade"] = u.unidade_id.map(dados.rotulo_unidade)
    u = u.sort_values("documentos", ascending=False)
    u["destaque"] = u.unidade_id.eq(unidade).map({True: "Unidade escolhida", False: "Outras unidades"})
    top = u.head(25)
    if unidade and unidade not in set(top.unidade_id):          # a unidade escolhida aparece sempre
        top = pd.concat([top, u[u.unidade_id == unidade]])
    fig = px.bar(top, x="documentos", y="unidade", orientation="h", color="destaque",
                 color_discrete_map={"Unidade escolhida": "#C62828", "Outras unidades": "#2E7D32"},
                 category_orders={"unidade": top.unidade.tolist()}, height=max(320, 24 * len(top) + 100),
                 hover_data={"pct_unidade": ":.0f", "especializacao": ":.2f", "destaque": False},
                 labels={"documentos": "Documentos", "unidade": "", "pct_unidade": "% da produção da unidade",
                         "especializacao": "Especialização"})
    fig.update_layout(showlegend=bool(unidade), legend=dict(orientation="h", y=1.02, yanchor="bottom", x=0, title=""),
                      margin=dict(l=0, r=10, t=30))
    st.plotly_chart(fig, width="stretch")
    if unidade and unidade in set(u.unidade_id):
        p = u.reset_index(drop=True)
        pos = int(p.index[p.unidade_id == unidade][0]) + 1
        st.caption(f"**{nome_un}**: {pos}ª de {len(u)} unidades em número de documentos neste "
                   f"{NIVEIS[nivel].lower()}.")
    st.caption("Todas as unidades com documentos aderentes a este item (independe do filtro de unidade). "
               "**% da produção da unidade**: quanto da produção dela está neste item. **Especialização**: esse "
               "percentual dividido pelo da Embrapa (acima de 1 = a unidade se dedica mais a este item que a média).")
    ui.tabela_navegavel(u[["unidade_id", "unidade", "documentos", "pct_unidade", "especializacao"]], "unidade",
                        "unidade_id", f"prog_un_{nivel}", altura=320,
                        colunas={"unidade": "Unidade", "documentos": "Documentos",
                                 "pct_unidade": st.column_config.NumberColumn("% da produção da unidade", format="%.0f%%"),
                                 "especializacao": st.column_config.NumberColumn("Especialização", format="%.2f")})
with t_docs:
    if nivel == "desafio":
        # para um desafio, entram também documentos em que ele é o 2º ou 3º mais aderente
        join_un = "join documento_unidade du using (doc_uid)" if unidade else ""
        filtro_un = "and du.unidade_id = ?" if unidade else ""
        docs = q(f"""select distinct dd.doc_uid, dd.rank, dd.sim, dd.confianca, d.tipo_doc tipo, d.ano, d.titulo,
                            d.unidade_id
                     from doc_desafio dd join documento d using (doc_uid) {join_un}
                     where dd.desafio_id = ? and list_contains(?, dd.confianca) and list_contains(?, d.tipo_doc)
                     {filtro_un} order by dd.sim desc limit 300""",
                 (dd.desafio_id.iloc[0], list(conf), list(tipos)) + ((unidade,) if unidade else ()))
        st.caption("Inclui documentos em que este é o 2º ou 3º desafio mais aderente (coluna *posição*).")
    else:
        docs = base[base[col] == item].sort_values("sim", ascending=False).head(300) \
            .rename(columns={"tipo_doc": "tipo"}).assign(rank=1)
    if unidade:
        st.caption(f"Só documentos com participação da **{nome_un}**. Para ver os de todas as unidades, limpe o "
                   "filtro de unidade.")
    docs["unidade"] = docs.unidade_id.map(dados.rotulo_unidade)
    docs["tipo"] = docs.tipo.map({"projeto": "Projeto", "publicacao": "Publicação", "tecnologia": "Tecnologia"})
    docs["confianca"] = docs.confianca.map(CONF)
    cols = ["doc_uid", "titulo", "tipo", "ano", "unidade", "confianca", "sim"] + (["rank"] if nivel == "desafio" else [])
    ui.tabela_navegavel(docs[cols], "doc", "doc_uid", f"prog_docs_{nivel}", altura=420,
                        colunas={"titulo": "Título", "tipo": "Tipo", "ano": "Ano", "unidade": "Unidade responsável",
                                 "confianca": "Confiança", "rank": "Posição",
                                 "sim": st.column_config.ProgressColumn("Aderência", min_value=0, max_value=0.5,
                                                                        format="%.2f")})
with t_des:
    sub = base[base[col] == item]
    d2 = sub.groupby(["desafio_id", "desafio", "portfolio"]).size().reset_index(name="documentos") \
        .sort_values("documentos", ascending=False)
    st.dataframe(d2, hide_index=True, width="stretch",
                 column_config={"desafio_id": "Id", "desafio": "Desafio", "portfolio": "Portfólio",
                                "documentos": "Documentos"})
