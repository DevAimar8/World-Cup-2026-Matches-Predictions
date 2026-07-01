# -*- coding: utf-8 -*-
"""Modelo de predicción para partidos de eliminatoria.

Basado en el núcleo del ZIP original: Elo calibrado + Poisson + corrección Dixon-Coles.
Este módulo añade una simulación completa de eliminatoria:
- 90 minutos
- prórroga si hay empate
- penaltis si sigue el empate

No descarga datos externos ni actualiza ratings automáticamente.
"""
from __future__ import annotations

import math
import random
import unicodedata
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

DC_RHO = -0.13
HOME_BONUS = 75
MAX_GOALS = 8
MAX_GOALS_PRORROGA = 4
EXTRA_TIME_FACTOR = 0.30  # La prórroga dura 30 minutos: aprox. un tercio de un partido.

RATINGS: Dict[str, int] = {
    "argentina": 1976,
    "france": 2009,
    "spain": 2010,
    "brazil": 1955,
    "england": 1993,
    "portugal": 1945,
    "netherlands": 1894,
    "germany": 1926,
    "belgium": 1878,
    "colombia": 1878,
    "uruguay": 1831,
    "croatia": 1852,
    "morocco": 1874,
    "switzerland": 1812,
    "usa": 1826,
    "mexico": 1834,
    "japan": 1825,
    "senegal": 1848,
    "ecuador": 1829,
    "australia": 1772,
    "south-korea": 1760,
    "iran": 1747,
    "canada": 1740,
    "ghana": 1659,
    "tunisia": 1680,
    "ivory-coast": 1732,
    "saudi-arabia": 1657,
    "qatar": 1592,
    "egypt": 1695,
    "algeria": 1704,
    "scotland": 1663,
    "paraguay": 1681,
    "czech-republic": 1651,
    "bosnia-and-herzegovina": 1602,
    "south-africa": 1591,
    "new-zealand": 1591,
    "panama": 1615,
    "jordan": 1548,
    "haiti": 1537,
    "norway": 1880,
    "sweden": 1752,
    "turkey": 1731,
    "austria": 1718,
    "iraq": 1599,
    "uzbekistan": 1633,
    "cape-verde": 1650,
    "dr-congo": 1650,
    "curacao": 1548,
}

NOMBRES_ES: Dict[str, str] = {
    "argentina": "Argentina",
    "france": "Francia",
    "spain": "España",
    "brazil": "Brasil",
    "england": "Inglaterra",
    "portugal": "Portugal",
    "netherlands": "Países Bajos",
    "germany": "Alemania",
    "belgium": "Bélgica",
    "colombia": "Colombia",
    "uruguay": "Uruguay",
    "croatia": "Croacia",
    "morocco": "Marruecos",
    "switzerland": "Suiza",
    "usa": "Estados Unidos",
    "mexico": "México",
    "japan": "Japón",
    "senegal": "Senegal",
    "ecuador": "Ecuador",
    "australia": "Australia",
    "south-korea": "Corea del Sur",
    "iran": "Irán",
    "canada": "Canadá",
    "ghana": "Ghana",
    "tunisia": "Túnez",
    "ivory-coast": "Costa de Marfil",
    "saudi-arabia": "Arabia Saudí",
    "qatar": "Catar",
    "egypt": "Egipto",
    "algeria": "Argelia",
    "scotland": "Escocia",
    "paraguay": "Paraguay",
    "czech-republic": "Chequia",
    "bosnia-and-herzegovina": "Bosnia y Herzegovina",
    "south-africa": "Sudáfrica",
    "new-zealand": "Nueva Zelanda",
    "panama": "Panamá",
    "jordan": "Jordania",
    "haiti": "Haití",
    "norway": "Noruega",
    "sweden": "Suecia",
    "turkey": "Turquía",
    "austria": "Austria",
    "iraq": "Irak",
    "uzbekistan": "Uzbekistán",
    "cape-verde": "Cabo Verde",
    "dr-congo": "RD Congo",
    "curacao": "Curazao",
}

