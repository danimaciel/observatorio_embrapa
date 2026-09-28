import pandas as pd
import plotly.express as px
import streamlit as st

from lib import dados, ui
from lib.dados import q

a0, a1 = dados.periodo()
st.title("Pesquisadores")


@st.cache_data(show_spinner=False)
def pessoas_com_producao() -> pd.DataFrame:
    return q("""select pessoa_id, nome_exibicao, unidade_ref_id from pessoa
                where n_obras > 0 or n_projetos_lider > 0 order by nome_exibicao""")


pes = pessoas_com_producao()
rot = dict(zip(pes.pessoa_id, pes.nome_exibicao + " — " + pes.unidade_ref_id.map(dados.rotulo_unidade)))
ids = pes.pessoa_id.tolist()
sel = ui.seletor_url("Pesquisador", ids, "pessoa", "pes_sel", format_func=rot.get,
                     placeholder="Digite o nome do pesquisador…")
if sel is None:
    st.info("Digite parte do nome para buscar. Estão listados os pesquisadores com projetos liderados ou "
            "publicações identificadas.")
    st.stop()

p = q("select * from pessoa where pessoa_id = ?", (sel,)).iloc[0]
docs = q("""
    select d.doc_uid, d.tipo_doc, d.titulo, d.ano, d.categoria, dp.papel, dp.nivel
    from documento_pessoa dp join documento d using (doc_uid)
    where dp.pessoa_id = ? and d.ano between ? and ?
""", (sel, a0, a1))
tecs = q("""
    select distinct t.doc_uid, t.titulo, t.ano, t.categoria, pt.obra
    from pessoa_tecnologia pt join documento t on t.doc_uid = pt.tecnologia_uid
    where pt.pessoa_id = ?
""", (sel,))
co = q("""
    select case when pessoa1 = ? then pessoa2 else pessoa1 end coautor,
           count(distinct doc_uid) obras, sum(peso_frac) peso, list(distinct doc_uid) docs
    from aresta_pessoa where (pessoa1 = ? or pessoa2 = ?) and ano between ? and ?
    group by 1 order by peso desc
""", (sel, sel, sel, a0, a1))
co = co.merge(q("select pessoa_id coautor, nome_exibicao nome, unidade_ref_id from pessoa"), on="coautor")
co["unidade"] = co.unidade_ref_id.map(dados.rotulo_unidade)

st.subheader(p.nome_exibicao)
c1, c2 = st.columns([3, 1])
c1.caption(f"Assinatura: {p.assinatura_principal} · período {a0}–{a1}")
with c2:
    ui.link("unidade", p.unidade_ref_id, dados.nome_unidade(p.unidade_ref_id), ":material/apartment:")

ui.kpis([
    ("Projetos liderados", int((docs.papel == "lider").sum())),
    ("Publicações (obras)", docs.loc[docs.tipo_doc == "publicacao", "doc_uid"].nunique()),
    ("Tecnologias associadas", len(tecs)),
    ("Coautores Embrapa", len(co)),
    ("Unidades dos coautores", co.unidade_ref_id.nunique()),
])

t_col, t_rede, t_evo, t_prod = st.tabs(["Com quem trabalha", "Rede", "Evolução temática", "Produção"])

with t_col:
    if co.empty:
        st.caption("Sem coautorias com outros pesquisadores Embrapa identificados no período.")
    else:
        # palavras-chave dos documentos em comum com cada coautor (temas provisórios)
        todos = tuple(sorted({d for l in co.docs for d in l}))
        kw = q("""select doc_uid, keyword_norm, lower(any_value(keyword_raw)) palavra from documento_keyword
                  where list_contains(?, doc_uid) group by all""", (list(todos),))
        def temas(lista):
            k = kw[kw.doc_uid.isin(lista)].groupby("palavra").size().nlargest(3)
            return ", ".join(k.index)
        co["temas_em_comum"] = co.docs.map(temas)

        st.markdown("#### Pesquisadores com quem mais trabalha")
        ui.tabela_navegavel(
            co[["coautor", "nome", "unidade", "obras", "peso", "temas_em_comum"]].head(50), "pessoa", "coautor",
            "pes_coaut", altura=420,
            colunas={"peso": st.column_config.NumberColumn("Intensidade", format="%.2f",
                                                           help="Contagem fracionária de Newman"),
                     "temas_em_comum": "Temas em comum (palavras-chave)"})

        st.markdown("#### Em quais unidades")
        pu = co.groupby(["unidade_ref_id", "unidade"], as_index=False).agg(
            coautores=("coautor", "nunique"), peso=("peso", "sum"), docs=("docs", lambda s: sorted({d for l in s for d in l})))
        pu["obras"] = pu.docs.map(len)
        pu["temas"] = pu.docs.map(temas)
        pu = pu.sort_values("peso", ascending=False)
        ca, cb = st.columns([1, 1])
        ca.plotly_chart(px.bar(pu.head(12)[::-1], x="peso", y="unidade", orientation="h",
                               labels={"peso": "Intensidade", "unidade": ""}), width="stretch")
        with cb:
            ui.tabela_navegavel(pu[["unidade_ref_id", "unidade", "coautores", "obras", "temas"]], "unidade",
                                "unidade_ref_id", "pes_unid", altura=380)
        ui.aviso_tema_provisorio()

