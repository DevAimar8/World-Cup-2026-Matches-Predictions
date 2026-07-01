const params = new URLSearchParams(window.location.search);
const matchId = params.get("id");

let match = null;
let teamsBySlug = {};
let lastPrediction = null;

const title = document.getElementById("matchTitle");
const subtitle = document.getElementById("matchSubtitle");
const matchCard = document.getElementById("matchCard");
const predictionCard = document.getElementById("predictionCard");
const realResultCard = document.getElementById("realResultCard");

function esc(s) {
  return String(s ?? "").replace(/[&<>"]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;"}[c]));
}
function pct(x) { return `${(Number(x) * 100).toFixed(1)}%`; }
function team(slug) {
  if (!slug) return null;
  return teamsBySlug[slug] || { slug, codigo: slug.slice(0, 3).toUpperCase(), nombre: slug, bandera: "🏳️", flag_url: "" };
}
function flagHtml(t, cls = "bigflag-img") {
  if (!t) return `<span class="${cls}">🏳️</span>`;
  if (t.flag_url) {
    return `<img class="${cls}" src="${esc(t.flag_url)}" alt="Bandera de ${esc(t.nombre)}" loading="lazy" onerror="this.replaceWith(Object.assign(document.createElement('span'),{className:'${cls}',textContent:'${esc(t.bandera || "🏳️")}'}))">`;
  }
  return `<span class="${cls}">${esc(t.bandera || "🏳️")}</span>`;
}
function methodLabel(method) {
  if (method === "prórroga") return "120 minutos";
  if (method === "penaltis") return "Penaltis";
  return "90 minutos";
}
function scoreLineFromValues(totalA, totalB, penA = null, penB = null) {
  if (penA !== undefined && penA !== null && penB !== undefined && penB !== null) {
    return `${totalA}(${penA}) - ${totalB}(${penB})`;
  }
  return `${totalA} - ${totalB}`;
}
function resultText(m) {
  if (m.scoreA === undefined || m.scoreA === null) return "Sin resultado guardado";
  const a = team(m.a), b = team(m.b);
  const totalA = m.totalA ?? (Number(m.scoreA) + Number(m.extraA || 0));
  const totalB = m.totalB ?? (Number(m.scoreB) + Number(m.extraB || 0));
  const score = scoreLineFromValues(totalA, totalB, m.penA, m.penB);
  return `${a?.nombre ?? "A"} ${score} ${b?.nombre ?? "B"} · ${methodLabel(m.method)}`;
}
function savedResultHero(m) {
  if (!m.winner || m.scoreA === undefined || m.scoreA === null) return "";
  const a = team(m.a), b = team(m.b), winner = team(m.winner);
  const totalA = m.totalA ?? (Number(m.scoreA) + Number(m.extraA || 0));
  const totalB = m.totalB ?? (Number(m.scoreB) + Number(m.extraB || 0));
  const score = scoreLineFromValues(totalA, totalB, m.penA, m.penB);
  return `
    <div class="result-hero">
      <div class="hero-top">
        <span class="hero-winner">Pasa ${esc(winner?.nombre ?? "-")}</span>
        <span class="hero-method">${esc(methodLabel(m.method))}</span>
      </div>
      <div class="hero-score">
        <div class="hero-team">${flagHtml(a)}<span class="hero-team-name">${esc(a?.nombre ?? "Pendiente")}</span></div>
        <div class="hero-scoreline">${esc(score)}</div>
        <div class="hero-team right"><span class="hero-team-name">${esc(b?.nombre ?? "Pendiente")}</span>${flagHtml(b)}</div>
      </div>
      <p class="hero-sub">Resultado ${m.locked ? "real bloqueado" : "simulado"} guardado en el bracket.</p>
    </div>`;
}
function renderBaseMatch() {
  const a = team(match.a), b = team(match.b);
  title.textContent = `${match.label}: ${a?.nombre ?? "Pendiente"} vs ${b?.nombre ?? "Pendiente"}`;
  subtitle.textContent = match.locked ? "Resultado real bloqueado y guardado." : "Simula con el modelo o introduce el resultado real para hacer avanzar al ganador.";
  matchCard.innerHTML = `
    <h2>Partido</h2>
    <div class="versus">
      <div class="team-box">${flagHtml(a)}<strong>${esc(a?.nombre ?? "Pendiente")}</strong><span>${esc(a?.codigo ?? "-")}</span></div>
      <div class="vs">VS</div>
      <div class="team-box">${flagHtml(b)}<strong>${esc(b?.nombre ?? "Pendiente")}</strong><span>${esc(b?.codigo ?? "-")}</span></div>
    </div>
    ${savedResultHero(match)}
    <div class="metric"><span>Estado</span><strong>${match.locked ? "REAL" : match.simulated ? "SIMULADO" : "PENDIENTE"}</strong></div>
    <div class="metric"><span>Resultado guardado</span><strong>${esc(resultText(match))}</strong></div>
    <div class="metric"><span>Archivo de guardado</span><strong>data/bracket_state.json</strong></div>
    ${match.winner ? `<p class="success">Clasifica: <strong>${esc(team(match.winner)?.bandera)} ${esc(team(match.winner)?.nombre)}</strong></p>` : ""}
    ${(!match.a || !match.b) ? `<p class="warning">Este cruce todavía no tiene los dos equipos. Primero deben completarse los partidos anteriores.</p>` : ""}
  `;
}
function predictionScore(data) {
  const sim = data.simulacion;
  const totalA = sim.total_a ?? (Number(sim.goles_90_a) + Number(sim.goles_prorroga_a || 0));
  const totalB = sim.total_b ?? (Number(sim.goles_90_b) + Number(sim.goles_prorroga_b || 0));
  return scoreLineFromValues(totalA, totalB, sim.penaltis_a, sim.penaltis_b);
}
function probRow(label, value) {
  const val = Math.max(0, Math.min(1, Number(value)));
  return `
    <div class="prob-row">
      <label>${esc(label)}</label>
      <div class="prob-track"><div class="prob-fill" style="width:${(val*100).toFixed(1)}%"></div></div>
      <strong>${pct(val)}</strong>
    </div>`;
}
function renderPrediction(data) {
  lastPrediction = data;
  const a = data.equipo_a;
  const b = data.equipo_b;
  const sim = data.simulacion;
  const ganador = sim.ganador;
  const score = predictionScore(data);
  const method = methodLabel(sim.metodo);
  predictionCard.innerHTML = `
    <h2>Predicción del modelo</h2>
    <span class="pill">${esc(data.etiqueta)}</span>

    <div class="result-hero">
      <div class="hero-top">
        <span class="hero-winner">Pasa ${esc(ganador.nombre)}</span>
        <span class="hero-method">${esc(method)}</span>
      </div>
      <div class="hero-score">
        <div class="hero-team">${flagHtml(a)}<span class="hero-team-name">${esc(a.nombre)}</span></div>
        <div class="hero-scoreline">${esc(score)}</div>
        <div class="hero-team right"><span class="hero-team-name">${esc(b.nombre)}</span>${flagHtml(b)}</div>
      </div>
      <p class="hero-sub">Resultado determinista: parte del marcador puntual más probable del modelo a 90'. Si es empate, se decide en prórroga o penaltis.</p>
    </div>

    <h3>Probabilidades a 90 minutos</h3>
    <div class="prob-bars">
      ${probRow(a.nombre, data.probabilidades_90.a)}
      ${probRow("Empate", data.probabilidades_90.empate)}
      ${probRow(b.nombre, data.probabilidades_90.b)}
    </div>

    <h3>Probabilidades de eliminatoria</h3>
    <div class="prob-bars">
      ${probRow(`Clasifica ${a.nombre}`, data.probabilidades_eliminatoria.clasifica_a)}
      ${probRow(`Clasifica ${b.nombre}`, data.probabilidades_eliminatoria.clasifica_b)}
      ${probRow("Prórroga", data.probabilidades_eliminatoria.prorroga)}
      ${probRow("Penaltis", data.probabilidades_eliminatoria.penaltis)}
    </div>

    <h3>xGoals del modelo</h3>
    <div class="compact-grid">
      <div class="stat-card"><span>xG 90' ${esc(a.codigo)}</span><strong>${data.xg_detalle.noventa_minutos.a}</strong></div>
      <div class="stat-card"><span>xG 90' ${esc(b.codigo)}</span><strong>${data.xg_detalle.noventa_minutos.b}</strong></div>
      <div class="stat-card"><span>Ventaja xG</span><strong>${data.xg_detalle.diferencia_90}</strong></div>
      <div class="stat-card"><span>xG prórroga ${esc(a.codigo)}</span><strong>${data.xg_detalle.prorroga_condicional.a}</strong></div>
      <div class="stat-card"><span>xG prórroga ${esc(b.codigo)}</span><strong>${data.xg_detalle.prorroga_condicional.b}</strong></div>
      <div class="stat-card"><span>xG total</span><strong>${data.xg_detalle.total_eliminatoria_esperado.a} - ${data.xg_detalle.total_eliminatoria_esperado.b}</strong></div>
    </div>
    <p class="note">${esc(data.xg_detalle.nota)}</p>

    <h3>Coherencia del modelo</h3>
    <div class="grid-metrics">
      <div class="metric"><span>Marcador de la UI</span><strong>${esc(a.codigo)} ${data.marcador_mas_probable.a}-${data.marcador_mas_probable.b} ${esc(b.codigo)}</strong></div>
      <div class="metric"><span>Marcador más probable del modelo</span><strong>${esc(a.codigo)} ${data.marcador_puntual_mas_probable.a}-${data.marcador_puntual_mas_probable.b} ${esc(b.codigo)}</strong></div>
    </div>

    <h3>Análisis</h3>
    <div class="analysis-box"><p>${esc(data.analisis)}</p></div>

    <div class="button-row">
      <button class="primary-btn" type="button" onclick="saveSimulation()" ${match.locked ? "disabled" : ""}>Guardar y hacer pasar a ${esc(ganador.nombre)}</button>
      <button class="ghost-btn" type="button" onclick="calculatePrediction()">Recalcular predicción</button>
    </div>
  `;
}
function renderPredictionEmpty(message = "Pulsa calcular para obtener la predicción.") {
  predictionCard.innerHTML = `
    <h2>Predicción del modelo</h2>
    <p>${esc(message)}</p>
    <div class="button-row">
      <button class="primary-btn" type="button" onclick="calculatePrediction()" ${(!match?.a || !match?.b) ? "disabled" : ""}>Calcular predicción</button>
      <button class="ghost-btn" type="button" onclick="saveSimulation()" ${(!match?.a || !match?.b || match?.locked) ? "disabled" : ""}>Simular y avanzar</button>
    </div>
  `;
}
function renderRealForm() {
  const a = team(match.a), b = team(match.b);
  const method = match.method || "90 minutos";
  realResultCard.innerHTML = `
    <h2>Registrar resultado real</h2>
    <p>Úsalo cuando ya se haya jugado el partido. Guarda el marcador, bloquea el partido y coloca al ganador en la siguiente ronda.</p>
    <form id="realForm">
      <div class="form-grid">
        <label>Goles 90' ${esc(a?.codigo ?? "A")}<input name="scoreA" type="number" min="0" value="${match.scoreA ?? ""}" required></label>
        <label>Goles 90' ${esc(b?.codigo ?? "B")}<input name="scoreB" type="number" min="0" value="${match.scoreB ?? ""}" required></label>
        <label>Goles prórroga ${esc(a?.codigo ?? "A")}<input name="extraA" type="number" min="0" value="${match.extraA ?? ""}" placeholder="0"></label>
        <label>Goles prórroga ${esc(b?.codigo ?? "B")}<input name="extraB" type="number" min="0" value="${match.extraB ?? ""}" placeholder="0"></label>
        <label>Penaltis ${esc(a?.codigo ?? "A")}<input name="penA" type="number" min="0" value="${match.penA ?? ""}" placeholder="solo tanda"></label>
        <label>Penaltis ${esc(b?.codigo ?? "B")}<input name="penB" type="number" min="0" value="${match.penB ?? ""}" placeholder="solo tanda"></label>
        <label>Método
          <select name="method">
            <option ${method === "90 minutos" ? "selected" : ""}>90 minutos</option>
            <option ${method === "prórroga" ? "selected" : ""}>prórroga</option>
            <option ${method === "penaltis" ? "selected" : ""}>penaltis</option>
          </select>
        </label>
      </div>
      <div class="button-row">
        <button class="primary-btn" type="submit" ${(!match?.a || !match?.b) ? "disabled" : ""}>Guardar resultado real y avanzar</button>
        <button class="ghost-btn" type="button" onclick="window.location.href='/'">Volver al bracket</button>
      </div>
      <p id="realFormMsg"></p>
    </form>
  `;
  document.getElementById("realForm").addEventListener("submit", submitRealResult);
}
async function loadMatch() {
  if (!matchId) throw new Error("Falta el parámetro id del partido.");
  const res = await fetch(`/api/match/${encodeURIComponent(matchId)}`);
  const data = await res.json();
  if (!res.ok) throw new Error(data.error || "No se pudo cargar el partido");
  match = data.match;
  teamsBySlug = Object.fromEntries(data.equipos.map(t => [t.slug, t]));
  renderBaseMatch();
  renderPredictionEmpty(match.prediction ? "Este partido ya tiene una predicción guardada." : undefined);
  if (match.prediction) renderPrediction(match.prediction);
  renderRealForm();
}
async function calculatePrediction() {
  predictionCard.innerHTML = `<h2>Predicción del modelo</h2><p>Calculando...</p>`;
  const res = await fetch("/api/predecir-match", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ match_id: matchId })
  });
  const data = await res.json();
  if (!res.ok) {
    renderPredictionEmpty(data.error || "No se pudo calcular la predicción.");
    return;
  }
  renderPrediction(data.prediction);
}
async function saveSimulation() {
  const res = await fetch("/api/simular", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ match_id: matchId })
  });
  const data = await res.json();
  if (!res.ok) {
    predictionCard.insertAdjacentHTML("beforeend", `<p class="error">${esc(data.error || "No se pudo guardar la simulación")}</p>`);
    return;
  }
  match = data.match;
  renderBaseMatch();
  renderPrediction(data.prediction);
  renderRealForm();
  predictionCard.insertAdjacentHTML("beforeend", `<p class="success">Simulación guardada y ganador avanzado en el bracket.</p>`);
}
async function submitRealResult(ev) {
  ev.preventDefault();
  const msg = document.getElementById("realFormMsg");
  msg.textContent = "Guardando...";
  msg.className = "note";
  const fd = new FormData(ev.currentTarget);
  const payload = Object.fromEntries(fd.entries());
  payload.match_id = matchId;
  const res = await fetch("/api/resultado-real", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  });
  const data = await res.json();
  if (!res.ok) {
    msg.textContent = data.error || "No se pudo guardar el resultado real.";
    msg.className = "error";
    return;
  }
  match = data.match;
  msg.textContent = "Resultado real guardado y bracket actualizado.";
  msg.className = "success";
  renderBaseMatch();
  renderPredictionEmpty("Resultado real guardado. No se simula encima de un partido real bloqueado.");
  renderRealForm();
}

loadMatch().catch(err => {
  title.textContent = "Error";
  subtitle.textContent = err.message;
  matchCard.innerHTML = `<p class="error">${esc(err.message)}</p>`;
  predictionCard.innerHTML = "";
  realResultCard.innerHTML = "";
});
