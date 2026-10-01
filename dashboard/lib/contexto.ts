import { EMPRESA_PADRAO, buscar, primeiro, type Sensor } from "./api";

export type Params = Promise<Record<string, string | string[] | undefined>>;

/** Resolve empresa e sensor selecionados (?empresa=, ?sensor=); padrao: primeiro sensor da empresa. */
export async function contexto(params: Params): Promise<{
  empresa: string;
  sensores: Sensor[];
  sensor: string | undefined;
  modalidade: string;
}> {
  const p = await params;
  const empresa = primeiro(p.empresa) ?? EMPRESA_PADRAO;
  const sensores = await buscar<Sensor[]>("/sensores", empresa);
  const sensor = primeiro(p.sensor) ?? sensores[0]?.id;
  return { empresa, sensores, sensor, modalidade: primeiro(p.modalidade) ?? "branca" };
}
