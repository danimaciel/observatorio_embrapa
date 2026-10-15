# Observatório de Pesquisa da Embrapa — instruções para o Claude

Infraestrutura analítica que integra projetos, publicações, tecnologias, pesquisadores e unidades da Embrapa
(exportações públicas do Redape + base interna de pessoas). Desenho: `docs/01-desenho-do-sistema.md`;
roteiro de atualização mensal: `README.md`.

**Comece lendo `estado.md`** (dados em produção, entregas e pendências) e atualize-o ao fim de cada sessão.

## Ambiente (Windows)

- **R 4.5.1** em `C:/Program Files/R/R-4.5.1/bin` (não está no PATH). Pipeline em R com `{targets}`:
  `targets::tar_make()`. Rodar pelo **PowerShell** ou RStudio: no Git Bash o `sf` (`st_transform`) dá segfault.
- **Python**: `.venv-nlp` só para embeddings, similaridade e temas (`pipeline/py/`); o app usa o Python do sistema.
- **App Streamlit**: `app/app.py` (launch "observatorio", porta 8501). Banco `data/processed/observatorio_app.duckdb`.
- Pipeline completo ~14 min; embeddings em CPU ~3 docs/s (incremental por hash do texto; carga grande → Colab).

## Regras da usuária

- **R preferido**; Python só onde R não serve (embeddings/BERTopic/app).
- **Números**: sempre com a etapa a que pertencem e vindos de um artefato do pipeline, nunca de memória.
  Se um número mudar, dizer explicitamente quanto e por quê.
- **Referências**: toda categoria, taxonomia ou método com fonte e status (oficial / proposta / conhecimento
  do Claude a referendar).
- **Privacidade (LGPD)**: dados brutos e a base de pessoas nunca vão para o git (`data/`, `*.duckdb`, `*.xls*`).
  Matrícula é descartada na leitura. **Resultados analíticos são públicos**; restringir só o dado bruto —
  perguntar "o arquivo bruto ou também os resultados?" antes de esconder algo.
- **Documentar sempre**, com `.docx` além do `.md` quando for documento para outras pessoas
  (`documentacao/`, gerador em `documentacao/ferramentas/`).
- Não re-sortear amostras já rotuladas; rótulos ficam ligados a `doc_uid`.
- SBERT nunca leva stopwords (só os rótulos do BERTopic).

## Publicação

- Código público: github.com/danimaciel/observatorio_embrapa · dados privados: danimaciel/observatorio_embrapa_dados
  (Releases `dados-AAAA-MM` com `observatorio_app.duckdb`). App público no Streamlit Community Cloud.
- Atualizar dados: `tar_make()` → `gh release create dados-AAAA-MM data/processed/observatorio_app.duckdb
  --repo danimaciel/observatorio_embrapa_dados` → trocar `tag` nos secrets → Reboot.
- O token fine-grained `observatorio_embrapa` (lido pelos secrets deste app e do Observatório das Florestas)
  **expira em 28/10/2026**: regenerar e atualizar os secrets dos dois apps.

## Skills do projeto (`.claude/skills/`)

- `dados-observatorio-embrapa` (no perfil da usuária, `~/.claude/skills/`, vale em qualquer pasta) — contexto
  e acesso rápido aos bancos processados: atalhos em R (`obs_con`, `obs_buscar`…), busca SBERT, dicionário e receitas.

- `atualizacao-mensal` — nova exportação do Redape até os dois apps publicados ("atualiza o mês").
- `recorte-tematico` — novo recorte temático no molde de Florestas Plantadas.

## Subprojetos nesta pasta

- `Florestas Plantadas FAO/` — Centro de Referência da FAO em Florestas Plantadas e ILPF (tem seu próprio
  `CLAUDE.md`). O app derivado fica na pasta-irmã `../observatorio_florestas`.
