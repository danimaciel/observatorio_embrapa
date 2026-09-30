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
- **Publicações em conjunto**: unidades depositantes + unidades dos autores identificados.
- **Tecnologia que usa publicação de outra unidade**: a tecnologia de uma unidade cita publicação com
  participação de outra.
- **Intensidade**: contagem fracionária (cada documento distribui peso 1 entre seus pares).
- **Força de associação**: intensidade observada ÷ esperada pelo tamanho das unidades.
- **Proximidade temática** (separada da colaboração): semelhança entre os perfis de conteúdo das unidades.
  **Colaborações potenciais**: pares muito próximos em conteúdo que colaboram abaixo do esperado.
- Ainda não disponível: relações por **projetos** (a exportação traz só o líder, não a equipe).

### Camada semântica
- **Embeddings**: título + resumo/descrição + palavras-chave de cada projeto, publicação e tecnologia,
  representados pelo modelo multilíngue `intfloat/multilingual-e5-base`. Escolhido numa avaliação com as
  citações declaradas tecnologia → publicação: 87% das publicações citadas aparecem entre as 10 mais
  parecidas num conjunto de 5,3 mil; 69% entre as 177 mil da base.
- **Calibração**: remove-se o vetor médio de cada tipo de documento e idioma, para que projetos,
  publicações e tecnologias — e textos em português e inglês — sobre o mesmo assunto se aproximem.
- **Documentos semelhantes**: os 10 mais parecidos de cada tipo, por cosseno entre os vetores.
- **Temas**: BERTopic (UMAP + HDBSCAN) ajustado numa amostra equilibrada entre os tipos; todos os
  documentos são atribuídos ao tema de centro mais próximo; rótulos pelos termos mais característicos
  (c-TF-IDF). Macrotemas: agrupamento hierárquico dos temas. Os rótulos são automáticos e podem ser
  revisados por especialistas. O modelo é reajustado periodicamente (ex.: anual) para manter os temas
  estáveis entre as atualizações mensais.

### Camada territorial
- **Sedes**: coordenadas do campus-sede de cada unidade (Portal Embrapa).
- **Onde a pesquisa acontece**: municípios citados em título, resumo e palavras-chave, confrontados com a lista
  do IBGE. Só entram menções com contexto geográfico claro — UF ou estado ao lado ("Petrolina, PE"),
  "município de…", ou o estado citado no mesmo texto (~98% de precisão numa amostra conferida). Nomes que
  costumam ser outra coisa (cultivares, espécies, palavras comuns) exigem a UF ao lado.
- **Biomas**: *declarado* — campo Bioma do cadastro de tecnologias; *municípios citados* — bioma predominante
  (maior área) de cada município citado, pelos contornos IBGE 2019.
- O mapa mostra onde a pesquisa é **mencionada**; documentos sem local no texto não aparecem.

### Uso responsável
Os indicadores descrevem a atividade de pesquisa; não devem ser usados como *ranking* de pessoas.
""")

rel = RAIZ / "relatorios" / f"qualidade_{m['exportacao']}.md"
if rel.exists():
    with st.expander("Relatório de qualidade da carga"):
        st.markdown(rel.read_text(encoding="utf-8"))
