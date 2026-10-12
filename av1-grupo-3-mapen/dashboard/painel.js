/* Interface do painel: lê os filtros, chama MapenCalculo e desenha SVG. Nenhum cálculo de negócio aqui.
   Cores: azul = observado, cinza = referência/contexto, vermelho = acima da referência (sempre com ▲ ou sinal +). */
(function () {
  "use strict";
  const D = window.MAPEN_DADOS;
  const C = window.MapenCalculo;
  const NS = "http://www.w3.org/2000/svg";
  const TODOS = "__todos__";
  const COR = { obs: "#1d4f91", ref: "#5b6472", exc: "#b42318", abx: "#7b8494", grade: "#e3e7ee", faixa: "#eef1f5" };
  const $ = (id) => document.getElementById(id);

  const nf0 = new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 3 });
  const nf1 = new Intl.NumberFormat("pt-BR", { minimumFractionDigits: 1, maximumFractionDigits: 1 });
  const sinal = (v) => (Math.abs(v) < 0.05 ? "" : v > 0 ? "+" : "−") + nf1.format(Math.abs(v));
  const dm = (iso) => iso.slice(8, 10) + "/" + iso.slice(5, 7);
  const dmy = (iso) => dm(iso) + "/" + iso.slice(0, 4);
  const NOME_DIA = ["seg", "ter", "qua", "qui", "sex", "sáb", "dom"];
  const ULTIMO = D.datas[D.datas.length - 1];
  const PERIODOS = [
    ["Mês", D.inicio_avaliacao, ULTIMO],
    ["Sem. 1", "2018-11-04", "2018-11-10"],
    ["Sem. 2", "2018-11-11", "2018-11-17"],
    ["Sem. 3", "2018-11-18", "2018-11-24"],
    ["Sem. 4", "2018-11-25", ULTIMO],
  ];

  function el(nome, attrs, texto) {
    const e = document.createElementNS(NS, nome);
    for (const [k, v] of Object.entries(attrs || {})) e.setAttribute(k, String(v));
    if (texto !== undefined) e.textContent = texto;
    return e;
  }
  function svg(w, h) {
    return el("svg", { viewBox: `0 0 ${w} ${h}`, "aria-hidden": "true", focusable: "false" });
  }
  function texto(s, x, y, attrs, t) {
    s.appendChild(el("text", { x, y, "font-size": 13, ...attrs }, t));
  }
  function tabela(cabecalho, linhas) {
    const t = document.createElement("table");
    const cab = t.createTHead().insertRow();
    for (const c of cabecalho) cab.appendChild(Object.assign(document.createElement("th"), { textContent: c, scope: "col" }));
    const corpo = t.createTBody();
    for (const l of linhas) {
      const r = corpo.insertRow();
      l.forEach((c) => (r.insertCell().textContent = c));
    }
    const caixa = document.createElement("div");
    caixa.className = "rolar";
    caixa.appendChild(t);
    return caixa;
  }
  /** Marcas "redondas" (1, 2, 5 x 10^k) de 0 até o máximo. */
  function marcas(maximo) {
    const bruto = maximo / 4;
    const pot = Math.pow(10, Math.floor(Math.log10(bruto)));
    const passo = [1, 2, 5, 10].map((f) => f * pot).find((p) => p >= bruto);
    const n = Math.ceil(maximo / passo);
    return { topo: n * passo, marcas: Array.from({ length: n + 1 }, (_, k) => +(k * passo).toFixed(6)) };
  }

  function estado() {
    return {
      ativo: $("f-ativo").value,
      de: $("f-de").value,
      ate: $("f-ate").value,
      ref: document.querySelector("input[name=ref]:checked").value,
    };
  }
  // Nome legível vem de dados.js (rotulos), gerado a partir do código do ativo; sem rótulo, mostra o código.
  const R = (a) => (D.rotulos && D.rotulos[a]) || { nome: a, completo: a, zona: null };
  const nomeAtivo = (a) => (a === TODOS ? "Todos os ativos somados" : R(a).completo);

  /* ---------- Herói: o ativo a investigar primeiro (independe do filtro de ativo) ---------- */
  function desenharHeroi(rk) {
    const topo = rk[0];
    const acima = rk.filter((r) => r.soma_positivos > 0);
    if (!topo || topo.soma_positivos <= 0) {
      $("h-ativo").textContent = "Nenhum";
      $("h-cod").textContent = "";
      $("h-valor").textContent = "sem desvio positivo";
      $("h-titulo").textContent = "Nenhum ativo acima da referência no período.";
      $("h-apoio").replaceChildren();
      $("h-aviso").textContent = "";
      return;
    }
    $("h-ativo").textContent = R(topo.ativo).nome.replace(/-/g, "\u2011"); // hífen que não quebra linha
    $("h-cod").textContent = R(topo.ativo).zona === null ? topo.ativo : `zona ${R(topo.ativo).zona} · código ${topo.ativo}`;
    $("h-valor").textContent = `${sinal(topo.soma_positivos)} kWh acima`;
    const segundo = acima[1];
    $("h-titulo").textContent =
      `${topo.dias_acima} dias acima da referência` + (segundo ? `. Depois: ${R(segundo.ativo).completo} (${sinal(segundo.soma_positivos)} kWh).` : ".");
    const dl = $("h-apoio");
    dl.replaceChildren();
    const item = (t, v) => {
      const d = document.createElement("div");
      d.append(Object.assign(document.createElement("dt"), { textContent: t }), Object.assign(document.createElement("dd"), { textContent: v }));
      dl.appendChild(d);
    };
    item("Saldo", `${sinal(topo.saldo)} kWh`);
    item("Obs. × esp.", `${nf0.format(Math.round(topo.observado))} × ${nf0.format(Math.round(topo.esperado))} kWh`);
    item("Dias", `${topo.dias_acima} acima · ${topo.dias_abaixo} abaixo`);
    $("h-aviso").textContent = "";
  }

  /* ---------- V1: linhas (observado × esperado) + barras do desvio, mesmo eixo X ---------- */
  function desenharV1(pontos, e) {
    const W = 680, H = 470, m = { l: 50, r: 10 };
    const topoA = 34, baseA = 236, topoB = 300, baseB = 420;
    const s = svg(W, H);
    const n = pontos.length;
    const larg = (W - m.l - m.r) / n;
    const x = (i) => m.l + larg * (i + 0.5);
    const vals = pontos.flatMap((p) => [p.obs, p.esp]).filter((v) => v !== null);
    const { topo: ymax, marcas: yM } = marcas(Math.max(1, ...vals) * 1.08);
    const y = (v) => baseA - (v / ymax) * (baseA - topoA);
    const devs = pontos.map((p) => p.desvio).filter((v) => v !== null);
    const { topo: dmax, marcas: dM } = marcas(Math.max(0.5, ...devs.map(Math.abs)) * 1.15);
    const yd = (v) => (topoB + baseB) / 2 - (v / dmax) * ((baseB - topoB) / 2);
    pontos.forEach((p, i) => {
      if (C.diaSemana(p.data) >= 5) {
        s.appendChild(el("rect", { x: m.l + larg * i, y: topoA, width: larg, height: baseA - topoA, fill: COR.faixa }));
        s.appendChild(el("rect", { x: m.l + larg * i, y: topoB, width: larg, height: baseB - topoB, fill: COR.faixa }));
      }
    });
    for (const v of yM) {
      s.appendChild(el("line", { x1: m.l, x2: W - m.r, y1: y(v), y2: y(v), stroke: COR.grade }));
      texto(s, m.l - 8, y(v) + 4, { "text-anchor": "end", "font-size": 12 }, nf0.format(v));
    }
    const passo = Math.ceil(n / 10);
    const trilha = (campo, cor, tracejado, marca) => {
      let d = "", aberto = false;
      pontos.forEach((p, i) => {
        if (p[campo] === null) { aberto = false; return; }
        d += `${aberto ? "L" : "M"}${x(i).toFixed(1)} ${y(p[campo]).toFixed(1)} `;
        aberto = true;
      });
      s.appendChild(el("path", { d, fill: "none", stroke: cor, "stroke-width": marca ? 2.4 : 2, "stroke-dasharray": tracejado || "none", "stroke-linejoin": "round" }));
      if (n <= 31) pontos.forEach((p, i) => {
        if (p[campo] === null) return;
        s.appendChild(marca
          ? el("circle", { cx: x(i), cy: y(p[campo]), r: 3.2, fill: cor })
          : el("rect", { x: x(i) - 3, y: y(p[campo]) - 3, width: 6, height: 6, fill: "#fff", stroke: cor, "stroke-width": 1.6 }));
      });
    };
    trilha("esp", COR.ref, "7 5", false);
    trilha("obs", COR.obs, "", true);
    s.appendChild(el("line", { x1: m.l, x2: m.l + 34, y1: 14, y2: 14, stroke: COR.obs, "stroke-width": 2.4 }));
    s.appendChild(el("circle", { cx: m.l + 17, cy: 14, r: 3.2, fill: COR.obs }));
    texto(s, m.l + 42, 18, { "font-weight": 700, style: `fill:${COR.obs}` }, "Observado");
    s.appendChild(el("line", { x1: m.l + 126, x2: m.l + 160, y1: 14, y2: 14, stroke: COR.ref, "stroke-width": 2, "stroke-dasharray": "7 5" }));
    texto(s, m.l + 168, 18, { "font-weight": 700, style: `fill:${COR.ref}` }, "Esperado");
    texto(s, W - m.r, 18, { "text-anchor": "end", "font-size": 12, style: "fill:#4b5563" }, "kWh/dia · fundo cinza = sáb/dom");

    // painel de desvio: barras a partir do zero (posição em escala comum)
    texto(s, 4, topoB - 12, { "font-size": 12, "font-weight": 700 }, "Desvio = observado − esperado (kWh)");
    for (const v of dM.flatMap((k) => (k === 0 ? [0] : [k, -k]))) {
      s.appendChild(el("line", { x1: m.l, x2: W - m.r, y1: yd(v), y2: yd(v), stroke: v === 0 ? "#4b5563" : COR.grade }));
      texto(s, m.l - 8, yd(v) + 4, { "text-anchor": "end", "font-size": 12 }, (v > 0 ? "+" : v < 0 ? "−" : "") + nf0.format(Math.abs(v)));
    }
    pontos.forEach((p, i) => {
      if (p.desvio === null) return;
      const bw = Math.max(3, larg * 0.62);
      const y0 = yd(0), y1 = yd(p.desvio);
      s.appendChild(el("rect", { x: x(i) - bw / 2, y: Math.min(y0, y1), width: bw, height: Math.max(Math.abs(y1 - y0), 0.8), fill: p.desvio > 0 ? COR.exc : COR.abx }));
    });
    pontos.map((p, i) => ({ p, i })).filter((q) => q.p.desvio !== null && q.p.desvio > 0)
      .sort((a, b) => b.p.desvio - a.p.desvio).slice(0, 2).forEach(({ p, i }) => {
        texto(s, Math.min(Math.max(x(i), m.l + 40), W - m.r - 40), yd(p.desvio) - 6,
          { "text-anchor": "middle", "font-weight": 700, style: `fill:${COR.exc};paint-order:stroke;stroke:#fff;stroke-width:3px` }, `▲ ${sinal(p.desvio)} (${dm(p.data)})`);
      });
    pontos.forEach((p, i) => {
      if (i % passo === 0) texto(s, x(i), baseB + 20, { "text-anchor": "middle", "font-size": 12 }, dm(p.data));
    });
    $("g1").replaceChildren(s);

    const r = C.resumirSerie(pontos);
    const maior = pontos.filter((p) => p.desvio !== null).sort((a, b) => b.desvio - a.desvio)[0];
    const titulo = r.dias_validos === 0
      ? `${nomeAtivo(e.ativo)}: sem dia com dado e referência no período`
      : `${nomeAtivo(e.ativo)}: acima da referência em ${r.dias_acima} de ${r.dias_validos} dias (${sinal(r.soma_positivos)} kWh)`;
    $("t1-txt").textContent = titulo;
    $("g1").setAttribute("aria-label", `${titulo}. ` + (maior && maior.desvio > 0 ? `Maior excesso: ${sinal(maior.desvio)} kWh em ${dm(maior.data)}.` : "Nenhum dia acima da referência.") + " A tabela equivalente está logo abaixo.");
    $("tab1").replaceChildren(tabela(["Data", "Dia", "Observado (kWh)", "Esperado (kWh)", "Desvio (kWh)", "Desvio relativo (%)"],
      pontos.map((p) => [dmy(p.data), NOME_DIA[C.diaSemana(p.data)],
        p.obs === null ? "sem dado" : nf1.format(p.obs), p.esp === null ? "sem referência" : nf1.format(p.esp),
        p.desvio === null ? "—" : sinal(p.desvio) || "0,0", p.rel === null ? "n/c" : sinal(p.rel) || "0,0"])));
    const semDado = pontos.filter((p) => p.obs === null).length;
    const espZero = n > 0 && pontos.every((p) => p.esp === 0);
    $("d1").textContent = `Lacuna = dia sem dado (${semDado} aqui), não zero.` + (espZero ? " Esperado = 0: desvio relativo n/c." : "");
  }

  /* ---------- V2: ranking por ativo (clicável): soma dos desvios positivos e negativos ---------- */
  function desenharV2(linhas, e) {
    const W = 480, linhaH = 40, m = { t: 52, r: 62, b: 16, l: 132 };
    const H = m.t + linhas.length * linhaH + m.b;
    const s = svg(W, H);
    const lim = Math.max(1, ...linhas.flatMap((r) => [r.soma_positivos, -r.soma_negativos])) * 1.12;
    const x = (v) => m.l + ((v + lim) / (2 * lim)) * (W - m.l - m.r);
    texto(s, x(0), 16, { "text-anchor": "middle", "font-size": 12 }, "0 = igual à referência");
    texto(s, x(-lim / 2), 38, { "text-anchor": "middle", "font-size": 12, style: `fill:${COR.ref}`, "font-weight": 700 }, "◀ abaixo");
    texto(s, x(lim / 2), 38, { "text-anchor": "middle", "font-size": 12, style: `fill:${COR.exc}`, "font-weight": 700 }, "acima ▶");
    texto(s, W - 2, 38, { "text-anchor": "end", "font-size": 12, "font-weight": 700 }, "saldo");
    linhas.forEach((r, i) => {
      const yy = m.t + i * linhaH;
      const sel = r.ativo === e.ativo;
      const g = el("g", { class: "linha-sel", tabindex: 0, role: "button", "aria-pressed": sel, "aria-label": `Selecionar ${R(r.ativo).completo}: soma de desvios positivos ${sinal(r.soma_positivos) || "0,0"} kWh` });
      g.appendChild(el("rect", { x: 0, y: yy - 3, width: W, height: linhaH - 4, rx: 6, fill: sel ? COR.faixa : "transparent", stroke: sel ? COR.obs : "none", "stroke-width": 1.5 }));
      texto(g, m.l - 8, yy + 16, { "text-anchor": "end", "font-weight": sel ? 800 : 600 }, R(r.ativo).nome);
      texto(g, m.l - 8, yy + 31, { "text-anchor": "end", "font-size": 12, style: `fill:${COR.ref}` }, R(r.ativo).zona === null ? r.ativo : `zona ${R(r.ativo).zona} · ${r.ativo}`);
      g.appendChild(el("rect", { x: x(r.soma_negativos), y: yy + 4, width: Math.max(x(0) - x(r.soma_negativos), 0), height: 22, fill: COR.abx }));
      g.appendChild(el("rect", { x: x(0), y: yy + 4, width: Math.max(x(r.soma_positivos) - x(0), 0), height: 22, fill: COR.exc }));
      if (r.soma_positivos >= 0.05) texto(g, x(r.soma_positivos) + 5, yy + 20, { "font-weight": 700, "font-size": 12, style: `fill:${COR.exc}` }, `▲ ${sinal(r.soma_positivos)}`);
      texto(g, W - 2, yy + 20, { "text-anchor": "end" }, r.dias_validos === 0 ? "sem dado" : sinal(r.saldo) || "0,0");
      const escolher = () => {
        $("f-ativo").value = r.ativo;
        atualizar();
        const novo = $("g2").querySelectorAll("g[role=button]")[i];
        if (novo) novo.focus();
      };
      g.addEventListener("click", escolher);
      g.addEventListener("keydown", (ev) => { if (ev.key === "Enter" || ev.key === " ") { ev.preventDefault(); escolher(); } });
      s.appendChild(g);
    });
    s.appendChild(el("line", { x1: x(0), x2: x(0), y1: m.t - 8, y2: H - m.b, class: "eixo" }));
    $("g2").replaceChildren(s);
    const acima = linhas.filter((r) => r.soma_positivos > 0);
    const t2 = acima.length === 0 ? "Nenhum ativo acima da referência"
      : `Investigar ${R(acima[0].ativo).completo}${acima[1] ? `, depois ${R(acima[1].ativo).completo}` : ""}`;
    $("t2-txt").textContent = t2;
    $("g2").setAttribute("aria-label", `${t2}. Barras: soma dos desvios diários positivos (acima da referência) e negativos (abaixo), em kWh, por ativo. Tabela equivalente abaixo.`);
    $("tab2").replaceChildren(tabela(["Ativo", "Soma desvios + (kWh)", "Soma desvios − (kWh)", "Saldo (kWh)", "Observado (kWh)", "Esperado (kWh)", "Dias válidos"],
      linhas.map((r) => [`${R(r.ativo).completo} (${r.ativo})`, sinal(r.soma_positivos) || "0,0", sinal(r.soma_negativos) || "0,0", sinal(r.saldo) || "0,0", nf1.format(r.observado), nf1.format(r.esperado), String(r.dias_validos)])));
    $("d2").textContent = "Ordem: soma dos desvios positivos (kWh). Clique numa linha para escolher o ativo.";
  }

  /* ---------- V3: perfil horário, mesma escala nos dois painéis ---------- */
  function desenharV3(e) {
    const alvo = $("g3");
    alvo.replaceChildren();
    if (e.ativo === TODOS) {
      alvo.appendChild(Object.assign(document.createElement("p"), { textContent: "Escolha um ativo para ver o perfil horário (a mediana por hora não se soma entre ativos)." }));
      $("tab3").replaceChildren();
      $("d3").textContent = "";
      $("t3-txt").textContent = "Perfil horário: escolha um ativo";
      $("g3").setAttribute("aria-label", "Perfil horário indisponível para todos os ativos somados.");
      return;
    }
    const perfis = { dia_util: C.perfil(D, e.ativo, e.ref, "dia_util"), fim_de_semana: C.perfil(D, e.ativo, e.ref, "fim_de_semana") };
    const todos = Object.values(perfis).flatMap((p) => p.flatMap((q) => [q.observado_kw, q.referencia_kw])).filter((v) => v !== null);
    const { topo: ymax, marcas: yM } = marcas(Math.max(0.1, ...todos) * 1.1);
    const linhasTab = [];
    const resumo = [];
    for (const tipo of ["dia_util", "fim_de_semana"]) {
      const p = perfis[tipo];
      const W = 520, H = 250, m = { t: 34, r: 12, b: 38, l: 46 };
      const s = svg(W, H);
      const x = (h) => m.l + (h / 23) * (W - m.l - m.r);
      const y = (v) => H - m.b - (v / ymax) * (H - m.t - m.b);
      if (tipo === "dia_util") {
        s.appendChild(el("rect", { x: x(D.expediente.inicio), y: m.t, width: x(D.expediente.fim) - x(D.expediente.inicio), height: H - m.b - m.t, fill: COR.faixa }));
        texto(s, x(D.expediente.inicio) + 4, m.t + 14, { "font-size": 11, style: "fill:#4b5563" }, `expediente assumido ${D.expediente.inicio}h–${D.expediente.fim}h`);
      }
      texto(s, m.l, 18, { "font-weight": 700 }, tipo === "dia_util" ? "Dias úteis" : "Sábados e domingos");
      for (const v of yM) {
        s.appendChild(el("line", { x1: m.l, x2: W - m.r, y1: y(v), y2: y(v), stroke: COR.grade }));
        texto(s, m.l - 6, y(v) + 4, { "text-anchor": "end", "font-size": 12 }, nf0.format(v));
      }
      [0, 6, 12, 18, 23].forEach((h) => texto(s, x(h), H - m.b + 16, { "text-anchor": "middle", "font-size": 12 }, `${h}h`));
      texto(s, W - m.r, H - 6, { "text-anchor": "end", "font-size": 12, style: "fill:#4b5563" }, "hora do dia · kW médio");
      const trilha = (campo, cor, tracejado) => {
        let d = "", aberto = false;
        p.forEach((q) => {
          if (q[campo] === null) { aberto = false; return; }
          d += `${aberto ? "L" : "M"}${x(q.hora).toFixed(1)} ${y(q[campo]).toFixed(1)} `;
          aberto = true;
        });
        s.appendChild(el("path", { d, fill: "none", stroke: cor, "stroke-width": 2.4, "stroke-dasharray": tracejado || "none", "stroke-linejoin": "round" }));
      };
      trilha("referencia_kw", COR.ref, "7 5");
      trilha("observado_kw", COR.obs);
      alvo.appendChild(s);
      const dif = p.filter((q) => q.observado_kw !== null && q.referencia_kw !== null).map((q) => ({ h: q.hora, d: q.observado_kw - q.referencia_kw }));
      const pior = dif.sort((a, b) => Math.abs(b.d) - Math.abs(a.d))[0];
      const nomeTipo = tipo === "dia_util" ? "dias úteis" : "fins de semana";
      resumo.push(pior ? `${nomeTipo} ${(pior.d >= 0 ? "+" : "−") + nf1.format(Math.abs(pior.d))} kW às ${pior.h}h` : `${nomeTipo}: sem dado`);
      p.forEach((q) => linhasTab.push([tipo === "dia_util" ? "dia útil" : "fim de semana", `${q.hora}h`,
        q.observado_kw === null ? "sem dado" : nf1.format(q.observado_kw), q.referencia_kw === null ? "sem dado" : nf1.format(q.referencia_kw)]));
    }
    const t3 = `${nomeAtivo(e.ativo)}, maior diferença horária: ${resumo.join(" · ")}`;
    $("t3-txt").textContent = t3;
    $("g3").setAttribute("aria-label", `${t3}. Tabela equivalente abaixo.`);
    $("tab3").replaceChildren(tabela(["Tipo de dia", "Hora", "Observado (kW)", "Referência (kW)"], linhasTab));
    $("d3").textContent = "Mediana por hora (kW, potência). Mesma escala nos dois painéis.";
  }

  /* ---------- orquestração ---------- */
  function atualizarRapidos(e) {
    $("rapido").querySelectorAll("button").forEach((b, i) => b.setAttribute("aria-pressed", String(PERIODOS[i][1] === e.de && PERIODOS[i][2] === e.ate)));
  }

  function atualizar() {
    const e = estado();
    const ref = C.referencia(D, e.ref);
    atualizarRapidos(e);
    $("regra").textContent = `Referência ${ref.id}: ${ref.nome.toLowerCase()} (${dm(ref.inicio)} a ${dm(D.datas[D.datas.indexOf(ref.fim_excl) - 1] || ref.fim_excl)}).`;
    const dias = C.diasAvaliados(D, e.de, e.ate);
    if (e.de > e.ate || dias.length === 0) {
      $("vazio").hidden = false;
      $("vazio").textContent = `Sem dados no período ${e.de ? dmy(e.de) : "?"} a ${e.ate ? dmy(e.ate) : "?"}. Os dados avaliados vão de ${dmy(D.inicio_avaliacao)} a ${dmy(ULTIMO)}.`;
      $("conteudo").hidden = true;
      return;
    }
    $("vazio").hidden = true;
    $("conteudo").hidden = false;
    const pontos = e.ativo === TODOS ? C.serieTodos(D, e.ref, e.de, e.ate) : C.serieAtivo(D, e.ativo, e.ref, e.de, e.ate);
    const rk = C.ranking(D, e.ref, e.de, e.ate);
    desenharHeroi(rk);
    desenharV1(pontos, e);
    desenharV2(rk, e);
    desenharV3(e);
  }

  function iniciar() {
    $("cabecalho").textContent = `CU-BEMS, andar 2 · ${dmy(D.inicio_avaliacao)} a ${dmy(ULTIMO)}`;
    const sel = $("f-ativo");
    sel.add(new Option("Todos os ativos (somados)", TODOS));
    for (const a of D.ativos) sel.add(new Option(R(a).zona === null ? a : `${R(a).completo} (${a})`, a));
    sel.value = "z1_AC1";
    const q = new URLSearchParams(window.location.search); // estado inicial por URL: ?ativo=&de=&ate=&ref=
    if (q.get("ativo")) sel.value = q.get("ativo") === "todos" ? TODOS : q.get("ativo");
    if (q.get("de")) $("f-de").value = q.get("de");
    if (q.get("ate")) $("f-ate").value = q.get("ate");
    const r = document.querySelector(`input[name=ref][value="${q.get("ref")}"]`);
    if (r) r.checked = true;
    PERIODOS.forEach(([nome, de, ate]) => {
      const b = Object.assign(document.createElement("button"), { type: "button", textContent: nome, title: `${dm(de)} a ${dm(ate)}` });
      b.addEventListener("click", () => { $("f-de").value = de; $("f-ate").value = ate; atualizar(); });
      $("rapido").appendChild(b);
    });
    $("rodape").textContent = "kWh/dia = potência média (kW) × 24 h; dia válido com ≥ 95% dos minutos. Referência C exclui 13, 15 e 23/10 (feriados). Fonte: CU-BEMS, Pipattanasomporn et al. 2020 (CC BY 4.0).";
    document.querySelectorAll("button.ajuda").forEach((b) => {
      b.addEventListener("click", () => {
        const painel = $(b.getAttribute("aria-controls"));
        const abrir = painel.hidden;
        painel.hidden = !abrir;
        b.setAttribute("aria-expanded", String(abrir));
      });
    });
    document.addEventListener("keydown", (ev) => {
      if (ev.key !== "Escape") return;
      document.querySelectorAll("button.ajuda[aria-expanded=true]").forEach((b) => b.click());
    });
    $("filtros").addEventListener("input", atualizar);
    $("filtros").addEventListener("submit", (ev) => ev.preventDefault());
    atualizar();
  }
  iniciar();
})();
