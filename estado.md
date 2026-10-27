# Estado do projeto · Observatório de Pesquisa da Embrapa

*Atualizado em 2026-10-27. Atualizar este arquivo ao fim de cada sessão de trabalho.*

## Pessoas e temas no arquivo público (27/10/2026, PR aberto, falta rodar)

- **Pedido da usuária (Rede iAgro):** mostrar "quem trabalha com isso" ao lado do kit de leitura, com nomes
  tirados das publicações e projetos (dado pessoal já público; aprovado por ela em 27/10).
- **`pipeline/py/enriquecimento.py`** passa a gravar também `temas.csv`, `pessoas.csv.gz`,
  `pessoa_produto.csv.gz`, `pessoa_tema.csv.gz` e `evidencias.csv.gz`; `enriquecimento.csv.gz` ganha `tema` e
  `macrotema` (por isso passa a ter quase todos os documentos, não só os com produto ou local).
- **Critério (referendado pela usuária em 27/10):** só vínculos A/B/M e pessoas com unidade; peso projeto liderado 3, solução
  2 (via `pessoa_tecnologia`), publicação/participação 1, metade para documentos com mais de 10 anos; entra quem
  tem ≥ 3 documentos no produto/tema, 1 deles recente; até 5 evidências. Id público = hash do `pessoa_id`
  (`PS` + 10 hex); sem matrícula, contato ou id interno.
- Testado só com dados sintéticos (sessão na nuvem, sem `data/`). **Falta:** `tar_make()` no PC, conferir
  números e publicar `enriquecimento-2026-10` de novo (ou `-2026-11`) com os arquivos novos.

## Frente estratégica: capa e programação (18/10/2026, em andamento)

- **Pedido da usuária:** capa com "Visão geral" e "Visão por programação"; cards com temas e produtos; mapas mais
  bonitos; todo o acervo organizado por objetivos estratégicos **e** por portfólios, com duas leituras lado a lado
  (desde 2024 e todo o acervo).
- **Referências oficiais prontas:** `ref/objetivos_estrategicos.csv` (7 objetivos finalísticos, 38 especificações,
  Plano Diretor 2024–2030, p. 28–34) e `ref/portfolios.csv` (9 portfólios, Portal Embrapa, acesso 18/10/2026);
  gerador `ref/fontes/gerar_ref_programacao.R`. O Plano Diretor não caracteriza portfólios; a ligação
  portfólio × objetivo vem dos desafios (planilha reenviada em 18/10 é idêntica à anterior).
- **Mapa combinado (feito, commit f82c405):** `doc_localizacao` = município citado → estado citado → sede da
  unidade (aproximação). Cobre 99,4% (15,0% município, 12,9% estado, 71,5% sede). Banco `dados-2026-10`
  republicado; o app online só mostra a visão nova depois da troca da `tag`.
- **Teste de classificação direta (18/10, `pipeline/py/programacao_oficial.py`, fora do pipeline):** documento ×
  textos oficiais (38 especificações, 9 portfólios) por SBERT. Não serve: 5 variantes dão ~20% de concordância com
  a via dos desafios (acaso ≈ 11%) e distribuição implausível; nos temas de cultura/praga a similaridade com os
  textos dos portfólios é ≈ 0 (os textos não descrevem cadeias). Proposta à usuária: **tabela tema → portfólio(s)
  e especificação(ões)** (146 temas BERTopic), rascunho do Claude (status: proposta a referendar) validado por ela.
- **Rascunho tema → programação (18/10):** `ref/tema_programacao.csv` (146 temas → portfólio 1/2 e especificação
  1/2, critério, certeza, nota; status "proposta a referendar"), gerador `ref/fontes/tema_programacao_proposta.py`.
  Certeza: 118 alta, 22 média, 6 dúvida. Revisão da usuária em `relatorios/tema_programacao_revisao.xlsx`
  (colunas decisao/correcao/comentario). Pelo portfólio principal, Sistemas de Produção concentra 82.580 docs (44,5%).
- **Revisão aplicada (18/10):** 146 temas referendados; T031 Seringueira corrigida pela usuária → Economia da
  Biodiversidade, O05.1 (moveu 988 docs de Sistemas de Produção; 4 desde 2024).
- **Capa nova (página inicial, `app/paginas/capa.py`):** Visão geral (números, mapa por estado combinado colorível por
  macrotema ou produto, cards de 12 macrotemas e 12 produtos com minigráfico) e Visão por programação (cards dos 7
  objetivos ou 9 portfólios com "todo o acervo" × "desde 2024", secundário, produtos; detalhe com mapa,
  especificações, produtos, temas, unidades, documentos). Banco com `tema_programacao`, `portfolio`, `especificacao`.
- **Nota metodológica:** `documentacao/Capa_e_programacao_2026-10-18.{md,docx}`.
- **Ajustes da capa (18/10, commit af09a55):** filtros Macrotema → Produto (produtos com ≥ 0,5% dos docs do
  macrotema, ordem alfabética sem acento); cards dos grandes temas abrem `temas?macro=M##`. Tema T127 renomeado
  "Mamão e mamona" (BERTopic juntou os dois: 368 de 810 docs são de mamona; produtos marcam certo).
- **Pendente da usuária:** trocar `tag` para `dados-2026-10` nos secrets e Reboot (capa e
  mapa combinado só aparecem online depois disso); token vence 28/10.

## Rodada de outubro e camadas novas (17/10/2026)

