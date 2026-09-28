# Resolução de identidade de pesquisadores ------------------------------------
#
# Níveis de confiança de cada menção (líder de projeto ou assinatura de autor):
#   A  determinístico (candidato único + evidência de unidade)
#   B  desambiguado com margem clara
#   C  ambíguo: há candidatos Embrapa, nenhum atribuído
#   D  sem candidato: autor externo (ou ausente da base de pessoas)
#   M  decisão manual (ref/overrides_identidade.csv)
# O app usa por padrão apenas A, B e M.

# Etapa 1 — consolidar registros da base de autores em pessoas ---------------
# Mesmo nome completo + mesmo sobrenome de assinatura = mesma pessoa (a base
# tem pessoas com várias matrículas / registros).
consolidar_pessoas <- function(autores_raw, unidade_alias, unidade) {
  a <- autores_raw |>
    dplyr::transmute(
      id_autor = as.integer(id_autor),
      nome = stringr::str_squish(nome),
      nome_anterior = stringr::str_squish(nome_anterior),
      autoria = stringr::str_squish(autoria),
      afiliacao_sigla = stringr::str_squish(afiliacao),
      ativo = ativado == "S"
    ) |>
    dplyr::mutate(
      nome_norm = norm_nome(nome),
      unidade_afiliacao_id = mapear_unidade(afiliacao_sigla, unidade_alias, "afiliação dos autores")
    )
  sa <- parse_assinatura(a$autoria)
  a$sobrenome <- sa$sobrenome
  a$iniciais <- sa$iniciais

  a <- a |>
    dplyr::group_by(nome_norm, sobrenome) |>
    dplyr::mutate(pessoa_id = paste0("PE", min(id_autor))) |>
    dplyr::ungroup()
  a <- unir_variantes_de_nome(a)

  centro <- unidade$unidade_id[unidade$categoria == "centro"]
  pessoa <- a |>
    dplyr::arrange(dplyr::desc(ativo), dplyr::desc(id_autor)) |>
    dplyr::group_by(pessoa_id) |>
    dplyr::summarise(
      nome_norm = dplyr::first(nome_norm),
      nome_base = formatar_nome(dplyr::first(nome)),
      assinatura_principal = dplyr::first(autoria),
      afiliacao_sigla = dplyr::first(afiliacao_sigla),
      unidade_afiliacao_id = dplyr::first(unidade_afiliacao_id),
      ativo = any(ativo),
      n_registros_base = dplyr::n(),
      .groups = "drop"
    ) |>
    dplyr::mutate(afiliacao_em_centro = unidade_afiliacao_id %in% centro)

  # Formas de nome (para líderes) e de assinatura (para autores) por pessoa
  nomes <- dplyr::bind_rows(
    dplyr::transmute(a, pessoa_id, nome_norm, origem = "nome"),
    a |> dplyr::filter(!is.na(nome_anterior)) |>
      dplyr::transmute(pessoa_id, nome_norm = norm_nome(nome_anterior), origem = "nome_anterior")
  ) |> dplyr::distinct(pessoa_id, nome_norm, .keep_all = TRUE)

  sn <- assinatura_de_nome(nomes$nome_norm)
  assinaturas <- dplyr::bind_rows(
    dplyr::transmute(a, pessoa_id, sobrenome, iniciais, origem = "autoria"),
    dplyr::transmute(nomes, pessoa_id, sobrenome = sn$sobrenome, iniciais = sn$iniciais,
                     origem = paste0("derivada_", origem))
  ) |>
    dplyr::filter(!is.na(sobrenome), nzchar(sobrenome)) |>
    dplyr::distinct(pessoa_id, sobrenome, iniciais, .keep_all = TRUE)

  list(
    registro = dplyr::select(a, id_autor, pessoa_id, nome, nome_anterior, autoria,
                             afiliacao_sigla, unidade_afiliacao_id, ativo),
    pessoa = pessoa,
    nomes = nomes,
    assinaturas = assinaturas
  )
}

