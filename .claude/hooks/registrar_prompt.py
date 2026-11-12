#!/usr/bin/env python3
"""Guarda cada prompt enviado ao Claude Code em prompts/claude-code/.

O Claude Code roda este script a cada mensagem (evento UserPromptSubmit) e passa
um JSON na entrada padrão. O script acrescenta o prompt ao arquivo Markdown do dia.

Ele nunca bloqueia nem altera a mensagem: qualquer erro é ignorado, e nada é
impresso, porque o que um hook deste evento imprime vira contexto para a IA.
"""

import datetime
import json
import os
import sys


def main():
    dados = json.load(sys.stdin)
    prompt = (dados.get("prompt") or "").strip()
    if not prompt:
        return
    raiz = os.environ.get("CLAUDE_PROJECT_DIR") or dados.get("cwd") or os.getcwd()
    agora = datetime.datetime.now().astimezone()
    pasta = os.path.join(raiz, "prompts", "claude-code")
    os.makedirs(pasta, exist_ok=True)
    caminho = os.path.join(pasta, f"{agora:%Y-%m-%d}.md")
    novo = not os.path.exists(caminho)
    sessao = (dados.get("session_id") or "")[:8]
    with open(caminho, "a", encoding="utf-8") as arquivo:
        if novo:
            arquivo.write(f"# Prompts de {agora:%d/%m/%Y}\n")
        arquivo.write(f"\n## {agora:%H:%M:%S} · sessão {sessao}\n\n````text\n{prompt}\n````\n")


try:
    main()
except Exception:
    pass
sys.exit(0)
