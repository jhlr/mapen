# M2 seguranca: correcoes da revisao adversarial (2026-10-01)

Complemento de `docs/m2_notas.md`. Todos os numeros vem de execucoes reais nesta sessao. Sem hardware: o atuador continua simulado.

## Modelo de ameaca (10 linhas)

1. Ativo protegido: o canal de comando que liga/desliga cargas de um cliente (e os dados de consumo por empresa).
2. Atacante 1: cliente anonimo na rede que adivinha ids e manda `X-Empresa-Id` (antes bastava o header).
3. Atacante 2: usuario autenticado de uma empresa que sonda recursos e dispositivos de outra (tenant spoofing).
4. Atacante 3: quem captura um comando assinado e o repete, o adia por anos ou o reaponta a outro equipamento.
5. Atacante 4: quem forja o campo de assinatura (nao ASCII, tamanho, formato) para derrubar o servidor ou escapar do registro.
6. Atacante 5: dispositivo ou cliente com credencial vazada; o dano e limitado por chave por empresa, token por dispositivo e rotacao.
7. Vazamento do banco: so ha hash SHA-256 de chaves e tokens; a chave de comando deriva de um segredo mestre fora do banco.
8. Falha operacional: equipamento novo ou sem classe nao pode virar desligavel por omissao (falha fechada).
9. Auditoria: todo pedido de comando deixa intencao e resultado; o rele so e acionado depois da intencao gravada.
10. Fora do escopo desta rodada: TLS, rate limiting, botao fisico, agendador de regras, JWT/OIDC, pen-test (ver ultima secao).

## Correcao por achado (camada + arquivo)

Caminhos relativos a `src/mapen_plataforma/`.

