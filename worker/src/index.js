// Cidadania · serviço de confirmação de e-mail
// Envia um código de 6 dígitos ao e-mail, confere o código e devolve um atestado assinado
// ("esta chave tem e-mail confirmado") para o app publicar na rede. O e-mail nunca é guardado
// em claro: só uma impressão (HMAC) dele, para garantir um e-mail por conta.
import { finalizeEvent, getPublicKey } from "nostr-tools/pure";
import { hexToBytes } from "nostr-tools/utils";

const ORIGENS = ["https://thephilosopherx.github.io", "http://localhost:8765"];
const APP_TAG = "cidadania-app-v1";
const VALIDADE_CODIGO = 15 * 60;          // segundos
const MAX_TENTATIVAS = 5;
const LIMITE_POR_EMAIL_HORA = 3;
const LIMITE_POR_IP_HORA = 10;

function cors(req) {
  const o = req.headers.get("Origin") || "";
  return {
    "Access-Control-Allow-Origin": ORIGENS.includes(o) ? o : ORIGENS[0],
    "Access-Control-Allow-Methods": "POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type",
    "Vary": "Origin",
  };
}
const json = (req, obj, status = 200) =>
  new Response(JSON.stringify(obj), { status, headers: { "Content-Type": "application/json", ...cors(req) } });

const normEmail = (e) => String(e || "").trim().toLowerCase();
const emailOk = (e) => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(e) && e.length <= 254;
const pkOk = (pk) => /^[0-9a-f]{64}$/.test(pk || "");

async function hmac(segredo, texto) {
  const k = await crypto.subtle.importKey("raw", new TextEncoder().encode(segredo), { name: "HMAC", hash: "SHA-256" }, false, ["sign"]);
  const sig = await crypto.subtle.sign("HMAC", k, new TextEncoder().encode(texto));
  return [...new Uint8Array(sig)].map((b) => b.toString(16).padStart(2, "0")).join("");
}
function codigo6() {
  const n = new Uint32Array(1);
  crypto.getRandomValues(n);
  return String(n[0] % 1000000).padStart(6, "0");
}
async function conta(env, chave, limite) {
  const n = parseInt((await env.KV.get(chave)) || "0", 10);
  if (n >= limite) return false;
  await env.KV.put(chave, String(n + 1), { expirationTtl: 3600 });
  return true;
}
function evento(env, sujeitoPk, conteudo) {
  return finalizeEvent({
    kind: 30078,
    created_at: Math.floor(Date.now() / 1000),
    tags: [["d", `cid:atesta:${sujeitoPk}`], ["t", APP_TAG], ["c", "atesta"]],
    content: JSON.stringify(conteudo),
  }, hexToBytes(env.ATTESTOR_SK));
}

async function enviarEmail(env, para, codigo) {
  const corpo = {
    sender: { email: env.REMETENTE_EMAIL, name: "Cidadania" },
    to: [{ email: para }],
    subject: `Seu código do Cidadania: ${codigo}`,
    textContent: `Seu código para confirmar este e-mail no app Cidadania é ${codigo}.\n\nEle vale por 15 minutos. Se você não pediu este código, ignore esta mensagem: ninguém conseguirá usar seu e-mail sem ele.\n\nCidadania · https://thephilosopherx.github.io/cidadania/`,
  };
  const r = await fetch("https://api.brevo.com/v3/smtp/email", {
    method: "POST",
    headers: { "api-key": env.BREVO_API_KEY, "Content-Type": "application/json", "Accept": "application/json" },
    body: JSON.stringify(corpo),
  });
  if (!r.ok) throw new Error(`envio falhou (${r.status})`);
}

async function inicio(req, env) {
  const { email, pk } = await req.json().catch(() => ({}));
  const e = normEmail(email);
  if (!emailOk(e) || !pkOk(pk)) return json(req, { erro: "Dados inválidos." }, 400);
  const h = await hmac(env.PEPPER, e);
  const ip = req.headers.get("CF-Connecting-IP") || "?";
  if (!(await conta(env, `rl:ip:${await hmac(env.PEPPER, ip)}`, LIMITE_POR_IP_HORA)))
    return json(req, { erro: "Muitos pedidos deste aparelho. Tente de novo em uma hora." }, 429);
  if (!(await conta(env, `rl:em:${h}`, LIMITE_POR_EMAIL_HORA)))
    return json(req, { erro: "Já enviamos vários códigos para este e-mail. Tente de novo em uma hora." }, 429);
  const c = codigo6();
  await env.KV.put(`pend:${h}`, JSON.stringify({ c, pk, t: 0 }), { expirationTtl: VALIDADE_CODIGO });
  try { await enviarEmail(env, e, c); }
  catch (x) { return json(req, { erro: "Não foi possível enviar o e-mail agora. Tente mais tarde." }, 502); }
  return json(req, { ok: true });
}

async function confirma(req, env) {
  const { email, pk, codigo } = await req.json().catch(() => ({}));
  const e = normEmail(email);
  if (!emailOk(e) || !pkOk(pk) || !/^\d{6}$/.test(String(codigo || ""))) return json(req, { erro: "Dados inválidos." }, 400);
  const h = await hmac(env.PEPPER, e);
  const pend = JSON.parse((await env.KV.get(`pend:${h}`)) || "null");
  if (!pend || pend.pk !== pk) return json(req, { erro: "Código expirado. Peça um novo." }, 410);
  if (pend.c !== String(codigo)) {
    pend.t += 1;
    if (pend.t >= MAX_TENTATIVAS) { await env.KV.delete(`pend:${h}`); return json(req, { erro: "Muitas tentativas. Peça um novo código." }, 429); }
    await env.KV.put(`pend:${h}`, JSON.stringify(pend), { expirationTtl: VALIDADE_CODIGO });
    return json(req, { erro: `Código incorreto. Restam ${MAX_TENTATIVAS - pend.t} tentativas.` }, 401);
  }
  await env.KV.delete(`pend:${h}`);
  // Um e-mail confirma uma única conta. Quem prova ter a caixa de entrada leva o vínculo;
  // a conta que tinha o vínculo antes perde o atestado.
  const antes = JSON.parse((await env.KV.get(`bind:${h}`)) || "null");
  await env.KV.put(`bind:${h}`, JSON.stringify({ pk, em: Date.now() }));
  const eventos = [evento(env, pk, { email: Date.now() })];
  if (antes && antes.pk !== pk) eventos.push(evento(env, antes.pk, { revogado: true, motivo: "e-mail confirmado em outra conta" }));
  return json(req, { ok: true, eventos, transferido: !!(antes && antes.pk !== pk) });
}

export default {
  async fetch(req, env) {
    if (req.method === "OPTIONS") return new Response(null, { headers: cors(req) });
    const url = new URL(req.url);
    try {
      if (req.method === "POST" && url.pathname === "/email/inicio") return await inicio(req, env);
      if (req.method === "POST" && url.pathname === "/email/confirma") return await confirma(req, env);
      if (url.pathname === "/") return json(req, { servico: "Cidadania · confirmação de e-mail", atestador: getPublicKey(hexToBytes(env.ATTESTOR_SK)) });
      return json(req, { erro: "Não encontrado." }, 404);
    } catch (x) {
      return json(req, { erro: "Erro interno." }, 500);
    }
  },
};
