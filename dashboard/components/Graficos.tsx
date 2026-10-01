"use client";

import { useEffect, useRef, useState } from "react";
import { num } from "../lib/dominio/formatacao";
import { trechosDeFaixa } from "../lib/dominio/serie";

const ME = 46, MD = 10, MS = 10, MI = 30, LARGURA_INICIAL = 640, PX_ROTULO = 40;

const NOME_FAIXA: Record<string, string> = { fora_ponta: "Fora de ponta", intermediario: "Intermediária", ponta: "Ponta", unico: "Única" };
const classeFaixa = (f: string | null): string => `faixa f-${f ?? "nd"}`;

/** Passo "redondo" para o eixo Y (1, 2, 5 x 10^k) com ~4 divisoes. */
function escalaY(max: number): { topo: number; passo: number } {
  const bruto = Math.max(max, 1e-6) / 4;
  const pot = 10 ** Math.floor(Math.log10(bruto));
  const passo = ([1, 2, 5, 10].find((m) => m * pot >= bruto) ?? 10) * pot;
  return { topo: Math.ceil(Math.max(max, 1e-6) / passo) * passo, passo };
}

export function LegendaFaixas({ faixas }: { faixas: (string | null)[] }) {
  const presentes = [...new Set(faixas)].filter((f): f is string => f !== null);
  return (
    <ul className="legenda" aria-label="Faixas tarifárias">
      {presentes.map((f) => (
        <li key={f}><span className={`amostra f-${f}`} />{NOME_FAIXA[f] ?? f}</li>
      ))}
    </ul>
  );
}

/** Largura do elemento, acompanhando redimensionamento (janela, rotacao, menu). */
function useLargura(): [React.RefObject<HTMLDivElement | null>, number] {
  const ref = useRef<HTMLDivElement | null>(null);
  const [largura, setLargura] = useState(LARGURA_INICIAL);
  useEffect(() => {
    const el = ref.current;
    if (el === null) return;
    const medir = (): void => setLargura(Math.max(200, Math.floor(el.clientWidth)));
    medir();
    const obs = new ResizeObserver(medir);
    obs.observe(el);
    return () => obs.disconnect();
  }, []);
  return [ref, largura];
}

type Base = {
  faixas: (string | null)[];
  valores: number[];
  rotuloX: (i: number) => string;
  /** Candidatos (em indices) para o espacamento entre rotulos do eixo X; usa o menor que couber. */
  passos: number[];
  descricao: string;
};

function Moldura({ faixas, valores, rotuloX, passos, descricao, tipo }: Base & { tipo: "barras" | "linha" }) {
  const [ref, L] = useLargura();
  const A = L < 480 ? 220 : L < 900 ? 260 : 300;
  const LARG = L - ME - MD, ALT = A - MS - MI;
  const n = valores.length;
  const { topo, passo } = escalaY(Math.max(...valores, 0));
  const largura = LARG / n;
  const passoX = passos.find((p) => p * largura >= PX_ROTULO) ?? passos[passos.length - 1] ?? 1;
  const x = (i: number): number => ME + (tipo === "barras" ? (i + 0.5) * largura : ((i + 0.5) / n) * LARG);
  const y = (v: number): number => MS + ALT - (v / topo) * ALT;
  const ticks = Array.from({ length: Math.round(topo / passo) + 1 }, (_, k) => k * passo);
  const casas = passo < 1 ? 1 : 0;
  return (
    <div className="grafico" role="region" aria-label={descricao} tabIndex={0}>
      <div ref={ref} className="grafico-medida">
        <svg viewBox={`0 0 ${L} ${A}`} role="img" aria-label={descricao}>
          <defs>
            <pattern id="hachura-ponta" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
              <line x1="0" y1="0" x2="0" y2="6" className="hachura" strokeWidth="2" />
            </pattern>
          </defs>
          {trechosDeFaixa(faixas).map((t) => (
            <g key={`${t.de}-${t.faixa}`}>
              <rect className={classeFaixa(t.faixa)} x={ME + t.de * largura} y={MS} width={(t.ate - t.de) * largura} height={ALT} />
              {t.faixa === "ponta" && (
                <rect fill="url(#hachura-ponta)" x={ME + t.de * largura} y={MS} width={(t.ate - t.de) * largura} height={ALT} />
              )}
            </g>
          ))}
          {ticks.map((v) => (
            <g key={v}>
              <line className="grade" x1={ME} x2={L - MD} y1={y(v)} y2={y(v)} />
              <text className="eixo" x={ME - 6} y={y(v) + 4} textAnchor="end">{num(v, casas)}</text>
            </g>
          ))}
          {valores.map((_, i) =>
            i % passoX === 0 ? (
              <text key={i} className="eixo" x={tipo === "barras" ? x(i) : ME + (i / n) * LARG + 2} y={A - MI + 18} textAnchor={tipo === "barras" ? "middle" : "start"}>{rotuloX(i)}</text>
            ) : null,
          )}
          {tipo === "barras" ? (
            valores.map((v, i) => (
              <rect key={i} className="barra-svg" x={x(i) - largura * 0.32} width={largura * 0.64} y={y(v)} height={MS + ALT - y(v)}>
                <title>{`${rotuloX(i)}: ${num(v, 1)} kW`}</title>
              </rect>
            ))
          ) : (
            <polyline className="linha-svg" fill="none" points={valores.map((v, i) => `${x(i)},${y(v)}`).join(" ")} />
          )}
        </svg>
      </div>
      <p className="eixo-y">kW (média da hora)</p>
    </div>
  );
}

const PASSOS_HORA = [1, 2, 3, 4, 6, 8, 12, 24];

export function GraficoMediaPorHora({ medias }: { medias: { hora: number; kw: number; faixa: string | null }[] }) {
  return (
    <Moldura
      tipo="barras"
      faixas={medias.map((m) => m.faixa)}
      valores={medias.map((m) => m.kw)}
      rotuloX={(i) => `${String(i).padStart(2, "0")}h`}
      passos={PASSOS_HORA}
      descricao="Média de kW por hora do dia, com as faixas tarifárias ao fundo"
    />
  );
}

export function GraficoSerie({ pontos }: { pontos: { inicio: string; kw: number; faixa: string | null }[] }) {
  const dias = Math.max(1, Math.round(pontos.length / 24));
  return (
    <Moldura
      tipo="linha"
      faixas={pontos.map((p) => p.faixa)}
      valores={pontos.map((p) => p.kw)}
      rotuloX={(i) => {
        const p = pontos[i];
        if (p === undefined) return "";
        return dias <= 1 ? `${p.inicio.slice(11, 13)}h` : `${p.inicio.slice(8, 10)}/${p.inicio.slice(5, 7)}`;
      }}
      passos={dias <= 1 ? PASSOS_HORA : [24, 48, 72, 168, 336, 720]}
      descricao="Potência média (kW) hora a hora no período, com as faixas tarifárias ao fundo"
    />
  );
}
