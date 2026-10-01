import { Cabecalho } from "../../components/Basicos";
import { Indisponivel, SecaoModelos } from "../../components/ResultadosM3";
import { resumoModelos } from "../../lib/api";

export const dynamic = "force-dynamic";

export default async function Modelos() {
  const r = await resumoModelos();
  return (
    <>
      <Cabecalho titulo="Modelos" subtitulo="Baseline sazonal contra LightGBM, explicações e benchmark sintético" />
      {r.disponivel ? <SecaoModelos r={r} /> : <Indisponivel o="modelos" />}
    </>
  );
}