# Mesma assinatura + nomes compatíveis ("DEUSIMAR RODRIGUES LIMA" ~
# "DEUSIMAR RODRIGUES DE LIMA") = mesma pessoa, desde que na mesma unidade ou
# com um dos registros na Sede. Em unidades diferentes podem ser homônimos.
unir_variantes_de_nome <- function(a) {
  p <- dplyr::distinct(a, pessoa_id, nome_norm, sobrenome, iniciais, unidade_afiliacao_id)
  pares <- p |>
    dplyr::inner_join(p, by = c("sobrenome", "iniciais"), suffix = c("1", "2"),
                      relationship = "many-to-many") |>
    dplyr::filter(pessoa_id1 < pessoa_id2,
                  unidade_afiliacao_id1 == unidade_afiliacao_id2 |
                    unidade_afiliacao_id1 == "sede" | unidade_afiliacao_id2 == "sede")
  if (!nrow(pares)) return(a)
  pares <- pares[mapply(nomes_compativeis, tokens_nome(pares$nome_norm1), tokens_nome(pares$nome_norm2)), ]
  if (!nrow(pares)) return(a)
  g <- igraph::graph_from_data_frame(dplyr::select(pares, pessoa_id1, pessoa_id2), directed = FALSE)
  comp <- igraph::components(g)$membership
  novo <- tapply(names(comp), comp, function(ids) ids[which.min(as.integer(sub("PE", "", ids)))])
  mapa <- stats::setNames(as.character(novo[as.character(comp)]), names(comp))
  a$pessoa_id <- dplyr::coalesce(unname(mapa[a$pessoa_id]), a$pessoa_id)
  a
}

# Etapa 2 — líderes de projeto (nome completo) ---------------------------------
resolver_lideres <- function(projeto, pessoas) {
  pes_un <- dplyr::select(pessoas$pessoa, pessoa_id, unidade_afiliacao_id)
  l <- projeto |>
    dplyr::transmute(doc_uid, unidade_id = unidade_lider_id, nome_origem = lider_raw,
                     nome_norm = norm_nome(lider_raw))

  # 2.1 nome normalizado exato (inclui nome anterior)
  exato <- l |>
    dplyr::inner_join(pessoas$nomes, by = "nome_norm", relationship = "many-to-many") |>
    dplyr::left_join(pes_un, by = "pessoa_id") |>
    dplyr::mutate(unidade_ok = unidade_afiliacao_id == unidade_id, metodo = paste0("exato_", origem)) |>
    dplyr::distinct(doc_uid, pessoa_id, .keep_all = TRUE)

  # 2.2 compatibilidade token a token para os demais
  rest <- dplyr::filter(l, !doc_uid %in% exato$doc_uid)
  tk_l <- tokens_nome(rest$nome_norm)
  rest$primeiro <- vapply(tk_l, function(t) t[1], "")
  rest$ultimo <- vapply(tk_l, function(t) t[length(t)], "")
  tk_p <- tokens_nome(pessoas$nomes$nome_norm)
  base <- pessoas$nomes |>
    dplyr::mutate(primeiro = vapply(tk_p, function(t) if (length(t)) t[1] else NA_character_, ""),
                  ultimo = vapply(tk_p, function(t) if (length(t)) t[length(t)] else NA_character_, ""),
                  nome_norm_p = nome_norm) |>
    dplyr::select(pessoa_id, primeiro, ultimo, nome_norm_p)
  tokens <- rest |>
    dplyr::inner_join(base, by = c("primeiro", "ultimo"), relationship = "many-to-many")
  if (nrow(tokens)) {
    tokens$compativel <- mapply(nomes_compativeis, tokens_nome(tokens$nome_norm), tokens_nome(tokens$nome_norm_p))
    tokens$min_tokens <- pmin(lengths(tokens_nome(tokens$nome_norm)), lengths(tokens_nome(tokens$nome_norm_p)))
  } else {
    tokens$compativel <- logical(); tokens$min_tokens <- integer()
  }
  tokens <- tokens |>
    dplyr::filter(compativel) |>
    dplyr::left_join(pes_un, by = "pessoa_id") |>
    dplyr::mutate(unidade_ok = unidade_afiliacao_id == unidade_id, metodo = "tokens") |>
    dplyr::distinct(doc_uid, pessoa_id, .keep_all = TRUE)

  decidir <- function(cand, exato) {
    cand |>
      dplyr::group_by(doc_uid) |>
      dplyr::summarise(
        n_cand = dplyr::n(),
        n_un = sum(unidade_ok, na.rm = TRUE),
        pessoa_unica = dplyr::first(pessoa_id),
        pessoa_un = dplyr::first(pessoa_id[unidade_ok %in% TRUE]),
        curto = dplyr::first(if ("min_tokens" %in% names(cand)) min_tokens else 99L) < 3,
        metodo = dplyr::first(metodo),
        candidatos = paste(pessoa_id, collapse = ";"),
        .groups = "drop"
      ) |>
      dplyr::mutate(
        nivel = dplyr::case_when(
          n_cand == 1 & (exato | n_un == 1 | !curto) ~ if (exato) "A" else "B",
          n_cand > 1 & n_un == 1 ~ if (exato) "A" else "B",
          TRUE ~ "C"),
        pessoa_id = dplyr::case_when(nivel != "C" & n_cand == 1 ~ pessoa_unica,
                                     nivel != "C" ~ pessoa_un, TRUE ~ NA_character_),
        candidatos = dplyr::if_else(nivel == "C", candidatos, NA_character_)
      ) |>
      dplyr::select(doc_uid, pessoa_id, nivel, metodo, candidatos)
  }

  res <- dplyr::bind_rows(decidir(exato, TRUE), decidir(tokens, FALSE))
  l |>
    dplyr::select(doc_uid, nome_origem) |>
    dplyr::left_join(res, by = "doc_uid") |>
    dplyr::mutate(
      nivel = dplyr::coalesce(nivel, "D"),
      metodo = dplyr::coalesce(metodo, "sem_candidato"),
      papel = "lider", ordem = 1L, score = NA_real_
    )
}

