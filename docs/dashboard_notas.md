# Dashboard: notas de implementação (2026-10-01)

Tudo abaixo vem de execuções reais nesta sessão: API (uvicorn) com uma cópia do banco M2 (`MAPEN_DB` em diretório temporário, para não sujar `data/mapen_m2.duckdb`) e `MAPEN_CHAVE_DEMO` definida, dashboard em `npm run build && npm run start`, navegador Playwright e painel de navegador do app.

## Mapa de camadas de `dashboard/`

Dependências só para baixo: pages > components/actions > lib/servicos > lib/api, lib/dominio. Nenhum `fetch` fora de `lib/api/cliente.ts` (verificado por grep).

| Camada | Arquivos | Papel |
|---|---|---|
| Cliente da API | `lib/api/cliente.ts` | único `fetch`; `requisitar` (devolve `Resposta<T>` sem lançar por status HTTP) e `ler` (lança, cai no `error.tsx`) |
| | `lib/api/tipos.ts` | contratos JSON (espelham `esquemas.py`) |
| | `lib/api/leituras.ts`, `lib/api/comandos.ts` | funções tipadas por endpoint (GET e POST/PATCH); `index.ts` reexporta |
| Serviço | `lib/servicos/serieHoraria.ts` | orquestra N consultas de `/custo` em janelas de 1 h (ver "Limites") |
| View-model | `lib/dominio/formatacao.ts` | R$, kWh, W, %, datas, tudo em pt-BR (vírgula decimal, ponto de milhar) |
| | `lib/dominio/periodo.ts`, `agregacao.ts`, `serie.ts`, `seguranca.ts`, `parametros.ts` | funções puras: mês de referência, agrupar por faixa, janelas/médias horárias e trechos de faixa, motivos de rejeição e inferência do modo remoto, parsing de query string |
| Contexto | `lib/contexto.ts` | resolve empresa, sensor e modalidade da URL |
| Ações | `actions/cadastro.ts`, `actions/desligamento.ts`, `actions/estado.ts` | Server Actions: recebem o `FormData`, chamam `lib/api`, devolvem estado tipado e revalidam |
| Componentes | `components/Basicos.tsx` (Cabecalho, Aviso, Cartao, Barra, Tabela, Vazio, Secao), `Seletores.tsx`, `Graficos.tsx` (SVG sem biblioteca), `Navegacao.tsx`, `Campo.tsx`, `FormEquipamento.tsx`, `FormRegra.tsx`, `AlternarRegra.tsx`, `PainelDesligamento.tsx` | UI |
| Páginas | `app/page.tsx`, `horario/`, `custo/`, `ranking/`, `cadastro/`, `desligamento/`, `eventos/`, `loading.tsx`, `error.tsx` | só compõem componentes e chamam `lib/api`/`lib/servicos` |

Os formulários chamam Server Actions, não a API direto do navegador: a API não precisa de CORS e `MAPEN_API_URL` fica só no servidor. Sem dependência nova (só next, react, react-dom).

## O que mudou visualmente

1. Tokens de cor e escala tipográfica (0,8125 / 0,9375 / 1,125 / 1,5 rem); tema claro e escuro via `prefers-color-scheme`; sem emoji nem gradiente.
2. Navegação com item ativo, preservando `?empresa=`; nova rota `/horario` (Por hora) e `/desligamento`.
3. Tabelas com legenda, números alinhados à direita, rolagem horizontal contida; barras com trilho. No celular a coluna de barras some.
4. Formatação pt-BR: `R$ 5.823,74`, `7.142,7 kWh`, `5.280 W`, datas `31/08/2018 23:59`, mês por extenso. Textos com acentuação.
5. Estados: carregando (`loading.tsx`), erro (`error.tsx`, ex.: empresa desconhecida), vazio (por tela), aviso de dado de demonstração.
6. Layout: `html` e `body` com fundo e `min-height: 100dvh`, `main` fluido com `max-width: 1200px` centralizado. O limite de ~1100x940 visto no screenshot do dono veio do viewport que eu tinha fixado no Playwright (1100x800); o CSS antigo só limitava o `main` a 960 px. No painel do app, após `resize_window preset desktop`, o fundo preenche todo o painel (claro e escuro). Viewport deixado em "desktop".
7. Gráficos de consumo por hora em SVG: média de kW por hora do dia (24 barras) e série kW hora a hora no período (1, 3 ou 7 dias), com a faixa tarifária sombreada ao fundo (fora de ponta, intermediária, ponta) e legenda.

## Formulários: comportamento verificado

Banco de teste, empresa `demo`. Respostas literais da API:

