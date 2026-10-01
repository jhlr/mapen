# Dashboard: atualização para a API autenticada (2026-10-01)

Todos os números abaixo vêm de execuções reais nesta sessão: API (uvicorn) sobre uma cópia do banco M1 em diretório temporário, dashboard em `npm run build && npm run start`, navegador Playwright. Servidores parados no fim (`pgrep` sem uvicorn nem next). As notas da primeira versão estão mais abaixo, em "Histórico"; onde conflitam com esta seção, vale esta.

## Como rodar (demo)

1. API, na raiz do repositório, com chaves fixas para a demo (mínimo 32 caracteres cada):
   `MAPEN_CHAVE_API_DEMO=<chave-demo> MAPEN_CHAVE_API_OUTRA=<outra-chave> .venv/bin/python -m uvicorn --factory mapen_plataforma.interface.api.composicao:criar_app_padrao --port 8000`
   Sem essas variáveis a API gera chaves novas a cada partida e as imprime uma vez no stdout (`[demo] empresa=demo chave_api=...`). Outra empresa: `.venv/bin/python -m mapen_plataforma.interface.cli criar-empresa --nome "X"`.
2. Dashboard, em `dashboard/`: `MAPEN_API_KEY=<chave-demo> npm run build && MAPEN_API_KEY=<chave-demo> npm run start` (ou `dashboard/.env.local` com `MAPEN_API_KEY=...`). `MAPEN_API_URL` (padrão `http://127.0.0.1:8000`) é opcional.
3. A chave é variável só do servidor (sem `NEXT_PUBLIC_`). `lib/api/cliente.ts` importa `server-only`, então o build quebra se um componente de cliente o importar. O bundle estático não contém a chave (grep em `.next/static` sem resultado).

## O que mudou

1. Autenticação: `requisitar`/`ler` mandam `Authorization: Bearer $MAPEN_API_KEY`. `X-Empresa-Id` e o parâmetro `?empresa=` saíram de tudo (a empresa é a da chave). 401 (chave recusada ou `MAPEN_API_KEY` ausente) chama `unauthorized()` do Next (flag experimental `authInterrupts` em `next.config.ts`) e renderiza `app/unauthorized.tsx` com as instruções. Nas Server Actions o 401 vira mensagem no formulário.
2. Datas com fuso: novo `lib/dominio/fuso.ts` (America/Recife via `Intl`, sem offset fixo no código). Consultas de custo, ranking e horário mandam `...-03:00`, com `encodeURIComponent` (o `+` de outros offsets vira `%2B`). Os campos do desligamento (`emitido_em`, `validade`) são horário de Recife e a action converte com offset. `dataHora` converte qualquer ISO com fuso para Recife.
3. Página Por hora: uma chamada a `GET /consumo/horario` (antes 24 por dia). Períodos de 1, 3, 7 e 31 dias (máximo da API). Mantidos o sombreado de faixas e a média por hora do dia. Horas sem leitura: 0 kW no gráfico hora a hora, fora da média por hora do dia, contadas no aviso da página.
4. Desligamento: o banner lê `GET /configuracao` (a inferência por eventos foi removida). Novo controle `ControleRemoto` com `PUT /configuracao` em duas etapas (botão abre uma confirmação que explica o efeito e o evento `configuracao_alterada`; Cancelar volta). Formulário de desligamento sem `autorizado_por`, com `emitido_em` e a mensagem canônica a assinar. Formulário de regra sem `autorizado_por` (a API usa o nome do principal). Equipamento sempre envia `critico` explícito. O dashboard não cria sensor, então nada envia id de sensor. Eventos mostram `comando_recebido` e `configuracao_alterada`; motivos novos explicados.
5. Responsivo: sem largura máxima no `main` (padding fluido), `body` com `min-height: 100dvh`. Navegação vira botão "Menu" abaixo de 900 px. Alvos de toque de 44 px (medido: 44 nos itens e no botão da navegação). Formulários em grade de 1 coluna no celular e várias colunas em tela larga. Tabelas de eventos, regras, equipamentos e ranking viram cartões a 600 px ou menos (`data-label`); as demais rolam dentro do próprio contêiner. Gráficos SVG medem o contêiner com `ResizeObserver` (sem largura fixa; rótulos do eixo X escolhem o passo conforme a largura).
6. Contraste das faixas: texto dos gráficos usa `--texto` (antes `--suave`). Escuro: faixas `#17402a` / `#5a4510` / `#7a2b30`, texto `#e6eaf0` sobre elas com razão 9,6 / 5,9 / 7,9 (calculado por WCAG; mínimo exigido 4,5). A faixa ponta tem hachura (também na legenda), então a distinção não depende só da cor. Claro: texto `#1c2430` sobre as faixas com 12,1 / 12,4 / 9,3.

