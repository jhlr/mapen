import Link from "next/link";
import type { Alerta, Economia, Previsao, ResumoModelos } from "../lib/api/tipos";
import { num, pct } from "../lib/dominio/formatacao";
import {
  ALERTAS_POR_PAGINA, TIPOS_ALERTA, dia, faixaDeItens, hrefAlertas, kw, linhasAlertas, linhasEconomia, linhasMae,
  linhasMase, nomeFeature, nomeGrupo, nomeMetodoCurto, nomePrevisor, nomeTipo, pp, resumosMetodos, textoAvisoD7, textoVitorias,
  type FiltrosAlertasUrl,
} from "../lib/dominio/resultadosM3";
import { Aviso, Secao, Tabela, Vazio } from "./Basicos";

/** Marcador textual (nunca so cor) para baseline fraca. */
export const MarcaFraca = () => <span className="selo fraca" title="Baseline fraca: pouco histórico de treino para este equipamento">baseline fraca</span>;

export function Indisponivel({ o }: { o: string }) {
  return <Vazio>{`Os resultados de ${o} não estão disponíveis para esta empresa.`}</Vazio>;
}

// ---------- Modelos ----------
export function GraficoMae({ resumo }: { resumo: ResumoModelos }) {
  const { linhas } = linhasMae(resumo);
  if (linhas.length === 0) return <Vazio>Sem MAE por equipamento.</Vazio>;
  return (
    <div className="grafico-html" role="group" aria-label="MAE por equipamento: baseline sazonal contra LightGBM (lag 1), menor é melhor">
      <ul className="legenda" aria-hidden="true">
        <li><span className="amostra cor-base" />Baseline sazonal</li>
        <li><span className="amostra cor-lgbm" />LightGBM (usa lag 1)</li>
      </ul>
      <ol className="pares">
        {linhas.map((l) => (
          <li key={l.equipamento}>
            <span className="nome">{l.equipamento}{l.fraca && <> <MarcaFraca /></>}</span>
            <span className="trilhos">
              <span className="trilho"><span className="barra base" style={{ width: `${l.larguraBaseline}%` }} /></span>
              <span className="trilho"><span className="barra" style={{ width: `${l.larguraLightgbm}%` }} /></span>
            </span>
            <span className="val">{num(l.mae_baseline_kw, 3)} → {num(l.mae_lightgbm_kw, 3)} kW <span className="nota">({pct(l.melhora_pct)} menor)</span></span>
          </li>
        ))}
      </ol>
    </div>
  );
}

