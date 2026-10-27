"""Gera ref/produtos.csv: taxonomia de produtos agropecuários para marcar documentos.

Base oficial: categorias de produto do IBGE (SIDRA), guardadas em ref/ibge_produtos_sidra.json
  PAM 5457 (c782) lavouras temporárias e permanentes · PPM 3939 (c79) rebanhos · PPM 74 (c80) produtos de
  origem animal · PPM 3940 (c654) aquicultura · PEVS 289 (c193) extração vegetal · PEVS 291 (c194) silvicultura.
Grupo de atividade: CNAE 2.0 / Censo Agropecuário 2017 (oficial). Categoria ampla "Grãos" = cereais, leguminosas
e oleaginosas do LSPA/IBGE (oficial); "Pastagens e forrageiras" = Censo Agropecuário (oficial, uso da terra);
"Frutas", "Hortaliças", "Fibras", "Estimulantes" etc. = agrupamentos da lista PAM (proposta metodológica, em validação).
Termos de busca, nomes científicos e regras de contexto: proposta metodológica, em validação.

Rodar quando a taxonomia mudar:  python pipeline/py/produtos_taxonomia.py
Colunas de ref/produtos.csv:
  produto_id, produto, grupo_atividade, categoria_ampla, fonte_ibge (tabela:categoria; várias separadas por " | "),
  termos (separados por "|"; "*" no fim = qualquer terminação), contexto (se preenchido, o termo só conta com uma
  dessas palavras no mesmo texto), excluir (frases apagadas antes de procurar o produto), status
"""
import csv
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]

LT, LP, HO, PE, AQ, FP, FN = ("Lavoura temporária", "Lavoura permanente", "Horticultura e floricultura",
                              "Pecuária", "Aquicultura", "Produção florestal plantada", "Produção florestal nativa")
GR, FR, HT, FB, ES, OL, FO, CN = ("Grãos", "Frutas", "Hortaliças", "Fibras", "Estimulantes e especiarias",
                                  "Oleaginosas e palmeiras", "Pastagens e forrageiras", "Cana e energia")
PAM, REB, POA, AQT, PEX, PSI = ("PAM 5457", "PPM 3939", "PPM 74", "PPM 3940", "PEVS 289", "PEVS 291")