with t_rede:
    n_max = st.slider("Coautores exibidos", 5, 40, 15)
    top = co.head(n_max)
    nos_ids = [sel] + top.coautor.tolist()
    ar = q("""select pessoa1 origem, pessoa2 destino, sum(peso_frac) peso, count(distinct doc_uid) n
              from aresta_pessoa where list_contains(?, pessoa1) and list_contains(?, pessoa2)
              and ano between ? and ? group by all""", (nos_ids, nos_ids, a0, a1))
    if ar.empty:
        st.caption("Sem rede no período.")
    else:
        info = q("select pessoa_id id, nome_exibicao rotulo, unidade_ref_id from pessoa where list_contains(?, pessoa_id)",
                 (nos_ids,))
        unid = {u: i for i, u in enumerate(info.unidade_ref_id.unique())}
        forca = pd.concat([ar[["origem", "peso"]].rename(columns={"origem": "id"}),
                           ar[["destino", "peso"]].rename(columns={"destino": "id"})]).groupby("id").peso.sum()
        nos = info.assign(tamanho=info.id.map(forca).fillna(0), grupo=info.unidade_ref_id.map(unid),
                          titulo=info.rotulo + " · " + info.unidade_ref_id.map(dados.rotulo_unidade))
        ar["titulo"] = ar.n.astype(str) + " obras em comum"
        ui.rede_pyvis(nos, ar, altura=560, destaque=sel)
        st.caption("Cor = unidade do pesquisador · espessura = intensidade da coautoria · "
                   "inclui as coautorias entre os próprios coautores.")

with t_evo:
    s = docs.assign(tipo=docs.tipo_doc.map(dados.TIPOS)).groupby(["ano", "tipo"], as_index=False).size()
    st.plotly_chart(px.bar(s, x="ano", y="size", color="tipo",
                           color_discrete_map={dados.TIPOS[k]: v for k, v in dados.CORES_TIPO.items()},
                           labels={"ano": "Ano", "size": "Documentos", "tipo": ""}), width="stretch")
    ui.aviso_tema_provisorio()
    kw = q("""select k.doc_uid, lower(any_value(k.keyword_raw)) palavra, d.ano from documento_keyword k
              join documento d using (doc_uid) where list_contains(?, k.doc_uid) group by k.doc_uid, k.keyword_norm, d.ano""",
           (docs.doc_uid.tolist(),))
    if not kw.empty:
        jan = 5
        kw["periodo"] = ((kw.ano // jan) * jan).astype(str) + "–" + ((kw.ano // jan) * jan + jan - 1).astype(str)
        topk = kw.palavra.value_counts().head(15).index
        h = kw[kw.palavra.isin(topk)].groupby(["palavra", "periodo"]).size().reset_index(name="n")
        st.plotly_chart(px.density_heatmap(h, x="periodo", y="palavra", z="n", color_continuous_scale="Greens",
                                           labels={"periodo": "Período", "palavra": "", "n": "Documentos"},
                                           category_orders={"palavra": list(topk)}),
                        width="stretch")

with t_prod:
    st.markdown("**Projetos liderados**")
    ui.tabela_navegavel(docs[docs.papel == "lider"][["doc_uid", "ano", "titulo", "categoria"]]
                        .sort_values("ano", ascending=False), "doc", "doc_uid", "pes_proj")
    st.markdown("**Publicações**")
    ui.tabela_navegavel(docs[docs.tipo_doc == "publicacao"][["doc_uid", "ano", "titulo", "categoria", "nivel"]]
                        .sort_values("ano", ascending=False), "doc", "doc_uid", "pes_pub", altura=400,
                        colunas={"nivel": st.column_config.TextColumn("Identificação", help="A determinística · "
                                                                      "B desambiguada · M manual")})
    st.markdown("**Tecnologias associadas** — vínculo declarado: a tecnologia cita uma publicação deste pesquisador")
    ui.tabela_navegavel(tecs.drop(columns="obra").drop_duplicates(), "doc", "doc_uid", "pes_tec")
