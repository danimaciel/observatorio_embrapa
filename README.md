# Observatório de Pesquisa da Embrapa

Infraestrutura analítica que integra projetos, publicações, tecnologias, pesquisadores e unidades da Embrapa.
Desenho completo: [docs/01-desenho-do-sistema.md](docs/01-desenho-do-sistema.md).

## Estado atual

Implementadas as fases 1 (ingestão e harmonização) e 2 (resolução de identidade), em R com `{targets}`.

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

## Aplicação (Streamlit)

```bash
pip install -r requirements.txt
streamlit run app/app.py
```

O app só lê `data/processed/observatorio.duckdb`: qualquer revisão (identidade, unidades) entra rodando o
pipeline de novo, sem alterar o app. Páginas: Embrapa · Unidades · Redes · Temas · Pesquisadores · Documentos ·
Metodologia. Links diretos: `/unidades?unidade=solos`, `/pesquisadores?pessoa=PE39798`, `/documentos?doc=OB:160215`.

Temas e similaridade semântica ainda usam palavras-chave como aproximação (fases 3–4 pendentes).

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

## Conceitos principais

- **Obra**: registros da mesma publicação depositados por unidades diferentes (mesmo título e ano, autores sobrepostos) formam uma obra. Contagens de publicações usam obras; várias unidades depositantes = colaboração declarada.
- **Níveis de identificação**: A determinístico · B desambiguado · C ambíguo · D externo · M manual. O app usa A, B e M.
- **Exibição de autores**: identificados pelo nome; externos como `SOBRENOME, I. (autor externo)`; ambíguos como `SOBRENOME, I. (identificação ambígua)`.
- **Unidade do autor na época**: a afiliação do cadastro é atual; quando uma unidade depositante da obra é unidade conhecida da pessoa, usa-se essa.
