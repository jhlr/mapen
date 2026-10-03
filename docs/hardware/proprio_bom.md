# BOM preliminar da placa propria (sensor de rede com last gasp)

Data de consulta: 2026-10-01. Rascunho de estudo, nao projeto validado.
Taxa: PTAX venda 2026-09-30 = R$ 5,1809/USD, fonte https://www.piranot.com.br/2026/09/30/noticias/economia/dolar-ptax-fecha-em-r-51809-nesta-quarta-feira-veja-a-cotacao-oficial/ (acessado 2026-10-01). Conversao = USD x 5,1809 (cálculo); sem frete, impostos de importacao nem IOF.

## Componentes

| # | Funcao | Part number exemplo | Preco unitario (qtd 1, visto 2026-10-01) | Papel / observacao | Fonte |
|---|---|---|---|---|---|
| 1 | MCU Wi-Fi | ESP32-WROOM-32E-N4 | USD 3,7644 = R$ 19,50 (cálculo), LCSC | Wi-Fi 2,4 GHz + BLE; flash de 4 MB no modulo (log local) | https://www.lcsc.com/product-detail/C701341.html |
| 2 | CI de medicao | ATM90E26-YU-R (SSOP-28) | USD 2,311 = R$ 11,97 (cálculo), LCSC | Monofasico, 0,1% energia ativa, faixa dinamica 5000:1, 3,3 V | https://www.lcsc.com/product-detail/C616398.html |
| 2b | Alternativa de medicao | BL0937 (SOP-8) | USD 0,2535 = R$ 1,31 (cálculo), segundo a busca; pagina LCSC mostra sem estoque | Saida em pulsos, erro < 0,5% em 2500:1; menos fino | https://www.lcsc.com/product-detail/Energy-Metering-ICs_BL-Shanghai-Belling-BL0937_C2684338.html |
| 3 | RTC com backup | PCF8523T/1,118 | USD 1,0595 (10+) = R$ 5,49 (cálculo), LCSC | Troca automatica VDD/VBAT; VBAT 1,8 a 5,5 V com gerencia de energia ativa | https://www.lcsc.com/product-detail/C2651516.html |
| 3b | RTC alternativo | DS3231 (modulo Eletrogate) | nao encontrado em 2026-10-01 (pagina sem preco, esgotado) | Pagina cita < 500 nA em modo bateria | https://www.eletrogate.com/real-time-clock-rtc-ds3231 |
| 4 | Memoria nao volatil | FM24CL64B-G (FRAM 64 Kbit, I2C) | USD 1,2974 (versao GTR, LCSC) = R$ 6,72 (cálculo); Mouser USD 3,16 (resultado de busca) | FRAM aguenta muitas escritas; guarda o carimbo do last gasp. Flash do ESP32 serve para log longo | https://www.lcsc.com/product-detail/C9829.html |
| 5 | Supercapacitor | KEMET FT0H105ZF (1 F, 5,5 V) | USD 6,19 = R$ 32,07 (cálculo), Mouser, resultado de busca (pagina nao abriu) | Reserva do last gasp e do RTC. Corrente de fuga: nao encontrado em 2026-10-01 | https://www.mouser.com/ProductDetail/KEMET/FT0H105ZF?qs=BenOyfdfArrd0jy7BORhIQ%3D%3D |
| 6 | Rele | Modulo rele 1 canal 5 V (Eletrogate) | R$ 7,50 (resultado de busca) | Corte remoto. E modulo de bancada, nao serve na placa final; rele nu 10 A/250 V: nao encontrado em 2026-10-01 | https://www.eletrogate.com/modulo-rele-1-canal-5v |
| 7 | Fonte isolada CA-CC | Hi-Link HLK-PM01 (5 V, 3 W) | R$ 29,41 Pix (R$ 30,96 normal), Eletrogate | 100-240 V CA, 600 mA continuo, protecao de curto. Classe de isolamento e certificacao: nao encontrado na pagina | https://www.eletrogate.com/mini-fonte-hlk-pm01-100-240vac-para-5vdc-3w |
| 8 | Varistor | S14K275 (275 V RMS, 14 mm) | R$ 1,49 (Soldafria, resultado de busca) | Supressao de surto na entrada, depois do fusivel | https://www.soldafria.com.br/varistor-14k-275vac-s14k275-dnr14d431k |
| 9 | Fusivel | 250 V, 5x20 mm (valor a definir) | nao encontrado em 2026-10-01 | Protecao contra curto antes do varistor | - |
| 10 | Sensor de corrente (TC) e regulador 3,3 V | nao definidos | nao pesquisado | Necessarios; regulador depende da queda minima de entrada | - |

Subtotal dos itens 1, 2, 3, 4, 5, 6, 7, 8: 19,50 + 11,97 + 5,49 + 6,72 + 32,07 + 7,50 + 29,41 + 1,49 = R$ 114,15 (cálculo; mistura loja e distribuidor; sem PCB, TC, fusivel, regulador, conectores nem caixa).

## Abordagem de isolamento (decisao em aberto)

