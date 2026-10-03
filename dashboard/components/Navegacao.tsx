"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";

const ITENS = [
  { href: "/", rotulo: "Consumo" },
  { href: "/horario", rotulo: "Por hora" },
  { href: "/custo", rotulo: "Custo por faixa" },
  { href: "/ranking", rotulo: "Ranking" },
  { href: "/modelos", rotulo: "Modelos" },
  { href: "/previsao", rotulo: "Previsão" },
  { href: "/alertas", rotulo: "Alertas" },
  { href: "/economia", rotulo: "Economia" },
  { href: "/cadastro", rotulo: "Cadastro" },
  { href: "/desligamento", rotulo: "Desligamento" },
  { href: "/eventos", rotulo: "Eventos" },
];

/** Em tela larga os itens ficam em linha; abaixo de 900 px viram um menu que abre e fecha (botao de 44 px). */
export function Navegacao() {
  const caminho = usePathname();
  const [aberto, setAberto] = useState(false);
  return (
    <nav aria-label="Principal" data-aberto={aberto}>
      <span className="marca">MAPEN</span>
      <button
        type="button"
        className="menu-botao"
        aria-expanded={aberto}
        aria-controls="menu-itens"
        onClick={() => setAberto((a) => !a)}
      >
        {aberto ? "Fechar" : "Menu"}
      </button>
      <ul id="menu-itens">
        {ITENS.map((i) => (
          <li key={i.href}>
            <Link href={i.href} aria-current={caminho === i.href ? "page" : undefined} onClick={() => setAberto(false)}>
              {i.rotulo}
            </Link>
          </li>
        ))}
      </ul>
    </nav>
  );
}
