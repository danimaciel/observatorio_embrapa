import plotly.express as px
import streamlit as st

from lib import dados, ui
from lib.dados import q

a0, a1 = dados.periodo()
un = dados.unidades().query("n_docs > 0")
ids = un.unidade_id.tolist()

st.title("Unidades")
sel = ui.seletor_url("Unidade", ids, "unidade", "un_sel", format_func=dados.nome_unidade,
                     placeholder="Escolha uma unidade")
if sel is None:
    st.info("Escolha uma unidade para ver seu perfil, colaborações e temas.")
    st.stop()
info = un.set_index("unidade_id").loc[sel]
st.caption(f"{info.nome_atual} · sigla histórica {info.sigla_historica} · {info.uf} · {a0}–{a1}")

# Documentos com participação da unidade (qualquer papel)
docs = q("""
    select distinct d.doc_uid, d.tipo_doc, d.titulo, d.ano, d.categoria, du.papel
    from documento_unidade du join documento d using (doc_uid)
    where du.unidade_id = ? and d.ano between ? and ?
""", (sel, a0, a1))
por_doc = docs.groupby(["doc_uid", "tipo_doc", "titulo", "ano", "categoria"], as_index=False)["papel"] \
    .agg(lambda p: ", ".join(sorted(set(p))))
if por_doc.empty:
    st.info("Sem documentos desta unidade no período escolhido.")
    st.stop()
cont = por_doc.tipo_doc.value_counts()
pesq = q("""
    select count(distinct p.pessoa_id) n from pessoa p join documento_pessoa dp using (pessoa_id)
    join documento d using (doc_uid) where p.unidade_ref_id = ? and d.ano between ? and ?
""", (sel, a0, a1)).n[0]
camadas_todas = tuple(dados.CAMADAS)
rede = dados.rede_unidades(a0, a1, camadas_todas)
parc = rede[(rede.unidade1 == sel) | (rede.unidade2 == sel)]

ui.kpis([
    ("Projetos liderados", int(cont.get("projeto", 0))),
    ("Publicações (obras)", int(cont.get("publicacao", 0))),
    ("Tecnologias", int(cont.get("tecnologia", 0))),
    ("Pesquisadores com produção", int(pesq)),
    ("Unidades parceiras", len(parc)),
])

t_col, t_evo, t_pes, t_tema, t_prod = st.tabs(
    ["Colaboração", "Evolução", "Pesquisadores", "Temas", "Produção"])

with t_col:
    st.markdown("#### Com quais unidades mais se relaciona — e em torno de quais temas")
    c1, c2 = st.columns([2, 1])
    camadas = c1.pills("Tipo de relação", list(dados.CAMADAS), selection_mode="multi", default=list(dados.CAMADAS),
                       format_func=dados.CAMADAS.get, key="un_camadas", help=dados.CAMADAS_AJUDA)
    metrica = c2.radio("Ordenar por", ["peso", "forca", "n_docs"], horizontal=True,
                       format_func={"peso": "Intensidade", "forca": "Força de associação",
                                    "n_docs": "Nº de documentos"}.get)
    r = dados.rede_unidades(a0, a1, tuple(camadas))
    r = r[(r.unidade1 == sel) | (r.unidade2 == sel)].copy()
    if r.empty:
        st.caption("Sem colaborações observadas no período e nas camadas escolhidas.")
    else:
        r["parceira_id"] = r.unidade1.where(r.unidade1 != sel, r.unidade2)
        r["parceira"] = r.parceira_id.map(dados.rotulo_unidade)
        r = r.sort_values(metrica, ascending=False)
        top = r.head(15)
        fig = px.bar(top[::-1], x=metrica, y="parceira", orientation="h", hover_data=["n_docs", "peso", "forca"],
                     labels={"peso": "Intensidade (contagem fracionária)", "forca": "Força de associação",
                             "n_docs": "Documentos", "parceira": ""})
        st.plotly_chart(fig, width="stretch")
        with st.expander("O que são intensidade e força de associação?"):
            st.markdown(dados.METRICAS_AJUDA)

        parceira = st.selectbox("Temas da colaboração com", r.parceira_id.tolist(),
                                format_func=dados.nome_unidade)
        dd = dados.docs_da_relacao(sel, parceira, a0, a1, tuple(camadas))
        ca, cb = st.columns(2)
        with ca:
            if dados.tem_semantica():
                tt = dados.temas_de_docs(tuple(dd), 12)
                if not tt.empty:
                    st.markdown("**Temas dos documentos em comum**")
                    st.plotly_chart(px.bar(tt.sort_values("n"), x="n", y="rotulo", orientation="h",
                                           labels={"n": "Documentos em comum", "rotulo": ""}), width="stretch")
            else:
                kw = dados.palavras_chave(tuple(dd), 15)
                if not kw.empty:
                    st.plotly_chart(px.bar(kw.sort_values("n"), x="n", y="palavra", orientation="h",
                                           labels={"n": "Documentos em comum", "palavra": ""}), width="stretch")
            ui.aviso_tema_provisorio()
        with cb:
            st.markdown(f"**Documentos em comum** ({len(dd)})")
            lista = q("select doc_uid, tipo_doc tipo, ano, titulo from documento where list_contains(?, doc_uid) "
                      "order by ano desc", (dd,))
            ui.tabela_navegavel(lista, "doc", "doc_uid", "un_docs_rel", altura=420)

