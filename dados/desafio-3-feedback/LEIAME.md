# Desafio 3 — O feedback que ninguém dá

Dados fictícios da loja do Diego: L004, Aurora Shopping Centro, São Paulo. Nenhuma pessoa ou venda é real.
O período vai de **01/08/2026 a 01/11/2026**. O cenário da demo é o fim de outubro.

## Arquivos

| Arquivo | Linhas | O que é |
| --- | --- | --- |
| `vendedores.csv` | 9 | O Diego (gerente) e os 8 vendedores: admissão, escala, folgas, turno e férias no período |
| `indicadores_diarios_vendedor.csv` | 661 | Uma linha por pessoa por dia trabalhado: valor vendido, vendas, peças e atendimentos |
| `metas_vendedor.csv` | 31 | A meta de cada vendedor por mês, com os dias de escala dele no mês |
| `metas_loja.csv` | 4 | A meta da loja por mês |
| `anotacoes_gerente.csv` | 21 | Anotações soltas que o Diego fez no celular ao longo dos meses, do jeito que ele escreveu |
| `anotacoes_regional.csv` | 5 | Anotações da Patrícia, a gerente regional, nas visitas à loja |
| `exemplos_feedbacks_ruins.md` | — | Feedbacks ruins que gerentes da rede já deram |

## Como calcular os indicadores

| Indicador | Conta |
| --- | --- |
| Ticket médio | valor vendido ÷ vendas |
| P.A. (peças por atendimento) | peças ÷ vendas |
| Taxa de conversão | vendas ÷ atendimentos |
| Atingimento da meta | valor vendido no mês ÷ meta do mês |

A meta de cada vendedor é a meta da loja dividida entre os vendedores na proporção dos dias de escala de cada um no mês.
O gerente também vende, mas não tem meta individual.
