import type { ReactNode } from "react";

export function Cabecalho({ titulo, subtitulo }: { titulo: string; subtitulo?: string }) {
  return (
    <header className="cabecalho">
      <h1>{titulo}</h1>
      {subtitulo !== undefined && <p className="sub">{subtitulo}</p>}
    </header>
  );
}

export function Aviso({ tom = "info", titulo, children }: { tom?: "info" | "atencao" | "erro"; titulo?: string; children: ReactNode }) {
  return (
    <div className={`aviso ${tom}`} role={tom === "erro" ? "alert" : "note"}>
      {titulo !== undefined && <strong>{titulo}</strong>}
      <div>{children}</div>
    </div>
  );
}

export function Cartao({ rotulo, valor, nota }: { rotulo: string; valor: string; nota?: string }) {
  return (
    <div className="card">
      <span className="rotulo">{rotulo}</span>
      <b>{valor}</b>
      {nota !== undefined && <span className="nota">{nota}</span>}
    </div>
  );
}

export function Cartoes({ children }: { children: ReactNode }) {
  return <div className="cards">{children}</div>;
}

export function Barra({ valor, maximo }: { valor: number; maximo: number }) {
  const largura = maximo > 0 ? Math.max(0, Math.min(100, (100 * valor) / maximo)) : 0;
  return (
    <div className="trilho" aria-hidden="true">
      <div className="barra" style={{ width: `${largura}%` }} />
    </div>
  );
}

export function Tabela({ legenda, children }: { legenda: string; children: ReactNode }) {
  return (
    <div className="rolagem">
      <table>
        <caption>{legenda}</caption>
        {children}
      </table>
    </div>
  );
}

export function Vazio({ children }: { children: ReactNode }) {
  return <p className="vazio">{children}</p>;
}

export function Secao({ titulo, children }: { titulo: string; children: ReactNode }) {
  return (
    <section className="secao">
      <h2>{titulo}</h2>
      {children}
    </section>
  );
}
