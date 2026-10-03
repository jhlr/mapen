import { Cabecalho, Tabela, Vazio } from "../../components/Basicos";
import { listarEquipamentos, listarEventos } from "../../lib/api";
import { detalheDispositivo } from "../../lib/dominio/eventos";
import { dataHora } from "../../lib/dominio/formatacao";
import { explicarMotivo } from "../../lib/dominio/seguranca";

export const dynamic = "force-dynamic";

const TIPOS: Record<string, string> = {
  desligamento_executado: "Desligamento executado",
  religamento_executado: "Religamento executado",
  comando_recebido: "Comando recebido",
  comando_rejeitado: "Comando rejeitado",
  configuracao_alterada: "Configuração alterada",
  ultimo_suspiro: "Último suspiro (início da queda)",
  queda_energia: "Queda de energia",
  falha_conexao: "Falha de conexão",
};

export default async function Eventos() {
  const [eventos, equipamentos] = await Promise.all([listarEventos(), listarEquipamentos()]);
  const nomes = new Map(equipamentos.map((x) => [x.id, x.nome]));
  return (
    <>
      <Cabecalho titulo="Alertas e eventos" subtitulo="Mais recentes primeiro, até 100. Horários de Recife." />
      {eventos.length === 0 ? <Vazio>Nenhum evento registrado.</Vazio> : (
        <Tabela legenda="Eventos" empilhar>
          <thead><tr><th>Quando (Recife)</th><th>Tipo</th><th>Equipamento</th><th>Origem</th><th>Autorizado por</th><th>Detalhe</th></tr></thead>
          <tbody>
            {eventos.map((e) => {
              const motivo = e.payload.motivo;
              return (
                <tr key={e.id}>
                  <td className="nw" data-label="Quando">{dataHora(e.ts)}</td>
                  <td data-label="Tipo" className={e.tipo === "comando_rejeitado" ? "rej" : undefined}>{TIPOS[e.tipo] ?? e.tipo}</td>
                  <td data-label="Equipamento">{e.equipamento_id === null ? "-" : (nomes.get(e.equipamento_id) ?? e.equipamento_id)}</td>
                  <td data-label="Origem">{e.origem}</td>
                  <td data-label="Autorizado por">{e.autorizado_por ?? "-"}</td>
                  <td className="det" data-label="Detalhe">{motivo !== undefined ? explicarMotivo(motivo) : detalheDispositivo(e) ?? Object.entries(e.payload).map(([k, v]) => `${k}: ${v}`).join(", ")}</td>
                </tr>
              );
            })}
          </tbody>
        </Tabela>
      )}
    </>
  );
}
