"""Rascunho da tabela tema (BERTopic) → portfólio(s) e especificação(ões) do Plano Diretor 2024–2030.

Status: validada em 18/10/2026 (revisão de 146 temas: 144 sem mudança, 2 corrigidos); T031 Seringueira
corrigida para Economia da Biodiversidade, O05.1. Fontes dos critérios: caracterização oficial
dos portfólios (ref/portfolios.csv, Portal Embrapa) e especificações oficiais (ref/objetivos_estrategicos.csv,
Plano Diretor). A ligação documento → programação é herdada do tema do documento (doc_tema).

Critérios (coluna `criterio`):
  producao      — sistema de produção de uma cadeia (manejo, cultivo, nutrição) → prosur, O01.1
  melhoramento  — cultivares, raças, melhoramento → prosur + biorrevolucao, O01.2
  fitossanidade — pragas, doenças, plantas daninhas → bioeficiencia, O04.6 (defesa) / O04.7 (agroquímicos)
  sanidade      — saúde animal → bioeficiencia, O04.6 / O04.7 (antimicrobianos, antiparasitários)
  bioinsumos    — microrganismos, biocontrole, fertilizantes orgânicos → everde, O05.4
  biomassa      — bioprocessos, bioenergia, resíduos, novos materiais → everde, O05.2 / O05.5
  recursos_nat  — solo, água, clima, geotecnologias, paisagem → ecoclima, O02.x
  sociobio      — espécies nativas, produtos da sociobiodiversidade → biodiversidade, O05.1 / O05.3
  alimentos     — qualidade, processamento, consumo → consumidor, O03.x
  agroecologia  — agricultura familiar, agroecologia, SAF, tecnologias sociais → agroecois, O06.x
  digital       — IA, sensores, automação → agrodigital, O07.x
  biotec        — genômica, biotecnologia, nanotecnologia → biorrevolucao, O01.2 / O07.3
  transversal   — gestão institucional e formação: sem portfólio

Gera: ref/tema_programacao.csv (decisões, editável) e relatorios/tema_programacao_revisao.xlsx (para revisão).
Uso: .venv-nlp/Scripts/python ref/fontes/tema_programacao_proposta.py
"""

from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parents[2]