| # | Achado | Correcao | Camada e arquivo |
|---|---|---|---|
| 1 | Sem autenticacao | `Authorization: Bearer <chave>` por empresa; chave de `secrets.token_urlsafe(32)`, so o SHA-256 em `credencial_empresa`, comparacao com `hmac.compare_digest`. O `Principal` (empresa + nome) vem da chave; `autorizado_por` vem do principal em regras e desligamentos, e o corpo com esse campo e rejeitado (422). 401 sem dado do tenant. Bootstrap por CLI. Ingestao autentica por token de dispositivo (hash). Demo cria chaves proprias na partida | domain `domain/credenciais.py`; application `AutenticarEmpresa`, `AutenticarDispositivo`, `ProvisionarEmpresa`, `EmitirCredenciaisDispositivo` em `application/casos_de_uso.py`; infrastructure `CredenciaisEmpresaDuckDB`, `CredenciaisDispositivoDuckDB` em `infrastructure/repositorios.py`, `infrastructure/demo.py`; interface `interface/api/app.py` (dependencias `principal_empresa` e `principal_dispositivo`), `interface/cli.py` |
| 2 | `compare_digest` com texto nao ASCII dava 500 | Compara bytes; assinatura validada no esquema com `^[0-9a-f]{64}$` (422); se um valor ruim chegar ao caso de uso, vira rejeicao com evento | domain `domain/comando.py` (`assinatura_valida`, `PADRAO_ASSINATURA`); interface `interface/api/esquemas.py` |
| 3 | Comando valido por anos | `MAX_TTL` 60 s e tolerancia 5 s na politica; `emitido_em` entra na mensagem assinada; nonce guarda `expira_em = validade + tolerancia` e e podado a cada pedido | domain `domain/comando.py`; infrastructure `NonceDuckDB.podar`; application `SolicitarDesligamento` |
| 4 | Sem evento em varios caminhos | Intencao gravada primeiro, depois atuador, depois resultado; equipamento/regra desconhecidos, sonda entre empresas, comando malformado e falha do atuador tambem geram evento; se a intencao falhar, o atuador nao e chamado | application `SolicitarDesligamento` |
| 5 | Ids de sensor escolhidos pelo cliente | Id gerado no servidor (`uuid4`); `id` no corpo e rejeitado (`extra="forbid"`); sem existencia por colisao | application `Cadastro.criar_sensor`; interface `SensorIn` |
| 6 | Assinatura nao amarrava o que autoriza | JSON canonico (chaves ordenadas, sem espacos) de `{device_id, empresa_id, equipamento_id, acao, nonce, emitido_em, validade}`; empresa e equipamento vem da requisicao autenticada, nao do corpo. Ordem: dispositivo, assinatura, TTL, nonce, regra, critico, autorizacao, flag; falha de assinatura ou TTL nao queima o nonce | domain `mensagem_assinada`, `avaliar_comando` |
| 7 | Flag `critico` falhava aberto | Equipamento que nao casa com o YAML nasce `critico=true` (`ConfigEquipamentos.encontrar` devolve `None` sem casamento); `Equipamento.critico` nao tem padrao; a API exige `critico` na criacao | `mapen_aconselhamento/recomenda.py` (metodo novo, aditivo), `infrastructure/demo.py` (`critico_inicial`), `domain/entidades.py`, `interface/api/esquemas.py` |
| 8 | Flag so global; `regra_id` sem checagem | `desligamento_remoto_habilitado` por empresa na tabela `configuracao_empresa` (padrao falso), `GET/PUT /configuracao` (PUT grava `configuracao_alterada` com o principal, antes de mudar). `regra_id` precisa ser regra ativa do mesmo equipamento e empresa, senao `regra_invalida` com evento | application `ObterConfiguracao`, `AlterarConfiguracao`, `SolicitarDesligamento`; infrastructure `ConfiguracaoDuckDB` |
| 9 | Faltavam testes | Ver contagem abaixo | `tests/m2/` |
| 10 | Validacao fraca | `limite` 1..500, `n` 1..100, limites de tamanho (nome 120, nonce 128, origem 64, ids 128), lote de leituras maximo 5000, numeros nao finitos recusados, datas sem fuso recusadas em todo lugar (ver contrato). 422 nao ecoa o valor recebido (achado novo: um `NaN` no corpo derrubava o handler de erro com 500) | interface `esquemas.py`, `app.py` (handler de `RequestValidationError`); application (constantes e checagem de dominio dos limites) |
| 11 | `obter` filtrava em Python | `obter` de unidade, sensor, equipamento e regra com `WHERE empresa_id = ? AND id = ?` | infrastructure `repositorios.py` |
| 12 | Nonce sem atomicidade clara | `PRIMARY KEY (device_id, nonce)` + `INSERT ... ON CONFLICT DO NOTHING` com checagem do numero de linhas afetadas | `NonceDuckDB.registrar`, DDL em `infrastructure/banco.py` |
| 13 | Chave compartilhada de demo | Token de ingestao por dispositivo (hash). Chave de comando por dispositivo derivada de `HMAC(segredo mestre, device_id\|sal)`; so o sal fica no banco. Rotacao: `POST /sensores/{id}/credenciais` (novo token e novo sal; os antigos deixam de valer) | domain `derivar_chave_comando`; application `EmitirCredenciaisDispositivo`, `Cadastro.rotacionar_sensor`; infrastructure `DerivadorHmac`, `ChavesDerivadas` |
| + | `GET /consumo/horario` | Banco soma kWh por hora; o caso de uso converte para kW e pega a faixa por `CalculadoraCusto.faixas`, que chama a mesma `Tarifas.faixas` do custo (sem duplicar horarios). Periodo maximo de 31 dias | application `ConsumoHorario`; infrastructure `LeituraDuckDB.consumo_horario`, `CalculadoraM1.faixas` |

Decisoes que merecem olho:

- A retencao do nonce usa `validade + tolerancia` por linha, nao um corte fixo de TTL + tolerancia. Um corte fixo deixaria uma janela de replay (comando emitido ate 5 s no futuro continua aceito ate `emitido + 65 s`).
- Assinatura fora do padrao e recusada no esquema (422) e portanto nao gera evento; so valores ruins que passam do esquema geram evento. Se a auditoria precisar registrar tambem esses 422, falta um handler de validacao que grave evento.
- Fuso: a tabela `leitura` guarda hora local ingenua (como o M1). A API so aceita e devolve instantes com fuso; a conversao para `America/Recife` fica na infraestrutura (`domain/tempo.py` + repositorios), a aplicacao so ve instantes com fuso.
- A chave de comando do dispositivo precisa existir no servidor para verificar o HMAC, entao ela nao e "so hash". Ela nao e guardada: deriva de segredo mestre (env `MAPEN_SEGREDO_MESTRE`, fora do banco) e sal. Vazar so o banco nao permite forjar comando.

