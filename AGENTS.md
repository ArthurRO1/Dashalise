# Instruções para assistentes de IA

Este repositório é de um participante do Programa de Estágio FullStore, que trabalha sozinho num desafio prático.
A banca vai ler o histórico do git e os prompts para entender como ele pensou e evoluiu. Siga estas regras:

1. **Commits pequenos e coesos.** Uma ideia por commit, com a mensagem em português dizendo o que mudou e por quê.
2. **Não reescreva o histórico.** Nada de `git commit --amend` em commit já enviado, `rebase` de commits
   publicados, squash ou `git push --force`. Erros também ficam no histórico: corrija com um commit novo.
3. **Registre os prompts.** O Claude Code já registra sozinho em `prompts/claude-code/`. Se você é outra
   ferramenta (Cursor, Copilot, Codex…), ao começar cada tarefa acrescente o pedido do usuário, como ele
   escreveu, e a hora em `prompts/<nome-da-ferramenta>/AAAA-MM-DD.md`. Inclua esse arquivo no commit da tarefa.
4. **O diário é do participante.** Ao terminar uma tarefa, lembre o usuário de anotar no `DIARIO.md` o que
   decidiu, o que deu errado e o que aprendeu, mas não escreva o diário por ele.
5. **Só dados fictícios.** Use os dados do desafio em `dados/` ou dados que o participante criou. Nada de dados
   reais de pessoas ou empresas.
6. **Nada de segredos no repositório.** Senhas, tokens e chaves de API ficam em variáveis de ambiente ou num
   `.env`, que já está no `.gitignore`.
