"""Use TerraPulse as a library: no Streamlit needed.

    python examples/quickstart.py                 # Svalbard
    python examples/quickstart.py "Tibetan Plateau"

Shows the three reusable layers: data (climate), statistics (trends) and explanation (questions, narrative).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))   # allow running from the examples folder

from terrapulse import narrative, questions, trends
from terrapulse.climate import PLACES, load_monthly
from terrapulse.variables import CODES, VARIABLES


def main(place_name: str = "Svalbard, Arctic") -> None:
    """Load one place, scan all 20 variables, and answer a plain question, using only the analysis library."""
    place = PLACES[place_name]
    df = load_monthly(place.lat, place.lon)                    # 1. data: 20 monthly variables, 1990-2025
    results = trends.scan(df, CODES, 1990, 2025)               # 2. statistics: Mann-Kendall, Sen slope, FDR, jump check

    print(f"{place.name}: {sum(r.usable for r in results.values())} variables tested\n")
    ranked = sorted((r for r in results.values() if r.usable), key=lambda r: r.q)
    for r in ranked[:5]:                                       # 3. explanation: plain-language results
        v = VARIABLES[r.code]
        print(f"  {v.name:26s} {narrative.rate_text(v, r):28s} {trends.evidence_label(r.q)}")

    question = questions.QUESTIONS_BY_ID["hotter"]             # a guided question
    answer = questions.answer(question, results)
    print(f"\n{question.text} -> {answer.headline}. {answer.body}")


if __name__ == "__main__":
    main(*sys.argv[1:2])
