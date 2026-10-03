# Simulador do dispositivo (M2): notas

Data: 2026-10-01. Pacote `src/mapen_simulador/`. Todos os numeros abaixo vem de execucoes reais desta sessao.

**O que e:** um modelo em software do comportamento de firmware que o plano e a spec exigem do hardware proprio (log local com RTC, buffer circular, Wi-Fi e energia da rede que caem, bateria com autonomia, "ultimo suspiro", envio em lote na volta) mais um emissor de comando assinado. Serve para testar a API e o contrato de ingestao e comando antes de existir placa. **Nao prova nada sobre hardware real** (ver "Limites").

## Mapa de camadas

Contratos no `pyproject.toml` (import-linter): `interface > infrastructure > application > domain`; domain e application sem duckdb, pandas, httpx, fastapi, pydantic, M1 nem as camadas externas da plataforma (so `mapen_plataforma.domain` e permitido); nenhuma outra peca importa o simulador.

| Camada | Arquivo | Papel |
|---|---|---|
| domain | `relogio.py` | `RelogioDispositivo`: RTC com deriva em ppm |
| domain | `cenario.py` | `Janela`, `Cenario` (quedas de Wi-Fi e de energia, autonomia), `Conectividade` (online / wifi_down / mains_down) |
| domain | `carga.py` | `SerieCarga` (perfil de carga; `None` = sensor nao mediu), `Medida` |
| domain | `amostras.py` | `Amostra` (com `seq` e hora do RTC), `LoteLeituras` (id deterministico `device:primeira-ultima`) |
| domain | `dispositivo.py` | `DispositivoSimulado`: dono do ciclo (buffer circular, maquina de conectividade, ultimo suspiro, contagem regressiva da bateria, lotes na volta, confirmacao so apaga do buffer) |
| domain | `eventos.py`, `relatorio.py` | eventos do dispositivo (`ultimo_suspiro`, `queda_energia`, `falha_conexao`), lacunas, relatorio |
| domain | `comando.py` | regra de emissao: validade em (0, 60 s]; chama `assinar` e `ComandoRele` da plataforma (nada de canonicalizacao nem HMAC duplicado) |
| application | `portas.py` | `Relogio`, `GeradorNonce`, `ProvedorChaves`, `FonteSerie`, `EnvioLeituras`, `EnvioComando` |
| application | `casos_de_uso.py` | `SimularSensor` (repete a serie com cenario de falhas) e `EmitirComando` |
| infrastructure | `api_http.py` | cliente httpx: leituras com token do dispositivo, comandos com Bearer da empresa |
| infrastructure | `serie_m1.py` | `FonteSerieM1`: le a tabela `leitura` pelo leitor do M1 (`LeiturasDuckDB`), kWh/min vira W |
| infrastructure | `chaves.py` | `ChaveDerivada` (usa `derivar_chave_comando` da plataforma com segredo mestre + sal) e `ChaveFixa` |
| infrastructure | `relogio.py`, `nonces.py`, `cenario_json.py` | relogio do sistema, nonce uuid4, cenario em arquivo JSON |
| interface | `cli.py` | `mapen-simulador simular` e `emitir` |

## Variaveis de ambiente

| Variavel | Uso |
|---|---|
| `MAPEN_SIM_URL` | URL da API (padrao `http://127.0.0.1:8000`) |
| `MAPEN_SIM_TOKEN` | token do dispositivo (`simular`) |
| `MAPEN_SIM_CHAVE_API` | chave Bearer da empresa (`emitir`) |
| `MAPEN_SIM_CHAVE_COMANDO` | chave de comando do dispositivo em hex (`emitir`) |
| `MAPEN_SEGREDO_MESTRE` + `MAPEN_SIM_SAL` | alternativa a `MAPEN_SIM_CHAVE_COMANDO`: a chave e derivada como a plataforma faz |
| `MAPEN_DB_M1` | banco do M1 com a CU-BEMS (padrao `data/mapen_m1.duckdb`) |

Segredo nunca vai em argumento de linha de comando.

## Rodar um cenario ponta a ponta (API local)

O console script `mapen-simulador` so existe depois de `pip install -e .` com setuptools; sem isso use `python -m mapen_simulador.interface.cli` (igual).

1. Subir a API de demo em outro terminal (copia do banco, chaves fixas; os tokens saem no stdout):

