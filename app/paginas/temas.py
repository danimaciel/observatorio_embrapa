import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

from lib import dados, ui
from lib.dados import q
from lib.palavras import explorador_palavras

a0, a1 = dados.periodo()
st.title("Temas")

if not dados.tem_semantica():
    ui.aviso_tema_provisorio()
    explorador_palavras(a0, a1)
    st.stop()

tm = dados.temas()
tema_lista = tm[tm.nivel == 2].sort_values("n_total", ascending=False)
macro_lista = tm[tm.nivel == 1].sort_values("n_total", ascending=False)
st.caption(f"{len(tema_lista)} temas agrupados em {len(macro_lista)} macrotemas, identificados automaticamente "
           "(BERTopic) a partir do conteúdo de projetos, publicações e tecnologias num espaço semântico comum. "
           f"Período: {a0}–{a1}.")


@st.cache_data(show_spinner=False)
def base_temas(a0: int, a1: int) -> pd.DataFrame:
    return q("""select t.doc_uid, t.tema_id, t.macro_id, t.score, d.tipo_doc, d.ano
                from doc_tema t join documento d using (doc_uid) where d.ano between ? and ?""", (a0, a1))


base = base_temas(a0, a1)
c1, c2 = st.columns(2)
with c1:
    macro = st.selectbox("Macrotema", macro_lista.tema_id.tolist(), index=None,
                         format_func=lambda m: f"{dados.rotulo_tema(m)} ({tm.set_index('tema_id').n_total[m]:,})"
                         .replace(",", "."), placeholder="Todos os macrotemas")
with c2:
    opcoes = tema_lista[tema_lista.pai_id == macro].tema_id.tolist() if macro else tema_lista.tema_id.tolist()
    sel = ui.seletor_url("Tema", opcoes, "tema", "tema_sel",
                         format_func=lambda t: f"{dados.rotulo_tema(t)} ({tm.set_index('tema_id').n_total[t]:,})"
                         .replace(",", "."), placeholder="Escolha um tema para ver o detalhe")

# Detalhe de um tema ------------------------------------------------------------------
if sel:
    info = tm.set_index("tema_id").loc[sel]
    st.subheader(info.rotulo)
    st.caption(f"Macrotema: **{dados.rotulo_tema(info.pai_id)}** · termos característicos: {info.termos}")
    sub = base[base.tema_id == sel]
    cont = sub.tipo_doc.value_counts()
    ui.kpis([("Projetos", int(cont.get("projeto", 0))), ("Publicações", int(cont.get("publicacao", 0))),
             ("Tecnologias", int(cont.get("tecnologia", 0))),
             ("Participação na Embrapa", f"{100 * len(sub) / max(len(base), 1):.2f}%")])
    t_evo, t_un, t_pes, t_docs = st.tabs(["Evolução", "Unidades", "Pesquisadores", "Documentos"])
    with t_evo:
        s = sub.groupby(["ano", "tipo_doc"]).size().reset_index(name="n")
        s["tipo"] = s.tipo_doc.map(dados.TIPOS)
        st.plotly_chart(px.bar(s, x="ano", y="n", color="tipo",
                               color_discrete_map={dados.TIPOS[k]: v for k, v in dados.CORES_TIPO.items()},
                               labels={"ano": "Ano", "n": "Documentos", "tipo": ""}), width="stretch")
        part = (base.groupby("ano").tema_id.apply(lambda x: (x == sel).mean() * 1000)).reset_index(name="p")
        st.plotly_chart(px.line(part, x="ano", y="p", markers=True,
                                labels={"ano": "Ano", "p": "‰ dos documentos do ano"}), width="stretch")
    docs = sub.doc_uid.tolist()
    with t_un:
        u = q("""select unidade_id, count(distinct doc_uid) documentos from documento_unidade
                 where list_contains(?, doc_uid) group by 1 order by 2 desc""", (docs,))
        tot_un = q("""select du.unidade_id, count(distinct du.doc_uid) total from documento_unidade du
                      join documento d using (doc_uid) where d.ano between ? and ? group by 1""", (a0, a1))
        u = u.merge(tot_un, on="unidade_id")
        u["especializacao"] = (u.documentos / u.total) / (len(sub) / max(len(base), 1))
        u["unidade"] = u.unidade_id.map(dados.rotulo_unidade)
        ui.tabela_navegavel(u[["unidade_id", "unidade", "documentos", "especializacao"]], "unidade", "unidade_id",
                            "tema_un", altura=420,
                            colunas={"especializacao": st.column_config.NumberColumn(
                                "Especialização", format="%.1f",
                                help="Peso do tema na unidade ÷ peso do tema na Embrapa (> 1 = mais que a média)")})
    with t_pes:
        p = q("""select p.pessoa_id, p.nome_exibicao nome, p.unidade_ref_id, count(distinct dp.doc_uid) documentos
                 from documento_pessoa dp join pessoa p using (pessoa_id)
                 where list_contains(?, dp.doc_uid) group by all order by documentos desc limit 100""", (docs,))
        p["unidade"] = p.unidade_ref_id.map(dados.rotulo_unidade)
        ui.tabela_navegavel(p[["pessoa_id", "nome", "unidade", "documentos"]], "pessoa", "pessoa_id",
                            "tema_pes", altura=420)
    with t_docs:
        st.caption("Ordenados pelos mais representativos do tema (mais próximos do seu centro).")
        dl = q("""select d.doc_uid, d.tipo_doc tipo, d.ano, d.titulo from doc_tema t join documento d using (doc_uid)
                  where t.tema_id = ? and d.ano between ? and ? order by t.score desc limit 300""", (sel, a0, a1))
        dl["tipo"] = dl.tipo.map({"projeto": "Projeto", "publicacao": "Publicação", "tecnologia": "Tecnologia"})
        ui.tabela_navegavel(dl, "doc", "doc_uid", "tema_docs", altura=420)
    st.divider()