# (id, produto, grupo, categoria ampla, fontes IBGE, termos, científico, contexto)
P = [
    # ---- grãos (LSPA: cereais, leguminosas e oleaginosas)
    ("soja", "Soja", LT, GR, [f"{PAM}:Soja (em grão)"], "soja|sojicultor*|sojicultura", "Glycine max", ""),
    ("milho", "Milho", LT, GR, [f"{PAM}:Milho (em grão)", f"{PAM}:Milho verde"], "milho|milharal|milhos|milho verde", "Zea mays", ""),
    ("arroz", "Arroz", LT, GR, [f"{PAM}:Arroz (em casca)"], "arroz|rizicultura|orizicultura|arrozal", "Oryza sativa", ""),
    ("feijao", "Feijão", LT, GR, [f"{PAM}:Feijão (em grão)"], "feijao|feijoeiro*|feijao-caupi|caupi|feijao-de-corda|feijao comum", "Phaseolus vulgaris; Vigna unguiculata", ""),
    ("trigo", "Trigo", LT, GR, [f"{PAM}:Trigo (em grão)"], "trigo|triticultura|tritícola", "Triticum aestivum", ""),
    ("sorgo", "Sorgo", LT, GR, [f"{PAM}:Sorgo (em grão)"], "sorgo", "Sorghum bicolor", ""),
    ("aveia", "Aveia", LT, GR, [f"{PAM}:Aveia (em grão)"], "aveia|aveia-preta|aveia preta", "Avena", ""),
    ("cevada", "Cevada", LT, GR, [f"{PAM}:Cevada (em grão)"], "cevada", "Hordeum vulgare", ""),
    ("centeio", "Centeio", LT, GR, [f"{PAM}:Centeio (em grão)"], "centeio", "Secale cereale", ""),
    ("triticale", "Triticale", LT, GR, [f"{PAM}:Triticale (em grão)"], "triticale", "×Triticosecale", ""),
    ("amendoim", "Amendoim", LT, GR, [f"{PAM}:Amendoim (em casca)"], "amendoim", "Arachis hypogaea", ""),
    ("girassol", "Girassol", LT, GR, [f"{PAM}:Girassol (em grão)"], "girassol", "Helianthus annuus", ""),
    ("canola", "Canola", LT, GR, [f"{PAM}:Canola"], "canola", "Brassica napus", ""),
    ("mamona", "Mamona", LT, GR, [f"{PAM}:Mamona (baga)"], "mamona|mamoneira", "Ricinus communis", ""),
    ("gergelim", "Gergelim", LT, GR, [f"{PAM}:Gergelim"], "gergelim", "Sesamum indicum", ""),
    ("ervilha", "Ervilha", LT, GR, [f"{PAM}:Ervilha (em grão)"], "ervilha", "Pisum sativum", ""),
    ("fava", "Fava", LT, GR, [f"{PAM}:Fava (em grão)"], "fava|feijao-fava", "Phaseolus lunatus", ""),
    ("linho", "Linho", LT, GR, [f"{PAM}:Linho (semente)"], "linhaca|linho", "Linum usitatissimum", ""),
    ("algodao", "Algodão", LT, FB, [f"{PAM}:Algodão herbáceo (em caroço)", f"{PAM}:Algodão arbóreo (em caroço)"], "algodao|algodoeiro*|cotonicultura", "Gossypium hirsutum", ""),
    # ---- raízes e tubérculos
    ("mandioca", "Mandioca", LT, HT, [f"{PAM}:Mandioca"], "mandioca|aipim|macaxeira|mandiocultura|farinha de mandioca", "Manihot esculenta", ""),
    ("batata", "Batata", LT, HT, [f"{PAM}:Batata-inglesa"], "batata|batata-inglesa|bataticultura|batata-semente", "Solanum tuberosum", ""),
    ("batata_doce", "Batata-doce", LT, HT, [f"{PAM}:Batata-doce"], "batata-doce|batata doce", "Ipomoea batatas", ""),
    ("inhame", "Inhame", LT, HT, [f"{PAM}:Inhame"], "inhame|cara", "Dioscorea", "inhame|dioscorea|tuberculo"),
    # ---- hortaliças (PAM; CNAE 01.21 horticultura)
    ("tomate", "Tomate", LT, HT, [f"{PAM}:Tomate"], "tomate|tomateiro*|tomaticultura", "Solanum lycopersicum", ""),
    ("cebola", "Cebola", LT, HT, [f"{PAM}:Cebola"], "cebola", "Allium cepa", ""),
    ("alho", "Alho", LT, HT, [f"{PAM}:Alho"], "alho", "Allium sativum", ""),
    ("cenoura", "Cenoura", LT, HT, [f"{PAM}:Cenoura"], "cenoura", "Daucus carota", ""),
    ("alface", "Alface", LT, HT, [f"{PAM}:Alface"], "alface", "Lactuca sativa", ""),
    ("repolho", "Repolho", LT, HT, [f"{PAM}:Repolho"], "repolho|brassicas|couve", "Brassica oleracea", ""),
    ("pimentao", "Pimentão e pimentas", LT, HT, [f"{PAM}:Pimentão"], "pimentao|pimenta|pimentas|capsicum", "Capsicum", ""),
    ("abobora", "Abóbora", LT, HT, [f"{PAM}:Abóbora"], "abobora|moranga|cucurbitaceas", "Cucurbita", ""),
    ("chuchu", "Chuchu", LT, HT, [f"{PAM}:Chuchu"], "chuchu", "Sechium edule", ""),
    ("hortalicas", "Hortaliças (geral)", LT, HT, [], "hortalica*|olericultura|olericola*|horticultura|horta|hortas|verduras", "", ""),
    # ---- frutas (PAM)
    ("laranja", "Laranja e citros", LP, FR, [f"{PAM}:Laranja", f"{PAM}:Tangerina", f"{PAM}:Limão"], "laranja|laranjeira*|citros|citrus|citricultura|citricola*|tangerina|limao|lima acida|bergamota|mexerica", "Citrus", ""),
    ("banana", "Banana", LP, FR, [f"{PAM}:Banana (cacho)"], "banana|bananeira*|bananicultura", "Musa", ""),
    ("uva", "Uva", LP, FR, [f"{PAM}:Uva"], "uva|uvas|videira*|viticultura|vitivinicultura|vinhedo*|vinicola*|vitis", "Vitis", ""),
    ("maca", "Maçã", LP, FR, [f"{PAM}:Maçã"], "maca|macieira*|malus", "Malus domestica", "maca|macieira|pomar|fruta|malus"),
    ("manga", "Manga", LP, FR, [f"{PAM}:Manga"], "manga|mangueira*|mangicultura", "Mangifera indica", "fruta|fruto|frutifera|pomar|mangifera|mangicultura|tommy|palmer|exporta"),
    ("mamao", "Mamão", LP, FR, [f"{PAM}:Mamão"], "mamao|mamoeiro*", "Carica papaya", ""),
    ("abacaxi", "Abacaxi", LT, FR, [f"{PAM}:Abacaxi*"], "abacaxi|abacaxizeiro*|ananas", "Ananas comosus", ""),
    ("coco", "Coco", LP, FR, [f"{PAM}:Coco-da-baía*"], "coco|coqueiro*|coco-da-baia|cocos nucifera", "Cocos nucifera", ""),
    ("maracuja", "Maracujá", LP, FR, [f"{PAM}:Maracujá"], "maracuja|maracujazeiro*|passiflora", "Passiflora edulis", ""),
    ("caju", "Caju", LP, FR, [f"{PAM}:Caju", f"{PAM}:Castanha de caju", f"{PEX}:1.5 - Castanha-de-caju"], "caju|cajueiro*|castanha de caju|castanha-de-caju|cajucultura", "Anacardium occidentale", ""),
    ("acai", "Açaí", LP, FR, [f"{PAM}:Açaí", f"{PEX}:1.1 - Açaí (fruto)"], "acai|acaizeiro*|euterpe", "Euterpe oleracea", ""),
    ("cupuacu", "Cupuaçu", LP, FR, [f"{PAM}:Cupuaçu", f"{PEX}:1.7 - Cupuaçu (fruto)"], "cupuacu|cupuacuzeiro*|theobroma grandiflorum", "Theobroma grandiflorum", ""),
    ("goiaba", "Goiaba", LP, FR, [f"{PAM}:Goiaba"], "goiaba|goiabeira*", "Psidium guajava", ""),
    ("acerola", "Acerola", LP, FR, [f"{PAM}:Acerola"], "acerola|aceroleira*", "Malpighia emarginata", ""),
    ("abacate", "Abacate", LP, FR, [f"{PAM}:Abacate"], "abacate|abacateiro*", "Persea americana", ""),
    ("melancia", "Melancia", LT, FR, [f"{PAM}:Melancia"], "melancia", "Citrullus lanatus", ""),
    ("melao", "Melão", LT, FR, [f"{PAM}:Melão"], "melao|meloeiro*", "Cucumis melo", ""),
    ("morango", "Morango", LT, FR, [f"{PAM}:Morango"], "morango|morangueiro*", "Fragaria", ""),
    ("pessego", "Pêssego e frutas de caroço", LP, FR, [f"{PAM}:Pêssego", f"{PAM}:Marmelo", f"{PAM}:Pera"], "pessego|pessegueiro*|nectarina|ameixa|marmelo|pera|pereira", "Prunus persica", "fruta|fruto|frutifera|pomar|prunus|pyrus|pessego|ameixa"),
    ("figo", "Figo", LP, FR, [f"{PAM}:Figo"], "figo|figueira*", "Ficus carica", ""),
    ("caqui", "Caqui", LP, FR, [f"{PAM}:Caqui"], "caqui|caquizeiro*", "Diospyros kaki", ""),
    ("graviola", "Graviola e anonáceas", LP, FR, [f"{PAM}:Graviola"], "graviola|pinha|ata|fruta-do-conde|atemoia|anonaceas", "Annona", "graviola|anona|annona|atemoia|fruta"),
    ("azeitona", "Oliveira", LP, FR, [f"{PAM}:Azeitona"], "azeitona|oliveira*|olivicultura|azeite", "Olea europaea", "azeitona|olivicultura|azeite|olea|pomar|fruto"),
    ("noz", "Nozes", LP, FR, [f"{PAM}:Noz (fruto seco)"], "noz|nozes|nogueira-peca|noz-peca|pecan|macadamia", "Carya illinoinensis", ""),
    ("frutas", "Frutas (geral)", LP, FR, [], "fruticultura|frutifera*|frutas|fruteira*|frutícola*|pomar|pomares", "", ""),
    ("pupunha", "Pupunha", LP, FR, [f"{PEX}:1.15 - Pupunha (fruto)"], "pupunha|pupunheira*|bactris gasipaes", "Bactris gasipaes", ""),
    ("frutas_nativas", "Frutas nativas do Cerrado e Caatinga", FN, FR,
     [f"{PEX}:1.13 - Pequi (fruto)", f"{PEX}:1.11 - Mangaba (fruto)", f"{PEX}:1.17 - Umbu (fruto)", f"{PEX}:1.4 - Cajá (fruto)", f"{PEX}:1.3 - Buriti (fruto)", f"{PEX}:1.2 - Baru ou Cumaru (amêndoa)"],
     "pequi|pequizeiro*|mangaba|mangabeira*|umbu|umbuzeiro*|caja|cajazeira*|buriti|baru|cagaita|araticum|cumbaru", "", ""),
    # ---- estimulantes e especiarias
    ("cafe", "Café", LP, ES, [f"{PAM}:Café (em grão) Total", f"{PAM}:Café (em grão) Arábica", f"{PAM}:Café (em grão) Canephora"], "cafe|cafeeiro*|cafeicultura|cafeicultor*|cafezal|cafezais|coffea|arabica|conilon|robusta", "Coffea arabica; Coffea canephora", "cafe|cafeeiro|cafeicultura|coffea|cafezal|cafeicultor"),
    ("cacau", "Cacau", LP, ES, [f"{PAM}:Cacau (em amêndoa)"], "cacau|cacaueiro*|cacauicultura|theobroma cacao|chocolate", "Theobroma cacao", ""),
    ("erva_mate", "Erva-mate", LP, ES, [f"{PAM}:Erva-mate (folha verde)", f"{PEX}:1.8 - Erva-mate"], "erva-mate|erva mate|ervais|ilex paraguariensis|chimarrao", "Ilex paraguariensis", ""),
    ("guarana", "Guaraná", LP, ES, [f"{PAM}:Guaraná (semente)"], "guarana|guaranazeiro*|paullinia cupana", "Paullinia cupana", ""),
    ("pimenta_reino", "Pimenta-do-reino", LP, ES, [f"{PAM}:Pimenta-do-reino"], "pimenta-do-reino|pimenta do reino|piper nigrum", "Piper nigrum", ""),
    ("cha", "Chá", LP, ES, [f"{PAM}:Chá-da-índia (folha verde)"], "cha-da-india|camellia sinensis", "Camellia sinensis", ""),
    ("fumo", "Fumo", LT, ES, [f"{PAM}:Fumo (em folha)"], "fumo|tabaco|fumicultura|fumicultor*", "Nicotiana tabacum", ""),
    ("urucum", "Urucum", LP, ES, [f"{PAM}:Urucum (semente)", f"{PEX}:2.3 - Urucum (semente)"], "urucum|bixa orellana|coloral", "Bixa orellana", ""),
    # ---- cana e energia
    ("cana", "Cana-de-açúcar", LT, CN, [f"{PAM}:Cana-de-açúcar", f"{PAM}:Cana para forragem"], "cana-de-acucar|cana de acucar|canavial|canaviais|canavieir*|sucroenerget*|sucroalcooleir*|saccharum", "Saccharum officinarum", ""),
    # ---- oleaginosas e palmeiras
    ("dende", "Dendê (palma de óleo)", LP, OL, [f"{PAM}:Dendê (cacho de coco)"], "dende|dendezeiro*|palma de oleo|palma-de-oleo|elaeis", "Elaeis guineensis", ""),
    ("babacu", "Babaçu", FN, OL, [f"{PEX}:8.2 - Babaçu (amêndoa)"], "babacu|babacuais|attalea speciosa", "Attalea speciosa", ""),
    ("macauba", "Macaúba", FN, OL, [f"{PEX}:1.10 - Macaúba (fruto)"], "macauba|acrocomia", "Acrocomia aculeata", ""),
    ("castanha_para", "Castanha-do-brasil", FN, OL, [f"{PEX}:1.6 - Castanha-do-pará"], "castanha-do-para|castanha do para|castanha-do-brasil|castanha do brasil|castanheira*|bertholletia", "Bertholletia excelsa", ""),
    ("andiroba_copaiba", "Andiroba e copaíba", FN, OL, [f"{PEX}:8.1 - Andiroba (amêndoa)", f"{PEX}:8.3 - Copaíba (óleo)"], "andiroba|copaiba|carapa guianensis|copaifera", "", ""),
    ("carnauba", "Carnaúba", FN, OL, [f"{PEX}:4.1 - Carnaúba (cera)", f"{PEX}:4.2 - Carnaúba (pó)", f"{PEX}:5.2 - Carnaúba"], "carnauba|carnaubais|copernicia", "Copernicia prunifera", ""),
    ("licuri", "Licuri", FN, OL, [f"{PEX}:8.5 - Licuri (coquilho)"], "licuri|ouricuri|syagrus coronata", "Syagrus coronata", ""),
    ("palmito", "Palmito", LP, OL, [f"{PAM}:Palmito", f"{PEX}:1.12 - Palmito", f"{PEX}:1.9 - Juçara (fruto)"], "palmito|jucara|euterpe edulis", "", ""),
    # ---- fibras
    ("sisal", "Sisal", LP, FB, [f"{PAM}:Sisal ou agave (fibra)"], "sisal|agave", "Agave sisalana", ""),
    ("juta_malva", "Juta e malva", LT, FB, [f"{PAM}:Juta (fibra)", f"{PAM}:Malva (fibra)"], "juta|malva", "", "fibra|juta|varzea|amazonas|amazonia"),
    ("rami", "Rami", LT, FB, [f"{PAM}:Rami (fibra)"], "rami|boehmeria", "Boehmeria nivea", "fibra|boehmeria"),
    ("borracha", "Seringueira (borracha)", LP, FB, [f"{PAM}:Borracha (látex coagulado)", f"{PAM}:Borracha (látex líquido)", f"{PEX}:3.2 - Hevea (látex coagulado)", f"{PEX}:3.3 - Hevea (látex líquido)"], "seringueira*|heveicultura|hevea|borracha natural|seringal|seringais", "Hevea brasiliensis", ""),
    # ---- pastagens e forrageiras (Censo Agropecuário: pastagens naturais e plantadas)
    ("pastagem", "Pastagens e forrageiras", LT, FO, [f"{PAM}:Alfafa fenada", f"{PAM}:Cana para forragem"], "pastagem|pastagens|pasto|pastos|forrageira*|forragem|forragens|capim|capins|brachiaria|braquiaria|urochloa|panicum|mombaca|silagem|feno|alfafa|leucena|estilosantes|amendoim forrageiro|amendoim-forrageiro|arachis pintoi", "", ""),
    # ---- pecuária (PPM rebanhos)
    ("bovinos", "Bovinos (corte e leite)", PE, "Pecuária", [f"{REB}:Bovino"], "bovino*|bovinocultura|gado|boi|bois|vaca|vacas|novilha*|bezerro*|rebanho bovino|nelore|bos taurus|bos indicus|zebuino*", "Bos taurus; Bos indicus", ""),
    ("leite", "Leite e derivados", PE, "Produtos de origem animal", [f"{POA}:Leite"], "leite|leiteir*|laticinio*|queijo*|pecuaria de leite", "", ""),
    ("bubalinos", "Búfalos", PE, "Pecuária", [f"{REB}:Bubalino"], "bufalo*|bubalino*|bubalinocultura", "Bubalus bubalis", ""),
    ("suinos", "Suínos", PE, "Pecuária", [f"{REB}:Suíno - total", f"{REB}:Suíno - matrizes de suínos"], "suino*|suinocultura|porco*|leitao|leitoes|granja de suinos", "Sus scrofa", ""),
    ("aves", "Aves (frango e ovos)", PE, "Pecuária", [f"{REB}:Galináceos - total", f"{REB}:Galináceos - galinhas", f"{REB}:Codornas", f"{POA}:Ovos de galinha", f"{POA}:Ovos de codorna"], "frango*|galinha*|avicultura|avicola*|aves de corte|poedeira*|ovos de galinha|ovos de codorna|producao de ovos|codorna*|gallus", "Gallus gallus", ""),
    ("ovinos_caprinos", "Ovinos e caprinos", PE, "Pecuária", [f"{REB}:Ovino", f"{REB}:Caprino", f"{POA}:Lã"], "ovino*|ovinocultura|ovelha*|cordeiro*|caprino*|caprinocultura|cabra*|cabrito*|caprinovinocultura", "", ""),
    ("equinos", "Equinos", PE, "Pecuária", [f"{REB}:Equino"], "equino*|equinocultura|cavalo*", "Equus caballus", ""),
    ("mel", "Abelhas e mel", PE, "Produtos de origem animal", [f"{POA}:Mel de abelha"], "apicultura|apicola*|meliponicultura|meliponineos|abelha*|mel|apis mellifera", "Apis mellifera", "abelha|apicultura|apicola|meliponicultura|colmeia|apis"),
    ("seda", "Bicho-da-seda", PE, "Produtos de origem animal", [f"{POA}:Casulos do bicho-da-seda"], "bicho-da-seda|sericicultura|bombyx", "Bombyx mori", ""),
    # ---- aquicultura (PPM 3940)
    ("tilapia", "Tilápia", AQ, "Aquicultura", [f"{AQT}:Tilápia"], "tilapia*|oreochromis", "Oreochromis niloticus", ""),
    ("tambaqui", "Tambaqui e peixes redondos", AQ, "Aquicultura", [f"{AQT}:Tambaqui", f"{AQT}:Tambacu, tambatinga", f"{AQT}:Pacu e patinga", f"{AQT}:Pirapitinga"], "tambaqui|tambacu|tambatinga|pacu|pirapitinga|peixes redondos|colossoma", "Colossoma macropomum", ""),
    ("pirarucu", "Pirarucu", AQ, "Aquicultura", [f"{AQT}:Pirarucu"], "pirarucu|arapaima", "Arapaima gigas", ""),
    ("camarao", "Camarão", AQ, "Aquicultura", [f"{AQT}:Camarão", f"{AQT}:Larvas e pós-larvas de camarão"], "camarao|camaroes|carcinicultura|litopenaeus", "Litopenaeus vannamei", ""),
    ("moluscos", "Ostras e mexilhões", AQ, "Aquicultura", [f"{AQT}:Ostras, vieiras e mexilhões", f"{AQT}:Sementes de moluscos"], "ostra*|ostreicultura|mexilhao|mexilhoes|mitilicultura|malacocultura|vieira*", "", "ostra|mexilhao|molusco|maricultura|malacocultura|cultivo"),
    ("peixes", "Peixes (geral)", AQ, "Aquicultura", [f"{AQT}:Peixes", f"{AQT}:Outros peixes", f"{AQT}:Alevinos"], "piscicultura|aquicultura|aquicola*|peixe*|alevino*|pescado*|viveiro escavado|tanque-rede|tanques-rede", "", ""),
    # ---- silvicultura (PEVS 291)
    ("eucalipto", "Eucalipto", FP, "Silvicultura", [f"{PSI}:1.1.3 - Carvão vegetal de eucalipto", f"{PSI}:1.2.3 - Lenha de eucalipto", f"{PSI}:1.3.1.3 - Madeira em tora de eucalipto para papel e celulose", f"{PSI}:1.3.2.3 - Madeira em tora de eucalipto para outras finalidades"], "eucalipto*|eucaliptocultura|eucalyptus|corymbia", "Eucalyptus", ""),
    ("pinus", "Pinus", FP, "Silvicultura", [f"{PSI}:1.1.5 - Carvão vegetal de pinus", f"{PSI}:1.2.5 - Lenha de pinus", f"{PSI}:1.3.1.5 - Madeira em tora de pinus para papel e celulose", f"{PSI}:1.3.2.5 - Madeira em tora de pinus para outras finalidades"], "pinus|pinheiro americano|pinus taeda|pinus elliottii", "Pinus", ""),
    ("acacia_negra", "Acácia-negra", FP, "Silvicultura", [f"{PSI}:1.1.1 - Carvão vegetal de acácia negra", f"{PSI}:1.2.1 - Lenha de acácia negra"], "acacia-negra|acacia negra|acacia mearnsii", "Acacia mearnsii", ""),
    ("teca_mogno", "Teca, mogno-africano e cedro-australiano", FP, "Silvicultura", [f"{PSI}:1.1.6 - Carvão vegetal de teca", f"{PSI}:1.1.4 - Carvão vegetal de mogno africano", f"{PSI}:1.1.2 - Carvão vegetal de cedro australiano"], "teca|tectona|mogno-africano|mogno africano|khaya|cedro-australiano|cedro australiano|toona", "", ""),
    ("araucaria", "Araucária (pinheiro-brasileiro)", FN, "Silvicultura", [f"{PEX}:9.1 - Pinheiro brasileiro (nó de pinho)", f"{PEX}:9.3 - Pinheiro brasileiro (madeira em tora)", f"{PEX}:1.14 - Pinhão"], "araucaria|pinheiro-do-parana|pinheiro brasileiro|pinhao", "Araucaria angustifolia", ""),
    ("florestas_plantadas", "Florestas plantadas (geral)", FP, "Silvicultura", [f"{PSI}:1.1 - Carvão vegetal", f"{PSI}:1.2 - Lenha", f"{PSI}:1.3 - Madeira em tora"], "silvicultura|florestas plantadas|floresta plantada|plantios florestais|reflorestamento*|carvao vegetal|lenha", "", ""),
    ("extrativismo", "Extrativismo vegetal (geral)", FN, "Extrativismo vegetal", [], "extrativismo|extrativista*|produtos florestais nao madeireiros|pfnm|sociobiodiversidade", "", ""),
]


# frases que não contam para o produto (apagadas do texto antes de procurá-lo)
EXCLUIR = {
    "amendoim": "amendoim forrageiro|amendoim-forrageiro|arachis pintoi",
    "aves": "cama de frango|cama de aviario|cama de aves",
}


def main():
    saida = RAIZ / "ref" / "produtos.csv"
    with open(saida, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["produto_id", "produto", "grupo_atividade", "categoria_ampla", "fonte_ibge", "termos",
                    "cientifico", "contexto", "excluir", "status"])
        for pid, nome, grupo, cat, fontes, termos, cient, ctx in P:
            status = "categoria IBGE oficial; termos e agrupamento: proposta metodológica, em validação" if fontes \
                else "categoria ampla: proposta metodológica, em validação"
            w.writerow([pid, nome, grupo, cat, " | ".join(fontes), termos, cient, ctx, EXCLUIR.get(pid, ""), status])
    print(f"{len(P)} produtos em {saida}")


if __name__ == "__main__":
    main()
