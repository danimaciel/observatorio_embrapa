# Conferência independente dos números do app do Observatório ------------------------------
#
# Lê o banco do app (data/processed/observatorio_app.duckdb) direto, sem passar pelo app, e imprime
# os totais que cada página deve mostrar. Serve para conferir à mão o que aparece na tela.
#
# Uso (na raiz do projeto):
#   Rscript tests/conferir_numeros.R               # acervo completo (o período padrão do app)
#   Rscript tests/conferir_numeros.R 2000 2010     # um período escolhido na barra lateral
#
# Regras do app (desde 21/10/2026):
#   - O banco é um só: observatorio_app.duckdb (o publicado na release dados-AAAA-MM).
#   - Todas as páginas usam o período da barra lateral; o padrão é o acervo completo (do primeiro ao
#     último ano do banco). A capa (Visão geral) e a página Embrapa mostram, portanto, os mesmos totais.
#   - Exceção declarada na tela: a Visão por programação mostra sempre "todo o acervo" e "desde 2024".
#   - Publicações e tecnologias contam pelo ano; projetos pelo ano de início.

con <- DBI::dbConnect(duckdb::duckdb(), "data/processed/observatorio_app.duckdb", read_only = TRUE)
on.exit(DBI::dbDisconnect(con, shutdown = TRUE))

anos <- DBI::dbGetQuery(con, "select min(ano) a0, max(ano) a1 from documento")
args <- as.integer(commandArgs(trailingOnly = TRUE))
periodo <- if (length(args) == 2) args else c(anos$a0, anos$a1)
meta <- DBI::dbGetQuery(con, "select * from meta")

cat(sprintf("Banco: exportação %s, processado em %s\n", meta$exportacao, meta$gerado_em))
cat(sprintf("Acervo completo: %d–%d · período conferido: %d–%d\n\n", anos$a0, anos$a1, periodo[1], periodo[2]))

# 1. Totais por tipo no período: os números da capa (Visão geral) e da página Embrapa
tot <- DBI::dbGetQuery(con, "
  select tipo_doc, count(*) n from documento where ano between ? and ? group by 1 order by 1",
  params = list(periodo[1], periodo[2]))
cat("Totais por tipo no período (capa e página Embrapa devem mostrar estes):\n")
print(tot, row.names = FALSE)

# 2. Como o período muda o total de publicações (explica diferenças entre recortes)
faixas <- DBI::dbGetQuery(con, "
  select count(*) filter (where ano < 1970)                total_antes_1970,
         count(*) filter (where ano between 1970 and 1989) total_1970_1989,
         count(*) filter (where ano between 1990 and 2026) total_1990_2026,
         count(*) filter (where ano > 2026)                total_depois_2026,
         count(*)                                           total
  from documento where tipo_doc = 'publicacao'")
cat("\nPublicações por faixa de ano (acervo completo):\n")
print(faixas, row.names = FALSE)

# 3. Indicadores da capa que são proporções do período
pct <- DBI::dbGetQuery(con, "
  with d as (select doc_uid from documento where ano between ? and ?)
  select (select count(*) from d) documentos,
         (select count(distinct p.doc_uid) from doc_produto p join d using (doc_uid) where p.forca = 'principal') com_produto,
         (select count(distinct l.doc_uid) from doc_localizacao l join d using (doc_uid) where l.fonte <> 'sede_unidade') com_local_citado,
         (select count(distinct du.unidade_id) from documento_unidade du join d using (doc_uid)) unidades",
  params = list(periodo[1], periodo[2]))
cat(sprintf("\nCapa: %d unidades com produção · %.0f%% com produto agropecuário · %.0f%% com local citado no texto\n",
            pct$unidades, 100 * pct$com_produto / pct$documentos, 100 * pct$com_local_citado / pct$documentos))
