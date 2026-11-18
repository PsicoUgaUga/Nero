# MAPA DE TRAJETÓRIAS

**Total:** 53 trajetórias (45 micros, 8 compostas)


## 🔧 MICRO-TRAJETÓRIAS

### micro_abrir_duckduckgo
- **O que faz:** Abre a página inicial do DuckDuckGo no navegador. Útil como primeiro passo pra pesquisar na web sem bloqueio de robô ou CAPTCHA.
- **Template:** `abre o duckduckgo`
- **Exemplo:** "abre o duckduckgo"
- **Ferramentas:** navegar
- **Passos:** 1

### micro_abrir_google
- **O que faz:** Abre a página inicial do Google no navegador. Útil como primeiro passo pra qualquer pesquisa ou busca na web usando o Google.
- **Template:** `abre o google`
- **Exemplo:** "abre o google"
- **Ferramentas:** navegar
- **Passos:** 1

### micro_abrir_primeiro_video_youtube
- **O que faz:** Clica no primeiro vídeo da página de resultados do YouTube e espera carregar. Útil pra abrir o vídeo mais relevante de uma busca já feita.
- **Template:** `abre o primeiro vídeo da busca`
- **Exemplo:** "abre o primeiro vídeo"
- **Ferramentas:** clicar_selector, esperar
- **Passos:** 2

### micro_abrir_youtube
- **O que faz:** Abre a página inicial do YouTube no navegador. Útil como primeiro passo pra pesquisar, assistir ou listar vídeos.
- **Template:** `abre o youtube`
- **Exemplo:** "abre o youtube"
- **Ferramentas:** navegar
- **Passos:** 1

### micro_baixar_foto_google
- **O que faz:** Com uma imagem do Google Imagens já aberta em modo preview, extrai a URL em tamanho real e baixa pra pasta de downloads. Útil pra salvar fotos encontradas na busca de imagens do Google.
- **Template:** `baixa a foto aberta no google imagens`
- **Exemplo:** "baixa essa imagem que tá aberta no google"
- **Ferramentas:** baixar_imagem_url, ler_pagina_estruturada
- **Passos:** 2

### micro_baixar_imagem_da_pagina
- **O que faz:** Navega até uma página da web e baixa a imagem principal (a maior imagem do conteúdo) pra pasta de downloads. Útil pra salvar fotos de artigos, notícias, blogs e páginas da Wikipedia.
- **Template:** `baixa a imagem principal da página {url_pagina}`
- **Parâmetros:** url_pagina
- **Exemplo:** "baixa a imagem do artigo da wikipedia sobre gatos"
- **Ferramentas:** baixar_imagem_url, esperar, ler_pagina_estruturada, navegar
- **Passos:** 4

### micro_buscar_hackernews_algolia
- **O que faz:** Busca notícias e discussões no Hacker News via API Algolia. Útil pra ver o que a comunidade de tecnologia está discutindo sobre um assunto.
- **Template:** `buscar {termo} no hacker news`
- **Parâmetros:** termo
- **Exemplo:** "o que estão falando sobre python no hacker news"
- **Ferramentas:** esperar, ler_texto_pagina, navegar
- **Passos:** 3

### micro_buscar_livro_openlibrary
- **O que faz:** Busca livros por título, autor ou assunto na Open Library via API. Útil pra achar informações sobre livros, autores e ISBN sem abrir navegador.
- **Template:** `busca livro {termo} na open library`
- **Parâmetros:** termo
- **Exemplo:** "acha livro do machado de assis"
- **Ferramentas:** esperar, ler_texto_pagina, navegar
- **Passos:** 3

### micro_buscar_receita_themealdb
- **O que faz:** Busca receitas completas com ingredientes e modo de preparo via TheMealDB. Útil pra encontrar receitas de pratos como bolo, sopa, massa ou qualquer comida.
- **Template:** `buscar receita de {prato}`
- **Parâmetros:** prato
- **Exemplo:** "como fazer bolo de cenoura"
- **Ferramentas:** esperar, ler_texto_pagina, navegar
- **Passos:** 3