## Prova vermelha

Metodo: sem `git stash`. Antes de mexer no codigo, escrevi 14 sondas contra a API antiga (arquivo temporario fora do repositorio, usando o `ambiente.py` antigo) que afirmam o comportamento seguro. Resultado contra o codigo antigo: `13 failed, 1 passed`.

Vermelhas (13): header sozinho autentica (esperado 401), assinatura nao ASCII (500), validade de 3 anos aceita, equipamento desconhecido sem evento, `id` de sensor escolhido pelo cliente aceito, comando sem amarracao a equipamento, equipamento criado sem `critico` aceito, `/configuracao` inexistente, `regra_id` inexistente aceito, limites (`limite=0`, `limite=100000`, `n=100000`) aceitos, nome de 100000 caracteres aceito, nonce concorrente e `/consumo/horario` ausente.

A unica verde (datetime sem fuso na validade) ja era recusada (422); ficou como guarda de regressao.

Os testes finais dos mesmos achados foram escritos para a API nova e passam (abaixo). Nao rodei cada teste final contra o codigo antigo (eles nem importam: a API mudou), so as 14 sondas acima.

## Contagens reais

- `pytest -W error -q` (suite inteira, M1 + M2): 213 passed. Em `tests/m2`: 156 passed (antes: 46).
- `mypy` strict (`src/mapen_aconselhamento`, `src/mapen_plataforma`, `tests/m2`): `Success: no issues found in 40 source files`.
- `lint-imports`: `Contracts: 2 kept, 0 broken.`
- Verificacao ao vivo (uvicorn em background, banco de demo em copia temporaria, depois parado; `pgrep` sem processo uvicorn e porta livre): sem chave 401; chave errada 401 com `{"detail":"nao autenticado"}`; so `X-Empresa-Id` 401; chave valida em `/sensores` 200; `/configuracao` 200 (`false`); `/consumo/horario` 200 (CU-BEMS 2018-08-06 17h = 23,09 kW `intermediario`, 18h = 9,57 kW `ponta`); `POST /desligamentos` com assinatura errada 403 `assinatura_invalida` com evento; ingestao com token de dispositivo 200.

Arquivos de teste: `test_politica_comando.py` (32), `test_api_desligamento.py` (26), `test_autenticacao.py` (31), `test_nonce.py` (7), `test_validacao.py` (27), `test_consumo_horario.py` (9), `test_tenant.py` (11), `test_integracao_m2.py` (9), `test_contrato_camadas.py` (4), mais `ambiente.py`/`conftest.py`.

Cobertura do item 9: nonce apos reinicio com banco em arquivo (`test_nonce_sobrevive_ao_reinicio_com_banco_em_arquivo`), nonce concorrente por threads (repositorio e API), assinatura nao ASCII/malformada (dominio e esquema), horizonte de TTL e tolerancia, evento de equipamento desconhecido, spoofing de tenant com a chave de outra empresa, e a guarda do caminho feliz (`test_caminho_feliz_com_flag_ligada` e `test_guarda_adulterar_qualquer_campo_assinado_e_rejeitado`, que exigem o comando intacto aceito e cada campo adulterado recusado).

## O que NAO foi feito

1. TLS: a API fala HTTP puro; a chave vai em claro sem proxy TLS.
2. Rotacao de chave de empresa em producao: `ProvisionarEmpresa` substitui a chave do principal, mas nao ha endpoint, expiracao, nem revogacao por uso. Dispositivo tem rotacao (`/sensores/{id}/credenciais`).
3. Rate limiting e bloqueio por tentativas falhas.
4. Botao fisico e confirmacao local no rele.
5. Agendador de regras: a regra e so cadastro; nada dispara o desligamento sozinho.
6. JWT/OIDC, papeis por principal e mais de um principal por empresa via API (a CLI cria o principal `admin`).
7. Pen-test e revisao externa.
8. 422 de esquema (assinatura fora do padrao, campo extra) nao grava evento.
9. Migracao do banco antigo: o `ALTER TABLE nonce ADD COLUMN IF NOT EXISTS` cobre a coluna nova; nonces antigos sem `expira_em` nunca sao podados. Chaves antigas (`X-Empresa-Id`) deixam de existir; a demo reemite na partida.
10. Segredo mestre: sem `MAPEN_SEGREDO_MESTRE` a demo gera um aleatorio por processo (as chaves de comando impressas na partida valem so ate reiniciar).
11. Nao toquei em `dashboard/` (ainda manda `X-Empresa-Id`; ver contrato abaixo).