```
cp data/mapen_m1.duckdb /tmp/demo_m2.duckdb
MAPEN_DB=/tmp/demo_m2.duckdb MAPEN_SEGREDO_MESTRE=segredo-mestre-0123456789abcdef MAPEN_CHAVE_API_DEMO=chave-demo-0123456789abcdef0123 \
  .venv/bin/uvicorn --factory mapen_plataforma.interface.api.composicao:criar_app_padrao --port 8765
```

2. Copiar da linha `[demo] empresa=demo ...` o `token_dispositivo` e a `chave_comando`. Queda de Wi-Fi de 10 min e queda de energia de 15 min (bateria de 30 min), repetindo 2 h do `z1_AC1` da CU-BEMS num eixo de tempo novo (as leituras de 2018 ja estao no banco, entao sem `--reiniciar-em` nada de novo seria gravado):

```
export MAPEN_SIM_URL=http://127.0.0.1:8765 MAPEN_SIM_TOKEN=<token_dispositivo>
.venv/bin/python -m mapen_simulador.interface.cli simular --sensor-id cu_bems_2018Floor2 --equipamento z1_AC1 \
  --inicio 2018-08-06T10:00 --minutos 120 --reiniciar-em 2026-10-07T10:00-03:00 \
  --wifi-fora 10:10 --energia-fora 50:15 --bateria-min 30
```

`--wifi-fora INI:DUR` e `--energia-fora INI:DUR` (minutos desde o inicio, repetiveis), `--deriva-ppm`, `--lote`, ou `--cenario arquivo.json` (formato em `infrastructure/cenario_json.py`). Imprime o relatorio em JSON.

3. Emitir comando (flag de desligamento remoto comeca desligada por empresa):

```
export MAPEN_SIM_CHAVE_API=chave-demo-0123456789abcdef0123 MAPEN_SIM_CHAVE_COMANDO=<chave_comando>
curl -s -X PUT -H "Authorization: Bearer $MAPEN_SIM_CHAVE_API" -H 'content-type: application/json' \
  -d '{"desligamento_remoto_habilitado":true}' $MAPEN_SIM_URL/configuracao
.venv/bin/python -m mapen_simulador.interface.cli emitir --device-id cu_bems_2018Floor2 --empresa-id demo \
  --equipamento-id cu_bems_2018Floor2:z1_AC1 --acao desligar
```

Saida `{"aceito": true, "status": 200, ...}` (exit 0) ou a recusa com o motivo (exit 1). Depois, parar o uvicorn.

## Resultados reais dos cinco cenarios

Testes em `tests/simulador/` (API real da plataforma em processo, `TestClient`), 28 testes; passo de 1 min, 60 min de serie. Conferencia direta na tabela `leitura`.

| # | Cenario | Resultado |
|---|---|---|
| 1 | Leituras estaveis | 60 registradas, 60 confirmadas, 60 linhas na tabela com os instantes esperados, sem lacuna nem evento |
| 2 | Wi-Fi fora 10 min | 60 linhas, sem buraco; as 10 amostras guardadas saem num unico lote de 11 na volta, com a hora do dispositivo; 1 evento `falha_conexao` de 600 s. Reenvio de cada lote (2b) e ack perdido com reenvio do mesmo id (2c): 60 linhas, 60 distintas, zero duplicata. Hora gravada = hora do RTC com deriva de 1000 ppm (2d) |
| 3 | Queda de energia de 15 min, bateria de 30 | `ultimo_suspiro` com o inicio pelo RTC; `queda_energia` com duracao calculada pelo RTC (900,45 s com deriva de 500 ppm, contra 900 s reais); registro continuou na bateria, sem lacuna; um unico lote com os 15 minutos, enviado so depois da volta; 60 linhas |
| 4 | Queda de 30 min, bateria de 10 | 40 registradas e 40 linhas; lacuna real de 20 amostras (do minuto 29 ao 50), nenhuma linha dentro dela, sem interpolacao; `queda_energia` de 1800 s com `bateria_esgotada`. Com RTC que nao sobrevive (4b): duracao e fim ficam `None`, nao se inventa |
| 5 | Comando | aceito (flag ligada, nao critico); `ligar` aceito com flag desligada; recusados: critico (`equipamento_critico`), expirado (`validade_vencida`), nonce repetido (`nonce_repetido`), `equipamento_id` adulterado (`assinatura_invalida`), flag desligada (`desligamento_remoto_desabilitado`), chave errada; validade fora de (0, 60 s] nem e assinada. A chave derivada pelo simulador e identica a do provisionamento |
| extra | Buffer circular de 5 posicoes, 20 min sem Wi-Fi | 16 perdidas (20 min + a amostra da volta, que entra antes do envio), contadas no relatorio; as mais antigas e perdidas |

