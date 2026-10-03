# 6 modelos de negócio — eficiência energética PF/PJ (Fase D)

> Origem: pasta do Drive `https://drive.google.com/drive/u/1/folders/1cg5QKQCmOL6HZaXu7d_NPH_NSAlbdEQu`
> (compartilhada por jmsf@cesar.school, arquivos criados 2026-09-16). Continuação de
> `docs/oportunidades_negocio_energia.md` (ranking bruto de 10 oportunidades) e do design
> `docs/designs/eficiencia-energetica-pf-pj.md` (Fase D, APPROVED 2026-09-11) — mesma frente de
> mercado, agora com 4 temas consolidados em 6 modelos de negócio individuais (2 a mais que o
> doc de temas: Proof e Energy Intensity). Registrado cru, sem validação de números — todos os
> 6 documentos se autodeclaram "modelo conceitual", sem dado real de piloto.

## Os 4 temas-base (doc "Sugestões de temas Eficiencia Energetica")

Critérios de seleção usados pra gerar os temas: foco direto em redução de consumo/desperdício/
custo; uso inicial de dado já existente (fatura, planilha, medição); benefício mensurável em
kWh e R$; sem comando automático sobre equipamento crítico no 1º estágio; aplicável a fábricas,
instalações técnicas e empresas de energia; evolução futura pra IA/sensores/tempo real.

| Tema | Complexidade | Potencial | Valor comprovável | Prioridade (doc) |
|---|---|---|---|---|
| Índice de Energia Invisível | Baixa | Alto | Muito alto | 1 |
| Validador de Projetos | Baixa | Muito alto | Muito alto | 2 |
| Passaporte de Equipamentos | Baixa a média | Alto | Alto | 3 |
| Planejador de Janelas | Média | Alto | Alto | 4 |

Rota de produto sugerida pelo doc: Energia Invisível → Validação de Investimentos → Saúde
Energética dos Ativos → Planejamento Otimizado.

## Os 6 modelos de negócio individuais

### 1. MAPEN Zero Waste (= Índice de Energia Invisível)
- **Proposta:** identifica quando/quanto a organização consome sem gerar produção,
  disponibilidade ou serviço útil.
- **Público:** primário = PMEs com carga previsível (supermercado, hotel, clínica,
  restaurante, escola, oficina, pequena fábrica); secundário = prédios administrativos,
  bombeamento, instalações técnicas.
- **MVP:** importação de fatura/CSV/Excel; cadastro de turnos/feriados/paradas/produção; mapa
  de calor produtivo×necessário×ocioso; alertas + relatório mensal (kWh e R$).
- **Receita:** SaaS por instalação/faixa de consumo; diagnóstico inicial pago + monitoramento
  recorrente; white-label pra consultorias/ESCOs.
- **Piloto:** 1 instalação com curva de carga horária + calendário operacional + indicador de
  produção/ocupação.
- **Risco citado:** consumo fora de horário nem sempre é desperdício; dado sem granularidade
  suficiente limita a explicação.

### 2. MAPEN Energy Health (= Passaporte de Equipamentos)
- **Proposta:** transforma consumo energético em indicador de degradação do ativo, ligando
  eficiência, manutenção e gestão de ativos.
- **Público:** primário = operações com motor/bomba/compressor/refrigeração/climatização/
  transformador com medição disponível; secundário = saneamento, mineração, indústria.
- **MVP:** cadastro de ativos + potência nominal; carga de medições/horas/produção/manutenção;
  linha de base individual; ficha de saúde energética + alerta estatístico de desvio.
- **Receita:** assinatura por qtd de ativos monitorados; pacote de diagnóstico do parque;
  licença corporativa.
- **Piloto:** 10-30 ativos semelhantes com consumo + horas + histórico de manutenção.
- **Risco citado:** mudança de carga pode parecer degradação (precisa normalizar); poucas
  medições reduzem precisão.

### 3. MAPEN Proof (não está nos 4 temas-base — idéia extra)
- **Proposta:** compara consumo esperado × observado pra comprovar, com transparência, se uma
  intervenção entregou economia normalizada (M&V — measurement & verification).
