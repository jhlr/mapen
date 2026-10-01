import { Aviso, Cabecalho } from "../../components/Basicos";
import { PainelDesligamento } from "../../components/PainelDesligamento";
import { listarEquipamentos, listarEventos, listarRegras } from "../../lib/api";
import { empresaDe } from "../../lib/contexto";
import type { Params } from "../../lib/dominio/parametros";
import { inferirModo } from "../../lib/dominio/seguranca";

export const dynamic = "force-dynamic";

export default async function Desligamento({ searchParams }: { searchParams: Params }) {
  const empresa = await empresaDe(searchParams);
  const [equipamentos, regras, eventos] = await Promise.all([
    listarEquipamentos(empresa), listarRegras(empresa), listarEventos(empresa, 50),
  ]);
  const modo = inferirModo(eventos);
  return (
    <>
      <Cabecalho titulo="Solicitar desligamento" subtitulo="Envia um comando assinado para a API; toda tentativa gera um evento." />
      {modo === "recomendacao" && (
        <Aviso tom="atencao" titulo="Modo só recomendação: desligamento remoto desativado">
          A API recusou o último pedido de desligamento por estar com desligamento_remoto_habilitado = falso.
          Pedidos de desligar são registrados e rejeitados; nada chega ao relé.
        </Aviso>
      )}
      {modo === "habilitado" && (
        <Aviso titulo="Desligamento remoto habilitado">Já houve desligamento executado por esta empresa.</Aviso>
      )}
      {modo === "desconhecido" && (
        <Aviso tom="atencao" titulo="Estado do desligamento remoto desconhecido">
          A API não expõe a configuração desligamento_remoto_habilitado (padrão: falso, só recomendação). O estado
          aparece aqui após o primeiro pedido, a partir da resposta.
        </Aviso>
      )}
      <PainelDesligamento empresa={empresa} equipamentos={equipamentos} regras={regras} />
    </>
  );
}