- **Exportação 2026-10 processada** (base de pessoas de setembro reaproveitada, com autorização da usuária).
  Volumes (banco do app): 180.951 obras (+3.540; +2,0% sobre 2026-09) · 1.266 soluções (+17) · 3.192 projetos (+1).
  Testes: 11/11. Publicado: release privada `dados-2026-10` e release pública `enriquecimento-2026-10`.
- **Produtos agropecuários** (`doc_produto`): 119.967 documentos com produto principal; 143.678 pares principais e
  28.577 citados. Taxonomia de 104 produtos, base IBGE. Validação aguardando a usuária
  (`relatorios/produtos_validacao_2026-09.xlsx`).
- **Estados** (`doc_estado.fonte`): 51.790 documentos com estado (40.632 citados + 11.741 via município, com
  sobreposição); em 2026-09 eram 40.032 só com citação.
- **Arquivo público de resultados** (`pipeline/py/enriquecimento.py`, target `enriquecimento`) consumido pelos três
  iAgro, já publicados com filtros e etiquetas (iagro-embrapa também com mapa).
- **Correção:** `vetores.py` desalinhava a matriz quando dois documentos tinham texto idêntico (hash repetido no
  cache); agora uma linha por hash.
- **Pendente:**
  1. usuária trocar `tag = "dados-2026-10"` nos Secrets do app do Observatório e dar Reboot; **token vence 28/10**;
  2. rodada de outubro do Florestas Plantadas (pipeline FP, site, app e release das Florestas);
  3. validação da amostra de produtos; termos em inglês para publicações em inglês;
  4. página de produtos/mapa no app Streamlit do Observatório (dados já no banco: `doc_produto`).

## Dados em produção

- **Exportação:** Redape **2026-10** (`EXPORTACAO <- "2026-10"` em `_targets.R`), processada em 17/10/2026.
- **Base:** 180.951 publicações (obras) · 1.266 soluções tecnológicas · 3.192 projetos (185.409 documentos);
  publicações completas (o arquivo truncado de 33 MB foi substituído pelo completo).
- **Banco publicado:** release `dados-2026-10` em danimaciel/observatorio_embrapa_dados (privado); o app ainda aponta para `dados-2026-09` até a troca do Secret.
- **App:** público no Streamlit Community Cloud (código em github.com/danimaciel/observatorio_embrapa).
- Último commit no código: 30/09/2026 ("Programação: leitura por unidade mais clara").

## O que está pronto

- **Pipeline R/{targets}:**
  - ingestão com download automático do Redape e checagem de truncamento;
  - harmonização de unidades (incluindo escritórios do SPM como unidades próprias);
  - resolução de identidade de pessoas;
  - redes entre unidades e pessoas.
- **Camada semântica (Python):**
  - embeddings multilingual-e5-base com cache incremental;
  - documentos semelhantes e proximidade temática entre unidades;
  - temas BERTopic: 146 temas e 25 macrotemas, com nomes revisados.
- **Camada territorial:**
  - sedes das unidades;
  - municípios e estados citados nos textos (precisão de cerca de 98%);
  - biomas.
- **App com 9 páginas:** Embrapa, Unidades, Redes, Mapa, Temas, Programação (aderência aos 107 Desafios para
  Inovação, desde 2024; pública), Pesquisadores, Documentos, Metodologia.
- **Skill `dados-observatorio-embrapa`** (15/10, em `~/.claude/skills/`): contexto e acesso aos dados do
  Observatório em qualquer projeto — atalhos R, busca por significado, dicionário das tabelas e receitas testadas.
- **Documentação:** `documentacao/Observatorio_Pesquisa_Embrapa_Documentacao_2026-09-30.{md,docx}`.

## Pendências

**Urgente:**
- **Token do GitHub vence em 28/10/2026** (`observatorio_embrapa`, fine-grained). Regenerar com prazo maior e
  atualizar os secrets deste app **e** do Observatório das Florestas, que usa o mesmo token.

**Rotina:**
- **Atualização mensal de outubro:** a exportação 2026-10 do Redape já deve estar disponível (publicada todo
  dia 1º). Seguir o roteiro do `README.md`: baixar, copiar a base de pessoas do mês, trocar `EXPORTACAO`,
  `tar_make()`, conferir `relatorios/qualidade_2026-10.md`, publicar `dados-2026-10` e dar Reboot.
  Depois, rodar de novo o pipeline das Florestas e remontar o banco do Observatório das Florestas.

**Decisões da usuária ainda abertas (registradas em 30/09; confirmar se continuam valendo):**
- Programação com os 1.057 projetos atuais da planilha interna ("Projetos embrapa.xlsx"), considerada interna.
  A proposta é um segundo app Streamlit **privado** só com essa página, com convite por e-mail e o banco interno
  como asset separado na release privada. As alternativas são login OIDC ou senha compartilhada.
- Classificação projeto → grupo da taxonomia própria (6 macrogrupos / 18 grupos) via glmnet; falta a
  classificação de referência.
- Conferir `relatorios/programacao_amostra.csv`.
- Revisar os nomes dos temas (`ref/temas_rotulos.csv`).
- Revisar `relatorios/revisao_identidade_2026-09.csv` e preencher `ref/overrides_identidade.csv`.

## Subprojeto

- **Florestas Plantadas FAO** (`Florestas Plantadas FAO/`): estado próprio em `Florestas Plantadas FAO/estado.md`.
  O app derivado, Observatório das Florestas Plantadas, fica na pasta-irmã `../observatorio_florestas`.