1. Corrente por TC: isola galvanicamente o lado de corrente. Modelo e preco: nao pesquisado.
2. Tensao por divisor resistivo: o lado de baixa tensao fica no potencial da rede. A placa inteira fica "viva": caixa isolante, sem partes acessiveis, e porta de debug/serial so por isolador. Nunca ligar a serial a um PC com a placa energizada.
3. Alternativa: transformador de tensao de medicao, mantem tudo isolado. Modelo e preco: nao pesquisado.

## Supercapacitor: dimensionamento (estimativa)

Formula: t = C * (V1 - V2) / I, corrente constante, sem ESR e sem fuga (aproximacao otimista). Todas as premissas abaixo sao minhas, nao medidas.

- C = 1 F (KEMET FT0H105ZF); V1 = 5,0 V (abaixo dos 5,5 V nominais).
- Cenario A, last gasp (ESP32 sem radio, so gravar na FRAM): I = 50 mA. Consumo de 30-50 mA com CPU a 240 MHz e radio desligado, segundo resumo de busca do datasheet https://www.espressif.com/sites/default/files/documentation/esp32-wroom-32e_esp32-wroom-32ue_datasheet_en.pdf (nao aberto). V2 = 3,5 V (queda minima do regulador, hipotese). t = 1 * (5,0 - 3,5) / 0,050 = 30 s (cálculo). Basta para gravar o evento; Wi-Fi nao cabe nesse orcamento.
- Cenario B, so o RTC: PCF8523 em VBAT, I = 3600 nA (maximo, -40 a 85 C, 2 a 5 V, tabela de caracteristicas do datasheet NXP https://www.nxp.com/docs/en/data-sheet/PCF8523.pdf, lido em 2026-10-01). V2 = 1,8 V (VBAT minimo com gerencia de energia ativa). t = 1 * (5,0 - 1,8) / 3,6e-6 = 888.889 s = 10,3 dias (cálculo). Com o valor tipico de 150 nA (25 C, 3 V) a conta da 21,3e6 s, sem sentido pratico porque a autodescarga domina.
- Limite real: a fuga do supercap nao entrou na conta (nao encontrado em 2026-10-01). Referencia generica: supercap cai de 100% a 50% em cerca de 1 mes, segundo https://batteryguy.com/kb/knowledge-base/supercapacitors-versus-batteries/ (resumo de busca, nao aberto). Se valer para este componente, "dias" so se confirma com medicao em bancada.
- O rele fica fora do orcamento: a bobina consome muito mais que o ESP32. Usar rele de travamento (latching) ou aceitar que solte na queda. Corrente de bobina: nao pesquisada.

## Supercapacitor vs litio

| Criterio | Supercapacitor | Bateria de litio |
|---|---|---|
| Energia por massa | baixa (5-8 Wh/kg) | alta (100-180 Wh/kg) |
| Autodescarga | alta (100% a 50% em ~1 mes) | baixa (~5% em 1 mes) |
| Ciclos | ordem de milhoes | menor |
| Uso na placa | last gasp (segundos), RTC por poucos dias | RTC por meses; Wi-Fi por mais tempo |

Fontes (resumos de busca, nao abertos): https://www.e3s-conferences.org/articles/e3sconf/pdf/2024/121/e3sconf_icrera2024_01010.pdf ; https://batteryguy.com/kb/knowledge-base/supercapacitors-versus-batteries/ . Litio exige carregador e protecao, e e risco de incendio em produto ligado a rede; requisitos de certificacao e transporte: nao pesquisados. Alternativa para o RTC: pilha-botao primaria (ex. CR2032), nao cotada.

## Seguranca e certificacao

1. Tensao de rede: isolamento reforcado, distancias de isolacao e de fuga e norma de seguranca aplicavel (ex. familia IEC 62368): nao pesquisado nesta rodada. Revisao por profissional habilitado antes de ligar na tomada; testar primeiro com autotransformador isolador e lampada em serie.
2. Caixa: material isolante, sem acesso a partes vivas; norma de grau de protecao: nao pesquisada.
3. Anatel (Wi-Fi 2,4 GHz): radiacao restrita, Ato 14448/2017. Segundo https://yescert.com.br/blog/anatel/modulos-iot-2026-wifi-bluetooth-zigbee-lora-reaproveitamento/ (acessado 2026-10-01), a Resolucao 780/2025 teria revogado a isencao: o integrador do produto final normalmente precisa de homologacao propria, podendo referenciar o certificado do modulo e testar so o sistema (EMC, eletrico). Fonte e blog de consultoria; confirmar na Anatel. Trocar antena ou firmware que altere parametros de RF exige nova avaliacao. Custos e prazos: nao encontrado em 2026-10-01.
4. Inmetro: plugues e tomadas (ate 250 V e 20 A) tem certificacao compulsoria pela Portaria 90/2022 e NBR 14136, segundo https://yescert.com.br/blog/inmetro/portaria-inmetro-90-2022-plugues-tomadas/ (resumo de busca). Se a placa virar tomada/adaptador, entra nesse escopo; se for modulo de painel: nao verificado. Fonte oficial: http://www.inmetro.gov.br/qualidade/pluguestomadas/base-normativa.asp (nao aberta).
5. Para pesquisa e demonstracao, usar um candidato ja certificado (ver candidatos.md) reduz o risco ate a placa propria ser avaliada.
