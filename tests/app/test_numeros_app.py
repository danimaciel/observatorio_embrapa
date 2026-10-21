"""Testes do app do Observatório: os números batem entre as páginas e com o banco.

Como rodar (na raiz do projeto, com o banco gerado pelo pipeline em data/processed/observatorio_app.duckdb):

    python -m pytest tests/app -q

O que é verificado
------------------
1. **Período padrão = acervo completo.** Ao abrir o app, o período da barra lateral vai do primeiro ao último ano
   do banco. Antes (até 21/10/2026) ele abria em 1990, e a página Embrapa mostrava 170.967 publicações
   enquanto a capa mostrava 180.951.
2. **Capa e página Embrapa mostram o mesmo número de publicações, projetos e tecnologias**, e esse número é igual
   à contagem feita direto no banco, por SQL, sem passar pelo app. Vale para o período padrão e para um período
   escolhido (2000–2010).
3. **Todas as páginas abrem sem erro.**

O banco é um só (observatorio_app.duckdb). O teste lê o banco direto com DuckDB para ter um valor de referência
independente do código das páginas.
"""

import re
import sys
from pathlib import Path

import duckdb
import pytest
from streamlit.testing.v1 import AppTest

RAIZ = Path(__file__).resolve().parents[2]
APP = str(RAIZ / "app" / "app.py")
DB = RAIZ / "data" / "processed" / "observatorio_app.duckdb"
sys.path.insert(0, str(RAIZ / "app"))   # "from lib import ..." como no streamlit run

PAGINAS = ["capa", "embrapa", "unidades", "redes", "mapa", "temas", "programacao", "pesquisadores",
           "documentos", "metodologia"]
TIPOS = {"publicacao": "publicações (obras)", "projeto": "projetos", "tecnologia": "soluções tecnológicas"}


def contagem_no_banco(a0=None, a1=None) -> dict:
    """Referência independente: documentos por tipo, contados direto no banco."""
    con = duckdb.connect(str(DB), read_only=True)
    filtro = "where ano between ? and ?" if a0 is not None else ""
    linhas = con.execute(f"select tipo_doc, count(*) from documento {filtro} group by 1",
                         [a0, a1] if a0 is not None else []).fetchall()
    con.close()
    return dict(linhas)


def anos_no_banco() -> tuple[int, int]:
    con = duckdb.connect(str(DB), read_only=True)
    a0, a1 = con.execute("select min(ano), max(ano) from documento").fetchone()
    con.close()
    return a0, a1


def numero(texto: str) -> int:
    return int(re.sub(r"\D", "", texto))


def kpis_capa(at: AppTest) -> dict:
    """Lê os cartões de números da capa (HTML: valor + rótulo)."""
    achados = {}
    for md in at.markdown:
        m = re.search(r'class="v">([\d.]+)</div><div class="r">([^<]+)<', md.value)
        if m:
            achados[m.group(2)] = numero(m.group(1))
    return {tipo: achados[rot] for tipo, rot in TIPOS.items()}


def kpis_embrapa(at: AppTest) -> dict:
    """Lê os indicadores (st.metric) da página Embrapa."""
    m = {x.label: numero(str(x.value)) for x in at.metric}
    return {"publicacao": m["Publicações (obras)"], "projeto": m["Projetos"], "tecnologia": m["Tecnologias"]}


def abrir(pagina: str, periodo=None) -> AppTest:
    at = AppTest.from_file(APP, default_timeout=180)
    if periodo:
        at.session_state["periodo"] = periodo
    at.run()
    if pagina != "capa":
        at.switch_page(f"paginas/{pagina}.py").run()
    assert not at.exception, [e.value for e in at.exception]
    return at


def test_periodo_padrao_e_o_acervo_completo():
    at = abrir("capa")
    assert tuple(at.session_state["periodo"]) == anos_no_banco()


@pytest.mark.parametrize("periodo", [None, (2000, 2010)])
def test_capa_e_embrapa_batem_com_o_banco(periodo):
    ref = contagem_no_banco(*(periodo or anos_no_banco()))
    capa = kpis_capa(abrir("capa", periodo))
    embrapa = kpis_embrapa(abrir("embrapa", periodo))
    for tipo in TIPOS:
        assert capa[tipo] == embrapa[tipo] == ref.get(tipo, 0), (tipo, capa[tipo], embrapa[tipo], ref.get(tipo))


@pytest.mark.parametrize("pagina", PAGINAS)
def test_pagina_abre_sem_erro(pagina):
    abrir(pagina)
