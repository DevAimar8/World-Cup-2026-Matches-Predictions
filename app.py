# -*- coding: utf-8 -*-
"""Servidor Flask para bracket editable del Mundial 2026.

El HTML es estático, pero el estado real/simulado del bracket se guarda en:
    data/bracket_state.json

Así puedes simular partidos, registrar resultados reales y volver a abrir la app
sin perder los cambios.
"""
from __future__ import annotations

import copy
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from flask import Flask, jsonify, request, send_from_directory

from src.modelo import listar_equipos, predecir_partido

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
STATE_PATH = DATA_DIR / "bracket_state.json"
SEED_PATH = DATA_DIR / "bracket_seed.json"

app = Flask(__name__, static_folder="static", static_url_path="/static")


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def ensure_state() -> dict:
    if not STATE_PATH.exists():
        seed = load_json(SEED_PATH)
        seed["updated_at"] = now_iso()
        save_json(STATE_PATH, seed)
    return load_json(STATE_PATH)


def save_state(state: dict) -> None:
    state["updated_at"] = now_iso()
    save_json(STATE_PATH, state)


def get_match(state: dict, match_id: str) -> Dict[str, Any]:
    matches = state.get("matches", {})
    if match_id not in matches:
        raise ValueError(f"Partido no encontrado: {match_id}")
    return matches[match_id]


def clear_outcome(match: dict) -> None:
    """Limpia resultado sin borrar equipos ni estructura."""
    for key in (
        "scoreA", "scoreB", "extraA", "extraB", "penA", "penB", "winner",
        "prediction", "simulated", "locked", "status", "source", "method", "saved_at",
    ):
        match.pop(key, None)


def reset_downstream(state: dict, match_id: str) -> None:
    """Borra los resultados dependientes de un partido que ha cambiado.

    Si mañana registras un resultado real distinto, los cruces posteriores que dependían
    de una simulación antigua se limpian para evitar equipos imposibles.
    """
    match = state["matches"].get(match_id)
    if not match:
        return

    for edge_key, slot_key in (("next", "nextSlot"), ("loserNext", "loserSlot")):
        next_id = match.get(edge_key)
        slot = match.get(slot_key)
        if not next_id or not slot or next_id not in state["matches"]:
            continue
        child = state["matches"][next_id]
        if not child.get("locked"):
            child[slot] = None
            clear_outcome(child)
            reset_downstream(state, next_id)


def advance(state: dict, match_id: str, winner_slug: str) -> None:
    match = get_match(state, match_id)
    loser_slug = match.get("b") if match.get("a") == winner_slug else match.get("a")

    # Antes de colocar nuevos participantes, limpiamos resultados posteriores no oficiales.
    reset_downstream(state, match_id)

    next_id = match.get("next")
    if next_id and next_id in state["matches"]:
        next_match = state["matches"][next_id]
        next_match[match.get("nextSlot", "a")] = winner_slug

    loser_next_id = match.get("loserNext")
    if loser_next_id and loser_next_id in state["matches"] and loser_slug:
        loser_next = state["matches"][loser_next_id]
        loser_next[match.get("loserSlot", "a")] = loser_slug


def apply_prediction_to_match(state: dict, match_id: str, prediction: dict, source: str = "simulado") -> dict:
    match = get_match(state, match_id)
    sim = prediction["simulacion"]
    ganador = sim["ganador"]["slug"]

    match["scoreA"] = sim["goles_90_a"]
    match["scoreB"] = sim["goles_90_b"]
    match["extraA"] = sim.get("goles_prorroga_a", 0)
    match["extraB"] = sim.get("goles_prorroga_b", 0)
    match["totalA"] = sim.get("total_a", match["scoreA"] + match["extraA"])
    match["totalB"] = sim.get("total_b", match["scoreB"] + match["extraB"])
    match["penA"] = sim.get("penaltis_a")
    match["penB"] = sim.get("penaltis_b")
    match["winner"] = ganador
    match["method"] = sim.get("metodo", "90 minutos")
    match["simulated"] = source == "simulado"
    match["locked"] = source == "real"
    match["status"] = source
    match["source"] = source
    match["prediction"] = prediction
    match["saved_at"] = now_iso()

    advance(state, match_id, ganador)
    return match


def parse_int(value: Any, field: str, required: bool = True) -> Optional[int]:
    if value in (None, ""):
        if required:
            raise ValueError(f"Falta el campo {field}.")
        return None
    try:
        return int(value)
    except Exception as exc:
        raise ValueError(f"{field} debe ser un número entero.") from exc


@app.get("/")
def inicio():
    return send_from_directory("static", "index.html")


@app.get("/partido")
def partido():
    return send_from_directory("static", "partido.html")


@app.get("/api/equipos")
def api_equipos():
    return jsonify({"equipos": listar_equipos()})


@app.get("/api/bracket")
def api_bracket():
    state = ensure_state()
    return jsonify({"state": state, "equipos": listar_equipos()})


@app.get("/api/match/<match_id>")
def api_match(match_id: str):
    state = ensure_state()
    try:
        match = get_match(state, match_id)
        return jsonify({"match": match, "state_updated_at": state.get("updated_at"), "equipos": listar_equipos()})
    except Exception as exc:
        return jsonify({"error": str(exc)}), 404


