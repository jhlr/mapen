import type { ReactNode } from "react";
import "./globals.css";

export const metadata = { title: "MAPEN" };

export default function Layout({ children }: { children: ReactNode }) {
  return (
    <html lang="pt-BR">
      <body>
        <nav>
          <a href="/">Consumo</a>
          <a href="/custo">Custo por faixa</a>
          <a href="/ranking">Ranking</a>
          <a href="/cadastro">Cadastro</a>
          <a href="/eventos">Eventos</a>
        </nav>
        <main>{children}</main>
      </body>
    </html>
  );
}
