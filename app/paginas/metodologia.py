import streamlit as st

from lib import dados
from lib.dados import RAIZ, q

st.title("Metodologia")
m = dados.meta()

st.markdown(f"""
### Fontes
Exportações do portal da Embrapa ({m['exportacao']}): projetos, publicações (repositórios Alice/Infoteca),
soluções tecnológicas e a base de autores/pessoas da Embrapa. **As publicações são as depositadas nos
repositórios institucionais, não toda a produção científica.**

### Unidade de análise
- **Projeto**, contado pelo ano de início.
- **Obra**: cada unidade deposita seu próprio registro de uma publicação em coautoria. Registros com mesmo
  título, mesmo ano e autores sobrepostos formam uma obra — contada uma vez. Várias unidades depositantes
  são tratadas como evidência declarada de colaboração.
- **Tecnologia**, pelo ano de lançamento.

### Identificação de pesquisadores
Líderes de projeto (nome completo) e autores (assinatura `SOBRENOME, I.`) são associados à base de pessoas:

| Nível | Significado | Usado nas análises |
|---|---|---|
| A | determinístico (candidato único + evidência de unidade) | sim |
| B | desambiguado por iniciais, unidade e coautores, com margem clara | sim |
| M | decisão manual | sim |
| C | ambíguo — vários candidatos Embrapa | não (exibido como *identificação ambígua*) |
| D | sem candidato na base | não (exibido como *autor externo*) |

A afiliação do cadastro é a **atual**. Para não criar colaborações falsas com quem mudou de unidade, a unidade
de um autor numa obra é a unidade depositante quando ela é unidade conhecida da pessoa; senão, a de referência.

### Relações entre unidades
- **Coautoria em publicações**: unidades depositantes + unidades dos autores identificados.
- **Tecnologias (indireta)**: a tecnologia de uma unidade cita publicação com participação de outra.
- **Intensidade**: contagem fracionária (cada documento distribui peso 1 entre seus pares).
- **Força de associação**: razão entre a intensidade observada e a esperada pelo tamanho das unidades.
- Ainda não disponíveis: **projetos** (a exportação traz só o líder, não a equipe) e **proximidade temática**
  (depende do modelo de temas) — esta será mostrada separada da colaboração observada.

### Temas
Provisoriamente, palavras-chave declaradas. Na versão final: embeddings multilíngues (Sentence Transformers) e
BERTopic em dois níveis (macrotema → tema), com rótulos revisados por especialistas.

### Uso responsável
Os indicadores descrevem a atividade de pesquisa; não devem ser usados como *ranking* de pessoas.
""")

rel = RAIZ / "relatorios" / f"qualidade_{m['exportacao']}.md"
if rel.exists():
    with st.expander("Relatório de qualidade da carga"):
        st.markdown(rel.read_text(encoding="utf-8"))
