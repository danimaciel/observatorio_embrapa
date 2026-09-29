"""Municípios e estados mencionados nos textos (piloto do mapa territorial).

Procura os 5.570 municípios do IBGE em título, resumo e palavras-chave e
atribui um nível de confiança a cada menção:

  alta   nome seguido da UF ("Petrolina, PE", "Petrolina-PE", "Petrolina (PE)")
         ou nome único no país que não é palavra comum
  media  homônimo (mesmo nome em vários estados) em texto que cita o estado
         de um único dos candidatos
  baixa  palavra comum ou homônimo sem contexto — descartada nos mapas

"Palavra comum" é definida pelos próprios textos: nomes que aparecem com
frequência em minúsculas (manga, floresta, canela, palmeira...) só contam
com a UF ao lado. Nomes que também são estados (Goiás, Paraná, Tocantins,
São Paulo...) contam como menção ao estado, salvo com a UF ao lado.

Saídas em data/processed/: doc_municipio.parquet, doc_estado.parquet
Relatório: relatorios/piloto_municipios.md e amostra para conferência.
Uso: .venv-nlp/Scripts/python pipeline/py/municipios.py
"""

import json
import re
import time
import unicodedata

import numpy as np
import pandas as pd

from textos import PROC, RAIZ, carregar_textos

GEO = RAIZ / "data" / "raw" / "geo"
UFS = {"AC": "Acre", "AL": "Alagoas", "AP": "Amapá", "AM": "Amazonas", "BA": "Bahia", "CE": "Ceará",
       "DF": "Distrito Federal", "ES": "Espírito Santo", "GO": "Goiás", "MA": "Maranhão", "MT": "Mato Grosso",
       "MS": "Mato Grosso do Sul", "MG": "Minas Gerais", "PA": "Pará", "PB": "Paraíba", "PR": "Paraná",
       "PE": "Pernambuco", "PI": "Piauí", "RJ": "Rio de Janeiro", "RN": "Rio Grande do Norte",
       "RS": "Rio Grande do Sul", "RO": "Rondônia", "RR": "Roraima", "SC": "Santa Catarina", "SP": "São Paulo",
       "SE": "Sergipe", "TO": "Tocantins"}


def sem_acento(s: str) -> str:
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()


def carregar_municipios() -> pd.DataFrame:
    m = json.load(open(GEO / "municipios_ibge.json", encoding="utf-8"))
    df = pd.DataFrame([{"cod_ibge": str(x["id"]), "municipio": x["nome"],
                        "uf": (x.get("microrregiao") or {}).get("mesorregiao", {}).get("UF", {}).get("sigla")
                        or x["regiao-imediata"]["regiao-intermediaria"]["UF"]["sigla"]} for x in m])
    df["chave"] = df.municipio.map(sem_acento)
    return df


