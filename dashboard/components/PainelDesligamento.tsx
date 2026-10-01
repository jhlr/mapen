"use client";

import { useActionState, useEffect, useState } from "react";
import { acaoDesligar } from "../actions/desligamento";
import type { EstadoDesligamento } from "../actions/estado";
import type { Equipamento, Regra } from "../lib/api";
import { explicarMotivo } from "../lib/dominio/seguranca";
import { Aviso } from "./Basicos";
import { Campo } from "./Campo";

const NONCE_LIVRE = new Set(["assinatura_invalida", "validade_vencida", "dispositivo_divergente"]);
const pad = (n: number): string => String(n).padStart(2, "0");
function utcDaquiA(minutos: number): string {
  const d = new Date(Date.now() + minutos * 60_000);
  return `${d.getUTCFullYear()}-${pad(d.getUTCMonth() + 1)}-${pad(d.getUTCDate())}T${pad(d.getUTCHours())}:${pad(d.getUTCMinutes())}:${pad(d.getUTCSeconds())}`;
}
const epoch = (utc: string): string => (utc === "" ? "?" : String(Math.floor(Date.parse(`${utc}Z`) / 1000)));

export function PainelDesligamento({
  empresa, equipamentos, regras,
}: { empresa: string; equipamentos: Equipamento[]; regras: Regra[] }) {
  const [estado, enviar, pendente] = useActionState(acaoDesligar, null);
  const [equip, setEquip] = useState(equipamentos[0]?.id ?? "");
  const [acao, setAcao] = useState("desligar");
  const [nonce, setNonce] = useState("");
  const [validade, setValidade] = useState("");
  const [assinatura, setAssinatura] = useState("");
  const [autorizado, setAutorizado] = useState("");
  const [regra, setRegra] = useState("");
  useEffect(() => {
    setNonce(crypto.randomUUID());
    setValidade(utcDaquiA(5));
  }, []);
  // O nonce e consumido quando o comando e autentico (aceito ou rejeitado por regra de negocio);
  // so nesses casos gera outro e pede nova assinatura.
  useEffect(() => {
    if (estado?.tipo === "resposta" && !NONCE_LIVRE.has(estado.resposta.motivo ?? "")) {
      setNonce(crypto.randomUUID());
      setAssinatura("");
    }
  }, [estado]);
  const eq = equipamentos.find((e) => e.id === equip);
  const device = eq?.sensor_id ?? "";
  const regrasDoEquip = regras.filter((r) => r.equipamento_id === equip);

  return (
    <>
      <form action={enviar} className="form">
        <input type="hidden" name="empresa" value={empresa} />
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
        <Campo rotulo="Validade (UTC)" dica="Depois desse instante o comando é recusado.">
          <input name="validade" type="datetime-local" step={1} value={validade} onChange={(e) => setValidade(e.target.value)} required />
        </Campo>
        <Campo
          rotulo="Assinatura HMAC-SHA256 (hex)"
          dica={`O dashboard não tem a chave. Quem emite assina a mensagem ${device}|${acao}|${nonce}|${epoch(validade)} com a chave do dispositivo.`}
        >
          <input name="assinatura" value={assinatura} onChange={(e) => setAssinatura(e.target.value)} required autoComplete="off" spellCheck={false} placeholder="64 caracteres hexadecimais" />
        </Campo>
        <Campo rotulo="Autorizado por" dica="Obrigatório. Sem isso a API rejeita com sem_autorizacao.">
          <input name="autorizado_por" value={autorizado} onChange={(e) => setAutorizado(e.target.value)} placeholder="nome ou e-mail" />
        </Campo>
        <Campo rotulo="Regra de origem (opcional)">
          <select name="regra_id" value={regra} onChange={(e) => setRegra(e.target.value)}>
            <option value="">nenhuma (pedido manual)</option>
            {regrasDoEquip.map((r) => <option key={r.id} value={r.id}>{r.cron} ({r.ativo ? "ativa" : "inativa"})</option>)}
          </select>
        </Campo>
        <div className="acoes">
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
