import { Aviso, Cabecalho } from "../components/Basicos";

/** Renderizada com HTTP 401 quando a API recusa a chave ou quando MAPEN_API_KEY nao esta definida. */
export default function NaoAutenticado() {
  return (
    <>
      <Cabecalho titulo="Chave de API ausente ou recusada" subtitulo="A API respondeu 401 (não autenticado)." />
      <Aviso tom="erro" titulo="O dashboard não conseguiu se autenticar na API">
        <ol>
          <li>Defina <code>MAPEN_API_KEY</code> no servidor do dashboard (por exemplo em <code>dashboard/.env.local</code>), sem prefixo <code>NEXT_PUBLIC_</code>.</li>
          <li>A chave de demo é impressa uma vez no stdout da API (<code>[demo] empresa=demo chave_api=...</code>) ou fixada em <code>MAPEN_CHAVE_API_DEMO</code>; para outra empresa use o comando <code>criar-empresa</code> da CLI.</li>
          <li>Reinicie o dashboard depois de mudar a variável. A chave nunca vai para o navegador.</li>
        </ol>
      </Aviso>
    </>
  );
}
