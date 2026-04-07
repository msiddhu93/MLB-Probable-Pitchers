# =============================================================================
# formatter.py — Build the plain-text email body
# =============================================================================
# Think of this file as the plating station.
# All data arrives ready-to-use; this file only cares about layout.
#
# Home team is always on the LEFT (left column), away on the RIGHT.
# We use fixed column widths so stats line up neatly in a monospace font.
# =============================================================================

from datetime import date, datetime
import zoneinfo  # built into Python 3.9+; converts UTC game times to ET

# ── Layout constants ──────────────────────────────────────────────────────────
COL_W        = 46    # width of the home (left) column in characters
DIVIDER_BOLD = "═" * 54
DIVIDER_SOFT = "─" * 54


# ── Internal helpers ──────────────────────────────────────────────────────────

def _row(label, home_val, away_val):
    """
    One stat row, home on left, away on right.

    Example output:
      "  ERA   3.42  ERA+ 118            ERA   1.89  ERA+ 215"
    """
    left = f"  {label:<5} {str(home_val)}"
    return f"{left:<{COL_W}}{label:<5} {str(away_val)}"


def _format_game_time(game_date_utc):
    """
    Convert the API's UTC timestamp to a readable Eastern Time string.

    The API gives us something like "2026-04-06T17:05:00Z".
    We convert to ET so readers see "1:05 PM".
    """
    try:
        dt_utc = datetime.fromisoformat(game_date_utc.replace("Z", "+00:00"))
        dt_et  = dt_utc.astimezone(zoneinfo.ZoneInfo("America/New_York"))
        return dt_et.strftime("%-I:%M %p")  # e.g. "1:05 PM"  (%-I = no leading zero)
    except Exception:
        return "TBD"


def _pitcher_vals(pitcher):
    """
    Extract display-ready values from a pitcher dict.
    Returns a dict of strings safe to pass straight to _row().
    """
    if not pitcher:
        return None

    era_plus = pitcher.get("era_plus")
    fip      = pitcher.get("fip")

    return {
        "name":  f"{pitcher.get('name', 'Unknown')} ({pitcher.get('hand', '?')}HP)",
        "wl":    pitcher.get("wl", "?-?"),
        "era":   f"{pitcher.get('era', '-.--')}  ERA+ {era_plus if era_plus is not None else 'N/A'}",
        "fip":   f"{fip:.2f}" if fip is not None else "N/A",
        "last":  pitcher.get("last_outing", "N/A"),
        "form":  pitcher.get("form", "N/A"),
    }


# ── Public functions ──────────────────────────────────────────────────────────

def format_game(game):
    """
    Format one game as a multi-line string with home on left, away on right.

    Layout:
      BOS (6-5) vs NYY (8-3)  •  1:05 PM ET

        Brayan Bello (RHP)          vs  Gerrit Cole (RHP)
        W-L   2-2                       W-L   3-1
        ERA   3.42  ERA+ 118            ERA   1.89  ERA+ 215
        ...
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
        # Name row — home left-padded, "vs" prefix on away
        lines.append(f"  {h['name']:<{COL_W - 2}}vs  {a['name']}")
        lines.append("")
        # Stat rows — each label appears once, values aligned in two columns
        lines.append(_row("W-L",  h["wl"],   a["wl"]))
        lines.append(_row("ERA",  h["era"],  a["era"]))
        lines.append(_row("FIP",  h["fip"],  a["fip"]))
        lines.append(_row("Last", h["last"], a["last"]))
        lines.append(_row("Form", h["form"], a["form"]))

    elif h:
        # Away starter TBD
        lines.append(f"  {h['name']}")
        lines.append("")
        lines.append(f"  W-L  {h['wl']}    ERA  {h['era']}")
        lines.append(f"  FIP  {h['fip']}    Last {h['last']}")
        lines.append(f"  Form {h['form']}")
        lines.append(f"  Away starter TBD")

    elif a:
        # Home starter TBD
        lines.append(f"  Home starter TBD")
        lines.append("")
        lines.append(f"  vs  {a['name']}")
        lines.append(f"      W-L  {a['wl']}    ERA  {a['era']}")
        lines.append(f"      FIP  {a['fip']}    Last {a['last']}")
        lines.append(f"      Form {a['form']}")

    else:
        lines.append("  Both starters TBD")

    return "\n".join(lines)


def build_email(games):
    """
    Assemble the full email body from a list of processed game dicts.

    Structure:
      Header
      ══════ (thick divider)
      Game 1
      ────── (soft divider)
      Game 2
      ──────
      ...
      Footer summary
    """
    today      = date.today().strftime("%A, %B %-d, %Y")
    game_count = len(games)

    # Count games where at least one starter is still TBD
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
