import Link from "next/link";
import type { Sensor } from "../lib/api";
import { MODALIDADES, PERIODOS_DIAS, consulta } from "../lib/dominio/parametros";

type Base = { rota: string; sensor?: string; modalidade?: string; dias?: number };

export function SeletorSensor({ rota, sensor, modalidade, dias, sensores }: Base & { sensores: Sensor[] }) {
  if (sensores.length < 2) return <p className="sub">Sensor: {sensores[0]?.nome ?? "nenhum"}</p>;
  return (
    <div className="seletor" role="group" aria-label="Sensor">
      <span>Sensor</span>
      {sensores.map((s) => (
        <Link
          key={s.id}
          href={`${rota}${consulta({ sensor: s.id, modalidade, dias })}`}
          aria-current={s.id === sensor ? "true" : undefined}
        >
          {s.nome}
        </Link>
      ))}
    </div>
  );
}

export function SeletorModalidade({ rota, sensor, modalidade, dias }: Base) {
  return (
    <div className="seletor" role="group" aria-label="Modalidade tarifária">
      <span>Modalidade</span>
      {MODALIDADES.map((m) => (
        <Link key={m} href={`${rota}${consulta({ sensor, modalidade: m, dias })}`} aria-current={m === modalidade ? "true" : undefined}>
          {m}
        </Link>
      ))}
    </div>
  );
}

export function SeletorPeriodo({ rota, sensor, modalidade, dias }: Base) {
  return (
    <div className="seletor" role="group" aria-label="Período">
      <span>Período</span>
      {PERIODOS_DIAS.map((d) => (
        <Link key={d} href={`${rota}${consulta({ sensor, modalidade, dias: d })}`} aria-current={d === dias ? "true" : undefined}>
          {d === 1 ? "1 dia" : `${d} dias`}
        </Link>
      ))}
    </div>
  );
}
