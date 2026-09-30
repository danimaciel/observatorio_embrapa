# Biomas ------------------------------------------------------------------------
# Contornos: IBGE 2019 (1:250.000), versão simplificada distribuída pelo geobr/IPEA:
# https://www.ipea.gov.br/geobr/data_gpkg/biomes/2019/biomes_2019_simplified.gpkg
# (baixada para data/raw/geo/). O "Sistema Costeiro" não é bioma e fica de fora.

BIOMAS <- c("Amazônia", "Caatinga", "Cerrado", "Mata Atlântica", "Pampa", "Pantanal")

ler_biomas <- function(path) {
  b <- sf::st_read(path, quiet = TRUE)
  b <- b[b$name_biome %in% BIOMAS, ]
  b <- sf::st_make_valid(sf::st_transform(b["name_biome"], 5880))   # SIRGAS 2000 / Brazil Polyconic
  poligonos(b)
}

# st_make_valid/st_simplify podem gerar GeometryCollection (com linhas e pontos
# soltos), que os mapas não desenham: fica só a parte poligonal.
poligonos <- function(x) {
  x <- suppressWarnings(sf::st_collection_extract(x, "POLYGON"))
  x <- stats::aggregate(x, by = list(nome = x[[1]]), FUN = function(v) v[1])
  sf::st_cast(x[, names(x) != "nome"], "MULTIPOLYGON")
}

# Bioma predominante (maior área) de cada município.
bioma_municipio <- function(biomas_path, municipios_path) {
  old <- sf::sf_use_s2(FALSE)
  on.exit(sf::sf_use_s2(old))
  b <- ler_biomas(biomas_path)
  m <- sf::st_read(municipios_path, quiet = TRUE)
  m <- sf::st_make_valid(sf::st_transform(m["codarea"], 5880))
  x <- suppressWarnings(sf::st_intersection(m, b))
  x$area <- as.numeric(sf::st_area(x))
  sf::st_drop_geometry(x) |>
    dplyr::group_by(cod_ibge = as.character(codarea)) |>
    dplyr::mutate(frac = area / sum(area)) |>
    dplyr::slice_max(area, n = 1, with_ties = FALSE) |>
    dplyr::ungroup() |>
    dplyr::transmute(cod_ibge, bioma = name_biome, fracao_area = round(frac, 3))
}

# Documento × bioma, por duas vias:
#  - "declarado": campo Bioma das tecnologias (lista separada por vírgula);
#  - "municipio_citado": bioma predominante dos municípios citados no texto
#    (só menções de confiança alta ou média).
montar_doc_bioma <- function(tecnologia, doc_municipio_path, bioma_mun) {
  decl <- tecnologia |>
    dplyr::filter(!is.na(biomas)) |>
    dplyr::transmute(doc_uid, bioma = strsplit(biomas, ",\\s*")) |>
    tidyr::unnest_longer(bioma) |>
    dplyr::mutate(bioma = stringr::str_squish(bioma)) |>
    dplyr::filter(bioma %in% BIOMAS) |>
    dplyr::distinct() |>
    dplyr::mutate(fonte = "declarado")
  cit <- arrow::read_parquet(doc_municipio_path) |>
    dplyr::filter(confianca %in% c("alta", "media")) |>
    dplyr::inner_join(bioma_mun, by = "cod_ibge") |>
    dplyr::distinct(doc_uid, bioma) |>
    dplyr::mutate(fonte = "municipio_citado")
  dplyr::bind_rows(decl, cit) |>
    dplyr::group_by(doc_uid, fonte) |>
    dplyr::mutate(n_biomas = dplyr::n()) |>   # 6 = tecnologia declarada para todos os biomas
    dplyr::ungroup()
}

# Contornos leves para o app (app/assets/br_biomas.geojson).
exportar_geo_biomas <- function(biomas_path, destino) {
  old <- sf::sf_use_s2(FALSE)
  on.exit(sf::sf_use_s2(old))
  b <- ler_biomas(biomas_path) |>
    sf::st_simplify(dTolerance = 5000, preserveTopology = TRUE) |>
    sf::st_transform(4326) |>
    sf::st_set_precision(1000) |>          # 3 casas decimais (~100 m), aplicadas antes de validar
    sf::st_make_valid() |>
    poligonos()
  names(b)[1] <- "bioma"
  if (file.exists(destino)) file.remove(destino)
  sf::st_write(b, destino, driver = "GeoJSON", quiet = TRUE, layer_options = "RFC7946=YES")
  destino
}