# Etapa 3 — assinaturas de autores em publicações --------------------------------
# Pontuação de cada candidato:
#   iniciais exatas +3 | compatíveis +1
#   unidade do candidato entre as unidades depositantes da obra +3
#   coautores já resolvidos que também coassinam com o candidato em outras obras +2 cada (máx. +4)
resolver_autorias <- function(publicacao, pessoas, pessoa_unidade, n_rodadas = 3) {
  mencoes <- publicacao |>
    dplyr::filter(!is.na(autores_raw)) |>
    dplyr::transmute(doc_uid, obra_id, a = stringr::str_split(autores_raw, ";")) |>
    tidyr::unnest_longer(a, values_to = "nome_origem", indices_to = "ordem") |>
    dplyr::mutate(nome_origem = stringr::str_squish(nome_origem)) |>
    dplyr::filter(nzchar(nome_origem)) |>
    dplyr::mutate(mencao_id = dplyr::row_number())
  pa <- parse_assinatura(mencoes$nome_origem)
  mencoes$sobrenome <- pa$sobrenome
  mencoes$iniciais <- pa$iniciais
  mencoes$ini1 <- substr(mencoes$iniciais, 1, 1)

  cand <- mencoes |>
    dplyr::filter(nzchar(ini1)) |>
    dplyr::select(mencao_id, obra_id, sobrenome, ini1, iniciais) |>
    dplyr::inner_join(
      dplyr::mutate(pessoas$assinaturas, ini1 = substr(iniciais, 1, 1)) |>
        dplyr::select(pessoa_id, sobrenome, ini1, iniciais_p = iniciais),
      by = c("sobrenome", "ini1"), relationship = "many-to-many") |>
    dplyr::mutate(compat = compat_iniciais(iniciais, iniciais_p)) |>
    dplyr::filter(compat != "incompativel") |>
    dplyr::group_by(mencao_id, obra_id, pessoa_id) |>
    dplyr::summarise(exata = any(compat == "exata"), .groups = "drop")

  obra_un <- publicacao |>
    dplyr::filter(!is.na(unidade_id)) |>
    dplyr::distinct(obra_id, unidade_id)

  # Sobrenomes comuns (SILVA, LIMA...) também são comuns entre coautores
  # externos: candidato único sem outra evidência não basta.
  freq_sob <- pessoas$assinaturas |>
    dplyr::distinct(sobrenome, pessoa_id) |>
    dplyr::count(sobrenome, name = "freq_sobrenome")
  n_ini <- mencoes |>
    dplyr::select(mencao_id, doc_uid, iniciais, sobrenome) |>
    dplyr::left_join(freq_sob, by = "sobrenome") |>
    dplyr::transmute(mencao_id, doc_uid, n_ini = nchar(iniciais),
                     sob_raro = dplyr::coalesce(freq_sobrenome, 0L) <= 3,
                     sob_unico = dplyr::coalesce(freq_sobrenome, 0L) <= 1)
  resolvidos <- tibble::tibble(mencao_id = integer(), obra_id = character(), pessoa_id = character())
  dec <- NULL

  for (rodada in seq_len(n_rodadas)) {
    # Evidência de unidade: cadastro + unidades em que a pessoa já aparece
    # resolvida em pelo menos 2 obras (aprendida nas rodadas anteriores)
    un_aprendida <- resolvidos |>
      dplyr::inner_join(obra_un, by = "obra_id", relationship = "many-to-many") |>
      dplyr::distinct(pessoa_id, unidade_id, obra_id) |>
      dplyr::count(pessoa_id, unidade_id) |>
      dplyr::filter(n >= 2) |>
      dplyr::select(pessoa_id, unidade_id)
    com_unidade <- cand |>
      dplyr::select(mencao_id, obra_id, pessoa_id) |>
      dplyr::inner_join(dplyr::distinct(dplyr::bind_rows(pessoa_unidade, un_aprendida)),
                        by = "pessoa_id", relationship = "many-to-many") |>
      dplyr::semi_join(obra_un, by = c("obra_id", "unidade_id")) |>
      dplyr::distinct(mencao_id, pessoa_id) |>
      dplyr::mutate(unidade = TRUE)

    coaut <- contar_coautores(cand, resolvidos)
    s <- cand |>
      dplyr::left_join(com_unidade, by = c("mencao_id", "pessoa_id")) |>
      dplyr::left_join(coaut, by = c("mencao_id", "pessoa_id")) |>
      dplyr::mutate(unidade = dplyr::coalesce(unidade, FALSE),
                    n_coaut = dplyr::coalesce(n_coaut, 0L),
                    score = ifelse(exata, 3, 1) + ifelse(unidade, 3, 0) + 2 * pmin(n_coaut, 2L))
    dec <- s |>
      dplyr::arrange(mencao_id, dplyr::desc(score)) |>
      dplyr::group_by(mencao_id) |>
      dplyr::summarise(
        candidatos = paste0(pessoa_id, ":", score, collapse = ";"),
        n_cand = dplyr::n(),
        n_exatas = sum(exata),
        s1 = dplyr::first(score),
        s2 = if (dplyr::n() > 1) dplyr::nth(score, 2) else 0,
        exata1 = dplyr::first(exata),
        unidade1 = dplyr::first(unidade),
        coaut1 = dplyr::first(n_coaut),
        pessoa_id = dplyr::first(pessoa_id),
        .groups = "drop"
      ) |>
      dplyr::left_join(n_ini, by = "mencao_id") |>
      dplyr::mutate(nivel = dplyr::case_when(
        n_cand == 1 & exata1 & unidade1 ~ "A",
        n_cand == 1 & exata1 & (n_ini >= 3 | (n_ini >= 2 & sob_raro) | sob_unico) ~ "B",
        n_cand == 1 & (unidade1 | coaut1 >= 1) ~ "B",
        # única com iniciais exatas; as demais só compatíveis (MA vs MAS)
        n_cand > 1 & exata1 & n_exatas == 1 & n_ini >= 2 & (s1 - s2) >= 2 ~ "B",
        n_cand > 1 & s1 >= 5 & (s1 - s2) >= 3 ~ "B",
        TRUE ~ "C"))
    # a mesma pessoa não pode assinar duas vezes o mesmo registro
    dup <- dec |>
      dplyr::filter(nivel %in% c("A", "B")) |>
      dplyr::count(doc_uid, pessoa_id) |>
      dplyr::filter(n > 1)
    dec <- dec |>
      dplyr::mutate(nivel = dplyr::if_else(
        paste(doc_uid, pessoa_id) %in% paste(dup$doc_uid, dup$pessoa_id) & nivel %in% c("A", "B"),
        "C", nivel))
    resolvidos <- dec |>
      dplyr::filter(nivel %in% c("A", "B")) |>
      dplyr::select(mencao_id, pessoa_id) |>
      dplyr::left_join(dplyr::select(mencoes, mencao_id, obra_id), by = "mencao_id")
  }

  mencoes |>
    dplyr::select(mencao_id, doc_uid, ordem, nome_origem) |>
    dplyr::left_join(dplyr::select(dec, mencao_id, pessoa_id, nivel, score = s1, candidatos),
                     by = "mencao_id") |>
    dplyr::mutate(
      nivel = dplyr::coalesce(nivel, "D"),
      candidatos = dplyr::if_else(nivel == "C", candidatos, NA_character_),
      pessoa_id = dplyr::if_else(nivel %in% c("A", "B"), pessoa_id, NA_character_),
      metodo = dplyr::if_else(nivel == "D", "sem_candidato", "assinatura"),
      papel = "autor", ordem = as.integer(ordem)
    ) |>
    dplyr::select(-mencao_id)
}

