# Observatório de Pesquisa da Embrapa

Infraestrutura analítica que integra projetos, publicações, tecnologias, pesquisadores e unidades da Embrapa.
Desenho completo: [docs/01-desenho-do-sistema.md](docs/01-desenho-do-sistema.md).

## Estado atual

Implementados: ingestão e harmonização, resolução de identidade, redes entre unidades e pessoas (R com
`{targets}`); camada semântica — similaridade e temas (Python); camada territorial — municípios e estados
citados nos textos e biomas; app Streamlit publicado.

## Atualização mensal (roteiro)

Tudo abaixo é incremental: só o que mudou é recalculado.

1. `Rscript pipeline/baixar_dados.R AAAA-MM` — baixa as três exportações do Redape (e, numa instalação nova,
   as malhas do IBGE e dos biomas).
2. Copiar `AutorPessoalEmbrapa.xls` do mês para `data/raw/AAAA-MM/` (base interna).
3. Trocar `EXPORTACAO` em `_targets.R` e rodar `targets::tar_make()` (no RStudio ou PowerShell; no Git Bash
   o pacote `sf` pode falhar). O pipeline **para com mensagem clara** se um arquivo vier truncado, se faltar
   coluna ou se aparecer unidade sem mapeamento (incluir em `ref/unidade_alias.csv`; unidade nova também
   precisa de linha em `ref/unidade.csv` e `ref/unidade_localizacao.csv`).
4. Conferir `relatorios/qualidade_AAAA-MM.md`.
5. Publicar o banco (seção *Publicação*) e dar *Reboot* no app.

Periodicamente (ex.: uma vez por ano): reajustar os temas (`temas.py --reajustar`) e revisar os rótulos.

## Como executar

1. Baixe as exportações do mês direto do Redape (projetos, publicações e tecnologias, publicadas todo dia 1º):
   ```bash
   Rscript pipeline/baixar_dados.R 2026-10
   ```
   O download retoma sozinho se a conexão cair e só aceita o arquivo com o tamanho informado pelo Redape.
   Rodar de novo é seguro: arquivos já completos não são baixados outra vez.
2. Copie a base de pessoas (`AutorPessoalEmbrapa.xls`, interna, não está no Redape) para `data/raw/<AAAA-MM>/`.
3. Ajuste `EXPORTACAO` em `_targets.R`.
4. No R: `targets::tar_make()`. Arquivo truncado interrompe o pipeline.
5. Testes: `Rscript tests/testthat.R`.