1. Criar equipamento `z9_Servidor`, sensor `cu_bems_2018Floor2`, `critico` marcado: HTTP 201, `crítico = sim`; aparece na tabela (coluna Crítico em vermelho). O texto do formulário explica que a API recusa qualquer desligamento remoto de equipamento crítico.
2. Criar regra com `autorizado_por` só de espaços: HTTP 422 `regra exige autorizado_por`; o formulário manteve todos os campos digitados.
3. Criar regra `0 22 * * 1-5` para z1_AC1, autorizada por `dra.maria@empresa.com`: HTTP 201, regra ativa na tabela.
4. Desativar a regra (PATCH): HTTP 200, estado "inativa", botão vira "Ativar".
5. Desligamento (comando assinado por mim com a chave de teste, em Python, via `assinar` do domínio; o dashboard não tem a chave):
   - desligar z1_AC1, assinatura válida, autorizado: HTTP 403 `aceito false`, `motivo desligamento_remoto_desabilitado`; a página passou a mostrar o banner "Modo só recomendação: desligamento remoto desativado".
   - desligar z9_Servidor (crítico): HTTP 403 `equipamento_critico`.
   - ligar z1_AC1, assinatura válida: HTTP 200 `aceito true` (religar não depende da flag).
   - assinatura `deadbeef`: HTTP 403 `assinatura_invalida`; nonce e assinatura digitados ficam no formulário.
   - A página Eventos listou as quatro tentativas (rejeições em vermelho, com motivo e autorizador).
   - Não testado no navegador: `sem_autorizacao`, `nonce_repetido`, `validade_vencida`, `dispositivo_divergente` (o campo device_id é somente leitura) e desligamento aceito com a flag ligada (a API foi iniciada sem `MAPEN_DESLIGAMENTO_REMOTO=1`).

Achado e correção: o React 19 limpa os campos não controlados depois de qualquer Server Action; na primeira versão, um erro da API apagava o que o usuário digitou. As ações agora devolvem os valores enviados quando a API recusa e os formulários os usam como `defaultValue`. No painel de desligamento, o nonce é regerado após resposta que o consome (aceito ou rejeição de negócio) e a assinatura é limpa; em `assinatura_invalida`, `validade_vencida` e `dispositivo_divergente` o nonce é mantido.

Responsivo e tema: telas conferidas em 1280, 768 e 375 px, claro e escuro (Por hora, Desligamento, Eventos, erro); sem rolagem horizontal da página (`scrollWidth` = largura da janela em todas as 7 rotas a 768 px). Build: `npm run build` compilou, passou o TypeScript strict, 7 rotas dinâmicas, as 7 páginas e `/?empresa=outra` responderam 200.

## Endpoints que faltam (não adicionados)

1. `GET /configuracao` (ou `/saude`) com `desligamento_remoto_habilitado`: sem ele o banner é inferido do último evento de desligamento (`inferirModo`) e fica "desconhecido" até o primeiro pedido.
2. Série temporal/agregação horária de leituras por sensor e por equipamento (por exemplo `GET /sensores/{id}/serie?inicio&fim&passo=1h`): hoje o dashboard monta a série com `/custo` em janelas de 1 h.
3. `PATCH /equipamentos/{id}` (editar `critico`, renomear) e `DELETE` de equipamento e de regra: hoje só se cria; regra só se desativa.
4. `GET /empresas` para trocar de empresa na interface (hoje só `?empresa=` na URL).
5. Emissão de comando assinado (o assinante/agendador não existe): o painel exige que a pessoa cole a assinatura HMAC.
6. Autenticação além do header `X-Empresa-Id` (já listado no M2).

## Limites conhecidos

1. Gráfico por hora: cada dia custa 24 chamadas a `/custo` (7 dias = 168, a API as atende em cerca de 2 s no total; medido: 24 chamadas paralelas em 0,3 s, página de 7 dias em cerca de 1,9 s). Por isso o período é limitado a 1, 3 ou 7 dias, terminando no dia da última leitura (dado de demo é histórico). Um mês seriam 744 chamadas: precisa do endpoint 2.
2. Horas sem leitura entram como 0 kW, não como lacuna. A faixa de cada hora vem da própria API (não duplica a regra tarifária); horas sem linha ficam sem sombreado.
3. kW por hora é o kWh da hora (potência média), somando todos os equipamentos do sensor; não é potência instantânea.
4. Nos gráficos, a 375 px o SVG rola horizontalmente dentro do cartão (largura mínima de 560 px para manter os rótulos legíveis).
5. No modo escuro o contraste entre as faixas sombreadas é baixo (visível no gráfico, discreto na legenda).
6. As regras de desligamento são cadastradas, mas nenhum agendador as executa (limite do M2).
7. Horários de eventos em UTC, leituras em horário ingênuo; o campo de validade do comando é UTC e é rotulado assim.
8. A mensagem de erro de `error.tsx` não traz o detalhe da API (o Next oculta erros de servidor em produção; só o código `digest`).
9. `/custo`, `/ranking` e `/horario` (7 dias) levam cerca de 2 s por página com os dados de demo.
10. Sem testes automatizados do dashboard (verificação manual no navegador e build).
