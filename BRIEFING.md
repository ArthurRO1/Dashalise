# Programa de Estágio FullStore — Briefings

06/11/2026 · Rodrigo Imenes

Quatro problemas reais do varejo para resolver em uma semana e apresentar em 5 minutos. Aqui está o contexto que vocês precisam sobre a FullStore e o problema de cada desafio; a solução é com vocês.

## Os 4 desafios

Cada participante escolhe um desafio da lista. Todos se passam na Rede Aurora, uma rede fictícia de lojas descrita na próxima seção. Os dados de cada desafio estão em [`dados/`](dados/), uma pasta por desafio.

| # | Desafio | A pergunta |
| --- | --- | --- |
| 1 | **Treinamento que ensina a vender** (treinamento gamificado com IA) | Como transformar o material que a marca já tem num treinamento que o vendedor queira fazer e que mude o jeito dele vender? |
| 2 | **O número certo, onde a pessoa já está** (dashboards personalizados com IA) | Como cada pessoa da rede recebe os números que importam para ela, do jeito que ela entende, sem abrir um sistema? |
| 3 | **O feedback que ninguém dá** (feedback com IA) | Como ajudar gerentes a dar feedback frequente, justo e útil para os vendedores, e a receber feedback também? |
| 4 | **O treinamento certo, na hora certa** (orquestração de treinamentos) | O conteúdo já existe. Como cada vendedor recebe o que precisa, quando precisa, e como provar que fez diferença? |

## Comece aqui: a FullStore e a Rede Aurora

A FullStore é uma plataforma para redes de varejo: marcas com dezenas ou centenas de lojas físicas, muitas delas franquias. Ela junta num lugar só o que a rede precisa para as lojas venderem mais: metas e resultados de venda, comissão dos vendedores, comunicação da matriz com as lojas, treinamento, avaliação de desempenho e a rotina da loja.

Os gestores usam um painel na web; os vendedores usam um app no celular. As vendas chegam sozinhas do sistema de caixa de cada loja.

### A Rede Aurora

Todos os desafios se passam na **Rede Aurora**, uma rede fictícia de moda feminina com 120 lojas em shoppings e em rua, cerca de 40 donos de franquia e 900 vendedores. As pessoas abaixo aparecem nos briefings; nenhuma existe de verdade.

| Quem | Papel na rede | Onde passa o dia | O que mais quer |
| --- | --- | --- | --- |
| Marcos | Diretor comercial da franqueadora (a matriz) | Escritório central | Que a rede inteira venda mais e siga o padrão da marca |
| Juliana | Coordenadora de treinamento da franqueadora | Escritório central | Que todo vendedor saiba vender a coleção nova |
| Patrícia | Gerente regional de 20 lojas | Na estrada, visitando lojas | Saber rápido quais lojas precisam de ajuda |
| Diego | Gerente da loja do Shopping Centro, promovido de vendedor há 6 meses | Na loja, o dia todo | Bater a meta do mês com o time que tem |
| Bianca | Vendedora há 3 anos | No salão, atendendo | Bater a meta e ganhar o prêmio |
| Lucas | Vendedor há 2 meses, 19 anos | No salão, atendendo | Aprender rápido e não passar vergonha com a cliente |

### Glossário do varejo

| Termo | O que significa |
| --- | --- |
| Franqueadora (matriz) | A dona da marca. Define produtos, padrões e treinamentos para todas as lojas |
| Franqueado | Quem compra o direito de abrir lojas da marca e é dono delas |
| Meta | Quanto a loja e cada vendedor precisam vender no mês; bater a meta libera prêmio |
| Comissão | A parte do salário do vendedor que depende do quanto ele vendeu |
| Atendimento | Cada vez que um vendedor atende uma cliente, comprando ela ou não |
| Ticket médio | Valor médio de cada compra |
| P.A. (peças por atendimento) | Quantas peças, em média, a cliente leva em cada compra |
| Taxa de conversão | De quem foi atendido (ou de quem entrou na loja), quantos compraram |
| Coleção | O conjunto de produtos novos de uma estação (verão, inverno…) |
| PDV | O sistema de caixa da loja, de onde vêm as vendas |

## Como funciona a seleção?

Vocês têm uma semana, do kickoff à apresentação. No dia, cada participante tem 5 minutos para apresentar e mostrar a demo, seguidos de perguntas da banca. Só serão aceitos commits feitos até 13/11/2026, antes das 18h (horário de Brasília).

**Regras**

- **Demo funcionando.** Tragam um vídeo gravado da demo.
- **Tecnologia livre.** Usem a linguagem e as ferramentas que quiserem, IA inclusive, tanto para programar quanto dentro da solução.
- **Só dados fictícios.** Usem os dados em `dados/` ou dados que vocês mesmos criarem. Nada de dados reais de clientes, e nenhuma imagem de pessoas sem autorização delas.
- **Converse com quem vive o problema.** É recomendado falar com pelo menos uma pessoa do varejo (vendedor, gerente, dono de loja) e contar na apresentação o que vocês aprenderam.
- **Sem código nos slides.** A banca não vai olhar código nesta etapa.

