"""Wildfire spread simulation on a terrain grid.

Model 1 (required)  : DeterministicFireModel - a Rothermel-style empirical spread rate
                      (fuel dryness x wind x slope) turned into fire arrival times.
Model 2 (advanced)  : ProbabilisticFireModel - the same physics run many times with
                      random wind gusts and patchy vegetation (Monte Carlo burn probability).
Model 3 (optional)  : ParticleFireModel - front-tracking particles carried outward by the same
                      spread rate; free of the grid bias of the shortest-path models.

Spread-rate form follows the empirical wind/slope factors used in cellular-automata
fire models (Alexandridis et al., 2008), which simplify Rothermel (1972):
    rate = base_rate * fuel_factor * exp(c1 V) * exp(c2 V (cos a - 1)) * exp(k * slope_deg)
where V is wind speed (m/s), a the angle between wind and spread direction.
Arrival times are found with Dijkstra's shortest-path algorithm over the 8-neighbour grid.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.ndimage import binary_erosion, gaussian_filter, label
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import dijkstra

C1, C2, SLOPE_K = 0.045, 0.131, 0.078
BASE_RATE_M_MIN = 4.0  # metres per minute on flat, still, fully dry fuel
NEIGHBOURS = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]  # (drow, dcol)


def dryness_from_wetness(wetness: float) -> float:
    """Map forecast root-zone soil wetness (0..1) to a fuel dryness index (0..1)."""
    return float(np.clip((0.8 - wetness) / 0.6, 0.0, 1.0))


@dataclass
class FireScenario:
    """Everything that defines one fire: terrain, ignition point, fuel dryness and wind."""

    dem: np.ndarray                 # elevation, metres, row 0 = south
    ignition: tuple[int, int]       # (row, col)
    dryness: float                  # 0..1, from the soil forecast
    wind_speed_ms: float = 5.0
    wind_toward_deg: float = 45.0   # compass bearing the wind blows TOWARD (0 = north, 90 = east)
    cell_m: float = 30.0

    def __post_init__(self):
        """Reject an ignition point off the grid or a dryness outside 0 to 1."""
        rows, cols = self.dem.shape
        r, c = self.ignition
        if not (0 <= r < rows and 0 <= c < cols):
            raise ValueError("ignition point is outside the terrain grid")
        if not 0.0 <= self.dryness <= 1.0:
            raise ValueError("dryness must be between 0 and 1")


def _arrival_times(dem, ignition, dryness, wind_speed, wind_deg, cell_m, fuel_field=None) -> np.ndarray:
    """Minutes until fire reaches each cell (inf = never). Core of both models."""
    rows, cols = dem.shape
    n = rows * cols
    idx = np.arange(n).reshape(rows, cols)
    fuel = (0.15 + 0.85 * dryness) * np.ones((rows, cols))
    if fuel_field is not None:
        fuel = fuel * fuel_field
    src, dst, cost = [], [], []
    for dr, dc in NEIGHBOURS:
        r0, r1 = max(0, -dr), rows - max(0, dr)
        c0, c1 = max(0, -dc), cols - max(0, dc)
        a = idx[r0:r1, c0:c1]
        b = idx[r0 + dr:r1 + dr, c0 + dc:c1 + dc]
        dist = cell_m * np.hypot(dr, dc)
        dz = dem[r0 + dr:r1 + dr, c0 + dc:c1 + dc] - dem[r0:r1, c0:c1]
        slope_deg = np.clip(np.degrees(np.arctan2(dz, dist)), -30, 30)
        # spread bearing: drow = north (+), dcol = east (+)
        bearing = np.degrees(np.arctan2(dc, dr)) % 360
        cos_a = np.cos(np.radians(bearing - wind_deg))
        wind_f = np.exp(C1 * wind_speed) * np.exp(C2 * wind_speed * (cos_a - 1.0))
        rate = BASE_RATE_M_MIN * fuel[r0:r1, c0:c1] * wind_f * np.exp(SLOPE_K * slope_deg)
        src.append(a.ravel())
        dst.append(b.ravel())
        cost.append((dist / np.maximum(rate, 1e-6)).ravel())
    graph = csr_matrix((np.concatenate(cost), (np.concatenate(src), np.concatenate(dst))), shape=(n, n))
    t = dijkstra(graph, directed=True, indices=int(idx[ignition]))
    return t.reshape(rows, cols)


def burned_mask(arrival_min: np.ndarray, t_min: float) -> np.ndarray:
    """Boolean map of cells the fire has reached by ``t_min`` minutes."""
    return arrival_min <= t_min


def iou(a: np.ndarray, b: np.ndarray) -> float:
    """Intersection over Union of two boolean masks (1.0 = identical)."""
    union = np.logical_or(a, b).sum()
    return float(np.logical_and(a, b).sum() / union) if union else 1.0


def perimeter_mask(mask: np.ndarray) -> np.ndarray:
    """Segment the fire front: burned cells that touch an unburned cell (image erosion with SciPy)."""
    return mask & ~binary_erosion(mask, border_value=1)


def perimeter_km(mask: np.ndarray, cell_m: float) -> float:
    """Length of the burn boundary in km: the exposed cell edges between burned and unburned cells."""
    m = np.pad(mask.astype(np.int8), 1)
    edges = np.abs(np.diff(m, axis=0)).sum() + np.abs(np.diff(m, axis=1)).sum()
    return float(edges * cell_m / 1000.0)


def count_burn_regions(mask: np.ndarray) -> int:
    """Number of separate burned patches (connected-component labelling with SciPy)."""
    return int(label(mask)[1])


class DeterministicFireModel:
    """One fire front per scenario: the same inputs always give the same arrival times."""

    name = "Deterministic (Rothermel-style)"

    def run(self, sc: FireScenario) -> np.ndarray:
        """Minutes until the fire reaches each cell (infinity if it never does)."""
        return _arrival_times(sc.dem, sc.ignition, sc.dryness, sc.wind_speed_ms,
                              sc.wind_toward_deg, sc.cell_m)


class ProbabilisticFireModel:
    """Monte Carlo ensemble: gusty wind direction/speed plus patchy fuel."""

    name = "Probabilistic (Monte Carlo)"

    def __init__(self, n_runs: int = 40, seed: int = 0, wind_dir_sd: float = 18.0,
                 gust_sd: float = 0.25, patch_sd: float = 0.35):
        """Set the ensemble size, random seed and how much wind and fuel vary between runs."""
        self.n_runs, self.seed = n_runs, seed
        self.wind_dir_sd, self.gust_sd, self.patch_sd = wind_dir_sd, gust_sd, patch_sd

    def run(self, sc: FireScenario) -> np.ndarray:
        """Returns arrival times of shape (n_runs, rows, cols)."""
        rng = np.random.default_rng(self.seed)
        out = np.empty((self.n_runs, *sc.dem.shape))
        for i in range(self.n_runs):
            patches = gaussian_filter(rng.normal(size=sc.dem.shape), sigma=4)
            patches = patches / (patches.std() + 1e-9)
            fuel_field = np.exp(self.patch_sd * patches)
            out[i] = _arrival_times(
                sc.dem, sc.ignition, sc.dryness,
                sc.wind_speed_ms * rng.lognormal(0.0, self.gust_sd),
                sc.wind_toward_deg + rng.normal(0.0, self.wind_dir_sd),
                sc.cell_m, fuel_field)
        return out

    @staticmethod
    def burn_probability(arrivals: np.ndarray, t_min: float) -> np.ndarray:
        """Fraction of ensemble runs in which each cell has burned by ``t_min`` minutes."""
        return (arrivals <= t_min).mean(axis=0)


def _wrap180(deg: np.ndarray) -> np.ndarray:
    """Wrap angle differences into [-180, 180)."""
    return (deg + 180.0) % 360.0 - 180.0


class ParticleFireModel:
    """Optional third model: a ring of front particles, each advancing along its own heading.

    Every step a particle moves at the local spread rate (fuel x wind x slope along its heading) with a
    little heading noise. New particles are inserted wherever neighbours drift apart so the front stays
    resolved, and the area inside the ring is marked burned with that step's time. Because particles move
    in continuous space, the result has no 8-neighbour grid bias.
    """

    name = "Particle flow"

    def __init__(self, n_start: int = 180, dt_min: float = 2.0, max_min: float = 720.0,
                 jitter_deg: float = 1.0, max_particles: int = 3000, seed: int = 0):
        """Set the number of starting particles, time step, horizon, heading noise and random seed."""
        self.n_start, self.dt_min, self.max_min = n_start, dt_min, max_min
        self.jitter_deg, self.max_particles, self.seed = jitter_deg, max_particles, seed

    def run(self, sc: FireScenario) -> np.ndarray:
        """Minutes until the front first covers each cell (infinity if it never does)."""
        from PIL import Image, ImageDraw

        rows, cols = sc.dem.shape
        r0, c0 = sc.ignition
        rng = np.random.default_rng(self.seed)
        phi = np.linspace(0.0, 360.0, self.n_start, endpoint=False)   # heading, compass degrees
        x = np.full(self.n_start, float(c0))
        y = np.full(self.n_start, float(r0))
        fuel = 0.15 + 0.85 * sc.dryness
        wind_f_scale = np.exp(C1 * sc.wind_speed_ms)
        arrival = np.full((rows, cols), np.inf)
        arrival[r0, c0] = 0.0
        t = 0.0
        while t < self.max_min:
            t += self.dt_min
            rad = np.radians(phi)
            east, north = np.sin(rad), np.cos(rad)
            ix, iy = np.clip(np.rint(x).astype(int), 0, cols - 1), np.clip(np.rint(y).astype(int), 0, rows - 1)
            jx = np.clip(np.rint(x + east).astype(int), 0, cols - 1)
            jy = np.clip(np.rint(y + north).astype(int), 0, rows - 1)
            slope = np.clip(np.degrees(np.arctan2(sc.dem[jy, jx] - sc.dem[iy, ix], sc.cell_m)), -30, 30)
            cos_a = np.cos(np.radians(phi - sc.wind_toward_deg))
            rate = (BASE_RATE_M_MIN * fuel * wind_f_scale * np.exp(C2 * sc.wind_speed_ms * (cos_a - 1.0))
                    * np.exp(SLOPE_K * slope))                                    # metres per minute
            step = rate * self.dt_min / sc.cell_m                                 # cells per time step
            phi = phi + rng.normal(0.0, self.jitter_deg, phi.size)
            x = np.clip(x + east * step, 0, cols - 1)
            y = np.clip(y + north * step, 0, rows - 1)
            nx, ny = np.roll(x, -1), np.roll(y, -1)
            gap = np.hypot(nx - x, ny - y)
            ins = np.nonzero(gap > 1.2)[0]                                        # keep the front resolved
            if ins.size and x.size + ins.size <= self.max_particles:
                mphi = phi[ins] + 0.5 * _wrap180(phi[(ins + 1) % phi.size] - phi[ins])
                x = np.insert(x, ins + 1, (x[ins] + nx[ins]) / 2)
                y = np.insert(y, ins + 1, (y[ins] + ny[ins]) / 2)
                phi = np.insert(phi, ins + 1, mphi)
            img = Image.new("1", (cols, rows), 0)
            ImageDraw.Draw(img).polygon(list(zip(x.tolist(), y.tolist())), fill=1)
            newly = np.asarray(img, dtype=bool) & np.isinf(arrival)
            arrival[newly] = t
        return arrival

