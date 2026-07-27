"""
Writing statistics: sessions, streaks, pace and deadline projection.

On counting deletions. A revision day where you cut 800 words and write 600 is
real work, and a tool that reports "-200" as your day's output is discouraging
and wrong. So two numbers are kept:

  * **added**  - the sum of positive changes. What you typed.
  * **net**    - end minus start. What the manuscript gained.

Daily targets are measured against `added`, because that is the behaviour you
are trying to build. Progress toward the book's total uses `net`, because that
is what actually exists.
"""

from __future__ import annotations

import math
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional, Tuple

from .model import ProjectData, Session, today_iso


# ==========================================================================
# Session tracking
# ==========================================================================


class SessionTracker:
    """
    Live tracking for the current sitting.

    The tool calls `update` with the project's current total word count; the
    tracker works out deltas. Positive and negative movement is accumulated
    separately so neither is lost.
    """

    def __init__(self, data: ProjectData) -> None:
        self.data = data
        self.session: Session = self._todays_session()
        self._last_total: int = self.session.words_end or data.word_count
        self._started_at = datetime.now()

    def _todays_session(self) -> Session:
        existing = self.data.session_for_today()
        if existing:
            return existing
        total = self.data.word_count
        session = Session(
            date=today_iso(),
            words_start=total,
            words_end=total,
        )
        self.data.sessions.append(session)
        return session

    def update(self, total_words: int, scene_id: str = "") -> None:
        delta = total_words - self._last_total
        if delta > 0:
            self.session.words_added += delta
        elif delta < 0:
            self.session.words_deleted += -delta
        self._last_total = total_words
        self.session.words_end = total_words
        if scene_id and scene_id not in self.session.scenes_touched:
            self.session.scenes_touched.append(scene_id)

    def close(self) -> None:
        self.session.ended = datetime.now().replace(microsecond=0).isoformat()
        self.session.minutes = round(
            (datetime.now() - self._started_at).total_seconds() / 60.0, 1
        )

    @property
    def added(self) -> int:
        return self.session.words_added

    @property
    def net(self) -> int:
        return self.session.words_net

    @property
    def deleted(self) -> int:
        return self.session.words_deleted

    @property
    def minutes(self) -> float:
        return round((datetime.now() - self._started_at).total_seconds() / 60.0, 1)

    @property
    def words_per_hour(self) -> int:
        mins = self.minutes
        if mins < 1:
            return 0
        return int(self.added / (mins / 60.0))


# ==========================================================================
# Aggregate statistics
# ==========================================================================


def _as_date(value: str) -> Optional[date]:
    """
    Parse an ISO date defensively.

    Session dates come from the manifest, which a user may have hand-edited or
    a sync client may have merged badly. An unparseable date must be skipped,
    not allowed to crash the dashboard.
    """
    try:
        return date.fromisoformat(str(value))
    except (ValueError, TypeError):
        return None


def daily_totals(data: ProjectData) -> Dict[str, Tuple[int, int]]:
    """
    {date: (added, net)} merging any duplicate sessions for a day.

    Only well-formed dates are included, so every consumer can rely on the
    keys parsing.
    """
    out: Dict[str, Tuple[int, int]] = {}
    for session in data.sessions:
        if _as_date(session.date) is None:
            continue
        added, net = out.get(session.date, (0, 0))
        out[session.date] = (added + session.words_added, net + session.words_net)
    return out


def streak(data: ProjectData, minimum: int = 1) -> int:
    """
    Consecutive days up to today with at least `minimum` words added.

    Today not yet started does not break the streak - the run is measured from
    yesterday in that case, so opening the app at 9am shows the true figure.

    The walk stops at the first day below the threshold, so it is bounded by
    the number of recorded days; the explicit cap only guards against a
    manifest carrying decades of fabricated sessions.
    """
    totals = daily_totals(data)
    if not totals:
        return 0
    today = date.today()
    start = today if totals.get(today.isoformat(), (0, 0))[0] >= minimum \
        else today - timedelta(days=1)
    count = 0
    cursor = start
    for _ in range(len(totals) + 2):
        if totals.get(cursor.isoformat(), (0, 0))[0] < minimum:
            break
        count += 1
        cursor -= timedelta(days=1)
    return count