CODIGOS: Dict[str, str] = {
    "argentina": "ARG",
    "france": "FRA",
    "spain": "ESP",
    "brazil": "BRA",
    "england": "ENG",
    "portugal": "POR",
    "netherlands": "NED",
    "germany": "GER",
    "belgium": "BEL",
    "colombia": "COL",
    "uruguay": "URU",
    "croatia": "CRO",
    "morocco": "MAR",
    "switzerland": "SUI",
    "usa": "USA",
    "mexico": "MEX",
    "japan": "JPN",
    "senegal": "SEN",
    "ecuador": "ECU",
    "australia": "AUS",
    "south-korea": "KOR",
    "iran": "IRN",
    "canada": "CAN",
    "ghana": "GHA",
    "tunisia": "TUN",
    "ivory-coast": "CIV",
    "saudi-arabia": "KSA",
    "qatar": "QAT",
    "egypt": "EGY",
    "algeria": "DZA",
    "scotland": "SCO",
    "paraguay": "PAR",
    "czech-republic": "CZE",
    "bosnia-and-herzegovina": "BIH",
    "south-africa": "RSA",
    "new-zealand": "NZL",
    "panama": "PAN",
    "jordan": "JOR",
    "haiti": "HAI",
    "norway": "NOR",
    "sweden": "SWE",
    "turkey": "TUR",
    "austria": "AUT",
    "iraq": "IRQ",
    "uzbekistan": "UZB",
    "cape-verde": "CPV",
    "dr-congo": "COD",
    "curacao": "CUW",
}

BANDERAS: Dict[str, str] = {
    "argentina": "🇦🇷",
    "france": "🇫🇷",
    "spain": "🇪🇸",
    "brazil": "🇧🇷",
    "england": "🏴",
    "portugal": "🇵🇹",
    "netherlands": "🇳🇱",
    "germany": "🇩🇪",
    "belgium": "🇧🇪",
    "colombia": "🇨🇴",
    "uruguay": "🇺🇾",
    "croatia": "🇭🇷",
    "morocco": "🇲🇦",
    "switzerland": "🇨🇭",
    "usa": "🇺🇸",
    "mexico": "🇲🇽",
    "japan": "🇯🇵",
    "senegal": "🇸🇳",
    "ecuador": "🇪🇨",
    "australia": "🇦🇺",
    "south-korea": "🇰🇷",
    "iran": "🇮🇷",
    "canada": "🇨🇦",
    "ghana": "🇬🇭",
    "tunisia": "🇹🇳",
    "ivory-coast": "🇨🇮",
    "saudi-arabia": "🇸🇦",
    "qatar": "🇶🇦",
    "egypt": "🇪🇬",
    "algeria": "🇩🇿",
    "scotland": "🏴󠁧󠁢󠁳󠁣󠁴󠁿",
    "paraguay": "🇵🇾",
    "czech-republic": "🇨🇿",
    "bosnia-and-herzegovina": "🇧🇦",
    "south-africa": "🇿🇦",
    "new-zealand": "🇳🇿",
    "panama": "🇵🇦",
    "jordan": "🇯🇴",
    "haiti": "🇭🇹",
    "norway": "🇳🇴",
    "sweden": "🇸🇪",
    "turkey": "🇹🇷",
    "austria": "🇦🇹",
    "iraq": "🇮🇶",
    "uzbekistan": "🇺🇿",
    "cape-verde": "🇨🇻",
    "dr-congo": "🇨🇩",
    "curacao": "🇨🇼",
}


ISO2_FLAGS: Dict[str, str] = {
    "argentina": "ar",
    "france": "fr",
    "spain": "es",
    "brazil": "br",
    "england": "gb-eng",
    "portugal": "pt",
    "netherlands": "nl",
    "germany": "de",
    "belgium": "be",
    "colombia": "co",
    "uruguay": "uy",
    "croatia": "hr",
    "morocco": "ma",
    "switzerland": "ch",
    "usa": "us",
    "mexico": "mx",
    "japan": "jp",
    "senegal": "sn",
    "ecuador": "ec",
    "australia": "au",
    "south-korea": "kr",
    "iran": "ir",
    "canada": "ca",
    "ghana": "gh",
    "tunisia": "tn",
    "ivory-coast": "ci",
    "saudi-arabia": "sa",
    "qatar": "qa",
    "egypt": "eg",
    "algeria": "dz",
    "scotland": "gb-sct",
    "paraguay": "py",
    "czech-republic": "cz",
    "bosnia-and-herzegovina": "ba",
    "south-africa": "za",
    "new-zealand": "nz",
    "panama": "pa",
    "jordan": "jo",
    "haiti": "ht",
    "norway": "no",
    "sweden": "se",
    "turkey": "tr",
    "austria": "at",
    "iraq": "iq",
    "uzbekistan": "uz",
    "cape-verde": "cv",
    "dr-congo": "cd",
    "curacao": "cw",
}


