# Validação da dor — gerente de loja com pouca visibilidade acionável

## Hipótese de problema

Um gerente de loja fecha o mês com um número agregado de faturamento, mas precisa abrir planilhas e comparar vendedores manualmente para descobrir onde uma conversa de acompanhamento pode ser útil. A dor proposta pelo Dashalise é reduzir o tempo entre “a loja fechou o mês” e “sei quem chamar, quais indicadores levar para a conversa e o que ainda preciso investigar”.

Essa é uma **hipótese para validar**, não um problema comprovado por estes arquivos: os dados são fictícios e não medem o tempo nem o processo atual de um gerente real.

## Cenário para você interpretar

É segunda-feira, **02/11/2026**. Diego Furtado, gerente da loja L004 — Aurora Shopping Centro, abre o painel para revisar outubro com a equipe.

- A loja vendeu **R$ 326.697,48** para uma meta de **R$ 317.200,00**: **103,0% de atingimento**.
- No período comparável do arquivo do ano anterior, deslocado em 364 dias para manter o mesmo dia da semana, a loja havia vendido **R$ 301.555,98**: variação de aproximadamente **+8,3%**.
- O conjunto diário da loja soma **1.014 vendas, 1.790 peças e 2.679 atendimentos**: conversão de **37,8%**, P.A. de **1,77 peça por venda**, ticket médio de **R$ 322,19** e preço médio de **R$ 182,51 por peça**.
- O total agregado esconde diferenças entre pessoas. Bianca Rocha vendeu **R$ 45.856,89** contra meta individual de **R$ 40.782,86** (**112,4%**), com conversão de **51,0%** (201 vendas / 394 atendimentos).
- Kaique Ramos vendeu **R$ 25.989,01** contra meta de **R$ 40.782,86** (**63,7%**), com conversão de **29,8%** (82 / 275).
- Lucas Moreira vendeu **R$ 23.659,92** contra meta de **R$ 39.272,38** (**60,2%**), com conversão de **30,7%** (94 / 306).

Diego não precisa concluir que Kaique ou Lucas atendem mal. Ele precisa localizar a diferença, abrir os painéis individuais, entender o contexto e escolher uma conversa de acompanhamento sem transformar o indicador em culpa.

## Encenação da demonstração

1. Escolha **Gerente de loja**. O perfil representa Diego e mostra o escopo da L004.
2. Abra **Equipe** e compare a visão agregada da loja com os cartões individuais.
3. Abra Bianca, Kaique e Lucas. Observe atingimento, conversão, ticket, P.A. e atendimentos juntos.
4. Pergunte ao assistente: **“Quais diferenças entre Bianca, Kaique e Lucas aparecem nos dados de outubro? O que eu deveria investigar antes de concluir que é a abordagem?”**
5. Uma boa resposta deve citar os números do período, apontar conversão como diferença observável, propor perguntas para uma conversa individual e esclarecer que os dados não mostram o motivo da diferença.
6. Decida se o Dashalise ajudou Diego a sair do total da loja e chegar a uma próxima ação concreta em menos tempo.

## O que contaria como evidência de que a dor foi reduzida

- O gerente encontra a loja, o período e as pessoas pertinentes sem exportar e cruzar planilhas.
- Os números da resposta do assistente coincidem com os indicadores calculados no backend e têm um atalho para a tela usada.
- O gerente entende que conversão é uma pista para investigar, não prova de uma falha individual.
- Em entrevistas ou teste cronometrado com gerentes reais, o tempo para preparar a conversa diminui e eles conseguem explicar de onde vieram os números.
- Em um piloto posterior, é possível observar se as ações de acompanhamento são feitas e comparar resultados com um grupo de referência.

## Limites desta base

Os arquivos informam vendas, peças e atendimentos agregados por vendedor e dia, metas, escala, loja e um período comparável do ano anterior. Eles **não** trazem transações individuais, produtos por venda, clientes, estoque, descontos, horários/turnos, motivos de perda ou cancelamento, gravação de atendimento, satisfação do cliente, nem histórico de quais orientações foram dadas a cada vendedor.

Por isso, o produto consegue responder **o que aconteceu, onde, em que período e para quem** dentro do escopo autorizado. Ele não consegue demonstrar por que alguém converte menos, dizer que uma técnica causou o resultado, calcular cancelamentos, apontar produto campeão ou provar que a IA aumentou as vendas. Hipóteses de coaching devem ser verificadas em conversa com o funcionário e complementadas por dados apropriados.

## Pesquisa científica e personalização por empresa

É possível combinar três fontes, mantendo-as separadas:

1. **Dados da empresa:** métricas e comparações calculadas pelo backend, respeitando período, loja e perfil.
2. **Pesquisa externa:** estudos e revisões encontrados pelo Gemini/Google Search, com links para as fontes e indicação de que são evidência publicada, não resultado da empresa.
3. **Contexto da empresa:** catálogo, público, política comercial, limites do produto e perguntas de descoberta cadastrados pelo gerente.

A IA deve explicar se uma conclusão é um cálculo descritivo, uma associação observada em estudo, uma hipótese a validar ou uma relação causal demonstrada em experimento. O conjunto fictício da Rede Aurora serve para demonstrar cálculos; ele não permite generalizar resultados para empresas reais nem comprovar eficácia do Dashalise.

### Referências científicas iniciais

- Franke e Park, **“Salesperson Adaptive Selling Behavior and Customer Orientation: A Meta-Analysis”**, sintetiza 155 amostras e mais de 31 mil vendedores. A meta-análise encontrou associação entre comportamento adaptativo de venda e diferentes medidas de desempenho; isso apoia a relevância de adaptar a conversa, mas não prova que este software ou um chatbot cause aumento de vendas. [Journal of Marketing Research / DOI](https://doi.org/10.1509/jmkr.43.4.693)
- Chaker et al., **“The past, present, and future of adaptive selling: Toward an integrative framework”**, revisão aberta publicada em 2025, organiza décadas de estudos e também descreve limites e diferentes formas de medir venda adaptativa. [Journal of the Academy of Marketing Science](https://link.springer.com/article/10.1007/s11747-025-01096-3)
- Ferreira, Lee e Simchi-Levi avaliaram uma ferramenta analítica de apoio a decisões de preço em um varejista online com experimento de campo. É um exemplo de como avaliar uma decisão assistida por dados com grupo de comparação; o resultado específico de moda e preço não deve ser transferido diretamente para coaching de vendedores em lojas. [Harvard Business School — Analytics for an Online Retailer](https://www.hbs.edu/ris/Publication%20Files/kris%20Analytics%20for%20an%20Online%20Retailer_6ef5f3e6-48e7-4923-a2d4-607d3a3d943c.pdf)

Uma avaliação própria poderia começar com um piloto por lojas ou equipes, acompanhando conversão, ticket e P.A. antes/depois, satisfação e uso do painel. Para atribuir uma mudança ao produto, seria necessário um grupo de comparação e registrar fatores como escala, tráfego, estoque, campanha, tipo de loja, experiência e sazonalidade. Os indicadores atuais não contêm todos esses controles.
