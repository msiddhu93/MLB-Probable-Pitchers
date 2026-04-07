# =============================================================================
# main.py — The entry point. Runs the full pipeline.
# =============================================================================
# Think of this file as the head chef — it calls every other station
# in the right order and passes data between them.
#
# Pipeline:
#   1. Fetch raw schedule data       (mlb_api.py)
#   2. Enrich each pitcher with stats (mlb_api.py + stats.py)
#   3. Build the email body           (formatter.py)
#   4. Send the email                 (emailer.py)
# =============================================================================

from datetime import date

import mlb_api   as api
import stats     as metrics
import formatter as fmt
import emailer
import config


# ── Step 1 helper: enrich one pitcher ────────────────────────────────────────

def enrich_pitcher(raw_pitcher, league_era):
    """
    Takes the bare pitcher stub from the schedule API (just an ID and name)
    and builds a full data dict with season stats, advanced metrics, and form.

    league_era is fetched once per run and passed in here so we don't
    hit the API 30 times — one fetch, shared across all pitchers.

    Returns None if the pitcher is TBD (no stub in the schedule response).
    """
    if not raw_pitcher:
        return None

    player_id = raw_pitcher["id"]
    print(f"    Fetching stats for {raw_pitcher.get('fullName', player_id)}...")

    # Fetch raw data from three endpoints
    season_stats = api.get_pitcher_season_stats(player_id)
    game_log     = api.get_pitcher_game_log(player_id)
    details      = api.get_pitcher_details(player_id)

    # Calculate advanced metrics from the raw numbers
    fip      = metrics.calculate_fip(season_stats)
    era_plus = metrics.calculate_era_plus(season_stats, league_era)
    form     = metrics.assess_form(game_log)
    last     = metrics.get_last_outing(game_log)

    # Pull W-L record
    wins   = season_stats.get("wins",   0)
    losses = season_stats.get("losses", 0)

    # Pitching hand: "R" or "L"
    hand = details.get("pitchHand", {}).get("code", "?")

    return {
        "name":         raw_pitcher.get("fullName", "Unknown"),
        "hand":         hand,
        "wl":           f"{wins}-{losses}",
        "era":          season_stats.get("era", "-.--"),
        "era_plus":     era_plus,
        "fip":          fip,
        "last_outing":  last,
        "form":         form,
    }


# ── Step 2 helper: process one game ──────────────────────────────────────────

def build_game_data(raw_game, league_era):
    """
    Takes one raw game dict from the schedule API and returns a clean dict
    ready to hand to the formatter.

    Extracts team names, records, game time, and enriches both pitchers.
    league_era is passed through to enrich_pitcher for ERA+ calculation.
    """
    teams = raw_game.get("teams", {})
    home  = teams.get("home", {})
    away  = teams.get("away", {})

    home_rec = home.get("leagueRecord", {})
    away_rec = away.get("leagueRecord", {})

    home_team = home.get("team", {})
    away_team = away.get("team", {})

    print(f"\n  {home_team.get('abbreviation', '???')} vs {away_team.get('abbreviation', '???')}")

    return {
        "home_team":    home_team.get("abbreviation", "???"),
        "away_team":    away_team.get("abbreviation", "???"),
        "home_record":  f"{home_rec.get('wins', 0)}-{home_rec.get('losses', 0)}",
        "away_record":  f"{away_rec.get('wins', 0)}-{away_rec.get('losses', 0)}",
        "game_date":    raw_game.get("gameDate", ""),   # UTC ISO string → formatter converts to ET
        "home_pitcher": enrich_pitcher(home.get("probablePitcher"), league_era),
        "away_pitcher": enrich_pitcher(away.get("probablePitcher"), league_era),
    }


# ── Main pipeline ─────────────────────────────────────────────────────────────

def main():
    print("=" * 50)
    print("MLB Pitcher Email — starting pipeline")
    print("=" * 50)

    # 1. Fetch today's schedule + current league ERA (both needed before we process pitchers)
    print("\n[1/4] Fetching today's schedule and league ERA from MLB API...")
    raw_data   = api.get_todays_games()
    league_era = api.get_league_era()
    dates      = raw_data.get("dates", [])

    print(f"  Current league ERA: {league_era}")

    if not dates or not dates[0].get("games"):
        print("No MLB games today. No email sent.")
        return

    raw_games = dates[0]["games"]
    print(f"  Found {len(raw_games)} games.")

    # 2. Enrich each game with pitcher stats
    # league_era is fetched once above and passed through — not re-fetched per pitcher
    print("\n[2/4] Fetching pitcher stats...")
    games = [build_game_data(g, league_era) for g in raw_games]

    # 3. Build the email body
    print("\n[3/4] Building email body...")
    body    = fmt.build_email(games)
    today   = date.today().strftime("%A, %B %-d")
    subject = f"MLB Pitching Battle — {today}"

    # Uncomment the next line to preview the email in your terminal before sending:
    # print("\n" + body)

    # 4. Send the email
    print("\n[4/4] Sending email...")
    emailer.send_email(
        to      = config.RECIPIENT_EMAIL,
        subject = subject,
        body    = body,
    )

    print("\nDone.")


if __name__ == "__main__":
    main()
