# Execução dos passos em Python (camada semântica) a partir do {targets} --------

# Interpretador do ambiente .venv-nlp (ver pipeline/py/requirements-nlp.txt)
python_nlp <- function() {
  p <- if (.Platform$OS.type == "windows") ".venv-nlp/Scripts/python.exe" else ".venv-nlp/bin/python"
  if (!file.exists(p)) stop("Ambiente Python não encontrado em ", p, ". Veja pipeline/py/requirements-nlp.txt.")
  p
}

# Roda um script e devolve os arquivos que ele produz (para format = "file").
# `...` recebe as dependências (entradas) apenas para o {targets} ordenar os passos.
rodar_python <- function(script, saidas, args = character(), ...) {
  # (o argumento env= de system2 não funciona no Windows)
  antigo <- Sys.getenv("PYTHONIOENCODING", unset = NA)
  Sys.setenv(PYTHONIOENCODING = "utf-8")
  on.exit(if (is.na(antigo)) Sys.unsetenv("PYTHONIOENCODING") else Sys.setenv(PYTHONIOENCODING = antigo))
  status <- system2(python_nlp(), c(shQuote(script), args))
  if (!identical(status, 0L)) stop("Falha ao executar ", script, " (código ", status, ")")
  faltam <- saidas[!file.exists(saidas)]
  if (length(faltam)) stop(script, " não gerou: ", paste(faltam, collapse = ", "))
  saidas
}
