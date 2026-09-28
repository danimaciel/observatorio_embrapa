# Unidades, documentos canônicos e vínculos declarados -----------------------

chave_unidade <- function(x) norm_nome(x)

# Tabela alias -> unidade_id: nomes atuais e siglas de ref/unidade.csv
# mais os aliases curados de ref/unidade_alias.csv.
montar_unidade_alias <- function(unidade, alias_extra) {
  dplyr::bind_rows(
    dplyr::transmute(unidade, alias = nome_atual, unidade_id, tipo = "nome"),
    dplyr::transmute(unidade, alias = sigla_historica, unidade_id, tipo = "sigla"),
    dplyr::transmute(alias_extra, alias, unidade_id, tipo = "alias")
  ) |>
    dplyr::mutate(chave = chave_unidade(alias)) |>
    dplyr::distinct(chave, .keep_all = TRUE)
}

# Mapeia nomes/siglas para unidade_id. Valor não mapeado é erro: a curadoria
# de ref/unidade_alias.csv deve ser completada, nunca contornada.
mapear_unidade <- function(x, unidade_alias, origem) {
  id <- unidade_alias$unidade_id[match(chave_unidade(x), unidade_alias$chave)]
  faltam <- unique(x[!is.na(x) & is.na(id)])
  if (length(faltam)) {
    stop(sprintf("Unidades sem mapeamento em %s: %s. Inclua-as em ref/unidade_alias.csv.",
                 origem, paste(faltam, collapse = " | ")))
  }
  id
}

preparar_projetos <- function(raw, unidade_alias) {
  exigir_colunas(raw, c("id", "titulo", "resumo", "mes_ano_de_inicio", "mes_ano_de_finalizacao",
                        "unidade_lider", "lider_do_projeto", "palavras_chave", "situacao"))
  raw |>
    dplyr::transmute(
      doc_uid = paste0("P:", id),
      id = as.integer(id),
      titulo = stringr::str_squish(titulo),
      resumo = stringr::str_squish(resumo),
      ano_inicio = as.integer(stringr::str_sub(mes_ano_de_inicio, -4)),
      mes_inicio = as.integer(stringr::str_sub(mes_ano_de_inicio, 1, 2)),
      ano_fim = as.integer(stringr::str_sub(mes_ano_de_finalizacao, -4)),
      situacao,
      unidade_lider_raw = unidade_lider,
      unidade_lider_id = mapear_unidade(unidade_lider, unidade_alias, "projetos"),
      lider_raw = stringr::str_squish(lider_do_projeto),
      palavras_chave_raw = palavras_chave,
      url = pagina_do_projeto_no_portal_embrapa
    )
}

preparar_publicacoes <- function(raw, unidade_alias, tipo_publicacao) {
  exigir_colunas(raw, c("id", "titulo", "resumo", "ano_de_publicacao", "tipo_de_publicacao",
                        "unidade", "autores", "palavras_chave"))
  resumo <- stringr::str_squish(raw$resumo)
  raw |>
    dplyr::transmute(
      doc_uid = paste0("B:", id),
      id = as.integer(id),
      titulo = stringr::str_squish(titulo),
      resumo = dplyr::if_else(nchar(resumo) < 30, NA_character_, resumo),
      ano = as.integer(ano_de_publicacao),
      tipo = tipo_de_publicacao,
      tipo_grupo = dplyr::coalesce(
        tipo_publicacao$tipo_grupo[match(tipo_de_publicacao, tipo_publicacao$tipo_original)],
        "nao_classificado"),
      unidade_raw = unidade,
      unidade_id = mapear_unidade(unidade, unidade_alias, "publicações"),
      autores_raw = stringr::str_squish(autores),
      palavras_chave_raw = palavras_chave,
      url_repositorio = mais_informacoes,
      url_arquivo = url_do_arquivo,
      url = pagina_da_publicacao_no_portal_embrapa
    ) |>
    dplyr::mutate(texto_curto = is.na(resumo))
}

preparar_tecnologias <- function(raw, unidade_alias) {
  exigir_colunas(raw, c("id", "nome", "descricao", "tipo", "subtipo", "ano_de_lancamento",
                        "bioma", "unidade_responsavel", "onde_encontrar", "palavras_chave"))
  raw |>
    dplyr::transmute(
      doc_uid = paste0("T:", id),
      id = as.integer(id),
      nome = stringr::str_squish(nome),
      descricao = stringr::str_squish(descricao),
      tipo, subtipo,
      ano = as.integer(ano_de_lancamento),
      biomas = bioma,
      unidade_raw = unidade_responsavel,
      unidade_id = mapear_unidade(unidade_responsavel, unidade_alias, "tecnologias"),
      onde_encontrar,
      palavras_chave_raw = palavras_chave,
      url = pagina_da_tecnologia_no_portal_embrapa
    )
}

