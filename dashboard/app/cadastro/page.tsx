import { buscar, EMPRESA_PADRAO, primeiro, type Equipamento, type Regra, type Sensor } from "../../lib/api";
import type { Params } from "../../lib/contexto";

export const dynamic = "force-dynamic";

export default async function Cadastro({ searchParams }: { searchParams: Params }) {
  const empresa = primeiro((await searchParams).empresa) ?? EMPRESA_PADRAO;
  const [sensores, equipamentos, regras] = await Promise.all([
    buscar<Sensor[]>("/sensores", empresa),
    buscar<Equipamento[]>("/equipamentos", empresa),
    buscar<Regra[]>("/regras", empresa),
  ]);
  return (
    <>
      <h1>Cadastro</h1>
      <h2>Sensores ({sensores.length})</h2>
      <table>
        <thead><tr><th>Id</th><th>Nome</th></tr></thead>
        <tbody>{sensores.map((s) => <tr key={s.id}><td>{s.id}</td><td>{s.nome}</td></tr>)}</tbody>
      </table>
      <h2>Equipamentos ({equipamentos.length})</h2>
      <table>
        <thead><tr><th>Sensor</th><th>Equipamento</th><th>Critico</th></tr></thead>
        <tbody>
          {equipamentos.map((e) => (
            <tr key={e.id}><td>{e.sensor_id}</td><td>{e.nome}</td><td>{e.critico ? "sim" : "nao"}</td></tr>
          ))}
        </tbody>
      </table>
      <h2>Regras de desligamento ({regras.length})</h2>
      <table>
        <thead><tr><th>Equipamento</th><th>Cron</th><th>Ativa</th><th>Autorizado por</th></tr></thead>
        <tbody>
          {regras.map((r) => (
            <tr key={r.id}><td>{r.equipamento_id}</td><td>{r.cron}</td><td>{r.ativo ? "sim" : "nao"}</td><td>{r.autorizado_por}</td></tr>
          ))}
        </tbody>
      </table>
      {regras.length === 0 && <p>Nenhuma regra. O desligamento remoto comeca desativado (so recomendacao).</p>}
    </>
  );
}