## Contrato novo da API (para atualizar o dashboard)

### Autenticacao

- Endpoints da empresa: `Authorization: Bearer <chave_api>`. O header `X-Empresa-Id` foi removido (e ignorado). Falha: `401 {"detail":"nao autenticado"}` com `WWW-Authenticate: Bearer`.
- Ingestao (`POST /sensores/{id}/leituras`): `Authorization: Bearer <token_dispositivo>` (a chave da empresa nao vale ai, e o token do dispositivo nao vale nos demais).
- Chave de demo: impressa no stdout na partida (`[demo] empresa=demo chave_api=...`) ou fixada por `MAPEN_CHAVE_API_DEMO` / `MAPEN_CHAVE_API_OUTRA` (minimo 32 caracteres). Nova empresa: `.venv/bin/python -m mapen_plataforma.interface.cli criar-empresa --nome "X" [--principal admin] [--db caminho]` (imprime `empresa_id` e `chave_api` uma vez). Variavel nova: `MAPEN_SEGREDO_MESTRE`. Variaveis removidas: `MAPEN_DESLIGAMENTO_REMOTO`, `MAPEN_CHAVE_DEMO`.
- Dashboard: trocar `MAPEN_EMPRESA_ID` por uma chave de API (por exemplo `MAPEN_API_KEY`) e mandar o header acima.

### Datas

Toda data de entrada e saida tem fuso (`2018-08-01T00:00:00-03:00`; `+` vai como `%2B` na query). Sem fuso: 422. Horas de instalacao sao `America/Recife`. `ts_referencia` e `hora` voltam com `-03:00`.

### Endpoints (todos exigem a chave de empresa, salvo a ingestao)

| Metodo e caminho | Entrada | Saida |
|---|---|---|
| `GET /unidades`, `POST /unidades` | `{"nome"}` (1..120) | `{id, nome}` |
| `GET /sensores` | | `[{id, unidade_id, nome}]` |
| `POST /sensores` | `{"unidade_id","nome"}` (sem `id`) | 201 `{id, unidade_id, nome, credenciais:{token_dispositivo, chave_comando}}` (segredos so aqui) |
| `POST /sensores/{id}/credenciais` | sem corpo | `{token_dispositivo, chave_comando}` novos; os antigos deixam de valer |
| `GET /equipamentos` | | `[{id, sensor_id, nome, critico}]` |
| `POST /equipamentos` | `{"sensor_id","nome","critico"}` (`critico` obrigatorio) | 201 equipamento |
| `GET /regras`, `POST /regras` | `{"equipamento_id","cron","ativo"?}` (sem `autorizado_por`) | regra; `autorizado_por` = nome do principal |
| `PATCH /regras/{id}` | `{"ativo"}` | `{"ativo"}` |
| `GET /configuracao`, `PUT /configuracao` | `{"desligamento_remoto_habilitado": bool}` | idem; o PUT grava evento `configuracao_alterada` |
| `POST /sensores/{id}/leituras` (token de dispositivo) | `{"leituras":[{equipamento, ts (com fuso), potencia_w?, tensao_v?, kwh?, ausente?}]}` ate 5000 | `{"gravadas": n}` |
| `GET /sensores/{id}/consumo-agora` | | como antes, `ts_referencia` com fuso |
| `GET /sensores/{id}/custo` | `inicio`, `fim` com fuso, `modalidade` | como antes |
| `GET /sensores/{id}/ranking` | `inicio`, `fim`, `modalidade`, `n` (1..100) | como antes |
| `GET /consumo/horario` | `sensor_id`, `inicio`, `fim` (ate 31 dias), `modalidade` (`branca` padrao ou `convencional`) | `[{"hora","kw","faixa"}]` (`faixa`: `ponta`, `intermediario`, `fora_ponta` ou `unico`); horas sem leitura nao aparecem |
| `GET /eventos` | `limite` (1..500, padrao 100) | eventos; tipos novos `comando_recebido` e `configuracao_alterada` |
| `POST /desligamentos` | ver abaixo | `{"aceito","motivo","evento_id"}` |

