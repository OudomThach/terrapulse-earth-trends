import numpy as np
import pytest

from terrapulse import questions as Q
from terrapulse.trends import TrendResult
from terrapulse.variables import VARIABLES


def res(code, slope, q=0.001, usable=True, jump=False):
    r = TrendResult(code, usable, slope=slope, p=q, q=q, z=3.0 * np.sign(slope or 1), mean=1.0,
                    years=np.arange(1990, 2026), annual=np.zeros(36))
    if jump:                                   # make suspicious_jump True
        r.jump_year, r.jump_p, r.jump_fit_ratio = 2001, 0.001, 0.2
    return r


def test_every_question_uses_catalogued_variables_and_valid_polarity():
    assert len(Q.QUESTIONS) == len({q.id for q in Q.QUESTIONS}) == len({q.text for q in Q.QUESTIONS})
    for q in Q.QUESTIONS:
        assert q.clues and q.why and q.up and q.down and q.none
        assert set(q.clues) <= set(VARIABLES) and set(q.clues.values()) <= {1, -1}


def test_clear_up_answer_and_strongest_clue():
    q = Q.QUESTIONS_BY_ID["hotter"]
    a = Q.answer(q, {"T2M": res("T2M", 0.05), "T2M_MAX": res("T2M_MAX", 0.03, q=0.01),
                     "T2M_MIN": res("T2M_MIN", 0.09, q=0.0001), "TS": res("TS", 0.04, q=0.4)})
    assert a.outcome == "up" and a.headline == q.up and a.tone == "sig"
    assert "3 of 4" in a.body and "night-time low" in a.body       # strongest = lowest q, ties by |z|; names the clue


def test_polarity_makes_falling_frost_mean_a_shrinking_cold_season():
    q = Q.QUESTIONS_BY_ID["cold"]
    a = Q.answer(q, {"FROST_DAYS": res("FROST_DAYS", -0.08), "SNODP": res("SNODP", -0.5)})
    assert a.outcome == "up" and a.headline == q.up
    b = Q.answer(q, {"FROST_DAYS": res("FROST_DAYS", 0.08), "SNODP": res("SNODP", 0.5)})
    assert b.outcome == "down"


def test_opposite_signals_give_a_mixed_answer():
    q = Q.QUESTIONS_BY_ID["land"]
    a = Q.answer(q, {"PRECTOTCORR": res("PRECTOTCORR", 0.1), "GWETROOT": res("GWETROOT", -0.01),
                     "GWETTOP": res("GWETTOP", 0.0, q=0.9)})
    assert a.outcome == "mixed" and a.headline == "A mixed picture" and a.tone == "weak"


def test_nothing_significant_reports_closest_clue_honestly():
    q = Q.QUESTIONS_BY_ID["wind"]
    a = Q.answer(q, {"WS10M": res("WS10M", 0.01, q=0.31)})
    assert a.outcome == "none" and "0.31" in a.body and a.tone == "none"


def test_suspected_data_jumps_are_excluded_and_disclosed():
    q = Q.QUESTIONS_BY_ID["sun"]
    results = {"ALLSKY_SFC_SW_DWN": res("ALLSKY_SFC_SW_DWN", 0.2, q=0.5),
               "CLOUD_AMT": res("CLOUD_AMT", -8.0, q=0.001, jump=True), "AOD_55": res("AOD_55", 0.0, usable=False)}
    a = Q.answer(q, results)
    assert a.outcome == "none" and "possible data jump" in a.body and "cloud cover" in a.body


def test_unknown_when_no_clue_is_testable():
    q = Q.QUESTIONS_BY_ID["ozone"]
    assert Q.answer(q, {"TO3": res("TO3", 0.0, usable=False)}).outcome == "unknown"
    assert Q.answer(q, {}).outcome == "unknown"


def test_surprise_me_picks_clearest_clean_signals():
    results = {"T2M": res("T2M", 0.05, q=0.0001), "TS": res("TS", 0.04, q=0.02),
               "CLOUD_AMT": res("CLOUD_AMT", 9, q=0.000001, jump=True), "PS": res("PS", 0.0, usable=False),
               "WS10M": res("WS10M", -0.1, q=0.3)}
    assert Q.surprise_me(results, k=2) == ["T2M", "TS"]            # jump-flagged and untestable are skipped
