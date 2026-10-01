# Candidatos comerciais: tomadas Wi-Fi com medicao e medidor de pinca (CT)

Data de consulta: 2026-10-01. Regra: o que nao foi confirmado em pagina de loja ou do fabricante esta marcado "nao encontrado em 2026-10-01". Precos de loja mudam; "visto" = data em que a pagina foi aberta.

## Tomadas Wi-Fi com medicao de energia

| Modelo | Preco (R$, visto 2026-10-01) | Corrente / tensao max | Protocolo | Firmware aberto | Memoria local / bateria | Anatel / Inmetro | Fonte |
|---|---|---|---|---|---|---|---|
| Tuya "Tomada Smart Wifi 16A" (cod. PLUTOMINTZIGBSM) | 59,90 (58,70 Pix), Luminolandia | 16 A, 100-240 V CA | Nuvem Tuya / app SmartLife; API local: nao encontrado em 2026-10-01 | nao encontrado em 2026-10-01 | nao encontrado em 2026-10-01 | Anatel: nao encontrado na pagina; Inmetro: nao encontrado | https://www.luminolandia.com.br/tomada-smart-wifi-16a-mede-consumo-de-energia-alexa-siri |
| Novadigital TW-BR-16A | 75,00, distribuidorcftv | 16 A, 90-240 V CA | Nuvem (Tuya Smart, SmartLife, NovaDigital, SmartThings); API local: nao encontrado | nao encontrado em 2026-10-01 | nao encontrado em 2026-10-01 | Anatel: sim, codigo 05860-19-11765 (informado pela loja, nao conferido na base da Anatel); Inmetro: nao encontrado | https://www.distribuidorcftv.com.br/loja/produto-240387-3925-tomada_inteligente_wi_fi_16a_com_monitoramento_de_consumo_compativel_com_alexa_e_google_home |
| TP-Link Tapo P110 | Anuncio Mercado Livre listado a 66,90 (so no resultado de busca; pagina devolveu 403, nao confirmado). KaBuM: esgotado, sem preco | 10 A / 2400 W, 100-240 V | Nuvem Tapo; API local: nao encontrado em 2026-10-01 | nao encontrado em 2026-10-01 | nao encontrado em 2026-10-01 | KaBuM cita so CE e RoHS; Anatel/Inmetro: nao encontrado | https://www.kabum.com.br/produto/527346/tomada-inteligente-tp-link-tapo-p110-wi-fi-alexa-e-google-assistent-bivolt-branco-tapo-p110-br ; https://www.mercadolivre.com.br/tomada-inteligente-wi-fi-tapo-p110-tp-link/p/MLB37042297 |
| Shelly Plus Plug US-1 (110 V) | IDMSHOP: indisponivel, preco proprio nao encontrado em 2026-10-01 (a pagina so cita outros itens de R$ 600-1000) | 15 A / 1800 W, 120 V CA (pagina da Shelly: 15 A) | MQTT, RPC/HTTP local, scripts, nuvem Shelly, BLE | nao encontrado em 2026-10-01 (ha API local e scripts, mas isso nao e firmware aberto) | ESP32 com 4 MB de flash (scripts/automacao locais); bateria: nao encontrado | Anatel: a loja cita faixa RF 2,400-2,495 GHz, sem numero de homologacao; Inmetro: nao encontrado | https://www.idmshop.com.br/shelly-tomada-inteligente-comandada-com-medidor-de-consumo-automacao-wi-fi-plus-plug-us-1-110v-branco ; https://kb.shelly.cloud/knowledge-base/shelly-plus-plug-us |

Observacao: a Positivo Smart Plug Max (16 A) aparece em lojas, mas a pagina da KaBuM nao menciona medicao de energia (nao incluida na tabela). Fonte: https://www.kabum.com.br/produto/496181/tomada-inteligente-16a-positivo-max-wi-fi

## Medidor de energia com pinca (CT)

| Modelo | Preco (R$, visto 2026-10-01) | Corrente / tensao max | Protocolo | Firmware aberto | Memoria local / bateria | Anatel / Inmetro | Fonte |
|---|---|---|---|---|---|---|---|
| Shelly Pro 3EM-120 (trifasico, 3 CT de 120 A) | 1.350,00 (1.282,50 Pix), 4tronics | 120 A por fase, CT externos; tensao: nao encontrado na pagina | MQTT, Modbus TCP, scripts mJS; Wi-Fi, Ethernet, BLE | nao encontrado em 2026-10-01 | Memoria: sim, 60 dias a cada 1 min, export CSV/JSON; bateria: nao encontrado | Anatel: nao mencionado na pagina; Inmetro: nao encontrado | https://loja.4tronics.com.br/produtos/shelly-pro-3em/ |
| Shelly EM (2 canais, CT 50 A incluso; versao 120 A existe) | Busca listou R$ 649,90 (smartcasashop); pagina nao abriu (DNS), nao confirmado | 50 A (CT incluso) / 120 A (opcional) | nao verificado | nao encontrado | nao encontrado | nao encontrado | https://www.smartcasashop.com.br/products/modulo-interruptor-inteligente-rele-para-automacao-shelly-em-wifi-120a-com-medidor-de-consumo |

## Pontos a notar

1. Nenhuma pagina de loja trouxe numero de certificado Inmetro para as tomadas com medicao. O Inmetro tem certificacao compulsoria para plugues e tomadas (Portaria 90/2022, NBR 14136, ate 250 V e 20 A, segundo resumo de https://yescert.com.br/blog/inmetro/portaria-inmetro-90-2022-plugues-tomadas/, nao lido na integra). Se uma tomada com medicao entra nesse escopo: nao verificado.
2. Anatel: so a Novadigital apresentou codigo. Conferir qualquer modelo na base publica da Anatel antes de comprar em volume (nao feito aqui).
3. Nenhum dos candidatos tem "last gasp" documentado nem RTC com bateria na pagina: nao encontrado em 2026-10-01. Como referencia de medicao e atalho, nao como substituto da placa propria.
4. Firmware aberto (Tasmota/ESPHome) depende do chip e da revisao; nao foi pesquisado por modelo. Para o grupo, a Shelly (MQTT local + scripts) e a que mais se aproxima do requisito de operar sem nuvem.
