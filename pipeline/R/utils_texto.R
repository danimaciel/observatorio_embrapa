# Normalização de texto, nomes e assinaturas bibliográficas ------------------

PARTICULAS <- c("DE", "DA", "DO", "DAS", "DOS", "E", "D", "DI", "DU", "DEL",
                "DELLA", "VAN", "VON", "DER", "LA", "LE")
SUFIXOS <- c("JUNIOR", "FILHO", "NETO", "SOBRINHO")

sem_acento <- function(x) stringi::stri_trans_general(x, "Latin-ASCII")

# "Maria Aparecida da Silva" -> "MARIA APARECIDA DA SILVA"
norm_nome <- function(x) {
  x <- toupper(sem_acento(x))
  x <- stringr::str_replace_all(x, "[^A-Z ]", " ")
  stringr::str_squish(x)
}

# Chave de junção para títulos e palavras-chave
norm_titulo <- function(x) {
  x <- tolower(sem_acento(x))
  x <- stringr::str_replace_all(x, "[^a-z0-9 ]", " ")
  stringr::str_squish(x)
}

# Tokens de um nome completo, sem partículas e com sufixos padronizados
tokens_nome <- function(x) {
  tk <- stringr::str_split(norm_nome(x), " ")
  lapply(tk, function(t) {
    t <- t[nzchar(t) & !(t %in% PARTICULAS)]
    t[t == "JR"] <- "JUNIOR"
    t[t == "FO"] <- "FILHO"
    t[t == "NETTO"] <- "NETO"
    t
  })
}

# "TAVARES, S. C. C. de H." -> sobrenome "TAVARES", iniciais "SCCH".
# Partículas são descartadas: em minúsculas ("de", "dos") e também quando
# vêm por extenso em maiúsculas ("SANTOS, M. DOS" -> iniciais "M", e não "MD").
# Uma letra isolada ("D.") continua sendo inicial.
PARTICULAS_ASSINATURA <- c("DE", "DA", "DO", "DAS", "DOS", "DI", "DU", "DEL", "DELLA", "VAN", "VON", "DER")
parse_assinatura <- function(x) {
  x <- stringr::str_squish(x)
  tem_virgula <- stringr::str_detect(x, ",")
  sob <- ifelse(tem_virgula, stringr::str_remove(x, ",.*$"), x)
  resto <- ifelse(tem_virgula, sem_acento(stringr::str_remove(x, "^[^,]*,")), "")
  toks <- stringr::str_split(resto, "[\\s\\.\\-]+")
  ini <- vapply(toks, function(t) {
    t <- t[nzchar(t) & grepl("^[A-Z]", t) & !(toupper(t) %in% PARTICULAS_ASSINATURA)]
    paste(substr(t, 1, 1), collapse = "")
  }, character(1))
  tibble::tibble(sobrenome = norm_nome(sob), iniciais = ini)
}

# Assinatura esperada a partir do nome completo:
# "PAULO SERGIO DE PAULA HERRMANN JUNIOR" -> "HERRMANN JUNIOR", "PSP"
assinatura_de_nome <- function(nome) {
  tk <- tokens_nome(nome)
  n <- lengths(tk)
  composto <- n >= 3 & vapply(tk, function(t) length(t) > 0 && t[length(t)] %in% SUFIXOS, logical(1))
  k <- ifelse(composto, 2L, 1L)
  sob <- mapply(function(t, k) if (length(t)) paste(utils::tail(t, k), collapse = " ") else NA_character_, tk, k)
  ini <- mapply(function(t, k) {
    r <- utils::head(t, max(length(t) - k, 0))
    paste(substr(r, 1, 1), collapse = "")
  }, tk, k)
  tibble::tibble(sobrenome = unname(sob), iniciais = unname(ini))
}

# Compatibilidade entre iniciais: "exata" (MA = MA), "compativel" (a mais curta
# é subsequência da mais longa começando pela mesma letra: MS ~ MAS) ou "incompativel".
compat_iniciais <- function(a, b) {
  curta <- ifelse(nchar(a) <= nchar(b), a, b)
  longa <- ifelse(nchar(a) <= nchar(b), b, a)
  padrao <- paste0("^", stringi::stri_replace_all_regex(curta, "(?<=.)(?=.)", ".*"))
  sub <- nzchar(curta) & stringi::stri_detect_regex(longa, padrao)
  dplyr::case_when(a == b ~ "exata", sub ~ "compativel", TRUE ~ "incompativel")
}

# Dois nomes completos (vetores de tokens sem partículas) são compatíveis quando
# têm o mesmo primeiro e último token e os tokens do meio do nome mais curto
# aparecem, em ordem, no mais longo — por extenso ou como inicial.
# "CLAUDIO CESAR A BUSCHINELLI" ~ "CLAUDIO CESAR ALMEIDA BUSCHINELLI"
nomes_compativeis <- function(a, b) {
  if (length(a) < 2 || length(b) < 2) return(FALSE)
  if (a[1] != b[1] || a[length(a)] != b[length(b)]) return(FALSE)
  if (length(a) > length(b)) { tmp <- a; a <- b; b <- tmp }
  ma <- a[-c(1, length(a))]
  mb <- b[-c(1, length(b))]
  j <- 1
  for (t in ma) {
    achou <- FALSE
    while (j <= length(mb)) {
      u <- mb[j]
      j <- j + 1
      if (t == u || (nchar(t) == 1 && startsWith(u, t)) || (nchar(u) == 1 && startsWith(t, u))) {
        achou <- TRUE
        break
      }
    }
    if (!achou) return(FALSE)
  }
  TRUE
}

# "MARIA APARECIDA DA SILVA" -> "Maria Aparecida da Silva"
formatar_nome <- function(x) {
  x <- stringr::str_to_title(tolower(x))
  stringr::str_replace_all(x, "\\b(De|Da|Do|Das|Dos|E)\\b", tolower)
}

# Separa "a, b,, c" em vetor limpo
split_palavras_chave <- function(x) {
  lapply(stringr::str_split(dplyr::coalesce(x, ""), "[,;]"), function(k) {
    k <- stringr::str_squish(k)
    k[nzchar(k)]
  })
}
