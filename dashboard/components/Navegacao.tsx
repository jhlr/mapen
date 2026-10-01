"use client";

import Link from "next/link";
import { usePathname, useSearchParams } from "next/navigation";

const ITENS = [
  { href: "/", rotulo: "Consumo" },
  { href: "/horario", rotulo: "Por hora" },
  { href: "/custo", rotulo: "Custo por faixa" },
  { href: "/ranking", rotulo: "Ranking" },
  { href: "/cadastro", rotulo: "Cadastro" },
  { href: "/desligamento", rotulo: "Desligamento" },
  { href: "/eventos", rotulo: "Eventos" },
];

export function Navegacao() {
  const caminho = usePathname();
  const empresa = useSearchParams().get("empresa");
  const sufixo = empresa === null ? "" : `?empresa=${encodeURIComponent(empresa)}`;
  return (
    <nav aria-label="Principal">
      <span className="marca">MAPEN</span>
      <ul>
        {ITENS.map((i) => (
          <li key={i.href}>
            <Link href={`${i.href}${sufixo}`} aria-current={caminho === i.href ? "page" : undefined}>
              {i.rotulo}
            </Link>
          </li>
        ))}
      </ul>
      {empresa !== null && <span className="empresa">empresa: {empresa}</span>}
    </nav>
  );
}
