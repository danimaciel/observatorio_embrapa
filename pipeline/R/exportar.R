# Gravação dos produtos de dados e relatório de qualidade ----------------------

salvar_parquet <- function(tabelas, dir) {
  dir.create(dir, recursive = TRUE, showWarnings = FALSE)
  paths <- file.path(dir, paste0(names(tabelas), ".parquet"))
  purrr::walk2(tabelas, paths, function(t, p) arrow::write_parquet(t, p))
  paths
}

construir_duckdb <- function(parquets, db_path) {
  if (file.exists(db_path)) file.remove(db_path)
  con <- DBI::dbConnect(duckdb::duckdb(), db_path)
  on.exit(DBI::dbDisconnect(con, shutdown = TRUE))
  for (p in parquets) {
    nm <- tools::file_path_sans_ext(basename(p))
    DBI::dbExecute(con, sprintf("CREATE TABLE %s AS SELECT * FROM read_parquet('%s')",
                                nm, normalizePath(p, winslash = "/")))
  }
  db_path
}

# Banco publicado com o app: só tabelas e colunas que o app consome.
# Ficam de fora dados funcionais (situação ativo/inativo, afiliação no
# cadastro, registros da base de autores) e detalhes internos da identificação.
TABELAS_APP <- list(
  meta = "*",
  unidade = "*",
  unidade_localizacao = "unidade_id, municipio, uf, lat, lon",
  documento = "*",
  documento_unidade = "*",
  documento_pessoa = "*",
  documento_keyword = "*",
  aresta_unidade = "*",
  aresta_pessoa = "*",
  pessoa_tecnologia = "*",
  doc_link = "*",
  pessoa = "pessoa_id, nome_exibicao, assinatura_principal, unidade_ref_id, n_obras, n_projetos_lider",
  doc_pessoa = "doc_uid, papel, ordem, rotulo_exibicao, nivel, pessoa_id",
  publicacao = "doc_uid, obra_id, unidade_id, tipo, url_repositorio",
  # camada semântica (Python: pipeline/py/)
  similaridade = "*",
  proximidade_unidade = "*",
  tema = "*",
  doc_tema = "*",
  # territorial: só menções de confiança alta ou média entram no app
  doc_municipio = list(colunas = "doc_uid, cod_ibge, municipio, uf, confianca",
                       filtro = "confianca IN ('alta', 'media')"),
  doc_estado = "*",
  municipio_centroide = "*",
  doc_bioma = "*"
)

construir_duckdb_app <- function(parquets, db_path) {
  if (file.exists(db_path)) file.remove(db_path)
  por_nome <- stats::setNames(parquets, tools::file_path_sans_ext(basename(parquets)))
  con <- DBI::dbConnect(duckdb::duckdb(), db_path)
  on.exit(DBI::dbDisconnect(con, shutdown = TRUE))
  for (nm in names(TABELAS_APP)) {
    def <- TABELAS_APP[[nm]]
    colunas <- if (is.list(def)) def$colunas else def
    filtro <- if (is.list(def) && !is.null(def$filtro)) paste(" WHERE", def$filtro) else ""
    DBI::dbExecute(con, sprintf("CREATE TABLE %s AS SELECT %s FROM read_parquet('%s')%s",
                                nm, colunas, normalizePath(por_nome[[nm]], winslash = "/"), filtro))
  }
  DBI::dbExecute(con, "CHECKPOINT")
  db_path
}