**O que não precisa:** login, telas de cadastro, deploy em produção, design perfeito. Foquem no problema e em quem sofre com ele.

**Como avaliamos**

Nesta etapa a banca não vai olhar o código. Queremos ver como vocês pensam e como comunicam: se, em poucos minutos, qualquer pessoa entende o problema que vocês escolheram, para quem ele importa e o que vocês construíram. Uma boa apresentação conta uma história do começo ao fim, mostra a solução funcionando e deixa claro por que vocês seguiram por esse caminho. O cuidado com a apresentação e com o tempo também conta.

## Desafio 1 — Treinamento que ensina a vender

*Treinamento gamificado com IA.* Como transformar o material que a marca já tem num treinamento que o vendedor queira fazer e que mude o jeito dele vender?

**A situação**

Toda coleção nova da Aurora chega com material: um PDF de 40 páginas sobre tecidos, caimento e preços, um vídeo de 20 minutos da estilista e um guia de como argumentar com a cliente. O time de treinamento da franqueadora tem 2 pessoas para 900 vendedores.

Montar um treinamento bom leva semanas; quando fica pronto, a coleção já está na vitrine. Enquanto isso, o vendedor recebe o PDF pelo WhatsApp e não abre. Os poucos treinamentos que existem são decoreba: perguntas de múltipla escolha respondidas no chute, que não ensinam a lidar com a cliente que diz "está caro" ou "vou dar uma volta".

**Quem sofre com isso**

- **Juliana**, coordenadora de treinamento, não dá conta de produzir conteúdo na velocidade das coleções.
- **Lucas**, vendedor há 2 meses, aprende errando na frente da cliente.

**Por que é difícil**

- Vender é habilidade, não só conhecimento: saber a composição do tecido não ensina a contornar uma objeção.
- O vendedor treina no celular, em pé, entre um atendimento e outro, muitas vezes sem fone.
- Chega vendedor novo na Aurora toda semana, e cada um começa de um ponto diferente.
- Se a IA errar uma informação de produto (preço, tecido, tamanho), o vendedor repete o erro para a cliente.
- Jogo que só dá pontinho e medalha diverte, mas não ensina.
- Terminar o treinamento não é o mesmo que ter aprendido.

**Perguntas para começar**

- O que um vendedor experiente sabe fazer que um novato não sabe?
- O que seria um treinamento "complexo" para quem vende roupa?
- Como a Juliana sabe que o que foi gerado está certo antes de chegar a 900 pessoas?

**O que vocês recebem**

- O material da coleção Verão 2027 em [`dados/desafio-1-treinamento/`](dados/desafio-1-treinamento/): o guia de produtos em PDF, a planilha da coleção, a transcrição do vídeo da estilista e o guia de argumentação.

**Adicional:** você pode gerar os conteúdos do zero, se preferir.

## Desafio 2 — O número certo, onde a pessoa já está

*Dashboards personalizados com IA, da concepção à distribuição.* Como cada pessoa da rede recebe os números que importam para ela, do jeito que ela entende, sem abrir um sistema?

**A situação**

A Aurora gera muito dado: vendas por loja, por vendedor e por dia, meta, ticket médio, peças por atendimento, conversão. O painel existe, mas cada pessoa quer ver uma coisa diferente: o diretor quer a rede inteira, a regional quer as 20 lojas dela, o gerente quer a loja hoje, o vendedor quer saber quanto falta para a meta.

Na prática, quase ninguém abre o painel. O gerente tira print, cola no grupo de WhatsApp da loja e escreve "bora, time!". A regional monta uma planilha à mão toda segunda de manhã.

**Quem sofre com isso**

- **Patrícia**, regional, perde a manhã de segunda montando planilha em vez de visitar loja.
- **Diego**, gerente, não tem tempo de interpretar gráfico entre um atendimento e outro.
- **Marcos**, diretor, recebe números diferentes de pessoas diferentes para a mesma pergunta.

**Por que é difícil**

- Cada pessoa pergunta do seu jeito: "como foi ontem?", "quem está mal?", "estamos melhor que o ano passado?".
- Um número errado destrói a confiança, e uma IA pode inventar números.
- Nem todo mundo pode ver tudo: o vendedor não pode ver a comissão do colega, e o gerente não vê a loja vizinha.
- Informação demais é ignorada; de menos, não serve.
- WhatsApp não é painel: tela pequena, pouca interação, mensagem que some no meio do grupo.
- A hora importa: o resumo de ontem chegando às 18h não serve para mais nada.

**Perguntas para começar**

- O que a Patrícia precisa saber às 9h de segunda?
- Quem decide o que entra no painel de cada pessoa?
- Como alguém confia num número que chegou pelo WhatsApp?

**O que vocês recebem**

- Uma base fictícia da Aurora: lojas, vendedores e 90 dias de vendas, metas, peças e atendimentos.
- A definição de cada indicador (o glossário acima, com as contas).
- Envio real pelo WhatsApp é opcional: podem simular o canal ou usar outro.
- Tudo em [`dados/desafio-2-dashboards/`](dados/desafio-2-dashboards/), com um LEIAME que explica cada arquivo.