- **Público:** primário = ESCOs, integradores solares, HVAC, fornecedores de motor/automação/
  iluminação; secundário = quem comprou a intervenção (indústria, rede comercial, hospital).
- **MVP:** importação de consumo antes/depois; entrada de produção/clima/ocupação quando
  houver; baseline simplificado com sensibilidade; relatório de economia observada×normalizada.
- **Receita:** cobrança por projeto avaliado; assinatura por portfólio; white-label pra ESCOs;
  opcional futuro: remuneração vinculada à economia validada.
- **Piloto:** 1 intervenção já concluída com dado antes/depois.
- **Risco citado:** economia calculada depende da qualidade da baseline; projeto complexo pode
  exigir engenharia especializada. **Problema estrutural não citado no doc:** depende de já
  existir uma intervenção concluída pra comprovar — sem uma ESCO parceira como cliente inicial,
  não tem o que validar (ovo-e-galinha).

### 4. MAPEN Smart Investment (= Validador de Projetos)
- **Proposta:** prioriza ações de eficiência por impacto, investimento, facilidade de
  implantação e qualidade do dado — auditor energético digital pra PME.
- **Público:** primário = padaria, restaurante, mercado, clínica, academia, escola, hotel
  pequeno, loja, oficina; secundário = pequena fábrica, rede comercial de baixa maturidade.
- **MVP:** questionário setorial + leitura de 12 faturas (quando houver); cadastro dos
  principais equipamentos/horários; biblioteca de ações com faixa de investimento; ranking +
  sensibilidade + plano de execução.
- **Receita:** diagnóstico digital de entrada (preço fixo); assinatura leve de acompanhamento;
  venda em lote pra associação/cooperativa/banco/programa de eficiência.
- **Piloto:** 1 segmento homogêneo (ex: padaria ou clínica), 5-10 unidades.
- **Risco citado:** recomendação genérica reduz credibilidade; dado autodeclarado pode estar
  errado.

### 5. MAPEN Energy Intensity (não está nos 4 temas-base — idéia extra)
- **Proposta:** compara unidades/turnos/processos equivalentes por indicador de intensidade
  energética, preservando dado comercial sensível — benchmark interno privado.
- **Público:** primário = rede com múltiplas unidades (varejo, mercado, hotel, hospital,
  escola, saneamento, telecom); secundário = grupo industrial, empresa de energia.
- **MVP:** importação mensal de consumo + denominador operacional; KPI por segmento;
  comparação interna + dispersão; ranking privado de oportunidade (sem exposição pública).
- **Receita:** assinatura corporativa por nº de unidades; projeto de padronização de KPI;
  módulo futuro de benchmark externo anônimo (com consentimento).
- **Piloto:** 5+ unidades da mesma organização com consumo/área/ocupação/produção comparável.
- **Risco citado:** unidades parecidas podem operar em condição diferente; ranking mal
  interpretado gera conclusão errada.

### 6. MAPEN Best Time (= Planejador de Janelas)
- **Proposta:** recomenda janelas de menor custo/menor impacto de demanda pra atividade
  flexível, sem comando automático sobre equipamento.
- **Público:** primário = fábrica em turno, bombeamento, refrigeração, utilidades, teste,
  carregamento de bateria; secundário = quem tem tarifa horária/demanda contratada/geração
  solar.
- **MVP:** importação de curva de carga + calendário; cadastro de duração/potência/horário
  permitido; regra de tarifa e limite de demanda; ranking das 3 melhores janelas.
- **Receita:** assinatura por instalação; cobrança por módulo/qtd de atividade; integração
  futura com sistemas de produção/manutenção/energia.
- **Piloto:** 1 atividade recorrente, flexível e bem medida.
- **Risco citado:** restrição operacional incompleta gera recomendação inviável; tarifa/
  condição pode variar.

## Análise: qual das 6 encaixa com o que o MAPEN já tem construído