# Amostra estratificada por nível para conferência manual. Preencha a coluna
# "correto" (S/N) e registre correções em ref/overrides_identidade.csv.
amostra_auditoria <- function(doc_pessoa, pessoa, publicacao, projeto, path, n = 50, semente = 42) {
  docs <- dplyr::bind_rows(
    dplyr::select(publicacao, doc_uid, titulo, unidade_doc = unidade_id, ano),
    dplyr::select(projeto, doc_uid, titulo, unidade_doc = unidade_lider_id, ano = ano_inicio)
  )
  set.seed(semente)
  am <- doc_pessoa |>
    dplyr::filter(nivel %in% c("A", "B", "C")) |>
    dplyr::group_by(papel, nivel) |>
    dplyr::slice_sample(n = n) |>
    dplyr::ungroup() |>
    dplyr::left_join(docs, by = "doc_uid") |>
    dplyr::left_join(dplyr::select(pessoa, pessoa_id, nome_atribuido = nome_exibicao,
                                   unidade_pessoa = unidade_ref_id), by = "pessoa_id") |>
    dplyr::mutate(candidatos = formatar_candidatos(candidatos, pessoa)) |>
    dplyr::transmute(papel, nivel, doc_uid, ano, titulo, unidade_doc, nome_origem,
                     pessoa_id, nome_atribuido, unidade_pessoa, score, candidatos, correto = "")
  readr::write_excel_csv(am, path)
  path
}

# "PE1:6;PE2:3" -> "Ana Silva [semiarido] (PE1) 6 pts | Antonio Silva [solos] (PE2) 3 pts"
formatar_candidatos <- function(candidatos, pessoa) {
  if (all(is.na(candidatos))) return(candidatos)
  x <- tibble::tibble(i = seq_along(candidatos), c = strsplit(dplyr::coalesce(candidatos, ""), ";")) |>
    tidyr::unnest_longer(c) |>
    dplyr::filter(nzchar(c)) |>
    tidyr::separate_wider_delim(c, ":", names = c("pessoa_id", "pts")) |>
    dplyr::left_join(dplyr::select(pessoa, pessoa_id, nome_exibicao, unidade_ref_id), by = "pessoa_id") |>
    dplyr::mutate(txt = sprintf("%s [%s] (%s) %s pts", nome_exibicao, unidade_ref_id, pessoa_id, pts)) |>
    dplyr::group_by(i) |>
    dplyr::summarise(txt = paste(txt, collapse = " | "), .groups = "drop")
  out <- rep(NA_character_, length(candidatos))
  out[x$i] <- x$txt
  out
}

# Menções não resolvidas agrupadas por assinatura + unidade do documento,
# ordenadas por frequência: cada decisão resolve várias menções de uma vez.
# Para aplicar: preencha pessoa_id (ou EXTERNO) e copie as 6 primeiras colunas
# da linha para ref/overrides_identidade.csv. Este arquivo é regerado a cada carga.
revisao_identidade <- function(doc_pessoa, pessoa, doc_unidade_declarada, publicacao, projeto, path) {
  un_doc <- dplyr::distinct(doc_unidade_declarada, doc_uid, .keep_all = TRUE) |>
    dplyr::select(doc_uid, unidade_doc = unidade_id)
  titulos <- dplyr::bind_rows(dplyr::select(publicacao, doc_uid, titulo),
                              dplyr::select(projeto, doc_uid, titulo))
  pend <- doc_pessoa |>
    dplyr::filter(nivel == "C" | (papel == "lider" & nivel == "D")) |>
    dplyr::left_join(un_doc, by = "doc_uid") |>
    dplyr::left_join(titulos, by = "doc_uid")
  cand <- pend |>
    dplyr::filter(!is.na(candidatos)) |>
    dplyr::select(papel, nome_origem, unidade_doc, candidatos) |>
    dplyr::mutate(c = strsplit(candidatos, ";")) |>
    tidyr::unnest_longer(c) |>
    tidyr::separate_wider_delim(c, ":", names = c("pessoa_id", "pts")) |>
    dplyr::group_by(papel, nome_origem, unidade_doc, pessoa_id) |>
    dplyr::summarise(pts = max(as.numeric(pts)), .groups = "drop") |>
    dplyr::arrange(dplyr::desc(pts)) |>
    dplyr::group_by(papel, nome_origem, unidade_doc) |>
    dplyr::summarise(candidatos = paste0(pessoa_id, ":", pts, collapse = ";"), .groups = "drop")
  rev <- pend |>
    dplyr::group_by(papel, nome_origem, unidade_doc) |>
    dplyr::summarise(n_mencoes = dplyr::n(),
                     exemplos = paste(utils::head(unique(titulo), 2), collapse = " || "),
                     .groups = "drop") |>
    dplyr::left_join(cand, by = c("papel", "nome_origem", "unidade_doc")) |>
    dplyr::arrange(dplyr::desc(n_mencoes)) |>
    dplyr::transmute(contexto = papel, doc_uid = "", nome_origem, unidade_doc,
                     pessoa_id = "", nota = "", n_mencoes,
                     candidatos = formatar_candidatos(candidatos, pessoa), exemplos)
  readr::write_excel_csv(rev, path)
  path
}

