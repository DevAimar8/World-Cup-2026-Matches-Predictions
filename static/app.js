let state = null;
let teamsBySlug = {};

const grid = document.getElementById("bracketGrid");
const updatedAt = document.getElementById("updatedAt");
const downloadBtn = document.getElementById("downloadBtn");
const resetBtn = document.getElementById("resetBtn");

function esc(s) {
  return String(s ?? "").replace(/[&<>"]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;"}[c]));
}
function team(slug) {
  if (!slug) return null;
  return teamsBySlug[slug] || { slug, codigo: slug.slice(0, 3).toUpperCase(), nombre: slug, bandera: "🏳️", flag_url: "" };
}
function flagHtml(t, cls = "flag-img") {
  if (!t) return `<span class="${cls}">🏳️</span>`;
  if (t.flag_url) {
    return `<img class="${cls}" src="${esc(t.flag_url)}" alt="Bandera de ${esc(t.nombre)}" loading="lazy" onerror="this.replaceWith(Object.assign(document.createElement('span'),{className:'${cls}',textContent:'${esc(t.bandera || "🏳️")}'}))">`;
  }
  return `<span class="${cls}">${esc(t.bandera || "🏳️")}</span>`;
}
function scoreText(match, side) {
  const score = side === "a" ? match.scoreA : match.scoreB;
  const extra = side === "a" ? match.extraA : match.extraB;
  const pen = side === "a" ? match.penA : match.penB;
  if (score === undefined || score === null) return "";
  const total = (extra ? Number(score) + Number(extra) : Number(score));
  return `${total}${pen !== undefined && pen !== null ? ` <small>(${pen})</small>` : ""}`;
}
function renderTeamRow(match, side) {
  const slug = match[side];
  const t = team(slug);
  const isWinner = match.winner && match.winner === slug;
  if (!t) {
    return `<div class="team-row"><span></span><span class="code">${side === "a" ? esc(match.label) : "Pendiente"}</span><span></span></div>`;
  }
  return `
    <div class="team-row ${isWinner ? "winner" : ""}">
      ${flagHtml(t)}
      <span class="code" title="${esc(t.nombre)}">${esc(t.codigo)}</span>
      <span class="score">${scoreText(match, side)}</span>
    </div>`;
}
function cardClass(match) {
  const classes = ["match-card"];
  if (match.kind === "final") classes.push("final");
  if (match.kind === "third") classes.push("third");
  if (match.locked) classes.push("locked");
  if (match.simulated) classes.push("simulated");
  if (!match.a || !match.b) classes.push("empty");
  else if (!match.winner) classes.push("pending");
  return classes.join(" ");
}
function statusChip(match) {
  if (match.locked || match.status === "real") return `<span class="status-chip real">REAL</span>`;
  if (match.simulated || match.status === "simulado") return `<span class="status-chip simulado">SIM</span>`;
  if (!match.a || !match.b) return `<span class="status-chip">TBD</span>`;
  return `<span class="status-chip">EDITAR</span>`;
}
function render() {
  grid.innerHTML = "";
  Object.values(state.matches).forEach(match => {
    const card = document.createElement("article");
    card.className = cardClass(match);
    card.dataset.matchId = match.id;
    card.style.gridColumn = String(match.col);
    card.style.gridRow = `${match.row} / span 3`;
    let title = "";
    if (match.kind === "final") title = `<div class="match-title">🏆 FINAL</div>`;
    if (match.kind === "third") title = `<div class="match-title">3er Puesto</div>`;
    card.innerHTML = `<div class="card-meta">${statusChip(match)}</div>${title}${renderTeamRow(match, "a")}${renderTeamRow(match, "b")}`;
    card.addEventListener("click", () => { window.location.href = `/partido?id=${encodeURIComponent(match.id)}`; });
    grid.appendChild(card);
  });
}
async function loadBracket() {
  const res = await fetch("/api/bracket");
  const data = await res.json();
  state = data.state;
  teamsBySlug = Object.fromEntries(data.equipos.map(t => [t.slug, t]));
  updatedAt.textContent = state.updated_at ? `Último guardado: ${state.updated_at}` : "Haz clic en un partido para editar";
  render();
}
function buildSvgSnapshot() {
  const width = 1500;
  const height = 880;
  const colW = width / 9;
  const rowH = 27;
  const padX = 18;
  const padY = 112;
  let out = `<svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}" viewBox="0 0 ${width} ${height}">`;
  out += `<rect width="${width}" height="${height}" fill="#071712"/>`;
  out += `<text x="26" y="44" fill="#effdf7" font-size="30" font-weight="900">Predicción del Mundial de Aimar</text>`;
  out += `<text x="28" y="72" fill="#a7ffd8" font-size="13" font-weight="700">Bracket editable · xG · prórroga · penaltis</text>`;
  const labels = ["16avos","8avos","4tos","Semis","Final","Semis","4tos","8avos","16avos"];
  labels.forEach((l, i) => out += `<text x="${i*colW + colW/2}" y="98" fill="#a7ffd8" font-size="14" font-weight="900" text-anchor="middle">${l}</text>`);
  Object.values(state.matches).forEach(m => {
    const x = (m.col - 1) * colW + padX;
    const y = padY + (m.row - 1) * rowH;
    const w = colW - 32;
    const h = m.kind ? 92 : 78;
    const titleH = m.kind ? 26 : 0;
    const stroke = m.kind === "final" ? "#f4c84a" : m.kind === "third" ? "#ff8b3d" : m.locked ? "#ffffff" : m.simulated ? "#5ff2b6" : "#2f7e67";
    out += `<rect x="${x}" y="${y}" width="${w}" height="${h}" rx="12" fill="#0b2c23" stroke="${stroke}"/>`;
    if (m.kind) {
      const fill = m.kind === "final" ? "#f4c84a" : "#ff8b3d";
      const color = m.kind === "final" ? "#071712" : "#ffffff";
      out += `<rect x="${x}" y="${y}" width="${w}" height="${titleH}" rx="12" fill="${fill}"/>`;
      out += `<text x="${x+w/2}" y="${y+18}" fill="${color}" font-size="12" font-weight="900" text-anchor="middle">${esc(m.label)}</text>`;
    }
    ["a", "b"].forEach((side, idx) => {
      const t = team(m[side]);
      const yy = y + titleH + 24 + idx * 34;
      const s = scoreText(m, side).replace(/<[^>]+>/g, "");
      out += `<text x="${x+12}" y="${yy}" fill="#ffffff" font-size="13">${t ? esc(t.bandera || "") : ""}</text>`;
      out += `<text x="${x+42}" y="${yy}" fill="#effdf7" font-size="13" font-weight="900">${t ? esc(t.codigo) : esc(idx === 0 ? m.label : "Pendiente")}</text>`;
      out += `<text x="${x+w-12}" y="${yy}" fill="#effdf7" font-size="13" font-weight="900" text-anchor="end">${esc(s)}</text>`;
    });
  });
  out += `</svg>`;
  return out;
}

downloadBtn.addEventListener("click", () => {
  const svg = buildSvgSnapshot();
  const blob = new Blob([svg], { type: "image/svg+xml;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = "prediccion-mundial-aimar.svg";
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
});

resetBtn.addEventListener("click", async () => {
  const ok = confirm("¿Seguro que quieres reiniciar el bracket al estado inicial? Se perderán simulaciones y resultados manuales guardados.");
  if (!ok) return;
  await fetch("/api/reset", { method: "POST" });
  await loadBracket();
});

loadBracket().catch(err => {
  updatedAt.textContent = "Error cargando bracket";
  grid.innerHTML = `<p class="error">${esc(err.message)}</p>`;
});