O projeto hoje (Fase A) é `src/redflags_perdas.py` + `src/model_redflags.py` (planejado):
detecção de perda técnica/não técnica em série temporal EPE (UF/ano) + SAMP-Balanço
(distribuidora/mês), com z-score e depois XGBoost/LightGBM. Esse pipeline resolve **anomalia
em série temporal agregada por unidade organizacional** — não tem nada de telemetria de
equipamento nem curva de carga horária.

Cruzando isso com as 6 ideias:

| Ideia | Dado exigido | Reusa pipeline atual? |
|---|---|---|
| Energy Intensity | Consumo mensal + denominador operacional, por unidade | **Sim — é o mesmo tipo de comparação entre unidades que `redflags_perdas.py` já faz entre distribuidoras** |
| Smart Investment | Questionário + até 12 faturas | Não, mas MVP é o mais barato de construir do zero (sem telemetria) |
| Zero Waste | Curva de carga horária + calendário operacional | Não — precisa de granularidade que o MAPEN não tem hoje (mesma lacuna já registrada em `eficiencia-energetica-pf-pj.md`: dado de smart meter/equipamento não existe) |
| Energy Health | Medição por ativo | Não — telemetria de equipamento, dado novo |
| Proof | Par de consumo antes/depois de uma intervenção | Não, e depende de ter uma ESCO parceira com intervenção já feita |
| Best Time | Curva de carga horária + tarifa horária + demanda contratada | Não — maior exigência de dado das 6, mercado mais estreito |

## As 3 escolhidas (recomendação, 2026-09-17)

1. **Energy Intensity** — única que roda em cima do pipeline já validado
   (`redflags_perdas.py`, nível distribuidora); zero dado novo pra prototipar.
2. **Smart Investment** — maior potencial comercial pelo próprio ranking do doc
   (prioridade 2, "muito alto"); único MVP que não depende de telemetria/curva de carga —
   caminho mais rápido pra um piloto real com PME.
3. **Zero Waste** — prioridade 1 no doc; ROI mais fácil de contar (kWh/R$ ocioso fora de
   horário); serve de base pra evoluir depois pro Passaporte (Energy Health) e Planejador
   (Best Time), conforme a rota de produto do próprio doc de temas.

**Descartadas:** Energy Health (telemetria por ativo — aquisição de dado mais pesada), Proof
(ovo-e-galinha: precisa de parceiro ESCO com intervenção concluída antes de ter o que
comprovar), Best Time (maior exigência de dado das 6 + mercado mais estreito).

## Tensão estratégica não resolvida (flag, não decisão)

As 6 ideias miram **PME/indústria como cliente final** (eficiência energética do lado do
consumidor). O Kickoff Neoenergia e a Fase A miram **distribuidora como cliente**
(perda técnica/não técnica, lado regulatório). São dois públicos-compradores diferentes, dois
tipos de dado diferentes (fatura/telemetria de cliente final vs. EPE/SAMP-Balanço agregado),
e potencialmente dois produtos diferentes debaixo da mesma marca MAPEN — não necessariamente
um pivot (ver `docs/designs/eficiencia-energetica-pf-pj.md`, que já registra isso como "soma,
não pivot"), mas vale nomear antes de comprometer engenharia em qualquer uma das 3 escolhidas
acima. Nenhuma decisão de priorização entre Fase A (redflags/distribuidora) e Fase D
(PME/eficiência) foi tomada nesta sessão.

## Fontes (arquivos no Drive, lidos em 2026-09-17)

- `Sugestões de temas Eficiencia Energetica.docx` / `.pdf`
- `01_MAPEN_Zero_Waste_Modelo_de_Negocio.pdf`
- `02_MAPEN_Energy_Health_Modelo_de_Negocio.pdf`
- `03_MAPEN_Proof_Modelo_de_Negocio.pdf`
- `04_MAPEN_Smart_Investment_Modelo_de_Negocio.pdf`
- `05_MAPEN_Energy_Intensity_Modelo_de_Negocio.pdf`
- `06_MAPEN_Best_Time_Modelo_de_Negocio.pdf`
