import Link from "next/link";
import { Aviso, Cabecalho, Vazio } from "../../components/Basicos";
import { FiltrosAlertas, Indisponivel, PaginacaoAlertas, TabelaAlertas } from "../../components/ResultadosM3";
import { listarAlertas, resumoModelos } from "../../lib/api";
import { type Params } from "../../lib/dominio/parametros";
import { hrefAlertas, lerFiltrosAlertas, paraApi } from "../../lib/dominio/resultadosM3";

export const dynamic = "force-dynamic";

export default async function Alertas({ searchParams }: { searchParams: Params }) {
  // Os equipamentos do filtro vem do resumo dos modelos (os 19 modelados); valor fora da lista e descartado.
  const equipamentos = (await resumoModelos()).mae?.por_equipamento.map((l) => l.equipamento) ?? [];
  const filtros = lerFiltrosAlertas(await searchParams, equipamentos);
  const pagina = await listarAlertas(paraApi(filtros));
  return (
    <>
      <Cabecalho titulo="Alertas" subtitulo={pagina.aviso} />
      {filtros.erro !== undefined && <Aviso tom="atencao">{filtros.erro}</Aviso>}
      <FiltrosAlertas f={filtros} equipamentos={equipamentos} />
      {!pagina.disponivel ? <Indisponivel o="alertas" /> : pagina.itens.length === 0 ? <Vazio>{filtros.pagina > 1 ? <>Nenhum alerta nesta página. <Link href={hrefAlertas(filtros, 1)}>Voltar à primeira página</Link></> : "Nenhum alerta para estes filtros."}</Vazio> : (
        <>
          <TabelaAlertas itens={pagina.itens} />
          <PaginacaoAlertas f={filtros} total={pagina.total} qtd={pagina.itens.length} proximo={pagina.proximo_offset} />
        </>
      )}
    </>
  );
}
