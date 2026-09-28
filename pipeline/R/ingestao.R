# Leitura das exportações com verificação de integridade ----------------------

caminho_raw <- function(exportacao, base) {
  arq <- switch(base,
    projetos     = sprintf("projetos-da-embrapa-%s.csv", exportacao),
    publicacoes  = sprintf("publicacoes-da-embrapa-%s.csv", exportacao),
    tecnologias  = sprintf("solucoes-tecnologicas-da-embrapa-%s.csv", exportacao),
    autores      = "AutorPessoalEmbrapa.xls"
  )
  p <- file.path("data", "raw", exportacao, arq)
  if (!file.exists(p)) stop("Arquivo não encontrado: ", p)
  p
}

# Lê um CSV exportado do portal. Um arquivo íntegro termina com aspas
# (fim do último campo) e tem número par de aspas. Se estiver truncado:
# erro, ou — com permitir_truncado = TRUE — descarta o último registro
# incompleto e segue com aviso.
ler_csv_exportacao <- function(path, permitir_truncado = FALSE) {
  txt <- readr::read_file(path)
  fim_ok <- grepl('"\\s*$', stringi::stri_sub(txt, -20))
  aspas_pares <- stringi::stri_count_fixed(txt, '"') %% 2 == 0
  truncado <- !(fim_ok && aspas_pares)
  if (truncado) {
    msg <- sprintf("Arquivo truncado: %s (termina no meio de um registro).", basename(path))
    if (!permitir_truncado) stop(msg, " Reexporte a base.")
    warning(msg, " O último registro incompleto foi descartado.")
    txt <- stringi::stri_sub(txt, 1, stringi::stri_locate_last_fixed(txt, '\n"')[1, 1])
  }
  df <- readr::read_csv(I(txt), col_types = readr::cols(.default = "c"),
                        na = c("", "NA"), progress = FALSE)
  names(df) <- janitor::make_clean_names(names(df))
  attr(df, "truncado") <- truncado
  attr(df, "arquivo") <- basename(path)
  df
}

# A matrícula é descartada já na leitura: não entra em nenhum artefato (LGPD).
ler_autores <- function(path) {
  df <- readxl::read_excel(path, col_types = "text")
  names(df) <- janitor::make_clean_names(names(df))
  dplyr::select(df, -dplyr::any_of("matricula"))
}

exigir_colunas <- function(df, cols) {
  faltam <- setdiff(cols, names(df))
  if (length(faltam)) stop("Colunas ausentes em ", attr(df, "arquivo"), ": ", paste(faltam, collapse = ", "))
  invisible(df)
}