def best_streak(data: ProjectData, minimum: int = 1) -> int:
    totals = daily_totals(data)
    days = sorted(
        parsed for day, (added, _net) in totals.items()
        if added >= minimum and (parsed := _as_date(day)) is not None
    )
    if not days:
        return 0
    best = run = 1
    for previous, current in zip(days, days[1:]):
        run = run + 1 if (current - previous).days == 1 else 1
        best = max(best, run)
    return best


def days_written(data: ProjectData, minimum: int = 1) -> int:
    return sum(1 for added, _net in daily_totals(data).values() if added >= minimum)


def average_daily(data: ProjectData, window: int = 14) -> float:
    """Mean words added per *writing* day over the recent window."""
    totals = daily_totals(data)
    if not totals:
        return 0.0
    cutoff = date.today() - timedelta(days=max(1, window))
    recent = [
        added for day, (added, _net) in totals.items()
        if added > 0 and (parsed := _as_date(day)) is not None and parsed >= cutoff
    ]
    if not recent:
        recent = [added for added, _net in totals.values() if added > 0]
    return round(sum(recent) / len(recent), 1) if recent else 0.0


def target_days_hit(data: ProjectData) -> int:
    goal = max(1, data.targets.daily_words)
    return sum(1 for added, _net in daily_totals(data).values() if added >= goal)


# ==========================================================================
# Projection
# ==========================================================================


class Projection:
    """Deadline arithmetic, computed once and read as attributes."""

    def __init__(self, data: ProjectData) -> None:
        self.total = data.word_count
        self.goal = max(0, data.targets.total_words)
        self.remaining = max(0, self.goal - self.total)
        self.percent = (
            min(100.0, round(self.total / self.goal * 100, 1)) if self.goal else 0.0
        )
        self.daily_goal = max(1, data.targets.daily_words)
        self.average = average_daily(data)

        self.deadline: Optional[date] = None
        self.days_left: Optional[int] = None
        self.required_daily: Optional[int] = None
        self.on_track: Optional[bool] = None

        raw = (data.targets.deadline or "").strip()
        if raw:
            try:
                self.deadline = date.fromisoformat(raw)
            except ValueError:
                self.deadline = None
        if self.deadline:
            self.days_left = (self.deadline - date.today()).days
            if self.days_left > 0:
                self.required_daily = math.ceil(self.remaining / self.days_left)
            elif self.remaining > 0:
                self.required_daily = self.remaining
            else:
                self.required_daily = 0
            if self.required_daily is not None:
                pace = self.average or self.daily_goal
                self.on_track = pace >= self.required_daily

        # Projected finish at the current pace.
        self.finish_date: Optional[date] = None
        self.days_at_pace: Optional[int] = None
        pace = self.average or self.daily_goal
        if self.remaining and pace > 0:
            self.days_at_pace = math.ceil(self.remaining / pace)
            self.finish_date = date.today() + timedelta(days=self.days_at_pace)
        elif not self.remaining:
            self.days_at_pace = 0
            self.finish_date = date.today()

    def headline(self) -> str:
        if not self.goal:
            return f"{self.total:,} words"
        return f"{self.total:,} / {self.goal:,} words  ({self.percent:.1f}%)"

    def pace_line(self) -> str:
        bits: List[str] = []
        if self.average:
            bits.append(f"averaging {self.average:,.0f}/day")
        if self.finish_date and self.remaining:
            bits.append(f"finishing about {self.finish_date.strftime('%d %b %Y')}")
        if self.days_left is not None:
            if self.days_left > 0:
                bits.append(
                    f"{self.days_left} days left, need "
                    f"{self.required_daily:,}/day"
                )
            elif self.remaining:
                bits.append(f"deadline passed, {self.remaining:,} words short")
            else:
                bits.append("deadline met")
        return " - ".join(bits) if bits else "no pace data yet"


# ==========================================================================
# Breakdowns
# ==========================================================================


def chapter_breakdown(data: ProjectData) -> List[Tuple[str, int, int, str]]:
    """(chapter title, words, scene count, dominant status)."""
    rows: List[Tuple[str, int, int, str]] = []
    for chapter in data.ordered_chapters():
        scenes = data.scenes_in(chapter.id)
        words = sum(s.word_count for s in scenes)
        statuses = [s.status for s in scenes]
        dominant = max(set(statuses), key=statuses.count) if statuses else "-"
        rows.append((chapter.title, words, len(scenes), dominant))
    return rows


def status_counts(data: ProjectData) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for scene in data.scenes:
        counts[scene.status] = counts.get(scene.status, 0) + 1
    return counts


