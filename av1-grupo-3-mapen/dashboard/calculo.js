/* Cálculos do painel (funções puras, sem DOM). Mesmas regras de codigo/av1_desvio.py.
   Usado pelo navegador (window.MapenCalculo) e pelo Node (module.exports) na conferência cruzada. */
(function (raiz) {
  "use strict";

  /** Dia da semana com segunda = 0 (igual ao pandas dayofweek). */
  function diaSemana(iso) {
    const d = new Date(iso + "T00:00:00Z").getUTCDay();
    return (d + 6) % 7;
  }

  function mediana(valores) {
    const v = valores.filter((x) => x !== null && !Number.isNaN(x)).sort((a, b) => a - b);
    if (v.length === 0) return null;
    const m = v.length >> 1;
    return v.length % 2 ? v[m] : (v[m - 1] + v[m]) / 2;
  }

  /** Índice da data; uma data fora da lista (ex.: fim exclusivo depois do último dia) vira o tamanho da lista. */
  function indiceDe(dados, iso) {
    const i = dados.datas.indexOf(iso);
    return i === -1 ? dados.datas.length : i;
  }

  /** Índices dos dias da janela de referência (excluindo feriados quando a referência pede). */
  function diasReferencia(dados, ref) {
    const ini = indiceDe(dados, ref.inicio);
    const fim = indiceDe(dados, ref.fim_excl);
    const idx = [];
    for (let i = ini; i < fim; i++) {
      if (ref.excluir_feriados && dados.feriados.includes(dados.datas[i])) continue;
      idx.push(i);
    }
    return idx;
  }

  function referencia(dados, refId) {
    return dados.referencias.find((r) => r.id === refId);
  }

  /** Dias avaliados que caem em [de, ate] (ISO inclusivo), dentro do intervalo avaliado. */
  function diasAvaliados(dados, de, ate) {
    const ini = indiceDe(dados, dados.inicio_avaliacao);
    const fim = indiceDe(dados, dados.fim_avaliacao_exclusivo);
    const idx = [];
    for (let i = ini; i < fim; i++) {
      const d = dados.datas[i];
      if (d >= de && d <= ate) idx.push(i);
    }
    return idx;
  }

  /** Esperado (kWh/dia) de um ativo em cada dia da semana (0..6) para a referência escolhida. */
  function esperadoPorDiaSemana(dados, ativo, refId) {
    const idxRef = diasReferencia(dados, referencia(dados, refId));
    const porDia = [[], [], [], [], [], [], []];
    for (const i of idxRef) porDia[diaSemana(dados.datas[i])].push(dados.diario[ativo][i]);
    return porDia.map(mediana);
  }

  /** Série diária de um ativo: observado, esperado, desvio e desvio relativo. */
  function serieAtivo(dados, ativo, refId, de, ate) {
    const esp = esperadoPorDiaSemana(dados, ativo, refId);
    return diasAvaliados(dados, de, ate).map((i) => {
      const data = dados.datas[i];
      const obs = dados.diario[ativo][i];
      const e = esp[diaSemana(data)];
      const desvio = obs === null || e === null ? null : obs - e;
      const rel = desvio !== null && e > 0 ? (100 * desvio) / e : null;
      return { data, obs, esp: e, desvio, rel };
    });
  }

  /** Soma de todos os ativos: um dia só conta se todos os ativos tiverem dado e referência. */
  function serieTodos(dados, refId, de, ate) {
    const series = dados.ativos.map((a) => serieAtivo(dados, a, refId, de, ate));
    return series[0].map((_, k) => {
      const dia = series.map((s) => s[k]);
      const completo = dia.every((p) => p.obs !== null && p.esp !== null);
      const obs = completo ? dia.reduce((s, p) => s + p.obs, 0) : null;
      const esp = completo ? dia.reduce((s, p) => s + p.esp, 0) : null;
      const desvio = completo ? obs - esp : null;
      const rel = completo && esp > 0 ? (100 * desvio) / esp : null;
      return { data: dia[0].data, obs, esp, desvio, rel };
    });
  }

  function resumirSerie(pontos) {
    const validos = pontos.filter((p) => p.desvio !== null);
    return {
      soma_positivos: validos.filter((p) => p.desvio > 0).reduce((s, p) => s + p.desvio, 0),
      soma_negativos: validos.filter((p) => p.desvio < 0).reduce((s, p) => s + p.desvio, 0),
      saldo: validos.reduce((s, p) => s + p.desvio, 0),
      dias_validos: validos.length,
      dias_acima: validos.filter((p) => p.desvio > 0).length,
      dias_abaixo: validos.filter((p) => p.desvio < 0).length,
      observado: validos.reduce((s, p) => s + p.obs, 0),
      esperado: validos.reduce((s, p) => s + p.esp, 0),
    };
  }

  /** Ranking por ativo ordenado pela soma dos desvios positivos (empate: nome do ativo). */
  function ranking(dados, refId, de, ate) {
    return dados.ativos
      .map((a) => ({ ativo: a, ...resumirSerie(serieAtivo(dados, a, refId, de, ate)) }))
      .sort((x, y) => y.soma_positivos - x.soma_positivos || x.ativo.localeCompare(y.ativo));
  }

  /** Perfil horário (mediana entre dias da potência média por hora): observado x referência. */
  function perfil(dados, ativo, refId, tipo) {
    const ehFim = (iso) => diaSemana(iso) >= 5;
    const doTipo = (i) => (tipo === "fim_de_semana") === ehFim(dados.datas[i]);
    const valido = (i) => dados.diario[ativo][i] !== null;
    const ini = indiceDe(dados, dados.inicio_avaliacao);
    const fim = indiceDe(dados, dados.fim_avaliacao_exclusivo);
    const idxObs = [];
    for (let i = ini; i < fim; i++) if (doTipo(i) && valido(i)) idxObs.push(i);
    const idxRef = diasReferencia(dados, referencia(dados, refId)).filter((i) => doTipo(i) && valido(i));
    const porHora = (idx, h) => mediana(idx.map((i) => dados.horario[ativo][i][h]));
    return Array.from({ length: 24 }, (_, h) => ({
      hora: h,
      observado_kw: porHora(idxObs, h),
      referencia_kw: porHora(idxRef, h),
    }));
  }

  const api = { diaSemana, mediana, serieAtivo, serieTodos, resumirSerie, ranking, perfil, referencia, diasAvaliados };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else raiz.MapenCalculo = api;
})(typeof window !== "undefined" ? window : globalThis);