relatorio_qualidade <- function(exportacao, brutos, projeto, publicacao, obra, tecnologia,
                                doc_link, doc_pessoa, doc_unidade, pessoa, path) {
  pct <- function(x) sprintf("%.1f%%", 100 * x)
  trunc <- vapply(brutos, function(b) isTRUE(attr(b, "truncado")), logical(1))
  niveis <- doc_pessoa |>
    dplyr::count(papel, nivel) |>
    dplyr::group_by(papel) |>
    dplyr::mutate(pct = pct(n / sum(n))) |>
    dplyr::ungroup()
  tabela_md <- function(df) {
    c(paste0("| ", paste(names(df), collapse = " | "), " |"),
      paste0("|", paste(rep("---", ncol(df)), collapse = "|"), "|"),
      apply(df, 1, function(r) paste0("| ", paste(r, collapse = " | "), " |")))
  }
  multi <- dplyr::filter(obra, n_unidades_depositantes > 1)
  pubs_multi_aut <- doc_unidade |>
    dplyr::filter(papel %in% c("depositante", "afiliacao_autor")) |>
    dplyr::inner_join(dplyr::select(publicacao, doc_uid, obra_id), by = "doc_uid") |>
    dplyr::group_by(obra_id) |>
    dplyr::summarise(n_un = dplyr::n_distinct(unidade_id), .groups = "drop")

  linhas <- c(
    sprintf("# Relatório de qualidade — exportação %s", exportacao),
    sprintf("Gerado em %s.", format(Sys.time(), "%Y-%m-%d %H:%M")),
    "",
    "## Integridade dos arquivos",
    if (any(trunc)) paste0("- ⚠️ **Truncado:** ", paste(names(brutos)[trunc], collapse = ", "),
                           " — último registro incompleto descartado. Reexportar.")
    else "- Todos os arquivos íntegros.",
    "",
    "## Volumes",
    sprintf("- Projetos: %d (%d–%d)", nrow(projeto), min(projeto$ano_inicio, na.rm = TRUE), max(projeto$ano_inicio, na.rm = TRUE)),
    sprintf("- Publicações: %d registros → %d obras (%d–%d)", nrow(publicacao), nrow(obra),
            min(publicacao$ano, na.rm = TRUE), max(publicacao$ano, na.rm = TRUE)),
    sprintf("- Tecnologias: %d", nrow(tecnologia)),
    sprintf("- Pessoas (base consolidada): %d", nrow(pessoa)),
    "",
    "## Publicações depositadas por mais de uma unidade",
    sprintf("- Obras com registros de ≥ 2 unidades depositantes: %d", nrow(multi)),
    sprintf("- Obras com ≥ 2 unidades (depositantes + afiliação dos autores na época): %d", sum(pubs_multi_aut$n_un > 1)),
    sprintf("- Registros sem resumo (texto curto): %s", pct(mean(publicacao$texto_curto))),
    sprintf("- Tipos de publicação não classificados: %d", sum(publicacao$tipo_grupo == "nao_classificado")),
    "",
    "## Vínculos declarados tecnologia → publicação",
    sprintf("- %d vínculos em %d tecnologias; %d apontam para publicações presentes na base",
            nrow(doc_link), dplyr::n_distinct(doc_link$origem_uid), sum(doc_link$destino_na_base)),
    "",
    "## Resolução de identidade",
    "A = determinístico · B = desambiguado · C = ambíguo · D = externo/sem candidato · M = manual",
    "",
    tabela_md(niveis)
  )
  dir.create(dirname(path), recursive = TRUE, showWarnings = FALSE)
  writeLines(linhas, path, useBytes = FALSE)
  path
}
