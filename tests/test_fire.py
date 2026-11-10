import numpy as np
import pytest

from terrapulse import fire


def flat(n=41):
    return np.full((n, n), 500.0)


def scenario(dem=None, **kw):
    dem = flat() if dem is None else dem
    c = dem.shape[0] // 2
    args = dict(ignition=(c, c), dryness=0.8, wind_speed_ms=0.0, wind_toward_deg=90.0)
    args.update(kw)
    return fire.FireScenario(dem, **args)


def test_dryness_mapping_bounds():
    assert fire.dryness_from_wetness(0.9) == 0.0
    assert fire.dryness_from_wetness(0.2) == 1.0
    assert 0.0 < fire.dryness_from_wetness(0.5) < 1.0


def test_ignition_cell_burns_at_time_zero():
    sc = scenario()
    t = fire.DeterministicFireModel().run(sc)
    assert t[sc.ignition] == 0.0


def test_flat_calm_fire_is_symmetric():
    sc = scenario()
    t = fire.DeterministicFireModel().run(sc)
    c = sc.ignition[0]
    assert t[c, c + 8] == pytest.approx(t[c, c - 8])
    assert t[c + 8, c] == pytest.approx(t[c - 8, c])
    assert t[c, c + 8] == pytest.approx(t[c + 8, c])


def test_wind_makes_downwind_faster_than_upwind():
    sc = scenario(wind_speed_ms=8.0, wind_toward_deg=90.0)  # blowing east
    t = fire.DeterministicFireModel().run(sc)
    c = sc.ignition[0]
    assert t[c, c + 8] < t[c, c - 8]


def test_fire_runs_faster_uphill():
    n = 41
    dem = 500.0 + np.tile(np.arange(n) * 8.0, (n, 1))  # rises to the east
    sc = scenario(dem)
    t = fire.DeterministicFireModel().run(sc)
    c = n // 2
    assert t[c, c + 8] < t[c, c - 8]


def test_drier_fuel_burns_more_area():
    slow = fire.DeterministicFireModel().run(scenario(dryness=0.1))
    fast = fire.DeterministicFireModel().run(scenario(dryness=0.9))
    assert fire.burned_mask(fast, 120).sum() > fire.burned_mask(slow, 120).sum()


def test_burned_area_never_shrinks_over_time():
    t = fire.DeterministicFireModel().run(scenario(wind_speed_ms=4.0))
    areas = [fire.burned_mask(t, m).sum() for m in (10, 60, 120, 300)]
    assert areas == sorted(areas)


def test_invalid_scenarios_rejected():
    with pytest.raises(ValueError):
        scenario(ignition=(999, 0))
    with pytest.raises(ValueError):
        scenario(dryness=1.5)


def test_iou():
    a = np.array([[1, 1], [0, 0]], dtype=bool)
    assert fire.iou(a, a) == 1.0
    assert fire.iou(a, ~a) == 0.0
    assert fire.iou(np.zeros((2, 2), bool), np.zeros((2, 2), bool)) == 1.0


def test_probabilistic_model_shape_reproducible_and_valid_probabilities():
    sc = scenario(wind_speed_ms=5.0)
    pm = fire.ProbabilisticFireModel(n_runs=8, seed=3)
    a1, a2 = pm.run(sc), pm.run(sc)
    assert a1.shape == (8, *sc.dem.shape)
    assert np.array_equal(a1, a2)  # same seed -> same ensemble
    p = pm.burn_probability(a1, 90)
    assert p.min() >= 0.0 and p.max() <= 1.0
    assert p[sc.ignition] == 1.0


# ------------------------------------------------------------------ perimeter segmentation
def test_perimeter_of_a_square_block():
    m = np.zeros((10, 10), bool)
    m[3:7, 3:7] = True                                   # 4 x 4 block
    ring = fire.perimeter_mask(m)
    assert ring.sum() == 12                              # 16 cells minus the 2 x 2 interior
    assert not ring[4:6, 4:6].any()
    assert fire.perimeter_km(m, 30.0) == pytest.approx(16 * 30 / 1000)   # four sides of 4 cells


def test_perimeter_counts_the_grid_edge_as_boundary_only_for_cells_that_touch_unburned():
    full = np.ones((5, 5), bool)
    assert fire.perimeter_mask(full).sum() == 0          # nothing is unburned inside the grid
    assert fire.perimeter_km(np.zeros((5, 5), bool), 30.0) == 0.0


def test_count_burn_regions_and_fire_perimeter_grows_with_time():
    m = np.zeros((9, 9), bool)
    m[1:3, 1:3] = True
    m[6:8, 6:8] = True
    assert fire.count_burn_regions(m) == 2
    t = fire.DeterministicFireModel().run(scenario(wind_speed_ms=3.0))
    p = [fire.perimeter_km(fire.burned_mask(t, h), 30.0) for h in (30, 120, 240)]
    assert p[0] < p[1] < p[2]


# ------------------------------------------------------------------ particle model (optional third model)
def _area_ha(arrival, minutes):
    return float((arrival <= minutes).sum() * 0.09)


def test_particle_model_matches_analytic_circle_on_flat_calm_ground():
    sc = scenario(np.full((80, 80), 500.0), dryness=0.8, wind_speed_ms=0.0)
    expected = np.pi * (fire.BASE_RATE_M_MIN * (0.15 + 0.85 * 0.8) * 120) ** 2 / 1e4      # radius = rate x time
    particle = _area_ha(fire.ParticleFireModel().run(sc), 120)
    dijkstra = _area_ha(fire.DeterministicFireModel().run(sc), 120)
    assert particle == pytest.approx(expected, rel=0.15)
    assert dijkstra == pytest.approx(expected, rel=0.15)
    assert dijkstra < expected < particle * 1.01       # grid shortest-path under-reaches; the models bracket the truth


def test_particle_model_agrees_with_deterministic_model_and_responds_to_wind():
    dem = np.full((80, 80), 500.0)
    calm = scenario(dem, wind_speed_ms=0.0)
    windy = scenario(dem, wind_speed_ms=8.0, wind_toward_deg=90.0)
    a = fire.ParticleFireModel().run(windy)
    assert fire.iou(fire.burned_mask(a, 360), fire.burned_mask(fire.DeterministicFireModel().run(windy), 360)) > 0.8
    c = windy.ignition[0]
    assert a[c, c + 12] < a[c, c - 12]                 # downwind arrives first
    assert a[calm.ignition] == 0.0


def test_particle_model_is_reproducible_and_never_burns_backwards_in_time():
    sc = scenario(np.full((60, 60), 500.0), wind_speed_ms=4.0)
    first, second = fire.ParticleFireModel(seed=5).run(sc), fire.ParticleFireModel(seed=5).run(sc)
    assert np.array_equal(first, second)
    areas = [_area_ha(first, m) for m in (30, 120, 300)]
    assert areas == sorted(areas)
