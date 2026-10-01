import type { ReactNode } from "react";
import { Navegacao } from "../components/Navegacao";
import "./globals.css";

export const metadata = { title: "MAPEN", description: "Consumo, custo e controle de equipamentos" };
export const viewport = { width: "device-width", initialScale: 1 };

export default function Layout({ children }: { children: ReactNode }) {
  return (
    <html lang="pt-BR">
      <body>
        <Navegacao />
        <main>{children}</main>
      </body>
    </html>
  );
}
