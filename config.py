# =============================================================================
# config.py — All settings in one place
# =============================================================================
# This is the only file you need to personalise.
#
# IMPORTANT: credentials are read from environment variables, not typed here.
# That means your Gmail password never lives in the code — it stays private
# inside GitHub Secrets (Settings → Secrets and variables → Actions).
#
# Locally (for testing): set these in your terminal before running main.py:
#   export SENDER_EMAIL="you@gmail.com"
#   export SENDER_PASSWORD="your-app-password"
#   export RECIPIENT_EMAIL="you@gmail.com"
# =============================================================================

import os

# ── Email ─────────────────────────────────────────────────────────────────────
SENDER_EMAIL    = os.environ["SENDER_EMAIL"]     # Gmail you're sending FROM
SENDER_PASSWORD = os.environ["SENDER_PASSWORD"]  # Gmail App Password (not your real password)
RECIPIENT_EMAIL = os.environ["RECIPIENT_EMAIL"]  # Where the email is delivered

# ── Advanced stat constants ───────────────────────────────────────────────────

# FIP_CONSTANT normalises FIP onto the same scale as ERA.
# It shifts each year with the run environment; 3.15 is a solid MLB average.
# This one genuinely is a constant — it doesn't change game to game.
FIP_CONSTANT = 3.15

# League ERA is NOT here anymore — it's fetched live from the MLB API
# each morning via mlb_api.get_league_era(), so ERA+ stays accurate
# as the season's run environment evolves.