**Cenário da demo:** a segunda-feira de manhã de três pessoas diferentes da Aurora.

## Desafio 3 — O feedback que ninguém dá

*Feedback para vendedores e gerentes usando IA.* Como ajudar gerentes a dar feedback frequente, justo e útil para os vendedores, e a receber feedback também?

**A situação**

Na Aurora, o gerente deveria conversar com cada vendedor sobre o desempenho dele. Na prática, falta tempo (ele também vende, abre o caixa e cuida do estoque), ninguém o ensinou a dar feedback, e a conversa só acontece quando dá problema. O que sai é vago ("precisa vender mais") ou duro demais.

O vendedor passa meses sem saber se está indo bem, e por quê. Os números para basear a conversa existem (ticket médio, peças por atendimento, conversão, meta), mas o gerente não sabe ler o que eles dizem sobre cada pessoa. E o próprio gerente quase nunca recebe feedback da regional.

**Quem sofre com isso**

- **Diego**, gerente há 6 meses, era o melhor vendedor da loja e nunca aprendeu a liderar.
- **Bianca**, vendedora, é ótima no atendimento, mas quase toda cliente dela leva uma peça só. Ninguém nunca disse isso a ela.

**Por que é difícil**

- Feedback mexe com pessoas: um texto frio ou injusto desmotiva e pode até virar problema trabalhista.
- Número sem contexto engana: a vendedora que esteve de férias, a loja em reforma, o mês de chuva.
- Feedback vago não muda nada; ele precisa dizer o que fazer diferente amanhã.
- Uma IA pode soar genérica, ou pior, afirmar algo que não aconteceu.
- O vendedor percebe quando o feedback é "texto de robô", e o gerente precisa continuar dono da conversa.
- Saber se o feedback funcionou leva semanas.

**Perguntas para começar**

- Qual é a diferença entre um feedback bom e um ruim?
- O que a Bianca precisa ouvir, e como?
- Quem dá feedback para o Diego?

**O que vocês recebem**

- Uma base fictícia da loja do Diego: 8 vendedores, 3 meses de indicadores e anotações soltas do gerente.
- Exemplos fictícios de feedbacks ruins.
- Tudo em [`dados/desafio-3-feedback/`](dados/desafio-3-feedback/), com um LEIAME que explica cada arquivo.

**Cenário da demo:** é fim de mês. Mostrem o Diego preparando e dando o feedback da Bianca, e alguém dando feedback para o Diego.

## Desafio 4 — O treinamento certo, na hora certa

*Orquestração e distribuição de treinamentos.* O conteúdo já existe. Como cada vendedor recebe o que precisa, quando precisa, e como provar que fez diferença?

**A situação**

A biblioteca da Aurora tem 300 vídeos, PDFs e guias sobre produto, atendimento, vitrine, caixa e cultura da marca. O problema não é falta de conteúdo, é a entrega. Neste desafio o conteúdo já está pronto; criar conteúdo novo é o Desafio 1.

Hoje a franqueadora manda tudo para todo mundo, no grupo de WhatsApp ou num e-mail que ninguém lê. O vendedor novo recebe o mesmo que a veterana de 8 anos. O treinamento da coleção chega depois que ela já está na loja. Quem volta de férias encontra 12 conteúdos acumulados. E quando o Marcos pergunta "o treinamento de atendimento aumentou as vendas?", ninguém sabe responder.

**Quem sofre com isso**

- **Juliana**, coordenadora de treinamento, não consegue escolher à mão o que vai para 900 pessoas.
- **Patrícia**, regional, vê uma loja com a conversão caindo e não sabe o que mandar para o time dela.
- **Lucas**, vendedor novo, recebe 40 conteúdos na primeira semana e não sabe por onde começar.

**Por que é difícil**

- Cada pessoa é diferente: cargo, tempo de casa, loja, região, o que já sabe.
- A ordem importa: alguns conteúdos só fazem sentido depois de outros.
- A hora importa: antes do lançamento, não depois; não no dia de folga.
- Quem recebe demais para de abrir tudo.
- Abrir não é assistir, assistir não é aprender, aprender não é aplicar na loja.
- Venda sobe e desce por muitos motivos; separar o efeito do treinamento é difícil.

**Perguntas para começar**

- Quem decide o que cada vendedor recebe?
- O que muda entre o primeiro mês de um vendedor e o quinto ano dele?
- Como saber se um treinamento mudou alguma coisa na loja?

**O que vocês recebem**

- O catálogo fictício da biblioteca: título, tema, formato e duração de cada conteúdo.
- A base fictícia de vendedores: cargo, loja, data de admissão, folgas e férias.
- Os indicadores diários das lojas.
- Tudo em [`dados/desafio-4-orquestracao/`](dados/desafio-4-orquestracao/), junto com o histórico de envios dos últimos meses e o calendário de novembro. O LEIAME explica cada arquivo.

**Cenário da demo:** um mês da Aurora com o lançamento da coleção de verão, 5 vendedores novos e uma loja com a conversão caindo.
