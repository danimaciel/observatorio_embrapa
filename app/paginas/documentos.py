import streamlit as st

from lib import dados, ui
from lib.dados import q

PAPEIS = {"lider": "unidade líder", "depositante": "depositante", "responsavel": "responsável",
          "afiliacao_autor": "afiliação de autor"}
NIVEIS = {"A": "identificado", "B": "identificado (desambiguado)", "M": "identificado (manual)",
          "C": "ambíguo", "D": "externo / não identificado"}

st.title("Documentos")
param = st.query_params.get("doc")

with st.expander("Buscar documento", expanded=param is None):
    c1, c2 = st.columns([3, 2])
    termo = c1.text_input("Título contém", placeholder="ex.: maracujazeiro, integração lavoura-pecuária…")
    tipos = c2.pills("Tipo", list(dados.TIPOS), selection_mode="multi", default=list(dados.TIPOS),
                     format_func=dados.TIPOS.get)
    if termo and len(termo) >= 3:
        res = q("""
            select doc_uid, tipo_doc tipo, ano, titulo, unidade_id from documento
            where strip_accents(lower(titulo)) like '%' || strip_accents(lower(?)) || '%'
              and list_contains(?, tipo_doc)
            order by ano desc limit 300
        """, (termo, list(tipos)))
        res["unidade"] = res.unidade_id.map(dados.rotulo_unidade)
        st.caption(f"{len(res)} resultado(s) (máx. 300)")
        ui.tabela_navegavel(res.drop(columns="unidade_id"), "doc", "doc_uid", "doc_busca", altura=380)

if not param:
    st.stop()

d = q("select * from documento where doc_uid = ?", (param,))
if d.empty:
    st.warning("Documento não encontrado.")
    st.stop()
d = d.iloc[0]
st.query_params["doc"] = param

st.caption(f"{dados.TIPOS[d.tipo_doc][:-1] if d.tipo_doc != 'publicacao' else 'Publicação'} · {d.doc_uid}")
st.subheader(d.titulo)
anos = f"{d.ano}–{int(d.ano_fim)}" if d.tipo_doc == "projeto" and d.ano_fim == d.ano_fim else f"{d.ano}"
st.markdown(f"**Ano:** {anos} · **Categoria:** {dados.GRUPOS_PUB.get(d.categoria, d.categoria)}"
            + (f" · {d.detalhe}" if d.detalhe and d.detalhe != d.categoria else ""))
if d.url:
    st.link_button("Ver no portal da Embrapa", d.url, icon=":material/open_in_new:")
if d.resumo:
    with st.expander("Resumo / descrição", expanded=True):
        st.write(d.resumo)

c1, c2 = st.columns(2)
with c1:
    st.markdown("**Unidades**")
    u = q("select unidade_id, papel from documento_unidade where doc_uid = ?", (param,))
    u = u.groupby("unidade_id", as_index=False).papel.agg(lambda s: ", ".join(PAPEIS.get(x, x) for x in sorted(set(s))))
    u["unidade"] = u.unidade_id.map(dados.nome_unidade)
    ui.tabela_navegavel(u[["unidade_id", "unidade", "papel"]], "unidade", "unidade_id", "doc_unid")
with c2:
    st.markdown("**Pessoas**" if d.tipo_doc != "publicacao" else "**Autores**")
    if d.tipo_doc == "tecnologia":
        st.caption("A base de tecnologias não traz pessoas; veja as publicações citadas abaixo.")
    else:
        ref = d.doc_uid_representante if d.tipo_doc == "publicacao" else d.doc_uid
        a = q("""select ordem, rotulo_exibicao nome, nivel, pessoa_id from doc_pessoa
                 where doc_uid = ? order by papel desc, ordem""", (ref,))
        a["identificacao"] = a.nivel.map(NIVEIS)
        ident = a[a.pessoa_id.notna()]
        ui.tabela_navegavel(ident[["pessoa_id", "nome", "identificacao"]], "pessoa", "pessoa_id", "doc_pes")
        outros = a[a.pessoa_id.isna()]
        if not outros.empty:
            st.caption("Demais autores: " + "; ".join(outros.nome))

kw = q("select distinct keyword_raw from documento_keyword where doc_uid = ?", (param,))
if not kw.empty:
    st.markdown("**Palavras-chave:** " + " · ".join(kw.keyword_raw))

if d.tipo_doc == "publicacao" and d.n_registros and d.n_registros > 1:
    st.markdown("**Registros desta obra no repositório** — depositada por mais de uma unidade")
    r = q("select doc_uid, unidade_id, tipo, url_repositorio from publicacao where obra_id = ?", (param,))
    r["unidade"] = r.unidade_id.map(dados.nome_unidade)
    st.dataframe(r[["doc_uid", "unidade", "tipo", "url_repositorio"]], hide_index=True, width="stretch",
                 column_config={"url_repositorio": st.column_config.LinkColumn("Repositório")})

if d.tipo_doc == "tecnologia":
    lk = q("""select distinct p.obra_id doc_uid, d.ano, d.titulo from doc_link l
              join publicacao p on p.doc_uid = l.destino_uid join documento d on d.doc_uid = p.obra_id
              where l.origem_uid = ?""", (param,))
    todos = q("select count(*) n from doc_link where origem_uid = ?", (param,)).n[0]
    st.markdown(f"**Publicações citadas pela tecnologia** ({todos} citadas; {len(lk)} presentes na base)")
    ui.tabela_navegavel(lk, "doc", "doc_uid", "doc_link_t")
elif d.tipo_doc == "publicacao":
    lk = q("""select distinct t.doc_uid, t.ano, t.titulo from doc_link l
              join publicacao p on p.doc_uid = l.destino_uid join documento t on t.doc_uid = l.origem_uid
              where p.obra_id = ?""", (param,))
    if not lk.empty:
        st.markdown("**Tecnologias que citam esta publicação**")
        ui.tabela_navegavel(lk, "doc", "doc_uid", "doc_link_b")

st.markdown("#### Documentos semelhantes")
st.info("Projetos, publicações e tecnologias semanticamente relacionados a este documento aparecerão aqui "
        "após a geração dos embeddings (fase 3 do pipeline).", icon=":material/hourglass_top:")
