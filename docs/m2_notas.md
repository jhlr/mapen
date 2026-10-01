# M2 notas de implementacao (2026-10-01)

Pacote `src/mapen_plataforma/` (API e regras de seguranca do canal de comando) e `dashboard/` (Next.js). Todos os numeros abaixo vem de execucoes reais nesta sessao. Sem hardware: nao ha MQTT nem firmware, so a porta de ingestao e adaptadores de demo.

## Mapa de camadas

As dependencias apontam so para dentro: interface > infrastructure > application > domain.

| Camada | Arquivo | Conteudo |
|---|---|---|
| domain | `domain/entidades.py` | Empresa, Unidade, Sensor, Equipamento (`critico`), Leitura, RegraDesligamento, Evento, TipoEvento |
| domain | `domain/comando.py` | ComandoRele, assinatura HMAC-SHA256 sobre (device_id, acao, nonce, validade), `avaliar_comando`, `ConfiguracaoSeguranca` (flag `desligamento_remoto_habilitado`, padrao falso), estado inicial do rele (energizado) |
| application | `application/portas.py` | Portas (Protocol): repositorios, NonceStore, ChavesDispositivo, Atuador, Relogio, GeradorId, LeituraRepo (ingestao), CalculadoraCusto |
| application | `application/casos_de_uso.py` | RegistrarLeitura, ConsumoAgoraEHoje, ListarConsumoECusto, RankingEquipamentos, CriarRegraDesligamento, AlterarRegra, ListarRegras, SolicitarDesligamento, ListarEventos, Cadastro |
| infrastructure | `infrastructure/banco.py` | Conexao DuckDB com trava e DDL (`leitura` reusa o DDL do M1, mais `evento`, `regra_desligamento`, `sensor`, `equipamento`, `unidade`, `empresa`, `nonce`) |
| infrastructure | `infrastructure/repositorios.py` | Repositorios DuckDB, NonceDuckDB, LeituraDuckDB (ingestao sem duplicar) |
| infrastructure | `infrastructure/custo_m1.py` | Adaptador que chama `mapen_aconselhamento` (custo_por_faixa, top_n, ler_leituras); nao duplica logica |
| infrastructure | `infrastructure/servicos.py` | RelogioSistema, RelogioFixo, geradores de id, ChavesEmMemoria, AtuadorSimulado |
| infrastructure | `infrastructure/demo.py` | Semente: empresa `demo` (CU-BEMS, 24 equipamentos) e `outra` (BDG2), `critico` lido do YAML do M1 |
| interface | `interface/api/app.py`, `esquemas.py` | Controladores FastAPI finos e esquemas JSON |
| interface | `interface/api/composicao.py` | Raiz de composicao (liga adaptadores aos casos de uso) |
| interface | `dashboard/` | Next.js App Router, TypeScript strict, 5 telas lendo so a API |

## Como rodar

API (copia `data/mapen_m1.duckdb` para `data/mapen_m2.duckdb` na primeira execucao e semeia o demo):

    .venv/bin/uvicorn mapen_plataforma.interface.api.composicao:criar_app_padrao --factory --port 8000

Variaveis: `MAPEN_DB` (caminho do banco), `MAPEN_DESLIGAMENTO_REMOTO=1` (liga o desligamento; padrao desligado), `MAPEN_CHAVE_DEMO` (chave HMAC dos sensores de demo; sem ela todo comando e rejeitado).

Dashboard (a API deve estar no ar):

    cd dashboard && npm install && npm run build && npm run start   # ou npm run dev