# Para cada (menção, candidato): quantos outros autores já resolvidos na
# mesma obra também são coautores do candidato em outra obra.
contar_coautores <- function(cand, resolvidos) {
  vazio <- tibble::tibble(mencao_id = integer(), pessoa_id = character(), n_coaut = integer())
  if (!nrow(resolvidos)) return(vazio)
  pares <- resolvidos |>
    dplyr::select(obra_par = obra_id, p1 = pessoa_id) |>
    dplyr::inner_join(dplyr::select(resolvidos, obra_par = obra_id, p2 = pessoa_id),
                      by = "obra_par", relationship = "many-to-many") |>
    dplyr::filter(p1 != p2) |>
    dplyr::distinct()
  cand |>
    dplyr::select(mencao_id, obra_id, pessoa_id) |>
    dplyr::inner_join(dplyr::select(resolvidos, obra_id, q = pessoa_id, mencao_q = mencao_id),
                      by = "obra_id", relationship = "many-to-many") |>
    dplyr::filter(mencao_q != mencao_id, q != pessoa_id) |>
    dplyr::inner_join(pares, by = c("pessoa_id" = "p1", "q" = "p2"), relationship = "many-to-many") |>
    dplyr::filter(obra_par != obra_id) |>
    dplyr::distinct(mencao_id, pessoa_id, q) |>
    dplyr::count(mencao_id, pessoa_id, name = "n_coaut")
}