def main() -> None:
    t0 = time.time()
    docs = carregar_textos()[["doc_uid", "tipo_doc", "texto_rotulo"]]
    originais = docs.texto_rotulo.fillna("").tolist()
    textos = [sem_acento(t) for t in originais]
    # nomes de estado com acento exato; "Pará" só com acento (sem ele, é a preposição "para")
    padroes_estado_orig = {uf: re.compile(rf"\b{re.escape(nome)}\b") for uf, nome in UFS.items()}
    padroes_estado_orig["MT"] = re.compile(r"\bMato Grosso\b(?! do Sul)")   # não confundir com MS
    mun = carregar_municipios()
    por_nome = mun.groupby("chave").apply(lambda g: list(zip(g.cod_ibge, g.municipio, g.uf)), include_groups=False).to_dict()
    nomes_estado = {sem_acento(v): k for k, v in UFS.items()}

    # palavras comuns: frequência em minúsculas × com inicial maiúscula no corpus
    # (contagem única de palavras; nomes de uma só palavra)
    from collections import Counter
    freq = Counter(w for t in textos for w in re.findall(r"[A-Za-z]+", t))
    comuns = set()
    for chave in por_nome:
        if " " in chave or len(chave) < 3:
            continue
        cap, low = freq.get(chave, 0), freq.get(chave.lower(), 0)
        if (low >= 20 and low >= 0.5 * cap) or low >= 100:
            comuns.add(chave)
    arq = RAIZ / "ref" / "municipios_ambiguos.txt"
    manuais = {sem_acento(l.strip()) for l in arq.read_text(encoding="utf-8").splitlines()
               if l.strip() and not l.startswith("#")}
    comuns |= manuais & set(por_nome)
    print(f"{len(comuns)} nomes de município tratados como palavra comum (ex.: {sorted(comuns)[:12]})", flush=True)

    alternativas = sorted(por_nome, key=len, reverse=True)
    padrao = re.compile(r"\b(" + "|".join(map(re.escape, alternativas)) + r")\b")
    uf_ctx = re.compile(r"^\s*(?:[-–,/]\s*|\(\s*)(" + "|".join(UFS) + r")\b")
    estado_ctx = {uf: re.compile(rf"\b{re.escape(sem_acento(n))}\b|[,(\-/]\s*{uf}\b") for uf, n in UFS.items()}
    falso_prefixo = re.compile(r"^\s+do\s+(sul|norte)\b", re.I)   # "Rio Grande do Sul/sul", "do Norte"
    nomes_uf = sorted(map(sem_acento, UFS.values()), key=len, reverse=True)
    estado_por_nome = {sem_acento(v): k for k, v in UFS.items()}
    # estado logo após o nome: "Araioses, Maranhao", "Rio Branco - Acre", "Campo Grande, Estado do Mato Grosso do Sul"
    estado_lado = re.compile(r"^\s*(?:[-–,/(]\s*)?(?:(?:no\s+)?[Ee]stado\s+d[oae]\s+|[Ss]tate\s+of\s+)?("
                             + "|".join(map(re.escape, nomes_uf)) + r")\b")
    municipio_antes = re.compile(r"\b(munic[ií]pios?|cidade|city|municipality|municipio)\s+(de|of)\s+$", re.I)
    descarte_antes = re.compile(r"\b(rio|rios|river|bacia|bacias|fazenda|empresa|cultivar|cultivares|cv\.?|variedade|"
                                r"variedades|raca|racas|breed|sitio|ilha|igarape|riacho|represa|reservatorio|acude|"
                                r"comunidade|pinheiro)\s+(d[oae]s?\s+)?$", re.I)
    # nome científico: gênero seguido de epíteto em minúscula (Theobroma cacao, Araucaria angustifolia)
    FUNCIONAIS = set("de da do das dos e em no na nos nas para por com a o as os ao aos que foi sao se entre sobre "
                     "durante apos ate como pelo pela pelos pelas".split())
    epiteto = re.compile(r"^\s+([a-z]{3,})\b")
    padrao_estado = re.compile(r"\b(" + "|".join(sorted(map(sem_acento, UFS.values()), key=len, reverse=True)) + r")\b")

    mencoes, estados = [], []
    for i, texto in enumerate(textos):
        if not texto:
            continue
        uid = docs.doc_uid.iat[i]
        spans_estado = [m.span() for m in padrao_estado.finditer(texto)]
        for m in padrao.finditer(texto):
            nome, depois = m.group(1), texto[m.end():m.end() + 45]
            antes = texto[max(0, m.start() - 30):m.start()]
            if falso_prefixo.match(depois):
                continue
            # pedaço de nome de estado ("Catarina" em "Santa Catarina")
            if nome not in nomes_estado and any(a <= m.start() and m.end() <= b and (b - a) > len(nome)
                                                for a, b in spans_estado):
                continue
            # rio, bacia, fazenda, empresa, cultivar, raça... ("rios São Francisco", "cultivar São Carlos")
            if descarte_antes.search(antes):
                continue
            cands = por_nome[nome]
            u = uf_ctx.match(depois)
            e_lado = estado_lado.match(depois)
            if u or e_lado:
                uf = u.group(1) if u else estado_por_nome[e_lado.group(1)]
                if not any(c[2] == uf for c in cands):
                    continue                              # "Planaltina, DF" — UF não confere
                c = next(c for c in cands if c[2] == uf)
                conf, motivo = "alta", "UF ao lado" if u else "estado ao lado"
            elif nome in nomes_estado:
                estados.append((uid, nomes_estado[nome]))       # "Goiás", "Paraná"... = estado
                continue
            elif " " not in nome and (e := epiteto.match(depois)) and e.group(1) not in FUNCIONAIS:
                c, conf, motivo = cands[0], "baixa", "provável nome científico"
            else:
                citados = [c for c in cands if estado_ctx[c[2]].search(texto)]
                if municipio_antes.search(antes) and (len(cands) == 1 or len(citados) == 1):
                    c = cands[0] if len(cands) == 1 else citados[0]
                    conf, motivo = "alta", "'município de'"
                elif nome in comuns:
                    c, conf, motivo = cands[0], "baixa", "palavra comum sem contexto"
                elif len(citados) == 1:
                    c, conf, motivo = citados[0], "media", "estado citado no texto"
                else:
                    c, conf, motivo = cands[0], "baixa", "sem contexto geográfico"
            trecho = texto[max(0, m.start() - 60):m.end() + 40].replace("\n", " ")
            mencoes.append((uid, c[0], c[1], c[2], conf, motivo, trecho))
        # menções diretas a estados, no texto ORIGINAL (com acentos): sem acento,
        # "Pará" viraria "Para" e casaria com a preposição no início de frases
        original = originais[i]
        for uf, rx in padroes_estado_orig.items():
            if rx.search(original):
                estados.append((uid, uf))

    # ponto central de cada município (dos contornos do IBGE), para o mapa
    geo = json.load(open(GEO / "br_municipios.geojson", encoding="utf-8"))
    cent = []
    for f in geo["features"]:
        g = f["geometry"]
        aneis = [g["coordinates"][0]] if g["type"] == "Polygon" else [p[0] for p in g["coordinates"]]
        maior = max(aneis, key=len)                   # anel externo do maior polígono
        xs, ys = zip(*[(p[0], p[1]) for p in maior])
        cent.append((f["properties"]["codarea"], float(np.mean(ys)), float(np.mean(xs))))
    centroides = pd.DataFrame(cent, columns=["cod_ibge", "lat", "lon"]).merge(
        mun[["cod_ibge", "municipio", "uf"]], on="cod_ibge", how="left")
    centroides.to_parquet(PROC / "municipio_centroide.parquet", index=False)

    dm = pd.DataFrame(mencoes, columns=["doc_uid", "cod_ibge", "municipio", "uf", "confianca", "motivo", "trecho"])
    dm = dm.drop_duplicates(["doc_uid", "cod_ibge", "confianca"])
    dm.drop(columns="trecho").to_parquet(PROC / "doc_municipio.parquet", index=False)
    de = pd.DataFrame(estados, columns=["doc_uid", "uf"]).drop_duplicates()
    de.to_parquet(PROC / "doc_estado.parquet", index=False)

    # Relatório do piloto ------------------------------------------------------------
    usados = dm[dm.confianca.isin(["alta", "media"])]
    tipo = docs.set_index("doc_uid").tipo_doc
    cob = (usados.drop_duplicates("doc_uid").doc_uid.map(tipo).value_counts() / docs.tipo_doc.value_counts() * 100).round(1)
    cob_uf = (de.drop_duplicates("doc_uid").doc_uid.map(tipo).value_counts() / docs.tipo_doc.value_counts() * 100).round(1)
    amostra = pd.concat([g.sample(min(len(g), 60), random_state=42) for _, g in dm.groupby("confianca")])
    amostra.assign(correto="").to_csv(RAIZ / "relatorios" / "piloto_municipios_amostra.csv", index=False, encoding="utf-8-sig")
    top = usados.groupby(["municipio", "uf"]).doc_uid.nunique().sort_values(ascending=False).head(25)
    linhas = ["# Piloto — municípios e estados citados nos textos", "",
              f"Documentos analisados: {len(docs):,}".replace(",", "."), "",
              "## Menções de municípios por nível de confiança",
              dm.confianca.value_counts().rename_axis("confiança").reset_index(name="menções").to_markdown(index=False), "",
              f"Nomes tratados como palavra comum (só valem com a UF ao lado): {len(comuns)}", "",
              "## Cobertura (% dos documentos com ao menos um município de confiança alta ou média)",
              cob.rename_axis("tipo").reset_index(name="%").to_markdown(index=False), "",
              "## Cobertura por estado (% dos documentos que citam ao menos um estado)",
              cob_uf.rename_axis("tipo").reset_index(name="%").to_markdown(index=False), "",
              "## Municípios mais citados (confiança alta ou média)", top.reset_index(name="documentos").to_markdown(index=False),
              "", f"Amostra para conferência: relatorios/piloto_municipios_amostra.csv · {time.time() - t0:.0f}s"]
    (RAIZ / "relatorios" / "piloto_municipios.md").write_text("\n".join(linhas) + "\n", encoding="utf-8")
    print("\n".join(linhas))


if __name__ == "__main__":
    main()