### `POST /desligamentos`

```json
{
  "equipamento_id": "...",
  "comando": {
    "device_id": "...", "acao": "desligar|ligar", "nonce": "1..128",
    "emitido_em": "2026-10-05T12:00:00+00:00", "validade": "2026-10-05T12:00:30+00:00",
    "assinatura": "64 hex minusculos"
  },
  "origem": "api", "regra_id": null
}
```

- Sem `autorizado_por` (422 se enviado): o autor e o nome do principal da chave.
- Assinatura: HMAC-SHA256 com a `chave_comando` do dispositivo (hex do retorno do provisionamento) sobre o JSON canonico (`sort_keys`, separadores `,` e `:`, ASCII) de `{device_id, empresa_id, equipamento_id, acao, nonce, emitido_em, validade}`, com `emitido_em` e `validade` em epoch segundos inteiros. `empresa_id` e o da chave; `equipamento_id` e o do corpo.
- `validade - emitido_em` <= 60 s; `emitido_em` ate 5 s no futuro; `validade` ate 5 s no passado.
- Status: 200 aceito; 404 `equipamento_desconhecido`; 403 qualquer outro motivo. Motivos: `comando_malformado`, `dispositivo_divergente`, `assinatura_invalida`, `ttl_excessivo`, `emissao_futura`, `validade_vencida`, `nonce_repetido`, `regra_invalida`, `equipamento_critico`, `sem_autorizacao`, `desligamento_remoto_desabilitado`, `falha_atuador`.
- Cada pedido gera dois eventos: `comando_recebido` (intencao) e o resultado (`desligamento_executado`, `religamento_executado`, `comando_rejeitado` ou `falha_conexao`), ligados por `payload.intencao_id`.

## Contrato M3

Camada nova em `mapen_plataforma`: `domain/resultados_m3.py` (tipos, filtro, veredito, aviso D7), `application/resultados_m3.py` (`ConsultarResumoM3`, `ListarAlertasM3`, `ConsultarEconomiaM3`) e a porta `ResultadosM3Repositorio` em `application/portas.py`, `infrastructure/resultados_m3_json.py` (adaptador sobre `data/m3/*.json`), `interface/api/{app,esquemas,composicao}.py`. Import-linter: 9 contratos mantidos. Todos os numeros abaixo vem de chamadas reais a uma API em background com a chave de demo.

### Regras comuns

- Autenticacao: `Authorization: Bearer <chave_api>`; sem chave ou chave errada: `401`.
- Tenant: os artefatos do M3 sao da empresa demo (`EMPRESA_DEMO`). Outra empresa recebe `200` com `"disponivel": false` e listas vazias, nunca o dado da demo, e nunca `503` (nao revela se o artefato existe).
- Artefatos: `MAPEN_M3_DIR` (padrao `data/m3`) com `resumo.json`, `alertas.json`, `economia.json` (nomes fixos, nunca vem da requisicao; link simbolico que escapa do diretorio e recusado). Esquema estrito (campo extra, tipo errado, NaN, `versao_esquema != 1`, `natureza` diferente de `validacao_de_metodo_sintetica`, `top_shap` em alerta z-score ou ausente em alerta LightGBM): recusa o arquivo inteiro. Artefato ausente, ilegivel ou invalido para a empresa dona: `503 {"detail": "resultados do M3 indisponiveis: artefato alertas.json ausente"}` (so o nome do arquivo, nunca caminho nem conteudo).
- Datas: instantes com fuso, como no resto da API (`2018-11-05T17:00:00-03:00`). Os artefatos guardam hora local ingenua; o adaptador converte para `America/Recife`.
- Somente leitura: `POST` nessas rotas e `405`.

### `GET /modelos/resumo`

Sem parametros. Campos: `disponivel`, `rotulo`, `sensor_id`, `dados` (fonte, periodo, treino, reservado, `equipamentos_no_andar`, `equipamentos_modelados`, `equipamentos_sem_carga`, `linhas_minuto`), `mae` (`baseline_sazonal_kw`, `lightgbm_kw`, `horas_teste`, `melhora_mediana_pct`, `equipamentos_total`, `equipamentos_lightgbm_melhor`, `ressalva_nowcast`, `por_equipamento[]`), `shap` (`calendario_pct`, `historico_pct`, `por_feature[]`, `por_equipamento[]`, `aviso_d7`), `benchmark_sintetico` (`sintetico: true`, `rotulo` "SINTETICO...", `detectores[]` com taxas por tipo, total e falso alarme) e `baseline_fraca` (`criterio`, `semanas_completas_treino`, `equipamentos[]`). `aviso_d7.disparado` e derivado: a maior feature agregada passa do limiar (50%). `baseline_fraca.equipamentos` e a uniao dos marcados em `economia.json` e `alertas.json`.