# Obras ------------------------------------------------------------------------
# No repositório cada unidade deposita seu próprio registro de uma publicação
# em coautoria. Registros com mesmo título normalizado, mesmo ano e listas de
# autores sobrepostas (coef. de sobreposição >= 0,5) formam uma "obra".
# Várias unidades depositantes numa obra = evidência declarada de colaboração.
# Títulos genéricos ("Anais", "Tecido vegetal") não são agrupados.
agrupar_obras <- function(publicacao, min_palavras = 4, min_sobreposicao = 0.5) {
  b <- publicacao |>
    dplyr::select(doc_uid, id, titulo, ano, autores_raw) |>
    dplyr::mutate(tn = norm_titulo(titulo),
                  elegivel = stringr::str_count(tn, "\\S+") >= min_palavras & nchar(tn) >= 25)

  aut <- b |>
    dplyr::filter(elegivel) |>
    dplyr::group_by(tn, ano) |>
    dplyr::filter(dplyr::n() > 1) |>
    dplyr::ungroup()

  chave_aut <- function(x) {
    if (is.na(x)) return(character())
    a <- parse_assinatura(stringr::str_split(x, ";")[[1]])
    unique(paste(a$sobrenome, substr(a$iniciais, 1, 1)))
  }
  conj <- stats::setNames(lapply(aut$autores_raw, chave_aut), aut$doc_uid)

  pares <- aut |>
    dplyr::select(tn, ano, d1 = doc_uid) |>
    dplyr::inner_join(dplyr::select(aut, tn, ano, d2 = doc_uid), by = c("tn", "ano"),
                      relationship = "many-to-many") |>
    dplyr::filter(d1 < d2)
  if (nrow(pares)) {
    pares$sobreposicao <- mapply(function(x, y) {
      a <- conj[[x]]; b <- conj[[y]]
      if (!length(a) || !length(b)) return(1)
      length(intersect(a, b)) / min(length(a), length(b))
    }, pares$d1, pares$d2)
    pares <- dplyr::filter(pares, sobreposicao >= min_sobreposicao)
  }

  g <- igraph::graph_from_data_frame(dplyr::select(pares, d1, d2), directed = FALSE,
                                     vertices = data.frame(name = b$doc_uid))
  comp <- igraph::components(g)$membership
  b |>
    dplyr::mutate(grupo = comp[doc_uid]) |>
    dplyr::group_by(grupo) |>
    dplyr::mutate(obra_id = paste0("OB:", min(id))) |>
    dplyr::ungroup() |>
    dplyr::select(doc_uid, obra_id)
}

montar_obras <- function(publicacao) {
  publicacao |>
    dplyr::group_by(obra_id) |>
    dplyr::arrange(dplyr::desc(dplyr::coalesce(nchar(resumo), 0L)), id, .by_group = TRUE) |>
    dplyr::summarise(
      doc_uid_representante = dplyr::first(doc_uid),
      titulo = dplyr::first(titulo),
      ano = dplyr::first(ano),
      tipo_grupo = dplyr::first(tipo_grupo),
      n_registros = dplyr::n(),
      unidades_depositantes = paste(sort(unique(stats::na.omit(unidade_id))), collapse = ";"),
      n_unidades_depositantes = dplyr::n_distinct(unidade_id, na.rm = TRUE),
      .groups = "drop"
    )
}

# Vínculos e associações -------------------------------------------------------

montar_doc_keyword <- function(projeto, publicacao, tecnologia) {
  dplyr::bind_rows(
    dplyr::select(projeto, doc_uid, palavras_chave_raw),
    dplyr::select(publicacao, doc_uid, palavras_chave_raw),
    dplyr::select(tecnologia, doc_uid, palavras_chave_raw)
  ) |>
    dplyr::mutate(keyword_raw = split_palavras_chave(palavras_chave_raw)) |>
    dplyr::select(-palavras_chave_raw) |>
    tidyr::unnest_longer(keyword_raw) |>
    dplyr::mutate(keyword_norm = norm_titulo(keyword_raw)) |>
    dplyr::filter(nzchar(keyword_norm)) |>
    dplyr::distinct(doc_uid, keyword_norm, .keep_all = TRUE)
}

# Tecnologias que citam publicações por URL em "Onde encontrar"
montar_doc_link <- function(tecnologia, publicacao) {
  tecnologia |>
    dplyr::select(origem_uid = doc_uid, onde_encontrar) |>
    dplyr::mutate(ids = stringr::str_match_all(
      dplyr::coalesce(onde_encontrar, ""), "(?:publicacao/|handle/doc/)(\\d+)")) |>
    dplyr::mutate(ids = lapply(ids, function(m) unique(m[, 2]))) |>
    dplyr::select(-onde_encontrar) |>
    tidyr::unnest_longer(ids, values_to = "id_destino") |>
    dplyr::transmute(origem_uid, destino_uid = paste0("B:", id_destino),
                     tipo = "cita_publicacao", fonte = "onde_encontrar",
                     destino_na_base = destino_uid %in% publicacao$doc_uid)
}

# Unidades declaradas nas fontes (a camada de afiliação dos autores é
# acrescentada depois da resolução de identidade)
montar_doc_unidade_declarada <- function(projeto, publicacao, tecnologia) {
  dplyr::bind_rows(
    dplyr::transmute(projeto, doc_uid, unidade_id = unidade_lider_id, papel = "lider"),
    dplyr::transmute(publicacao, doc_uid, unidade_id, papel = "depositante"),
    dplyr::transmute(tecnologia, doc_uid, unidade_id, papel = "responsavel")
  ) |>
    dplyr::filter(!is.na(unidade_id)) |>
    dplyr::mutate(fonte = "declarada")
}
