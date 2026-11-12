# Desafio 2 — O número certo, onde a pessoa já está

Dados fictícios da Rede Aurora: 120 lojas, 42 franqueados e 931 vendedores ativos.
Nenhuma pessoa, loja, telefone ou venda é real.

As vendas vão de **01/08/2026 a 01/11/2026** (domingo). O cenário da demo é a manhã de **segunda-feira, 02/11/2026**.

## Arquivos

| Arquivo | Linhas | O que é |
| --- | --- | --- |
| `lojas.csv` | 120 | Cada loja: cidade, regional, gerente regional, franqueado, gerente da loja, tipo (shopping ou rua), inauguração |
| `vendedores.csv` | 1095 | Vendedores e gerentes de loja, com admissão e desligamento (quem saiu no período continua na lista) |
| `usuarios.csv` | 1101 | Quem pode receber informação: papel, o que cada um pode ver (`escopo`), WhatsApp e e-mail fictícios |
| `vendas_diarias_vendedor.csv` | 80136 | Uma linha por vendedor por dia trabalhado: valor vendido, vendas, peças e atendimentos |
| `metas_loja.csv` | 480 | A meta de cada loja em cada mês (agosto a novembro de 2026) |
| `metas_vendedor.csv` | 3750 | A meta de cada vendedor em cada mês, com os dias de escala dele no mês |
| `vendas_loja_ano_anterior.csv` | 10262 | Vendas diárias de cada loja de 02/08/2025 a 02/11/2025, cada data 364 dias antes (mesmo dia da semana) |

## Quem é quem nos dados

- **Marcos Albuquerque**, diretor comercial: vê a rede inteira.
- **Patrícia Lemos**, gerente regional da R1 (São Paulo Capital): vê as 20 lojas da R1.
- **Carla Menezes**, franqueada: dona das lojas L004, L011 e L017.
- **Diego Furtado**, gerente da L004 (Aurora Shopping Centro).
- **Bianca Rocha** e **Lucas Moreira**, vendedores da L004.

## Como calcular os indicadores

| Indicador | Conta |
| --- | --- |
| Ticket médio | valor vendido ÷ vendas |
| P.A. (peças por atendimento) | peças ÷ vendas |
| Preço médio | valor vendido ÷ peças |
| Taxa de conversão | vendas ÷ atendimentos |
| Atingimento da meta | valor vendido no mês ÷ meta do mês |
| Comissão do vendedor | 3% do valor vendido, mais R$ 300 de prêmio se bater a meta do mês |

A meta de cada vendedor é a meta da loja dividida entre os vendedores na proporção dos dias de escala de cada um no mês.

## Observações

- `escopo` em `usuarios.csv`: `rede`, um código de regional (`R1`), uma lista de lojas (`L004,L011,L017`), uma loja (`L004`)
  ou o próprio código do vendedor (`C0003`).
- Os WhatsApp usam o DDD 00, que não existe. Para testar um envio real, usem o número de vocês.
- Os e-mails usam o domínio `aurora.example`, reservado para exemplos.
- Lojas de rua não abrem aos domingos.
