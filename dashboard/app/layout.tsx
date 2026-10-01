import { Suspense, type ReactNode } from "react";
import { Navegacao } from "../components/Navegacao";
import "./globals.css";

export const metadata = { title: "MAPEN", description: "Consumo, custo e controle de equipamentos" };
export const viewport = { width: "device-width", initialScale: 1 };

export default function Layout({ children }: { children: ReactNode }) {
  return (
    <html lang="pt-BR">
      <body>
        <Suspense fallback={<nav aria-label="Principal"><span className="marca">MAPEN</span></nav>}>
          <Navegacao />
        </Suspense>
        <main>{children}</main>
      </body>
    </html>
  );
}
