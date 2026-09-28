"""Explorador de palavras-chave declaradas (complemento aos temas do BERTopic)."""

import numpy as np
import plotly.express as px
import streamlit as st

from lib import dados, ui
from lib.dados import q


@st.cache_data(show_spinner=False)
def base_kw(a0: int, a1: int):
    return q("""
        select k.keyword_norm, lower(any_value(k.keyword_raw)) palavra, d.tipo_doc, d.ano, k.doc_uid
        from documento_keyword k join documento d using (doc_uid)
        where d.ano between ? and ? group by k.keyword_norm, d.tipo_doc, d.ano, k.doc_uid
    """, (a0, a1))




def explorador_palavras(a0: int, a1: int) -> None:
    kw = base_kw(a0, a1)
    rotulo = kw.groupby("keyword_norm").palavra.agg(lambda s: s.mode().iat[0])
    freq = kw.groupby("keyword_norm").doc_uid.nunique().sort_values(ascending=False)

    t_exp, t_cres, t_lac = st.tabs(["Explorar palavra-chave", "Crescimento e declínio", "Lacunas projeto × publicação × tecnologia"])

    with t_exp:
        opcoes = freq.head(3000).index.tolist()
        sel = st.selectbox("Palavra-chave", opcoes, index=None, format_func=lambda k: f"{rotulo[k]} ({freq[k]})",
                           placeholder="Digite uma palavra-chave…")
        if sel:
            sub = kw[kw.keyword_norm == sel]
            s = sub.groupby(["ano", "tipo_doc"]).doc_uid.nunique().reset_index(name="n")
            s["tipo"] = s.tipo_doc.map(dados.TIPOS)
            st.plotly_chart(px.bar(s, x="ano", y="n", color="tipo",
                                   color_discrete_map={dados.TIPOS[k]: v for k, v in dados.CORES_TIPO.items()},
                                   labels={"ano": "Ano", "n": "Documentos", "tipo": ""}), width="stretch")
            docs = sub.doc_uid.unique().tolist()
            c1, c2 = st.columns(2)
            with c1:
                st.markdown("**Unidades**")
                u = q("""select unidade_id, count(distinct doc_uid) documentos from documento_unidade
                         where list_contains(?, doc_uid) group by 1 order by 2 desc""", (docs,))
                u["unidade"] = u.unidade_id.map(dados.rotulo_unidade)
                ui.tabela_navegavel(u[["unidade_id", "unidade", "documentos"]], "unidade", "unidade_id", "kw_un",
                                    altura=350)
            with c2:
                st.markdown("**Pesquisadores**")
                p = q("""select p.pessoa_id, p.nome_exibicao nome, count(distinct dp.doc_uid) documentos
                         from documento_pessoa dp join pessoa p using (pessoa_id)
                         where list_contains(?, dp.doc_uid) group by all order by 3 desc limit 100""", (docs,))
                ui.tabela_navegavel(p, "pessoa", "pessoa_id", "kw_pes", altura=350)
            st.markdown("**Documentos**")
            dl = q("select doc_uid, tipo_doc tipo, ano, titulo from documento where list_contains(?, doc_uid) "
                   "order by ano desc", (docs,))
            ui.tabela_navegavel(dl, "doc", "doc_uid", "kw_docs", altura=400)

    with t_cres:
        meio = (a0 + a1) // 2
        st.caption(f"Participação de cada tema no total de documentos: {a0}–{meio} vs. {meio + 1}–{a1}. "
                   "Temas com pelo menos 15 documentos.")
        tot = kw.assign(fase=np.where(kw.ano <= meio, "antes", "depois")).groupby("fase").doc_uid.nunique()
        x = (kw.assign(fase=np.where(kw.ano <= meio, "antes", "depois"))
             .groupby(["keyword_norm", "fase"]).doc_uid.nunique().unstack(fill_value=0))
        x = x[x.sum(axis=1) >= 15]
        if {"antes", "depois"} <= set(x.columns) and not x.empty:
            x["part_antes"] = 1000 * x.antes / tot["antes"]
            x["part_depois"] = 1000 * x.depois / tot["depois"]
            x["variacao"] = np.log2((x.part_depois + 0.5) / (x.part_antes + 0.5))
            x["tema"] = rotulo.reindex(x.index)
            c1, c2 = st.columns(2)
            cfg = {"part_antes": st.column_config.NumberColumn("‰ antes", format="%.1f"),
                   "part_depois": st.column_config.NumberColumn("‰ depois", format="%.1f"),
                   "variacao": st.column_config.NumberColumn("log₂ variação", format="%.2f")}
            c1.markdown("**Em crescimento**")
            c1.dataframe(x.nlargest(20, "variacao")[["tema", "part_antes", "part_depois", "variacao"]],
                         hide_index=True, column_config=cfg, width="stretch")
            c2.markdown("**Em declínio**")
            c2.dataframe(x.nsmallest(20, "variacao")[["tema", "part_antes", "part_depois", "variacao"]],
                         hide_index=True, column_config=cfg, width="stretch")
        else:
            st.caption("Período curto demais para comparar.")

    with t_lac:
        st.caption("Participação de cada tema entre projetos, publicações e tecnologias. Temas muito presentes em "
                   "projetos e pouco em publicações (ou tecnologias) indicam possíveis lacunas de resultado — ou "
                   "defasagem temporal. Temas com pelo menos 10 documentos.")
        tot = kw.groupby("tipo_doc").doc_uid.nunique()
        m = kw.groupby(["keyword_norm", "tipo_doc"]).doc_uid.nunique().unstack(fill_value=0)
        m = m[m.sum(axis=1) >= 10]
        for t in dados.TIPOS:
            if t not in m:
                m[t] = 0
            m[f"p_{t}"] = 1000 * m[t] / max(tot.get(t, 1), 1)
        m["lacuna_pub"] = np.log2((m.p_projeto + 0.5) / (m.p_publicacao + 0.5))
        m["tema"] = rotulo.reindex(m.index)
        fig = px.scatter(m.reset_index(), x="p_publicacao", y="p_projeto", size="publicacao", hover_name="tema",
                         color="lacuna_pub", color_continuous_scale="RdBu_r", color_continuous_midpoint=0,
                         log_x=True, log_y=True,
                         labels={"p_publicacao": "‰ das publicações", "p_projeto": "‰ dos projetos",
                                 "lacuna_pub": "log₂ proj/pub"})
        st.plotly_chart(fig, width="stretch")
        cfg = {"p_projeto": st.column_config.NumberColumn("‰ projetos", format="%.1f"),
               "p_publicacao": st.column_config.NumberColumn("‰ publicações", format="%.1f"),
               "p_tecnologia": st.column_config.NumberColumn("‰ tecnologias", format="%.1f"),
               "lacuna_pub": st.column_config.NumberColumn("log₂ proj/pub", format="%.2f")}
        st.markdown("**Mais presentes em projetos do que em publicações**")
        st.dataframe(m.nlargest(25, "lacuna_pub")[["tema", "projeto", "publicacao", "tecnologia", "p_projeto",
                                                  "p_publicacao", "p_tecnologia", "lacuna_pub"]],
                     hide_index=True, column_config=cfg, width="stretch")
        if dados.meta().get("arquivos_truncados"):
            st.warning("Com a base de publicações incompleta (quase só até 2009), as lacunas estão fortemente "
                       "distorcidas para temas recentes.", icon=":material/warning:")
