# Localização combinada de cada documento --------------------------------------------
# Um local por documento, na ordem de preferência (decisão da usuária em 18/10/2026):
#   1. municipio_citado — municípios citados no texto (confiança alta ou média);
#   2. estado_citado    — estado citado no texto, sem município identificado;
#   3. sede_unidade     — aproximação: município da sede da unidade principal do documento
#                         (ou de todas as unidades participantes, se não houver principal).
# A fonte fica explícita para o app distinguir "onde a pesquisa acontece" de "onde está a unidade".

montar_doc_localizacao <- function(arquivos_municipios, documento, documento_unidade, unidade_localizacao) {
  ler <- function(padrao) arrow::read_parquet(arquivos_municipios[grepl(padrao, arquivos_municipios)])
  mun <- ler("doc_municipio") |>
    dplyr::filter(confianca %in% c("alta", "media")) |>
    dplyr::distinct(doc_uid, cod_ibge, municipio, uf) |>
    dplyr::mutate(fonte = "municipio_citado")
  centro <- ler("municipio_centroide")

  est <- ler("doc_estado") |>
    dplyr::filter(fonte == "citado", !doc_uid %in% mun$doc_uid) |>
    dplyr::distinct(doc_uid, uf) |>
    dplyr::mutate(cod_ibge = NA_character_, municipio = NA_character_, fonte = "estado_citado")

  sede_un <- unidade_localizacao |>
    dplyr::left_join(dplyr::select(centro, cod_ibge, municipio, uf), by = c("municipio", "uf")) |>
    dplyr::select(unidade_id, cod_ibge, municipio, uf)
  sem_local <- setdiff(documento$doc_uid, c(mun$doc_uid, est$doc_uid))
  principal <- documento |>
    dplyr::filter(doc_uid %in% sem_local, !is.na(unidade_id)) |>
    dplyr::select(doc_uid, unidade_id)
  participantes <- documento_unidade |>
    dplyr::filter(doc_uid %in% setdiff(sem_local, principal$doc_uid)) |>
    dplyr::distinct(doc_uid, unidade_id)
  sede <- dplyr::bind_rows(principal, participantes) |>
    dplyr::inner_join(sede_un, by = "unidade_id") |>
    dplyr::distinct(doc_uid, cod_ibge, municipio, uf) |>
    dplyr::mutate(fonte = "sede_unidade")

  dplyr::bind_rows(mun, est, sede) |>
    dplyr::select(doc_uid, fonte, uf, cod_ibge, municipio)
}
