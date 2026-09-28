# Download das exportações mensais publicadas no Redape (Dataverse da Embrapa) ---
# Cada base é um dataset com um arquivo por mês ("<prefixo>-AAAA-MM"). Baixa-se
# o formato original (CSV), com retomada se a conexão cair, e o arquivo só é
# aceito se o tamanho bater com o informado pelo Redape.

REDAPE_URL <- "https://www.redape.dados.embrapa.br"
REDAPE_BASES <- list(
  projetos    = list(doi = "doi:10.48432/EZDXWF", prefixo = "projetos-da-embrapa"),
  publicacoes = list(doi = "doi:10.48432/TRBT0S", prefixo = "publicacoes-da-embrapa"),
  tecnologias = list(doi = "doi:10.48432/ZQE5FV", prefixo = "solucoes-tecnologicas-da-embrapa")
)

# Metadados do arquivo "<prefixo>-<exportacao>" na última versão do dataset
redape_arquivo <- function(base, exportacao) {
  cfg <- REDAPE_BASES[[base]]
  url <- sprintf("%s/api/datasets/:persistentId/?persistentId=%s", REDAPE_URL, cfg$doi)
  meta <- jsonlite::fromJSON(url, simplifyVector = FALSE)
  alvo <- sprintf("%s-%s", cfg$prefixo, exportacao)
  for (f in meta$data$latestVersion$files) {
    df <- f$dataFile
    if (tools::file_path_sans_ext(df$filename) == alvo) {
      return(list(id = df$id, nome = paste0(alvo, ".csv"),
                  tamanho = as.numeric(df$originalFileSize %||% df$filesize)))
    }
  }
  disponiveis <- vapply(meta$data$latestVersion$files, function(f) f$dataFile$filename, "")
  stop(sprintf("Exportação %s não encontrada no Redape para %s. Mais recente: %s",
               exportacao, base, utils::tail(sort(disponiveis), 1)))
}

# Baixa uma base para data/raw/<exportacao>/. Idempotente: se o arquivo já
# existe com o tamanho correto, não baixa de novo.
baixar_redape <- function(base, exportacao, dir_raw = "data/raw", tentativas = 8) {
  arq <- redape_arquivo(base, exportacao)
  destino <- file.path(dir_raw, exportacao, arq$nome)
  dir.create(dirname(destino), recursive = TRUE, showWarnings = FALSE)
  if (file.exists(destino) && file.size(destino) == arq$tamanho) {
    message(sprintf("✔ %s já está completo (%s)", arq$nome, formatar_mb(arq$tamanho)))
    return(invisible(destino))
  }
  parte <- paste0(destino, ".part")
  url <- sprintf("%s/api/access/datafile/%s?format=original", REDAPE_URL, arq$id)
  message(sprintf("↓ %s (%s)", arq$nome, formatar_mb(arq$tamanho)))
  for (i in seq_len(tentativas)) {
    # -C - retoma de onde parou; cada tentativa tem até 15 minutos
    status <- system2("curl", c("-sS", "-L", "-C", "-", "--max-time", "900", "-o", shQuote(parte), shQuote(url)))
    obtido <- if (file.exists(parte)) file.size(parte) else 0
    if (obtido == arq$tamanho) break
    if (obtido > arq$tamanho) {
      file.remove(parte)
      stop("Arquivo maior que o esperado; download descartado: ", arq$nome)
    }
    message(sprintf("  tentativa %d interrompida em %s; retomando…", i, formatar_mb(obtido)))
  }
  if (!file.exists(parte) || file.size(parte) != arq$tamanho) {
    stop(sprintf("Download incompleto de %s após %d tentativas. Rode de novo para retomar.", arq$nome, tentativas))
  }
  if (file.exists(destino)) file.rename(destino, paste0(destino, ".anterior"))
  file.rename(parte, destino)
  message(sprintf("✔ %s", destino))
  invisible(destino)
}

formatar_mb <- function(bytes) sprintf("%.1f MB", bytes / 1024^2)