Fontes no Redape: projetos [doi:10.48432/EZDXWF](https://doi.org/10.48432/EZDXWF) ·
publicações [doi:10.48432/TRBT0S](https://doi.org/10.48432/TRBT0S) ·
tecnologias [doi:10.48432/ZQE5FV](https://doi.org/10.48432/ZQE5FV).

Pacotes: `dplyr tidyr stringr stringi readr readxl purrr igraph arrow duckdb DBI janitor targets testthat`.

## Camada semântica (embeddings, similaridade e temas)

Roda dentro do `tar_make()` (passos em Python, ambiente `.venv-nlp`, ver `pipeline/py/requirements-nlp.txt`):

- `embeddings.py` — vetores `multilingual-e5-base` com cache por hash do texto: só documentos novos ou
  alterados são calculados (CPU local ~3 docs/s; a carga inicial foi feita no Colab com GPU, via
  `pipeline/colab/embeddings_colab.ipynb` + `exportar_textos.py`).
- `similaridade.py` — 10 documentos mais semelhantes de cada tipo e proximidade temática entre unidades.
- `temas.py` — atribui os documentos aos temas salvos. Para **reajustar** o modelo (ex.: uma vez por ano):
  `.venv-nlp/Scripts/python pipeline/py/temas.py --reajustar`.
- Rótulos dos temas: `relatorios/temas_para_curadoria.csv` lista todos os temas; para renomear, copie
  `tema_id` e o novo `rotulo` para `ref/temas_rotulos.csv`.
- Avaliação dos modelos: `relatorios/avaliacao_modelos.md`.

## Aplicação (Streamlit)

```bash
pip install -r requirements.txt
streamlit run app/app.py
```

O app só lê `data/processed/observatorio_app.duckdb`: qualquer revisão (identidade, unidades) entra rodando o
pipeline de novo, sem alterar o app. Páginas: Embrapa · Unidades · Redes · Mapa · Temas · Pesquisadores ·
Documentos · Metodologia. Links diretos: `/unidades?unidade=solos`, `/pesquisadores?pessoa=PE39798`,
`/documentos?doc=OB:160215`.

## Programação (página Programação)

`pipeline/py/programacao.py` compara cada documento desde 2024 aos 107 Desafios para Inovação
(`ref/programacao_desafios.csv`: desafio → portfólio, objetivo, meta, ODS) por similaridade SBERT; guarda os 3
mais aderentes com confiança alta/média/baixa. Os **resultados** são públicos no app; a planilha da programação
é interna e não está no repositório (copie-a para `ref/` antes de rodar o pipeline). Amostra para conferência:
`relatorios/programacao_amostra.csv` (coluna `correto`). Nova versão da programação: substituir o CSV e rodar.

## Camada territorial (página Mapa)

- **Sedes das unidades**: coordenadas em `ref/unidade_localizacao.csv`.
- **Onde a pesquisa acontece** (`pipeline/py/municipios.py`): municípios e estados citados em título, resumo e
  palavras-chave, com nível de confiança pelo contexto (UF ao lado, "município de…", estado citado). O app usa
  só confiança alta e média. Nomes que costumam ser outra coisa (cultivar, espécie) ficam em
  `ref/municipios_ambiguos.txt`. Relatório: `relatorios/piloto_municipios.md`.
- **Biomas** (`pipeline/R/biomas.R`): bioma declarado das tecnologias e bioma predominante (maior área) dos
  municípios citados. Contornos IBGE 2019 via geobr/IPEA; `app/assets/br_biomas.geojson` é gerado pelo pipeline.

## Publicação (Streamlit Community Cloud)

O código é público; o banco do app fica numa Release do repositório **privado**
`danimaciel/observatorio_embrapa_dados` e é baixado quando o app inicia.

1. **Token de leitura** (uma vez): GitHub → Settings → Developer settings → *Fine-grained tokens* →
   acesso **apenas** ao repositório `observatorio_embrapa_dados`, permissão *Contents: Read-only*.
2. **Criar o app** em share.streamlit.io: repositório `danimaciel/observatorio_embrapa`, branch `main`,
   arquivo principal `app/app.py`, Python 3.12.
3. **Secrets** (Advanced settings → Secrets):
   ```toml
   [dados]
   repo = "danimaciel/observatorio_embrapa_dados"
   tag = "dados-2026-09"
   arquivo = "observatorio_app.duckdb"
   token = "<token do passo 1>"
   ```

**Atualizar os dados** (nova exportação ou revisão de identidade): rodar `targets::tar_make()`, publicar o banco
numa nova Release e trocar `tag` nos secrets (o app reinicia e baixa a nova versão):

```bash
gh release create dados-AAAA-MM data/processed/observatorio_app.duckdb --repo danimaciel/observatorio_embrapa_dados --title "Dados AAAA-MM"
```

O banco publicado (`observatorio_app.duckdb`) contém só o que o app usa: não inclui matrícula, situação
funcional nem a base de autores.

## Revisão de identidade

`relatorios/revisao_identidade_<AAAA-MM>.csv` agrupa as menções ambíguas por assinatura + unidade, ordenadas
por frequência, com os candidatos (nome, unidade, id, pontuação). Preencha `pessoa_id` (ou `EXTERNO`) e copie as
6 primeiras colunas da linha para `ref/overrides_identidade.csv`. Com `unidade_doc` preenchida, a decisão vale para
todos os documentos daquela unidade; com `doc_uid`, só para aquele documento.

## Saídas

- `data/processed/*.parquet` e `data/processed/observatorio.duckdb` — tabelas do modelo de dados.
- `relatorios/qualidade_<AAAA-MM>.md` — integridade, volumes e níveis de identificação.
- `relatorios/auditoria_identidade_<AAAA-MM>.csv` — amostra para conferência manual (coluna `correto`).

## Curadoria (`ref/`)

| Arquivo | Conteúdo |
|---|---|
| `unidade.csv` | unidades, sigla histórica, categoria, UF (`confirmar = S` indica sigla a validar) |
| `unidade_alias.csv` | nomes antigos, grafias e siglas de unidades centrais → `unidade_id` |
| `tipo_publicacao.csv` | tipo de publicação → grupo analítico |
| `overrides_identidade.csv` | decisões manuais de identidade (`pessoa_id` ou `EXTERNO`), aplicadas a cada carga |
| `unidade_localizacao.csv` | município e coordenadas da sede de cada unidade |
| `municipios_ambiguos.txt` | nomes de município que só contam com a UF ao lado |
| `stopwords_pt.txt` | palavras ignoradas nos rótulos automáticos dos temas |
| `temas_rotulos.csv` | rótulos curados dos temas (`tema_id`, `rotulo`) |

## Conceitos principais

- **Obra**: registros da mesma publicação depositados por unidades diferentes (mesmo título e ano, autores sobrepostos) formam uma obra. Contagens de publicações usam obras; várias unidades depositantes = colaboração declarada.
- **Níveis de identificação**: A determinístico · B desambiguado · C ambíguo · D externo · M manual. O app usa A, B e M.
- **Exibição de autores**: identificados pelo nome; externos como `SOBRENOME, I. (autor externo)`; ambíguos como `SOBRENOME, I. (identificação ambígua)`.
- **Unidade do autor na época**: a afiliação do cadastro é atual; quando uma unidade depositante da obra é unidade conhecida da pessoa, usa-se essa.
