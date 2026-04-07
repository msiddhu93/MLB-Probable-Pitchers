# =============================================================================
# formatter.py — Build the plain-text email body
# =============================================================================
# Think of this file as the plating station.
# All data arrives ready-to-use; this file only cares about layout.
#
# Home team is always on the LEFT (left column), away on the RIGHT.
# A | separator anchors the two columns — important because Gmail renders
# plain text in a proportional font where spaces don't align perfectly.
# =============================================================================

from datetime import date, datetime
import zoneinfo  # built into Python 3.9+; converts UTC game times to ET

# ── Layout constants ──────────────────────────────────────────────────────────
COL_W        = 42    # width of the home (left) column in characters
DIVIDER_BOLD = "═" * 56
DIVIDER_SOFT = "─" * 56


# ── Internal helpers ──────────────────────────────────────────────────────────

def _row(label, home_val, away_val):
    """
    One stat row, home on left, away on right, | as a column anchor.

    Example output:
      "  ERA   2.25 ↑  ERA+ 180 ↑           |  ERA   1.80 ↑  ERA+ 225 ↑"
    """
    left = f"  {label:<5} {str(home_val)}"
    return f"{left:<{COL_W}}|  {label:<5} {str(away_val)}"


def _format_game_time(game_date_utc):
    """
    Convert the API's UTC timestamp to a readable Eastern Time string.
    The API gives us "2026-04-06T17:05:00Z"; we convert to "1:05 PM".
    """
    try:
        dt_utc = datetime.fromisoformat(game_date_utc.replace("Z", "+00:00"))
        dt_et  = dt_utc.astimezone(zoneinfo.ZoneInfo("America/New_York"))
        return dt_et.strftime("%-I:%M %p")
    except Exception:
        return "TBD"


def _quality_arrow(value, stat):
    """
    Returns ↑, →, or ↓ indicating pitcher quality — NOT the direction of the number.
    ↑ always means 'this pitcher is performing well above average'.
    ↓ always means 'struggling'.

    ERA / FIP: lower number = better pitcher → low value earns ↑
    ERA+:      higher number = better pitcher → high value earns ↑
    """
    if value is None:
        return ""
    try:
        v = float(value)
    except (ValueError, TypeError):
        return ""

    if stat in ("era", "fip"):
        if v < 3.25:  return "↑"
        if v < 4.75:  return "→"
        return "↓"

    if stat == "era_plus":
        if v > 120:  return "↑"
        if v > 80:   return "→"
        return "↓"

    return ""


def _pitcher_vals(pitcher):
    """
    Extract display-ready values from a pitcher dict, including quality arrows.
    Returns a dict of strings safe to pass straight to _row().
    """
    if not pitcher:
        return None

    era      = pitcher.get("era")
    era_plus = pitcher.get("era_plus")
    fip      = pitcher.get("fip")

    era_arrow  = _quality_arrow(era,      "era")
    fip_arrow  = _quality_arrow(fip,      "fip")
    erap_arrow = _quality_arrow(era_plus, "era_plus")

    era_str  = f"{era} {era_arrow}" if era else "-.--"
    erap_str = f"{era_plus} {erap_arrow}" if era_plus is not None else "N/A"
    fip_str  = f"{fip:.2f} {fip_arrow}" if fip is not None else "N/A"

    return {
        "name": f"{pitcher.get('name', 'Unknown')} ({pitcher.get('hand', '?')}HP)",
        "wl":   pitcher.get("wl", "?-?"),
        "era":  f"{era_str}  ERA+ {erap_str}",
        "fip":  fip_str,
        "last": pitcher.get("last_outing", "N/A"),
        "form": pitcher.get("form", "N/A"),
    }


# ── Public functions ──────────────────────────────────────────────────────────

def format_game(game):
    """
    Format one game as a multi-line string with home on left, away on right.
    """
    home_rec  = game.get("home_record", "?-?")
    away_rec  = game.get("away_record", "?-?")
    game_time = _format_game_time(game.get("game_date", ""))

    header = (
        f"{game.get('home_team', '???')} ({home_rec})"
        f" vs {game.get('away_team', '???')} ({away_rec})"
        f"  •  {game_time} ET"
    )

    lines = [header, ""]

    h = _pitcher_vals(game.get("home_pitcher"))
    a = _pitcher_vals(game.get("away_pitcher"))

    if h and a:
        # Name row — | anchors the column split
        lines.append(f"  {h['name']:<{COL_W - 2}}|  vs  {a['name']}")
        lines.append(f"  {'':^{COL_W - 2}}|")
        lines.append(_row("W-L",  h["wl"],   a["wl"]))
        lines.append(_row("ERA",  h["era"],  a["era"]))
        lines.append(_row("FIP",  h["fip"],  a["fip"]))
        lines.append(_row("Last", h["last"], a["last"]))
        lines.append(_row("Form", h["form"], a["form"]))

    elif h:
        lines.append(f"  {h['name']}")
        lines.append(f"  W-L {h['wl']}  ERA {h['era']}  FIP {h['fip']}")
        lines.append(f"  Last {h['last']}  |  Form {h['form']}")
        lines.append(f"  Away starter TBD")

    elif a:
        lines.append(f"  Home starter TBD")
        lines.append(f"  vs  {a['name']}")
        lines.append(f"      W-L {a['wl']}  ERA {a['era']}  FIP {a['fip']}")
        lines.append(f"      Last {a['last']}  |  Form {a['form']}")

    else:
        lines.append("  Both starters TBD")

    return "\n".join(lines)


def build_email(games):
    """
    Assemble the full email body from a list of processed game dicts.
    """
    today      = date.today().strftime("%A, %B %-d, %Y")
    game_count = len(games)

    tbd_count = sum(
        1 for g in games
        if not g.get("home_pitcher") or not g.get("away_pitcher")
    )

    sections = [
        f"TODAY'S PITCHING MATCHUPS  |  {today}",
        DIVIDER_BOLD,
    ]

    for game in games:
        sections.append(format_game(game))
        sections.append(DIVIDER_SOFT)

    sections.append(
        f"{game_count} game{'s' if game_count != 1 else ''} today"
        + (f"  •  {tbd_count} starter{'s' if tbd_count != 1 else ''} TBD" if tbd_count else "")
    )

    return "\n\n".join(sections)
