const $ = (id) => document.getElementById(id);
const money = (n) => (n == null ? "—" : Number(n).toLocaleString("en-IN", { style: "currency", currency: "INR" }));
const LABEL = { needs_review: "Needs review", pending_approval: "Awaiting approval", approved: "Approved", rejected: "Rejected" };
const FIELDS = [["vendor","Vendor"],["invoice_number","Invoice number"],["invoice_date","Invoice date"],["po_number","PO number"],["tax_id","Tax ID (GSTIN/VAT)"],["subtotal","Subtotal"],["tax","Tax"],["total","Total"]];
const NUMERIC = ["subtotal", "tax", "total"];
let invoices = [], selected = null, filter = "all";

const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;" }[c]));
const TOKEN = localStorage.getItem("token");
if (!TOKEN) location.replace("/login");
async function api(path, opts = {}) {
  opts.headers = { ...(opts.headers || {}), Authorization: "Bearer " + TOKEN };
  const r = await fetch(path, opts);
  if (r.status === 401) { localStorage.clear(); location.replace("/login"); }
  if (!r.ok) throw new Error((await r.json()).detail || "Request failed");
  return r.json();
}

async function load() {
  invoices = await api("/api/invoices");
  const s = await api("/api/stats");
  $("stats").innerHTML = [["Invoices", s.total], ["Needs review", s.needs_review], ["Awaiting approval", s.pending_approval], ["Approved", money(s.approved_value)]]
    .map(([k, v]) => `<div><b>${v}</b><span>${k}</span></div>`).join("");
  renderTabs(); renderList();
  if (selected) renderDetail(invoices.find((i) => i.id === selected));
}

function renderTabs() {
  $("tabs").innerHTML = ["all", "needs_review", "pending_approval", "approved", "rejected"]
    .map((f) => `<button aria-pressed="${filter === f}" data-f="${f}">${f === "all" ? "All" : LABEL[f]}</button>`).join("");
  $("tabs").querySelectorAll("button").forEach((b) => (b.onclick = () => { filter = b.dataset.f; renderTabs(); renderList(); }));
}

function renderList() {
  const rows = invoices.filter((i) => filter === "all" || i.status === filter);
  $("list").innerHTML = rows.length ? rows.map((i) => `
    <li class="item ${i.id === selected ? "sel" : ""}" tabindex="0" data-id="${i.id}">
      <strong>${esc(i.fields.vendor || "Unknown vendor")}</strong><span class="badge s-${i.status}">${LABEL[i.status]}</span>
      <small>${esc(i.fields.invoice_number || "No number")} · ${i.issues.length} issue${i.issues.length === 1 ? "" : "s"}</small><small>${money(i.fields.total)}</small>
    </li>`).join("") : `<li class="empty" style="padding:12px 8px">No invoices here yet.</li>`;
  $("list").querySelectorAll(".item").forEach((el) => {
    const open = () => { selected = +el.dataset.id; renderList(); renderDetail(invoices.find((i) => i.id === selected)); };
    el.onclick = open; el.onkeydown = (e) => e.key === "Enter" && open();
  });
}

function renderDetail(inv) {
  if (!inv) return;
  const open = inv.status === "needs_review" || inv.status === "pending_approval";
  $("detail").innerHTML = `
    <h2 style="margin-top:0">${esc(inv.fields.vendor || "Unknown vendor")} · ${esc(inv.fields.invoice_number || "")}</h2>
    <div class="route"><span class="badge s-${inv.status}">${LABEL[inv.status]}</span><span>Route: <b>${esc(inv.approver)}</b></span></div>
    <h2>Checks</h2>
    ${inv.issues.length ? `<ul class="issues">${inv.issues.map((i) => `<li class="${i.severity}"><b>${esc(i.code.replaceAll("_", " ").toLowerCase())}</b>${esc(i.message)}</li>`).join("")}</ul>` : `<p class="clear">All checks passed: fields complete, tax correct, PO matched, no duplicate.</p>`}
    <h2>Extracted fields</h2>
    <div class="fields">${FIELDS.map(([k, l]) => `<div><label for="f-${k}">${l}</label><input type="text" id="f-${k}" data-k="${k}" value="${esc(inv.fields[k])}" ${open ? "" : "disabled"}></div>`).join("")}</div>
    ${open ? `<div class="actions">
      <button class="btn ghost" id="recheck">Save corrections and re-check</button>
      <button class="btn" id="approve">Approve for payment</button>
      <button class="btn danger" id="reject">Reject</button></div>` : ""}
    <h2>Audit trail</h2><ul class="audit">${inv.audit.map((a) => `<li>${a.at.replace("T", " ").slice(0, 19)} — ${esc(a.event)}</li>`).join("")}</ul>`;
  if (!open) return;
  $("recheck").onclick = async () => {
    const fields = {};
    $("detail").querySelectorAll("input[data-k]").forEach((el) => { fields[el.dataset.k] = NUMERIC.includes(el.dataset.k) ? (el.value === "" ? null : parseFloat(el.value.replace(/,/g, ""))) : el.value.trim() || null; });
    await api(`/api/invoices/${inv.id}`, { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ fields }) });
    load();
  };
  const decide = (action) => async () => {
    try {
      await api(`/api/invoices/${inv.id}/decision`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ action }) });
      load();
    } catch (e) { $("msg").textContent = e.message; window.scrollTo(0, 0); }
  };
  $("approve").onclick = decide("approve"); $("reject").onclick = decide("reject");
}

async function submit(form) {
  $("msg").textContent = "";
  try {
    const inv = await api("/api/invoices", { method: "POST", body: form });
    selected = inv.id; await load();
  } catch (e) { $("msg").textContent = e.message; }
}
$("file").onchange = (e) => { const f = new FormData(); f.append("file", e.target.files[0]); submit(f); e.target.value = ""; };
$("submitPaste").onclick = () => { const f = new FormData(); f.append("text", $("paste").value); submit(f); };
load();

$("who").textContent = (localStorage.getItem("name") || "") ;
$("logout").onclick = () => { localStorage.clear(); location.replace("/login"); };
