# Gera as tabelas de referência da programação a partir de fontes oficiais:
#   ref/objetivos_estrategicos.csv  — 7 objetivos finalísticos do Plano Diretor 2024–2030 e suas especificações
#   ref/portfolios.csv              — 9 portfólios (caracterização do Portal Embrapa)
# Fontes:
#   EMBRAPA. Plano Diretor da Embrapa: 2024–2030. Brasília, DF: Embrapa, 2024. (texto extraído do PDF em
#   data/raw/plano_diretor/plano_diretor_2024_2030.txt, fora do git; páginas 28–34)
#   EMBRAPA. Portfólios. https://www.embrapa.br/pesquisa/portfolios (acesso em 18 out. 2026)
# Uso: Rscript ref/fontes/gerar_ref_programacao.R

txt <- readLines("data/raw/plano_diretor/plano_diretor_2024_2030.txt", encoding = "UTF-8")
ini <- grep("^=== p34 ===", txt); fim <- grep("^=== p41 ===", txt)
corpo <- txt[ini:(fim - 1)]
corpo <- corpo[!grepl("^=== p|^PLANO DIRETOR DA EMBRAPA|^\\d{2}$|^Especificações", corpo)]
corpo <- paste(corpo, collapse = "\n")
corpo <- gsub("-\n", "", corpo)                       # hifenização de fim de linha
corpo <- gsub("\\s+", " ", corpo)

# Objetivos finalísticos: título e enunciado como no Plano Diretor (os enunciados são removidos do corpo
# antes de separar as especificações, porque a diagramação os intercala entre elas).
oe <- data.frame(
  objetivo_id = sprintf("O%02d", 1:7),
  objetivo = c("Produção Sustentável e Competitividade", "Recursos Naturais e Mudança do Clima",
               "Tendências de Consumo e Agregação de Valor", "Segurança Alimentar e Saúde Única",
               "Bioeconomia e Economia Circular", "Inclusão Socioprodutiva e Digital",
               "Tecnologias Emergentes e Disruptivas"),
  enunciado = c(
    "Gerar soluções tecnológicas e oportunidades de inovação para promover a sustentabilidade, a produtividade e a competitividade da agropecuária nacional.",
    "Gerar conhecimentos, tecnologias e informações para o uso racional dos recursos naturais dos biomas brasileiros e o enfrentamento e mitigação das mudanças do clima.",
    "Gerar conhecimentos e tecnologias que promovam a agregação de valor e a diversificação de produtos, processos e serviços oriundos das cadeias agropecuárias, florestais e agroindustriais, explorando as novas tendências de consumo.",
    "Fortalecer a capacidade de apoio à segurança e soberania alimentar e à Saúde Única, gerando alimentos saudáveis em sistemas agrícolas sustentáveis.",
    "Desenvolver tecnologias e conhecimentos que contribuam para os diferentes potenciais da bioeconomia brasileira, por meio da agregação de valor a produtos da sociobiodiversidade, do aproveitamento de coprodutos e resíduos, da geração de bioprodutos, bioinsumos e energia renovável, da redução de emissões de GEEs e do uso eficiente dos recursos naturais.",
    "Gerar e compartilhar conhecimento, práticas produtivas e alternativas tecnológicas voltadas para a inclusão socioprodutiva e digital, visando à transição agroecológica e ao desenvolvimento territorial sustentável.",
    "Contribuir para uma agricultura sustentável de futuro a partir da ampliação da produção de conhecimento em tecnologias emergentes e disruptivas."),
  stringsAsFactors = FALSE)
for (i in seq_len(nrow(oe))) {
  corpo <- sub(paste(oe$objetivo[i], oe$enunciado[i]), " ", corpo, fixed = TRUE)
  corpo <- sub(oe$objetivo[i], " ", corpo, fixed = TRUE)
}
corpo <- gsub("\\s+", " ", corpo)