# Decisões manuais têm precedência sobre as regras. Escopo de cada decisão:
# um documento (doc_uid), todos os documentos de uma unidade (unidade_doc)
# ou, com ambos vazios, todas as ocorrências da assinatura.
aplicar_overrides <- function(doc_pessoa, overrides, doc_unidade_declarada) {
  overrides <- dplyr::filter(overrides, !is.na(pessoa_id), nzchar(pessoa_id))
  if (!nrow(overrides)) return(doc_pessoa)
  ov <- overrides |>
    dplyr::mutate(doc_uid = dplyr::na_if(doc_uid, ""),
                  unidade_doc = dplyr::na_if(unidade_doc, ""),
                  papel = dplyr::if_else(contexto == "lider", "lider", "autor"))
  for (i in seq_len(nrow(ov))) {
    docs_unidade <- if (is.na(ov$unidade_doc[i])) NULL else
      doc_unidade_declarada$doc_uid[doc_unidade_declarada$unidade_id == ov$unidade_doc[i]]
    alvo <- doc_pessoa$papel == ov$papel[i] & doc_pessoa$nome_origem == ov$nome_origem[i] &
      (is.na(ov$doc_uid[i]) | doc_pessoa$doc_uid == ov$doc_uid[i]) &
      (is.na(ov$unidade_doc[i]) | doc_pessoa$doc_uid %in% docs_unidade)
    externo <- ov$pessoa_id[i] == "EXTERNO"
    doc_pessoa$pessoa_id[alvo] <- if (externo) NA_character_ else ov$pessoa_id[i]
    doc_pessoa$nivel[alvo] <- if (externo) "D" else "M"
    doc_pessoa$metodo[alvo] <- "manual"
  }
  doc_pessoa
}

