// Shared helpers for the channel dashboard (Cloudflare Pages Functions).
// Env (Pages > Settings > Variables and Secrets):
//   GOOGLE_CLIENT_ID      Web OAuth client id (plain)
//   GOOGLE_CLIENT_SECRET  Web OAuth client secret (encrypted)
//   OWNER_EMAILS          comma-separated Google emails allowed to sign in (plain)
//   PIPELINE_KEY          shared key the GitHub pipeline sends (encrypted)
// KV binding: CHANNELS_KV

export const GOOGLE_AUTH = "https://accounts.google.com/o/oauth2/v2/auth";
export const GOOGLE_TOKEN = "https://oauth2.googleapis.com/token";
export const YT_SCOPES =
  "openid email https://www.googleapis.com/auth/youtube.upload https://www.googleapis.com/auth/youtube.readonly";

const enc = new TextEncoder();

function b64url(bytes) {
  let s = btoa(String.fromCharCode(...new Uint8Array(bytes)));
  return s.replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}
function b64urlDecode(s) {
  s = s.replace(/-/g, "+").replace(/_/g, "/");
  while (s.length % 4) s += "=";
  return Uint8Array.from(atob(s), (c) => c.charCodeAt(0));
}

async function hmacKey(env) {
  if (!env.PIPELINE_KEY) throw new Error("PIPELINE_KEY not configured");
  return crypto.subtle.importKey("raw", enc.encode("session:" + env.PIPELINE_KEY),
    { name: "HMAC", hash: "SHA-256" }, false, ["sign", "verify"]);
}

export async function sign(env, obj) {
  const body = b64url(enc.encode(JSON.stringify(obj)));
  const sig = await crypto.subtle.sign("HMAC", await hmacKey(env), enc.encode(body));
  return body + "." + b64url(sig);
}

export async function verify(env, token) {
  if (!token || !token.includes(".")) return null;
  const [body, sig] = token.split(".");
  const ok = await crypto.subtle.verify("HMAC", await hmacKey(env), b64urlDecode(sig), enc.encode(body));
  if (!ok) return null;
  const obj = JSON.parse(new TextDecoder().decode(b64urlDecode(body)));
  if (obj.exp && Date.now() > obj.exp) return null;
  return obj;
}

export function getCookie(request, name) {
  const raw = request.headers.get("Cookie") || "";
  for (const part of raw.split(/;\s*/)) {
    const i = part.indexOf("=");
    if (i > 0 && part.slice(0, i) === name) return decodeURIComponent(part.slice(i + 1));
  }
  return "";
}

export function cookie(name, value, maxAge) {
  return `${name}=${encodeURIComponent(value)}; Path=/; HttpOnly; Secure; SameSite=Lax; Max-Age=${maxAge}`;
}

export async function session(context) {
  return verify(context.env, getCookie(context.request, "pk_session"));
}

export function redirect(location, headers = {}) {
  return new Response(null, { status: 302, headers: { Location: location, ...headers } });
}

export function json(obj, status = 200) {
  return new Response(JSON.stringify(obj), {
    status, headers: { "Content-Type": "application/json", "Cache-Control": "no-store" },
  });
}

export function html(body, status = 200) {
  return new Response(body, {
    status, headers: { "Content-Type": "text/html; charset=utf-8", "Cache-Control": "no-store" },
  });
}

export function owners(env) {
  return (env.OWNER_EMAILS || "").split(",").map((s) => s.trim().toLowerCase()).filter(Boolean);
}

export function pipelineAuthorized(context) {
  const k = context.request.headers.get("X-Pipeline-Key") || "";
  return !!context.env.PIPELINE_KEY && k.length > 20 && k === context.env.PIPELINE_KEY;
}

export function callbackUrl(request) {
  return new URL("/auth/callback", request.url).toString();
}

export function randomId() {
  return b64url(crypto.getRandomValues(new Uint8Array(18)));
}

export function idTokenEmail(idToken) {
  try {
    const payload = JSON.parse(new TextDecoder().decode(b64urlDecode(idToken.split(".")[1])));
    return payload.email_verified ? String(payload.email || "").toLowerCase() : "";
  } catch (e) {
    return "";
  }
}

export async function channelList(context) {
  // channels.json is copied into the static site by site/build.py (no secrets in it)
  const r = await context.env.ASSETS.fetch(new URL("/channels.json", context.request.url));
  return r.ok ? (await r.json()).channels : [];
}

export async function getState(env) {
  const raw = await env.CHANNELS_KV.get("state");
  return raw ? JSON.parse(raw) : { paused: false, channels: {} };
}

export async function putState(env, st) {
  await env.CHANNELS_KV.put("state", JSON.stringify(st));
}

// refresh tokens live under their own keys, never in the state blob
export async function getRefresh(env, ch) {
  return env.CHANNELS_KV.get("refresh:" + ch);
}
export async function putRefresh(env, ch, token) {
  await env.CHANNELS_KV.put("refresh:" + ch, token);
}

export function esc(s) {
  return String(s ?? "").replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}
