# Tabelas analíticas consumidas pelo app ---------------------------------------
# Unidade de análise: projeto (P:), obra (OB:) e tecnologia (T:). Publicações
# entram como obras, para não contar duas vezes registros de várias unidades.

# Registro de publicação (B:) -> obra (OB:); demais documentos mantêm o id
mapa_obra <- function(publicacao) {
  dplyr::select(publicacao, doc_uid, doc_id = obra_id)
}
para_documento <- function(df, publicacao) {
  m <- mapa_obra(publicacao)
  df |>
    dplyr::left_join(m, by = "doc_uid") |>
    dplyr::mutate(doc_uid = dplyr::coalesce(doc_id, doc_uid)) |>
    dplyr::select(-doc_id)
}

montar_documento <- function(projeto, obra, publicacao, tecnologia) {
  rep <- dplyr::select(publicacao, doc_uid, resumo, tipo, url, unidade_id)
  dplyr::bind_rows(
    projeto |>
      dplyr::transmute(doc_uid, tipo_doc = "projeto", titulo, resumo, ano = ano_inicio, ano_fim,
                       categoria = situacao, detalhe = situacao, unidade_id = unidade_lider_id, url),
    obra |>
      dplyr::left_join(rep, by = c("doc_uid_representante" = "doc_uid")) |>
      dplyr::transmute(doc_uid = obra_id, tipo_doc = "publicacao", titulo, resumo, ano, ano_fim = ano,
                       categoria = tipo_grupo, detalhe = tipo, unidade_id, url,
                       doc_uid_representante, n_registros),
    tecnologia |>
      dplyr::transmute(doc_uid, tipo_doc = "tecnologia", titulo = nome, resumo = descricao, ano,
                       ano_fim = ano, categoria = tipo, detalhe = subtipo, unidade_id, url)
  )
}

montar_documento_unidade <- function(doc_unidade, publicacao) {
  para_documento(doc_unidade, publicacao) |>
    dplyr::distinct(doc_uid, unidade_id, papel, .keep_all = TRUE)
}

montar_documento_pessoa <- function(doc_pessoa, publicacao) {
  doc_pessoa |>
    dplyr::filter(nivel %in% c("A", "B", "M")) |>
    para_documento(publicacao) |>
    dplyr::group_by(doc_uid, pessoa_id, papel) |>
    dplyr::summarise(nivel = min(nivel), .groups = "drop")
}

montar_documento_keyword <- function(doc_keyword, publicacao) {
  para_documento(doc_keyword, publicacao) |>
    dplyr::distinct(doc_uid, keyword_norm, .keep_all = TRUE)
}

# Pares de nós que coocorrem num documento, com contagem fracionária de
# Newman: cada documento com k participantes dá peso 1/(k-1) a cada par.
pares_por_documento <- function(df, k_total = NULL) {
  df <- dplyr::distinct(df, doc_uid, no)
  k <- if (is.null(k_total)) dplyr::count(df, doc_uid, name = "k") else k_total
  df |>
    dplyr::inner_join(df, by = "doc_uid", suffix = c("1", "2"), relationship = "many-to-many") |>
    dplyr::filter(no1 < no2) |>
    dplyr::left_join(k, by = "doc_uid") |>
    dplyr::mutate(peso = 1, peso_frac = 1 / pmax(k - 1, 1)) |>
    dplyr::select(doc_uid, no1, no2, peso, peso_frac)
}

