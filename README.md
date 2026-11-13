# Dashalise · Inteligência Comercial

Demonstração do **Desafio 2 — O número certo, onde a pessoa já está**, do Programa de Estágio FullStore. A aplicação apresenta painéis de vendas personalizados e um assistente comercial com IA, construída com **Django, Django REST Framework, SQLite, HTML, CSS e JavaScript**.

> Todos os nomes, valores e registros usados na demonstração são fictícios. A troca de perfil dispensa login para facilitar a apresentação e não representa autenticação segura para produção.

O briefing original, as regras do desafio e os dados fornecidos pela organização estão preservados neste repositório, em `BRIEFING.md` e `dados/`. Consulte também os arquivos `LEIAME.md` dentro de cada desafio.

## Executar localmente

Requer Python 3.10 ou mais recente.

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python manage.py migrate --run-syncdb
python manage.py prepare_demo_schema
python manage.py seed_demo
python manage.py runserver
```

Abra <http://127.0.0.1:8000>. A demonstração usa SQLite em `db.sqlite3`. O comando `seed_demo` carrega os CSVs de `dados/desafio-2-dashboards/` para a empresa fictícia Rede Aurora; ele substitui os registros demonstrativos da empresa no banco local, inclusive conversas e anotações vinculadas aos dados antigos. Execute-o somente quando quiser recriar a base da demo.

São importadas 120 lojas, 1.101 perfis de usuários, a lista de 1.095 vendedores e gerentes (incluindo identidades históricas inativas para manter vendas de pessoas desligadas), 80.136 resumos diários vendedor-loja, metas individuais e por loja e 10.262 observações de lojas do ano anterior. A demonstração abre outubro de 2026, o último mês fechado antes do cenário de 02/11/2026. A comparação anual usa as datas 364 dias antes, conforme o arquivo.

Os registros de venda são agregados por pessoa e dia; não incluem produto por venda, clientes, motivos de cancelamento, nem conversas de atendimento. Por isso o painel mantém conversão, P.A., ticket médio, preço médio, metas e comissão baseados nos registros operacionais. Para demonstração, `seed_demo` cria quatro produtos fictícios, especializações da IA e métricas simuladas de outubro em `ProductDemoPerformance`, uma tabela separada. Esses exemplos aparecem identificados na tela Produtos, ajudam a demonstrar comparações e perguntas sobre catálogo e nunca entram nas vendas, metas ou comissões dos funcionários.

### Assistente Gemini e pesquisa web automática

Configure `GEMINI_API_KEY` no ambiente do servidor antes de iniciar. O projeto usa `google-genai>=2.3.0` porque a busca web depende da API Interactions do SDK. Depois de atualizar dependências, execute `python -m pip install --upgrade -r requirements.txt` no mesmo ambiente virtual do Django e reinicie o servidor. Opcionalmente, defina `GEMINI_MODEL` (padrão no código: `gemini-3.8-flash`). Com a chave, dúvidas de técnica e condução comercial são respondidas pelo Gemini com artigos, especializações e exemplos de referência relevantes. Perguntas de metas, vendas, comissões e outros indicadores continuam sendo calculadas pelo Django; esses números não são delegados ao modelo. Sem chave, permanecem as respostas locais por regras.

O Google Search fica disponível automaticamente nas perguntas de orientação: o Gemini decide quando uma busca externa ajuda e pode devolver fontes citadas. Perguntas de indicadores continuam no Django e não são enviadas à web. Evite incluir nomes ou dados pessoais de clientes nas perguntas.

Exemplo no PowerShell (somente para a janela atual): `$env:GEMINI_API_KEY = 'sua-chave'`. Não coloque a chave em HTML, JavaScript ou no repositório.

O Gemini pode usar Google Search grounding, sintetizar informação recente e devolver citações URL para exibição. A disponibilidade e o preço dependem do modelo/plano; consulte a [documentação oficial de grounding](https://ai.google.dev/gemini-api/docs/google-search) e a [página de preços](https://ai.google.dev/gemini-api/docs/pricing).

### Avaliação contínua e Langfuse opcional

As respostas do assistente aceitam avaliação positiva/negativa e um motivo opcional. Esses registros ficam associados à mensagem no SQLite. Para revisar os casos avaliados, execute `python manage.py export_assistant_feedback --rating not_helpful` (ou omita `--rating` para exportar todos) e selecione manualmente os exemplos que devem melhorar a base. Atualize `sales/data/assistant_reference_examples.json` após a revisão; o arquivo é carregado como contexto de referência pelo Gemini. Os exemplos também servem como conjunto inicial de casos para avaliação manual e não atualizam automaticamente os pesos do modelo.

Para registrar chamadas no Langfuse, configure `LANGFUSE_ENABLED=true`, `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY` e, se necessário, `LANGFUSE_BASE_URL` no ambiente antes de iniciar. A captura é desativada por padrão. O código registra somente pergunta, perfil, etapa, modelo e resposta; não envia métricas nem o contexto de venda ao Langfuse. Se o Langfuse estiver indisponível, a resposta continua funcionando.

O ajuste de pesos (fine-tuning) não está disponível atualmente na Gemini Developer API / AI Studio; o Google documenta tuning em sua plataforma Vertex AI/Agent Platform. Nesta versão, a melhoria é feita por contexto recuperado (RAG simples), exemplos de referência, prompt versionado, avaliação humana e ciclos de comparação. Isso melhora a aplicação sem alegar que o modelo está sendo retreinado automaticamente.

## O que a demonstração faz

- Tela inicial limpa com conversa em destaque e navegação por barra superior.
- Troca sem login entre Funcionário, Supervisor, Gerente e Administrador.
- O perfil gerente/administrador vê um resumo da equipe e abre cada vendedor em um painel individual com o mesmo recorte de indicadores, metas, vendas, produtos, alertas e chat.
- Em cada venda, vendedor ou gestor pode registrar uma dificuldade percebida e a etapa relacionada. A IA usa esse relato e a documentação comercial para sugerir uma prática; o registro é tratado como autorrelato, não como avaliação objetiva.
- Conversas persistidas no banco e organizadas por venda e etapa do Método de Venda Adaptativa.
- Chat compacto disponível ao navegar para outras abas, preservando a conversa ativa.
- Respostas podem trazer atalhos para a aba da meta, produto, equipe ou venda correspondente.
- Painel de indicadores com evolução diária de vendas, ticket médio, conversão, peças por venda, preço médio e projeção de fechamento. A comparação anual é apresentada por loja, pois o arquivo histórico não detalha vendedor.
- Vendas, metas e comissões são calculadas no backend e personalizadas pelo perfil: funcionário vê os próprios dados; supervisor vê as lojas da sua regional; gerente vê as lojas que gerencia; administrador vê a empresa inteira.
- Alertas inteligentes acompanham prazo e ritmo da meta. Alertas de desenvolvimento incluem práticas do conteúdo comercial e permitem pedir um exemplo à IA; não há alertas de cancelamento ou produto porque essas dimensões não existem na fonte.
- O chat pode exibir um cartão com período, vendas, meta, atendimentos, conversão e comparação agregada da loja que fundamentam uma resposta; conversas da equipe mostram os menores faturamentos no escopo autorizado e permitem abrir o painel individual. Diferenças são tratadas como sinais para investigar, não como diagnóstico automático.
- A IA responde perguntas sobre indicadores e vendas no escopo do perfil selecionado; orientações comerciais usam Gemini quando há chave e consultam a base de conhecimento e exemplos relevantes. Links internos abrem a tela correspondente e mantêm a conversa no modal flutuante. Cada resposta pode receber avaliação humana.
- A área de especialização fica disponível somente ao perfil gerente. Permite cadastrar produtos e associar um ou mais produtos a uma especialização com público, diferenciais, limitações, perguntas e orientação comercial.
- Conteúdo de referência cobre as sete etapas de venda adaptativa, SPIN, Challenger e situações de cliente; o assistente oferece orientação, mas não avalia automaticamente funcionários.
- Importação e exportação CSV, registro de aprendizados por venda, marcação de alertas e auditoria básica.

## Estrutura

```text
sales_platform/       configurações Django, URLs e entrypoints ASGI/WSGI
sales/                modelos, serviços comerciais, API e recuperação de orientação
sales/management/     carga repetível de dados e conteúdo demonstrativo
sales/data/           exemplos de referência para respostas comerciais
sales/templates/      template HTML identado
sales/static/sales/   CSS e JavaScript da interface
requirements.txt      Django, Django REST Framework, SDK Gemini e Langfuse opcional
dados/                briefing e bases fictícias fornecidas para os quatro desafios
apresentacao/         espaço para materiais de apresentação e vídeo
prompts/              histórico de prompts usados no desenvolvimento
DIARIO.md             diário de decisões e aprendizados do participante
```

A rota `/` renderiza `sales/templates/sales/index.html` por meio de `sales/pages.py`. O `index.html` que está na raiz é uma cópia antiga e não é usado pelo Django.

## Rotas principais

As rotas de dados usam `X-Demo-Role` com `funcionario`, `supervisor`, `gerente` ou `administrador`. Gerente e administrador podem incluir `?employee_id=<id>` em dashboard, vendas, produtos e alertas para consultar o recorte individual daquele vendedor, validado pela associação à empresa.

| Rota | Uso |
| --- | --- |
| `GET /api/health/` | Verificar se a API está respondendo |
| `GET /api/dashboard/` | Resumo de vendas, metas, comissões, indicadores e série diária |
| `GET/POST /api/sales/` | Consultar vendas ou cadastrar uma venda para gerente/administrador |
| `POST /api/sales/{id}/reflections/` | Registrar dificuldade e etapa de aprendizado da venda |
| `POST /api/sales/import-csv/` | Importação CSV para gerente/administrador |
| `GET /api/teams/` | Equipes do escopo do perfil |
| `GET /api/people/` | Resumo individual de vendas e metas (gerente/administrador) |
| `GET/POST /api/products/` | Consultar catálogo e métricas separadas ou cadastrar produto (gerente/administrador) |
| `GET /api/alerts/` | Alertas inteligentes visíveis ao perfil e atualizados na consulta |
| `POST /api/alerts/{id}/read/` | Marcar alerta como lido dentro do escopo do perfil |
| `GET/POST /api/conversations/` | Listar e criar conversas por venda/etapa |
| `GET /api/conversations/{id}/` | Carregar mensagens e fontes da conversa |
| `POST /api/assistant/` | Perguntar sobre dados internos ou pesquisar na web |
| `GET /api/assistant/status/` | Consultar disponibilidade da integração Gemini/Search pela chave configurada |
| `POST /api/assistant/messages/{id}/feedback/` | Avaliar uma resposta do assistente |
| `GET/POST /api/specializations/` | Consultar/criar especialização (gerente) |
| `PATCH/DELETE /api/specializations/{id}/` | Editar ou remover especialização (gerente) |

CSV esperado: `external_id,seller_email,team,product_sku,amount,sold_at,customer_name`. O exemplo fica em `sales/fixtures/sales_import_example.csv`.

## Dados e limites

O banco relacional cobre empresas, equipes, membros, produtos, especializações, metas, vendas, alertas, artigos de conhecimento, conversas, mensagens e auditoria. Os cálculos de vendas permanecem no backend. A busca interna da base de treinamento usa palavras-chave como uma versão simples de recuperação contextual; pode evoluir para embeddings e pgvector.

Uma situação pronta para avaliar a dor proposta, com números reais dos CSVs fictícios e limites de inferência, está em [apresentacao/validacao-da-dor.md](apresentacao/validacao-da-dor.md).

Esta versão é uma demonstração. Para produção, troque a seleção de perfil por autenticação e autorização reais, isole as empresas no servidor, use PostgreSQL e segredos por ambiente, revise LGPD/retensão, adicione testes, migrações versionadas, limites de uso e observabilidade. A pesquisa web usa grounding do Google e pode gerar custos conforme os termos e preços do Google.

No PowerShell, defina a variável para esta sessão antes de iniciar o Django: `$env:GEMINI_API_KEY = 'sua-chave'`. Não salve chaves no repositório.
