test_that("parse_assinatura separa sobrenome e iniciais, descartando partículas", {
  x <- parse_assinatura(c("TAVARES, S. C. C. de H.", "OIANO NETO, J.", "SOSA-GOMES, D.", "SOUZA, K. X. S. de"))
  expect_equal(x$sobrenome, c("TAVARES", "OIANO NETO", "SOSA GOMES", "SOUZA"))
  expect_equal(x$iniciais, c("SCCH", "J", "D", "KXS"))
})

test_that("parse_assinatura descarta partículas em maiúsculas, mas mantém iniciais isoladas", {
  x <- parse_assinatura(c("SANTOS, M. DOS", "OLIVEIRA, R. F. DE", "ANJOS, L. H. C. DOS", "SILVA, M. A. D."))
  expect_equal(x$iniciais, c("M", "RF", "LHC", "MAD"))
})

test_that("assinatura_de_nome trata sufixos como parte do sobrenome", {
  x <- assinatura_de_nome(c("Maria Aparecida da Silva", "Paulo Sergio de Paula Herrmann Junior"))
  expect_equal(x$sobrenome, c("SILVA", "HERRMANN JUNIOR"))
  expect_equal(x$iniciais, c("MA", "PSP"))
})

test_that("compat_iniciais distingue exata, compatível e incompatível", {
  expect_equal(compat_iniciais(c("MA", "MS", "MA", "JD", "MAD"), c("MA", "MAS", "MS", "JE", "MA")),
               c("exata", "compativel", "incompativel", "incompativel", "compativel"))
})

test_that("nomes_compativeis aceita abreviações e rejeita nomes diferentes", {
  tk <- function(x) tokens_nome(x)[[1]]
  expect_true(nomes_compativeis(tk("CLAUDIO CESAR DE A BUSCHINELLI"), tk("Claudio Cesar de Almeida Buschinelli")))
  expect_true(nomes_compativeis(tk("PAULO SERGIO DE P HERRMANN JR"), tk("Paulo Sergio de Paula Herrmann Junior")))
  expect_false(nomes_compativeis(tk("MARIA APARECIDA SILVA"), tk("MARIA HELENA SILVA")))
  expect_false(nomes_compativeis(tk("JOAO SILVA"), tk("JOSE SILVA")))
})

test_that("formatar_nome mantém partículas em minúsculas", {
  expect_equal(formatar_nome("MARIA APARECIDA DA SILVA"), "Maria Aparecida da Silva")
})