# Rede de unidades, por camada e documento (o app agrega por período).
#  publicacoes          unidades de uma obra (depositantes + afiliação dos autores)
#  tecnologias_indireta tecnologia de U1 cita obra com participação de U2
# A camada de projetos depende de dados de equipe (ainda indisponíveis).
montar_aresta_unidade <- function(documento, documento_unidade, doc_link, publicacao) {
  ano <- dplyr::select(documento, doc_uid, ano)
  pub <- documento_unidade |>
    dplyr::filter(startsWith(doc_uid, "OB:"), papel %in% c("depositante", "afiliacao_autor")) |>
    dplyr::transmute(doc_uid, no = unidade_id) |>
    pares_por_documento() |>
    dplyr::mutate(camada = "publicacoes")

  un_obra <- documento_unidade |>
    dplyr::filter(startsWith(doc_uid, "OB:"), papel %in% c("depositante", "afiliacao_autor")) |>
    dplyr::distinct(obra = doc_uid, u2 = unidade_id)
  tec <- doc_link |>
    dplyr::filter(destino_na_base) |>
    dplyr::left_join(dplyr::select(publicacao, doc_uid, obra = obra_id), by = c("destino_uid" = "doc_uid")) |>
    dplyr::inner_join(dplyr::filter(documento_unidade, papel == "responsavel") |>
                        dplyr::select(origem_uid = doc_uid, u1 = unidade_id), by = "origem_uid") |>
    dplyr::inner_join(un_obra, by = "obra", relationship = "many-to-many") |>
    dplyr::filter(u1 != u2) |>
    dplyr::distinct(doc_uid = origem_uid, u1, u2) |>
    dplyr::group_by(doc_uid) |>
    dplyr::mutate(peso = 1, peso_frac = 1 / dplyr::n()) |>
    dplyr::ungroup() |>
    dplyr::transmute(doc_uid, no1 = pmin(u1, u2), no2 = pmax(u1, u2), peso, peso_frac,
                     camada = "tecnologias_indireta") |>
    dplyr::distinct(doc_uid, no1, no2, .keep_all = TRUE)

  dplyr::bind_rows(pub, tec) |>
    dplyr::left_join(ano, by = "doc_uid") |>
    dplyr::rename(unidade1 = no1, unidade2 = no2)
}

# Coautoria entre pesquisadores identificados. k = total de autores da obra
# (inclusive externos), para que obras muito coletivas pesem menos.
montar_aresta_pessoa <- function(documento_pessoa, doc_pessoa, documento, publicacao) {
  k <- doc_pessoa |>
    dplyr::filter(papel == "autor") |>
    dplyr::semi_join(dplyr::select(documento, doc_uid = doc_uid_representante), by = "doc_uid") |>
    para_documento(publicacao) |>
    dplyr::count(doc_uid, name = "k")
  documento_pessoa |>
    dplyr::filter(papel == "autor") |>
    dplyr::transmute(doc_uid, no = pessoa_id) |>
    pares_por_documento(k_total = k) |>
    dplyr::left_join(dplyr::select(documento, doc_uid, ano), by = "doc_uid") |>
    dplyr::rename(pessoa1 = no1, pessoa2 = no2)
}

# Tecnologias associadas a pessoas por vínculo declarado: a tecnologia cita
# uma publicação de autoria da pessoa.
montar_pessoa_tecnologia <- function(doc_link, documento_pessoa, publicacao) {
  doc_link |>
    dplyr::filter(destino_na_base) |>
    dplyr::left_join(dplyr::select(publicacao, doc_uid, obra = obra_id), by = c("destino_uid" = "doc_uid")) |>
    dplyr::inner_join(dplyr::filter(documento_pessoa, papel == "autor") |>
                        dplyr::select(obra = doc_uid, pessoa_id), by = "obra") |>
    dplyr::distinct(pessoa_id, tecnologia_uid = origem_uid, obra) |>
    dplyr::mutate(vinculo = "declarado")
}

montar_meta <- function(exportacao, brutos) {
  tibble::tibble(
    exportacao = exportacao,
    gerado_em = format(Sys.time(), "%Y-%m-%d %H:%M"),
    arquivos_truncados = paste(names(brutos)[vapply(brutos, function(b) isTRUE(attr(b, "truncado")), logical(1))],
                               collapse = ";")
  )
}