Resposta real (abreviada):

```json
{"disponivel": true, "sensor_id": "cu_bems_2018Floor2",
 "dados": {"equipamentos_no_andar": 24, "equipamentos_modelados": 19, "linhas_minuto": 5322240,
           "equipamentos_sem_carga": ["z2_AC11","z2_AC12","z2_AC13","z2_AC14","z4_Plug"]},
 "mae": {"baseline_sazonal_kw": 0.6113, "lightgbm_kw": 0.2051, "horas_teste": 31763,
         "melhora_mediana_pct": 67.6, "equipamentos_total": 19, "equipamentos_lightgbm_melhor": 19},
 "shap": {"calendario_pct": 14.9, "historico_pct": 85.1,
          "aviso_d7": {"disparado": true, "feature": "kw_lag1", "pct": 59.5, "limiar_pct": 50.0,
                       "equipamentos_com_dominante": 12}},
 "benchmark_sintetico": {"sintetico": true, "detectores": [{"detector": "zscore", "total_detectados": 84,
                         "total_eventos": 114, "falso_alarme_horas": 114, "horas_base": 9145}]},
 "baseline_fraca": {"semanas_completas_treino": 18, "equipamentos": []}}
```

### `GET /alertas`

Query: `equipamento` (1..128), `tipo` (`zscore` ou `lightgbm`), `de` (inclusivo) e `ate` (exclusivo) com fuso (`+` vai como `%2B`; `de >= ate` e `422`), `limite` 1..500 (padrao 100), `offset` >= 0. Ordem estavel: instante, equipamento, tipo. Resposta: `disponivel`, `rotulo`, `aviso`, `limiar_z`, `periodo`, `total` (apos filtros), `limite`, `offset`, `proximo_offset` (`null` na ultima pagina), `itens[]`. Cada item: `equipamento`, `timestamp`, `tipo`, `rotulo` = `"candidato, nao corroborado"`, `baseline_fraca` e `explicacao` (`z`, `esperado_kw`, `observado_kw`, `janela_baseline`, `top_shap` = 3 features no LightGBM, `null` no z-score).

`GET /alertas?limite=2&tipo=lightgbm&equipamento=z1_Light&de=2018-11-05T00:00:00%2B00:00` (real, total 21):

```json
{"disponivel": true, "rotulo": "candidato, nao corroborado", "limiar_z": 4.0, "total": 21, "limite": 2,
 "offset": 0, "proximo_offset": 2,
 "itens": [{"equipamento": "z1_Light", "timestamp": "2018-11-05T17:00:00-03:00", "tipo": "lightgbm",
            "rotulo": "candidato, nao corroborado", "baseline_fraca": false,
            "explicacao": {"z": -6.146339582931916, "esperado_kw": 7.274438967263248,
                           "observado_kw": 3.379166666666665,
                           "janela_baseline": {"inicio": "2018-07-01T00:00:00-03:00", "fim": "2018-11-04T00:00:00-03:00"},
                           "top_shap": [{"feature": "kw_lag1", "shap": 3.9836835668818145},
                                        {"feature": "dia_semana", "shap": 0.33049464292685427},
                                        {"feature": "hora", "shap": -0.1250357914626631}]}}]}
```

(Sem filtros: 182 alertas, 128 z-score e 54 LightGBM, depois da troca do baseline do z-score por seasonal-naive-168; eram 214, 160 e 54.)

### `GET /economia`

