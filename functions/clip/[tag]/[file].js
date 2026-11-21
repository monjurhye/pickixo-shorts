// GET /clip/<clips-YYYY-MM-DD>/<name>.mp4 -> streams the Short kept as a GitHub Release asset
// (pipeline/clips.py). Instagram and Threads fetch the video from this public URL.
const REPO = "monjurhye/pickixo-shorts";

async function handle(context) {
  const { tag, file } = context.params;
  if (!/^clips-\d{4}-\d{2}-\d{2}$/.test(tag) || !/^[a-z0-9-]{1,100}\.mp4$/.test(file)) return new Response("Not found", { status: 404 });
  const headers = { "User-Agent": "pickixo-clip" };
  const range = context.request.headers.get("Range");
  if (range) headers.Range = range;
  const r = await fetch(`https://github.com/${REPO}/releases/download/${tag}/${file}`, { headers, redirect: "follow" });
  if (!r.ok && r.status !== 206) return new Response("Not found", { status: 404 });
  const h = new Headers({ "Content-Type": "video/mp4", "Accept-Ranges": "bytes", "Cache-Control": "public, max-age=86400" });
  for (const k of ["Content-Length", "Content-Range", "ETag", "Last-Modified"]) if (r.headers.get(k)) h.set(k, r.headers.get(k));
  return new Response(context.request.method === "HEAD" ? null : r.body, { status: r.status, headers: h });
}
export const onRequestGet = handle;
export const onRequestHead = handle;