## Rolagem horizontal da página: `scrollWidth / innerWidth`

Medido em cada uma das 7 rotas (`/`, `/horario`, `/custo`, `/ranking`, `/cadastro`, `/desligamento`, `/eventos`), claro e escuro, banco com dados reais:

| Largura | Resultado (14 medições por largura) |
|---|---|
| 375 | 375/375 em todas, claro e escuro |
| 768 | 768/768 em todas, claro e escuro |
| 1280 | 1280/1280 em todas, claro e escuro |

Nenhuma medição com `scrollWidth > innerWidth`. Screenshots conferidos a olho: Por hora (375 e 1280 escuro), Cadastro (375 claro), Desligamento (768 escuro), Eventos (375 escuro, após corrigir texto longo cortado dentro dos cartões empilhados).

## Formulários verificados contra a API ao vivo (empresa demo)

1. Criar equipamento normal (`z9_Teste`, `critico` desmarcado): HTTP 201, `critico = não`.
2. Criar equipamento crítico (`z9_Servidor`): HTTP 201, `critico = sim`.
3. Criar regra `0 22 * * 1-5` para `z9_Teste`: HTTP 201, ativa, autorizada por `admin` (nome do principal).
4. Desligar `z9_Teste` com flag desligada: HTTP 403 `desligamento_remoto_desabilitado`; banner "Modo só recomendação".
5. Alternar a flag: confirmação aparece, Cancelar volta sem chamar a API; Confirmar: HTTP 200, banner passa a "habilitado".
6. Desligar `z9_Servidor` com flag ligada: HTTP 403 `equipamento_critico`.
7. Desligar `z9_Teste` com flag ligada: HTTP 200 `aceito true`.
8. Flag desligada de novo; Eventos listou `configuracao_alterada` (true e false, autor `admin`), `comando_recebido` e os resultados.
9. 401: dashboard iniciado com chave errada e sem `MAPEN_API_KEY` mostra a tela "Chave de API ausente ou recusada".

A assinatura HMAC foi calculada no navegador de teste com a chave de comando impressa pela API (o dashboard não a tem).

## Limites conhecidos

1. A tela 401 sai com HTTP 200: o `loading.tsx` já enviou o cabeçalho antes de a leitura falhar (a tela correta aparece, o status não). Não verificado com `curl -I` fora do streaming.
2. `authInterrupts` é experimental no Next 16.3.8.
3. O comando assinado precisa ser assinado por fora em até 60 s (emissão e validade); não existe emissor de comandos, então o fluxo manual é desconfortável na prática.
4. A mensagem a assinar mostra `empresa_id` como `<empresa da chave>`: a API não expõe o id da empresa da chave.
5. Sem trocar de empresa na interface (uma chave, uma empresa; trocar exige reiniciar com outra `MAPEN_API_KEY`). Sem formulário de sensor.
6. Horas sem leitura aparecem como 0 kW no gráfico hora a hora (sem lacuna); a faixa delas vem da faixa típica daquela hora do dia nos pontos da API, só para sombrear.
7. Nem todos os 12 motivos de rejeição foram exercitados no navegador (só `desligamento_remoto_desabilitado`, `equipamento_critico` e aceito).
8. `error.tsx` ainda mostra só o código `digest` (Next oculta o erro de servidor em produção).
9. Testado só em Chromium (Playwright); sem teste em celular real e sem testes automatizados do dashboard.
10. `/custo` e `/ranking` levam cerca de 1,7 s por página (medido com curl).

## Histórico (primeira versão)

Mapa de camadas e decisões de design da primeira versão continuam valendo: pages só compõem; `lib/api/cliente.ts` é o único `fetch`; `lib/dominio` tem funções puras; Server Actions chamam `lib/api`. O serviço `lib/servicos/serieHoraria.ts` agora faz uma só chamada. Itens antigos obsoletos: inferência do modo remoto por eventos, `X-Empresa-Id`, `?empresa=`, 24 consultas por dia, largura mínima de 560 px nos gráficos, contraste baixo no escuro.