espec <- list(
  O01 = c("Aumento de eficiência produtiva", "Aplicação de novas tecnologias", "Métricas e indicadores de sustentabilidade"),
  O02 = c("Redução da pressão sobre os biomas", "Tecnologias para adaptação à mudança do clima",
          "Agricultura conservacionista", "Dados dos recursos naturais",
          "Paisagem agrícola, biodiversidade e serviços ecossistêmicos", "Conservação de recursos genéticos",
          "Práticas resilientes"),
  O03 = c("Demandas por novos produtos alimentares", "Tecnologias relacionadas a fontes de proteínas",
          "Agregação de valor ao modo de produção e/ou território", "Valorização de atributos relacionados à sustentabilidade"),
  O04 = c("Parcerias para o acesso ao alimento de qualidade", "Redução de perdas e desperdício de alimentos",
          "Dieta brasileira", "Agricultura urbana e periurbana", "Acesso equitativo a tecnologias",
          "Apoio à defesa agropecuária", "Produção de alimentos seguros", "Abordagens para Saúde Única"),
  O05 = c("Potencial da biodiversidade", "Agricultura e bioeconomia", "Bioeconomia na Amazônia", "Bioinsumos",
          "Energias renováveis", "Multifuncionalidade da agricultura"),
  O06 = c("Políticas públicas e desenvolvimento territorial", "Transição agroecológica", "Nichos de inovação locais",
          "Plataformas colaborativas regionais", "Capacitação tecnológica", "Inclusão digital",
          "Automação para pequena escala"),
  O07 = c("Automação, agricultura de precisão e digital", "Aplicações da inteligência artificial",
          "Áreas portadoras de futuro"))

titulos <- unlist(espec)
pos <- vapply(titulos, function(t) regexpr(paste0(t, ":"), corpo, fixed = TRUE)[1], numeric(1))
if (any(pos < 0)) stop("Especificação não encontrada no texto: ", paste(titulos[pos < 0], collapse = "; "))
ordem <- order(pos)
pos_ord <- pos[ordem]
txt_esp <- vapply(seq_along(ordem), function(k) {
  a <- pos_ord[k] + nchar(titulos[ordem][k]) + 1
  b <- if (k < length(ordem)) pos_ord[k + 1] - 1 else nchar(corpo)
  trimws(substr(corpo, a, b))
}, character(1))
esp <- data.frame(especificacao = titulos[ordem], texto = txt_esp, stringsAsFactors = FALSE)
esp$objetivo_id <- rep(names(espec), lengths(espec))[match(esp$especificacao, titulos)]
esp <- esp[order(esp$objetivo_id, match(esp$especificacao, titulos)), ]
esp$especificacao_id <- ave(esp$objetivo_id, esp$objetivo_id, FUN = function(x) sprintf("%s.%d", x, seq_along(x)))

out <- merge(oe, esp, by = "objetivo_id")
out <- out[order(out$especificacao_id), c("objetivo_id", "objetivo", "enunciado", "especificacao_id",
                                          "especificacao", "texto")]
out$fonte <- "EMBRAPA. Plano Diretor da Embrapa: 2024–2030. Brasília, DF: Embrapa, 2024. p. 28–34"
out$status <- "oficial"
readr::write_csv(out, "ref/objetivos_estrategicos.csv")
cat(nrow(out), "especificações em", length(unique(out$objetivo_id)), "objetivos\n")
print(table(out$objetivo_id))
cat("\nMaior e menor texto:", range(nchar(out$texto)), "\n")

