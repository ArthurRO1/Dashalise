# Desafio do Programa de Estágio FullStore

Repositório base do desafio prático. Cada participante cria a sua cópia, privada, a partir dele.

**Comece pelo [BRIEFING.md](BRIEFING.md):** o contexto da FullStore, os quatro desafios e como funciona a seleção.

## Como começar

1. Nesta página do GitHub, clique em **Use this template** e depois em **Create a new repository**.
2. Dê um nome ao repositório, marque **Private** e crie.
3. Em **Settings → Collaborators**, convide o usuário `rodrigoimenes`.
4. Clone o repositório. Os dados do seu desafio já estão em `dados/`.

## Regras

- Tudo vai para o repositório: código, apresentação, anotações e prompts.
- Faça commits pequenos, cada um com uma ideia só, ao longo da semana, inclusive do que deu errado.
- Não apague nem reescreva o histórico: nada de squash, de `--amend` em commit já enviado ou de `push --force`.
  Queremos ver as suas escolhas e a evolução do projeto.
- **Prazo:** só serão aceitos commits feitos até 13/11/2026, antes das 18h (horário de Brasília).

## IA e prompts

O uso de IA está liberado. A banca quer ver como você usou, por isso o histórico dos prompts fica em `prompts/`.

| Ferramenta | Como o prompt é registrado |
| --- | --- |
| Claude Code | Sozinho: a cada mensagem, o prompt vai para `prompts/claude-code/<data>.md`. Precisa de Python 3 instalado. Depois da primeira mensagem, confira se o arquivo apareceu |
| Cursor, Copilot, Codex | O `AGENTS.md` pede para a IA registrar os pedidos em `prompts/<ferramenta>/`. Ela pode esquecer: confira |
| ChatGPT, Claude.ai, Gemini e outros chats | À mão: exporte a conversa ou cole o link de compartilhamento em `prompts/chats.md` |

Não cole senhas nem chaves nos prompts: esses arquivos vão para o GitHub.

## Pastas

| Pasta ou arquivo | O que vai nela |
| --- | --- |
| `BRIEFING.md` | Os desafios e as regras da seleção |
| `apresentacao/` | Os slides, de preferência em PDF, e o link do vídeo da demo |
| `dados/` | Os dados dos quatro desafios, uma pasta para cada |
| `prompts/` | O histórico dos prompts |
| `DIARIO.md` | O seu diário: decisões, erros e aprendizados de cada dia |

## Dúvidas

Pelo WhatsApp que está no grupo do estágio.