### micro_calcular_rota_osrm
- **O que faz:** Calcula rota de carro entre dois pontos usando coordenadas via OSRM do OpenStreetMap. Útil pra saber distância e tempo de viagem entre dois endereços.
- **Template:** `calcular rota de carro entre lon {lon1} lat {lat1} e lon {lon2} lat {lat2}`
- **Parâmetros:** lon1, lat1, lon2, lat2
- **Exemplo:** "rota de carro entre são paulo e rio"
- **Ferramentas:** esperar, ler_texto_pagina, navegar
- **Passos:** 3

### micro_cambio_frankfurter
- **O que faz:** Consulta taxas de câmbio atuais do Banco Central Europeu via Frankfurter. Útil pra converter valores entre moedas (USD para BRL, EUR para USD, etc) com dados oficiais.
- **Template:** `conversão de câmbio de {base} para {alvo}`
- **Parâmetros:** base, alvo
- **Exemplo:** "quanto tá 1 dólar em real"
- **Ferramentas:** esperar, ler_texto_pagina, navegar
- **Passos:** 3

### micro_consultar_cep_brasilapi
- **O que faz:** Consulta o endereço completo de um CEP brasileiro via BrasilAPI: rua, bairro, cidade, estado. Útil pra descobrir endereço a partir de um CEP.
- **Template:** `consultar cep {cep}`
- **Parâmetros:** cep
- **Exemplo:** "qual o endereço do cep 01310100"
- **Ferramentas:** esperar, ler_texto_pagina, navegar
- **Passos:** 3

### micro_consultar_cnpj_brasilapi
- **O que faz:** Consulta dados cadastrais de uma empresa brasileira pelo CNPJ via BrasilAPI: razão social, sócios, endereço, situação. Útil pra saber informações oficiais de qualquer empresa do Brasil.
- **Template:** `consultar cnpj {cnpj}`
- **Parâmetros:** cnpj
- **Exemplo:** "dados da empresa com cnpj 00000000000191"
- **Ferramentas:** esperar, ler_texto_pagina, navegar
- **Passos:** 3

### micro_cotacao_awesomeapi
- **O que faz:** Consulta a cotação em tempo real de pares de moedas via AwesomeAPI. Útil pra saber valor do dólar (USD-BRL), euro (EUR-BRL), bitcoin (BTC-BRL) e outros pares em tempo real.
- **Template:** `cotação do par de moedas {par}`
- **Parâmetros:** par
- **Exemplo:** "cotação do dólar hoje"
- **Ferramentas:** esperar, ler_texto_pagina, navegar
- **Passos:** 3

### micro_feriados_brasilapi
- **O que faz:** Lista todos os feriados nacionais brasileiros de um ano via BrasilAPI. Útil pra saber quais são os feriados do ano e suas datas.
- **Template:** `feriados nacionais do ano {ano}`
- **Parâmetros:** ano
- **Exemplo:** "quais feriados tem em 2025"
- **Ferramentas:** esperar, ler_texto_pagina, navegar
- **Passos:** 3

### micro_geocodificar_nominatim
- **O que faz:** Converte um endereço ou nome de lugar em coordenadas (latitude, longitude) via Nominatim do OpenStreetMap. Útil como primeiro passo pra calcular rotas ou consultar clima de uma cidade.
- **Template:** `geocodificar endereço {endereco}`
- **Parâmetros:** endereco
- **Exemplo:** "coordenadas da avenida paulista"
- **Ferramentas:** esperar, ler_texto_pagina, navegar
- **Passos:** 3

### micro_geolocalizar_ipapi_co
- **O que faz:** Consulta a localização geográfica aproximada de um endereço IP via ipapi.co: país, cidade, coordenadas, provedor. Útil pra descobrir onde fica um IP.
- **Template:** `geolocalizar ip {ip} via ipapi.co`
- **Parâmetros:** ip
- **Exemplo:** "onde fica o ip 8.8.8.8"
- **Ferramentas:** esperar, ler_texto_pagina, navegar
- **Passos:** 3

### micro_geolocalizar_ipapicom
- **O que faz:** Consulta a localização geográfica aproximada de um endereço IP via ip-api.com: país, região, cidade, provedor. Alternativa ao ipapi.co pra descobrir onde fica um IP.
- **Template:** `geolocalizar ip {ip} via ip-api`
- **Parâmetros:** ip
- **Exemplo:** "onde fica o ip 8.8.8.8"
- **Ferramentas:** esperar, ler_texto_pagina, navegar
- **Passos:** 3

