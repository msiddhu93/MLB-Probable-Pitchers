# =============================================================================
# stats.py — Calculate advanced pitching metrics
# =============================================================================
# Think of this file as the prep station.
# Raw numbers come in; meaningful metrics come out.
#
# Nothing is fetched here. All inputs are plain Python dicts.
# This makes it easy to test each function independently.
# =============================================================================

from config import FIP_CONSTANT


def _parse_innings(ip_str):
    """
    Convert MLB's innings pitched notation to a true decimal.

    "33.2" means 33 full innings + 2 outs = 33.667, not 33.2.
    See mlb_api._parse_innings for the full explanation.
    """
    try:
        parts = str(ip_str).split(".")
        full  = int(parts[0])
        outs  = int(parts[1]) if len(parts) > 1 else 0
        return full + outs / 3
    except (ValueError, IndexError):
        return 0.0


def calculate_fip(stat):
    """
    FIP — Fielding Independent Pitching.

    Measures what a pitcher's ERA *should* look like based solely on
    outcomes they control: strikeouts, walks, hit-by-pitches, home runs.
    It strips out defence and luck.

    Formula: (13*HR + 3*(BB + HBP) - 2*K) / IP  +  FIP_constant

    Scale is the same as ERA. Lower is better.
    A gap between ERA and FIP tells a story:
      ERA < FIP  →  pitcher has been lucky (ERA likely to rise)
      ERA > FIP  →  pitcher has been unlucky (ERA likely to fall)
    """
    try:
        ip  = _parse_innings(stat.get("inningsPitched", "0"))
        hr  = int(stat.get("homeRuns",    0) or 0)
        bb  = int(stat.get("baseOnBalls", 0) or 0)
        hbp = int(stat.get("hitByPitch",  0) or 0)
        k   = int(stat.get("strikeOuts",  0) or 0)

        if ip == 0:
            return None  # can't divide by zero; pitcher hasn't thrown yet

        fip = (13 * hr + 3 * (bb + hbp) - 2 * k) / ip + FIP_CONSTANT
        return round(fip, 2)

    except (ValueError, TypeError, ZeroDivisionError):
        return None


def calculate_era_plus(stat, league_era):
    """
    ERA+ — ERA adjusted to league average, park-neutral.

    100  = exactly league average
    150  = 50% better than average
    200  = twice as good as average
    Higher is always better.

    Formula: 100 × (League ERA / Pitcher ERA)

    league_era is fetched live from the API each run (via mlb_api.get_league_era),
    so it reflects the actual run environment as the season progresses.
    """
    try:
        era_str = stat.get("era", None)

        # The API returns "-.--" or "0.00" for pitchers with no decisions yet
        if not era_str or era_str in ("-.--", "0.00"):
            return None

        era = float(era_str)
        if era == 0:
            return None  # infinite ERA+ isn't meaningful to display

        return round(100 * (league_era / era))

    except (ValueError, TypeError, ZeroDivisionError):
        return None


def assess_form(game_log):
    """
    Rate a pitcher's recent form based on their last 3 starts.

    A Quality Start (QS) = 6 or more innings pitched with 3 or fewer earned runs.
    This is the standard baseball benchmark for "pitcher did their job today."

    Returns a short label:
      "Sharp (3/3 QS)"        — dominant recent form
      "Steady (2/3 QS)"       — solid, reliable
      "Struggling (0/3 QS)"   — worrying trend
    """
    if not game_log:
        return "No starts yet"

    quality_starts = 0
    for game in game_log:
        stat = game.get("stat", {})
        try:
            ip = _parse_innings(stat.get("inningsPitched", "0"))
            er = int(stat.get("earnedRuns", 0) or 0)
            if ip >= 6.0 and er <= 3:
                quality_starts += 1
        except (ValueError, TypeError):
            continue

    n = len(game_log)

    if quality_starts == n:
        return f"Sharp ({quality_starts}/{n} QS)"
    elif quality_starts == 0:
        return f"Struggling (0/{n} QS)"
    else:
        return f"Steady ({quality_starts}/{n} QS)"


def get_last_outing(game_log):
    """
    Pull the headline numbers from a pitcher's most recent start.

    Returns a formatted string like "7 IP, 1 ER, 9 K".
    The game log is oldest-first, so the last entry is the most recent.
    """
    if not game_log:
        return "No starts yet"

    last = game_log[-1].get("stat", {})
    ip   = last.get("inningsPitched", "?")
    er   = last.get("earnedRuns",     "?")
    k    = last.get("strikeOuts",     "?")

    return f"{ip} IP, {er} ER, {k} K"
