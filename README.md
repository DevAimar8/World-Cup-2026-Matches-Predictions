# Predicción del Mundial de Aimar

Bracket editable del Mundial 2026 con HTML/CSS/JS + Flask + modelo Python.

## Qué incluye

- UI renovada con estilo más limpio e inspirado en AimarDev.
- Bracket de eliminatorias editable.
- Pantalla propia por partido.
- Banderas de cada selección mediante `flagcdn.com`, con emoji como fallback.
- Predicción con Elo + Poisson/Dixon-Coles.
- xGoals a 90 minutos, xG de prórroga condicional y xG total esperado.
- Resultado principal grande: `Pasa X`, marcador y método.
- Métodos de resolución:
  - 90 minutos
  - 120 minutos / prórroga
  - penaltis con formato `1(5) - 1(4)`
- Guardar simulación y avanzar al ganador.
- Registrar resultado real, bloquear el partido y avanzar al ganador.
- Estado persistente en `data/bracket_state.json`.

## Ejecutar en Windows PowerShell

```powershell
cd Downloads
cd bracket-mundial-2026-aimar-ui-v3

python -m venv .venv
.venv\Scripts\activate

pip install -r requirements.txt
python app.py
```

Después abre:

```text
http://127.0.0.1:5000
```

## Uso

1. Abre el bracket.
2. Haz clic en un partido.
3. Pulsa **Calcular predicción** o **Simular y avanzar**.
4. Si ya se jugó el partido, introduce el resultado real y pulsa **Guardar resultado real y avanzar**.

Los resultados reales no se sobrescriben con simulaciones.

## Nota sobre datos

Este proyecto no descarga datos oficiales de FIFA automáticamente. El bracket y el modelo funcionan localmente. Los cambios que hagas desde la UI se guardan en `data/bracket_state.json`.