Variaveis: `MAPEN_API_URL` (padrao http://127.0.0.1:8000), `MAPEN_EMPRESA_ID` (padrao `demo`); `?empresa=outra` na URL troca de empresa. Telas: `/` consumo agora e hoje, `/custo`, `/ranking`, `/cadastro`, `/eventos`.

ATENCAO: este arquivo descreve o M2 original. O header `X-Empresa-Id` foi substituido por `Authorization: Bearer` e o contrato mudou; ver `docs/m2_seguranca_notas.md`.

API (versao original, todas exigiam o header `X-Empresa-Id`): `GET/POST /unidades`, `/sensores`, `/equipamentos`, `/regras`; `PATCH /regras/{id}`; `POST /sensores/{id}/leituras`; `GET /sensores/{id}/consumo-agora`, `/custo`, `/ranking`; `POST /desligamentos`; `GET /eventos`.

## Resultados

- pytest: tests/m2 = 46 passed; suite inteira (M1 + M2) = 103 passed, com `-W error`.
- mypy strict (`src/mapen_aconselhamento`, `src/mapen_plataforma`, `tests/m2`): `Success: no issues found in 33 source files`.
- `npm run build` (Next 16.3.8, TypeScript 7.0.2): compilou e passou o type-check; rotas `/`, `/cadastro`, `/custo`, `/eventos`, `/ranking` dinamicas.
- Render com a API no ar e o CU-BEMS de demo: as 5 paginas e `/?empresa=outra` responderam HTTP 200 com dado (ranking: z1_AC1 R$ 5.823,74 e 7.142,7 kWh em 2018-08). `/custo` e `/ranking` levam cerca de 1,7 s (leitura do mes inteiro a 1 min). Sem screenshots.
- O teste de integracao com o CU-BEMS reproduz o custo convencional do relatorio do M1 (R$ 17725.21, tolerancia de 1 centavo) pela API.

## Prova vermelha do contrato de camadas (import-linter)

Contratos em `pyproject.toml`: `layers` (interface > infrastructure > application > domain) e `forbidden` (domain e application sem fastapi, starlette, pydantic, duckdb, pandas, numpy, httpx nem mapen_aconselhamento). Executados no pytest por `tests/m2/test_contrato_camadas.py`, que tambem gera pacotes minimos violadores num tmp e exige falha (2 casos vermelhos, 1 verde).

Prova no pacote real: copia de `src/mapen_plataforma` para um diretorio temporario fora do repositorio, sem git, com `domain/violador.py` contendo `import duckdb` e `from mapen_plataforma.infrastructure.banco import BancoDuckDB`. A copia sem o violador deu `Contracts: 2 kept, 0 broken.` Com o violador:

```

Contracts
---------

Analyzed 40 files, 86 dependencies.
-----------------------------------

Camadas: interface > infrastructure > application > domain BROKEN
Dominio e aplicacao sem I/O nem framework BROKEN

Contracts: 0 kept, 2 broken.


----------------
Broken contracts
----------------

Camadas: interface > infrastructure > application > domain
----------------------------------------------------------

mapen_plataforma.domain is not allowed to import 
mapen_plataforma.infrastructure:

- mapen_plataforma.domain.violador -> mapen_plataforma.infrastructure.banco 
(l.2)


Dominio e aplicacao sem I/O nem framework
-----------------------------------------

mapen_plataforma.domain is not allowed to import duckdb:

-   mapen_plataforma.domain.violador -> duckdb (l.1)

-   mapen_plataforma.domain.violador -> mapen_plataforma.infrastructure.banco 
(l.2)
    mapen_plataforma.infrastructure.banco -> duckdb (l.9)


mapen_plataforma.domain is not allowed to import mapen_aconselhamento:

-   mapen_plataforma.domain.violador -> mapen_plataforma.infrastructure.banco 
(l.2)
    mapen_plataforma.infrastructure.banco -> mapen_aconselhamento (l.11)
```

## O que NAO foi feito

1. MQTT e firmware (so a porta `LeituraRepo` e o adaptador DuckDB; o teste de integracao broker -> ingestao do spec nao existe).
2. Chaves reais por dispositivo: so `ChavesEmMemoria` (provisionamento, rotacao e armazenamento seguro faltam).
3. Autenticacao alem do header `X-Empresa-Id`: qualquer cliente que o conheca age como a empresa. Nao ha papel, usuario nem token.
4. Pen-test e revisao de seguranca externa.
5. TLS, botao fisico local sobrepondo comando remoto e deteccao de queda: dependem do hardware.
6. O `AtuadorSimulado` guarda estado so em memoria; nao ha acionamento real de rele. A regra de desligamento (cron) e cadastrada mas nenhum agendador a executa.
7. Quem assina o comando: a API so verifica comando ja assinado; o emissor (agendador de regras) nao existe, e o dashboard nao tem formulario de desligamento.
8. Retencao, acesso por papel e apagamento sob pedido (criterio 6c do spec).
9. Dashboard sem formularios de cadastro (so leitura); nao foi testado em navegador.
10. `consumo-agora` usa a ultima leitura do sensor e o dia dela (dado de demo e historico).
11. Fuso: leituras sao timestamps ingenuos (como no M1); eventos e comandos usam UTC.
