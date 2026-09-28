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
message("Pronto. Ajuste EXPORTACAO em _targets.R (se mudou) e rode targets::tar_make().")