# tema_id: (portfolio_1, portfolio_2, especificacao_1, especificacao_2, criterio, certeza, nota)
P = {
    # M00 Café, algodão, citros, cana e outras culturas
    "T002": ("prosur", "consumidor", "O01.1", "O03.3", "producao", "alta", ""),
    "T028": ("prosur", "biorrevolucao", "O01.1", "O01.2", "producao", "alta", ""),
    "T014": ("prosur", "bioeficiencia", "O01.1", "O04.6", "producao", "media", "inclui HLB e porta-enxertos"),
    "T027": ("prosur", "everde", "O01.1", "O05.5", "producao", "alta", "cana também é bioenergia"),
    "T017": ("prosur", "", "O01.1", "", "producao", "alta", ""),
    "T022": ("ecoclima", "biodiversidade", "O02.5", "O05.1", "recursos_nat", "duvida",
             "polinizadores (serviço ecossistêmico) × mel e meliponicultura (produto da biodiversidade)"),
    "T031": ("biodiversidade", "prosur", "O05.1", "O01.1", "sociobio", "alta", "revisão de 18/10/2026: Economia da Biodiversidade, O05.1"),
    "T055": ("prosur", "consumidor", "O01.1", "O03.3", "producao", "alta", ""),
    "T064": ("prosur", "everde", "O01.1", "O05.5", "producao", "media", "dendê: óleo e biocombustível"),
    "T117": ("prosur", "", "O01.1", "", "producao", "alta", ""),
    "T141": ("prosur", "", "O01.1", "", "producao", "alta", ""),
    # M01 Fitossanidade
    "T026": ("everde", "bioeficiencia", "O05.4", "O04.6", "bioinsumos", "alta", "biocontrole = bioinsumo"),
    "T033": ("bioeficiencia", "prosur", "O04.7", "O01.1", "fitossanidade", "alta", ""),
    "T041": ("bioeficiencia", "", "O04.6", "", "fitossanidade", "alta", ""),
    "T070": ("bioeficiencia", "", "O04.6", "", "fitossanidade", "alta", ""),
    "T082": ("bioeficiencia", "ecoclima", "O04.7", "O02.1", "fitossanidade", "alta", "risco ambiental de agroquímicos"),
    "T145": ("bioeficiencia", "", "O04.6", "", "fitossanidade", "alta", ""),
    # M02 Tecnologia de alimentos, bioprocessos e novos materiais
    "T052": ("everde", "", "O05.2", "O05.5", "biomassa", "alta", ""),
    "T116": ("consumidor", "biodiversidade", "O03.1", "O05.2", "alimentos", "alta", ""),
    "T056": ("everde", "consumidor", "O05.2", "O03.1", "biomassa", "media", "novos materiais de biomassa; embalagens"),
    "T079": ("agrodigital", "consumidor", "O07.1", "O01.3", "digital", "duvida",
             "métodos analíticos (NIR, LIBS) para solo e alimentos: instrumentação"),
    "T112": ("biorrevolucao", "", "O01.2", "O07.3", "biotec", "alta", "nanotecnologia citada no portfólio"),
    "T068": ("consumidor", "", "O03.1", "O03.3", "alimentos", "alta", ""),
    "T092": ("consumidor", "", "O03.1", "O03.2", "alimentos", "alta", ""),
    # M03 Hortaliças
    "T038": ("consumidor", "bioeficiencia", "O04.2", "O03.1", "alimentos", "media",
             "guias de compra e conservação: perdas e desperdício"),
    "T139": ("bioeficiencia", "", "O04.6", "", "fitossanidade", "alta", ""),
    "T049": ("prosur", "", "O01.1", "O04.3", "producao", "alta", ""),
    "T063": ("prosur", "", "O01.1", "", "producao", "alta", ""),
    "T040": ("prosur", "", "O01.1", "", "producao", "alta", ""),
    "T121": ("prosur", "", "O01.1", "O04.4", "producao", "alta", ""),
    # M04 Solos e fertilidade
    "T011": ("ecoclima", "prosur", "O02.3", "O02.4", "recursos_nat", "alta", "agricultura conservacionista, carbono"),
    "T095": ("everde", "agroecois", "O05.4", "O05.2", "bioinsumos", "alta", "fertilizantes orgânicos"),
    "T114": ("prosur", "everde", "O01.1", "O05.4", "producao", "media", "remineralizadores como insumo"),
    "T075": ("prosur", "", "O01.1", "", "producao", "alta", ""),
    "T096": ("ecoclima", "", "O02.4", "", "recursos_nat", "alta", ""),
    "T091": ("ecoclima", "prosur", "O02.3", "O01.1", "recursos_nat", "media", "plantas de cobertura, biochar"),
    "T143": ("ecoclima", "", "O02.4", "", "recursos_nat", "alta", ""),
    "T123": ("everde", "bioeficiencia", "O05.2", "O04.7", "biomassa", "media", "resíduos × contaminantes"),
    "T134": ("ecoclima", "biodiversidade", "O02.4", "O05.1", "recursos_nat", "media", ""),
    # M05 Florestas plantadas, sementes e propagação
    "T030": ("ecoclima", "biodiversidade", "O02.5", "O05.1", "recursos_nat", "media", "conhecimento da vegetação nativa"),
    "T023": ("prosur", "biodiversidade", "O01.1", "O02.6", "producao", "media", "inclui sementes de espécies nativas"),
    "T058": ("biorrevolucao", "prosur", "O01.2", "", "biotec", "alta", ""),
    "T101": ("prosur", "everde", "O01.1", "O05.2", "producao", "alta", "florestas plantadas"),
    "T083": ("prosur", "", "O01.1", "", "producao", "alta", ""),
    "T128": ("prosur", "everde", "O01.1", "O05.2", "producao", "alta", "florestas plantadas"),
    "T104": ("prosur", "biodiversidade", "O01.1", "O03.3", "producao", "media", ""),
    # M06 Agricultura familiar, sistemas integrados, florestas e clima
    "T007": ("agroecois", "", "O06.2", "O06.1", "agroecologia", "alta", ""),
    "T099": ("biodiversidade", "ecoclima", "O05.2", "O02.1", "sociobio", "alta", "produtos florestais madeireiros"),
    "T020": ("prosur", "ecoclima", "O01.1", "O02.3", "producao", "alta", "sistemas integrados (citados em O01.1)"),
    "T131": ("ecoclima", "", "O02.5", "", "recursos_nat", "alta", ""),
    "T115": ("ecoclima", "everde", "O02.2", "O01.3", "recursos_nat", "alta", "mudança do clima, emissões"),
    "T069": ("agroecois", "ecoclima", "O06.2", "O02.3", "agroecologia", "alta", ""),
    "T130": ("ecoclima", "", "O02.1", "O02.4", "recursos_nat", "alta", ""),
    "T062": ("ecoclima", "", "O02.5", "", "recursos_nat", "alta", ""),
    # M07 Geotecnologias, agrometeorologia e zoneamento
    "T054": ("ecoclima", "agrodigital", "O02.4", "O07.1", "recursos_nat", "alta", ""),
    "T074": ("ecoclima", "", "O02.2", "O02.4", "recursos_nat", "alta", ""),
    "T090": ("ecoclima", "", "O02.4", "O02.1", "recursos_nat", "alta", ""),
    "T098": ("ecoclima", "agrodigital", "O02.2", "", "recursos_nat", "alta", ""),
    "T073": ("ecoclima", "", "O02.4", "O02.2", "recursos_nat", "alta", ""),
    "T043": ("ecoclima", "agrodigital", "O02.4", "O07.1", "recursos_nat", "alta", ""),
    "T125": ("agrodigital", "", "O07.2", "", "digital", "alta", ""),
    "T136": ("ecoclima", "agrodigital", "O02.4", "", "recursos_nat", "alta", ""),
    # M08 Gestão, formação e biotecnologia
    "T003": ("", "agrodigital", "", "", "transversal", "duvida",
             "gestão, inovação e informática institucional; parte é agricultura digital"),
    "T080": ("", "", "", "", "transversal", "duvida", "gestão ambiental e planejamento institucional"),
    "T085": ("biorrevolucao", "", "O07.3", "O01.2", "biotec", "alta", "genômica citada no portfólio"),
    "T087": ("", "", "", "", "transversal", "alta", "formação (iniciação científica)"),
    "T126": ("biorrevolucao", "", "O07.3", "", "biotec", "alta", ""),
    "T133": ("", "agroecois", "", "", "transversal", "duvida", "séries institucionais do Semiárido e mecanização"),
    # M09 Recursos genéticos e fruteiras nativas
    "T045": ("biodiversidade", "biorrevolucao", "O02.6", "", "sociobio", "duvida",
             "recursos genéticos: especificação O02.6, mas nenhum portfólio os cita explicitamente"),
    "T076": ("biodiversidade", "", "O05.1", "", "sociobio", "alta", ""),
    "T016": ("prosur", "biodiversidade", "O01.1", "O04.7", "producao", "media", "maracujá cultivado e nativo"),
    "T057": ("biodiversidade", "prosur", "O05.3", "", "sociobio", "alta", ""),
    "T050": ("biodiversidade", "", "O05.3", "", "sociobio", "alta", ""),
    "T053": ("biodiversidade", "prosur", "O05.3", "", "sociobio", "alta", ""),
    "T024": ("biodiversidade", "", "O05.3", "", "sociobio", "alta", ""),
    "T061": ("biodiversidade", "prosur", "O05.3", "", "sociobio", "alta", ""),
    "T078": ("biodiversidade", "agroecois", "O05.1", "", "sociobio", "alta", "fruteira nativa da Caatinga"),
    "T110": ("prosur", "", "O01.1", "", "producao", "alta", ""),
    "T132": ("prosur", "", "O01.1", "", "producao", "alta", ""),
    # M10 Piscicultura, mandioca, pimentas e óleos essenciais
    "T001": ("prosur", "biodiversidade", "O01.1", "", "producao", "alta", "sistemas aquícolas citados em O01.1"),
    "T006": ("prosur", "agroecois", "O01.1", "O04.3", "producao", "alta", "base da dieta brasileira"),
    "T019": ("biodiversidade", "", "O05.2", "", "sociobio", "alta", "bioativos, cosméticos e fármacos"),
    "T119": ("prosur", "", "O01.1", "", "producao", "alta", ""),
    "T113": ("everde", "prosur", "O05.5", "", "biomassa", "alta", "biodiesel"),
    # M11 Feijões
    "T010": ("prosur", "consumidor", "O01.1", "O03.2", "producao", "alta", "fonte de proteína; dieta brasileira"),
    "T013": ("prosur", "biorrevolucao", "O01.2", "", "melhoramento", "alta", ""),
    "T032": ("bioeficiencia", "", "O04.6", "", "fitossanidade", "alta", ""),
    "T108": ("prosur", "", "O01.1", "", "producao", "alta", ""),
    "T093": ("prosur", "biorrevolucao", "O01.2", "", "melhoramento", "alta", ""),
    # M12 Microbiologia do solo e FBN
    "T140": ("biorrevolucao", "everde", "O05.4", "O02.6", "biotec", "media", "microbioma; coleções de microrganismos"),
    "T044": ("everde", "biorrevolucao", "O05.4", "", "bioinsumos", "alta", "inoculantes"),
    "T138": ("everde", "", "O05.4", "", "bioinsumos", "alta", "fixação biológica de nitrogênio"),
    "T097": ("everde", "biodiversidade", "O05.4", "", "bioinsumos", "alta", ""),
    # M13 Arroz
    "T004": ("prosur", "biorrevolucao", "O01.2", "", "melhoramento", "alta", ""),
    "T039": ("bioeficiencia", "", "O04.6", "", "fitossanidade", "alta", ""),
    "T081": ("prosur", "", "O01.1", "", "producao", "alta", ""),
    # M14 Uva e vinho
    "T000": ("consumidor", "prosur", "O03.3", "O01.1", "alimentos", "media", "vinhos, origem, enoturismo"),
    "T065": ("bioeficiencia", "", "O04.6", "", "fitossanidade", "alta", ""),
    # M15 Nutrição animal
    "T036": ("prosur", "", "O01.1", "", "producao", "alta", ""),
    "T084": ("prosur", "consumidor", "O01.1", "O03.4", "producao", "alta", ""),
    "T144": ("prosur", "", "O01.1", "", "producao", "alta", ""),
    "T122": ("prosur", "ecoclima", "O01.1", "O02.2", "producao", "alta", "metano entérico"),
    "T072": ("prosur", "", "O01.1", "", "producao", "alta", ""),
    # M16 Grãos
    "T015": ("prosur", "biorrevolucao", "O01.2", "", "melhoramento", "alta", ""),
    "T009": ("prosur", "biorrevolucao", "O01.2", "", "melhoramento", "alta", ""),
    "T059": ("prosur", "everde", "O01.2", "O05.5", "melhoramento", "alta", "sorgo sacarino: bioenergia"),
    "T124": ("prosur", "", "O01.1", "", "producao", "alta", ""),
    "T088": ("prosur", "ecoclima", "O01.1", "O02.3", "producao", "alta", ""),
    "T118": ("biorrevolucao", "ecoclima", "O02.2", "O01.2", "biotec", "media", "adaptação à seca"),
    "T089": ("prosur", "everde", "O01.1", "", "producao", "alta", ""),
    "T142": ("biorrevolucao", "prosur", "O01.2", "", "biotec", "media", "revisão: especificação 2 = outra (não listada)"),
    # M17 Fruticultura
    "T008": ("bioeficiencia", "prosur", "O04.6", "O01.1", "fitossanidade", "media", "termos dominados por sigatoka"),
    "T048": ("prosur", "", "O01.1", "", "producao", "alta", ""),
    "T029": ("prosur", "", "O01.1", "", "producao", "alta", ""),
    "T105": ("bioeficiencia", "", "O04.6", "", "fitossanidade", "alta", ""),
    "T051": ("prosur", "", "O01.1", "", "producao", "alta", ""),
    "T127": ("prosur", "bioeficiencia", "O01.1", "O04.6", "producao", "media", ""),
    "T129": ("prosur", "", "O01.1", "", "producao", "alta", ""),
    # M18 Pragas agrícolas
    "T005": ("bioeficiencia", "everde", "O04.6", "O05.4", "fitossanidade", "alta", "inclui controle biológico"),
    "T100": ("bioeficiencia", "", "O04.6", "", "fitossanidade", "alta", ""),
    "T034": ("bioeficiencia", "", "O04.6", "", "fitossanidade", "alta", ""),
    "T103": ("bioeficiencia", "", "O04.6", "", "fitossanidade", "alta", ""),
    "T111": ("bioeficiencia", "", "O04.6", "", "fitossanidade", "alta", ""),
    # M19 Cadeias pecuárias
    "T012": ("prosur", "consumidor", "O01.1", "O01.3", "producao", "alta", ""),
    "T109": ("prosur", "", "O01.1", "", "producao", "alta", ""),
    "T086": ("prosur", "agroecois", "O01.1", "", "producao", "alta", ""),
    "T106": ("prosur", "", "O01.1", "", "producao", "alta", ""),
    # M20 Sanidade animal
    "T037": ("bioeficiencia", "", "O04.6", "O04.8", "sanidade", "alta", ""),
    "T060": ("bioeficiencia", "", "O04.7", "O04.8", "sanidade", "alta", "antimicrobianos"),
    "T046": ("bioeficiencia", "", "O04.7", "", "sanidade", "alta", "antiparasitários"),
    "T035": ("bioeficiencia", "", "O04.7", "", "sanidade", "alta", "antiparasitários"),
    # M21 Pastagens e forrageiras
    "T067": ("prosur", "", "O01.1", "", "producao", "alta", ""),
    "T018": ("prosur", "", "O01.1", "", "producao", "alta", ""),
    "T094": ("prosur", "biodiversidade", "O01.1", "", "producao", "media", "forrageiras nativas do Cerrado; revisão: especificação 2 = outra (não listada)"),
    "T042": ("prosur", "", "O01.1", "", "producao", "alta", ""),
    "T120": ("biorrevolucao", "prosur", "O01.2", "O02.6", "biotec", "media", "melhoramento e apomixia"),
    "T107": ("prosur", "biodiversidade", "O01.2", "O02.6", "melhoramento", "media", "germoplasma nativo"),
    # M22 Reprodução e melhoramento genético animal
    "T021": ("prosur", "biorrevolucao", "O01.2", "", "melhoramento", "alta", "biotecnologias da reprodução"),
    "T025": ("prosur", "biorrevolucao", "O01.2", "", "melhoramento", "alta", ""),
    "T077": ("biorrevolucao", "prosur", "O01.2", "O07.3", "biotec", "alta", "genômica"),
    "T071": ("prosur", "biorrevolucao", "O01.2", "", "melhoramento", "alta", ""),
    # M23 Trigo
    "T047": ("prosur", "biorrevolucao", "O01.2", "", "melhoramento", "alta", ""),
    "T135": ("bioeficiencia", "", "O04.6", "O04.7", "fitossanidade", "alta", "micotoxinas da giberela"),
    # M24 Recursos hídricos e irrigação
    "T102": ("ecoclima", "", "O02.4", "", "recursos_nat", "alta", ""),
    "T137": ("prosur", "ecoclima", "O01.1", "", "producao", "alta", "uso eficiente da água"),
    "T066": ("ecoclima", "agroecois", "O02.7", "O06.3", "recursos_nat", "alta", "convivência com a seca"),
}