export function SecaoModelos({ r }: { r: ResumoModelos }) {
  const { dados, mae, shap, benchmark_sintetico: bench, baseline_fraca: fraca } = r;
  const d7 = shap === null ? null : textoAvisoD7(shap.aviso_d7);
  return (
    <>
      <Aviso tom="atencao" titulo="Escopo dos resultados">{r.rotulo}</Aviso>

      {dados !== null && (
        <Secao titulo="Dados">
          <dl className="fatos">
            <div><dt>Fonte</dt><dd>{dados.fonte}</dd></div>
            <div><dt>Período</dt><dd>{dia(dados.periodo.inicio)} a {dia(dados.periodo.fim)}</dd></div>
            <div><dt>Treino</dt><dd>{dia(dados.treino.inicio)} a {dia(dados.treino.fim)}</dd></div>
            <div><dt>Reservado (teste)</dt><dd>{dia(dados.reservado.inicio)} a {dia(dados.reservado.fim)}</dd></div>
            <div><dt>Equipamentos</dt><dd>{num(dados.equipamentos_modelados, 0)} modelados de {num(dados.equipamentos_no_andar, 0)} no andar</dd></div>
            <div><dt>Sem carga (fora do modelo)</dt><dd>{dados.equipamentos_sem_carga.length === 0 ? "nenhum" : dados.equipamentos_sem_carga.join(", ")}</dd></div>
            <div><dt>Linhas de minuto</dt><dd>{num(dados.linhas_minuto, 0)}</dd></div>
          </dl>
        </Secao>
      )}

      {mae !== null && (
        <Secao titulo="Erro (MAE): baseline sazonal contra LightGBM">
          <Aviso tom="atencao" titulo="Nowcast, não previsão">
            O LightGBM usa o consumo da hora anterior (lag 1): é um nowcast, não uma previsão. {mae.ressalva_nowcast}
          </Aviso>
          <div className="cards">
            <div className="card"><span className="rotulo">MAE baseline sazonal</span><b>{kw(mae.baseline_sazonal_kw, 3)}</b></div>
            <div className="card"><span className="rotulo">MAE LightGBM (lag 1)</span><b>{kw(mae.lightgbm_kw, 3)}</b></div>
            <div className="card"><span className="rotulo">Melhora mediana</span><b>{pct(mae.melhora_mediana_pct)}</b><span className="nota">{mae.equipamentos_lightgbm_melhor} de {mae.equipamentos_total} equipamentos melhores</span></div>
            <div className="card"><span className="rotulo">Horas de teste</span><b>{num(mae.horas_teste, 0)}</b></div>
          </div>
          <h3>Por equipamento (barra menor é melhor)</h3>
          <GraficoMae resumo={r} />
        </Secao>
      )}

      {shap !== null && (
        <Secao titulo="O que o LightGBM usa (SHAP)">
          {d7 !== null && <Aviso tom="atencao" titulo="Aviso D7: dependência de uma feature">{d7}</Aviso>}
          <div className="empilhada" role="img" aria-label={`Importância SHAP: calendário ${pct(shap.calendario_pct)}, histórico (lag e janelas) ${pct(shap.historico_pct)}`}>
            <span className="seg cal" style={{ flexGrow: shap.calendario_pct }}>Calendário {pct(shap.calendario_pct)}</span>
            <span className="seg his" style={{ flexGrow: shap.historico_pct }}>Lag e janelas {pct(shap.historico_pct)}</span>
          </div>
          <p className="dica">Calculado em {num(shap.horas_equipamento, 0)} horas de equipamento. Calendário: hora, dia da semana, feriado. Lag e janelas: consumo anterior.</p>
          <Tabela legenda="Importância SHAP por feature (agregada)" empilhar>
            <thead><tr><th>Feature</th><th className="n">Parcela</th></tr></thead>
            <tbody>
              {shap.por_feature.map((f) => <tr key={f.feature}><td data-label="Feature"><div className="c">{nomeFeature(f.feature)}</div></td><td className="n" data-label="Parcela"><div className="c">{pct(f.pct)}</div></td></tr>)}
            </tbody>
          </Tabela>
        </Secao>
      )}

      {bench !== null && (
        <Secao titulo="Benchmark de injeção">
          <Aviso tom="atencao" titulo="Benchmark sintético">{bench.rotulo} Taxas medidas em anomalias injetadas ({bench.eventos_por_tipo_por_equipamento} por tipo por equipamento, semente {bench.semente}, limiar z {num(bench.limiar_z, 1)}).</Aviso>
          <Tabela legenda="Taxa de detecção sintética e falso alarme sobre horas sem injeção" empilhar>
            <thead>
              <tr><th>Detector</th><th className="n">Detecção total (sintética)</th>{bench.detectores[0]?.por_tipo.map((t) => <th key={t.tipo} className="n">{nomeTipo(t.tipo)}</th>)}<th className="n">Falso alarme (sintético)</th></tr>
            </thead>
            <tbody>
              {bench.detectores.map((x) => (
                <tr key={x.detector}>
                  <td data-label="Detector"><div className="c">{nomeTipo(x.detector)}</div></td>
                  <td className="n" data-label="Detecção total (sintética)"><div className="c">{pct(x.taxa_deteccao_pct)} ({x.total_detectados}/{x.total_eventos})</div></td>
                  {x.por_tipo.map((t) => <td key={t.tipo} className="n" data-label={nomeTipo(t.tipo)}><div className="c">{pct(t.taxa_deteccao_pct)} ({t.detectados}/{t.eventos})</div></td>)}
                  <td className="n" data-label="Falso alarme (sintético)"><div className="c">{pct(x.taxa_falso_alarme_pct)} ({x.falso_alarme_horas}/{num(x.horas_base, 0)} h)</div></td>
                </tr>
              ))}
            </tbody>
          </Tabela>
        </Secao>
      )}

      {fraca !== null && (
        <Secao titulo="Baseline fraca">
          <p className="dica">Critério: {fraca.criterio}. O treino tem {fraca.semanas_completas_treino} semanas completas.</p>
          {fraca.equipamentos.length === 0 ? <p>Nenhum equipamento marcado.</p> : <p>{fraca.equipamentos.map((e) => <span key={e}>{e} <MarcaFraca /> </span>)}</p>}
        </Secao>
      )}
    </>
  );
}

