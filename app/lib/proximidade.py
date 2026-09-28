"""Proximidade temática entre unidades e colaborações potenciais (página Redes).

A proximidade compara o *conteúdo* da produção das unidades (centróide dos
embeddings de seus projetos, publicações e tecnologias) — é diferente da
colaboração observada, que conta documentos feitos em conjunto.
"""

import pandas as pd
import streamlit as st

from lib import dados, ui
from lib.dados import q

AJUDA = (
    "**Proximidade temática**: quão parecido é o conteúdo do que duas unidades produzem (projetos, publicações "
    "e tecnologias), segundo o modelo de linguagem — independentemente de trabalharem juntas. É medida pela "
    "semelhança entre os perfis temáticos das unidades e expressa em percentil entre todos os pares "
    "(99 = entre os 1% de pares mais parecidos).\n\n"
    "**Colaborações potenciais**: pares com conteúdo muito próximo, mas que colaboram pouco (força de "
    "associação abaixo de 1, ou nenhuma publicação em conjunto). São candidatos a aproximação — ou a "
    "investigar por que não colaboram."
)


@st.cache_data(show_spinner=False)
def proximidade() -> pd.DataFrame:
    p = q("select * from proximidade_unidade")
    return pd.concat([p, p.rename(columns={"unidade1": "unidade2", "unidade2": "unidade1"})], ignore_index=True)


def _colaboracao(a0: int, a1: int, camadas: tuple) -> pd.DataFrame:
    r = dados.rede_unidades(a0, a1, camadas)
    r2 = pd.concat([r, r.rename(columns={"unidade1": "unidade2", "unidade2": "unidade1"})], ignore_index=True)
    return r2[["unidade1", "unidade2", "n_docs", "forca"]]


def mostrar(modo: str, foco: str | None, camadas: tuple, a0: int, a1: int) -> None:
    with st.expander("O que são proximidade temática e colaborações potenciais?", expanded=False):
        st.markdown(AJUDA)
    p = proximidade().merge(_colaboracao(a0, a1, camadas), on=["unidade1", "unidade2"], how="left")
    p["n_docs"] = p.n_docs.fillna(0).astype(int)
    p["forca"] = p.forca.fillna(0.0)
    p["unidade_a"] = p.unidade1.map(dados.rotulo_unidade)
    p["unidade_b"] = p.unidade2.map(dados.rotulo_unidade)
    cfg = {"unidade_a": "Unidade", "unidade_b": "Unidade próxima", "unidade2": None, "unidade1": None,
           "percentil": st.column_config.ProgressColumn("Proximidade temática", min_value=0, max_value=100,
                                                        format="%.0f"),
           "n_docs": st.column_config.NumberColumn("Publicações em conjunto", help="No período e tipos escolhidos"),
           "forca": st.column_config.NumberColumn("Força de associação", format="%.2f")}

    if modo == "prox":
        if foco:
            v = p[p.unidade1 == foco].sort_values("cos", ascending=False)
            st.markdown(f"#### Unidades com conteúdo mais parecido com o de {dados.nome_unidade(foco)}")
            st.caption("Compare a proximidade temática com a colaboração observada: unidades muito próximas e com "
                       "pouca colaboração aparecem em *Colaborações potenciais*.")
            ui.tabela_navegavel(v[["unidade2", "unidade_b", "percentil", "n_docs", "forca"]], "unidade", "unidade2",
                                f"prox_{foco}", altura=520, colunas=cfg)
        else:
            k = st.slider("Ligações por unidade (as mais próximas)", 2, 8, 4)
            viz = p.sort_values("cos", ascending=False).groupby("unidade1").head(k)
            viz = viz.assign(a=viz[["unidade1", "unidade2"]].min(axis=1), b=viz[["unidade1", "unidade2"]].max(axis=1)) \
                .drop_duplicates(["a", "b"])
            ar = pd.DataFrame({"origem": viz.a, "destino": viz.b, "peso": viz.cos.clip(lower=0.01),
                               "titulo": viz.a.map(dados.rotulo_unidade) + " — " + viz.b.map(dados.rotulo_unidade)
                               + ": proximidade " + viz.percentil.round(0).astype(int).astype(str)})
            comm = ui.comunidades(ar)
            ids = sorted(set(ar.origem) | set(ar.destino))
            grau = pd.concat([ar.origem, ar.destino]).value_counts()
            nos = pd.DataFrame({"id": ids, "rotulo": [dados.rotulo_unidade(u) for u in ids],
                                "tamanho": [grau.get(u, 1) for u in ids],
                                "grupo": [comm.get(u, 0) for u in ids]})
            nos["titulo"] = nos.rotulo + " · grupo temático " + (nos.grupo + 1).astype(str)
            ui.rede_pyvis(nos, ar, altura=600)
            st.caption(f"Cada unidade ligada às {k} unidades de conteúdo mais parecido. Cor = grupo temático "
                       "(unidades que trabalham com assuntos semelhantes). Escolha uma unidade em foco para o detalhe.")
            grupos = nos.groupby("grupo").rotulo.apply(lambda s: ", ".join(sorted(s))).reset_index()
            grupos["grupo"] += 1
            st.dataframe(grupos, hide_index=True, width="stretch",
                         column_config={"grupo": st.column_config.NumberColumn("Grupo temático", width="small"),
                                        "rotulo": "Unidades"})
    else:  # colaborações potenciais
        corte = st.slider("Proximidade temática mínima (percentil)", 50, 99, 80)
        pot = p[(p.percentil >= corte) & (p.forca < 1)]
        if foco:
            pot = pot[pot.unidade1 == foco]
        else:
            pot = pot[pot.unidade1 < pot.unidade2]
        pot = pot.sort_values(["percentil", "n_docs"], ascending=[False, True])
        st.markdown(f"#### Colaborações potenciais{' de ' + dados.nome_unidade(foco) if foco else ''}")
        st.caption(f"Pares entre os {100 - corte}% mais próximos em conteúdo, mas com colaboração abaixo do "
                   "esperado (força de associação < 1). Clique para abrir a unidade próxima.")
        ui.tabela_navegavel(pot[["unidade2", "unidade_a", "unidade_b", "percentil", "n_docs", "forca"]],
                            "unidade", "unidade2", f"pot_{foco}", altura=520, colunas=cfg)
    st.caption("A proximidade temática considera toda a produção das unidades (todo o período); a colaboração "
               "segue o período e os tipos de relação escolhidos acima.")