def flag_url(slug: str) -> str:
    code = ISO2_FLAGS.get(slug)
    if not code:
        return ""
    return f"https://flagcdn.com/w80/{code}.png"


ALIASES_EXTRA = {
    "espana": "spain", "españa": "spain", "spain": "spain",
    "francia": "france", "france": "france",
    "alemania": "germany", "germany": "germany",
    "brasil": "brazil", "brazil": "brazil",
    "inglaterra": "england", "england": "england",
    "paises bajos": "netherlands", "países bajos": "netherlands", "holanda": "netherlands", "netherlands": "netherlands",
    "belgica": "belgium", "bélgica": "belgium", "belgium": "belgium",
    "mexico": "mexico", "méxico": "mexico",
    "estados unidos": "usa", "eeuu": "usa", "ee.uu.": "usa", "usa": "usa", "united states": "usa",
    "marruecos": "morocco", "morocco": "morocco",
    "suiza": "switzerland", "switzerland": "switzerland",
    "japon": "japan", "japón": "japan", "japan": "japan",
    "corea del sur": "south-korea", "south korea": "south-korea",
    "iran": "iran", "irán": "iran",
    "canada": "canada", "canadá": "canada",
    "tunez": "tunisia", "túnez": "tunisia", "tunisia": "tunisia",
    "costa de marfil": "ivory-coast", "ivory coast": "ivory-coast",
    "arabia saudi": "saudi-arabia", "arabia saudí": "saudi-arabia", "saudi arabia": "saudi-arabia",
    "catar": "qatar", "qatar": "qatar",
    "egipto": "egypt", "egypt": "egypt",
    "argelia": "algeria", "algeria": "algeria",
    "escocia": "scotland", "scotland": "scotland",
    "chequia": "czech-republic", "republica checa": "czech-republic", "república checa": "czech-republic", "czech republic": "czech-republic", "czechia": "czech-republic",
    "bosnia": "bosnia-and-herzegovina", "bosnia y herzegovina": "bosnia-and-herzegovina", "bosnia and herzegovina": "bosnia-and-herzegovina",
    "sudafrica": "south-africa", "sudáfrica": "south-africa", "south africa": "south-africa",
    "nueva zelanda": "new-zealand", "new zealand": "new-zealand",
    "panama": "panama", "panamá": "panama",
    "jordania": "jordan", "jordan": "jordan",
    "haiti": "haiti", "haití": "haiti",
    "noruega": "norway", "norway": "norway",
    "suecia": "sweden", "sweden": "sweden",
    "turquia": "turkey", "turquía": "turkey", "turkey": "turkey",
    "austria": "austria",
    "irak": "iraq", "iraq": "iraq",
    "uzbekistan": "uzbekistan", "uzbekistán": "uzbekistan",
    "cabo verde": "cape-verde", "cape verde": "cape-verde",
    "rd congo": "dr-congo", "republica democratica del congo": "dr-congo", "república democrática del congo": "dr-congo", "dr congo": "dr-congo",
    "curazao": "curacao", "curacao": "curacao", "curaçao": "curacao",
}


def normalizar_texto(texto: str) -> str:
    texto = texto.strip().lower().replace("_", " ").replace("-", " ")
    texto = " ".join(texto.split())
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return texto


