# Baixa do Redape as exportações de projetos, publicações e tecnologias.
#
# Uso (na raiz do projeto):
#   Rscript pipeline/baixar_dados.R 2026-10
# Sem argumento, usa a EXPORTACAO definida em _targets.R.
#
# A base de pessoas (AutorPessoalEmbrapa.xls) é interna e não está no Redape:
# copie-a manualmente para data/raw/<exportacao>/.

source("pipeline/R/redape.R", encoding = "UTF-8")

args <- commandArgs(trailingOnly = TRUE)
exportacao <- if (length(args)) args[1] else {
  linha <- grep("^EXPORTACAO <-", readLines("_targets.R", encoding = "UTF-8"), value = TRUE)
  sub('.*"(.*)".*', "\\1", linha)
}
if (!grepl("^\\d{4}-\\d{2}$", exportacao)) stop("Exportação deve ter o formato AAAA-MM: ", exportacao)

message("Exportação ", exportacao)
for (base in names(REDAPE_BASES)) baixar_redape(base, exportacao)

autores <- file.path("data", "raw", exportacao, "AutorPessoalEmbrapa.xls")
if (!file.exists(autores)) {
  message("⚠ Falta a base de pessoas: copie AutorPessoalEmbrapa.xls para ", dirname(autores))
}
# Malhas geográficas (estáticas): baixadas só se faltarem.
ibge <- "https://servicodados.ibge.gov.br/api"
malha <- "/v3/malhas/paises/BR?formato=application/vnd.geo%2Bjson&qualidade=minima&intrarregiao="
geo <- c(
  br_uf.geojson = paste0(ibge, malha, "UF"),
  br_municipios.geojson = paste0(ibge, malha, "municipio"),
  municipios_ibge.json = paste0(ibge, "/v1/localidades/municipios"),
  biomas_2019_simplificado.gpkg = "https://www.ipea.gov.br/geobr/data_gpkg/biomes/2019/biomes_2019_simplified.gpkg"
)
dir.create(file.path("data", "raw", "geo"), recursive = TRUE, showWarnings = FALSE)
for (arq in names(geo)) {
  destino <- file.path("data", "raw", "geo", arq)
  if (!file.exists(destino)) {
    message("Baixando ", arq)
    utils::download.file(geo[[arq]], destino, mode = "wb", quiet = TRUE)
  }
}

message("Pronto. Ajuste EXPORTACAO em _targets.R (se mudou) e rode targets::tar_make().")
