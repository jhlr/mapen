import { EMPRESA_PADRAO, listarSensores, type Sensor } from "./api";
import { ehModalidade, primeiro, type Modalidade, type Params } from "./dominio/parametros";

export type Contexto = { empresa: string; sensores: Sensor[]; sensor: string | undefined; modalidade: Modalidade };

export async function empresaDe(params: Params): Promise<string> {
  return primeiro((await params).empresa) ?? EMPRESA_PADRAO;
}

/** Resolve empresa, sensor e modalidade da URL; padrao: primeiro sensor da empresa e tarifa branca. */
export async function contexto(params: Params): Promise<Contexto> {
  const p = await params;
  const empresa = primeiro(p.empresa) ?? EMPRESA_PADRAO;
  const sensores = await listarSensores(empresa);
  const modalidade = primeiro(p.modalidade);
  return {
    empresa,
    sensores,
    sensor: primeiro(p.sensor) ?? sensores[0]?.id,
    modalidade: ehModalidade(modalidade) ? modalidade : "branca",
  };
}
