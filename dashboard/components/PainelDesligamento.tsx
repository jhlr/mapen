"use client";

import { useActionState, useEffect, useState } from "react";
import { acaoDesligar } from "../actions/desligamento";
import type { EstadoDesligamento } from "../actions/estado";
import type { Equipamento, Regra } from "../lib/api";
import { epochSegundos, naivoRecife } from "../lib/dominio/fuso";
import { explicarMotivo } from "../lib/dominio/seguranca";
import { Aviso } from "./Basicos";
import { Campo } from "./Campo";

const NONCE_LIVRE = new Set([
  "assinatura_invalida", "validade_vencida", "dispositivo_divergente", "ttl_excessivo", "emissao_futura", "comando_malformado",
]);
const TTL_PADRAO_S = 60;

export function PainelDesligamento({ equipamentos, regras }: { equipamentos: Equipamento[]; regras: Regra[] }) {
  const [estado, enviar, pendente] = useActionState(acaoDesligar, null);
  const [equip, setEquip] = useState(equipamentos[0]?.id ?? "");
  const [acao, setAcao] = useState("desligar");
  const [nonce, setNonce] = useState("");
  const [emitido, setEmitido] = useState("");
  const [validade, setValidade] = useState("");
  const [assinatura, setAssinatura] = useState("");
  const [regra, setRegra] = useState("");
  const renovarHorarios = (): void => {
    const agora = Date.now();
    setEmitido(naivoRecife(agora));
    setValidade(naivoRecife(agora + TTL_PADRAO_S * 1000));
  };
  useEffect(() => {
    setNonce(crypto.randomUUID());
    renovarHorarios();
  }, []);
  // O nonce e consumido quando o comando e autentico (aceito ou rejeitado por regra de negocio);
  // so nesses casos gera outro e pede nova assinatura.
  useEffect(() => {
    if (estado?.tipo === "resposta" && !NONCE_LIVRE.has(estado.resposta.motivo ?? "")) {
      setNonce(crypto.randomUUID());
      setAssinatura("");
      renovarHorarios();
    }
  }, [estado]);
  const eq = equipamentos.find((e) => e.id === equip);
  const device = eq?.sensor_id ?? "";
  const regrasDoEquip = regras.filter((r) => r.equipamento_id === equip);
  const mensagem = JSON.stringify({
    acao, device_id: device, emitido_em: epochSegundos(emitido), empresa_id: "<empresa da chave>",
    equipamento_id: equip, nonce, validade: epochSegundos(validade),
  });

  return (
    <>
      <form action={enviar} className="form">
        <Campo rotulo="Equipamento">
          <select name="equipamento_id" value={equip} onChange={(e) => setEquip(e.target.value)} required>
            {equipamentos.map((e) => (
              <option key={e.id} value={e.id}>{e.nome}{e.critico ? " (crítico)" : ""}</option>
            ))}
          </select>
        </Campo>
        <Campo rotulo="Ação">
          <select name="acao" value={acao} onChange={(e) => setAcao(e.target.value)}>
            <option value="desligar">desligar</option>
            <option value="ligar">ligar (religar)</option>
          </select>
        </Campo>
        <Campo rotulo="Dispositivo (device_id)" dica="Deve ser o sensor do equipamento; a API recusa se divergir.">
          <input name="device_id" value={device} readOnly />
        </Campo>
        <Campo rotulo="Nonce" dica="Uso único por dispositivo.">
          <span className="linha">
            <input name="nonce" value={nonce} onChange={(e) => setNonce(e.target.value)} required />
            <button type="button" className="secundario" onClick={() => setNonce(crypto.randomUUID())}>Novo</button>
          </span>
        </Campo>
        <Campo rotulo="Emitido em (Recife, UTC-03:00)" dica="Até 5 s no futuro.">
          <input name="emitido_em" type="datetime-local" step={1} value={emitido} onChange={(e) => setEmitido(e.target.value)} required />
        </Campo>
        <Campo rotulo="Validade (Recife, UTC-03:00)" dica="No máximo 60 s depois da emissão.">
          <span className="linha">
            <input name="validade" type="datetime-local" step={1} value={validade} onChange={(e) => setValidade(e.target.value)} required />
            <button type="button" className="secundario" onClick={renovarHorarios}>Agora</button>
          </span>
        </Campo>
        <Campo rotulo="Regra de origem (opcional)" dica="Precisa ser uma regra ativa deste equipamento.">
          <select name="regra_id" value={regra} onChange={(e) => setRegra(e.target.value)}>
            <option value="">nenhuma (pedido manual)</option>
            {regrasDoEquip.map((r) => <option key={r.id} value={r.id}>{r.cron} ({r.ativo ? "ativa" : "inativa"})</option>)}
          </select>
        </Campo>
        <div className="largo">
          <Campo
            rotulo="Assinatura HMAC-SHA256 (hex)"
            dica="O dashboard não tem a chave do dispositivo. Quem emite assina, com a chave de comando dele, este JSON canônico (chaves ordenadas, sem espaços; instantes em epoch s):"
          >
            <input name="assinatura" value={assinatura} onChange={(e) => setAssinatura(e.target.value)} required autoComplete="off" spellCheck={false} placeholder="64 caracteres hexadecimais minúsculos" />
          </Campo>
          <code className="mensagem">{mensagem}</code>
          <p className="dica">Quem autoriza o pedido é o usuário da chave de API; não há campo &quot;autorizado por&quot;.</p>
        </div>
        <div className="acoes largo">
          <button type="submit" disabled={pendente || equipamentos.length === 0}>{pendente ? "Enviando..." : "Solicitar"}</button>
        </div>
      </form>
      <Resposta estado={estado} />
    </>
  );
}

function Resposta({ estado }: { estado: EstadoDesligamento }) {
  if (estado === null) return null;
  if (estado.tipo === "erro") return <Aviso tom="erro" titulo="Requisição não processada">{estado.mensagem}</Aviso>;
  const r = estado.resposta;
  return (
    <div className="resposta" role="status">
      <h3>Resposta da API</h3>
      <Aviso tom={r.aceito ? "info" : "erro"} titulo={r.aceito ? "Aceito" : "Rejeitado"}>
        {r.aceito
          ? `Comando "${estado.acao}" aceito para ${estado.equipamento}.`
          : r.motivo === null ? "Rejeitado sem motivo informado." : explicarMotivo(r.motivo)}
      </Aviso>
      <pre>{`HTTP ${estado.status}\n${JSON.stringify(r, null, 2)}`}</pre>
    </div>
  );
}
