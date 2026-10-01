import { AlternarRegra } from "../../components/AlternarRegra";
import { Aviso, Cabecalho, Secao, Tabela, Vazio } from "../../components/Basicos";
import { FormEquipamento } from "../../components/FormEquipamento";
import { FormRegra } from "../../components/FormRegra";
import { listarEquipamentos, listarRegras, listarSensores } from "../../lib/api";
import { empresaDe } from "../../lib/contexto";
import { dataHora, SIM_NAO } from "../../lib/dominio/formatacao";
import type { Params } from "../../lib/dominio/parametros";

export const dynamic = "force-dynamic";

export default async function Cadastro({ searchParams }: { searchParams: Params }) {
  const empresa = await empresaDe(searchParams);
  const [sensores, equipamentos, regras] = await Promise.all([
    listarSensores(empresa), listarEquipamentos(empresa), listarRegras(empresa),
  ]);
  const nomeEquip = new Map(equipamentos.map((e) => [e.id, e.nome]));
  return (
    <>
      <Cabecalho titulo="Cadastro" subtitulo="Sensores, equipamentos e regras de desligamento." />
      <Secao titulo={`Sensores (${sensores.length})`}>
        <Tabela legenda="Sensores">
          <thead><tr><th>Id</th><th>Nome</th></tr></thead>
          <tbody>{sensores.map((s) => <tr key={s.id}><td>{s.id}</td><td>{s.nome}</td></tr>)}</tbody>
        </Tabela>
      </Secao>
      <Secao titulo={`Equipamentos (${equipamentos.length})`}>
        <Tabela legenda="Equipamentos">
          <thead><tr><th>Sensor</th><th>Equipamento</th><th>Crítico</th></tr></thead>
          <tbody>
            {equipamentos.map((e) => (
              <tr key={e.id}>
                <td>{e.sensor_id}</td><td>{e.nome}</td>
                <td className={e.critico ? "rej" : undefined}>{SIM_NAO(e.critico)}</td>
              </tr>
            ))}
          </tbody>
        </Tabela>
        <details className="novo">
          <summary>Novo equipamento</summary>
          <FormEquipamento empresa={empresa} sensores={sensores} />
        </details>
      </Secao>
      <Secao titulo={`Regras de desligamento (${regras.length})`}>
        {regras.length === 0 ? (
          <Vazio>Nenhuma regra. O desligamento remoto começa desativado (só recomendação).</Vazio>
        ) : (
          <Tabela legenda="Regras de desligamento">
            <thead><tr><th>Equipamento</th><th>Agenda (cron)</th><th>Estado</th><th>Autorizado por</th><th>Criada em</th><th /></tr></thead>
            <tbody>
              {regras.map((r) => (
                <tr key={r.id}>
                  <td>{nomeEquip.get(r.equipamento_id) ?? r.equipamento_id}</td>
                  <td><code>{r.cron}</code></td>
                  <td>{r.ativo ? "ativa" : "inativa"}</td>
                  <td>{r.autorizado_por}</td>
                  <td className="nw">{dataHora(r.criado_em)}</td>
                  <td><AlternarRegra empresa={empresa} regra={r} /></td>
                </tr>
              ))}
            </tbody>
          </Tabela>
        )}
        <Aviso tom="atencao" titulo="Regras não são executadas">
          A API só guarda a regra. Nenhum agendador a dispara ainda. Não existe excluir regra: use Desativar.
        </Aviso>
        <details className="novo">
          <summary>Nova regra</summary>
          <FormRegra empresa={empresa} equipamentos={equipamentos} />
        </details>
      </Secao>
    </>
  );
}
