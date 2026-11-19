import { cookie, redirect } from "../../lib/dashboard.js";

export async function onRequestGet() {
  return redirect("/admin", { "Set-Cookie": cookie("pk_session", "", 0) });
}
