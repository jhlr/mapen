import { Cabecalho } from "../../components/Basicos";
import { Indisponivel, SecaoEconomia } from "../../components/ResultadosM3";
import { economiaM3 } from "../../lib/api";

export const dynamic = "force-dynamic";

export default async function Economia() {
  const e = await economiaM3();
  return (
    <>
      <Cabecalho titulo="Economia" subtitulo="Validação do método: redução sintética conhecida em dado real" />
      {e.disponivel ? <SecaoEconomia e={e} /> : <Indisponivel o="economia" />}
    </>
  );
}
