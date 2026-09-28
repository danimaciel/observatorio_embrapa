import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
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
    st.markdown("#### Colaboração entre unidades nas publicações")
    st.caption("Uma obra é colaborativa quando envolve 2 ou mais unidades: unidades depositantes + unidade dos "
               "autores Embrapa identificados (na época da obra). Detalhes em Metodologia.")
    s = q("""
        with u as (select doc_uid, count(distinct unidade_id) k from documento_unidade
                   where papel in ('depositante','afiliacao_autor') group by 1)
        select d.ano, count(*) obras, sum(case when k > 1 then 1 else 0 end) colaborativas
        from u join documento d using (doc_uid) where d.ano between ? and ? group by 1 order by 1
    """, (a0, a1))
    s["pct"] = (100 * s.colaborativas / s.obras).where(s.obras >= 30)
    fig = go.Figure()
    fig.add_bar(x=s.ano, y=s.colaborativas, name="Obras colaborativas", marker_color=dados.CORES_TIPO["publicacao"])
    fig.add_scatter(x=s.ano, y=s.pct, name="% das obras do ano", yaxis="y2", mode="lines+markers",
                    line_color="#EF6C00", connectgaps=False)
    fig.update_layout(yaxis=dict(title="Obras com ≥ 2 unidades"),
                      yaxis2=dict(title="% das obras", overlaying="y", side="right", rangemode="tozero"),
                      legend=dict(orientation="h", y=1.12), margin=dict(t=40))
    st.plotly_chart(fig, width="stretch")
    st.caption("O percentual só é mostrado em anos com pelo menos 30 obras, para evitar distorções "
               "em anos com pouca produção registrada.")

    r = dados.rede_unidades(a0, a1, ("publicacoes",))
    if not r.empty:
        forca_un = pd.concat([r[["unidade1", "peso"]].rename(columns={"unidade1": "u"}),
                              r[["unidade2", "peso"]].rename(columns={"unidade2": "u"})]).groupby("u").peso.sum()
        n_top = st.slider("Unidades na matriz", 10, len(forca_un), min(20, len(forca_un)))
        top = forca_un.nlargest(n_top).index.tolist()
        rr = r[r.unidade1.isin(top) & r.unidade2.isin(top)]
        m = pd.concat([rr, rr.rename(columns={"unidade1": "unidade2", "unidade2": "unidade1"})])             .pivot_table(index="unidade1", columns="unidade2", values="n_docs", aggfunc="sum")             .reindex(index=top, columns=top)
        rot = [dados.rotulo_unidade(u) for u in top]
        fig = px.imshow(m.values, x=rot, y=rot, color_continuous_scale="Blues", aspect="auto",
                        labels={"color": "Obras em comum"})
        fig.update_layout(height=250 + 22 * n_top, xaxis_tickangle=-45)
        st.markdown("**Matriz de colaboração** — obras em comum entre as unidades mais colaborativas")
        st.plotly_chart(fig, width="stretch")

        st.markdown("**Pares de unidades que mais colaboram**")
        pares = r.sort_values("n_docs", ascending=False).head(40).assign(
            unidade_a=lambda d: d.unidade1.map(dados.rotulo_unidade),
            unidade_b=lambda d: d.unidade2.map(dados.rotulo_unidade))
        ui.tabela_navegavel(
            pares[["unidade1", "unidade_a", "unidade_b", "n_docs", "peso", "forca"]], "unidade", "unidade1",
            "emb_pares", altura=400,
            colunas={"n_docs": "Obras em comum",
                     "peso": st.column_config.NumberColumn("Intensidade", format="%.1f"),
                     "forca": st.column_config.NumberColumn("Força de associação", format="%.2f")})

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
if dados.tem_semantica():
    k = q("""select t.tema_id, count(*) n from doc_tema t join documento d using (doc_uid)
             where d.ano between ? and ? group by 1 order by n desc limit 20""", (a0, a1))
    k["tema"] = k.tema_id.map(dados.rotulo_tema)
    k["macro"] = k.tema_id.map(dados.temas().set_index("tema_id").pai_id).map(dados.rotulo_tema)
    st.plotly_chart(px.bar(k.sort_values("n"), x="n", y="tema", color="macro", orientation="h", height=620,
                           labels={"n": "Documentos", "tema": "", "macro": "Macrotema"}), width="stretch")
    ui.tabela_navegavel(k[["tema_id", "tema", "macro", "n"]], "tema", "tema_id", "emb_temas", altura=300,
                        colunas={"tema": "Tema", "macro": "Macrotema", "n": "Documentos"})
    ui.aviso_tema_provisorio()
else:
    ui.aviso_tema_provisorio()
    k = q("""
        select lower(any_value(k.keyword_raw)) palavra, count(distinct k.doc_uid) n from documento_keyword k
        join documento d using (doc_uid) where d.ano between ? and ? group by k.keyword_norm
        order by n desc limit 20
    """, (a0, a1))
    st.plotly_chart(px.bar(k.sort_values("n"), x="n", y="palavra", orientation="h",
                           labels={"n": "Documentos", "palavra": ""}), width="stretch")
