"use client";

import { Aviso, Cabecalho } from "../components/Basicos";

export default function Erro({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  return (
    <>
      <Cabecalho titulo="Não foi possível carregar os dados" />
      <Aviso tom="erro" titulo="Falha ao falar com a API">
        Confira se a API está no ar (MAPEN_API_URL). Chave ausente ou recusada aparece em outra tela (401). O detalhe da falha fica no log do servidor{error.digest === undefined ? "" : ` (código ${error.digest})`}.
      </Aviso>
      <div className="acoes"><button type="button" onClick={reset}>Tentar de novo</button></div>
    </>
  );
}