def resolver_equipo(nombre: str) -> str:
    if not nombre:
        raise ValueError("Equipo vacío")
    clave = normalizar_texto(nombre)
    if clave in ALIASES_EXTRA:
        return ALIASES_EXTRA[clave]
    slug = clave.replace(" ", "-")
    if slug in RATINGS:
        return slug
    for slug_existente, nombre_es in NOMBRES_ES.items():
        if normalizar_texto(nombre_es) == clave:
            return slug_existente
    disponibles = ", ".join(NOMBRES_ES[k] for k in sorted(RATINGS))
    raise ValueError(f"Equipo no reconocido: '{nombre}'. Equipos disponibles: {disponibles}")


def expected_score(rating_a: float, rating_b: float, home_bonus_a: float = 0) -> float:
    return 1 / (1 + 10 ** ((rating_b - (rating_a + home_bonus_a)) / 400))


def expected_goals(rating: float, opponent: float, home_bonus: float = 0) -> float:
    diff = (rating + home_bonus) - opponent
    lamb = 1.35 + diff / 400
    return max(0.3, min(3.5, lamb))


def poisson_pmf(k: int, lamb: float) -> float:
    if lamb <= 0:
        return 1.0 if k == 0 else 0.0
    p = math.exp(-lamb)
    for i in range(1, k + 1):
        p *= lamb / i
    return p


def dc_tau(a: int, b: int, lamb: float, mu: float, rho: float = DC_RHO) -> float:
    if a == 0 and b == 0:
        return 1 - lamb * mu * rho
    if a == 0 and b == 1:
        return 1 + lamb * rho
    if a == 1 and b == 0:
        return 1 + mu * rho
    if a == 1 and b == 1:
        return 1 - rho
    return 1.0


def matriz_marcadores(lamb: float, mu: float, max_goals: int = MAX_GOALS, dixon_coles: bool = True) -> List[Tuple[int, int, float]]:
    datos: List[Tuple[int, int, float]] = []
    for a in range(max_goals + 1):
        pa = poisson_pmf(a, lamb)
        for b in range(max_goals + 1):
            p = pa * poisson_pmf(b, mu)
            if dixon_coles:
                p *= dc_tau(a, b, lamb, mu)
            datos.append((a, b, p))
    total = sum(p for _, _, p in datos) or 1.0
    datos = [(a, b, p / total) for a, b, p in datos]
    datos.sort(key=lambda x: x[2], reverse=True)
    return datos


def probabilidades_90(slug_a: str, slug_b: str, home_bonus_a: int = 0) -> Tuple[float, float, float, float, float, List[Tuple[int, int, float]]]:
    ra, rb = RATINGS[slug_a], RATINGS[slug_b]
    lamb = expected_goals(ra, rb, home_bonus_a)
    mu = expected_goals(rb, ra, -home_bonus_a / 2)
    score_probs = matriz_marcadores(lamb, mu)
    win_a = sum(p for a, b, p in score_probs if a > b)
    draw = sum(p for a, b, p in score_probs if a == b)
    win_b = sum(p for a, b, p in score_probs if a < b)
    total = win_a + draw + win_b or 1.0
    return win_a / total, draw / total, win_b / total, lamb, mu, score_probs


def elegir_marcador(score_probs: List[Tuple[int, int, float]], rng: random.Random) -> Tuple[int, int]:
    r = rng.random()
    acc = 0.0
    for a, b, p in score_probs:
        acc += p
        if r <= acc:
            return a, b
    return score_probs[-1][0], score_probs[-1][1]


def simular_penaltis(slug_a: str, slug_b: str, home_bonus_a: int, rng: random.Random) -> Tuple[str, int, int, float]:
    ra, rb = RATINGS[slug_a], RATINGS[slug_b]
    p_a = expected_score(ra, rb, home_bonus_a)
    # Suavizado: en penaltis nadie debe tener una probabilidad extrema.
    p_a = max(0.42, min(0.58, p_a))
    ganador_a = rng.random() < p_a
    # Marcadores habituales de tanda. Se evita empate por definición.
    opciones = [(4, 3), (5, 4), (3, 2), (4, 2), (5, 3)]
    pa, pb = rng.choice(opciones)
    if ganador_a:
        return slug_a, pa, pb, p_a
    return slug_b, pb, pa, p_a