PENDENTES: set[str] = set()     # T031 Seringueira resolvida em 18/10/2026


def main() -> None:
    tema = pd.read_parquet(RAIZ / "data" / "processed" / "tema.parquet")
    dt = pd.read_parquet(RAIZ / "data" / "processed" / "doc_tema.parquet")
    doc = pd.read_parquet(RAIZ / "data" / "processed" / "documento.parquet", columns=["doc_uid", "titulo", "ano"])
    port = pd.read_csv(RAIZ / "ref" / "portfolios.csv", dtype=str).set_index("portfolio_id")
    esp = pd.read_csv(RAIZ / "ref" / "objetivos_estrategicos.csv", dtype=str).set_index("especificacao_id")
    t2 = tema[tema.nivel == 2].set_index("tema_id")
    macro = tema[tema.nivel == 1].set_index("tema_id").rotulo
    faltam = set(t2.index) - set(P)
    assert not faltam, f"temas sem proposta: {sorted(faltam)}"
    for k, (p1, p2, e1, e2, *_r) in P.items():
        for p in (p1, p2):
            assert p == "" or p in port.index, (k, p)
        for e in (e1, e2):
            assert e == "" or e in esp.index, (k, e)

    n = dt.tema_id.value_counts()
    ex = dt.sort_values("score", ascending=False).groupby("tema_id").head(3).merge(doc, on="doc_uid") \
        .groupby("tema_id").titulo.agg(lambda s: " || ".join(s.str.slice(0, 90)))
    rows = []
    for tid, (p1, p2, e1, e2, crit, certeza, nota) in P.items():
        rows.append(dict(
            tema_id=tid, tema=t2.rotulo[tid], macrotema=macro[t2.pai_id[tid]], n_documentos=int(n.get(tid, 0)),
            portfolio_1=p1, portfolio_2=p2, especificacao_1=e1, especificacao_2=e2, criterio=crit,
            certeza=certeza, nota=nota,
            status="corrigir: a confirmar" if tid in PENDENTES else "validada (18/10/2026)"))
    x = pd.DataFrame(rows).sort_values(["macrotema", "n_documentos"], ascending=[True, False])
    x.to_csv(RAIZ / "ref" / "tema_programacao.csv", index=False, encoding="utf-8")

    # Planilha de revisão: nomes por extenso, exemplos de títulos e colunas para a decisão
    nomep = lambda p: port.nome_portal.get(p, "") if p else "— (transversal)"
    nomee = lambda e: f"{e} {esp.especificacao[e]} ({esp.objetivo[e]})" if e else ""
    r = x.assign(portfolio_1=x.portfolio_1.map(nomep), portfolio_2=x.portfolio_2.map(lambda p: nomep(p) if p else ""),
                 especificacao_1=x.especificacao_1.map(nomee), especificacao_2=x.especificacao_2.map(nomee),
                 exemplos=x.tema_id.map(ex), decisao="", correcao="", comentario="")
    saida = RAIZ / "relatorios" / "tema_programacao_revisao.xlsx"
    if saida.exists():          # não sobrescreve a planilha já revisada
        saida = saida.with_name("tema_programacao_revisao_v2.xlsx")
    with pd.ExcelWriter(saida, engine="openpyxl") as w:
        r.drop(columns=["status"]).to_excel(w, sheet_name="Temas", index=False)
        port.reset_index()[["portfolio_id", "nome_portal", "caracterizacao"]].to_excel(w, sheet_name="Portfólios",
                                                                                        index=False)
        esp.reset_index()[["especificacao_id", "objetivo", "especificacao", "texto"]].to_excel(
            w, sheet_name="Especificações", index=False)
        from openpyxl.worksheet.datavalidation import DataValidation
        ws = w.sheets["Temas"]
        col = {c.value: c.column_letter for c in ws[1]}
        dv = DataValidation(type="list", formula1='"ok,corrigir,dúvida"', allow_blank=True)
        ws.add_data_validation(dv)
        dv.add(f"{col['decisao']}2:{col['decisao']}{ws.max_row}")
        larg = {"tema": 34, "macrotema": 28, "portfolio_1": 32, "portfolio_2": 28, "especificacao_1": 48,
                "especificacao_2": 40, "nota": 40, "exemplos": 80, "correcao": 30, "comentario": 30}
        for k, v in larg.items():
            ws.column_dimensions[col[k]].width = v
        ws.freeze_panes = "C2"
        ws.auto_filter.ref = ws.dimensions

    # Resumo: documentos por portfólio principal (via tema)
    d = dt.merge(x[["tema_id", "portfolio_1"]], on="tema_id")
    print(f"Temas: {len(x)} · certeza: {x.certeza.value_counts().to_dict()}")
    print("Documentos por portfólio principal:",
          d.portfolio_1.replace("", "transversal").value_counts().to_dict())
    d2 = dt.merge(x[["tema_id", "especificacao_1"]], on="tema_id")
    print("Documentos por objetivo:", d2.especificacao_1.str.slice(0, 3).replace("", "transversal")
          .value_counts().sort_index().to_dict())
    print("Gravado:", saida)


if __name__ == "__main__":
    main()