### micro_gerar_qrcode
- **O que faz:** Gera a URL de um QR Code pra qualquer texto ou link via API qrserver. Útil pra criar QR Codes de links, mensagens ou contatos.
- **Template:** `gerar qr code para o texto {texto}`
- **Parâmetros:** texto
- **Exemplo:** "gera um qr code com o link do google"
- **Ferramentas:** navegar
- **Passos:** 1

### micro_google_aba_imagens
- **O que faz:** Clica na aba Imagens do Google pra ver os resultados em formato de grade de imagens. Útil pra buscar fotos, ilustrações e imagens sobre um termo já pesquisado.
- **Template:** `clica na aba imagens do google`
- **Exemplo:** "vai pra aba de imagens do google"
- **Ferramentas:** clicar_selector, esperar
- **Passos:** 2

### micro_google_aba_maps
- **O que faz:** Clica na aba Maps do Google pra ver os resultados em formato de mapa. Útil pra localizar lugares, endereços e pontos no mapa.
- **Template:** `clica na aba maps do google`
- **Exemplo:** "vai pra aba de mapas do google"
- **Ferramentas:** clicar_selector, esperar
- **Passos:** 2

### micro_google_aba_noticias
- **O que faz:** Clica na aba Notícias do Google pra ver os resultados em formato de notícias recentes. Útil pra buscar notícias atualizadas sobre um termo já pesquisado.
- **Template:** `clica na aba notícias do google`
- **Exemplo:** "vai pra aba de notícias do google"
- **Ferramentas:** clicar_selector, esperar
- **Passos:** 2

### micro_google_aba_shopping
- **O que faz:** Clica na aba Shopping do Google pra ver os resultados em formato de produtos com preços. Útil pra comparar preços e achar onde comprar algo.
- **Template:** `clica na aba shopping do google`
- **Exemplo:** "vai pra aba de compras do google"
- **Ferramentas:** clicar_selector, esperar
- **Passos:** 2

### micro_google_aba_videos
- **O que faz:** Clica na aba Vídeos do Google pra ver os resultados em formato de lista de vídeos. Útil pra buscar vídeos no Google sobre um termo já pesquisado.
- **Template:** `clica na aba vídeos do google`
- **Exemplo:** "vai pra aba de vídeos do google"
- **Ferramentas:** clicar_selector, esperar
- **Passos:** 2

### micro_google_clicar_resultado_1
- **O que faz:** Clica no primeiro resultado da página de busca do Google. Útil pra abrir o link mais relevante de uma pesquisa já feita.
- **Template:** `clica no primeiro resultado do google`
- **Exemplo:** "abre o primeiro resultado"
- **Ferramentas:** clicar_selector, esperar
- **Passos:** 2

### micro_google_clicar_resultado_2
- **O que faz:** Clica no segundo resultado da página de busca do Google. Útil quando o primeiro não serve e precisa ver a alternativa seguinte.
- **Template:** `clica no segundo resultado do google`
- **Exemplo:** "abre o segundo resultado"
- **Ferramentas:** clicar_selector, esperar
- **Passos:** 2

### micro_google_clicar_resultado_3
- **O que faz:** Clica no terceiro resultado da página de busca do Google. Útil quando precisa ir além dos dois primeiros links.
- **Template:** `clica no terceiro resultado do google`
- **Exemplo:** "abre o terceiro resultado"
- **Ferramentas:** clicar_selector, esperar
- **Passos:** 2

### micro_google_clicar_resultado_n
- **O que faz:** Clica no resultado de uma posição específica do Google pelo número {n}. Útil pra abrir o resultado de posição 4, 5, 6, 7, 8, 9 ou 10 da busca.
- **Template:** `clica no resultado de posição {n} do google`
- **Parâmetros:** n
- **Exemplo:** "abre o quinto resultado"
- **Ferramentas:** clicar_selector, esperar
- **Passos:** 2

### micro_google_ferramentas
- **O que faz:** Abre o menu Ferramentas de busca do Google. Útil pra acessar filtros avançados como período, idioma, país e tipo de arquivo.
- **Template:** `abre o menu ferramentas do google`
- **Exemplo:** "abre as ferramentas de busca do google"
- **Ferramentas:** clicar_selector, esperar
- **Passos:** 2

