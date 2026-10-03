# Status do pivô IoT: onde estamos em 3 de outubro de 2026

Para a Natália. Resumo do que existe, com os números que saíram de execuções reais e o que ainda não prova nada.

## 1. Em uma frase

O software do serviço (custo por faixa de tarifa, ranking, alertas, antes e depois, desligamento remoto com registro, eventos de queda) está funcionando de ponta a ponta sobre dado público real. Falta o que não depende de código: hardware próprio, uma empresa de teste e os donos de cada frente.

## 2. O que está pronto

1. M1, aconselhamento: custo por faixa horária (tarifa Neoenergia PE), ranking de equipamentos e recomendações a partir de fatura e curva de carga.
2. M2, plataforma: API com chave por empresa, cadastro de sensores e equipamentos, desligamento remoto com comando assinado e registro de quem mandou, dashboard com 11 telas.
3. M3, modelos: baseline de consumo, LightGBM por equipamento, alertas com explicação, antes e depois e estudo de previsão do dia seguinte.
4. Simulador de sensor: repete uma série real como se fosse o dispositivo, com queda de Wi-Fi, queda de energia, bateria e relógio próprio.
5. Novo nesta rodada: eventos do dispositivo (último suspiro, queda de energia, falha de conexão) agora chegam à plataforma e aparecem na tela Eventos, com o horário do relógio do dispositivo.

Dados: CU-BEMS 2018, andar 2 (24 equipamentos, 19 modelados), 22 semanas. É um prédio da Tailândia, não é dado brasileiro nem de cliente.

Qualidade do código: 451 testes passando, tipagem estrita limpa, contratos de camadas respeitados.

## 3. Números (todos de execução real, período reservado de 4 semanas)

### Previsão do dia seguinte

| Previsor | Mediana do erro (MASE, menor é melhor) |
|---|---|
| Naive sazonal de 168 h (mesma hora da semana passada) | 0,509 |
| Naive sazonal de 24 h | 0,729 |
| Ridge | 0,694 |
| LightGBM sem o consumo da hora anterior | 0,655 |
| Média por hora da semana (o baseline antigo) | 1,751 |

Nenhum modelo treinado bateu o naive de 168 h pela regra definida antes de rodar. Adotado: o naive de 168 h. O baseline antigo era o pior.

### Alertas de anomalia

1. Trocamos o baseline dos alertas pelo naive de 168 h, com a escala refeita toda semana.
2. No benchmark sintético (anomalias injetadas por nós): detecção de 88 de 114 eventos (antes 84) e 99 horas de falso alarme em 9.145 (antes 114).
3. No dado real saíram 128 alertas de z-score e 54 do LightGBM. Nenhum foi corroborado por alguém de fora, porque não existe cliente. São candidatos.

### Antes e depois (economia)

Injetamos uma redução conhecida de 15% e medimos quanto cada método recupera, com tolerância de 3 pontos percentuais:

| Método | Equipamentos dentro da tolerância | Alvo (injetado 15%) |
|---|---|---|
| Baseline normalizado | 7 de 19 | 27,2% (fora) |
| Com grupo de controle | 12 de 19 | 17,1% (dentro) |

O grupo de controle é melhor, mas nenhum dos dois atinge a tolerância em todos os equipamentos. Hoje não dá para prometer um número de economia a cliente.

## 4. O que não está provado

1. Nada disso foi testado em hardware real: tempo do último suspiro, curva da bateria, deriva do relógio em campo.
2. O benchmark de anomalias é sintético. Não é precisão nem recall em dado real.
3. A economia é validação do método com redução injetada, não economia de verdade.
4. Um andar, uma janela de teste de 4 semanas. A classificação dos métodos pode mudar com outra janela.
5. O LightGBM e o Ridge foram avaliados com modelo fixo no período de teste. Reajuste semanal deles não foi testado.
6. A prova de dano contra a distribuidora segue fora: depende do parecer jurídico e regulatório (frente H).

## 5. O que depende de decisão sua e do professor

1. Donos de cada frente e quantas pessoas existem no grupo.
2. Que tipo de empresa e equipamento o professor tem em mente. Isso define sensor, tarifa e o que é carga grande demais para tomada.
3. Ambiente do grupo para os primeiros dados reais (casa, laboratório) e quais equipamentos medir.
4. Forma de cobrança: mensalidade fixa por sensor, faixa de consumo ou parte da economia.
5. Neoenergia: parceira ou contraparte adversarial pela prova de dano. As duas posições não cabem juntas.

## 6. Caminho crítico e próximos passos

O código não é mais o gargalo. O caminho crítico é hardware próprio e dado real do próprio grupo.

1. Cotar 3 a 5 sensores comerciais e montar a lista de componentes da placa com bateria, e pedir já os componentes de prazo longo.
2. Escolher o ambiente de coleta e ligar o primeiro sensor, só com recomendação (desligamento remoto desativado até passar o checklist de segurança).
3. Rodar o mesmo ciclo do M3 em dado medido por nós, para ver se o naive de 168 h e o grupo de controle se sustentam fora da Tailândia.
4. Ler a regra da ANEEL sobre ressarcimento por dano elétrico antes de prometer qualquer prova a cliente.