with t_evo:
    s = por_doc.groupby(["ano", "tipo_doc"], as_index=False).size()
    s["tipo"] = s.tipo_doc.map(dados.TIPOS)
    st.plotly_chart(px.bar(s, x="ano", y="size", color="tipo",
                           color_discrete_map={dados.TIPOS[k]: v for k, v in dados.CORES_TIPO.items()},
                           labels={"ano": "Ano", "size": "Documentos", "tipo": ""}), width="stretch")
    if not parc.empty:
        ev = q("""select ano, count(distinct doc_uid) n from aresta_unidade
                  where (unidade1 = ? or unidade2 = ?) and ano between ? and ? group by 1 order by 1""",
               (sel, sel, a0, a1))
        st.plotly_chart(px.line(ev, x="ano", y="n", markers=True,
                                labels={"ano": "Ano", "n": "Documentos em colaboração com outras unidades"}),
                        width="stretch")

with t_pes:
    p = q("""
        select p.pessoa_id, p.nome_exibicao nome,
               count(distinct case when d.tipo_doc = 'publicacao' then d.doc_uid end) obras,
               count(distinct case when dp.papel = 'lider' then d.doc_uid end) projetos_liderados,
               min(d.ano) desde, max(d.ano) ate
        from pessoa p join documento_pessoa dp using (pessoa_id) join documento d using (doc_uid)
        where p.unidade_ref_id = ? and d.ano between ? and ?
        group by all order by obras desc, projetos_liderados desc
    """, (sel, a0, a1))
    st.caption("Pesquisadores cuja unidade de referência é esta unidade (afiliação no cadastro "
               "ou, para lotações centrais, unidade inferida pela produção).")
    ui.tabela_navegavel(p, "pessoa", "pessoa_id", "un_pesq", altura=500)

with t_tema:
    if dados.tem_semantica():
        esp = q("""
            with base as (
                select t.doc_uid, t.tema_id, max(case when du.unidade_id = ? then 1 else 0 end) da_unidade
                from doc_tema t join documento d using (doc_uid) left join documento_unidade du using (doc_uid)
                where d.ano between ? and ? group by t.doc_uid, t.tema_id),
            tot as (select count(*) N, sum(da_unidade) Nu from base)
            select tema_id, sum(da_unidade) n_unidade, count(*) n_embrapa,
                   (sum(da_unidade) / any_value(Nu)) / (count(*) / any_value(N)) especializacao
            from base, tot group by tema_id having sum(da_unidade) >= 3
        """, (sel, a0, a1))
        esp["tema"] = esp.tema_id.map(dados.rotulo_tema)
        esp["macro"] = esp.tema_id.map(dados.temas().set_index("tema_id").pai_id).map(dados.rotulo_tema)
        cfg = {"tema": "Tema", "macro": "Macrotema", "n_unidade": "Documentos",
               "especializacao": st.column_config.NumberColumn(
                   "Especialização", format="%.1f",
                   help="Peso do tema na unidade ÷ peso do tema na Embrapa (> 1 = mais que a média)")}
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**Temas principais** (mais documentos)")
            ui.tabela_navegavel(esp.nlargest(20, "n_unidade")[["tema_id", "tema", "n_unidade", "especializacao"]],
                                "tema", "tema_id", "un_tema_top", colunas=cfg, altura=460)
        with c2:
            st.markdown("**Especialidades relativas** (vs. Embrapa)")
            ui.tabela_navegavel(esp[esp.n_unidade >= 5].nlargest(20, "especializacao")
                                [["tema_id", "tema", "n_unidade", "especializacao"]],
                                "tema", "tema_id", "un_tema_esp", colunas=cfg, altura=460)
        mac = esp.groupby("macro").n_unidade.sum().reset_index().sort_values("n_unidade")
        st.plotly_chart(px.bar(mac, x="n_unidade", y="macro", orientation="h", height=520,
                               labels={"n_unidade": "Documentos da unidade", "macro": ""}), width="stretch")
        ui.aviso_tema_provisorio()
    else:
        ui.aviso_tema_provisorio()
        esp = q("""
            with base as (
                select k.keyword_norm, any_value(lower(k.keyword_raw)) palavra, k.doc_uid,
                       max(case when du.unidade_id = ? then 1 else 0 end) da_unidade
                from documento_keyword k join documento d using (doc_uid)
                left join documento_unidade du using (doc_uid)
                where d.ano between ? and ? group by k.keyword_norm, k.doc_uid),
            tot as (select count(distinct doc_uid) N, count(distinct case when da_unidade = 1 then doc_uid end) Nu from base)
            select any_value(palavra) palavra, sum(da_unidade) n_unidade, count(*) n_embrapa,
                   (sum(da_unidade) / any_value(Nu)) / (count(*) / any_value(N)) especializacao
            from base, tot group by keyword_norm having sum(da_unidade) >= 3
        """, (sel, a0, a1))
        st.dataframe(esp.nlargest(30, "n_unidade")[["palavra", "n_unidade", "especializacao"]], hide_index=True,
                     width="stretch")

with t_prod:
    for tipo, rot in dados.TIPOS.items():
        sub = por_doc[por_doc.tipo_doc == tipo].sort_values("ano", ascending=False)
        with st.expander(f"{rot} ({len(sub)})", expanded=tipo == "projeto"):
            ui.tabela_navegavel(sub[["doc_uid", "ano", "titulo", "categoria", "papel"]], "doc", "doc_uid",
                                f"un_prod_{tipo}", altura=400)