### micro_google_imagem_abrir_1
- **O que faz:** Clica na primeira imagem da grade do Google Imagens pra abrir em modo detalhe. Útil pra pegar a URL da imagem ou vê-la em tamanho maior.
- **Template:** `abre a primeira imagem do google imagens`
- **Exemplo:** "abre a primeira imagem"
- **Ferramentas:** clicar_selector, esperar, ler_pagina_estruturada
- **Passos:** 3

### micro_google_pagina_anterior
- **O que faz:** Clica em Anterior do Google pra voltar uma página de resultados. Útil pra retornar à página anterior sem usar o botão voltar do navegador.
- **Template:** `volta uma página de resultados do google`
- **Exemplo:** "volta pra página anterior do google"
- **Ferramentas:** clicar_selector, esperar
- **Passos:** 2

### micro_google_proxima_pagina
- **O que faz:** Clica em Mais resultados do Google pra ir pra próxima página. Útil quando os resultados da primeira página não foram suficientes.
- **Template:** `vai para a próxima página de resultados do google`
- **Exemplo:** "vai pra página 2 do google"
- **Ferramentas:** clicar_selector, esperar
- **Passos:** 2

### micro_google_videos_clicar_1
- **O que faz:** Clica no primeiro vídeo da página de resultados do Google Vídeos e espera carregar. Útil pra abrir o vídeo mais relevante de uma busca.
- **Template:** `clica no primeiro vídeo do google`
- **Exemplo:** "abre o primeiro vídeo"
- **Ferramentas:** clicar_selector, esperar
- **Passos:** 2

### micro_info_pacote_pypi
- **O que faz:** Consulta metadados de um pacote Python no PyPI: versão, autor, descrição, dependências. Útil pra saber informações de bibliotecas Python como requests, numpy, pandas.
- **Template:** `informações do pacote python {pacote}`
- **Parâmetros:** pacote
- **Exemplo:** "o que é o pacote requests do python"
- **Ferramentas:** esperar, ler_texto_pagina, navegar
- **Passos:** 3

### micro_info_usuario_github
- **O que faz:** Consulta dados públicos de um usuário no GitHub: nome, bio, número de repositórios, seguidores. Útil pra ver perfil de desenvolvedores e repositórios do GitHub.
- **Template:** `informações do usuário {usuario} no github`
- **Parâmetros:** usuario
- **Exemplo:** "quem é o torvalds no github"
- **Ferramentas:** esperar, ler_texto_pagina, navegar
- **Passos:** 3

### micro_listar_municipios_ibge
- **O que faz:** Lista todos os municípios de um estado brasileiro via API do IBGE. Útil pra saber quais cidades existem em uma UF, com seus códigos IBGE.
- **Template:** `listar municípios do estado {uf}`
- **Parâmetros:** uf
- **Exemplo:** "quais municípios tem em goiás"
- **Ferramentas:** esperar, ler_texto_pagina, navegar
- **Passos:** 3

### micro_pesquisar_duckduckgo
- **O que faz:** Digita um termo no campo de busca do DuckDuckGo e pressiona Enter. Útil pra buscar qualquer coisa na web sem CAPTCHA, a partir de uma página do DuckDuckGo já aberta.
- **Template:** `pesquisa {termo} no duckduckgo`
- **Parâmetros:** termo
- **Exemplo:** "pesquisa piada do dia no duckduckgo"
- **Ferramentas:** esperar, preencher_campo, pressionar
- **Passos:** 3

### micro_pesquisar_google
- **O que faz:** Digita um termo no campo de busca do Google e pressiona Enter. Útil pra buscar qualquer coisa na web usando o Google, a partir de uma página do Google já aberta.
- **Template:** `pesquisa {termo} no google`
- **Parâmetros:** termo
- **Exemplo:** "pesquisa piada do dia no google"
- **Ferramentas:** esperar, preencher_campo, pressionar
- **Passos:** 3

### micro_pesquisar_youtube
- **O que faz:** Digita um termo no campo de busca do YouTube e pressiona Enter. Útil pra buscar vídeos sobre qualquer assunto a partir de uma página do YouTube já aberta.
- **Template:** `pesquisa {termo} no youtube`
- **Parâmetros:** termo
- **Exemplo:** "pesquisa pomodoro no youtube"
- **Ferramentas:** esperar, preencher_campo, pressionar
- **Passos:** 3

