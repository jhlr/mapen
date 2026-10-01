import { Cabecalho, Tabela, Vazio } from "../../components/Basicos";
import { listarEquipamentos, listarEventos } from "../../lib/api";
import { empresaDe } from "../../lib/contexto";
import { dataHora } from "../../lib/dominio/formatacao";
import type { Params } from "../../lib/dominio/parametros";
import { explicarMotivo } from "../../lib/dominio/seguranca";

export const dynamic = "force-dynamic";

const TIPOS: Record<string, string> = {
  desligamento_executado: "Desligamento executado",
  religamento_executado: "Religamento executado",
  comando_rejeitado: "Comando rejeitado",
  queda_energia: "Queda de energia",
  falha_conexao: "Falha de conexão",
};

export default async function Eventos({ searchParams }: { searchParams: Params }) {
  const empresa = await empresaDe(searchParams);
  const [eventos, equipamentos] = await Promise.all([listarEventos(empresa), listarEquipamentos(empresa)]);
  const nomes = new Map(equipamentos.map((x) => [x.id, x.nome]));
  return (
    <>
      <Cabecalho titulo="Alertas e eventos" subtitulo="Mais recentes primeiro, até 100. Horários em UTC." />
      {eventos.length === 0 ? <Vazio>Nenhum evento registrado.</Vazio> : (
        <Tabela legenda="Eventos">
          <thead><tr><th>Quando (UTC)</th><th>Tipo</th><th>Equipamento</th><th>Origem</th><th>Autorizado por</th><th>Detalhe</th></tr></thead>
          <tbody>
            {eventos.map((e) => {
              const motivo = e.payload.motivo;
              return (
                <tr key={e.id}>
                  <td className="nw">{dataHora(e.ts)}</td>
                  <td className={e.tipo === "comando_rejeitado" ? "rej" : undefined}>{TIPOS[e.tipo] ?? e.tipo}</td>
                  <td>{e.equipamento_id === null ? "-" : (nomes.get(e.equipamento_id) ?? e.equipamento_id)}</td>
                  <td>{e.origem}</td>
                  <td>{e.autorizado_por ?? "-"}</td>
                  <td className="det">{motivo !== undefined ? explicarMotivo(motivo) : Object.entries(e.payload).map(([k, v]) => `${k}: ${v}`).join(", ")}</td>
                </tr>
              );
            })}
          </tbody>
        </Tabela>
      )}
    </>
  );
}
