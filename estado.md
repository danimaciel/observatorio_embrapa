# Estado do projeto · Observatório de Pesquisa da Embrapa

*Atualizado em 2026-10-15. Atualizar este arquivo ao fim de cada sessão de trabalho.*

## Dados em produção

- **Exportação:** Redape **2026-09** (`EXPORTACAO <- "2026-09"` em `_targets.R`), processada em 28/09/2026.
- **Base:** 177.411 publicações · 1.249 soluções tecnológicas · 3.191 projetos (181.851 documentos);
  publicações completas (o arquivo truncado de 33 MB foi substituído pelo completo).
- **Banco publicado:** release `dados-2026-09` em danimaciel/observatorio_embrapa_dados (privado).
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
