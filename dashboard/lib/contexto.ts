import { listarSensores, type Sensor } from "./api";
import { ehModalidade, primeiro, type Modalidade, type Params } from "./dominio/parametros";

export type Contexto = { sensores: Sensor[]; sensor: string | undefined; modalidade: Modalidade };

/** Resolve sensor e modalidade da URL; padrao: primeiro sensor da empresa da chave e tarifa branca. */
export async function contexto(params: Params): Promise<Contexto> {
  const p = await params;
  const sensores = await listarSensores();
  const modalidade = primeiro(p.modalidade);
  return {
    sensores,
    sensor: primeiro(p.sensor) ?? sensores[0]?.id,
    modalidade: ehModalidade(modalidade) ? modalidade : "branca",
  };
}