// ---------- Alertas ----------
export function FiltrosAlertas({ f, equipamentos }: { f: FiltrosAlertasUrl; equipamentos: readonly string[] }) {
  return (
    <form className="form filtros" method="get" action="/alertas">
      <label className="campo"><span className="campo-rotulo">Equipamento</span>
        <select name="equipamento" defaultValue={f.equipamento ?? ""}>
          <option value="">Todos</option>
          {equipamentos.map((e) => <option key={e} value={e}>{e}</option>)}
        </select>
      </label>
      <label className="campo"><span className="campo-rotulo">Tipo</span>
        <select name="tipo" defaultValue={f.tipo ?? ""}>
          <option value="">Todos</option>
          {TIPOS_ALERTA.map((t) => <option key={t} value={t}>{nomeTipo(t)}</option>)}
        </select>
      </label>
      <label className="campo"><span className="campo-rotulo">De</span><input type="date" name="de" defaultValue={f.de ?? ""} /></label>
      <label className="campo"><span className="campo-rotulo">Até (inclusive)</span><input type="date" name="ate" defaultValue={f.ate ?? ""} /></label>
      <div className="acoes largo">
        <button type="submit">Filtrar</button>
        <Link className="botao-link" href="/alertas">Limpar filtros</Link>
      </div>
    </form>
  );
}

function Explicacao({ a }: { a: Alerta }) {
  const e = a.explicacao;
  return (
    <>
      <span className="nw">z = {num(e.z, 2)}</span>
      {e.top_shap !== null && (
        <ul className="shap">
          {e.top_shap.map((s) => <li key={s.feature}>{nomeFeature(s.feature)} <span className="nota">({s.shap > 0 ? "+" : "−"}{num(Math.abs(s.shap), 2)} kW)</span></li>)}
        </ul>
      )}
    </>
  );
}

export function TabelaAlertas({ itens }: { itens: Alerta[] }) {
  const linhas = linhasAlertas(itens);
  return (
    <Tabela legenda="Alertas (candidatos, sem rótulo real)" empilhar>
      <thead>
        <tr><th>Quando (Recife)</th><th>Equipamento</th><th>Tipo</th><th>Esperado e observado</th><th>Explicação</th><th>Situação</th></tr>
      </thead>
      <tbody>
        {linhas.map(({ chave, alerta: a, larguraEsperado, larguraObservado, desvio }) => (
          <tr key={chave}>
            <td className="nw" data-label="Quando"><div className="c">{a.timestamp.slice(8, 10)}/{a.timestamp.slice(5, 7)}/{a.timestamp.slice(0, 4)} {a.timestamp.slice(11, 16)}</div></td>
            <td data-label="Equipamento"><div className="c">{a.equipamento}{a.baseline_fraca && <> <MarcaFraca /></>}</div></td>
            <td data-label="Tipo"><div className="c">{nomeTipo(a.tipo)}</div></td>
            <td className="det" data-label="Esperado e observado"><div className="c">
              <span className="par"><span className="rotulo">esperado</span><span className="trilho"><span className="barra base" style={{ width: `${larguraEsperado}%` }} /></span><span className="v">{kw(a.explicacao.esperado_kw)}</span></span>
              <span className="par"><span className="rotulo">observado</span><span className="trilho"><span className="barra" style={{ width: `${larguraObservado}%` }} /></span><span className="v">{kw(a.explicacao.observado_kw)}</span></span>
              <span className="nota">{desvio}</span>
            </div></td>
            <td data-label="Explicação"><div className="c"><Explicacao a={a} /></div></td>
            <td data-label="Situação"><div className="c"><span className="selo cand">{a.rotulo}</span></div></td>
          </tr>
        ))}
      </tbody>
    </Tabela>
  );
}

