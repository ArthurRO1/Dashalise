# Desafio 4 — O treinamento certo, na hora certa

Dados fictícios da Rede Aurora. Nenhuma pessoa, loja ou conteúdo é real.
O histórico vai de **01/08/2026 a 01/11/2026**. O cenário da demo é **novembro de 2026** (veja o calendário).

## Arquivos

| Arquivo | Linhas | O que é |
| --- | --- | --- |
| `catalogo_conteudos.csv` | 300 | A biblioteca: título, tema, formato, duração, público, nível, pré-requisito, coleção, se tem quiz e quando foi publicado |
| `colaboradores.csv` | 1225 | Todos que trabalham nas lojas: cargo, loja, admissão, desligamento, escala, folgas e turno. Inclui as admissões já marcadas para novembro |
| `ferias.csv` | 146 | Férias de agosto a dezembro de 2026, já tiradas ou marcadas |
| `lojas.csv` | 120 | As lojas e suas regionais |
| `indicadores_diarios_loja.csv` | 11003 | Uma linha por loja por dia: valor vendido, vendas, peças e atendimentos |
| `historico_envios.csv` | 59515 | Todo conteúdo enviado a cada colaborador de agosto a outubro, e o que ele fez com o conteúdo |
| `calendario_novembro_2026.csv` | 9 | O que acontece na rede em novembro |

## historico_envios.csv

| Coluna | O que é |
| --- | --- |
| `data_envio` | Quando o conteúdo foi enviado |
| `conteudo_id` | O conteúdo, em `catalogo_conteudos.csv` |
| `colaborador_id` | Quem recebeu, em `colaboradores.csv` |
| `origem` | `semanal` (o envio de toda terça para a rede), `integração` (o pacote de quem acabou de entrar) ou `campanha` |
| `aberto_em` | Quando a pessoa abriu; vazio se nunca abriu |
| `percentual_consumido` | Quanto do conteúdo a pessoa viu ou leu, de 0 a 100 |
| `concluido` | `sim` quando a pessoa consumiu 90% ou mais |
| `nota_quiz` | De 0 a 10, só para conteúdos com quiz que foram concluídos |

## Como calcular os indicadores

| Indicador | Conta |
| --- | --- |
| Ticket médio | valor vendido ÷ vendas |
| P.A. (peças por atendimento) | peças ÷ vendas |
| Taxa de conversão | vendas ÷ atendimentos |

As folgas estão em dias da semana (`seg`, `ter`…). Lojas de rua não abrem aos domingos.
