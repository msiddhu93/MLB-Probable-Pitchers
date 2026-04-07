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


def _format_pitcher_block(pitcher, side):
    """
    Build a list of stat strings for one pitcher.

    `side` is "home" or "away" — used to add the "vs" prefix for the away name line.
    Returns a list of strings (one per display row).
    """
    if not pitcher:
        # TBD case — show a placeholder with blank lines to keep spacing consistent
        prefix = "vs  " if side == "away" else "    "
        return [
            f"{prefix}Probable starter TBD",
            "", "", "", "", ""    # blank rows to match the 6-row stat block
        ]

    name = pitcher.get("name", "Unknown")
    hand = pitcher.get("hand", "?")
    wl   = pitcher.get("wl",   "?-?")
    era  = pitcher.get("era",  "-.--")

    era_plus = pitcher.get("era_plus")
    era_plus_str = f"ERA+ {era_plus:>4}" if era_plus is not None else "ERA+  N/A"

    fip  = pitcher.get("fip")
    fip_str = f"{fip:.2f}" if fip is not None else "N/A"

    last = pitcher.get("last_outing", "N/A")
    form = pitcher.get("form",        "N/A")

    prefix = "vs  " if side == "away" else "    "

    return [
        f"{prefix}{name} ({hand}HP)",
        f"W-L   {wl}",
        f"ERA   {era}  {era_plus_str}",
        f"FIP   {fip_str}",
        f"Last  {last}",
        f"Form  {form}",
    ]


# ── Public functions ──────────────────────────────────────────────────────────

def format_game(game):
    """
    Format one game as a multi-line string.

    Layout:
      BOS (6-5) vs NYY (8-3)  •  1:05 PM ET
      [home pitcher stats]    [away pitcher stats]  ← side by side
    """
    home_name = game.get("home_team",   "???")
    away_name = game.get("away_team",   "???")
    home_rec  = game.get("home_record", "?-?")
    away_rec  = game.get("away_record", "?-?")
    game_time = _format_game_time(game.get("game_date", ""))

    header = f"{home_name} ({home_rec}) vs {away_name} ({away_rec})  •  {game_time} ET"

    # Build per-pitcher row lists
    home_rows = _format_pitcher_block(game.get("home_pitcher"), side="home")
    away_rows = _format_pitcher_block(game.get("away_pitcher"), side="away")

    # Zip the two columns together side by side
    # The name row ("    Brayan Bello (RHP)") gets special treatment for alignment
    lines = [header, ""]
    for i, (h, a) in enumerate(zip(home_rows, away_rows)):
        if i == 0:
            # Name row: home left-padded, away follows
            lines.append(f"  {h:<{COL_W - 2}}{a}")
        elif h.strip() == "" and a.strip() == "":
            lines.append("")
        else:
            lines.append(_row(*h.split(None, 1), *a.split(None, 1))
                         if (h.strip() and a.strip()) else f"  {h}")

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