def pov_balance(data: ProjectData) -> List[Tuple[str, int, int, float]]:
    """(POV name, scenes, words, share of total words)."""
    totals: Dict[str, Tuple[int, int]] = {}
    for scene in data.scenes:
        entity = data.entity(scene.pov_id)
        name = entity.name if entity else "(unassigned)"
        count, words = totals.get(name, (0, 0))
        totals[name] = (count + 1, words + scene.word_count)
    grand = sum(words for _count, words in totals.values()) or 1
    rows = [
        (name, count, words, round(words / grand * 100, 1))
        for name, (count, words) in totals.items()
    ]
    return sorted(rows, key=lambda r: -r[2])


def thread_coverage(data: ProjectData) -> List[Tuple[str, int, str]]:
    """
    (thread name, scene count, largest gap).

    A thread absent for many consecutive scenes reads to a reader as dropped,
    so the gap is the number worth watching.
    """
    ordered = data.ordered_scenes()
    positions = {scene.id: i for i, scene in enumerate(ordered)}
    rows: List[Tuple[str, int, str]] = []
    for thread in data.entities_of("thread"):
        appearances = sorted(
            positions[s.id] for s in ordered if thread.id in s.thread_ids
        )
        if not appearances:
            rows.append((thread.name, 0, "never appears"))
            continue
        gaps = [b - a - 1 for a, b in zip(appearances, appearances[1:])]
        leading = appearances[0]
        trailing = len(ordered) - 1 - appearances[-1]
        worst = max(gaps + [leading, trailing]) if ordered else 0
        rows.append((thread.name, len(appearances), f"{worst} scenes"))
    return rows


def scene_length_outliers(data: ProjectData, tolerance: float = 2.0
                          ) -> Tuple[float, List[Tuple[str, int]]]:
    """
    Mean scene length plus the scenes far from it.

    Very short scenes are often unfinished; very long ones often contain a
    second scene trying to get out.
    """
    words = [s.word_count for s in data.scenes if s.word_count > 0]
    if len(words) < 3:
        return 0.0, []
    mean = sum(words) / len(words)
    variance = sum((w - mean) ** 2 for w in words) / len(words)
    sd = math.sqrt(variance)
    if sd == 0:
        return mean, []
    outliers = [
        (s.title, s.word_count)
        for s in data.ordered_scenes()
        if s.word_count > 0 and abs(s.word_count - mean) > tolerance * sd
    ]
    return round(mean, 1), outliers


def reading_time(words: int, wpm: int = 250) -> str:
    if not words:
        return "0 min"
    minutes = words / float(wpm)
    if minutes < 60:
        return f"{int(round(minutes))} min"
    hours, mins = divmod(int(round(minutes)), 60)
    return f"{hours}h {mins:02d}m"


def sparkline(data: ProjectData, days: int = 30) -> str:
    """A tiny text bar chart of the last N days, for the dashboard."""
    blocks = " ▁▂▃▄▅▆▇█"
    totals = daily_totals(data)
    today = date.today()
    series = [
        totals.get((today - timedelta(days=offset)).isoformat(), (0, 0))[0]
        for offset in range(days - 1, -1, -1)
    ]
    peak = max(series) if series else 0
    if not peak:
        return blocks[0] * days
    return "".join(
        blocks[min(len(blocks) - 1, int(value / peak * (len(blocks) - 1)))]
        for value in series
    )


def summary_lines(data: ProjectData) -> List[str]:
    """The dashboard's text block."""
    projection = Projection(data)
    counts = status_counts(data)
    mean, outliers = scene_length_outliers(data)
    lines = [
        projection.headline(),
        projection.pace_line(),
        "",
        f"Chapters {len(data.chapters)}    Scenes {len(data.scenes)}",
        f"Reading time about {reading_time(data.word_count)}",
        "",
        f"Streak {streak(data)} days   (best {best_streak(data)})",
        f"Days written {days_written(data)}   "
        f"target hit {target_days_hit(data)}",
        "",
        "Scene status:  " + ("  ".join(
            f"{name} {count}" for name, count in sorted(counts.items())
        ) or "none yet"),
    ]
    if mean:
        lines.append(f"Average scene {mean:,.0f} words")
    if outliers:
        preview = ", ".join(f"{t} ({w:,})" for t, w in outliers[:4])
        lines.append(f"Unusual lengths: {preview}")
    return lines
