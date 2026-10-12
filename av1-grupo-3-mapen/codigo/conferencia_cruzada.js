// Compara o cálculo do painel (dashboard/calculo.js) com o do Python (evidencias/resultados_python.json).
// Uso: node codigo/conferencia_cruzada.js
const fs = require("fs");
const path = require("path");
const raiz = path.resolve(__dirname, "..");
globalThis.window = {};
eval(fs.readFileSync(path.join(raiz, "dashboard/dados.js"), "utf8").replace("window.MAPEN_DADOS", "globalThis.D"));
const C = require(path.join(raiz, "dashboard/calculo.js"));
const py = JSON.parse(fs.readFileSync(path.join(raiz, "evidencias/resultados_python.json"), "utf8"));
const TOL = 1e-3;
let maxDif = 0, n = 0, falhas = 0;
for (const ref of ["A", "B", "C"]) {
  for (const linha of py.desvios_diarios[ref]) {
    const p = C.serieAtivo(globalThis.D, linha.ativo, ref, "2018-11-04", "2018-12-01").find((x) => x.data === linha.data);
    for (const [k, kp] of [["obs", "kwh"], ["esp", "esperado"], ["desvio", "desvio"]]) {
      const a = p[k], b = linha[kp];
      if ((a === null) !== (b === null)) { falhas++; continue; }
      if (a !== null) { maxDif = Math.max(maxDif, Math.abs(a - b)); n++; if (Math.abs(a - b) > TOL) falhas++; }
    }
  }
  const rk = C.ranking(globalThis.D, ref, "2018-11-04", "2018-12-01");
  const rp = py.ranking[ref];
  rk.forEach((r, i) => {
    if (r.ativo !== rp[i].ativo) falhas++;
    if (Math.abs(r.soma_positivos - rp[i].soma_positivos) > 0.01 || Math.abs(r.saldo - rp[i].saldo) > 0.01) falhas++;
  });
}
console.log(JSON.stringify({ comparacoes: n, maior_diferenca_abs: maxDif, falhas }));
process.exit(falhas ? 1 : 0);
