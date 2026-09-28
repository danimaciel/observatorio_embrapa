import plotly.express as px
import streamlit as st

from lib import dados, ui
from lib.dados import q

a0, a1 = dados.periodo()
st.title("Embrapa")
st.caption(f"Visão institucional · {a0}–{a1}")

tot = q("""
    select tipo_doc, count(*) n from documento where ano between ? and ? group by 1
""", (a0, a1)).set_index("tipo_doc")["n"]
pesq = q("""
    select count(distinct dp.pessoa_id) n from documento_pessoa dp
    join documento d using (doc_uid) where d.ano between ? and ?
""", (a0, a1)).n[0]
colab = q("""
    with u as (select doc_uid, count(distinct unidade_id) k from documento_unidade
               where papel in ('depositante','afiliacao_autor') group by 1)
    select avg(case when k > 1 then 1.0 else 0 end) p from u join documento d using (doc_uid)
    where d.ano between ? and ?
""", (a0, a1)).p[0]

ui.kpis([
    ("Projetos", int(tot.get("projeto", 0))),
    ("Publicações (obras)", int(tot.get("publicacao", 0))),
    ("Tecnologias", int(tot.get("tecnologia", 0))),
    ("Pesquisadores com produção", int(pesq)),
    ("Publicações com ≥ 2 unidades", f"{100 * (colab or 0):.1f}%"),
])

t1, t2, t3, t4 = st.tabs(["Produção anual", "Publicações por tipo", "Colaboração", "Unidades"])

with t1:
    s = q("select ano, tipo_doc, count(*) n from documento where ano between ? and ? group by all order by 1",
          (a0, a1))
    s["tipo"] = s.tipo_doc.map(dados.TIPOS)
    fig = px.line(s, x="ano", y="n", color="tipo", markers=True,
                  color_discrete_map={dados.TIPOS[k]: v for k, v in dados.CORES_TIPO.items()},
                  labels={"ano": "Ano", "n": "Documentos", "tipo": ""})
    st.plotly_chart(fig, width="stretch")
    st.caption("Projetos contados pelo ano de início.")

with t2:
    s = q("""select ano, categoria, count(*) n from documento
             where tipo_doc = 'publicacao' and ano between ? and ? group by all order by 1""", (a0, a1))
    s["categoria"] = s.categoria.map(dados.GRUPOS_PUB).fillna(s.categoria)
    fig = px.area(s, x="ano", y="n", color="categoria", labels={"ano": "Ano", "n": "Obras", "categoria": ""})
    st.plotly_chart(fig, width="stretch")

with t3:
    s = q("""
        with u as (select doc_uid, count(distinct unidade_id) k from documento_unidade
                   where papel in ('depositante','afiliacao_autor') group by 1)
        select d.ano, avg(case when k > 1 then 100.0 else 0 end) pct, count(*) n
        from u join documento d using (doc_uid) where d.ano between ? and ? group by 1 order by 1
    """, (a0, a1))
    fig = px.line(s, x="ano", y="pct", markers=True, hover_data=["n"],
                  labels={"ano": "Ano", "pct": "% de obras com ≥ 2 unidades", "n": "Obras"})
    st.plotly_chart(fig, width="stretch")
    st.caption("Unidades de uma obra = unidades depositantes + unidade dos autores Embrapa identificados "
               "(na época da obra). Detalhes em Metodologia.")

with t4:
    s = q("""
        select du.unidade_id, d.tipo_doc, count(distinct du.doc_uid) n
        from documento_unidade du join documento d using (doc_uid)
        where d.ano between ? and ? group by all
    """, (a0, a1))
    s["unidade"] = s.unidade_id.map(dados.rotulo_unidade)
    s["tipo"] = s.tipo_doc.map(dados.TIPOS)
    ordem = s.groupby("unidade")["n"].sum().sort_values().index.tolist()
    fig = px.bar(s, y="unidade", x="n", color="tipo", orientation="h", category_orders={"unidade": ordem[::-1]},
                 color_discrete_map={dados.TIPOS[k]: v for k, v in dados.CORES_TIPO.items()},
                 labels={"n": "Documentos com participação", "unidade": "", "tipo": ""}, height=900)
    st.plotly_chart(fig, width="stretch")
    tab = s.pivot_table(index=["unidade_id", "unidade"], columns="tipo", values="n", fill_value=0).reset_index()
    ui.tabela_navegavel(tab.sort_values("unidade"), "unidade", "unidade_id", "emb_unid")

st.subheader("Temas em destaque")
ui.aviso_tema_provisorio()
k = q("""
    select lower(any_value(k.keyword_raw)) palavra, count(distinct k.doc_uid) n from documento_keyword k
    join documento d using (doc_uid) where d.ano between ? and ? group by k.keyword_norm
    order by n desc limit 20
""", (a0, a1))
st.plotly_chart(px.bar(k.sort_values("n"), x="n", y="palavra", orientation="h",
                       labels={"n": "Documentos", "palavra": ""}), width="stretch")