Execucao ao vivo (CLI contra uvicorn local, banco de demo em copia, depois parado; sem processo restante e porta livre; 120 min de `z1_AC1` em quatro dias novos): estavel 120 registradas e 120 linhas; Wi-Fi 10 min: 120 linhas, 1 `falha_conexao` de 600 s, 110 envios (um deles com 11 amostras); energia 15 min com bateria de 30: 120 linhas, queda de 900 s, sem lacuna; energia 30 min com bateria de 10: 100 linhas (conferidas no banco, 100 distintas), lacuna de 20 amostras. Comandos: flag desligada recusado, flag ligada aceito (`desligar` e `ligar`), equipamento critico recusado.

## Suite e verificacoes

- `gtimeout 900 .venv/bin/pytest -W error -q`: 350 passed (28 do simulador).
- `.venv/bin/mypy` (strict, inclui `src/mapen_simulador` e `tests/simulador`): `Success: no issues found in 129 source files`.
- `.venv/bin/lint-imports`: `Contracts: 12 kept, 0 broken` (3 novos).

## Provas vermelhas

Metodo: copia do repositorio fora dele (diretorio de rascunho da sessao, sem git), quebra deliberada, teste rodado; depois a copia foi refeita a partir do repositorio. A copia intacta deu 28 passed.

1. Buffer descartado na reconexao (`self._buffer.clear()` ao voltar o Wi-Fi): 4 testes falharam (`test_2`, `test_2b`, `test_2c`, `test_buffer_circular`).
2. Nonce reutilizavel (`NonceDuckDB.registrar` sempre `True`): 1 falhou (`test_5_recusado_com_nonce_repetido`).
3. Assinatura sem `equipamento_id` na mensagem: 1 falhou (`test_5_recusado_com_equipamento_id_adulterado`).
4. Contrato de camadas: `domain` importando `infrastructure` e `application` importando `httpx`: `lint-imports` `Contracts: 10 kept, 2 broken` (camadas e dominio sem I/O do simulador).

## Limites (leia antes de citar qualquer numero)

1. Isto simula o **comportamento esperado do firmware**. Nao prova nada sobre hardware real: tempo de ultimo suspiro (N), consumo e curva de descarga da bateria, deriva do RTC em campo e com temperatura, perda de pacote e comportamento do radio.
2. O ultimo suspiro nunca falha aqui (a spec manda validar o tempo N em bancada). A bateria descarrega linearmente no passo de amostragem e **volta cheia** assim que a energia retorna; recarga nao e modelada.
3. Premissa: sem energia da rede, o roteador tambem cai, entao nao ha envio durante a queda. Janela de falha menor que um passo e recusada.
4. A deriva do RTC e constante em ppm; sem salto de hora, sem ressincronizacao por NTP.
5. (Resolvido em 2026-10-02) A plataforma ganhou `POST /sensores/{id}/eventos` (ver `docs/m2_seguranca_notas.md`, "Eventos do dispositivo"). O simulador envia os eventos pelo `EnvioEventosHttp` com o mesmo token das leituras: so com conexao (o ultimo suspiro sai junto com a queda, na volta da energia, pela premissa 3), o dispositivo guarda o evento ate o servidor confirmar (ack perdido ou rede ruim = reenvia; o servidor deduplica) e o relatorio traz `eventos_confirmados` e `eventos_nao_confirmados`. Sem `envio_eventos` o comportamento antigo se mantem (eventos so no relatorio). Testes: `tests/simulador/test_eventos.py` (9 casos contra a API real em processo). Prova vermelha por troca no codigo: confirmar evento sem ack = 3 falhas; enviar sem conexao = 3 falhas.
6. A idempotencia do lote vem da chave (sensor, equipamento, ts) da tabela `leitura`; o id do lote existe so no dispositivo (a API nao recebe id de lote nem registra desvio do relogio do servidor, que a spec cita).
7. Tempo virtual: o simulador anda a serie em ordem sem dormir; nao reproduz atrasos de rede nem concorrencia entre dispositivos.
8. Premissa do relatorio: lacuna = diferenca entre registros consecutivos maior que 1,5 passo, medida no relogio do dispositivo.
9. A serie vem da CU-BEMS (predio com ar-condicionado e luz), kWh por minuto convertido em potencia media; minuto `ausente` do M1 nao e medido (lacuna), nunca preenchido.
10. TLS, rate limiting e botao fisico continuam fora (ver `docs/m2_seguranca_notas.md`).