@app.post("/api/predecir")
def api_predecir():
    datos = request.get_json(force=True, silent=True) or {}
    equipo_a = datos.get("equipo_a")
    equipo_b = datos.get("equipo_b")
    local = datos.get("local")
    try:
        resultado = predecir_partido(equipo_a, equipo_b, local=local)
        return jsonify(resultado)
    except Exception as exc:
        return jsonify({"error": str(exc)}), 400


@app.post("/api/predecir-match")
def api_predecir_match():
    datos = request.get_json(force=True, silent=True) or {}
    state = ensure_state()
    try:
        match = get_match(state, datos.get("match_id"))
        if not match.get("a") or not match.get("b"):
            raise ValueError("Este partido todavía no tiene los dos equipos definidos.")
        prediction = predecir_partido(match["a"], match["b"])
        return jsonify({"prediction": prediction, "match": match})
    except Exception as exc:
        return jsonify({"error": str(exc)}), 400


@app.post("/api/simular")
def api_simular():
    """Calcula la predicción determinista, la guarda y hace avanzar al ganador."""
    datos = request.get_json(force=True, silent=True) or {}
    state = ensure_state()
    try:
        match = get_match(state, datos.get("match_id"))
        if match.get("locked"):
            raise ValueError("Este partido está bloqueado como resultado real. No se puede simular encima.")
        if not match.get("a") or not match.get("b"):
            raise ValueError("Este partido todavía no tiene los dos equipos definidos.")
        prediction = predecir_partido(match["a"], match["b"])
        updated = apply_prediction_to_match(state, match["id"], prediction, source="simulado")
        save_state(state)
        return jsonify({"ok": True, "match": updated, "prediction": prediction, "state": state})
    except Exception as exc:
        return jsonify({"error": str(exc)}), 400


@app.post("/api/resultado-real")
def api_resultado_real():
    """Guarda un resultado real, bloquea el partido y avanza al ganador."""
    datos = request.get_json(force=True, silent=True) or {}
    state = ensure_state()
    try:
        match = get_match(state, datos.get("match_id"))
        if not match.get("a") or not match.get("b"):
            raise ValueError("Este partido todavía no tiene los dos equipos definidos.")

        score_a = parse_int(datos.get("scoreA"), "scoreA")
        score_b = parse_int(datos.get("scoreB"), "scoreB")
        extra_a = parse_int(datos.get("extraA"), "extraA", required=False) or 0
        extra_b = parse_int(datos.get("extraB"), "extraB", required=False) or 0
        pen_a = parse_int(datos.get("penA"), "penA", required=False)
        pen_b = parse_int(datos.get("penB"), "penB", required=False)
        method = datos.get("method") or "90 minutos"

        total_a = score_a + extra_a
        total_b = score_b + extra_b
        if pen_a is not None or pen_b is not None:
            if pen_a is None or pen_b is None:
                raise ValueError("Para penaltis debes introducir penA y penB.")
            if total_a != total_b:
                raise ValueError("Solo hay penaltis si el marcador sigue empatado tras prórroga.")
            if pen_a == pen_b:
                raise ValueError("La tanda de penaltis no puede acabar empatada.")
            winner = match["a"] if pen_a > pen_b else match["b"]
            method = "penaltis"
        elif total_a > total_b:
            winner = match["a"]
            method = "prórroga" if extra_a or extra_b or method == "prórroga" else "90 minutos"
        elif total_b > total_a:
            winner = match["b"]
            method = "prórroga" if extra_a or extra_b or method == "prórroga" else "90 minutos"
        else:
            raise ValueError("Una eliminatoria no puede guardarse empatada. Añade prórroga o penaltis.")

        # Limpia predicción anterior y guarda resultado real.
        match["scoreA"] = score_a
        match["scoreB"] = score_b
        match["extraA"] = extra_a
        match["extraB"] = extra_b
        match["totalA"] = total_a
        match["totalB"] = total_b
        match["penA"] = pen_a
        match["penB"] = pen_b
        match["winner"] = winner
        match["method"] = method
        match["locked"] = True
        match["simulated"] = False
        match["status"] = "real"
        match["source"] = "resultado real manual"
        match["saved_at"] = now_iso()
        match.pop("prediction", None)

        advance(state, match["id"], winner)
        save_state(state)
        return jsonify({"ok": True, "match": match, "state": state})
    except Exception as exc:
        return jsonify({"error": str(exc)}), 400


@app.post("/api/desbloquear")
def api_desbloquear():
    datos = request.get_json(force=True, silent=True) or {}
    state = ensure_state()
    try:
        match = get_match(state, datos.get("match_id"))
        match["locked"] = False
        match["status"] = "editado"
        match["source"] = "desbloqueado manualmente"
        save_state(state)
        return jsonify({"ok": True, "match": match, "state": state})
    except Exception as exc:
        return jsonify({"error": str(exc)}), 400


@app.post("/api/reset")
def api_reset():
    seed = load_json(SEED_PATH)
    seed["updated_at"] = now_iso()
    save_json(STATE_PATH, seed)
    return jsonify({"ok": True, "state": seed})


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
