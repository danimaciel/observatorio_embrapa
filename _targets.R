# Pipeline do Observatório de Pesquisa da Embrapa — fases 1 e 2
# (ingestão, harmonização e resolução de identidade)
# Executar com: targets::tar_make()

library(targets)

tar_option_set(packages = c("dplyr", "tidyr", "stringr", "stringi", "readr", "readxl",
                            "purrr", "igraph", "arrow", "duckdb", "DBI", "janitor"))
tar_source("pipeline/R")

EXPORTACAO <- "2026-09"
# Arquivo truncado interrompe o pipeline. Use TRUE apenas para testes com
# uma exportação sabidamente incompleta (o último registro é descartado).
PERMITIR_TRUNCADO <- FALSE

list(
  # Arquivos de origem e referência (reprocessam quando mudam) ----------------
  tar_target(arq_projetos, caminho_raw(EXPORTACAO, "projetos"), format = "file"),
  tar_target(arq_publicacoes, caminho_raw(EXPORTACAO, "publicacoes"), format = "file"),
  tar_target(arq_tecnologias, caminho_raw(EXPORTACAO, "tecnologias"), format = "file"),
  tar_target(arq_autores, caminho_raw(EXPORTACAO, "autores"), format = "file"),
  tar_target(arq_ref_unidade, "ref/unidade.csv", format = "file"),
  tar_target(arq_ref_alias, "ref/unidade_alias.csv", format = "file"),
  tar_target(arq_ref_tipo_pub, "ref/tipo_publicacao.csv", format = "file"),
  tar_target(arq_ref_overrides, "ref/overrides_identidade.csv", format = "file"),
  tar_target(arq_ref_localizacao, "ref/unidade_localizacao.csv", format = "file"),

  # Fase 1 — ingestão ------------------------------------------------------------
  tar_target(raw_projetos, ler_csv_exportacao(arq_projetos, PERMITIR_TRUNCADO)),
  tar_target(raw_publicacoes, ler_csv_exportacao(arq_publicacoes, PERMITIR_TRUNCADO)),
  tar_target(raw_tecnologias, ler_csv_exportacao(arq_tecnologias, PERMITIR_TRUNCADO)),
  tar_target(raw_autores, ler_autores(arq_autores)),
  tar_target(ref_unidade, readr::read_csv(arq_ref_unidade, col_types = readr::cols(.default = "c"))),
  tar_target(ref_alias, readr::read_csv(arq_ref_alias, col_types = readr::cols(.default = "c"))),
  tar_target(ref_tipo_pub, readr::read_csv(arq_ref_tipo_pub, col_types = readr::cols(.default = "c"))),
  tar_target(ref_overrides, readr::read_csv(arq_ref_overrides, col_types = readr::cols(.default = "c"))),
  tar_target(unidade_localizacao, readr::read_csv(arq_ref_localizacao, show_col_types = FALSE,
                                                  col_types = readr::cols(lat = "d", lon = "d", .default = "c"))),

  # Fase 1 — harmonização ----------------------------------------------------------
  tar_target(unidade_alias, montar_unidade_alias(ref_unidade, ref_alias)),
  tar_target(projeto, preparar_projetos(raw_projetos, unidade_alias)),
  tar_target(publicacao_base, preparar_publicacoes(raw_publicacoes, unidade_alias, ref_tipo_pub)),
  tar_target(obra_map, agrupar_obras(publicacao_base)),
  tar_target(publicacao, dplyr::left_join(publicacao_base, obra_map, by = "doc_uid")),
  tar_target(obra, montar_obras(publicacao)),
  tar_target(tecnologia, preparar_tecnologias(raw_tecnologias, unidade_alias)),
  tar_target(doc_keyword, montar_doc_keyword(projeto, publicacao, tecnologia)),
  tar_target(doc_link, montar_doc_link(tecnologia, publicacao)),
  tar_target(doc_unidade_declarada, montar_doc_unidade_declarada(projeto, publicacao, tecnologia)),

  # Fase 2 — identidade ------------------------------------------------------------
  tar_target(pessoas, consolidar_pessoas(raw_autores, unidade_alias, ref_unidade)),
  tar_target(lideres, resolver_lideres(projeto, pessoas)),
  tar_target(pessoa_unidade, montar_pessoa_unidade(pessoas, lideres, projeto)),
  tar_target(autorias, resolver_autorias(publicacao, pessoas, pessoa_unidade)),
  tar_target(doc_pessoa_bruto, aplicar_overrides(dplyr::bind_rows(lideres, autorias), ref_overrides,
                                                 doc_unidade_declarada)),
  tar_target(pessoa, finalizar_pessoas(pessoas, doc_pessoa_bruto, publicacao, projeto)),
  tar_target(doc_pessoa, rotular_mencoes(doc_pessoa_bruto, pessoa)),
  tar_target(doc_unidade, dplyr::bind_rows(doc_unidade_declarada,
                                           doc_unidade_autores(doc_pessoa, pessoa, publicacao))),

  # Tabelas analíticas para o app ------------------------------------------------------
  tar_target(documento, montar_documento(projeto, obra, publicacao, tecnologia)),
  tar_target(documento_unidade, montar_documento_unidade(doc_unidade, publicacao)),
  tar_target(documento_pessoa, montar_documento_pessoa(doc_pessoa, publicacao)),
  tar_target(documento_keyword, montar_documento_keyword(doc_keyword, publicacao)),
  tar_target(aresta_unidade, montar_aresta_unidade(documento, documento_unidade, doc_link, publicacao)),
  tar_target(aresta_pessoa, montar_aresta_pessoa(documento_pessoa, doc_pessoa, documento, publicacao)),
  tar_target(pessoa_tecnologia, montar_pessoa_tecnologia(doc_link, documento_pessoa, publicacao)),
  tar_target(meta, montar_meta(EXPORTACAO, list(projetos = raw_projetos, publicacoes = raw_publicacoes,
                                                tecnologias = raw_tecnologias))),

  # Produtos -------------------------------------------------------------------------
  tar_target(parquets, salvar_parquet(list(
    meta = meta,
    documento_pessoa = documento_pessoa,
    aresta_unidade = aresta_unidade,
    aresta_pessoa = aresta_pessoa,
    pessoa_tecnologia = pessoa_tecnologia,
    unidade = ref_unidade,
    unidade_localizacao = unidade_localizacao,
    unidade_alias = dplyr::select(unidade_alias, alias, unidade_id, tipo),
    projeto = projeto,
    obra = obra,
    tecnologia = tecnologia,
    pessoa = pessoa,
    autor_registro = pessoas$registro,
    doc_pessoa = doc_pessoa,
    doc_unidade = doc_unidade,
    doc_keyword = doc_keyword
  ), "data/processed"), format = "file"),
  # Tabelas lidas pelos passos em Python: separadas para que mudanças em outras
  # tabelas não refaçam embeddings, similaridade e temas.
  tar_target(parquets_semantica, salvar_parquet(list(
    documento = documento,
    documento_unidade = documento_unidade,
    documento_keyword = documento_keyword,
    publicacao = publicacao,
    doc_link = doc_link
  ), "data/processed"), format = "file"),
  tar_target(duckdb_file, construir_duckdb(c(parquets, parquets_semantica), "data/processed/observatorio.duckdb"),
             format = "file"),
  # Fase 3–4 — camada semântica (Python) ---------------------------------------------
  # Embeddings incrementais: só documentos novos ou alterados são calculados.
  tar_target(embeddings, rodar_python(
    "pipeline/py/embeddings.py",
    saidas = c("data/interim/embeddings/e5-base.npy", "data/interim/embeddings/e5-base_ids.parquet"),
    dep = parquets_semantica), format = "file"),
  tar_target(semantica_similaridade, rodar_python(
    "pipeline/py/similaridade.py",
    saidas = c("data/processed/similaridade.parquet", "data/processed/proximidade_unidade.parquet"),
    dep = list(embeddings, parquets_semantica)), format = "file"),   # proximidade usa documento_unidade
  tar_target(arq_ref_stopwords, "ref/stopwords_pt.txt", format = "file"),
  tar_target(arq_ref_temas_rotulos, "ref/temas_rotulos.csv", format = "file"),
  # Temas: atribuição aos temas salvos; reajuste só com
  # `python pipeline/py/temas.py --reajustar` (ex.: anual).
  tar_target(semantica_temas, rodar_python(
    "pipeline/py/temas.py",
    saidas = c("data/processed/tema.parquet", "data/processed/doc_tema.parquet"),
    dep = list(embeddings, arq_ref_stopwords, arq_ref_temas_rotulos)), format = "file"),

  # Municípios e estados citados nos textos (mapa territorial)
  tar_target(arq_ref_municipios_ambiguos, "ref/municipios_ambiguos.txt", format = "file"),
  tar_target(arq_geo, c("data/raw/geo/municipios_ibge.json", "data/raw/geo/br_municipios.geojson"), format = "file"),
  tar_target(semantica_municipios, rodar_python(
    "pipeline/py/municipios.py",
    saidas = c("data/processed/doc_municipio.parquet", "data/processed/doc_estado.parquet",
               "data/processed/municipio_centroide.parquet"),
    dep = list(parquets_semantica, arq_ref_municipios_ambiguos, arq_geo)), format = "file"),

  # Biomas: declarados nas tecnologias + bioma predominante dos municípios citados
  tar_target(arq_biomas, "data/raw/geo/biomas_2019_simplificado.gpkg", format = "file"),
  tar_target(bioma_mun, bioma_municipio(arq_biomas, arq_geo[grepl("br_municipios", arq_geo)])),
  tar_target(parquets_biomas, salvar_parquet(list(
    doc_bioma = montar_doc_bioma(tecnologia, semantica_municipios[grepl("doc_municipio", semantica_municipios)],
                                 bioma_mun)
  ), "data/processed"), format = "file"),
  tar_target(geo_biomas_app, exportar_geo_biomas(arq_biomas, "app/assets/br_biomas.geojson"), format = "file"),

  # Programação da Embrapa: aderência aos Desafios para Inovação (conteúdo desde 2024).
  # Uso interno: fica em observatorio_local.duckdb, fora do banco publicado.
  tar_target(arq_ref_desafios, "ref/programacao_desafios.csv", format = "file"),
  tar_target(semantica_programacao, rodar_python(
    "pipeline/py/programacao.py",
    saidas = c("data/processed/desafio.parquet", "data/processed/doc_desafio.parquet"),
    dep = list(embeddings, parquets_semantica, arq_ref_desafios)), format = "file"),

  tar_target(duckdb_local, construir_duckdb_local(semantica_programacao, "data/processed/observatorio_local.duckdb"),
             format = "file"),

  tar_target(duckdb_app, construir_duckdb_app(c(parquets, parquets_semantica, semantica_similaridade, semantica_temas,
                                                semantica_municipios, parquets_biomas),
                                              "data/processed/observatorio_app.duckdb"),
             format = "file"),
  tar_target(auditoria, amostra_auditoria(doc_pessoa, pessoa, publicacao, projeto,
                                          sprintf("relatorios/auditoria_identidade_%s.csv", EXPORTACAO)),
             format = "file"),
  tar_target(revisao, revisao_identidade(doc_pessoa, pessoa, doc_unidade_declarada, publicacao, projeto,
                                         sprintf("relatorios/revisao_identidade_%s.csv", EXPORTACAO)),
             format = "file"),
  tar_target(relatorio, relatorio_qualidade(
    EXPORTACAO,
    list(projetos = raw_projetos, publicacoes = raw_publicacoes, tecnologias = raw_tecnologias),
    projeto, publicacao, obra, tecnologia, doc_link, doc_pessoa, doc_unidade, pessoa,
    sprintf("relatorios/qualidade_%s.md", EXPORTACAO)
  ), format = "file")
)