# Visão geral --------------------------------------------------------------------------
t_mapa, t_cres, t_lac, t_kw = st.tabs(["Mapa de temas", "Crescimento e declínio",
                                        "Lacunas projeto × publicação × tecnologia", "Palavras-chave"])
por_tema = base.groupby(["macro_id", "tema_id"]).size().reset_index(name="n")
por_tema["macro"] = por_tema.macro_id.map(dados.rotulo_tema)
por_tema["tema"] = por_tema.tema_id.map(dados.rotulo_tema)
if macro:
    por_tema = por_tema[por_tema.macro_id == macro]

with t_mapa:
    fig = px.treemap(por_tema, path=["macro", "tema"], values="n", color="macro")
    fig.update_traces(hovertemplate="%{label}<br>%{value} documentos<extra></extra>")
    fig.update_layout(height=620, margin=dict(t=10, l=0, r=0, b=0), showlegend=False)
    st.plotly_chart(fig, width="stretch")
    st.caption("Área = número de documentos no período. Escolha um tema no seletor acima para ver o detalhe.")
    tab = por_tema.sort_values("n", ascending=False)[["tema_id", "tema", "macro", "n"]]
    ui.tabela_navegavel(tab, "tema", "tema_id", "tema_lista", altura=380,
                        colunas={"tema": "Tema", "macro": "Macrotema", "n": "Documentos"})

with t_cres:
    meio = (a0 + a1) // 2
    b = base if not macro else base[base.macro_id == macro]
    tot = base.assign(f=np.where(base.ano <= meio, "antes", "depois")).groupby("f").size()
    x = b.assign(f=np.where(b.ano <= meio, "antes", "depois")).groupby(["tema_id", "f"]).size().unstack(fill_value=0)
    if {"antes", "depois"} <= set(x.columns):
        x = x[x.sum(axis=1) >= 30]
        x["p_antes"] = 1000 * x.antes / tot["antes"]
        x["p_depois"] = 1000 * x.depois / tot["depois"]
        x["variacao"] = np.log2((x.p_depois + 0.1) / (x.p_antes + 0.1))
        x = x.reset_index()
        x["tema"] = x.tema_id.map(dados.rotulo_tema)
        st.caption(f"Participação de cada tema (‰ dos documentos): {a0}–{meio} vs. {meio + 1}–{a1}. "
                   "log₂ variação: +1 = dobrou; −1 = caiu à metade.")
        cfg = {"p_antes": st.column_config.NumberColumn("‰ antes", format="%.1f"),
               "p_depois": st.column_config.NumberColumn("‰ depois", format="%.1f"),
               "variacao": st.column_config.NumberColumn("log₂ variação", format="%.2f"), "tema": "Tema"}
        cc1, cc2 = st.columns(2)
        with cc1:
            st.markdown("**Em crescimento**")
            ui.tabela_navegavel(x.nlargest(20, "variacao")[["tema_id", "tema", "p_antes", "p_depois", "variacao"]],
                                "tema", "tema_id", "tema_cresc", colunas=cfg)
        with cc2:
            st.markdown("**Em declínio**")
            ui.tabela_navegavel(x.nsmallest(20, "variacao")[["tema_id", "tema", "p_antes", "p_depois", "variacao"]],
                                "tema", "tema_id", "tema_decl", colunas=cfg)
    else:
        st.caption("Período curto demais para comparar.")

with t_lac:
    st.caption("Peso de cada tema entre projetos, publicações e tecnologias. Temas com peso muito maior nos "
               "projetos que nas publicações podem indicar resultados ainda não publicados — ou pesquisa recente.")
    b = base if not macro else base[base.macro_id == macro]
    tot = base.groupby("tipo_doc").size()
    m = b.groupby(["tema_id", "tipo_doc"]).size().unstack(fill_value=0)
    for t in dados.TIPOS:
        if t not in m:
            m[t] = 0
        m[f"p_{t}"] = 1000 * m[t] / max(tot.get(t, 1), 1)
    m["lacuna"] = np.log2((m.p_projeto + 0.1) / (m.p_publicacao + 0.1))
    m = m.reset_index()
    m["tema"] = m.tema_id.map(dados.rotulo_tema)
    fig = px.scatter(m, x="p_publicacao", y="p_projeto", size="publicacao", hover_name="tema",
                     color="lacuna", color_continuous_scale="RdBu_r", color_continuous_midpoint=0,
                     log_x=True, log_y=True,
                     labels={"p_publicacao": "‰ das publicações", "p_projeto": "‰ dos projetos",
                             "lacuna": "log₂ proj/pub"})
    st.plotly_chart(fig, width="stretch")
    st.markdown("**Mais presentes em projetos do que em publicações**")
    ui.tabela_navegavel(
        m[m.projeto >= 5].nlargest(25, "lacuna")[["tema_id", "tema", "projeto", "publicacao", "tecnologia",
                                                  "p_projeto", "p_publicacao", "lacuna"]],
        "tema", "tema_id", "tema_lac",
        colunas={"tema": "Tema", "projeto": "Projetos", "publicacao": "Publicações", "tecnologia": "Tecnologias",
                 "p_projeto": st.column_config.NumberColumn("‰ projetos", format="%.1f"),
                 "p_publicacao": st.column_config.NumberColumn("‰ publicações", format="%.1f"),
                 "lacuna": st.column_config.NumberColumn("log₂ proj/pub", format="%.2f")})

with t_kw:
    st.caption("Explorador das palavras-chave declaradas pelos autores — complementa os temas automáticos.")
    explorador_palavras(a0, a1)

ui.aviso_tema_provisorio()