# Unidades associadas a cada pessoa, usadas como evidência na desambiguação:
# afiliação (se for centro de pesquisa) + unidades dos projetos que lidera.
montar_pessoa_unidade <- function(pessoas, lideres, projeto) {
  dplyr::bind_rows(
    pessoas$pessoa |>
      dplyr::filter(afiliacao_em_centro) |>
      dplyr::transmute(pessoa_id, unidade_id = unidade_afiliacao_id),
    lideres |>
      dplyr::filter(nivel %in% c("A", "B", "M")) |>
      dplyr::inner_join(dplyr::select(projeto, doc_uid, unidade_id = unidade_lider_id), by = "doc_uid") |>
      dplyr::select(pessoa_id, unidade_id)
  ) |> dplyr::distinct()
}

# Tabela final de pessoas: nome de exibição, unidade inferida pela produção
# (moda das unidades dos documentos atribuídos) e unidade de referência
# (afiliação quando é centro de pesquisa; senão a inferida).
finalizar_pessoas <- function(pessoas, doc_pessoa, publicacao, projeto) {
  atr <- dplyr::filter(doc_pessoa, nivel %in% c("A", "B", "M"))
  un_docs <- dplyr::bind_rows(
    dplyr::select(publicacao, doc_uid, unidade_id),
    dplyr::select(projeto, doc_uid, unidade_id = unidade_lider_id)
  )
  inferida <- atr |>
    dplyr::inner_join(un_docs, by = "doc_uid") |>
    dplyr::filter(!is.na(unidade_id)) |>
    dplyr::count(pessoa_id, unidade_id) |>
    dplyr::group_by(pessoa_id) |>
    dplyr::slice_max(n, n = 1, with_ties = FALSE) |>
    dplyr::ungroup() |>
    dplyr::select(pessoa_id, unidade_inferida_id = unidade_id)
  nome_lider <- atr |>
    dplyr::filter(papel == "lider") |>
    dplyr::count(pessoa_id, nome_origem) |>
    dplyr::group_by(pessoa_id) |>
    dplyr::slice_max(n, n = 1, with_ties = FALSE) |>
    dplyr::ungroup() |>
    dplyr::select(pessoa_id, nome_lider = nome_origem)
  contagem <- atr |>
    dplyr::left_join(dplyr::select(publicacao, doc_uid, obra_id), by = "doc_uid") |>
    dplyr::group_by(pessoa_id) |>
    dplyr::summarise(n_projetos_lider = dplyr::n_distinct(doc_uid[papel == "lider"]),
                     n_obras = dplyr::n_distinct(obra_id[papel == "autor"]),
                     .groups = "drop")

  pessoas$pessoa |>
    dplyr::left_join(inferida, by = "pessoa_id") |>
    dplyr::left_join(nome_lider, by = "pessoa_id") |>
    dplyr::left_join(contagem, by = "pessoa_id") |>
    dplyr::mutate(
      nome_exibicao = dplyr::coalesce(nome_lider, nome_base),
      unidade_ref_id = dplyr::case_when(afiliacao_em_centro ~ unidade_afiliacao_id,
                                        !is.na(unidade_inferida_id) ~ unidade_inferida_id,
                                        TRUE ~ unidade_afiliacao_id),
      unidade_ref_origem = dplyr::case_when(afiliacao_em_centro ~ "afiliacao",
                                            !is.na(unidade_inferida_id) ~ "inferida_producao",
                                            TRUE ~ "afiliacao_central"),
      dplyr::across(c(n_projetos_lider, n_obras), ~ dplyr::coalesce(.x, 0L))
    ) |>
    dplyr::select(pessoa_id, nome_exibicao, nome_norm, assinatura_principal, afiliacao_sigla,
                  unidade_afiliacao_id, unidade_inferida_id, unidade_ref_id, unidade_ref_origem,
                  ativo, n_registros_base, n_projetos_lider, n_obras)
}

