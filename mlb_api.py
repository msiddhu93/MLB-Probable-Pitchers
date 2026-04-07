# =============================================================================
# mlb_api.py — Fetch raw data from the MLB Stats API
# =============================================================================
# Think of this file as the market run.
# It goes and gets the raw ingredients; nothing is cooked here.
#
# The MLB Stats API is free and requires no API key.
# Base URL: https://statsapi.mlb.com/api/v1
#
# The 'hydrate' parameter is the API's way of bundling related data
# into one response — like asking for a meal deal instead of ordering
# each item separately.
# =============================================================================

import requests
from datetime import date

BASE = "https://statsapi.mlb.com/api/v1"


def get_todays_games(game_date=None):
    """
    Fetch the full schedule for a given date, including probable starters
    and team records.

    Returns the raw JSON from the API. Each game is inside:
        response["dates"][0]["games"]
    """
    if game_date is None:
        game_date = date.today().strftime("%Y-%m-%d")

    resp = requests.get(f"{BASE}/schedule", params={
        "sportId": 1,           # 1 = MLB (other numbers cover MiLB, etc.)
        "date":    game_date,
        # hydrate bundles in the probable pitcher and team record per game
        "hydrate": "probablePitcher,team,linescore",
    })
    resp.raise_for_status()  # raises an error if the request failed
    return resp.json()


def get_pitcher_season_stats(player_id):
    """
    Fetch a pitcher's cumulative stats for the current season.

    Returns a flat dict of raw numbers, e.g.:
        { "era": "2.45", "wins": 3, "strikeOuts": 42, "inningsPitched": "33.0", ... }
    Returns an empty dict if the pitcher hasn't thrown yet this season.
    """
    season = date.today().year

    resp = requests.get(f"{BASE}/people/{player_id}/stats", params={
        "stats": "season",
        "season": season,
        "group":  "pitching",
    })
    resp.raise_for_status()

    splits = resp.json().get("stats", [{}])[0].get("splits", [])
    return splits[0]["stat"] if splits else {}


def get_pitcher_game_log(player_id, num_starts=3):
    """
    Fetch a pitcher's most recent starts.

    The API returns games oldest-first, so we slice from the end
    to get the most recent `num_starts` outings.

    Each entry in the returned list is a dict with a "stat" key containing
    that game's pitching line (IP, ER, K, etc.).
    """
    season = date.today().year

    resp = requests.get(f"{BASE}/people/{player_id}/stats", params={
        "stats": "gameLog",
        "season": season,
        "group":  "pitching",
    })
    resp.raise_for_status()

    splits = resp.json().get("stats", [{}])[0].get("splits", [])
    # Reverse-slice: [-3:] gives us the last 3 items in the list
    return splits[-num_starts:] if splits else []


def get_pitcher_details(player_id):
    """
    Fetch basic player info — most importantly, pitching hand (L or R).

    Returns the full player dict. The field we care about:
        result["pitchHand"]["code"]  →  "R" or "L"
    """
    resp = requests.get(f"{BASE}/people/{player_id}")
    resp.raise_for_status()

    people = resp.json().get("people", [{}])
    return people[0] if people else {}


def get_league_era():
    """
    Calculate the current MLB league ERA from live team pitching totals.

    Fetches season pitching stats for all 30 teams, sums earned runs and
    innings pitched across the league, then applies:
        League ERA = 9 × (total earned runs / total innings pitched)

    This gives us a real, up-to-date denominator for ERA+ rather than a
    hardcoded estimate that drifts as the season progresses.

    Returns a float (e.g. 4.12), or 4.00 as a fallback if the season
    hasn't started yet and the API returns no data.
    """
    season = date.today().year

    resp = requests.get(f"{BASE}/teams/stats", params={
        "season":  season,
        "group":   "pitching",
        "stats":   "season",
        "sportId": 1,
    })
    resp.raise_for_status()

    splits = resp.json().get("stats", [{}])[0].get("splits", [])

    total_er = 0
    total_ip = 0.0

    for team in splits:
        stat = team.get("stat", {})
        try:
            total_er += int(stat.get("earnedRuns",     0) or 0)
            total_ip += _parse_innings(stat.get("inningsPitched", "0"))
        except (ValueError, TypeError):
            continue

    if total_ip == 0:
        return 4.00  # pre-season fallback

    return round(9 * total_er / total_ip, 2)


def _parse_innings(ip_str):
    """
    Convert MLB's innings pitched notation to a true decimal.

    The API stores IP as "33.2" where the digit after the decimal is
    OUTS, not tenths — so "33.2" means 33 full innings + 2 outs = 33.667.

    Using plain float("33.2") = 33.2 is wrong and inflates ERA/FIP slightly.
    """
    try:
        parts = str(ip_str).split(".")
        full  = int(parts[0])
        outs  = int(parts[1]) if len(parts) > 1 else 0
        return full + outs / 3
    except (ValueError, IndexError):
        return 0.0
