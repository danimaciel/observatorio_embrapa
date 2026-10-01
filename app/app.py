"""Observatório de Pesquisa da Embrapa — ponto de entrada.

Executar na raiz do projeto:  streamlit run app/app.py
"""

import streamlit as st

from lib import dados

st.set_page_config(page_title="Observatório de Pesquisa da Embrapa", page_icon=":material/hub:",
                   layout="wide")

paginas = {
    "Visão institucional": [
        st.Page("paginas/embrapa.py", title="Embrapa", icon=":material/account_balance:",
                url_path="embrapa", default=True),
        st.Page("paginas/unidades.py", title="Unidades", icon=":material/apartment:", url_path="unidades"),
        st.Page("paginas/redes.py", title="Redes", icon=":material/hub:", url_path="redes"),
        st.Page("paginas/mapa.py", title="Mapa", icon=":material/map:", url_path="mapa"),
        st.Page("paginas/temas.py", title="Temas", icon=":material/category:", url_path="temas"),
    ],
    "Consulta": [
        st.Page("paginas/pesquisadores.py", title="Pesquisadores", icon=":material/person_search:",
                url_path="pesquisadores"),
        st.Page("paginas/documentos.py", title="Documentos", icon=":material/description:",
                url_path="documentos"),
    ],
    "Sobre": [
        st.Page("paginas/metodologia.py", title="Metodologia", icon=":material/menu_book:",
                url_path="metodologia"),
    ],
}
# Área restrita (programação): local, com o banco presente; online, protegida por senha
if dados.tem_interno():
    paginas["Área restrita"] = [
        st.Page("paginas/programacao.py", title="Programação", icon=":material/flag:", url_path="programacao"),
    ]
pg = st.navigation(paginas)

with st.sidebar:
    st.markdown("### Observatório de Pesquisa")
    a0, a1 = dados.faixa_anos()
    if "periodo" not in st.session_state:
        st.session_state["periodo"] = (max(a0, 1990), a1)
    st.slider("Período", min_value=a0, max_value=a1, key="periodo",
              help="Projetos pelo ano de início; publicações e tecnologias pelo ano.")
    m = dados.meta()
    st.caption(f"Dados: exportação {m['exportacao']} · processados em {m['gerado_em']}")
    if "publicacoes" in (m.get("arquivos_truncados") or ""):
        n_pub = dados.q("select count(*) n from publicacao").n[0]
        n_fmt = f"{n_pub:,}".replace(",", ".")
        st.warning(f"**Base de publicações incompleta.** O arquivo recebido foi cortado no meio da cópia: "
                   f"foram lidos {n_fmt} registros, quase todos até 2009. Publicações e as colaborações "
                   "derivadas delas estão subestimadas; projetos e tecnologias estão completos.",
                   icon=":material/warning:")

pg.run()