export function PaginacaoAlertas({ f, total, qtd, proximo }: { f: FiltrosAlertasUrl; total: number; qtd: number; proximo: number | null }) {
  const offset = (f.pagina - 1) * ALERTAS_POR_PAGINA;
  return (
    <div className="paginacao" role="navigation" aria-label="Paginação dos alertas">
      <span className="sub">{faixaDeItens(total, offset, qtd)}</span>
      <span className="acoes">
        {f.pagina > 1 ? <Link className="botao-link" href={hrefAlertas(f, f.pagina - 1)} rel="prev">Anterior</Link> : <span className="botao-link off" aria-disabled="true">Anterior</span>}
        {proximo !== null ? <Link className="botao-link" href={hrefAlertas(f, f.pagina + 1)} rel="next">Próxima</Link> : <span className="botao-link off" aria-disabled="true">Próxima</span>}
      </span>
    </div>
  );
}

// ---------- Economia ----------
export function SecaoEconomia({ e }: { e: Economia }) {
  const resumos = resumosMetodos(e);
  const linhas = linhasEconomia(e);
  return (
    <>
      <div className={`banner-metodo ${resumos.length > 0 && resumos.every((r) => r.atendida) ? "atendida" : "nao"}`} role="alert">
        <strong>{e.valida_metodo_nao_economia_real ? "Valida o MÉTODO, não é economia real." : "Resultado de validação do método."}</strong>
        {resumos.map((r) => <p key={r.metodo} className="veredito"><b>{r.nome}: {r.titulo}.</b> <span className="nota">{num(r.veredito.dentro_da_tolerancia, 0)} de {num(r.veredito.equipamentos, 0)} equipamentos dentro da tolerância.</span></p>)}
      </div>
      {e.reducao_sintetica !== null && e.periodo_antes !== null && e.periodo_depois !== null && (
        <p className="sub">
          Redução sintética de {pct(e.reducao_sintetica.fracao_pct)} injetada em {e.reducao_sintetica.equipamento} a partir de {dia(e.reducao_sintetica.a_partir_de)}.
          Antes: {dia(e.periodo_antes.inicio)} a {dia(e.periodo_antes.fim)}. Depois: {dia(e.periodo_depois.inicio)} a {dia(e.periodo_depois.fim)}.
          {resumos.length > 1 && " Os dois métodos recebem exatamente os mesmos dados; o grupo-controle usa equipamentos sem intervenção para descontar a deriva de carga comum."}
        </p>
      )}
      <Secao titulo="Métodos lado a lado">
        {resumos.length === 0 ? <Vazio>Sem resultados de antes e depois.</Vazio> : (
          <Tabela legenda="Resumo de cada método ao recuperar a redução sintética injetada" empilhar>
            <thead>
              <tr><th>Método</th><th className="n">Dentro da tolerância</th><th className="n">Alvo</th><th className="n">Erro absoluto mediano</th><th className="n">Erro absoluto máximo</th><th>Resultado</th></tr>
            </thead>
            <tbody>
              {resumos.map(({ metodo, nome, atendida, veredito: v }) => (
                <tr key={metodo}>
                  <td data-label="Método"><div className="c">{nome}</div></td>
                  <td className="n" data-label="Dentro da tolerância"><div className="c">{num(v.dentro_da_tolerancia, 0)} de {num(v.equipamentos, 0)}</div></td>
                  <td className="n" data-label="Alvo"><div className="c">{v.alvo_recuperado_pct === null ? "sem estimativa" : pct(v.alvo_recuperado_pct)} <span className="nota">(injetado {pct(v.alvo_injetado_pct)}, {v.alvo_dentro_da_tolerancia ? "dentro" : "fora"})</span></div></td>
                  <td className="n" data-label="Erro absoluto mediano"><div className="c">{v.erro_abs_mediano_pp === null ? "sem estimativa" : `${num(v.erro_abs_mediano_pp, 1)} pp`}</div></td>
                  <td className="n" data-label="Erro absoluto máximo"><div className="c">{v.erro_abs_maximo_pp === null ? "sem estimativa" : `${num(v.erro_abs_maximo_pp, 1)} pp`}</div></td>
                  <td data-label="Resultado"><div className="c"><span className={`selo ${atendida ? "dentro" : "fora"}`}>{atendida ? "tolerância atendida" : "tolerância não atendida"}</span></div></td>
                </tr>
              ))}
            </tbody>
          </Tabela>
        )}
      </Secao>
      <Secao titulo="Antes e depois, por equipamento">
        {linhas.length === 0 ? <Vazio>Sem equipamentos.</Vazio> : (
          <Tabela legenda="Redução injetada contra redução recuperada por cada método, em % do consumo" empilhar>
            <thead>
              <tr>
                <th>Equipamento</th><th className="n">Injetado</th>
                {e.metodos.map((m) => <th key={m.metodo} className="n">{nomeMetodoCurto(m.metodo)}: recuperado (erro)</th>)}
                {e.metodos.some((m) => m.equipamentos.some((x) => x.controles.length > 0)) && <th>Controles usados</th>}
              </tr>
            </thead>
            <tbody>
              {linhas.map((l) => (
                <tr key={l.equipamento}>
                  <td data-label="Equipamento"><div className="c">{l.equipamento}{l.alvo && <> <span className="selo alvo">alvo da injeção</span></>}{l.fraca && <> <MarcaFraca /></>}</div></td>
                  <td className="n" data-label="Injetado"><div className="c">{pct(l.injetado_pct)}</div></td>
                  {l.celulas.map((c) => (
                    <td key={c.metodo} className="n" data-label={`${nomeMetodoCurto(c.metodo)}: recuperado (erro)`}><div className="c">
                      {c.recuperado === null ? "sem estimativa" : `${pct(c.recuperado)} (${c.erro_pp === null ? "sem erro" : pp(c.erro_pp)})`}{" "}
                      <span className={`selo ${c.fora ? "fora" : "dentro"}`}>{c.fora ? "fora da tolerância" : "dentro da tolerância"}</span>
                    </div></td>
                  ))}
                  {e.metodos.some((m) => m.equipamentos.some((x) => x.controles.length > 0)) && (
                    <td data-label="Controles usados"><div className="c">{l.celulas.flatMap((c) => c.controles).join(", ") || "nenhum"}</div></td>
                  )}
                </tr>
              ))}
            </tbody>
          </Tabela>
        )}
      </Secao>
    </>
  );
}