Sem parametros. Sempre `valida_metodo_nao_economia_real: true`: reducao sintetica conhecida em dado real, nao e economia real. Campos: `disponivel`, `natureza`, `aviso`, `periodo_antes`, `periodo_depois`, `reducao_sintetica` (`equipamento`, `fracao_pct`, `a_partir_de`) e `metodos[]`, um item por metodo de antes x depois que o `economia.json` traz: `baseline_normalizado` (sempre) e `diferenca_em_diferencas_grupo_controle` (so se o M3 gravou os campos de controle; o esquema recusa o metodo pela metade). Cada item tem `metodo`, `rotulo`, `veredito` e `equipamentos[]` (`equipamento`, `injetado_pct`, `recuperado_pct`, `erro_pp`, `tolerancia_pp`, `dentro_da_tolerancia`, `economia_pct_sem_reducao`, `baseline_fraca`, `controles`, vazio no baseline). `dentro_da_tolerancia` = `|recuperado - injetado| <= tolerancia_pp` (recuperado ausente conta como fora). O veredito e calculado a cada chamada para cada metodo com a mesma regra: `tolerancia_atendida` so e verdadeiro se o alvo e todos os equipamentos estao dentro; `erro_abs_mediano_pp`/`erro_abs_maximo_pp` vem da mesma lista; `texto` e montado com esses numeros. Mudou em 2026-10-02: `veredito` e `equipamentos[]` deixaram de ser campos do topo e passaram a viver dentro de `metodos[]` (unico consumidor, o dashboard, foi migrado junto).

Resposta real (resumo dos dois metodos, dados de 2026-10-02):

| Metodo | Dentro da tolerancia | Alvo z1_Light (injetado 15,0%) | Erro abs. mediano / maximo |
|---|---|---|---|
| `baseline_normalizado` | 7 de 19 | 27,18% (fora) | 6,71 / 18,90 pp |
| `diferenca_em_diferencas_grupo_controle` | 12 de 19 | 17,1% (dentro) | 1,9 / 13,1 pp |

Nenhum dos dois atende a tolerancia de +-3,0 pp em todos os equipamentos (`tolerancia_atendida: false` nos dois).

### `GET /modelos/previsao`

Sem parametros. Le `previsao.json` (estudo de previsao do dia seguinte do M3, ver `docs/m3_notas.md`) com a mesma autenticacao, tenant e esquema estrito dos outros artefatos; arquivo ausente ou fora do esquema = 503 so com o nome do arquivo, e a falha dele nao derruba `/modelos/resumo`, `/alertas` nem `/economia` (sao artefatos independentes). Campos: `disponivel`, `rotulo`, `sensor_id`, `aviso`, `horizonte_h`, `defasagem_minima_h`, `treino`, `reservado`, `dobras_walk_forward`, `referencia_mase`, `equipamentos`, `sem_carga`, `modelos[]` (`modelo`, `adotado`, `mae_agregado_kw`, `mediana_mase_reservado`, `mediana_mase_desenvolvimento`, `vitorias_vs_naive168`, `vitorias_melhor_de_todos`), `decisao` (`regra_aplicada`, `adotado`, `passaram_regra_de_ganho`, `melhor_mediana`, `motivo`; a regra foi pre-registrada e aplicada pelo M3, a API nao a recalcula), `mase_por_equipamento[]`, `shap_lightgbm` (`por_grupo_pct`, `por_feature_pct`, `feature_dominante`, `equipamentos_com_feature_dominante`, `horas`), `benchmark_sintetico` (sempre `sintetico: true`, taxas em %) e `avisos`. O esquema recusa modelo desconhecido na decisao, tabelas com conjuntos de modelos diferentes e MASE que nao cobre todos os equipamentos. Dado real: adotado `seasonal_naive_168` (mediana de MASE 0,5089), nenhum candidato passou a regra de ganho, baseline sazonal estatico em 1,7505.

### Limites desta rodada

1. `resumo.json` nao e gerado pelo CLI do M3 (so `alertas.json`, `economia.json` e o relatorio em markdown). Foi gerado uma vez a partir das tabelas de `data/m3/relatorio_m3.md` por um script descartavel; o proximo `mapen_modelos.interface.cli` nao o recria nem o atualiza. Falta um emissor de `resumo.json` em `mapen_modelos/interface/artefatos_json.py` (o M3 ficou intocado). Se as metricas mudarem e o `resumo.json` nao, a API mostra o numero velho.
2. Nenhum cache: cada requisicao le e valida os JSON (80 KB de alertas).
3. `dashboard/` nao foi alterado.
4. Os testes novos (`tests/m2/test_resultados_m3.py`, 48) nao foram vistos vermelhos contra uma implementacao quebrada.