### micro_populacao_sidra
- **O que faz:** Consulta dados de população dos estados brasileiros no SIDRA do IBGE. Útil pra obter estatísticas populacionais oficiais do Brasil por estado.
- **Template:** `população dos estados brasileiros pela sidra`
- **Exemplo:** "qual a população dos estados do brasil"
- **Ferramentas:** esperar, ler_texto_pagina, navegar
- **Passos:** 3

### micro_preco_cripto_coingecko
- **O que faz:** Consulta o preço atual de uma criptomoeda em reais via CoinGecko. Útil pra saber cotação de bitcoin, ethereum, solana e outras criptomoedas em BRL.
- **Template:** `preço da criptomoeda {moeda} em reais`
- **Parâmetros:** moeda
- **Exemplo:** "quanto tá o bitcoin hoje"
- **Ferramentas:** esperar, ler_texto_pagina, navegar
- **Passos:** 3

### micro_preco_fipe_brasilapi
- **O que faz:** Consulta o preço de um veículo na Tabela FIPE pelo código FIPE via BrasilAPI. Útil pra saber valor de mercado de carros, motos e caminhões.
- **Template:** `preço fipe do veículo com código {codigo_fipe}`
- **Parâmetros:** codigo_fipe
- **Exemplo:** "quanto custa o carro de código fipe 001004-9"
- **Ferramentas:** esperar, ler_texto_pagina, navegar
- **Passos:** 3

### micro_previsao_brasilapi_cptec
- **O que faz:** Consulta a previsão do tempo no Brasil via CPTEC/INPE pela BrasilAPI usando o código INMET da cidade. Útil pra previsão de cidades brasileiras com dados oficiais do INPE.
- **Template:** `previsão do tempo no brasil para a cidade de código {codigo_cidade}`
- **Parâmetros:** codigo_cidade
- **Exemplo:** "previsão do tempo em São Paulo"
- **Ferramentas:** esperar, ler_texto_pagina, navegar
- **Passos:** 3

### micro_previsao_openmeteo
- **O que faz:** Consulta a previsão do tempo atual via Open-Meteo usando latitude e longitude. Útil pra saber temperatura, vento e condições climáticas em qualquer lugar do mundo sem chave de API.
- **Template:** `previsão do tempo na latitude {lat} e longitude {lon}`
- **Parâmetros:** lat, lon
- **Exemplo:** "previsão do tempo em lat -23.55 lon -46.63"
- **Ferramentas:** esperar, ler_texto_pagina, navegar
- **Passos:** 3

### micro_wikipedia_resumo
- **O que faz:** Retorna o resumo de um artigo da Wikipédia em português via API REST. Útil pra responder 'o que é X', 'quem foi Y' e definições rápidas sem abrir navegador.
- **Template:** `resumo da wikipedia sobre {termo}`
- **Parâmetros:** termo
- **Exemplo:** "o que é fotossíntese"
- **Ferramentas:** esperar, ler_texto_pagina, navegar
- **Passos:** 3


## 📦 TRAJETÓRIAS COMPOSTAS

### duckduckgo_pesquisar_e_abrir_primeiro_link
- **O que faz:** Abre o DuckDuckGo, pesquisa um termo, clica no primeiro resultado e retorna o TEXTO REAL da página de destino. Útil pra ir direto no site mais relevante e ler o conteúdo completo (piadas, receitas, notícias, previsão do tempo).
- **Template:** `pesquisa {termo} no duckduckgo, abre o primeiro link e lê o conteúdo`
- **Parâmetros:** termo
- **Exemplo:** "pesquisa receita de bolo no duckduckgo, abre o primeiro link e me diz o que tem lá"
- **Composta de:** micro_abrir_duckduckgo, micro_pesquisar_duckduckgo
- **Ferramentas:** clicar_selector, esperar, ler_pagina_estruturada, ler_texto_pagina, navegar, preencher_campo, pressionar
- **Passos:** 8

### duckduckgo_pesquisar_ler_resultado
- **O que faz:** Abre o DuckDuckGo, pesquisa um termo e retorna o conteúdo estruturado da página de resultados. Útil pra buscar informação rápida na web sem bloqueio, mostrando títulos e links.
- **Template:** `pesquisa {termo} no duckduckgo e lê o resultado`
- **Parâmetros:** termo
- **Exemplo:** "pesquisa piada do dia no duckduckgo"
- **Composta de:** micro_abrir_duckduckgo, micro_pesquisar_duckduckgo
- **Ferramentas:** esperar, ler_pagina_estruturada, navegar, preencher_campo, pressionar
- **Passos:** 5

