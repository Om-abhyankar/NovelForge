"""
Procedural map generation - build a world from parameters.

The pipeline, in order:

  1. **Heightmap.** Fractal value noise (several octaves of smoothed random
     grids) plus radial continent blobs, multiplied by an edge falloff so the
     map is surrounded by ocean rather than cut off mid-continent.
  2. **Sea level by percentile.** Rather than guessing a threshold, the heights
     are sorted and the cut taken at the requested land fraction - so "30% land"
     really gives 30% land on every seed.
  3. **Coastlines.** Connected land regions are labelled by flood fill and each
     one's boundary traced with Moore-neighbour tracing, then simplified with
     Douglas-Peucker. The result drops straight into the same Shape objects the
     hand-drawing tools produce, so generated and drawn maps are identical
     afterwards and every editing tool works on both.
  4. **Rivers.** Steepest-descent flow direction per cell, flow accumulation by
     processing cells from high to low, then trace the wettest cells downhill to
     the sea.
  5. **Biomes.** Temperature from latitude and altitude, moisture from noise and
     distance to water; the combination selects forest, desert, marsh or ice.
  6. **Settlements.** Every land cell is scored for habitability - coastal
     access, fresh water, gentle ground - and the best sites are taken with a
     minimum spacing so cities are not all in one corner.

Everything is seeded, so the same parameters always rebuild the same world.
Pure Python and the standard library; no numpy.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Set, Tuple

from .mapmaker import GameMap, Layer, MapLabel, Pin, Shape, generate_name

Point = Tuple[float, float]
Grid = List[List[float]]

# Working grid resolution. 220x150 is ~33,000 cells: fine enough for a
# convincing coastline, coarse enough to stay well under a second in pure
# Python. Detail comes from smoothing and simplification, not from cell count.
GRID_W = 220
GRID_H = 150


# ==========================================================================
# Parameters
# ==========================================================================

CLIMATES = {
    "temperate": "Temperate - mixed forest, four seasons",
    "tropical": "Tropical - jungle and swamp, hot and wet",
    "arid": "Arid - desert and dry scrub",
    "arctic": "Arctic - ice, tundra, short summers",
    "varied": "Varied - everything from ice caps to desert",
}

LANDMASS_SHAPES = {
    "continents": "A few large continents",
    "archipelago": "Many islands, little mainland",
    "pangaea": "One great supercontinent",
    "inland_sea": "Land surrounding an inland sea",
    "coastline": "One continent filling most of the map",
}


def seed_from_text(text: str) -> int:
    """
    Turn anything typed into a seed, the way Minecraft does.

    A run of digits is used as the number itself, so "12345" is the seed 12345
    and can be shared as such. Anything else is hashed with Java's String
    hashCode, which is the algorithm Minecraft uses - so a seed shared as a
    phrase always rebuilds the same world on any machine.

    Empty input returns 0; callers treat that as "pick one at random".
    """
    text = (text or "").strip()
    if not text:
        return 0
    if text.lstrip("-").isdigit():
        try:
            return abs(int(text)) & 0x7FFFFFFF
        except ValueError:
            pass
    h = 0
    for ch in text:
        h = (31 * h + ord(ch)) & 0xFFFFFFFF
    # Fold to a signed 32-bit range, then make it positive, exactly as Java's
    # hashCode would land before Minecraft takes the absolute value.
    if h >= 0x80000000:
        h -= 0x100000000
    return abs(h) & 0x7FFFFFFF


def random_seed() -> int:
    """A fresh seed for the 'surprise me' button."""
    return random.Random().randrange(1, 0x7FFFFFFF)


@dataclass
class MapParams:
    """Everything the generator needs. All of it is exposed in the dialog."""

    # 0 means "choose one at random". Any other value is used as given, so an
    # explicit seed still reproduces exactly. Defaulting to a real number here
    # would make a blank seed box silently generate the same world every time.
    seed: int = 0
    # What the writer actually typed, kept verbatim so the map can show the
    # seed back to them and they can share or re-enter it.
    seed_text: str = ""
    name: str = ""

    # --- land and water ------------------------------------------------
    shape: str = "continents"
    land_fraction: float = 0.34      # 0.05 - 0.85, share of the map that is land
    continents: int = 3              # major landmasses
    islands: int = 14                # scattered small islands
    roughness: float = 0.55          # 0 smooth coast, 1 deeply indented
    edge_water: float = 0.85         # how strongly the border is forced to ocean

    # --- relief ---------------------------------------------------------
    mountains: float = 0.45          # share of land that is mountainous
    hills: float = 0.35
    rivers: int = 8
    lakes: int = 4

    # --- climate --------------------------------------------------------
    climate: str = "temperate"
    forest: float = 0.4
    desert: float = 0.15
    marsh: float = 0.1
    ice_caps: bool = True

    # --- civilisation ---------------------------------------------------
    capitals: int = 2
    cities: int = 6
    towns: int = 12
    villages: int = 10
    ruins: int = 5
    landmarks: int = 4
    roads: bool = True
    name_flavour: str = "plain"
    name_places: bool = True

    # --- presentation ---------------------------------------------------
    width: int = 1800
    height: int = 1200
    style: str = "parchment"
    label_regions: bool = True
    scale_text: str = "200 leagues"

    def clamped(self) -> "MapParams":
        """Bring every value into a range the generator can actually handle."""
        p = MapParams(**self.__dict__)
        p.land_fraction = max(0.05, min(0.85, float(p.land_fraction)))
        p.roughness = max(0.0, min(1.0, float(p.roughness)))
        p.edge_water = max(0.0, min(1.0, float(p.edge_water)))
        p.mountains = max(0.0, min(1.0, float(p.mountains)))
        p.hills = max(0.0, min(1.0, float(p.hills)))
        p.forest = max(0.0, min(1.0, float(p.forest)))
        p.desert = max(0.0, min(1.0, float(p.desert)))
        p.marsh = max(0.0, min(1.0, float(p.marsh)))
        p.continents = max(1, min(12, int(p.continents)))
        p.islands = max(0, min(120, int(p.islands)))
        p.rivers = max(0, min(60, int(p.rivers)))
        p.lakes = max(0, min(40, int(p.lakes)))
        for attr in ("capitals", "cities", "towns", "villages", "ruins",
                     "landmarks"):
            setattr(p, attr, max(0, min(80, int(getattr(p, attr)))))
        p.width = max(600, min(6000, int(p.width)))
        p.height = max(400, min(6000, int(p.height)))
        # A typed seed always wins over a stale numeric one.
        if p.seed_text.strip():
            p.seed = seed_from_text(p.seed_text)
        if not p.seed:
            p.seed = random_seed()
        p.seed = int(p.seed) & 0x7FFFFFFF
        if p.shape not in LANDMASS_SHAPES:
            p.shape = "continents"
        if p.climate not in CLIMATES:
            p.climate = "temperate"
        return p


# ==========================================================================
# Noise
# ==========================================================================


def _smoothstep(t: float) -> float:
    return t * t * (3.0 - 2.0 * t)


def _value_noise(w: int, h: int, frequency: int, rng: random.Random) -> Grid:
    """One octave of value noise: a coarse random lattice, smoothly interpolated."""
    frequency = max(1, frequency)
    gw = frequency + 2
    gh = frequency + 2
    lattice = [[rng.random() for _ in range(gw)] for _ in range(gh)]

    out: Grid = [[0.0] * w for _ in range(h)]
    for y in range(h):
        fy = (y / max(1, h - 1)) * frequency
        y0 = int(fy)
        y1 = min(y0 + 1, gh - 1)
        ty = _smoothstep(fy - y0)
        row0 = lattice[y0]
        row1 = lattice[y1]
        row = out[y]
        for x in range(w):
            fx = (x / max(1, w - 1)) * frequency
            x0 = int(fx)
            x1 = min(x0 + 1, gw - 1)
            tx = _smoothstep(fx - x0)
            top = row0[x0] * (1.0 - tx) + row0[x1] * tx
            bottom = row1[x0] * (1.0 - tx) + row1[x1] * tx
            row[x] = top * (1.0 - ty) + bottom * ty
    return out


def _fbm(w: int, h: int, octaves: int, base_frequency: int,
         rng: random.Random, persistence: float = 0.5) -> Grid:
    """Fractal Brownian motion: octaves of noise at doubling frequency."""
    out: Grid = [[0.0] * w for _ in range(h)]
    amplitude = 1.0
    total = 0.0
    frequency = max(1, base_frequency)
    for _ in range(max(1, octaves)):
        layer = _value_noise(w, h, frequency, rng)
        for y in range(h):
            src = layer[y]
            dst = out[y]
            for x in range(w):
                dst[x] += src[x] * amplitude
        total += amplitude
        amplitude *= persistence
        frequency *= 2
        if frequency > max(w, h):
            break
    if total:
        for y in range(h):
            row = out[y]
            for x in range(w):
                row[x] /= total
    return out


# ==========================================================================
# Heightmap
# ==========================================================================


def _continent_centres(params: MapParams, rng: random.Random
                       ) -> List[Tuple[float, float, float]]:
    """(cx, cy, radius) in grid units for each major landmass."""
    shape = params.shape
    out: List[Tuple[float, float, float]] = []

    if shape == "pangaea":
        out.append((GRID_W * 0.5, GRID_H * 0.5, GRID_W * 0.42))
    elif shape == "coastline":
        out.append((GRID_W * 0.42, GRID_H * 0.5, GRID_W * 0.46))
    elif shape == "inland_sea":
        # A ring of land: four lobes around a central sea.
        for i in range(6):
            a = 2 * math.pi * i / 6
            out.append((GRID_W * 0.5 + math.cos(a) * GRID_W * 0.28,
                        GRID_H * 0.5 + math.sin(a) * GRID_H * 0.30,
                        GRID_W * 0.20))
    elif shape == "archipelago":
        for _ in range(max(2, params.continents)):
            out.append((rng.uniform(0.22, 0.78) * GRID_W,
                        rng.uniform(0.22, 0.78) * GRID_H,
                        GRID_W * rng.uniform(0.07, 0.13)))
    else:  # continents
        count = max(1, params.continents)
        for i in range(count):
            # Spread the centres out rather than clustering them randomly.
            angle = 2 * math.pi * i / count + rng.uniform(-0.4, 0.4)
            spread = rng.uniform(0.18, 0.30)
            out.append((GRID_W * (0.5 + math.cos(angle) * spread),
                        GRID_H * (0.5 + math.sin(angle) * spread * 1.1),
                        GRID_W * rng.uniform(0.16, 0.26)))
    return out


def build_heightmap(params: MapParams) -> Grid:
    rng = random.Random(params.seed)
    w, h = GRID_W, GRID_H

    # Detail level follows roughness: a rugged coast needs higher frequencies.
    octaves = 4 + int(params.roughness * 3)
    base = 3 + int(params.roughness * 4)
    noise = _fbm(w, h, octaves, base, rng, persistence=0.48 + params.roughness * 0.14)

    centres = _continent_centres(params, rng)
    islands: List[Tuple[float, float, float]] = []
    for _ in range(params.islands):
        islands.append((rng.uniform(0.05, 0.95) * w,
                        rng.uniform(0.05, 0.95) * h,
                        rng.uniform(2.5, 7.0)))

    height: Grid = [[0.0] * w for _ in range(h)]
    inv_w = 1.0 / max(1, w - 1)
    inv_h = 1.0 / max(1, h - 1)

    for y in range(h):
        row = height[y]
        noise_row = noise[y]
        ny = y * inv_h
        for x in range(w):
            nx = x * inv_w

            landmass = 0.0
            for cx, cy, radius in centres:
                dx = (x - cx) / radius
                dy = (y - cy) / (radius * 0.78)
                landmass = max(landmass, math.exp(-(dx * dx + dy * dy) * 1.15))

            island = 0.0
            for ix, iy, ir in islands:
                dx = (x - ix) / ir
                dy = (y - iy) / ir
                d2 = dx * dx + dy * dy
                if d2 < 9.0:
                    island = max(island, math.exp(-d2) * 0.62)

            # Push the borders under water so the world does not run off the page.
            edge = min(nx, 1.0 - nx, ny, 1.0 - ny) * 2.0
            falloff = min(1.0, edge / 0.42) ** 1.5
            falloff = 1.0 - (1.0 - falloff) * params.edge_water

            value = (landmass * 0.72 + island) * (0.55 + noise_row[x] * 0.85)
            value += noise_row[x] * 0.20
            row[x] = max(0.0, value * falloff)

    if params.shape == "inland_sea":
        # Carve the sea in the middle back out.
        for y in range(h):
            row = height[y]
            for x in range(w):
                dx = (x - w * 0.5) / (w * 0.19)
                dy = (y - h * 0.5) / (h * 0.20)
                d2 = dx * dx + dy * dy
                if d2 < 4.0:
                    row[x] *= min(1.0, d2 / 1.4) ** 1.2
    return height


def sea_level_for(height: Grid, land_fraction: float) -> float:
    """
    The threshold that yields exactly the requested land fraction.

    Taking a percentile of the sorted heights means "35% land" is honoured on
    every seed, instead of varying wildly with the noise.
    """
    values = sorted(v for row in height for v in row)
    if not values:
        return 0.5
    index = int((1.0 - land_fraction) * (len(values) - 1))
    return values[max(0, min(len(values) - 1, index))]


# ==========================================================================
# Region labelling and boundary tracing
# ==========================================================================


def _label_regions(mask: List[List[bool]], w: int, h: int,
                   min_size: int = 6) -> List[List[Tuple[int, int]]]:
    """Flood-fill connected True regions. Returns a cell list per region."""
    seen = [[False] * w for _ in range(h)]
    regions: List[List[Tuple[int, int]]] = []
    for sy in range(h):
        for sx in range(w):
            if not mask[sy][sx] or seen[sy][sx]:
                continue
            stack = [(sx, sy)]
            seen[sy][sx] = True
            cells: List[Tuple[int, int]] = []
            while stack:
                x, y = stack.pop()
                cells.append((x, y))
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < w and 0 <= ny < h and \
                            mask[ny][nx] and not seen[ny][nx]:
                        seen[ny][nx] = True
                        stack.append((nx, ny))
            if len(cells) >= min_size:
                regions.append(cells)
    regions.sort(key=len, reverse=True)
    return regions


_MOORE = [(1, 0), (1, 1), (0, 1), (-1, 1), (-1, 0), (-1, -1), (0, -1), (1, -1)]


def _trace_boundary(cells: Set[Tuple[int, int]], w: int, h: int
                    ) -> List[Tuple[int, int]]:
    """
    Moore-neighbour boundary tracing with Jacob's stopping criterion.

    Returns the region's outline as an ordered ring of cell coordinates. The
    iteration cap is a hard backstop - the criterion terminates on its own for
    well-formed regions, but a hang here would freeze the UI.
    """
    if not cells:
        return []
    start = min(cells, key=lambda c: (c[1], c[0]))
    boundary: List[Tuple[int, int]] = [start]

    # Start backtracking from the cell to the west, which is outside by
    # construction (start is the leftmost cell of the topmost row).
    current = start
    backtrack = (start[0] - 1, start[1])
    second: Optional[Tuple[int, int]] = None
    limit = max(1000, len(cells) * 8)

    for _ in range(limit):
        try:
            offset = _MOORE.index((backtrack[0] - current[0],
                                   backtrack[1] - current[1]))
        except ValueError:
            offset = 0

        found = None
        previous = backtrack
        for step in range(1, 9):
            dx, dy = _MOORE[(offset + step) % 8]
            candidate = (current[0] + dx, current[1] + dy)
            if candidate in cells:
                found = candidate
                break
            previous = candidate

        if found is None:
            break                      # isolated cell

        backtrack = previous
        current = found
        if second is None:
            second = current
            boundary.append(current)
            continue
        if current == start and boundary[-1] == start:
            break
        boundary.append(current)
        # Jacob's criterion: back at the start heading the same way as before.
        if len(boundary) > 2 and boundary[-1] == second and boundary[-2] == start:
            boundary.pop()
            break

    return boundary


def _simplify(points: Sequence[Point], tolerance: float) -> List[Point]:
    """
    Douglas-Peucker, written iteratively.

    A traced coastline can be thousands of points; recursion would risk the
    interpreter's stack limit on a pathological shape.
    """
    pts = list(points)
    if len(pts) < 3 or tolerance <= 0:
        return pts
    keep = [False] * len(pts)
    keep[0] = keep[-1] = True
    stack = [(0, len(pts) - 1)]

    while stack:
        first, last = stack.pop()
        if last <= first + 1:
            continue
        ax, ay = pts[first]
        bx, by = pts[last]
        dx, dy = bx - ax, by - ay
        span = math.hypot(dx, dy)
        worst = 0.0
        worst_index = -1
        for i in range(first + 1, last):
            px, py = pts[i]
            if span < 1e-12:
                distance = math.hypot(px - ax, py - ay)
            else:
                distance = abs(dy * px - dx * py + bx * ay - by * ax) / span
            if distance > worst:
                worst = distance
                worst_index = i
        if worst > tolerance and worst_index > 0:
            keep[worst_index] = True
            stack.append((first, worst_index))
            stack.append((worst_index, last))

    return [p for p, k in zip(pts, keep) if k]


# ==========================================================================
# Hydrology
# ==========================================================================


def _flow(height: Grid, mask: List[List[bool]], w: int, h: int
          ) -> Tuple[List[List[Optional[Tuple[int, int]]]], List[List[float]]]:
    """Steepest-descent flow direction and accumulated flow per land cell."""
    downhill: List[List[Optional[Tuple[int, int]]]] = [
        [None] * w for _ in range(h)
    ]
    land: List[Tuple[float, int, int]] = []
    for y in range(h):
        for x in range(w):
            if not mask[y][x]:
                continue
            land.append((height[y][x], x, y))
            best = height[y][x]
            target = None
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1),
                           (1, 1), (1, -1), (-1, 1), (-1, -1)):
                nx, ny = x + dx, y + dy
                if not (0 <= nx < w and 0 <= ny < h):
                    continue
                if height[ny][nx] < best:
                    best = height[ny][nx]
                    target = (nx, ny)
            downhill[y][x] = target

    accumulation = [[1.0 if mask[y][x] else 0.0 for x in range(w)]
                    for y in range(h)]
    # Processing from high to low means a cell's own inflow is final before it
    # passes water on, so one pass is enough.
    land.sort(reverse=True)
    for _value, x, y in land:
        target = downhill[y][x]
        if target is not None:
            accumulation[target[1]][target[0]] += accumulation[y][x]
    return downhill, accumulation


def _trace_river(x: int, y: int, downhill, mask, w: int, h: int,
                 limit: int = 4000) -> List[Tuple[int, int]]:
    path = [(x, y)]
    seen = {(x, y)}
    for _ in range(limit):
        target = downhill[y][x]
        if target is None:
            break
        x, y = target
        if (x, y) in seen:
            break                       # a basin: stop rather than loop
        seen.add((x, y))
        path.append((x, y))
        if not mask[y][x]:
            break                       # reached the sea
    return path


# ==========================================================================
# The generator
# ==========================================================================


def generate(params: MapParams) -> GameMap:
    """Build a complete GameMap from parameters."""
    params = params.clamped()
    rng = random.Random(params.seed ^ 0x5EED)
    w, h = GRID_W, GRID_H

    height = build_heightmap(params)
    sea = sea_level_for(height, params.land_fraction)
    mask = [[height[y][x] > sea for x in range(w)] for y in range(h)]

    gm = GameMap(
        name=params.name or generate_name(params.name_flavour, params.seed).title(),
        kind="world",
        style=params.style,
        width=params.width,
        height=params.height,
        seed=params.seed % 9973,
        scale_text=params.scale_text,
        layers=[Layer(name="Land"), Layer(name="Terrain"),
                Layer(name="Water"), Layer(name="Places")],
    )

    sx = params.width / float(w)
    sy = params.height / float(h)

    def to_map(cell: Tuple[int, int]) -> Point:
        return ((cell[0] + 0.5) * sx, (cell[1] + 0.5) * sy)

    # -- coastlines ----------------------------------------------------
    regions = _label_regions(mask, w, h, min_size=5)
    max_land = max((len(r) for r in regions), default=1)
    for cells in regions:
        ring = _trace_boundary(set(cells), w, h)
        if len(ring) < 8:
            continue
        points = _simplify([to_map(c) for c in ring],
                           tolerance=max(sx, sy) * 0.55)
        if len(points) < 4:
            continue
        gm.shapes.append(Shape(kind="land", points=points, closed=True,
                               layer="Land"))

    # -- lakes ---------------------------------------------------------
    if params.lakes:
        water_mask = [[not mask[y][x] for x in range(w)] for y in range(h)]
        # An enclosed water body is one that never touches the border.
        for cells in _label_regions(water_mask, w, h, min_size=8):
            touches_edge = any(x in (0, w - 1) or y in (0, h - 1)
                               for x, y in cells)
            if touches_edge or len(cells) > (w * h) * 0.02:
                continue
            ring = _trace_boundary(set(cells), w, h)
            if len(ring) < 8:
                continue
            points = _simplify([to_map(c) for c in ring],
                               tolerance=max(sx, sy) * 0.5)
            if len(points) >= 4:
                gm.shapes.append(Shape(kind="water", points=points,
                                       closed=True, layer="Water"))
            if sum(1 for s in gm.shapes if s.kind == "water") >= params.lakes:
                break

    # -- relief --------------------------------------------------------
    land_heights = sorted(height[y][x] for y in range(h) for x in range(w)
                          if mask[y][x])
    if land_heights:
        def land_percentile(fraction: float) -> float:
            index = int(max(0.0, min(1.0, fraction)) * (len(land_heights) - 1))
            return land_heights[index]

        mountain_cut = land_percentile(1.0 - params.mountains * 0.55)
        hill_cut = land_percentile(1.0 - params.mountains * 0.55
                                   - params.hills * 0.5)

        for kind, low, high, layer in (
            ("mountains", mountain_cut, None, "Terrain"),
            ("hills", hill_cut, mountain_cut, "Terrain"),
        ):
            band = [[mask[y][x] and height[y][x] >= low
                     and (high is None or height[y][x] < high)
                     for x in range(w)] for y in range(h)]
            for cells in _label_regions(band, w, h, min_size=10)[:14]:
                ridge = _ridge_line(cells)
                if len(ridge) < 2:
                    continue
                points = _simplify([to_map(c) for c in ridge],
                                   tolerance=max(sx, sy) * 0.8)
                if len(points) >= 2:
                    gm.shapes.append(Shape(kind=kind, points=points,
                                           closed=False, layer=layer))

    # -- rivers --------------------------------------------------------
    downhill, accumulation = _flow(height, mask, w, h)
    if params.rivers:
        sources = sorted(
            ((accumulation[y][x], x, y)
             for y in range(h) for x in range(w)
             if mask[y][x] and height[y][x] > sea + (1.0 - sea) * 0.28),
            reverse=True,
        )
        used: Set[Tuple[int, int]] = set()
        made = 0
        for _flowvalue, x, y in sources:
            if made >= params.rivers:
                break
            if any((x + dx, y + dy) in used
                   for dx in range(-4, 5) for dy in range(-4, 5)):
                continue
            path = _trace_river(x, y, downhill, mask, w, h)
            if len(path) < 6:
                continue
            used.update(path)
            points = _simplify([to_map(c) for c in path],
                               tolerance=max(sx, sy) * 0.4)
            if len(points) >= 3:
                gm.shapes.append(Shape(kind="river", points=points,
                                       closed=False, layer="Water"))
                made += 1

    # -- biomes --------------------------------------------------------
    moisture = _fbm(w, h, 4, 4, random.Random(params.seed ^ 0xB10),
                    persistence=0.55)
    _add_biomes(gm, params, mask, height, moisture, sea, to_map, sx, sy, w, h)

    # -- settlements ---------------------------------------------------
    _add_settlements(gm, params, mask, height, accumulation, sea,
                     to_map, w, h, rng, max_land)

    # -- labels --------------------------------------------------------
    if params.label_regions:
        _add_labels(gm, params, regions, to_map, rng)

    # Record the recipe on the map itself. Someone handed this file can type
    # the same seed and settings and get the identical world back.
    shown = params.seed_text.strip() or str(params.seed)
    gm.notes = (
        f"Generated world.\n\n"
        f"SEED: {shown}\n"
        f"(numeric seed {params.seed})\n\n"
        f"Arrangement: {LANDMASS_SHAPES.get(params.shape, params.shape)}\n"
        f"Climate: {CLIMATES.get(params.climate, params.climate)}\n"
        f"Land: {params.land_fraction:.0%}   Roughness: {params.roughness:.0%}\n"
        f"Continents {params.continents}, islands {params.islands}, "
        f"rivers {params.rivers}, lakes {params.lakes}\n"
        f"Mountains {params.mountains:.0%}, forest {params.forest:.0%}, "
        f"desert {params.desert:.0%}, marsh {params.marsh:.0%}\n\n"
        f"Same seed and settings always rebuild this exact world. "
        f"Everything here is fully editable - draw over it, move pins, "
        f"rename anything."
    ).strip()

    return gm


def _ridge_line(cells: Sequence[Tuple[int, int]]) -> List[Tuple[int, int]]:
    """
    Reduce a blob of high ground to a line to draw peaks along.

    One representative cell per column (or per row, whichever axis the blob is
    longer on) gives a spine that follows the range instead of zig-zagging.
    """
    if not cells:
        return []
    xs = [c[0] for c in cells]
    ys = [c[1] for c in cells]
    if (max(xs) - min(xs)) >= (max(ys) - min(ys)):
        buckets: Dict[int, List[int]] = {}
        for x, y in cells:
            buckets.setdefault(x, []).append(y)
        return [(x, sorted(vals)[len(vals) // 2])
                for x, vals in sorted(buckets.items())]
    buckets = {}
    for x, y in cells:
        buckets.setdefault(y, []).append(x)
    return [(sorted(vals)[len(vals) // 2], y)
            for y, vals in sorted(buckets.items())]


def _add_biomes(gm: GameMap, params: MapParams, mask, height, moisture,
                sea: float, to_map, sx: float, sy: float,
                w: int, h: int) -> None:
    """Temperature from latitude and altitude, moisture from noise."""
    climate = params.climate
    warm_shift = {"tropical": 0.32, "arid": 0.20, "temperate": 0.0,
                  "arctic": -0.34, "varied": 0.0}.get(climate, 0.0)
    wet_shift = {"tropical": 0.26, "arid": -0.30, "temperate": 0.0,
                 "arctic": -0.10, "varied": 0.0}.get(climate, 0.0)

    span = max(1e-6, 1.0 - sea)
    classes: Dict[str, List[List[bool]]] = {
        kind: [[False] * w for _ in range(h)]
        for kind in ("forest", "desert", "swamp", "ice")
    }

    for y in range(h):
        latitude = abs((y / max(1, h - 1)) - 0.5) * 2.0     # 0 equator, 1 pole
        for x in range(w):
            if not mask[y][x]:
                continue
            altitude = (height[y][x] - sea) / span
            temperature = (1.0 - latitude) - altitude * 0.45 + warm_shift
            wet = moisture[y][x] + wet_shift - altitude * 0.15

            if params.ice_caps and temperature < 0.18:
                classes["ice"][y][x] = True
            elif wet < 0.42 - params.desert * 0.30 and temperature > 0.45:
                classes["desert"][y][x] = True
            elif wet > 0.62 - params.marsh * 0.25 and altitude < 0.16:
                classes["swamp"][y][x] = True
            elif wet > 0.48 - params.forest * 0.28 and altitude < 0.62:
                classes["forest"][y][x] = True

    caps = {"forest": 18, "desert": 8, "swamp": 8, "ice": 4}
    for kind, grid in classes.items():
        for cells in _label_regions(grid, w, h, min_size=22)[:caps[kind]]:
            ring = _trace_boundary(set(cells), w, h)
            if len(ring) < 8:
                continue
            points = _simplify([to_map(c) for c in ring],
                               tolerance=max(sx, sy) * 0.7)
            if len(points) >= 4:
                gm.shapes.append(Shape(kind=kind, points=points, closed=True,
                                       layer="Terrain"))


def _add_settlements(gm: GameMap, params: MapParams, mask, height,
                     accumulation, sea: float, to_map, w: int, h: int,
                     rng: random.Random, max_land: int) -> None:
    """Score every land cell for habitability, then take the best sites apart."""
    span = max(1e-6, 1.0 - sea)
    scored: List[Tuple[float, int, int]] = []

    for y in range(h):
        for x in range(w):
            if not mask[y][x]:
                continue
            altitude = (height[y][x] - sea) / span
            if altitude > 0.72:
                continue                       # nobody builds a capital on a peak

            coastal = any(
                0 <= x + dx < w and 0 <= y + dy < h and not mask[y + dy][x + dx]
                for dx in (-2, -1, 0, 1, 2) for dy in (-2, -1, 0, 1, 2)
            )
            fresh_water = min(1.0, accumulation[y][x] / 260.0)
            gentle = 1.0 - min(1.0, altitude * 1.4)

            score = gentle * 0.45 + fresh_water * 0.35
            if coastal:
                score += 0.35
            score += rng.uniform(0.0, 0.14)
            scored.append((score, x, y))

    scored.sort(reverse=True)

    plan = [
        ("capital", params.capitals, 26, 9.0),
        ("city", params.cities, 18, 7.5),
        ("port", max(0, params.cities // 3), 16, 7.0),
        ("town", params.towns, 11, 6.5),
        ("village", params.villages, 7, 5.5),
        ("castle", max(0, params.towns // 4), 12, 6.5),
        ("ruin", params.ruins, 9, 6.0),
        ("landmark", params.landmarks, 14, 6.5),
    ]

    taken: List[Tuple[int, int]] = []
    index = 0
    used_names: Set[str] = set()

    for kind, count, spacing, size in plan:
        placed = 0
        guard = 0
        while placed < count and index < len(scored) and guard < len(scored) * 2:
            guard += 1
            _score, x, y = scored[index]
            index += 1
            if any(abs(x - tx) < spacing and abs(y - ty) < spacing
                   for tx, ty in taken):
                continue
            taken.append((x, y))
            px, py = to_map((x, y))
            label = ""
            if params.name_places:
                for _ in range(12):
                    candidate = generate_name(params.name_flavour)
                    if candidate not in used_names:
                        used_names.add(candidate)
                        label = candidate
                        break
            gm.pins.append(Pin(
                x=px, y=py, kind=kind, label=label, size=size,
                label_side=rng.choice(("e", "w", "n", "s")),
                layer="Places",
            ))
            placed += 1
        # Ruins and landmarks may sit anywhere, so restart the scan for them.
        if kind in ("ruin", "landmark"):
            index = 0

    if params.roads and len(taken) >= 2:
        _add_roads(gm, taken, to_map, rng)


def _add_roads(gm: GameMap, sites: Sequence[Tuple[int, int]], to_map,
               rng: random.Random) -> None:
    """
    Connect settlements with a nearest-neighbour chain.

    A minimum spanning tree would be prettier but a greedy chain reads fine on
    a map and costs a fraction of the time.
    """
    remaining = list(sites[: min(len(sites), 22)])
    if len(remaining) < 2:
        return
    current = remaining.pop(0)
    path = [current]
    while remaining:
        nearest = min(remaining, key=lambda s: (s[0] - current[0]) ** 2
                      + (s[1] - current[1]) ** 2)
        remaining.remove(nearest)
        # Bend the road so it is not a straight ruler line.
        mid = ((current[0] + nearest[0]) / 2 + rng.uniform(-3, 3),
               (current[1] + nearest[1]) / 2 + rng.uniform(-3, 3))
        path.extend([mid, nearest])
        current = nearest

    points = [to_map((int(px), int(py))) for px, py in path]
    if len(points) >= 2:
        gm.shapes.append(Shape(kind="road", points=points, closed=False,
                               layer="Places"))


def _add_labels(gm: GameMap, params: MapParams,
                regions: Sequence[Sequence[Tuple[int, int]]],
                to_map, rng: random.Random) -> None:
    """Name the largest landmasses, and the ocean."""
    # Only the two biggest landmasses get a name. More than that and the page
    # fills with large text that fights the place names for attention.
    suffixes = ["", "", " REACH", " LANDS", " MARCHES"]
    for cells in regions[:2]:
        if len(cells) < 400:
            continue
        cx = sum(c[0] for c in cells) / len(cells)
        cy = sum(c[1] for c in cells) / len(cells)
        px, py = to_map((int(cx), int(cy)))
        name = generate_name(params.name_flavour).upper()
        gm.labels.append(MapLabel(
            x=px, y=py, text=name + rng.choice(suffixes),
            size=max(14, int(gm.height * 0.020)),
            italic=False, bold=True, tracking=4.0, layer="Places",
        ))

    gm.labels.append(MapLabel(
        x=gm.width * 0.5, y=gm.height * 0.93,
        text=f"THE {generate_name(params.name_flavour).upper()} OCEAN",
        size=max(14, int(gm.height * 0.020)),
        italic=True, tracking=6.0, layer="Places",
    ))


# ==========================================================================
# Presets
# ==========================================================================

PRESETS: Dict[str, Dict] = {
    "Classic fantasy world": dict(
        shape="continents", land_fraction=0.34, continents=3, islands=16,
        roughness=0.55, mountains=0.45, rivers=9, climate="temperate",
        forest=0.45, capitals=2, cities=6, towns=12, villages=10),
    "Island archipelago": dict(
        shape="archipelago", land_fraction=0.18, continents=6, islands=45,
        roughness=0.7, mountains=0.3, rivers=4, climate="tropical",
        forest=0.6, marsh=0.2, capitals=1, cities=4, towns=8, villages=12),
    "Single supercontinent": dict(
        shape="pangaea", land_fraction=0.55, continents=1, islands=8,
        roughness=0.45, mountains=0.5, rivers=14, climate="varied",
        forest=0.35, desert=0.25, capitals=3, cities=10, towns=18),
    "Frozen north": dict(
        shape="continents", land_fraction=0.4, continents=2, islands=20,
        roughness=0.6, mountains=0.55, rivers=6, climate="arctic",
        forest=0.25, ice_caps=True, capitals=1, cities=3, towns=7,
        villages=9, ruins=8),
    "Desert kingdoms": dict(
        shape="coastline", land_fraction=0.5, continents=1, islands=5,
        roughness=0.4, mountains=0.35, rivers=3, climate="arid",
        forest=0.1, desert=0.6, capitals=2, cities=5, towns=9, ruins=7),
    "Inland sea": dict(
        shape="inland_sea", land_fraction=0.45, continents=6, islands=12,
        roughness=0.5, mountains=0.4, rivers=11, climate="temperate",
        forest=0.4, capitals=3, cities=8, towns=14),
    "Scattered isles": dict(
        shape="archipelago", land_fraction=0.1, continents=8, islands=70,
        roughness=0.8, mountains=0.2, rivers=2, climate="tropical",
        forest=0.55, capitals=1, cities=2, towns=5, villages=8, ruins=6),
}


def preset(name: str, seed: int = 1) -> MapParams:
    params = MapParams(seed=seed)
    for key, value in PRESETS.get(name, {}).items():
        setattr(params, key, value)
    return params.clamped()