# Portfólios: caracterização transcrita do Portal Embrapa (sem nomes nem e-mails de pessoas).
# `portfolio` = nome usado na planilha de desafios (ref/programacao_desafios.csv), para o cruzamento.
port <- data.frame(
  portfolio_id = c("prosur", "ecoclima", "consumidor", "bioeficiencia", "biodiversidade", "everde",
                   "agroecois", "biorrevolucao", "agrodigital"),
  portfolio = c("Sistemas de Produção Sustentáveis e Resilientes", "Clima, recursos naturais e transformação ecológica",
                "Protagonismo do Consumidor", "Bioeficiência na Agropecuária", "Economia da Biodiversidade",
                "Economia Verde", "Agroecologia e Inclusão Socioprodutiva", "Biorrevolução",
                "Transformação Digital no Agro"),
  nome_portal = c("Sistemas de Produção Sustentáveis e Resilientes", "Clima, recursos naturais e transformação ecológica",
                  "Protagonismo do consumidor", "Bioeficiência na agropecuária", "Economia da biodiversidade",
                  "Economia verde", "Agroecologia e Inclusão Socioprodutiva", "Biorrevolução",
                  "Transformação digital na agropecuária"),
  caracterizacao = c(
    "Focado na adequação dos processos produtivos com vistas à segurança alimentar e ao desenvolvimento sustentável para obtenção de produtos vegetais e animais com qualidade e com níveis de resíduos de agrotóxicos e contaminantes em conformidade com o que estabelece a legislação sanitária, mediante a aplicação de boas práticas agrícolas. O propósito é favorecer o uso de recursos naturais e a substituição de insumos poluentes, garantindo a sustentabilidade e a rastreabilidade da produção agropecuária, associados ao aumento de eficiência produtiva com aplicação de novas tecnologias, métricas, indicadores voltados para a competitividade e a sustentabilidade.",
    "Focado no enfrentamento dos desafios ambientais e na promoção do desenvolvimento sustentável, com ênfase na redução da pressão sobre os biomas na busca pela preservação ambiental e na viabilização de tecnologias adaptativas no combate às mudanças climáticas. É apoiado no conhecimento, mapeamento e monitoramento nos diversos níveis escalares e espaciais dos recursos naturais (solo, água, biodiversidade, florestas e recursos minerais), ancorados em plataformas de dados territoriais, por bioma, por regiões, por estados ou municípios. O portfólio está também associado a dados de recursos naturais confrontados com dados de uso da terra para gerar informações sobre os serviços ecossistêmicos, ambientais e agroambientais, propondo soluções e políticas públicas para adequação do território visando conciliar desenvolvimento econômico com preservação ambiental e garantir um futuro mais sustentável para o Brasil.",
    "Focado na oferta de produtos, processos e sistemas conexos e perceptíveis pelos consumidores às novas tendências do mercado, alinhados aos conceitos de saudabilidade, sustentabilidade, acessibilidade, rastreabilidade, certificação, segurança do consumidor, qualidade nutricional, funcional ou sensorial, novas fontes proteicas e práticas de produção e processamento relacionados ao bem estar animal. A ênfase do portfólio reflete o movimento crescente de protagonismo do consumidor na definição dos atributos de obtenção, logística e processamento de alimentos e outros produtos agropecuários que afetam diretamente os sistemas de produção, a tomada de decisão de compra e recompra e os mecanismos de agregação de valor.",
    "Focado no desenvolvimento de uma agricultura mais sustentável, equilibrando produtividade, qualidade e cuidado com o meio ambiente com vistas a segurança alimentar e saúde única. Promover a redução do desperdício de alimentos em toda as etapas da cadeia de produção agroalimentar. Interconectar a saúde humana vs plantas vs animais vs meio ambiente propondo soluções tecnológicas para o setor agropecuário com menor uso de insumos químicos, plantas mais resistentes a pragas e doenças, biofortificação de alimentos, revitalização dos solos. E apoiar à segurança e defesa zoofitossanitária e políticas públicas associadas.",
    "Tem como foco fortalecer o potencial da agricultura com equilíbrio ao meio ambiente ofertando novos produtos da biodiversidade e compostos bioativos derivados (cosméticos, fármacos e medicinais) incluindo produtos florestais madeireiros e não madeireiros. Contribuir para o uso sustentável dos recursos da sociobiodiversidade e seus usos potenciais dos Biomas Amazônia, Caatinga, Cerrado, Pantanal, Pampa e Mata Atlântica.",
    "Tem como foco fortalecer o potencial da agricultura com equilíbrio ao meio ambiente ofertando novos produtos a partir de biomassa e resíduos agrícolas e agroindustriais (por exemplo: novos materiais, químicos, biocombustíveis), estabelecendo novos vínculos entre a agricultura e a indústria. Objetiva ainda ampliar o uso de bioinsumos utilizados na agricultura e na produção de alimentos para melhorar a saúde do solo; aumentar a produtividade e reduzir o impacto ambiental (por exemplo: fertilizantes orgânicos, biopesticidas e biofertilizantes); e gerar produtos e tecnologias para o desenvolvimento e uso de energias renováveis.",
    "Tem como foco contribuir para a geração de soluções tecnológicas inovadoras em sistemas agroecológicos ou orgânicos de produção de alimentos, que preservem e melhorem a saúde de produtores e consumidores, possibilitando o uso racional dos recursos naturais e socioeconômicos disponíveis, de forma a ampliar a sustentabilidade social, econômica e ecológica da agricultura com vistas ao desenvolvimento territorial. Este portfólio é fortalecido por plataformas colaborativas regionais com diversos atores, como por exemplo as redes sociotécnicas, e orientado pelo objetivo de fortalecer ou promover processos que acarretem em mudança social.",
    "Tem como foco os avanços das ciências biológicas, que, associados ao desenvolvimento acelerado das tecnologias de informação, comunicação, emergentes e disruptivas viabilizando a redução de impactos ambientais, gestão territorial, descarbonização e rastreabilidade. Destacam-se os temas relacionados aos avanços: em tecnologias genéticas; uso da genômica e melhoramento de precisão; inovações em biossistemas de precisão; microbioma de plantas e animais para a sustentabilidade no agro; novos insumos em expansão, dentre outros o uso da nanotecnologia no agro. Associado ao conhecimento das aplicações de Inteligência Artificial visando acelerar a sistematização das informações sobre os recursos naturais dos biomas / territórios / regiões / municípios conexas as cadeias produtivas respectivas com vistas a geração de alertas se aquela porção do território está sendo usada de forma sustentável e de acordo com sua capacidade vocacional.",
    "Tem como foco modernizar e otimizar o setor agropecuário – denominada Agricultura Digital (AD). Várias tecnologias digitais estão desempenhando um papel significativo nesta transformação com a incorporação de conceitos da indústria 4.0 e de tecnologias como a computação em Nuvem: sistemas robóticos, Internet das Coisas (IoT) e Sensores, Inteligência Artificial (IA), Plataformas Virtuais e Aplicativos, Automação, Rastreabilidade, Certificação e Sustentabilidade. A transformação digital na agropecuária, a automação agrícola e a agricultura de precisão e agricultura digital não apenas aumentam a produtividade, mas também contribuem para a sustentabilidade e a segurança alimentar. Associado a acessibilidade, interoperabilidade e reprodutividade de dados abertos seguindo a tendência atual de gestão e compartilhamento em plataformas colaborativas com uso de arquiteturas big data e ferramentas de mineração de dados."),
  stringsAsFactors = FALSE)
des <- readr::read_csv("ref/programacao_desafios.csv", show_col_types = FALSE)
stopifnot(setequal(port$portfolio, unique(des$portfolio)))      # mesmos 9 portfólios da planilha
# objetivos a que cada portfólio se liga pelos desafios (nº de desafios por objetivo)
lig <- aggregate(desafio_id ~ portfolio + objetivo_id, des, length)
port$objetivos_por_desafios <- vapply(port$portfolio, function(p) {
  l <- lig[lig$portfolio == p, ]; l <- l[order(-l$desafio_id), ]
  paste0(l$objetivo_id, " (", l$desafio_id, ")", collapse = "; ")
}, character(1))
port$n_desafios <- as.integer(table(des$portfolio)[port$portfolio])
port$fonte <- "EMBRAPA. Portfólios. Disponível em: https://www.embrapa.br/pesquisa/portfolios. Acesso em: 18 out. 2026"
port$status <- "oficial"
readr::write_csv(port, "ref/portfolios.csv")
print(port[, c("portfolio_id", "n_desafios", "objetivos_por_desafios")])