# Rótulo de exibição de cada menção: pesquisador identificado, autor externo
# ou identificação ambígua.
rotular_mencoes <- function(doc_pessoa, pessoa) {
  doc_pessoa |>
    dplyr::left_join(dplyr::select(pessoa, pessoa_id, nome_exibicao), by = "pessoa_id") |>
    dplyr::mutate(rotulo_exibicao = dplyr::case_when(
      !is.na(nome_exibicao) ~ nome_exibicao,
      nivel == "C" ~ paste0(nome_origem, " (identificação ambígua)"),
      papel == "autor" ~ paste0(nome_origem, " (autor externo)"),
      TRUE ~ paste0(nome_origem, " (não identificado na base de pessoas)")
    )) |>
    dplyr::select(-nome_exibicao)
}

# Camada derivada: unidade de cada autor Embrapa identificado, na época da obra.
# A afiliação do cadastro é atual; quem mudou de unidade teria a produção
# antiga atribuída à unidade nova, criando colaborações falsas. Regra: se uma
# unidade depositante da obra é unidade conhecida da pessoa (afiliação ou
# unidade em que ela aparece em >= 2 obras), usa-se essa; senão, a de referência.
doc_unidade_autores <- function(doc_pessoa, pessoa, publicacao) {
  aut <- doc_pessoa |>
    dplyr::filter(papel == "autor", nivel %in% c("A", "B", "M")) |>
    dplyr::distinct(doc_uid, pessoa_id) |>
    dplyr::inner_join(dplyr::select(publicacao, doc_uid, obra_id), by = "doc_uid")
  obra_un <- publicacao |>
    dplyr::filter(!is.na(unidade_id)) |>
    dplyr::distinct(obra_id, unidade_id)
  conhecidas <- dplyr::bind_rows(
    aut |>
      dplyr::distinct(pessoa_id, obra_id) |>
      dplyr::inner_join(obra_un, by = "obra_id", relationship = "many-to-many") |>
      dplyr::count(pessoa_id, unidade_id) |>
      dplyr::filter(n >= 2) |>
      dplyr::select(pessoa_id, unidade_id),
    dplyr::transmute(pessoa, pessoa_id, unidade_id = unidade_afiliacao_id)
  ) |> dplyr::distinct()
  na_epoca <- aut |>
    dplyr::inner_join(obra_un, by = "obra_id", relationship = "many-to-many") |>
    dplyr::semi_join(conhecidas, by = c("pessoa_id", "unidade_id")) |>
    dplyr::group_by(doc_uid, pessoa_id) |>
    dplyr::summarise(unidade_id = dplyr::first(unidade_id), .groups = "drop") |>
    dplyr::mutate(origem = "depositante_conhecida")
  aut |>
    dplyr::select(doc_uid, pessoa_id) |>
    dplyr::left_join(na_epoca, by = c("doc_uid", "pessoa_id")) |>
    dplyr::left_join(dplyr::select(pessoa, pessoa_id, unidade_ref_id), by = "pessoa_id") |>
    dplyr::mutate(origem = dplyr::coalesce(origem, "referencia_pessoa"),
                  unidade_id = dplyr::coalesce(unidade_id, unidade_ref_id)) |>
    dplyr::filter(!is.na(unidade_id)) |>
    dplyr::distinct(doc_uid, unidade_id, .keep_all = TRUE) |>
    dplyr::transmute(doc_uid, unidade_id, papel = "afiliacao_autor",
                     fonte = paste0("resolvida_", origem))
}
