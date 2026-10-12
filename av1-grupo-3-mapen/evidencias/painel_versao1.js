/* Interface do painel: lê os filtros, chama MapenCalculo e desenha SVG. Nenhum cálculo de negócio aqui. */
(function () {
  "use strict";
  const D = window.MAPEN_DADOS;
  const C = window.MapenCalculo;
  const NS = "http://www.w3.org/2000/svg";
  const TODOS = "__todos__";
  const $ = (id) => document.getElementById(id);

  const nf0 = new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 1 });
  const nf1 = new Intl.NumberFormat("pt-BR", { minimumFractionDigits: 1, maximumFractionDigits: 1 });
  const sinal = (v) => (v > 0 ? "+" : v < 0 ? "−" : "") + nf1.format(Math.abs(v));
  const dm = (iso) => iso.slice(8, 10) + "/" + iso.slice(5, 7);
  const dmy = (iso) => dm(iso) + "/" + iso.slice(0, 4);
  const NOME_DIA = ["seg", "ter", "qua", "qui", "sex", "sáb", "dom"];

  function el(nome, attrs, texto) {
    const e = document.createElementNS(NS, nome);
    for (const [k, v] of Object.entries(attrs || {})) e.setAttribute(k, String(v));
    if (texto !== undefined) e.textContent = texto;
    return e;
  }

  function svg(w, h, titulo) {
    const s = el("svg", { viewBox: `0 0 ${w} ${h}`, role: "presentation", focusable: "false" });
    if (titulo) s.appendChild(el("title", {}, titulo));
    return s;
  }

  function tabela(cabecalho, linhas) {
    const t = document.createElement("table");
    const cab = t.createTHead().insertRow();
    for (const c of cabecalho) cab.appendChild(Object.assign(document.createElement("th"), { textContent: c, scope: "col" }));
    const corpo = t.createTBody();
    for (const l of linhas) {
      const r = corpo.insertRow();
      l.forEach((c) => r.insertCell().textContent = c);
    }
    const caixa = document.createElement("div");
    caixa.className = "rolar";
    caixa.appendChild(t);
    return caixa;
  }

  /** Marcas "redondas" (1, 2, 5 x 10^k) de 0 até o máximo; devolve {topo, marcas}. */
  function marcas(maximo) {
    const bruto = maximo / 4;
    const pot = Math.pow(10, Math.floor(Math.log10(bruto)));
    const passo = [1, 2, 5, 10].map((f) => f * pot).find((p) => p >= bruto);
    const n = Math.ceil(maximo / passo);
    return { topo: n * passo, marcas: Array.from({ length: n + 1 }, (_, k) => k * passo) };
  }

  function estado() {
    return {
      ativo: $("f-ativo").value,
      de: $("f-de").value,
      ate: $("f-ate").value,
      ref: document.querySelector("input[name=ref]:checked").value,
    };
  }

  function nomeAtivo(a) {
    return a === TODOS ? "todos os ativos somados" : a;
  }

  /* ---------- V1: observado x esperado por dia ---------- */
  function desenharV1(pontos, e) {
    const W = 680, H = 310, m = { t: 36, r: 16, b: 40, l: 52 };
    const s = svg(W, H, "Energia diária observada e esperada");
    const vals = pontos.flatMap((p) => [p.obs, p.esp]).filter((v) => v !== null);
    const { topo: ymax, marcas: yMarcas } = marcas(Math.max(1, ...vals) * 1.1);
    const x = (i) => m.l + (pontos.length === 1 ? (W - m.l - m.r) / 2 : (i * (W - m.l - m.r)) / (pontos.length - 1));
    const y = (v) => H - m.b - (v / ymax) * (H - m.t - m.b);
    const larg = (W - m.l - m.r) / Math.max(1, pontos.length - 1);
    pontos.forEach((p, i) => {
      if (C.diaSemana(p.data) >= 5)
        s.appendChild(el("rect", { x: x(i) - larg / 2, y: m.t, width: larg, height: H - m.t - m.b, fill: "#e6eaf0" }));
    });
    for (const v of yMarcas) {
      s.appendChild(el("line", { x1: m.l, x2: W - m.r, y1: y(v), y2: y(v), class: "grade" }));
      s.appendChild(el("text", { x: m.l - 6, y: y(v) + 4, "text-anchor": "end", "font-size": 11 }, nf0.format(v)));
    }
    s.appendChild(el("text", { x: 14, y: H - m.b, "font-size": 11, transform: `rotate(-90 14 ${H - m.b})`, "text-anchor": "start" }, "kWh por dia"));
    const passo = Math.ceil(pontos.length / 10);
    pontos.forEach((p, i) => {
      if (i % passo === 0) s.appendChild(el("text", { x: x(i), y: H - m.b + 16, "text-anchor": "middle", "font-size": 11 }, dm(p.data)));
    });
    const trilha = (campo, cor, tracejado) => {
      let d = "";
      let aberto = false;
      pontos.forEach((p, i) => {
        if (p[campo] === null) { aberto = false; return; }
        d += `${aberto ? "L" : "M"}${x(i).toFixed(1)} ${y(p[campo]).toFixed(1)} `;
        aberto = true;
      });
      s.appendChild(el("path", { d, fill: "none", stroke: cor, "stroke-width": 2, "stroke-dasharray": tracejado || "none" }));
      pontos.forEach((p, i) => {
        if (p[campo] === null) return;
        s.appendChild(campo === "obs"
          ? el("circle", { cx: x(i), cy: y(p[campo]), r: 3, fill: cor })
          : el("rect", { x: x(i) - 3, y: y(p[campo]) - 3, width: 6, height: 6, fill: "#fff", stroke: cor, "stroke-width": 1.5 }));
      });
    };
    trilha("esp", "#8a4b00", "6 4");
    trilha("obs", "#17456f");
    const maiores = pontos.map((p, i) => ({ p, i })).filter((q) => q.p.desvio !== null && q.p.desvio > 0)
      .sort((a, b) => b.p.desvio - a.p.desvio).slice(0, 2);
    maiores.forEach(({ p, i }) => {
      s.appendChild(el("text", { x: Math.min(Math.max(x(i), m.l + 50), W - m.r - 50), y: y(p.obs) - 8, "text-anchor": "middle", "font-size": 11, "font-weight": 700, style: "paint-order:stroke;stroke:#fff;stroke-width:3px" },
        `▲ ${sinal(p.desvio)} kWh (${dm(p.data)})`));
    });
    s.appendChild(el("text", { x: m.l, y: 16, "font-size": 12, "font-weight": 700, style: "fill:#17456f" }, "● ── Observado"));
    s.appendChild(el("text", { x: m.l + 130, y: 16, "font-size": 12, "font-weight": 700, style: "fill:#8a4b00" }, "□ - - Esperado (referência)"));
    $("g1").replaceChildren(s);
    $("g1").setAttribute("aria-label", "Linhas de energia diária observada e esperada");
    $("tab1").replaceChildren(tabela(["Data", "Dia", "Observado (kWh)", "Esperado (kWh)", "Desvio (kWh)", "Desvio relativo (%)"],
      pontos.map((p) => [dmy(p.data), NOME_DIA[C.diaSemana(p.data)],
        p.obs === null ? "sem dado" : nf1.format(p.obs), p.esp === null ? "sem referência" : nf1.format(p.esp),
        p.desvio === null ? "—" : sinal(p.desvio), p.rel === null ? "n/c" : sinal(p.rel)])));
    const semDado = pontos.filter((p) => p.obs === null).length;
    const espZero = pontos.length > 0 && pontos.every((p) => p.esp === 0);
    $("d1").textContent = `Faixas cinza: sábado e domingo. Lacunas são dias sem dado suficiente (${semDado} neste recorte), não zero. `
      + (espZero ? "Esperado = 0 em todos os dias: o desvio relativo não se calcula (n/c); só o absoluto é mostrado." : "Desvio relativo = 100 × desvio / esperado, calculado só com esperado > 0.");
  }

  /* ---------- V2: ranking por ativo (v1: ordenado pelo saldo) ---------- */
  function desenharV2(linhas, e) {
    const W = 680, H = 60 + linhas.length * 34, m = { t: 24, r: 90, b: 28, l: 90 };
    const s = svg(W, H, "Saldo de desvios por ativo");
    const lim = Math.max(1, ...linhas.map((r) => Math.abs(r.saldo))) * 1.1;
    const x = (v) => m.l + ((v + lim) / (2 * lim)) * (W - m.l - m.r);
    s.appendChild(el("line", { x1: x(0), x2: x(0), y1: m.t - 6, y2: H - m.b, class: "eixo" }));
    s.appendChild(el("text", { x: x(0), y: m.t - 10, "text-anchor": "middle", "font-size": 11 }, "0 = igual à referência"));
    linhas.forEach((r, i) => {
      const yy = m.t + i * 34;
      const w = Math.abs(x(r.saldo) - x(0));
      s.appendChild(el("rect", { x: Math.min(x(0), x(r.saldo)), y: yy, width: Math.max(w, 1), height: 22, fill: r.saldo > 0 ? "#a83232" : "#17456f" }));
      s.appendChild(el("text", { x: m.l - 8, y: yy + 15, "text-anchor": "end", "font-size": 12 }, r.ativo));
      s.appendChild(el("text", { x: r.saldo >= 0 ? x(r.saldo) + 5 : x(r.saldo) - 5, y: yy + 15, "font-size": 11, "text-anchor": r.saldo >= 0 ? "start" : "end" }, `${sinal(r.saldo)} kWh`));
    });
    s.appendChild(el("text", { x: W / 2, y: H - 6, "text-anchor": "middle", "font-size": 11 }, "Saldo = soma dos desvios do período (kWh): positivo acima da referência, negativo abaixo"));
    $("g2").replaceChildren(s);
    $("g2").setAttribute("aria-label", "Barras horizontais com o saldo de desvios por ativo");
    $("tab2").replaceChildren(tabela(["Ativo", "Saldo (kWh)", "Observado (kWh)", "Esperado (kWh)", "Dias válidos"],
      linhas.map((r) => [r.ativo, sinal(r.saldo), nf1.format(r.observado), nf1.format(r.esperado), String(r.dias_validos)])));
    $("d2").textContent = "Ordem: do maior saldo para o menor. Vermelho e azul também diferem pelo lado do zero e pelo sinal do rótulo.";
  }

  /* ---------- V3: perfil horário por tipo de dia ---------- */
  function desenharV3(e) {
    const alvo = $("g3");
    alvo.replaceChildren();
    if (e.ativo === TODOS) {
      alvo.appendChild(Object.assign(document.createElement("p"), { textContent: "Escolha um ativo para ver o perfil horário (a mediana por hora não se soma entre ativos)." }));
      $("tab3").replaceChildren();
      $("d3").textContent = "";
      return;
    }
    const linhasTab = [];
    for (const tipo of ["dia_util", "fim_de_semana"]) {
      const p = C.perfil(D, e.ativo, e.ref, tipo);
      const W = 330, H = 240, m = { t: 26, r: 10, b: 36, l: 44 };
      const s = svg(W, H, tipo === "dia_util" ? "Dias úteis" : "Fins de semana");
      const { topo: ymax, marcas: yMarcas } = marcas(Math.max(0.1, ...p.flatMap((q) => [q.observado_kw, q.referencia_kw]).filter((v) => v !== null)) * 1.1);
      const x = (h) => m.l + (h / 23) * (W - m.l - m.r);
      const y = (v) => H - m.b - (v / ymax) * (H - m.t - m.b);
      s.appendChild(el("text", { x: m.l, y: 16, "font-size": 12, "font-weight": 700 }, tipo === "dia_util" ? "Dias úteis" : "Sábados e domingos"));
      for (const v of yMarcas) {
        s.appendChild(el("line", { x1: m.l, x2: W - m.r, y1: y(v), y2: y(v), class: "grade" }));
        s.appendChild(el("text", { x: m.l - 5, y: y(v) + 4, "text-anchor": "end", "font-size": 10 }, nf0.format(v)));
      }
      [0, 6, 12, 18, 23].forEach((h) => s.appendChild(el("text", { x: x(h), y: H - m.b + 14, "text-anchor": "middle", "font-size": 10 }, `${h}h`)));
      s.appendChild(el("text", { x: (m.l + W - m.r) / 2, y: H - 6, "text-anchor": "middle", "font-size": 10 }, "hora do dia"));
      const trilha = (campo, cor, tracejado) => {
        let d = "", aberto = false;
        p.forEach((q) => {
          if (q[campo] === null) { aberto = false; return; }
          d += `${aberto ? "L" : "M"}${x(q.hora).toFixed(1)} ${y(q[campo]).toFixed(1)} `;
          aberto = true;
        });
        s.appendChild(el("path", { d, fill: "none", stroke: cor, "stroke-width": 2, "stroke-dasharray": tracejado || "none" }));
      };
      trilha("referencia_kw", "#8a4b00", "6 4");
      trilha("observado_kw", "#17456f");
      alvo.appendChild(s);
      p.forEach((q) => linhasTab.push([tipo === "dia_util" ? "dia útil" : "fim de semana", `${q.hora}h`,
        q.observado_kw === null ? "sem dado" : q.observado_kw.toFixed(2), q.referencia_kw === null ? "sem dado" : q.referencia_kw.toFixed(2)]));
    }
    alvo.setAttribute("aria-label", "Perfil horário de potência: observado e referência, dias úteis e fins de semana");
    $("tab3").replaceChildren(tabela(["Tipo de dia", "Hora", "Observado (kW)", "Referência (kW)"], linhasTab));
    $("d3").textContent = "Eixo: kW médio por hora (potência, não energia), mediana entre os dias do tipo. Contínua: observado; tracejada: referência. Consumo fora do expediente não é desperdício por si só.";
  }

  /* ---------- síntese, estados e orquestração ---------- */
  function atualizar() {
    const e = estado();
    const ref = C.referencia(D, e.ref);
    $("regra").textContent = `Referência ${ref.id}: ${ref.nome}, janela ${dmy(ref.inicio)} a ${dmy(D.datas[D.datas.indexOf(ref.fim_excl) - 1] || ref.fim_excl)} (termina antes do período avaliado). Esperado = mediana da energia diária do mesmo dia da semana.`;
    const dias = C.diasAvaliados(D, e.de, e.ate);
    const vazio = $("vazio");
    const vistas = $("vistas");
    if (e.de > e.ate || dias.length === 0) {
      vazio.hidden = false;
      vazio.textContent = `Sem dados no período ${dmy(e.de || "0000-00-00")} a ${dmy(e.ate || "0000-00-00")}. Os dados avaliados vão de ${dmy(D.inicio_avaliacao)} a ${dmy(D.datas[D.datas.length - 1])}.`;
      vistas.hidden = true;
      $("sintese").textContent = "";
      return;
    }
    vazio.hidden = true;
    vistas.hidden = false;
    const pontos = e.ativo === TODOS ? C.serieTodos(D, e.ref, e.de, e.ate) : C.serieAtivo(D, e.ativo, e.ref, e.de, e.ate);
    const r = C.resumirSerie(pontos);
    const linhas = C.ranking(D, e.ref, e.de, e.ate).sort((a, b) => b.saldo - a.saldo || a.ativo.localeCompare(b.ativo));
    desenharV1(pontos, e);
    desenharV2(linhas, e);
    desenharV3(e);
    const maior = pontos.filter((p) => p.desvio !== null).sort((a, b) => b.desvio - a.desvio)[0];
    $("sintese").textContent = r.dias_validos === 0
      ? `${nomeAtivo(e.ativo)}: nenhum dia com dado e referência no período.`
      : `${nomeAtivo(e.ativo)}, ${dmy(e.de)} a ${dmy(e.ate)}: observado ${nf1.format(r.observado)} kWh, esperado ${nf1.format(r.esperado)} kWh, saldo ${sinal(r.saldo)} kWh em ${r.dias_validos} dias.`
        + (maior && maior.desvio > 0 ? ` Maior excesso: ${sinal(maior.desvio)} kWh em ${dm(maior.data)}.` : " Nenhum dia acima da referência.")
        + " Investigar não é o mesmo que desperdício: confirme a necessidade operacional.";
  }

  function iniciar() {
    $("cabecalho").textContent = `Unidade: andar 2 de um prédio universitário (CU-BEMS, 2018). Período avaliado: ${dmy(D.inicio_avaliacao)} a ${dmy(D.datas[D.datas.length - 1])}. Fonte: ${D.fonte}`;
    const sel = $("f-ativo");
    sel.add(new Option("Todos os ativos (somados)", TODOS));
    for (const a of D.ativos) sel.add(new Option(a, a));
    sel.value = "z1_AC1";
    const q = new URLSearchParams(window.location.search); // estado inicial por URL: ?ativo=&de=&ate=&ref=
    if (q.get("ativo")) sel.value = q.get("ativo") === "todos" ? TODOS : q.get("ativo");
    if (q.get("de")) $("f-de").value = q.get("de");
    if (q.get("ate")) $("f-ate").value = q.get("ate");
    const r = document.querySelector(`input[name=ref][value="${q.get("ref")}"]`);
    if (r) r.checked = true;
    $("rodape").textContent = "Energia diária (kWh) = potência média dos minutos presentes (kW) × 24 h; dia válido com ≥ 95% dos minutos. kW é potência; kWh é energia. Calendário: 13, 15 e 23/10/2018 tratados como feriado na referência C.";
    $("filtros").addEventListener("input", atualizar);
    $("filtros").addEventListener("submit", (ev) => ev.preventDefault());
    atualizar();
  }
  iniciar();
})();