### google_pesquisar_e_abrir_primeiro_link
- **O que faz:** Abre o Google, pesquisa um termo, clica no primeiro resultado e retorna o TEXTO REAL da página de destino. Útil pra ir direto no site mais relevante do Google e ler o conteúdo completo.
- **Template:** `pesquisa {termo} no google, abre o primeiro link e lê o conteúdo`
- **Parâmetros:** termo
- **Exemplo:** "pesquisa receita de bolo no google, abre o primeiro link e me diz o que tem lá"
- **Composta de:** micro_abrir_google, micro_pesquisar_google
- **Ferramentas:** clicar_selector, esperar, ler_pagina_estruturada, ler_texto_pagina, navegar, preencher_campo, pressionar
- **Passos:** 8

### google_pesquisar_ler_links
- **O que faz:** Abre o Google, pesquisa um termo e retorna títulos e URLs de todos os resultados da primeira página. Útil pra listar os links de uma busca sem abrir nenhum, ver os 10 primeiros resultados ou ter uma visão geral dos sites disponíveis.
- **Template:** `pesquisa {termo} no google e lê os links dos resultados`
- **Parâmetros:** termo
- **Exemplo:** "pesquisa inteligência artificial no google e me mostra os links"
- **Composta de:** micro_abrir_google, micro_pesquisar_google
- **Ferramentas:** esperar, ler_pagina_estruturada, navegar, preencher_campo, pressionar
- **Passos:** 5

### google_pesquisar_ler_resultado
- **O que faz:** Abre o Google, pesquisa um termo e retorna o conteúdo estruturado da página de resultados. Útil pra buscar informação rápida no Google, mostrando títulos e links.
- **Template:** `pesquisa {termo} no google e lê o resultado`
- **Parâmetros:** termo
- **Exemplo:** "pesquisa piada do dia no google"
- **Composta de:** micro_abrir_google, micro_pesquisar_google
- **Ferramentas:** esperar, ler_pagina_estruturada, navegar, preencher_campo, pressionar
- **Passos:** 5

### google_videos_pesquisar_ler_links
- **O que faz:** Abre o Google, pesquisa um termo, clica na aba Vídeos e retorna títulos e URLs dos vídeos encontrados. Útil pra listar links de vídeos do Google sem abrir nenhum.
- **Template:** `pesquisa {termo} no google vídeos e lê os links dos resultados`
- **Parâmetros:** termo
- **Exemplo:** "pesquisa tutorial de python no google vídeos e me mostra os links"
- **Composta de:** micro_abrir_google, micro_pesquisar_google, micro_google_aba_videos
- **Ferramentas:** clicar_selector, esperar, ler_pagina_estruturada, navegar, preencher_campo, pressionar
- **Passos:** 7

### youtube_pesquisar_e_abrir_primeiro
- **O que faz:** Abre o YouTube, pesquisa um termo, clica no primeiro vídeo e retorna o texto da página do vídeo (título, descrição, canal). Útil pra ABRIR o vídeo mais relevante e ler o que ele diz sem precisar assistir.
- **Template:** `pesquisa {termo} no youtube e abre o primeiro vídeo`
- **Parâmetros:** termo
- **Exemplo:** "pesquisa pomodoro no youtube e abre o primeiro vídeo"
- **Composta de:** micro_abrir_youtube, micro_pesquisar_youtube, micro_abrir_primeiro_video_youtube
- **Ferramentas:** clicar_selector, esperar, ler_pagina_estruturada, ler_texto_pagina, navegar, preencher_campo, pressionar
- **Passos:** 8

### youtube_pesquisar_ler_resultados
- **O que faz:** Abre o YouTube, pesquisa um termo e retorna a lista estruturada de vídeos (títulos, links, canais). Útil pra LISTAR resultados de busca sem abrir nenhum vídeo — só ver as opções.
- **Template:** `pesquisa {termo} no youtube e lista os vídeos`
- **Parâmetros:** termo
- **Exemplo:** "pesquisa receita de bolo no youtube e me lista os vídeos"
- **Composta de:** micro_abrir_youtube, micro_pesquisar_youtube
- **Ferramentas:** esperar, ler_pagina_estruturada, navegar, preencher_campo, pressionar
- **Passos:** 5