def etiqueta_partido(prob_a: float, prob_b: float, prob_empate: float) -> str:
    diff = abs(prob_a - prob_b)
    if prob_empate >= 0.30 and diff < 0.12:
        return "alto riesgo de prórroga"
    if diff < 0.08:
        return "duelo igualado"
    if diff < 0.18:
        return "partido abierto"
    return "favorito claro"


def equipo_json(slug: Optional[str]) -> Optional[dict]:
    if not slug:
        return None
    return {
        "slug": slug,
        "nombre": NOMBRES_ES.get(slug, slug),
        "codigo": CODIGOS.get(slug, slug[:3].upper()),
        "bandera": BANDERAS.get(slug, "🏳️"),
        "flag_url": flag_url(slug),
        "rating": RATINGS.get(slug),
    }




def marcador_esperado_coherente_con_xg(score_probs: List[Tuple[int, int, float]], xg_a: float, xg_b: float) -> Tuple[int, int]:
    """Elige un marcador principal que sea coherente con los xG.

    El marcador más probable puro de Poisson puede ser 1-1 aunque un equipo tenga más xG.
    Para una UI de predicción, conviene que el resultado destacado respete la dirección de los xG:
    - si el xG de A es claramente mayor, el marcador esperado debe favorecer a A;
    - si el xG de B es claramente mayor, debe favorecer a B;
    - si la diferencia es mínima, se permite empate y la eliminatoria se decide después.
    """
    diferencia = xg_a - xg_b
    umbral_empate = 0.18

    if abs(diferencia) <= umbral_empate:
        candidatos = [(a, b, p) for a, b, p in score_probs if a == b]
    elif diferencia > 0:
        candidatos = [(a, b, p) for a, b, p in score_probs if a > b]
    else:
        candidatos = [(a, b, p) for a, b, p in score_probs if b > a]

    if not candidatos:
        candidatos = score_probs

    # Equilibrio entre cercanía a los xG y probabilidad del marcador.
    # La parte xG manda; la probabilidad desempata entre marcadores parecidos.
    def coste(item: Tuple[int, int, float]) -> float:
        a, b, p = item
        distancia_xg = abs(a - xg_a) + abs(b - xg_b)
        penalizacion_prob = -math.log(max(p, 1e-9)) * 0.08
        penalizacion_goles = max(0, a + b - 6) * 0.35
        return distancia_xg + penalizacion_prob + penalizacion_goles

    a, b, _ = min(candidatos, key=coste)
    return a, b


def resultado_esperado_eliminatoria(
    slug_a: str,
    slug_b: str,
    xg_a: float,
    xg_b: float,
    xg_prorroga_a: float,
    xg_prorroga_b: float,
    prob_clasifica_a: float,
    prob_clasifica_b: float,
    prob_penaltis_a: float,
    score_probs: List[Tuple[int, int, float]],
) -> dict:
    """Construye el resultado principal esperado con el marcador más probable del modelo.

    Importante para la UI:
    - el marcador base de 90' SIEMPRE es el marcador puntual más probable de la matriz Poisson;
    - si ese marcador es empate, la eliminatoria se resuelve después por prórroga o penaltis;
    - no es una muestra aleatoria, por lo que al recalcular no cambia sin cambiar los ratings/datos.
    """
    # Marcador puntual más probable según la matriz del modelo.
    g90_a, g90_b, _ = score_probs[0]
    pr_a = pr_b = 0
    pen_a = pen_b = None
    metodo = "90 minutos"

    if g90_a > g90_b:
        ganador = slug_a
    elif g90_b > g90_a:
        ganador = slug_b
    else:
        # Si el marcador más probable a 90' es empate, la eliminatoria se decide de forma determinista.
        diff_prorroga = xg_prorroga_a - xg_prorroga_b
        favorito = slug_a if prob_clasifica_a >= prob_clasifica_b else slug_b
        if abs(diff_prorroga) >= 0.10:
            if diff_prorroga > 0:
                pr_a, pr_b = 1, 0
                ganador = slug_a
            else:
                pr_a, pr_b = 0, 1
                ganador = slug_b
            metodo = "prórroga"
        else:
            ganador = favorito
            metodo = "penaltis"
            if ganador == slug_a:
                pen_a, pen_b = (5, 4) if prob_penaltis_a >= 0.50 else (4, 3)
            else:
                pen_a, pen_b = (4, 5) if prob_penaltis_a >= 0.50 else (3, 4)

    return {
        "goles_90_a": g90_a,
        "goles_90_b": g90_b,
        "goles_prorroga_a": pr_a,
        "goles_prorroga_b": pr_b,
        "total_a": g90_a + pr_a,
        "total_b": g90_b + pr_b,
        "penaltis_a": pen_a,
        "penaltis_b": pen_b,
        "ganador": equipo_json(ganador),
        "metodo": metodo,
        "nota": "Resultado determinista: usa el marcador puntual más probable del modelo a 90'. Si ese marcador es empate, la eliminatoria se resuelve por prórroga o penaltis.",
    }