// ---------- Previsao ----------
const mae = (v: number | null): string => (v === null ? "sem estimativa" : kw(v, 4));
const mase = (v: number | null): string => (v === null ? "sem estimativa" : num(v, 3));

export function SecaoPrevisao({ p }: { p: Previsao }) {
  const linhas = linhasMase(p);
  const shap = p.shap_lightgbm;
  const bench = p.benchmark_sintetico;
  const total = p.equipamentos.length;
  return (
    <>
      <Aviso tom="atencao" titulo="Escopo dos resultados">{p.rotulo}</Aviso>

      {p.treino !== null && p.reservado !== null && (
        <Secao titulo="Protocolo">
          <dl className="fatos">
            <div><dt>Origem da previsão</dt><dd>meia-noite, horizonte de {p.horizonte_h} h</dd></div>
            <div><dt>Defasagem mínima</dt><dd>{p.defasagem_minima_h} h (nenhuma feature usa consumo mais recente)</dd></div>
            <div><dt>Treino</dt><dd>{dia(p.treino.inicio)} a {dia(p.treino.fim)}</dd></div>
            <div><dt>Reservado (teste)</dt><dd>{dia(p.reservado.inicio)} a {dia(p.reservado.fim)}</dd></div>
            <div><dt>Dobras walk-forward</dt><dd>{p.dobras_walk_forward}</dd></div>
            <div><dt>Referência do MASE</dt><dd>{p.referencia_mase === null ? "n/d" : nomePrevisor(p.referencia_mase)}</dd></div>
            <div><dt>Equipamentos</dt><dd>{total} avaliados{p.sem_carga.length > 0 ? `; sem carga: ${p.sem_carga.join(", ")}` : ""}</dd></div>
          </dl>
        </Secao>
      )}

      {p.decisao !== null && (
        <div className="banner-metodo atendida" role="note">
          <strong>Previsor adotado: {nomePrevisor(p.decisao.adotado)}</strong>
          <p className="sub-banner">{p.decisao.motivo}</p>
          <p className="sub-banner">
            {p.decisao.passaram_regra_de_ganho.length === 0
              ? "Nenhum candidato passou na regra de ganho pré-registrada (mediana de MASE pelo menos 10% menor que a do naive de 168 h e vitória em pelo menos 12 de 19 equipamentos)."
              : `Passaram na regra de ganho: ${p.decisao.passaram_regra_de_ganho.map(nomePrevisor).join(", ")}.`}
          </p>
        </div>
      )}

      <Secao titulo="Previsores no período reservado">
        {p.modelos.length === 0 ? <Vazio>Sem previsores.</Vazio> : (
          <Tabela legenda="Erro de cada previsor do dia seguinte no período reservado; MASE menor é melhor e 1 é o erro do naive de 168 h no treino" empilhar>
            <thead>
              <tr><th>Previsor</th><th className="n">MAE agregado</th><th className="n">Mediana do MASE</th><th className="n">Mediana do MASE (dobras)</th><th className="n">Vitórias sobre o naive 168 h</th><th className="n">Melhor em</th></tr>
            </thead>
            <tbody>
              {p.modelos.map((m) => (
                <tr key={m.modelo}>
                  <td data-label="Previsor"><div className="c">{nomePrevisor(m.modelo)}{m.adotado && <> <span className="selo dentro">adotado</span></>}</div></td>
                  <td className="n" data-label="MAE agregado"><div className="c">{mae(m.mae_agregado_kw)}</div></td>
                  <td className="n" data-label="Mediana do MASE"><div className="c">{mase(m.mediana_mase_reservado)}</div></td>
                  <td className="n" data-label="Mediana do MASE (dobras)"><div className="c">{mase(m.mediana_mase_desenvolvimento)}</div></td>
                  <td className="n" data-label="Vitórias sobre o naive 168 h"><div className="c">{textoVitorias(m, total)}</div></td>
                  <td className="n" data-label="Melhor em"><div className="c">{num(m.vitorias_melhor_de_todos, 0)} de {num(total, 0)}</div></td>
                </tr>
              ))}
            </tbody>
          </Tabela>
        )}
      </Secao>

      <Secao titulo="MASE por equipamento">
        {linhas.length === 0 ? <Vazio>Sem equipamentos.</Vazio> : (
          <Tabela legenda="MASE de cada previsor por equipamento no período reservado; o menor da linha está marcado" empilhar>
            <thead>
              <tr><th>Equipamento</th>{p.modelos.map((m) => <th key={m.modelo} className="n">{nomePrevisor(m.modelo)}</th>)}</tr>
            </thead>
            <tbody>
              {linhas.map((l) => (
                <tr key={l.equipamento}>
                  <td data-label="Equipamento"><div className="c">{l.equipamento}</div></td>
                  {l.celulas.map((c) => (
                    <td key={c.modelo} className="n" data-label={nomePrevisor(c.modelo)}><div className="c">
                      {c.melhor ? <b>{mase(c.mase)} <span className="nota">(menor)</span></b> : mase(c.mase)}
                    </div></td>
                  ))}
                </tr>
              ))}
            </tbody>
          </Tabela>
        )}
      </Secao>

      {shap !== null && (
        <Secao titulo="O que o LightGBM de previsão usa (SHAP)">
          {shap.feature_dominante !== null
            ? <Aviso tom="atencao" titulo="Aviso D7: dependência de uma feature">A feature {nomeFeature(shap.feature_dominante)} concentra mais de metade da importância SHAP; {shap.equipamentos_com_feature_dominante.length} equipamento(s) têm uma feature dominante.</Aviso>
            : <p className="dica">Nenhuma feature passa de 50% da importância no agregado; em {shap.equipamentos_com_feature_dominante.length} equipamento(s) uma feature isolada passa{shap.equipamentos_com_feature_dominante.length > 0 ? `: ${shap.equipamentos_com_feature_dominante.join(", ")}` : ""}. O LightGBM não passou na regra de ganho, então esta atribuição explica um modelo que não foi adotado.</p>}
          <ul className="legenda">
            {Object.entries(shap.por_grupo_pct).map(([g, v]) => <li key={g}>{nomeGrupo(g)}: {v === null ? "sem estimativa" : pct(v)}</li>)}
          </ul>
          <Tabela legenda="Importância SHAP por feature do LightGBM de previsão (agregada)" empilhar>
            <thead><tr><th>Feature</th><th className="n">Parcela</th></tr></thead>
            <tbody>
              {Object.entries(shap.por_feature_pct).sort(([, a], [, b]) => (b ?? 0) - (a ?? 0)).map(([f, v]) => (
                <tr key={f}><td data-label="Feature"><div className="c">{nomeFeature(f)}</div></td><td className="n" data-label="Parcela"><div className="c">{v === null ? "sem estimativa" : pct(v)}</div></td></tr>
              ))}
            </tbody>
          </Tabela>
          <p className="dica">Calculado em {num(shap.horas, 0)} horas de equipamento.</p>
        </Secao>
      )}

      {bench !== null && (
        <Secao titulo="Benchmark de injeção com o previsor adotado">
          <Aviso tom="atencao" titulo="Benchmark sintético">Taxas medidas em anomalias injetadas ({bench.eventos_por_tipo_por_equipamento} por tipo por equipamento, semente {bench.semente}, limiar z {num(bench.limiar_z, 1)}), com o resíduo de {nomePrevisor(bench.previsor)}. Não é precisão nem recall em dado real.</Aviso>
          <Tabela legenda="Detecção sintética por tipo de anomalia e falso alarme sobre horas sem injeção" empilhar>
            <thead>
              <tr>{bench.por_tipo.map((t) => <th key={t.tipo} className="n">{nomeTipo(t.tipo)}</th>)}<th className="n">Total</th><th className="n">Falso alarme (sintético)</th></tr>
            </thead>
            <tbody>
              <tr>
                {bench.por_tipo.map((t) => <td key={t.tipo} className="n" data-label={nomeTipo(t.tipo)}><div className="c">{pct(t.taxa_deteccao_pct)} ({t.detectados}/{t.eventos})</div></td>)}
                <td className="n" data-label="Total"><div className="c">{bench.taxa_deteccao_pct === null ? "sem estimativa" : pct(bench.taxa_deteccao_pct)} ({bench.total_detectados}/{bench.total_eventos})</div></td>
                <td className="n" data-label="Falso alarme (sintético)"><div className="c">{bench.taxa_falso_alarme_pct === null ? "sem estimativa" : pct(bench.taxa_falso_alarme_pct)} ({bench.falso_alarme_horas}/{num(bench.horas_base, 0)} h)</div></td>
              </tr>
            </tbody>
          </Tabela>
        </Secao>
      )}

      {p.avisos.length > 0 && <Aviso tom="info" titulo="Avisos do estudo">{p.avisos.join(" ")}</Aviso>}
    </>
  );
}
