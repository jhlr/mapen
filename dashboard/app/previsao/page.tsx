import { Cabecalho } from "../../components/Basicos";
import { Indisponivel, SecaoPrevisao } from "../../components/ResultadosM3";
import { previsaoModelos } from "../../lib/api";

export const dynamic = "force-dynamic";

export default async function Previsao() {
  const p = await previsaoModelos();
  return (
    <>
      <Cabecalho titulo="Previsão" subtitulo="Previsão do dia seguinte: qual previsor adotar, sem usar consumo de menos de 24 h antes" />
      {p.disponivel ? <SecaoPrevisao p={p} /> : <Indisponivel o="previsão" />}
    </>
  );
}