def predecir_partido(equipo_a: str, equipo_b: str, local: Optional[str] = None, seed: Optional[int] = None) -> dict:
    slug_a = resolver_equipo(equipo_a)
    slug_b = resolver_equipo(equipo_b)
    if slug_a == slug_b:
        raise ValueError("Debes elegir dos equipos distintos.")

    home_bonus_a = 0
    if local:
        slug_local = resolver_equipo(local)
        if slug_local == slug_a:
            home_bonus_a = HOME_BONUS
        elif slug_local == slug_b:
            home_bonus_a = -HOME_BONUS
        else:
            raise ValueError("El equipo local debe ser uno de los dos equipos del partido.")

    rng = random.Random(seed)
    prob_a, prob_empate, prob_b, xg_a, xg_b, score_probs = probabilidades_90(slug_a, slug_b, home_bonus_a)

    # xGoals de prórroga: son condicionales a que el partido llegue empatado al minuto 90.
    # No cuentan penaltis porque las tandas no generan xG de juego.
    xg_prorroga_a = xg_a * EXTRA_TIME_FACTOR
    xg_prorroga_b = xg_b * EXTRA_TIME_FACTOR
    score_probs_et = matriz_marcadores(
        xg_prorroga_a,
        xg_prorroga_b,
        max_goals=MAX_GOALS_PRORROGA,
        dixon_coles=False,
    )
    prob_gana_prorroga_a_cond = sum(p for a, b, p in score_probs_et if a > b)
    prob_empate_prorroga_cond = sum(p for a, b, p in score_probs_et if a == b)
    prob_gana_prorroga_b_cond = sum(p for a, b, p in score_probs_et if a < b)

    prob_penaltis_a = expected_score(RATINGS[slug_a], RATINGS[slug_b], home_bonus_a)
    # Suavizado: una tanda de penaltis es muy ruidosa, incluso si un equipo es bastante superior.
    prob_penaltis_a = max(0.42, min(0.58, prob_penaltis_a))

    prob_prorroga = prob_empate
    prob_penaltis = prob_empate * prob_empate_prorroga_cond
    prob_clasifica_a = prob_a + prob_empate * (
        prob_gana_prorroga_a_cond + prob_empate_prorroga_cond * prob_penaltis_a
    )
    prob_clasifica_b = prob_b + prob_empate * (
        prob_gana_prorroga_b_cond + prob_empate_prorroga_cond * (1 - prob_penaltis_a)
    )

    # xG total esperado en una eliminatoria = xG 90' + probabilidad de prórroga * xG de prórroga.
    # Es menor que xG90 + xGPrórroga porque la prórroga no siempre se juega.
    xg_total_a = xg_a + prob_prorroga * xg_prorroga_a
    xg_total_b = xg_b + prob_prorroga * xg_prorroga_b

    esperado = resultado_esperado_eliminatoria(
        slug_a,
        slug_b,
        xg_a,
        xg_b,
        xg_prorroga_a,
        xg_prorroga_b,
        prob_clasifica_a,
        prob_clasifica_b,
        prob_penaltis_a,
        score_probs,
    )

    # La predicción principal que se muestra en la UI NO es aleatoria.
    # El marcador base de la UI es siempre el marcador puntual más probable del modelo.
    # Si ese marcador es empate, la eliminatoria se resuelve después por prórroga o penaltis.

    ma_puntual, mb_puntual, mp_puntual = score_probs[0]
    top_scores = [{"a": a, "b": b, "probabilidad": round(p, 4)} for a, b, p in score_probs[:5]]
    marcador_ui_a = esperado["goles_90_a"]
    marcador_ui_b = esperado["goles_90_b"]
    prob_marcador_ui = next((p for a, b, p in score_probs if a == marcador_ui_a and b == marcador_ui_b), 0.0)

    nombre_a, nombre_b = NOMBRES_ES[slug_a], NOMBRES_ES[slug_b]
    favorito = slug_a if prob_clasifica_a >= prob_clasifica_b else slug_b
    etiqueta = etiqueta_partido(prob_a, prob_b, prob_empate)
    texto = (
        f"{NOMBRES_ES[favorito]} aparece con más opciones de clasificarse. "
        f"El modelo estima {xg_a:.2f}-{xg_b:.2f} xG a 90 minutos "
        f"y {xg_total_a:.2f}-{xg_total_b:.2f} xG esperados totales ponderando la posibilidad de prórroga. "
        f"A 90 minutos, {nombre_a} gana el {prob_a*100:.1f}%, el empate aparece en el {prob_empate*100:.1f}% "
        f"y {nombre_b} gana el {prob_b*100:.1f}%. Al ser eliminatoria, la UI usa como base el marcador puntual más probable del modelo; si ese marcador acaba empatado, se resuelve con prórroga o penaltis de forma determinista según las probabilidades."
    )

    return {
        "equipo_a": equipo_json(slug_a),
        "equipo_b": equipo_json(slug_b),
        "xg": {"a": round(xg_a, 2), "b": round(xg_b, 2)},
        "xg_detalle": {
            "noventa_minutos": {"a": round(xg_a, 2), "b": round(xg_b, 2)},
            "prorroga_condicional": {"a": round(xg_prorroga_a, 2), "b": round(xg_prorroga_b, 2)},
            "total_eliminatoria_esperado": {"a": round(xg_total_a, 2), "b": round(xg_total_b, 2)},
            "diferencia_90": round(xg_a - xg_b, 2),
            "diferencia_total": round(xg_total_a - xg_total_b, 2),
            "nota": "Los xG de prórroga son condicionales a que el partido llegue empatado al minuto 90. Los penaltis no suman xG.",
        },
        "probabilidades_90": {
            "a": round(prob_a, 4),
            "empate": round(prob_empate, 4),
            "b": round(prob_b, 4),
        },
        "probabilidades_eliminatoria": {
            "clasifica_a": round(prob_clasifica_a, 4),
            "clasifica_b": round(prob_clasifica_b, 4),
            "prorroga": round(prob_prorroga, 4),
            "gana_prorroga_a_condicional": round(prob_gana_prorroga_a_cond, 4),
            "empate_prorroga_condicional": round(prob_empate_prorroga_cond, 4),
            "gana_prorroga_b_condicional": round(prob_gana_prorroga_b_cond, 4),
            "penaltis": round(prob_penaltis, 4),
            "penaltis_a_condicional": round(prob_penaltis_a, 4),
            "penaltis_b_condicional": round(1 - prob_penaltis_a, 4),
        },
        # Marcador base que usa la UI: siempre coincide con el marcador puntual más probable.
        "marcador_mas_probable": {"a": marcador_ui_a, "b": marcador_ui_b, "probabilidad": round(prob_marcador_ui, 4)},
        "marcador_puntual_mas_probable": {"a": ma_puntual, "b": mb_puntual, "probabilidad": round(mp_puntual, 4)},
        "marcadores_top": top_scores,
        "resultado_esperado": esperado,
        "simulacion": esperado,
        "favorito": equipo_json(favorito),
        "etiqueta": etiqueta,
        "analisis": texto,
    }


def listar_equipos() -> List[dict]:
    return [equipo_json(slug) for slug in sorted(RATINGS, key=lambda s: NOMBRES_ES[s])]
