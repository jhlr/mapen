(() => {
  "use strict";
  const D = window.MAPEN_DADOS;
  const corpo = document.getElementById("tab-ativos");
  for (const a of D.ativos) {
    const r = (D.rotulos && D.rotulos[a]) || { nome: a, zona: null, tipo: "", descricao: "", nota: "" };
    const tr = document.createElement("tr");
    const celulas = [a, r.nome, r.zona === null ? "—" : String(r.zona), [r.descricao, r.nota].filter(Boolean).join(" ")];
    celulas.forEach((texto, i) => {
      const td = document.createElement("td");
      td.className = i === 0 ? "cod-c esq" : "esq";
      td.textContent = texto;
      tr.appendChild(td);
    });
    corpo.appendChild(tr);
  }
})();
