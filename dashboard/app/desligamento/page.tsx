import { Aviso, Cabecalho } from "../../components/Basicos";
import { ControleRemoto } from "../../components/ControleRemoto";
import { PainelDesligamento } from "../../components/PainelDesligamento";
import { listarEquipamentos, listarRegras, obterConfiguracao } from "../../lib/api";

export const dynamic = "force-dynamic";

export default async function Desligamento() {
  const [equipamentos, regras, config] = await Promise.all([listarEquipamentos(), listarRegras(), obterConfiguracao()]);
  const habilitado = config.desligamento_remoto_habilitado;
  return (
    <>
      <Cabecalho titulo="Solicitar desligamento" subtitulo="Envia um comando assinado para a API; toda tentativa gera um evento." />
      {habilitado ? (
        <Aviso tom="atencao" titulo="Desligamento remoto habilitado">
          desligamento_remoto_habilitado = verdadeiro: comandos de desligar assinados e válidos são aceitos para
          equipamentos não críticos.
        </Aviso>
      ) : (
        <Aviso tom="atencao" titulo="Modo só recomendação: desligamento remoto desativado">
          desligamento_remoto_habilitado = falso: pedidos de desligar são registrados e rejeitados; nada chega ao relé.
        </Aviso>
      )}
      <ControleRemoto habilitado={habilitado} />
      <h2>Comando assinado</h2>
      <PainelDesligamento equipamentos={equipamentos} regras={regras} />
    </>
  );
}
